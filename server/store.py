"""Store Access: the file-based dataset store (SADS 2.1, 2.6; SRS SR-05).

Layout under the store root (one shared directory for all four processes):
    datasets/<dataset_id>.csv    accepted upload
    datasets/<dataset_id>.json   sidecar {dataset_id, rows, uploaded_at, expires_at}
    jobs/<job_id>.json           job record
    results/<job_id>.json        result of a completed job
    tmp/                         uploads being validated (never visible as datasets)

Directories are created 0700 and files 0600 so that only the service account can read
them (POSIX; on Windows the directory inherits the user-profile ACL - see DEVIATIONS).
Identifiers are random UUIDv4 values and are validated before they touch a path.
"""
import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
DIR_MODE = 0o700
FILE_MODE = 0o600


def new_id():
    return str(uuid.uuid4())


def is_valid_id(value):
    return isinstance(value, str) and bool(UUID_RE.match(value))


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def _chmod(path, mode):
    try:
        os.chmod(path, mode)
    except OSError:
        pass


class DatasetStore:
    def __init__(self, root, retention_s=24 * 3600):
        self.root = Path(root)
        self.retention_s = retention_s
        self.datasets = self.root / "datasets"
        self.jobs = self.root / "jobs"
        self.results = self.root / "results"
        self.tmp = self.root / "tmp"
        self._lock = threading.Lock()

    # ---------- setup ----------
    def init(self):
        for d in (self.root, self.datasets, self.jobs, self.results, self.tmp):
            d.mkdir(parents=True, exist_ok=True)
            _chmod(d, DIR_MODE)
        return self

    # ---------- low level ----------
    def _write_json(self, path, data):
        tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.part")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        _chmod(tmp, FILE_MODE)
        # On Windows os.replace fails while another thread has the target open: retry briefly
        for attempt in range(50):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.01 * (attempt + 1))
        os.replace(tmp, path)

    @staticmethod
    def _read_json(path):
        for attempt in range(20):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return None
            except PermissionError:  # Windows: file being replaced right now
                time.sleep(0.01 * (attempt + 1))
        return None

    # ---------- uploads ----------
    def new_upload_path(self):
        p = self.tmp / f"{uuid.uuid4().hex}.upload"
        p.touch()
        _chmod(p, FILE_MODE)
        return p

    def discard(self, path):
        for attempt in range(20):
            try:
                Path(path).unlink()
                return
            except FileNotFoundError:
                return
            except PermissionError:  # Windows: a handle is still being closed
                time.sleep(0.01 * (attempt + 1))

    # ---------- datasets ----------
    def register_dataset(self, upload_path, rows, now=None):
        now = time.time() if now is None else now
        dataset_id = new_id()
        target = self.datasets / f"{dataset_id}.csv"
        shutil.move(str(upload_path), target)
        _chmod(target, FILE_MODE)
        meta = {"dataset_id": dataset_id, "rows": int(rows),
                "uploaded_at": iso(now), "expires_at": iso(now + self.retention_s)}
        self._write_json(self.datasets / f"{dataset_id}.json", meta)
        return meta

    def dataset_meta(self, dataset_id, now=None):
        if not is_valid_id(dataset_id):
            return None
        meta = self._read_json(self.datasets / f"{dataset_id}.json")
        if meta is None or not (self.datasets / f"{dataset_id}.csv").exists():
            return None
        if parse_iso(meta["expires_at"]) <= (time.time() if now is None else now):
            return None
        return meta

    def dataset_path(self, dataset_id):
        if not is_valid_id(dataset_id):
            raise ValueError("invalid dataset id")
        return self.datasets / f"{dataset_id}.csv"

    # ---------- jobs and results ----------
    def save_job(self, job):
        with self._lock:
            self._write_json(self.jobs / f"{job['job_id']}.json", job)

    def load_job(self, job_id, now=None):
        if not is_valid_id(job_id):
            return None
        job = self._read_json(self.jobs / f"{job_id}.json")
        if job is None:
            return None
        if self.dataset_meta(job["dataset_id"], now=now) is None:
            return None  # its dataset has expired: the job is gone with it
        return job

    def save_result(self, job_id, result):
        self._write_json(self.results / f"{job_id}.json", result)

    def load_result(self, job_id):
        if not is_valid_id(job_id):
            return None
        return self._read_json(self.results / f"{job_id}.json")

    # ---------- retention (SR-05) ----------
    def purge_expired(self, now=None):
        """Delete every expired dataset with its sidecar, job records and results."""
        now = time.time() if now is None else now
        removed = []
        expired = set()
        for side in self.datasets.glob("*.json"):
            meta = self._read_json(side)
            if meta is None or parse_iso(meta["expires_at"]) <= now:
                expired.add(side.stem)
        for job_file in self.jobs.glob("*.json"):
            job = self._read_json(job_file)
            if job is not None and job.get("dataset_id") in expired:
                self.discard(self.results / f"{job_file.stem}.json")
                self.discard(job_file)
        for dataset_id in expired:
            self.discard(self.datasets / f"{dataset_id}.csv")
            self.discard(self.datasets / f"{dataset_id}.json")
            removed.append(dataset_id)
        # leftovers of interrupted uploads older than one hour
        for part in self.tmp.glob("*"):
            try:
                if now - part.stat().st_mtime > 3600:
                    self.discard(part)
            except FileNotFoundError:
                pass
        return removed

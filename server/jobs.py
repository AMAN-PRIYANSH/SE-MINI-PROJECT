"""Job Manager (SADS 2.1, 3.3; SRS REQ-FD-11, REQ-FD-12, REQ-FD-14).

POST /api/analyses creates a job record in the queued state and returns at once
(HTTP 202). A background worker then marks the job running, calls POST /predict on
the selected microservice with only the dataset_id, and records the outcome:
completed (result stored) or failed (reason stored). completed and failed are
terminal states.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from server.store import iso, new_id

log = logging.getLogger("ccfd.jobs")

MODEL_TYPES = ("ml", "dl", "qml")
REASONS = {
    "MODEL_SERVICE_ERROR": "The model service is unavailable; the job was marked failed.",
    "JOB_TIMEOUT": "The analysis timed out; the job was marked failed.",
}


class JobFailure(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class JobManager:
    def __init__(self, store, config):
        self.store = store
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="job")
        self._lock = threading.Lock()

    # ------------------------------------------------------------ public API
    def create(self, dataset_id, model_type):
        job = {"job_id": new_id(), "dataset_id": dataset_id, "model_type": model_type,
               "status": "queued", "created_at": iso(time.time())}
        self.store.save_job(job)
        self.executor.submit(self._run, job["job_id"])
        log.info("job queued job_id=%s dataset_id=%s model_type=%s", job["job_id"], dataset_id, model_type)
        return job

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)

    # ------------------------------------------------------------ worker
    def _update(self, job_id, **fields):
        with self._lock:
            job = self.store.load_job(job_id) or {}
            if not job or job.get("status") in ("completed", "failed"):
                return job
            job.update(fields)
            self.store.save_job(job)
            return job

    def _run(self, job_id):
        job = self._update(job_id, status="running", started_at=iso(time.time()))
        if not job:
            return
        try:
            result = self._call_service(job)
            self.store.save_result(job_id, result)
            self._update(job_id, status="completed", finished_at=iso(time.time()),
                         model_name=result["model_name"])
            log.info("job completed job_id=%s", job_id)
        except JobFailure as f:
            self._fail(job_id, f.code)
        except Exception as e:  # any other problem: never leave a job running, never fake results
            log.error("job error job_id=%s %s", job_id, type(e).__name__)
            self._fail(job_id, "MODEL_SERVICE_ERROR")

    def _fail(self, job_id, code):
        self._update(job_id, status="failed", finished_at=iso(time.time()),
                     reason={"code": code, "message": REASONS[code]})
        log.info("job failed job_id=%s reason=%s", job_id, code)

    def _call_service(self, job):
        """Call POST /predict with a hard overall deadline of job_timeout_s (REQ-FD-14).

        The HTTP call runs in a helper thread so that a service that never answers, or that
        trickles bytes slowly, still ends in JOB_TIMEOUT when the deadline passes.
        """
        url = self.config.service_urls[job["model_type"]].rstrip("/") + "/predict"
        deadline = self.config.job_timeout_s
        outcome = {}

        def call():
            try:
                outcome["resp"] = requests.post(url, json={"dataset_id": job["dataset_id"]},
                                                timeout=(5, deadline + 5))
            except Exception as e:  # recorded and mapped below
                outcome["error"] = e

        worker = threading.Thread(target=call, daemon=True, name=f"predict-{job['job_id'][:8]}")
        worker.start()
        worker.join(deadline)
        if worker.is_alive():
            raise JobFailure("JOB_TIMEOUT")  # the late answer, if any, is ignored
        if "error" in outcome:
            if isinstance(outcome["error"], requests.Timeout):
                raise JobFailure("JOB_TIMEOUT")
            raise JobFailure("MODEL_SERVICE_ERROR")
        resp = outcome["resp"]
        if resp.status_code != 200:
            raise JobFailure("MODEL_SERVICE_ERROR")
        try:
            result = resp.json()
        except ValueError:
            raise JobFailure("MODEL_SERVICE_ERROR")
        meta = self.store.dataset_meta(job["dataset_id"])
        if not valid_result(result, meta["rows"] if meta else None):
            raise JobFailure("MODEL_SERVICE_ERROR")  # contract violation: never shown as success
        return result

    def recover(self):
        """Fail jobs left queued or running by a previous server process (never leave them hanging)."""
        for job_file in self.store.jobs.glob("*.json"):
            job = self.store.load_job(job_file.stem)
            if job and job.get("status") in ("queued", "running"):
                self._fail(job["job_id"], "MODEL_SERVICE_ERROR")


METRIC_KEYS = {"accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix"}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def valid_result(result, expected_rows):
    """Check a POST /predict body against the IPredict contract (SADS 3.2)."""
    if not isinstance(result, dict) or set(result) != {"model_name", "predictions", "metrics"}:
        return False
    if not isinstance(result["model_name"], str) or not result["model_name"]:
        return False
    preds, metrics = result["predictions"], result["metrics"]
    if not isinstance(preds, list) or (expected_rows is not None and len(preds) != expected_rows):
        return False
    for i, p in enumerate(preds):
        if (not isinstance(p, dict) or p.get("row") != i or p.get("class") not in (0, 1)
                or not _is_number(p.get("probability")) or not 0 <= p["probability"] <= 1):
            return False
    if not isinstance(metrics, dict) or set(metrics) != METRIC_KEYS:
        return False
    for k in ("accuracy", "precision", "recall", "f1"):
        if not _is_number(metrics[k]) or not 0 <= metrics[k] <= 1:
            return False
    if metrics["roc_auc"] is not None and not (_is_number(metrics["roc_auc"]) and 0 <= metrics["roc_auc"] <= 1):
        return False
    cm = metrics["confusion_matrix"]
    if not isinstance(cm, dict) or set(cm) != {"tp", "tn", "fp", "fn"}:
        return False
    if not all(isinstance(v, int) and v >= 0 for v in cm.values()) or sum(cm.values()) != len(preds):
        return False
    return True

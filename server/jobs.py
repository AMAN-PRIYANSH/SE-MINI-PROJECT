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
        url = self.config.service_urls[job["model_type"]].rstrip("/") + "/predict"
        try:
            resp = requests.post(url, json={"dataset_id": job["dataset_id"]},
                                 timeout=(5, self.config.job_timeout_s))
        except requests.Timeout:
            raise JobFailure("JOB_TIMEOUT")
        except requests.RequestException:
            raise JobFailure("MODEL_SERVICE_ERROR")
        if resp.status_code != 200:
            raise JobFailure("MODEL_SERVICE_ERROR")
        return resp.json()

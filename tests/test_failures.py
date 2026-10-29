"""Job failure handling (S2-03; TC-JOB-05, TC-JOB-06, TC-SEC-07 step 4, BR-04, NFR-06)."""
import socket
import threading
import time

import pytest
from flask import Flask, jsonify

from server.jobs import valid_result
from server.store import new_id
from tests.helpers import FORBIDDEN_IN_ERRORS
from tests.live import LiveService, wait_for


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start(client, auth, dataset_id, model):
    r = client.post("/api/analyses", headers=auth, json={"dataset_id": dataset_id, "model_type": model})
    assert r.status_code == 202
    return r.get_json()["job_id"]


def poll(client, auth, job_id, timeout=30):
    return wait_for(lambda: (b := client.get(f"/api/analyses/{job_id}", headers=auth).get_json())
                    and b["status"] in ("completed", "failed") and b, timeout=timeout)


def stub(handler):
    app = Flask("stub")
    app.add_url_rule("/predict", "predict", handler, methods=["POST"])
    return LiveService(app)


def test_tc_job_05_service_down_job_fails_others_unaffected(client, auth, uploaded, config, ml_service):
    config.service_urls["qml"] = f"http://127.0.0.1:{free_port()}"  # QML microservice stopped
    dataset_id = uploaded()
    failed = poll(client, auth, start(client, auth, dataset_id, "qml"))
    assert failed["status"] == "failed"
    assert failed["reason"] == {"code": "MODEL_SERVICE_ERROR",
                                "message": "The model service is unavailable; the job was marked failed."}
    assert not {"predictions", "metrics", "model_name"} & set(failed)
    text = str(failed)
    assert not any(s in text for s in FORBIDDEN_IN_ERRORS)  # TC-SEC-07 step 4
    ok = poll(client, auth, start(client, auth, dataset_id, "ml"))
    assert ok["status"] == "completed"


def test_tc_job_06_timeout(client, auth, uploaded, config):
    release = threading.Event()

    def never():
        release.wait(30)
        return jsonify({})

    svc = stub(never)
    try:
        config.service_urls["ml"] = svc.url
        config.job_timeout_s = 1.0  # substitution recorded: 600 s lowered to 1 s
        t0 = time.time()
        body = poll(client, auth, start(client, auth, uploaded(), "ml"))
        assert body["status"] == "failed" and body["reason"]["code"] == "JOB_TIMEOUT"
        assert body["reason"]["message"] == "The analysis timed out; the job was marked failed."
        assert time.time() - t0 < 10
    finally:
        release.set()
        svc.stop()


@pytest.mark.parametrize("response", [
    ("not json", 200),
    ({"code": "E500_MODEL", "message": "x"}, 500),
    ({"model_name": "m", "predictions": [], "metrics": {}}, 200),        # wrong row count
    ({"model_name": "m", "predictions": "x", "metrics": {}}, 200),
])
def test_invalid_service_response_marks_job_failed(client, auth, uploaded, config, response):
    body, status = response
    svc = stub(lambda: (body if isinstance(body, str) else jsonify(body), status))
    try:
        config.service_urls["dl"] = svc.url
        result = poll(client, auth, start(client, auth, uploaded("valid_51.csv"), "dl"))
        assert result["status"] == "failed" and result["reason"]["code"] == "MODEL_SERVICE_ERROR"
    finally:
        svc.stop()


def test_jobs_interrupted_by_a_restart_are_failed_on_startup(config, uploaded, app):
    from server.app import create_app
    store = app.extensions["ccfd_store"]
    job = {"job_id": new_id(), "dataset_id": uploaded(), "model_type": "ml", "status": "running"}
    store.save_job(job)
    create_app(config)  # a new server process starting on the same store
    assert store.load_job(job["job_id"])["status"] == "failed"


def good_result(n):
    return {"model_name": "m",
            "predictions": [{"row": i, "class": 0, "probability": 0.1} for i in range(n)],
            "metrics": {"accuracy": 1.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "roc_auc": None,
                        "confusion_matrix": {"tp": 0, "tn": n, "fp": 0, "fn": 0}}}


def test_valid_result_contract_checks():
    assert valid_result(good_result(3), 3)
    assert not valid_result(good_result(3), 4)
    bad = good_result(3)
    bad["predictions"][1]["probability"] = 1.5
    assert not valid_result(bad, 3)
    bad = good_result(3)
    bad["metrics"]["confusion_matrix"]["tn"] = 2
    assert not valid_result(bad, 3)
    bad = good_result(3)
    bad["extra"] = 1
    assert not valid_result(bad, 3)

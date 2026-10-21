"""Start analysis and job lifecycle (S1-13; TC-JOB-01, TC-MOD-05, TC-SEC-03, TC-SEC-04, TC-API-02)."""
import logging
import time

import pytest

from server.store import new_id
from tests.helpers import assert_error_shape
from tests.live import wait_for


def jobs_in_store(app):
    return list(app.extensions["ccfd_store"].jobs.glob("*.json"))


def start(client, auth, dataset_id, model_type="ml", **extra):
    body = {"dataset_id": dataset_id, "model_type": model_type, **extra}
    return client.post("/api/analyses", headers=auth, json=body)


def test_tc_job_01_and_tc_api_02_accepted_within_2s(app, client, auth, uploaded, ml_service):
    dataset_id = uploaded()
    t0 = time.perf_counter()
    r = start(client, auth, dataset_id)
    assert time.perf_counter() - t0 <= 2
    assert r.status_code == 202 and r.mimetype == "application/json"
    body = r.get_json()
    assert list(body) == ["job_id", "status"] and body["status"] == "queued" and body["job_id"]


def test_job_reaches_completed_and_result_is_stored(app, client, auth, uploaded, ml_service):
    job_id = start(client, auth, uploaded()).get_json()["job_id"]
    store = app.extensions["ccfd_store"]
    job = wait_for(lambda: (j := store.load_job(job_id)) and j["status"] == "completed" and j)
    assert job["model_name"] == "random_forest"
    assert len(store.load_result(job_id)["predictions"]) == 1000
    assert ml_service.predict_calls()[-1][2] == job["dataset_id"]  # only the id is sent


def test_tc_sec_03_no_key_no_job_no_service_call(app, client, uploaded, ml_service):
    dataset_id = uploaded()
    r = client.post("/api/analyses", json={"dataset_id": dataset_id, "model_type": "ml"})
    assert_error_shape(r, 401, "E401_AUTH")
    assert jobs_in_store(app) == []
    assert ml_service.predict_calls() == []


@pytest.mark.parametrize("raw,reason", [
    ('{"dataset_id":', "malformed JSON body"),
    ('{"dataset_id":"DS"}', "missing field: model_type"),
    ('{"dataset_id":"DS","model_type":"ml","debug":true}', "unknown field: debug"),
    ('["ml"]', "the JSON body must be an object"),
    ('{"dataset_id":7,"model_type":"ml"}', "dataset_id must be a non-empty string"),
])
def test_tc_sec_04_malformed_json_rejected_not_logged(app, client, auth, uploaded, ml_service, caplog, raw, reason):
    dataset_id = uploaded()
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    r = client.post("/api/analyses", headers={**auth, "Content-Type": "application/json"},
                    data=raw.replace("DS", dataset_id))
    body = assert_error_shape(r, 400, "E400_VALIDATION")
    assert body["message"] == reason
    assert jobs_in_store(app) == []
    assert ml_service.predict_calls() == []
    logged = caplog.text
    for fragment in ('"debug"', '{"dataset_id"', "true}"):
        assert fragment not in logged


def test_tc_mod_05_unknown_model_type(app, client, auth, uploaded):
    body = assert_error_shape(start(client, auth, uploaded(), "quantum-xyz"), 400, "E400_VALIDATION")
    assert body["message"] == "invalid model_type: must be one of ml, dl, qml"
    assert jobs_in_store(app) == []


def test_unknown_dataset_is_404_without_job(app, client, auth):
    assert_error_shape(start(client, auth, new_id()), 404, "E404_NOT_FOUND")
    assert_error_shape(start(client, auth, "../../etc/passwd"), 404, "E404_NOT_FOUND")
    assert jobs_in_store(app) == []

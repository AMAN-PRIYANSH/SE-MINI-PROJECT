"""Job status endpoint (S1-14; TC-JOB-02 API part, TC-JOB-03, TC-JOB-04, TC-API-03, TC-SEC-10)."""
import pytest

from server.store import new_id
from tests.helpers import assert_error_shape
from tests.live import wait_for


def start(client, auth, dataset_id, model_type="ml"):
    r = client.post("/api/analyses", headers=auth, json={"dataset_id": dataset_id, "model_type": model_type})
    assert r.status_code == 202
    return r.get_json()["job_id"]


def poll(client, auth, job_id):
    return wait_for(lambda: (b := client.get(f"/api/analyses/{job_id}", headers=auth).get_json())
                    and b["status"] in ("completed", "failed") and b)


def test_tc_api_03_completed_shape(client, auth, uploaded, ml_service):
    dataset_id = uploaded()
    job_id = start(client, auth, dataset_id)
    body = poll(client, auth, job_id)
    assert list(body) == ["job_id", "dataset_id", "model_type", "status", "model_name", "predictions", "metrics"]
    assert body["job_id"] == job_id and body["dataset_id"] == dataset_id and body["model_type"] == "ml"
    assert body["status"] == "completed" and body["model_name"] == "random_forest"
    assert len(body["predictions"]) == 1000


def test_tc_api_03_queued_or_running_shape_has_no_results(app, client, auth, uploaded):
    store = app.extensions["ccfd_store"]
    dataset_id = uploaded()
    job = {"job_id": new_id(), "dataset_id": dataset_id, "model_type": "dl", "status": "running"}
    store.save_job(job)
    body = client.get(f"/api/analyses/{job['job_id']}", headers=auth).get_json()
    assert body == {"job_id": job["job_id"], "dataset_id": dataset_id, "model_type": "dl", "status": "running"}


def test_tc_api_03_failed_shape_has_reason_only(app, client, auth, uploaded):
    store = app.extensions["ccfd_store"]
    job = {"job_id": new_id(), "dataset_id": uploaded(), "model_type": "qml", "status": "failed",
           "reason": {"code": "MODEL_SERVICE_ERROR", "message": "m"}}
    store.save_job(job)
    body = client.get(f"/api/analyses/{job['job_id']}", headers=auth).get_json()
    assert body["reason"] == {"code": "MODEL_SERVICE_ERROR", "message": "m"}
    assert "predictions" not in body and "metrics" not in body and "model_name" not in body


def test_tc_job_03_unknown_job_is_404(client, auth):
    assert_error_shape(client.get(f"/api/analyses/{new_id()}", headers=auth), 404, "E404_NOT_FOUND")
    assert_error_shape(client.get("/api/analyses/not-a-uuid", headers=auth), 404, "E404_NOT_FOUND")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-key-123"}])
def test_tc_sec_10_results_need_the_key(client, auth, uploaded, ml_service, headers):
    job_id = start(client, auth, uploaded())
    poll(client, auth, job_id)
    r = client.get(f"/api/analyses/{job_id}", headers=headers)
    body = assert_error_shape(r, 401, "E401_AUTH")
    assert "predictions" not in body


def test_tc_api_05_delete_job_is_405(client, auth, uploaded, ml_service):
    job_id = start(client, auth, uploaded())
    assert_error_shape(client.delete(f"/api/analyses/{job_id}", headers=auth), 405, "E405_METHOD")


def test_tc_job_04_concurrent_jobs_stay_independent(client, auth, uploaded, ml_service):
    a_ds, b_ds = uploaded("valid_1000.csv"), uploaded("valid_51.csv")
    a, b = start(client, auth, a_ds), start(client, auth, b_ds)
    assert a != b
    ra, rb = poll(client, auth, a), poll(client, auth, b)
    assert (ra["dataset_id"], len(ra["predictions"])) == (a_ds, 1000)
    assert (rb["dataset_id"], len(rb["predictions"])) == (b_ds, 51)
    # still associated on a later read within the retention period
    assert client.get(f"/api/analyses/{a}", headers=auth).get_json()["dataset_id"] == a_ds

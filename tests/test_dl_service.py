"""DL microservice and routing (S2-01; TC-MOD-03, TC-MOD-06 for port 5002, TC-JOB-04)."""
import shutil

import pandas as pd

from server.store import new_id
from services.common.app_factory import create_service_app
from services.dl.server import DLPredictor
from shared.metrics import compute_metrics
from tests.conftest import DATA
from tests.helpers import assert_error_shape
from tests.live import wait_for


def test_tc_mod_06_dl_contract_in_isolation(tmp_path):
    (tmp_path / "datasets").mkdir()
    dataset_id = new_id()
    shutil.copy(DATA / "valid_1000.csv", tmp_path / "datasets" / f"{dataset_id}.csv")
    c = create_service_app(DLPredictor().load(), tmp_path, "dl").test_client()
    assert c.get("/health").get_json() == {"status": "ok"}
    body = c.post("/predict", json={"dataset_id": dataset_id}).get_json()
    assert body["model_name"] == "mlp" and len(body["predictions"]) == 1000
    labels = pd.read_csv(DATA / "valid_1000.csv")["Class"]
    assert body["metrics"] == compute_metrics(labels, [p["class"] for p in body["predictions"]],
                                              [p["probability"] for p in body["predictions"]])
    assert_error_shape(c.post("/predict", json={"dataset_id": new_id()}), 404, "E404_NOT_FOUND")


def poll(client, auth, job_id):
    return wait_for(lambda: (b := client.get(f"/api/analyses/{job_id}", headers=auth).get_json())
                    and b["status"] in ("completed", "failed") and b)


def test_tc_mod_03_dl_selection_routes_to_dl(client, auth, uploaded, ml_service, dl_service):
    r = client.post("/api/analyses", headers=auth, json={"dataset_id": uploaded(), "model_type": "dl"})
    assert r.status_code == 202
    body = poll(client, auth, r.get_json()["job_id"])
    assert body["status"] == "completed" and body["model_name"] == "mlp"
    assert len(dl_service.predict_calls()) == 1 and ml_service.predict_calls() == []


def test_tc_job_04_ml_and_dl_jobs_back_to_back(client, auth, uploaded, ml_service, dl_service):
    a_ds, b_ds = uploaded("valid_1000.csv"), uploaded("valid_51.csv")
    a = client.post("/api/analyses", headers=auth, json={"dataset_id": a_ds, "model_type": "ml"}).get_json()
    b = client.post("/api/analyses", headers=auth, json={"dataset_id": b_ds, "model_type": "dl"}).get_json()
    ra, rb = poll(client, auth, a["job_id"]), poll(client, auth, b["job_id"])
    assert (ra["dataset_id"], ra["model_type"], ra["model_name"], len(ra["predictions"])) == \
        (a_ds, "ml", "random_forest", 1000)
    assert (rb["dataset_id"], rb["model_type"], rb["model_name"], len(rb["predictions"])) == (b_ds, "dl", "mlp", 51)

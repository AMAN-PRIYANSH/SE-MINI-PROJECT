"""QML microservice (S2-02; TC-MOD-04, TC-MOD-06 for port 5003, TC-MET-04)."""
import shutil
import time

import numpy as np
import pandas as pd

from server.store import new_id
from services.common.app_factory import create_service_app
from services.qml.server import QMLPredictor
from shared.metrics import compute_metrics
from tests.conftest import DATA
from tests.helpers import assert_error_shape
from tests.live import wait_for


def test_tc_mod_06_qml_contract_in_isolation(tmp_path):
    (tmp_path / "datasets").mkdir()
    dataset_id = new_id()
    shutil.copy(DATA / "valid_1000.csv", tmp_path / "datasets" / f"{dataset_id}.csv")
    c = create_service_app(QMLPredictor().load(), tmp_path, "qml").test_client()
    assert c.get("/health").get_json() == {"status": "ok"}
    t0 = time.perf_counter()
    body = c.post("/predict", json={"dataset_id": dataset_id}).get_json()
    assert time.perf_counter() - t0 < 60  # far inside the 600 s job limit
    assert body["model_name"] == "vqc_4qubit" and len(body["predictions"]) == 1000
    labels = pd.read_csv(DATA / "valid_1000.csv")["Class"]
    assert body["metrics"] == compute_metrics(labels, [p["class"] for p in body["predictions"]],
                                              [p["probability"] for p in body["predictions"]])
    assert_error_shape(c.post("/predict", json={"dataset_id": new_id()}), 404, "E404_NOT_FOUND")


def test_qml_probabilities_are_deterministic_and_in_range():
    p = QMLPredictor().load()
    x = pd.read_csv(DATA / "valid_51.csv")[p.bundle["features"]].to_numpy(float)
    a, b = p.predict_proba(x), p.predict_proba(x)
    assert np.allclose(a, b) and (a >= 0).all() and (a <= 1).all()


def poll(client, auth, job_id):
    return wait_for(lambda: (b := client.get(f"/api/analyses/{job_id}", headers=auth).get_json())
                    and b["status"] in ("completed", "failed") and b, timeout=120)


def test_tc_mod_04_qml_routing(client, auth, uploaded, qml_service):
    r = client.post("/api/analyses", headers=auth, json={"dataset_id": uploaded(), "model_type": "qml"})
    assert r.status_code == 202
    body = poll(client, auth, r.get_json()["job_id"])
    assert body["status"] == "completed" and body["model_name"] == "vqc_4qubit"
    assert len(qml_service.predict_calls()) == 1


def test_tc_met_04_same_dataset_three_models_comparable(client, auth, uploaded, ml_service, dl_service, qml_service):
    dataset_id = uploaded()
    sets = {}
    for model in ("ml", "dl", "qml"):
        job = client.post("/api/analyses", headers=auth, json={"dataset_id": dataset_id, "model_type": model})
        body = poll(client, auth, job.get_json()["job_id"])
        assert body["status"] == "completed"
        sets[body["model_name"]] = body["metrics"]
        assert sum(body["metrics"]["confusion_matrix"].values()) == 1000
    assert set(sets) == {"random_forest", "mlp", "vqc_4qubit"}
    shapes = {name: (tuple(m), tuple(m["confusion_matrix"])) for name, m in sets.items()}
    assert len(set(shapes.values())) == 1

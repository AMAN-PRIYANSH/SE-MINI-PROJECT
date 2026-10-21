"""STP cases that need the whole API flow and are not covered in a feature test file
(S2-14): TC-MOD-02, TC-MET-01, TC-MET-02, TC-MET-05, TC-RES-03, TC-SEC-07, TC-API-04."""
import json
import re

import pytest

from server.store import new_id
from tests.conftest import DATA
from tests.fixtures.reference_metrics import labels_from_csv, reference
from tests.helpers import FORBIDDEN_IN_ERRORS, assert_error_shape
from tests.live import wait_for


def run_job(client, auth, dataset_id, model="ml"):
    r = client.post("/api/analyses", headers=auth, json={"dataset_id": dataset_id, "model_type": model})
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]
    return wait_for(lambda: (b := client.get(f"/api/analyses/{job_id}", headers=auth).get_json())
                    and b["status"] in ("completed", "failed") and b)


def test_tc_mod_02_ml_selection_routes_to_ml(client, auth, uploaded, ml_service):
    dataset_id = uploaded()
    body = run_job(client, auth, dataset_id, "ml")
    assert body["status"] == "completed" and body["model_name"] == "random_forest"  # configured classifier
    assert ml_service.predict_calls() == [("POST", "/predict", dataset_id)]


def test_tc_met_01_metrics_match_independent_reference(client, auth, uploaded, ml_service, tmp_path):
    body = run_job(client, auth, uploaded("valid_1000.csv"))
    preds = body["predictions"]
    ref = reference(labels_from_csv(DATA / "valid_1000.csv"), [p["class"] for p in preds],
                    [p["probability"] for p in preds])
    (tmp_path / "reference_metrics.json").write_text(json.dumps(ref))
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        value = body["metrics"][key]
        assert value == ref[key], key
        assert re.fullmatch(r"\d\.\d{1,4}", repr(value)) or value in (0, 1), key  # four decimal places
    assert body["metrics"]["confusion_matrix"] == ref["confusion_matrix"]


def test_tc_met_02_confusion_matrix_consistent(client, auth, uploaded, ml_service):
    body = run_job(client, auth, uploaded("valid_51.csv"))
    cm = body["metrics"]["confusion_matrix"]
    assert all(isinstance(cm[k], int) for k in ("tp", "tn", "fp", "fn"))
    assert sum(cm.values()) == 51


def test_tc_met_05_tiny_dataset_by_hand(client, auth, uploaded, ml_service):
    body = run_job(client, auth, uploaded("tiny_4row.csv"))
    labels = labels_from_csv(DATA / "tiny_4row.csv")
    preds = body["predictions"]
    assert len(preds) == 4
    # hand computation, written out for 4 rows
    tp = sum(y == 1 and p["class"] == 1 for y, p in zip(labels, preds))
    tn = sum(y == 0 and p["class"] == 0 for y, p in zip(labels, preds))
    fp = sum(y == 0 and p["class"] == 1 for y, p in zip(labels, preds))
    fn = sum(y == 1 and p["class"] == 0 for y, p in zip(labels, preds))
    assert body["metrics"]["confusion_matrix"] == {"tp": tp, "tn": tn, "fp": fp, "fn": fn}
    assert body["metrics"]["accuracy"] == round((tp + tn) / 4, 4)
    pos = [p["probability"] for y, p in zip(labels, preds) if y == 1]
    neg = [p["probability"] for y, p in zip(labels, preds) if y == 0]
    pairs = [(a, b) for a in pos for b in neg]
    assert body["metrics"]["roc_auc"] == round(sum(1 if a > b else 0.5 if a == b else 0 for a, b in pairs)
                                               / len(pairs), 4)


def test_tc_res_03_prediction_domains(client, auth, uploaded, ml_service):
    preds = run_job(client, auth, uploaded("valid_1000.csv"))["predictions"]
    assert len(preds) == 1000
    assert all(p["class"] in (0, 1) and 0.0 <= p["probability"] <= 1.0 for p in preds)


def test_tc_sec_07_errors_disclose_no_internals(client, auth, uploaded, app, monkeypatch, config, ml_service):
    # step 1: unknown job
    assert_error_shape(client.get(f"/api/analyses/{new_id()}", headers=auth), 404, "E404_NOT_FOUND")
    # step 2: malformed JSON
    r = client.post("/api/analyses", headers={**auth, "Content-Type": "application/json"}, data='{"dataset_id":')
    assert_error_shape(r, 400, "E400_VALIDATION")
    # step 3: the store cannot be written (read-only directory) -> 500 without paths or traces
    store = app.extensions["ccfd_store"]

    def read_only(*a, **k):
        raise PermissionError(13, "Permission denied", str(store.datasets / "x.csv"))
    monkeypatch.setattr(store, "register_dataset", read_only)
    import io
    r = client.post("/api/datasets", headers=auth,
                    data={"file": (io.BytesIO((DATA / "valid_1000.csv").read_bytes()), "valid_1000.csv")},
                    content_type="multipart/form-data")
    body = assert_error_shape(r, 500, "E500_INTERNAL")
    assert str(config.store_dir) not in str(body) and "Permission" not in body["message"]
    monkeypatch.undo()
    # step 4: a failed job's reason
    config.service_urls["qml"] = "http://127.0.0.1:9"
    failed = run_job(client, auth, uploaded("valid_51.csv"), "qml")
    assert set(failed["reason"]) == {"code", "message"}
    assert not any(s in json.dumps(failed) for s in FORBIDDEN_IN_ERRORS)


@pytest.mark.parametrize("call,status,code", [
    (lambda c, a: c.post("/api/datasets", headers=a, data={"file": (__import__("io").BytesIO(b""), "e.csv")},
                         content_type="multipart/form-data"), 400, "E400_VALIDATION"),
    (lambda c, a: c.get(f"/api/analyses/{new_id()}"), 401, "E401_AUTH"),
    (lambda c, a: c.get(f"/api/analyses/{new_id()}", headers=a), 404, "E404_NOT_FOUND"),
])
def test_tc_api_04_uniform_error_body(client, auth, call, status, code):
    assert_error_shape(call(client, auth), status, code)

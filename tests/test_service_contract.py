"""Shared microservice contract (S1-11; TC-MOD-06 shape, TC-MET-02, TC-RES-03)."""
import shutil

import numpy as np
import pytest

from server.store import new_id
from services.common.app_factory import create_service_app
from services.common.predictor import Predictor
from tests.conftest import DATA
from tests.helpers import assert_error_shape


class FakePredictor(Predictor):
    model_name = "fake_model"

    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail

    def load(self):
        self.ready = True

    def predict_proba(self, x):
        if self.fail:
            raise RuntimeError("boom")
        return 1 / (1 + np.exp(-x[:, 13]))  # any deterministic score in (0, 1)


@pytest.fixture
def store_dir(tmp_path):
    (tmp_path / "datasets").mkdir()
    return tmp_path


def place(store_dir, name="valid_1000.csv"):
    dataset_id = new_id()
    shutil.copy(DATA / name, store_dir / "datasets" / f"{dataset_id}.csv")
    return dataset_id


def service(store_dir, **kw):
    p = FakePredictor(**kw)
    p.load()
    return create_service_app(p, store_dir, "test").test_client()


def test_health_ok_and_not_ready(store_dir):
    assert service(store_dir).get("/health").get_json() == {"status": "ok"}
    p = FakePredictor()
    r = create_service_app(p, store_dir, "t").test_client().get("/health")
    assert r.status_code == 503 and r.get_json() == {"status": "not_ready"}


def test_predict_contract_shape(store_dir):
    r = service(store_dir).post("/predict", json={"dataset_id": place(store_dir)})
    assert r.status_code == 200
    body = r.get_json()
    assert list(body) == ["model_name", "predictions", "metrics"]
    assert body["model_name"] == "fake_model"
    assert set(body["metrics"]) == {"accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix"}
    assert set(body["metrics"]["confusion_matrix"]) == {"tp", "tn", "fp", "fn"}
    assert set(body["predictions"][0]) == {"row", "class", "probability"}


def test_tc_res_03_value_domains_and_tc_met_02_counts(store_dir):
    body = service(store_dir).post("/predict", json={"dataset_id": place(store_dir)}).get_json()
    preds = body["predictions"]
    assert len(preds) == 1000
    assert [p["row"] for p in preds] == list(range(1000))
    assert all(p["class"] in (0, 1) and 0 <= p["probability"] <= 1 for p in preds)
    assert all(p["class"] == int(p["probability"] >= 0.5) for p in preds)
    cm = body["metrics"]["confusion_matrix"]
    assert all(isinstance(v, int) for v in cm.values())
    assert sum(cm.values()) == 1000


def test_extra_columns_are_ignored(store_dir):
    body = service(store_dir).post("/predict", json={"dataset_id": place(store_dir, "extra_cols.csv")}).get_json()
    assert len(body["predictions"]) == 100


def test_unknown_dataset_is_404(store_dir):
    assert_error_shape(service(store_dir).post("/predict", json={"dataset_id": new_id()}), 404, "E404_NOT_FOUND")
    assert_error_shape(service(store_dir).post("/predict", json={"dataset_id": "../../x"}), 404, "E404_NOT_FOUND")


@pytest.mark.parametrize("body", [None, [], {}, {"dataset_id": 5}, {"dataset_id": "x", "debug": True}])
def test_bad_body_is_400(store_dir, body):
    c = service(store_dir)
    r = c.post("/predict", json=body) if body is not None else c.post("/predict", data="{bad")
    assert_error_shape(r, 400, "E400_VALIDATION")


def test_model_failure_is_500_without_partial_results(store_dir):
    r = service(store_dir, fail=True).post("/predict", json={"dataset_id": place(store_dir)})
    body = assert_error_shape(r, 500, "E500_MODEL")
    assert "predictions" not in body


def test_wrong_method_is_405(store_dir):
    assert_error_shape(service(store_dir).get("/predict"), 405, "E405_METHOD")

"""ML microservice with the real trained models (S1-12; TC-MOD-06 for port 5001)."""
import shutil

import pytest

from server.store import new_id
from services.common.app_factory import create_service_app
from services.ml.server import MLPredictor
from shared.metrics import compute_metrics
from tests.conftest import DATA

import pandas as pd


@pytest.fixture
def store_dir(tmp_path):
    (tmp_path / "datasets").mkdir()
    return tmp_path


@pytest.mark.parametrize("name", ["random_forest", "logistic_regression"])
def test_configured_classifier_is_used_and_named(store_dir, name):
    dataset_id = new_id()
    shutil.copy(DATA / "valid_1000.csv", store_dir / "datasets" / f"{dataset_id}.csv")
    client = create_service_app(MLPredictor(name).load(), store_dir, "ml").test_client()
    assert client.get("/health").get_json() == {"status": "ok"}
    body = client.post("/predict", json={"dataset_id": dataset_id}).get_json()
    assert body["model_name"] == name
    assert len(body["predictions"]) == 1000
    # TC-MET-01 style: metrics equal an independent computation from the same predictions
    labels = pd.read_csv(DATA / "valid_1000.csv")["Class"]
    classes = [p["class"] for p in body["predictions"]]
    probs = [p["probability"] for p in body["predictions"]]
    assert body["metrics"] == compute_metrics(labels, classes, probs)


def test_default_model_is_random_forest(monkeypatch):
    monkeypatch.delenv("CCFD_ML_MODEL", raising=False)
    assert MLPredictor().model_name == "random_forest"


def test_unknown_configured_model_rejected(monkeypatch):
    monkeypatch.setenv("CCFD_ML_MODEL", "svm")
    with pytest.raises(ValueError):
        MLPredictor()

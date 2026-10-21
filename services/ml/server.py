"""ML microservice - port 5001 (SRS REQ-FD-07; SADS 2.1, 2.5).

Hosts the trained Logistic Regression and Random Forest classifiers and runs the one
named in its configuration (CCFD_ML_MODEL, default random_forest) for every analysis.

    python -m services.ml.server
"""
import os
from pathlib import Path

import joblib

from services.common.app_factory import run_service
from services.common.predictor import Predictor

MODEL_DIR = Path(__file__).resolve().parent / "model"
CHOICES = ("random_forest", "logistic_regression")


class MLPredictor(Predictor):
    def __init__(self, model_name=None):
        super().__init__()
        self.model_name = model_name or os.environ.get("CCFD_ML_MODEL", "random_forest")
        if self.model_name not in CHOICES:
            raise ValueError(f"CCFD_ML_MODEL must be one of {CHOICES}")
        self.model = None

    def load(self):
        bundle = joblib.load(MODEL_DIR / f"{self.model_name}.joblib")
        self.model = bundle["model"]
        self.ready = True
        return self

    def predict_proba(self, x):
        return self.model.predict_proba(x)[:, 1]


if __name__ == "__main__":
    run_service(MLPredictor(), "ml", 5001, "CCFD_ML_PORT")

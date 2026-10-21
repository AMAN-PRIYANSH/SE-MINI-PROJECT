"""DL microservice - port 5002 (SRS REQ-FD-08; SADS 2.1, 2.5).

Hosts the trained multilayer perceptron (model_name "mlp").

    python -m services.dl.server
"""
from pathlib import Path

import joblib

from services.common.app_factory import run_service
from services.common.predictor import Predictor

MODEL_FILE = Path(__file__).resolve().parent / "model" / "mlp.joblib"


class DLPredictor(Predictor):
    model_name = "mlp"

    def __init__(self):
        super().__init__()
        self.model = None

    def load(self):
        self.model = joblib.load(MODEL_FILE)["model"]
        self.ready = True
        return self

    def predict_proba(self, x):
        return self.model.predict_proba(x)[:, 1]


if __name__ == "__main__":
    run_service(DLPredictor(), "dl", 5002, "CCFD_DL_PORT")

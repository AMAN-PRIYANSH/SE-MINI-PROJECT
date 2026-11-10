"""DL microservice - port 5002 (SRS REQ-FD-08; SADS 2.1, 2.5).

Hosts two deep-learning models and runs the one named in its configuration
(CCFD_DL_MODEL, default mlp) for every analysis:

    mlp  sklearn MLPClassifier (64+32 ReLU, Adam, early stopping)
    dnn  PyTorch feed-forward net (128+64 ReLU, dropout, Adam, BCE with a
         positive-class weight) - see services/dl/dnn.py

    python -m services.dl.server
"""
import os
from pathlib import Path

import joblib

from services.common.app_factory import run_service
from services.common.predictor import Predictor
from services.dl import dnn as dnn_mod

MODEL_DIR = Path(__file__).resolve().parent / "model"
CHOICES = ("mlp", "dnn")


class DLPredictor(Predictor):
    def __init__(self, model_name=None):
        super().__init__()
        self.model_name = model_name or os.environ.get("CCFD_DL_MODEL", "mlp")
        if self.model_name not in CHOICES:
            raise ValueError(f"CCFD_DL_MODEL must be one of {CHOICES}")
        self.model = None
        self.scaler = None
        self.threshold = 0.5

    def load(self):
        if self.model_name == "mlp":
            self.model = joblib.load(MODEL_DIR / "mlp.joblib")["model"]
        else:
            self.model, self.scaler, self.threshold = dnn_mod.load_bundle(MODEL_DIR / "dnn.joblib")
        self.ready = True
        return self

    def predict(self, x):
        classes, proba = super().predict(x)
        if self.model_name == "dnn":
            # The DNN was trained with a large positive-class weight, so its
            # probabilities are not calibrated for a 0.5 cut; use the threshold
            # tuned on the validation split (stored in the model bundle).
            classes = (proba >= self.threshold).astype(int)
        return classes, proba

    def predict_proba(self, x):
        if self.model_name == "mlp":
            return self.model.predict_proba(x)[:, 1]
        return dnn_mod.predict_proba(self.model, self.scaler, x)


if __name__ == "__main__":
    run_service(DLPredictor(), "dl", 5002, "CCFD_DL_PORT")

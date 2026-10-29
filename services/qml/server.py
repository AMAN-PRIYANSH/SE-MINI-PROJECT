"""QML microservice - port 5003 (SRS REQ-FD-09; SADS 2.1, 2.5).

Hosts a 4-qubit variational quantum classifier executed on the PennyLane
"default.qubit" state-vector simulator (see services/qml/circuit.py).

    python -m services.qml.server
"""
from pathlib import Path

import joblib
import numpy as np

from services.common.app_factory import run_service
from services.common.predictor import Predictor
from services.qml import circuit

MODEL_FILE = Path(__file__).resolve().parent / "model" / "vqc.joblib"


class QMLPredictor(Predictor):
    model_name = "vqc_4qubit"

    def __init__(self):
        super().__init__()
        self.bundle = None

    def load(self):
        self.bundle = joblib.load(MODEL_FILE)
        self.ready = True
        return self

    def predict_proba(self, x):
        b = self.bundle
        angles = b["angle"].transform(b["pca"].transform(b["scaler"].transform(x)))
        return circuit.predict_proba(angles, np.asarray(b["weights"]), b["a"], b["b"])


if __name__ == "__main__":
    run_service(QMLPredictor(), "qml", 5003, "CCFD_QML_PORT")

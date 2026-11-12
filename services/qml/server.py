"""QML microservice - port 5003 (SRS REQ-FD-09; SADS 2.1, 2.5).

Hosts two quantum models on the PennyLane "default.qubit" state-vector simulator
and runs the one named in its configuration (CCFD_QML_MODEL, default vqc_4qubit):

    vqc_4qubit  4-qubit variational quantum classifier (see services/qml/circuit.py)
    qsvm        quantum-kernel SVM: fidelity kernel + sklearn SVC (see services/qml/kernel.py)

    python -m services.qml.server
"""
import os
from pathlib import Path

import joblib
import numpy as np

from services.common.app_factory import run_service
from services.common.predictor import Predictor
from services.qml import circuit, kernel

MODEL_DIR = Path(__file__).resolve().parent / "model"
CHOICES = ("vqc_4qubit", "qsvm")


class QMLPredictor(Predictor):
    def __init__(self, model_name=None):
        super().__init__()
        self.model_name = model_name or os.environ.get("CCFD_QML_MODEL", "vqc_4qubit")
        if self.model_name not in CHOICES:
            raise ValueError(f"CCFD_QML_MODEL must be one of {CHOICES}")
        self.bundle = None

    def load(self):
        self.bundle = joblib.load(MODEL_DIR / f"{'vqc' if self.model_name == 'vqc_4qubit' else 'qsvm'}.joblib")
        self.ready = True
        return self

    def predict_proba(self, x):
        b = self.bundle
        angles = b["angle"].transform(b["pca"].transform(b["scaler"].transform(x)))
        if self.model_name == "vqc_4qubit":
            return circuit.predict_proba(angles, np.asarray(b["weights"]), b["a"], b["b"])
        states = kernel.feature_states(angles, b["kernel_weights"])
        k = kernel.fidelity_kernel(states, b["train_states"])
        return b["svc"].predict_proba(k)[:, 1]


if __name__ == "__main__":
    run_service(QMLPredictor(), "qml", 5003, "CCFD_QML_PORT")

"""Base class for the model held by a microservice (SADS 3.4: model_loader.py, predictor.py)."""
import numpy as np


class Predictor:
    """Subclasses load one trained model and turn a feature matrix into fraud probabilities."""

    model_name = "unknown"

    def __init__(self):
        self.ready = False

    def load(self):
        raise NotImplementedError

    def predict_proba(self, x):
        """Return the probability of class 1 (fraud) for every row of x."""
        raise NotImplementedError

    def predict(self, x):
        proba = np.clip(np.asarray(self.predict_proba(x), dtype=float), 0.0, 1.0)
        proba = np.round(proba, 6)
        classes = (proba >= 0.5).astype(int)
        return classes, proba

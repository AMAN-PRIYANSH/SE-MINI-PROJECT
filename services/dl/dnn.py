"""PyTorch deep neural network hosted by the DL microservice (second DL algorithm).

Architecture: StandardScaler -> Linear(29 -> 128) ReLU -> Dropout -> Linear(128 -> 64)
ReLU -> Dropout -> Linear(64 -> 1). Trained with Adam on BCEWithLogitsLoss with a
positive-class weight, because fraud is ~0.17 % of the data (see training/train_dl.py).

The model definition lives here, next to the service that loads it, so training and
serving can never drift apart: the training script saves a joblib bundle
(state_dict + architecture + scaler + decision threshold) and the service rebuilds
exactly this module.
"""
import numpy as np
import torch
import torch.nn as nn

MODEL_NAME = "dnn"


class FraudDNN(nn.Module):
    """Feed-forward classifier: input_dim features -> hidden_sizes -> one logit."""

    def __init__(self, input_dim, hidden_sizes=(128, 64), dropout=0.1):
        super().__init__()
        layers = []
        prev = input_dim
        for size in hidden_sizes:
            layers += [nn.Linear(prev, size), nn.ReLU(), nn.Dropout(dropout)]
            prev = size
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


def load_bundle(path):
    """Rebuild a FraudDNN from a joblib bundle saved by the training script.

    Returns (model, scaler, threshold): the decision threshold was tuned on the
    validation split for max F1 (see training/train_dl.py) and the service must
    apply it instead of the usual 0.5 cut.
    """
    import joblib

    bundle = joblib.load(path)
    model = FraudDNN(len(bundle["features"]), tuple(bundle["hidden_sizes"]),
                     bundle["dropout"])
    # state_dict was saved as numpy arrays (joblib); convert back to tensors.
    model.load_state_dict({k: torch.as_tensor(v) for k, v in bundle["state_dict"].items()})
    model.eval()
    return model, bundle["scaler"], float(bundle.get("threshold", 0.5))


def predict_proba(model, scaler, x, batch=10_000):
    """Fraud probabilities for a feature matrix (numpy -> numpy, no gradients)."""
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(x), batch):
            z = torch.as_tensor(scaler.transform(x[i:i + batch]), dtype=torch.float32)
            out.append(torch.sigmoid(model(z)).numpy())
    return np.concatenate(out) if out else np.zeros(0)

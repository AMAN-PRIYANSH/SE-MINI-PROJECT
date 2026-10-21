"""Variational quantum classifier used by the QML microservice (SRS REQ-FD-09).

Simulator (resolves SRS TBD-03): PennyLane "default.qubit", a classical state-vector
simulator - no quantum hardware is needed.

Model:
    features (29) -> StandardScaler -> PCA (4 components) -> scaled to [0, pi]
    -> AngleEmbedding (RY) on 4 qubits -> StronglyEntanglingLayers (4 layers)
    -> <Z> on wire 0 -> p(fraud) = sigmoid(a * <Z> + b)
The circuit is evaluated for many rows at once with parameter broadcasting.
"""
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

N_QUBITS = 4
N_LAYERS = 4
DEVICE = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(DEVICE, interface="autograd")
def circuit(angles, weights):
    # angles: (batch, N_QUBITS) -> broadcast over the batch dimension
    qml.AngleEmbedding(angles, wires=range(N_QUBITS), rotation="Y")
    qml.StronglyEntanglingLayers(weights, wires=range(N_QUBITS))
    return qml.expval(qml.PauliZ(0))


def sigmoid(z):
    return 1 / (1 + pnp.exp(-z))


def forward(angles, weights, a, b):
    return sigmoid(a * circuit(angles, weights) + b)


def predict_proba(angles, weights, a, b, chunk=20_000):
    out = []
    for i in range(0, len(angles), chunk):
        part = np.asarray(angles[i:i + chunk], dtype=float)
        out.append(np.asarray(forward(part, weights, a, b), dtype=float).reshape(-1))
    return np.concatenate(out) if out else np.zeros(0)

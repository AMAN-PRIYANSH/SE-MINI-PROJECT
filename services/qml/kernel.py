"""Quantum kernel for the QSVM hosted by the QML microservice (second QML algorithm).

Feature map: the same StandardScaler -> PCA (4) -> [0, pi] preprocessing as the VQC,
then AngleEmbedding (RY) plus StronglyEntanglingLayers with FIXED random weights on
4 qubits. The kernel between two rows is the squared fidelity of their feature states:

    k(x, y) = |<phi(x)|phi(y)>|^2

It is computed from batched statevectors, one circuit execution per row rather than
one per pair, so a whole kernel matrix is a single matrix product in numpy:
    K = |S @ S_train^H|^2
This is what makes the QSVM fast enough to score the full test split: the VQC
already evaluates the full test set the same way (see services/qml/circuit.py).
"""
import numpy as np
import pennylane as qml

N_QUBITS = 4
DEVICE = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(DEVICE, interface="autograd")
def _states(angles, weights):
    qml.AngleEmbedding(angles, wires=range(N_QUBITS), rotation="Y")
    qml.StronglyEntanglingLayers(weights, wires=range(N_QUBITS))
    return qml.state()


def feature_states(angles, weights, chunk=20_000):
    """Statevectors for a batch of angle-encoded rows: shape (n_rows, 2**N_QUBITS)."""
    out = []
    for i in range(0, len(angles), chunk):
        out.append(np.asarray(_states(np.asarray(angles[i:i + chunk], dtype=float), weights)))
    return np.concatenate(out) if out else np.zeros((0, 2 ** N_QUBITS), dtype=complex)


def fidelity_kernel(states_a, states_b):
    """Squared-fidelity kernel matrix between two sets of statevectors."""
    return np.abs(states_a @ states_b.conj().T) ** 2

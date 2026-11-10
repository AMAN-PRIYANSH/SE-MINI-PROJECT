"""Train the QML models served by the QML microservice (SRS REQ-FD-09, TBD-03).

    python training/train_qml.py

Two quantum models on the same 4 PCA features (StandardScaler -> PCA (4) -> [0, pi]):

    vqc_4qubit  4-qubit variational quantum classifier (AngleEmbedding +
                StronglyEntanglingLayers, Adam on binary cross-entropy).
    qsvm        quantum-kernel SVM: the same feature map with FIXED random weights
                defines a fidelity kernel k(x, y) = |<phi(x)|phi(y)>|^2, and a
                classical SVC is fitted on the precomputed kernel matrix.

Quantum simulation is expensive, so both models train on a balanced sample of the
training split (all fraud rows up to 400, plus as many legitimate rows); evaluation
uses the full 20 % test split. Hyperparameters come from params.yaml; the run is
logged to MLflow.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from pennylane import numpy as pnp
import pennylane as qml
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import SVC

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from services.qml import kernel  # noqa: E402
from services.qml.circuit import N_LAYERS, N_QUBITS, forward, predict_proba  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402
from training.mlflow_utils import end_run, log_artifact, log_metrics, start_run  # noqa: E402
from training.params import load_params  # noqa: E402
from training.prepare_data import SEED, load, split  # noqa: E402

OUT = ROOT / "services" / "qml" / "model"


def main():
    params = load_params()
    qp = params["qml"]
    assert qp["n_qubits"] == N_QUBITS and qp["n_layers"] == N_LAYERS, \
        "params.yaml qml.n_qubits/n_layers diverged from services/qml/circuit.py"
    start_run("train-qml", {"seed": params["seed"], "qml": qp,
                            "simulator": "pennylane default.qubit"})
    try:
        _train(qp)
    finally:
        end_run()


def _train(qp):
    per_class = qp["per_class"]
    rng = np.random.default_rng(SEED)
    train, test = split(load())
    x_all = train[FEATURE_COLUMNS].to_numpy(float)
    y_all = train[LABEL_COLUMN].to_numpy(int)

    # Preprocessing is fitted on the whole training split and shared by both models.
    scaler = StandardScaler().fit(x_all)
    pca = PCA(n_components=N_QUBITS, random_state=SEED).fit(scaler.transform(x_all))
    z_all = pca.transform(scaler.transform(x_all))
    angle = MinMaxScaler(feature_range=(0, np.pi), clip=True).fit(z_all)

    fraud = np.where(y_all == 1)[0]
    legit = np.where(y_all == 0)[0]
    idx = np.concatenate([rng.choice(fraud, min(per_class, len(fraud)), replace=False),
                          rng.choice(legit, per_class, replace=False)])

    def transform(x):
        return angle.transform(pca.transform(scaler.transform(x)))

    report = {}
    report["vqc_4qubit"] = _train_vqc(qp, rng, x_all, y_all, idx, transform, test,
                                      scaler, pca, angle)
    print("vqc_4qubit", report["vqc_4qubit"])
    report["qsvm"] = _train_qsvm(qp, x_all, y_all, idx, transform, test,
                                 scaler, pca, angle)
    print("qsvm", report["qsvm"])
    (OUT / "training_report.json").write_text(json.dumps(report, indent=2))
    log_metrics(report["vqc_4qubit"]["test_metrics"], prefix="vqc_4qubit_")
    log_metrics(report["qsvm"]["test_metrics"], prefix="qsvm_")
    # PennyLane has no MLflow flavor: log the bundles as generic artifacts.
    log_artifact(OUT / "vqc.joblib")
    log_artifact(OUT / "qsvm.joblib")
    log_artifact(OUT / "training_report.json")
    print(report)


def _train_vqc(qp, rng, x_all, y_all, idx, transform, test, scaler, pca, angle):
    steps, batch = qp["steps"], qp["batch"]
    x_train = transform(x_all[idx])
    y_train = y_all[idx].astype(float)

    weights = pnp.array(rng.normal(0, qp["init_std"], size=(N_LAYERS, N_QUBITS, 3)),
                        requires_grad=True)
    a = pnp.array(2.0, requires_grad=True)
    b = pnp.array(0.0, requires_grad=True)
    opt = qml.AdamOptimizer(stepsize=qp["stepsize"])

    def loss(w, a_, b_, xb, yb):
        p = pnp.clip(forward(xb, w, a_, b_), 1e-6, 1 - 1e-6)
        return -pnp.mean(yb * pnp.log(p) + (1 - yb) * pnp.log(1 - p))

    t0 = time.time()
    for step in range(steps):
        sel = rng.choice(len(x_train), batch, replace=False)
        xb = pnp.array(x_train[sel], requires_grad=False)
        yb = pnp.array(y_train[sel], requires_grad=False)
        (weights, a, b, _, _), cost = opt.step_and_cost(loss, weights, a, b, xb, yb)
        if step % 20 == 0:
            print(f"step {step:3d} loss {float(cost):.4f}")
    train_s = time.time() - t0

    t1 = time.time()
    x_test = transform(test[FEATURE_COLUMNS].to_numpy(float))
    proba = predict_proba(x_test, np.asarray(weights), float(a), float(b))
    infer_s = time.time() - t1
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "pca": pca, "angle": angle, "weights": np.asarray(weights),
                 "a": float(a), "b": float(b), "features": FEATURE_COLUMNS, "model_name": "vqc_4qubit"},
                OUT / "vqc.joblib", compress=3)
    return {"simulator": "pennylane default.qubit " + qml.__version__,
            "train_rows": int(len(idx)), "steps": steps, "train_seconds": round(train_s, 1),
            "test_rows": int(len(x_test)), "inference_seconds": round(infer_s, 1),
            "test_metrics": compute_metrics(test[LABEL_COLUMN], (proba >= 0.5).astype(int), proba)}


def _train_qsvm(qp, x_all, y_all, idx, transform, test, scaler, pca, angle):
    """Fidelity-kernel SVM on the same balanced subsample as the VQC.

    The kernel matrix is built from batched statevectors (one circuit execution
    per row), so scoring the full test split is a matrix product, not one
    circuit evaluation per (test, train) pair.
    """
    rng = np.random.default_rng(SEED)
    kernel_weights = rng.normal(0, qp["init_std"], size=(N_LAYERS, N_QUBITS, 3))
    x_train = transform(x_all[idx])
    y_train = y_all[idx].astype(int)

    t0 = time.time()
    train_states = kernel.feature_states(x_train, kernel_weights)
    k_train = kernel.fidelity_kernel(train_states, train_states)
    svc = SVC(kernel="precomputed", C=qp["qsvm"]["C"], probability=True, random_state=SEED)
    svc.fit(k_train, y_train)
    train_s = time.time() - t0

    t1 = time.time()
    x_test = transform(test[FEATURE_COLUMNS].to_numpy(float))
    states_test = kernel.feature_states(x_test, kernel_weights)
    k_test = kernel.fidelity_kernel(states_test, train_states)
    proba = svc.predict_proba(k_test)[:, 1]
    infer_s = time.time() - t1
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "pca": pca, "angle": angle,
                 "kernel_weights": kernel_weights, "train_states": train_states,
                 "svc": svc, "features": FEATURE_COLUMNS, "model_name": "qsvm"},
                OUT / "qsvm.joblib", compress=3)
    return {"simulator": "pennylane default.qubit " + qml.__version__,
            "train_rows": int(len(idx)), "train_seconds": round(train_s, 1),
            "test_rows": int(len(x_test)), "inference_seconds": round(infer_s, 1),
            "test_metrics": compute_metrics(test[LABEL_COLUMN], (proba >= 0.5).astype(int), proba)}


if __name__ == "__main__":
    main()

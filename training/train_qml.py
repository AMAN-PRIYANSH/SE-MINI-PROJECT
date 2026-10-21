"""Train the QML model served by the QML microservice (SRS REQ-FD-09, TBD-03).

    python training/train_qml.py

Quantum simulation is expensive, so the variational circuit is trained on a balanced
sample of the training split (all fraud rows up to 400, plus as many legitimate rows),
with Adam on binary cross-entropy. Evaluation uses the full 20 % test split.
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from services.qml.circuit import N_LAYERS, N_QUBITS, forward, predict_proba  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402
from training.prepare_data import SEED, load, split  # noqa: E402

OUT = ROOT / "services" / "qml" / "model"
PER_CLASS = 400
STEPS = 600
BATCH = 64


def main():
    rng = np.random.default_rng(SEED)
    train, test = split(load())
    x_all = train[FEATURE_COLUMNS].to_numpy(float)
    y_all = train[LABEL_COLUMN].to_numpy(int)

    # Preprocessing is fitted on the whole training split
    scaler = StandardScaler().fit(x_all)
    pca = PCA(n_components=N_QUBITS, random_state=SEED).fit(scaler.transform(x_all))
    z_all = pca.transform(scaler.transform(x_all))
    angle = MinMaxScaler(feature_range=(0, np.pi), clip=True).fit(z_all)

    fraud = np.where(y_all == 1)[0]
    legit = np.where(y_all == 0)[0]
    idx = np.concatenate([rng.choice(fraud, min(PER_CLASS, len(fraud)), replace=False),
                          rng.choice(legit, PER_CLASS, replace=False)])
    x_train = angle.transform(z_all[idx])
    y_train = y_all[idx].astype(float)

    weights = pnp.array(rng.normal(0, 0.3, size=(N_LAYERS, N_QUBITS, 3)), requires_grad=True)
    a = pnp.array(2.0, requires_grad=True)
    b = pnp.array(0.0, requires_grad=True)
    opt = qml.AdamOptimizer(stepsize=0.05)

    def loss(w, a_, b_, xb, yb):
        p = pnp.clip(forward(xb, w, a_, b_), 1e-6, 1 - 1e-6)
        return -pnp.mean(yb * pnp.log(p) + (1 - yb) * pnp.log(1 - p))

    t0 = time.time()
    for step in range(STEPS):
        batch = rng.choice(len(x_train), BATCH, replace=False)
        xb, yb = pnp.array(x_train[batch], requires_grad=False), pnp.array(y_train[batch], requires_grad=False)
        (weights, a, b, _, _), cost = opt.step_and_cost(loss, weights, a, b, xb, yb)
        if step % 20 == 0:
            print(f"step {step:3d} loss {float(cost):.4f}")
    train_s = time.time() - t0

    def transform(x):
        return angle.transform(pca.transform(scaler.transform(x)))

    t1 = time.time()
    x_test = transform(test[FEATURE_COLUMNS].to_numpy(float))
    proba = predict_proba(x_test, np.asarray(weights), float(a), float(b))
    infer_s = time.time() - t1
    report = {"vqc_4qubit": {
        "simulator": "pennylane default.qubit " + qml.__version__,
        "train_rows": int(len(idx)), "steps": STEPS, "train_seconds": round(train_s, 1),
        "test_rows": int(len(x_test)), "inference_seconds": round(infer_s, 1),
        "test_metrics": compute_metrics(test[LABEL_COLUMN], (proba >= 0.5).astype(int), proba)}}
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "pca": pca, "angle": angle, "weights": np.asarray(weights),
                 "a": float(a), "b": float(b), "features": FEATURE_COLUMNS, "model_name": "vqc_4qubit"},
                OUT / "vqc.joblib", compress=3)
    (OUT / "training_report.json").write_text(json.dumps(report, indent=2))
    print(report)


if __name__ == "__main__":
    main()

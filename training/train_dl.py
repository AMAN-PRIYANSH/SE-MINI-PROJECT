"""Train the DL baseline served by the DL microservice (SRS REQ-FD-08).

    python training/train_dl.py

A multilayer perceptron (two hidden layers, 64 and 32 ReLU units, Adam optimiser,
early stopping on a 10 % validation split) behind a StandardScaler, trained on the same
80 % split as the ML models. Saved to services/dl/model/mlp.joblib.
"""
import json
import sys
import time
from pathlib import Path

import joblib
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shared.metrics import compute_metrics  # noqa: E402
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402
from training.prepare_data import SEED, load, split  # noqa: E402

OUT = ROOT / "services" / "dl" / "model"


def main():
    train, test = split(load())
    model = make_pipeline(StandardScaler(), MLPClassifier(
        hidden_layer_sizes=(64, 32), activation="relu", solver="adam", alpha=1e-4,
        batch_size=512, learning_rate_init=1e-3, max_iter=60, early_stopping=True,
        validation_fraction=0.1, n_iter_no_change=6, random_state=SEED))
    t0 = time.time()
    model.fit(train[FEATURE_COLUMNS].to_numpy(float), train[LABEL_COLUMN].to_numpy(int))
    proba = model.predict_proba(test[FEATURE_COLUMNS].to_numpy(float))[:, 1]
    report = {"mlp": {"train_seconds": round(time.time() - t0, 1),
                      "epochs": int(model[-1].n_iter_),
                      "test_metrics": compute_metrics(test[LABEL_COLUMN], (proba >= 0.5).astype(int), proba)}}
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "model_name": "mlp"}, OUT / "mlp.joblib", compress=3)
    (OUT / "training_report.json").write_text(json.dumps(report, indent=2))
    print(report)


if __name__ == "__main__":
    main()

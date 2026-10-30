"""Train the ML baselines served by the ML microservice (SRS REQ-FD-07).

    python training/train_ml.py

Trains Logistic Regression and Random Forest on the 80 % training split of the public
Kaggle credit-card dataset (same split for every model, seed 404) and saves them to
services/ml/model/. A short report with test-split metrics is written next to them.
Model training is outside the product (SRS A4); the services only load these files.
"""
import json
import sys
import time
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shared.metrics import compute_metrics  # noqa: E402
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402
from training.mlflow_utils import end_run, log_artifact  # noqa: E402
from training.mlflow_utils import log_metrics, log_sklearn_model, start_run  # noqa: E402
from training.params import load_params  # noqa: E402
from training.prepare_data import SEED, load, split  # noqa: E402

OUT = ROOT / "services" / "ml" / "model"


def build_models(params):
    ml = params["ml"]
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=ml["logistic_regression"]["max_iter"])),
        "random_forest": RandomForestClassifier(
            n_estimators=ml["random_forest"]["n_estimators"],
            max_depth=ml["random_forest"]["max_depth"],
            min_samples_leaf=ml["random_forest"]["min_samples_leaf"],
            n_jobs=ml["random_forest"]["n_jobs"],
            random_state=SEED),
    }


def main():
    params = load_params()
    start_run("train-ml", {"seed": params["seed"], "ml": params["ml"]})
    try:
        train, test = split(load())
        x_train, y_train = train[FEATURE_COLUMNS].to_numpy(float), train[LABEL_COLUMN].to_numpy(int)
        x_test, y_test = test[FEATURE_COLUMNS].to_numpy(float), test[LABEL_COLUMN].to_numpy(int)
        OUT.mkdir(parents=True, exist_ok=True)
        report = {}
        for name, model in build_models(params).items():
            t0 = time.time()
            model.fit(x_train, y_train)
            proba = model.predict_proba(x_test)[:, 1]
            report[name] = {"train_seconds": round(time.time() - t0, 1),
                            "test_metrics": compute_metrics(y_test, (proba >= 0.5).astype(int), proba)}
            joblib.dump({"model": model, "features": FEATURE_COLUMNS, "model_name": name},
                        OUT / f"{name}.joblib", compress=3)
            log_metrics(report[name]["test_metrics"], prefix=f"{name}_")
            log_sklearn_model(model, artifact_path=f"model_{name}")
            print(name, report[name])
        (OUT / "training_report.json").write_text(json.dumps(report, indent=2))
        log_artifact(OUT / "training_report.json")
    finally:
        end_run()


if __name__ == "__main__":
    main()

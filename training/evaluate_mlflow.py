"""Compare the ML/DL/QML models on a dataset and log the comparison to MLflow.

    python training/evaluate_mlflow.py [--dataset data/samples/sample_transactions.csv]
                                       [--ml-model random_forest]

Loads the committed models exactly the way the microservices do (the same
predictor classes), scores every row of the dataset, prints a comparison
table and writes training/evaluation_report.json. The comparison is logged
as an MLflow run, so `mlflow ui` shows training runs and evaluations side
by side. This is the "run the different models and get the output" step.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from services.dl.server import DLPredictor  # noqa: E402
from services.ml.server import MLPredictor  # noqa: E402
from services.qml.server import QMLPredictor  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402
from training.mlflow_utils import end_run, log_metrics, start_run  # noqa: E402

REPORT = ROOT / "training" / "evaluation_report.json"


def main():
    ap = argparse.ArgumentParser(description="Compare ML/DL/QML models on a dataset.")
    ap.add_argument("--dataset", default=str(ROOT / "data" / "samples" / "sample_transactions.csv"),
                    help="Labelled CSV with the documented schema.")
    ap.add_argument("--ml-model", default="random_forest",
                    choices=["random_forest", "logistic_regression"],
                    help="Which ML baseline to evaluate.")
    args = ap.parse_args()

    df = pd.read_csv(args.dataset, usecols=FEATURE_COLUMNS + [LABEL_COLUMN],
                     encoding="utf-8-sig", dtype={c: np.float64 for c in FEATURE_COLUMNS})
    x = df[FEATURE_COLUMNS].to_numpy(dtype=np.float64)
    y = df[LABEL_COLUMN].astype(float).astype(int).to_numpy()

    start_run("evaluate", {"dataset": Path(args.dataset).name, "rows": len(df),
                           "ml_model": args.ml_model})
    try:
        report, table = {}, []
        for label, predictor in (("ml", MLPredictor(args.ml_model)),
                                 ("dl", DLPredictor()),
                                 ("qml", QMLPredictor())):
            predictor.load()
            classes, proba = predictor.predict(x)
            metrics = compute_metrics(y, classes, proba)
            report[predictor.model_name] = {"test_metrics": metrics}
            log_metrics(metrics, prefix=f"{predictor.model_name}_")
            m = metrics
            table.append((label, predictor.model_name, m["accuracy"], m["precision"],
                          m["recall"], m["f1"], m["roc_auc"]))
        REPORT.write_text(json.dumps(report, indent=2))
        print(f"{'model':<5} {'name':<16} {'acc':>7} {'prec':>7} {'rec':>7} {'f1':>7} {'auc':>7}")
        for label, name, acc, prec, rec, f1, auc in table:
            print(f"{label:<5} {name:<16} {acc:>7.4f} {prec:>7.4f} {rec:>7.4f} "
                  f"{f1:>7.4f} {str(auc):>7}")
        print(f"\nwrote {REPORT}")
    finally:
        end_run()


if __name__ == "__main__":
    main()

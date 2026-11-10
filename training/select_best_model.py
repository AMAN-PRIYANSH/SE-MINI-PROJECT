"""Pick the best of the six trained models and log the comparison to MLflow.

    python training/select_best_model.py

Reads the three training reports (services/*/model/training_report.json) — every
model was scored on the same 20 % test split (seed 404), so the numbers are
directly comparable — ranks all six by F1 (tiebreak: ROC-AUC, then accuracy) and
writes training/best_model.json, the file the Web Server surfaces as the headline
result. The comparison is logged as an MLflow run, so `mlflow ui` shows it next
to the training runs.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training.mlflow_utils import end_run, log_artifact, log_metrics, start_run  # noqa: E402
from training.params import load_params  # noqa: E402

REPORTS = {
    "ml": ROOT / "services" / "ml" / "model" / "training_report.json",
    "dl": ROOT / "services" / "dl" / "model" / "training_report.json",
    "qml": ROOT / "services" / "qml" / "model" / "training_report.json",
}
OUT = ROOT / "training" / "best_model.json"


def collect():
    """All six models with their test-split metrics, from the training reports."""
    models = []
    for category, path in REPORTS.items():
        report = json.loads(path.read_text())
        for name, entry in report.items():
            m = entry["test_metrics"]
            models.append({"category": category, "model": name,
                           "accuracy": m["accuracy"], "precision": m["precision"],
                           "recall": m["recall"], "f1": m["f1"], "roc_auc": m["roc_auc"]})
    return models


def rank(models):
    """Best first: F1, then ROC-AUC (a missing ROC-AUC sorts last), then accuracy."""
    return sorted(models,
                  key=lambda m: (m["f1"], m["roc_auc"] if m["roc_auc"] is not None else -1,
                                 m["accuracy"]),
                  reverse=True)


def main():
    metric = load_params().get("selection", {}).get("metric", "f1")
    assert metric == "f1", "only F1 selection is implemented (params.yaml selection.metric)"
    models = rank(collect())
    best = models[0]
    result = {"metric": metric, "best": best, "models": models}
    OUT.write_text(json.dumps(result, indent=2))

    start_run("select-best", {"metric": metric, "n_models": len(models),
                              "best_model": best["model"], "best_category": best["category"]})
    try:
        import mlflow

        mlflow.set_tag("best_model", best["model"])
        for m in models:
            log_metrics({"f1": m["f1"], "roc_auc": m["roc_auc"], "accuracy": m["accuracy"]},
                        prefix=f"{m['model']}_")
        log_artifact(OUT)
    finally:
        end_run()

    print(f"{'model':<20} {'cat':<4} {'acc':>7} {'prec':>7} {'rec':>7} {'f1':>7} {'auc':>7}")
    for m in models:
        mark = " <-- best" if m is best else ""
        print(f"{m['model']:<20} {m['category']:<4} {m['accuracy']:>7.4f} {m['precision']:>7.4f} "
              f"{m['recall']:>7.4f} {m['f1']:>7.4f} {str(m['roc_auc']):>7}{mark}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

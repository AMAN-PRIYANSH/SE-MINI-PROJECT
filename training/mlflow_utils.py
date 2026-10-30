"""MLflow tracking for the training scripts.

Every training run is logged to a local SQLite store (no server needed;
inspect it with `mlflow ui` from the repo root): hyperparameters as params,
test metrics as metrics, and the trained model files as artifacts.

The tracking code lives here so the training scripts keep a single
responsibility: building models. Usage in a training script::

    from training.mlflow_utils import end_run, log_metrics, start_run
    run = start_run("train-ml", {"seed": params["seed"], "ml": params["ml"]})
    try:
        ... train ...
        log_metrics(report["test_metrics"], prefix="random_forest_")
    finally:
        end_run()
"""
from pathlib import Path

import mlflow

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT = "ccfd-fraud-detection"
# Local SQLite tracking store (no server needed; inspect with `mlflow ui`).
# MLflow 3.x retired the plain file store, so SQLite is the supported default.
TRACKING_URI = f"sqlite:///{ROOT / 'mlruns.db'}"


def _flatten(prefix, obj, out):
    if isinstance(obj, dict):
        for key, value in obj.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), value, out)
    elif isinstance(obj, (list, tuple)):
        out[prefix] = ",".join(map(str, obj))
    else:
        out[prefix] = obj
    return out


def flatten_params(params):
    """Nested params.yaml section -> flat MLflow params."""
    return _flatten("", params, {})


def start_run(run_name, params):
    """Open an MLflow run and log hyperparameters. Returns the run."""
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    run = mlflow.start_run(run_name=run_name)
    mlflow.log_params(flatten_params(params))
    return run


def log_metrics(metrics, prefix=""):
    """Log a compute_metrics() dict; the confusion matrix becomes cm_tp etc."""
    flat = {}
    for key, value in metrics.items():
        if key == "confusion_matrix":
            for ck, cv in value.items():
                flat[f"{prefix}cm_{ck}"] = cv
        elif value is not None:
            flat[f"{prefix}{key}"] = value
    mlflow.log_metrics(flat)


def log_artifact(path):
    mlflow.log_artifact(str(path))


def log_sklearn_model(model, artifact_path):
    import mlflow.sklearn

    # `name` replaces the deprecated `artifact_path` in MLflow 3.x.
    # The trusted types are internals of models this script trained itself
    # seconds earlier (tree storage, Adam state), so loading them back is safe.
    mlflow.sklearn.log_model(
        model, name=artifact_path,
        skops_trusted_types=["sklearn.tree._tree.Tree",
                             "sklearn.neural_network._stochastic_optimizers.AdamOptimizer"])


def end_run():
    mlflow.end_run()

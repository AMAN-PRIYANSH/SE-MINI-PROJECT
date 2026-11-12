"""Train the DL models served by the DL microservice (SRS REQ-FD-08).

    python training/train_dl.py

Two deep-learning models on the same 80 % split as the ML models (seed 404):

    mlp  sklearn MLPClassifier (two hidden layers, 64 and 32 ReLU units, Adam,
         early stopping on a 10 % validation split) behind a StandardScaler.
    dnn  PyTorch feed-forward net (128+64 ReLU, dropout, Adam on BCEWithLogitsLoss
         with a positive-class weight, early stopping on a 10 % validation split).

Both are saved to services/dl/model/ (mlp.joblib, dnn.joblib) with one report
carrying the test-split metrics of each. The run is logged to MLflow.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from services.dl.dnn import FraudDNN  # noqa: E402
from shared.metrics import compute_metrics  # noqa: E402
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402
from training.mlflow_utils import end_run, log_artifact  # noqa: E402
from training.mlflow_utils import log_metrics, log_sklearn_model, start_run  # noqa: E402
from training.params import load_params  # noqa: E402
from training.prepare_data import SEED, load, split  # noqa: E402

OUT = ROOT / "services" / "dl" / "model"


def train_mlp(dl, x_train, y_train, x_test, y_test):
    model = make_pipeline(StandardScaler(), MLPClassifier(
        hidden_layer_sizes=tuple(dl["hidden_layer_sizes"]), activation=dl["activation"],
        solver=dl["solver"], alpha=dl["alpha"], batch_size=dl["batch_size"],
        learning_rate_init=dl["learning_rate_init"], max_iter=dl["max_iter"],
        early_stopping=dl["early_stopping"], validation_fraction=dl["validation_fraction"],
        n_iter_no_change=dl["n_iter_no_change"], random_state=SEED))
    t0 = time.time()
    model.fit(x_train, y_train)
    proba = model.predict_proba(x_test)[:, 1]
    entry = {"train_seconds": round(time.time() - t0, 1),
             "epochs": int(model[-1].n_iter_),
             "test_metrics": compute_metrics(y_test, (proba >= 0.5).astype(int), proba)}
    joblib.dump({"model": model, "features": FEATURE_COLUMNS, "model_name": "mlp"},
                OUT / "mlp.joblib", compress=3)
    return model, entry


def train_dnn(dnn_cfg, x_train, y_train, x_test, y_test):
    """PyTorch DNN with early stopping on a stratified 10 % validation split."""
    torch.manual_seed(SEED)
    x_tr, x_val, y_tr, y_val = train_test_split(
        x_train, y_train, test_size=0.1, stratify=y_train, random_state=SEED)
    scaler = StandardScaler().fit(x_tr)
    x_tr_s, x_val_s = scaler.transform(x_tr), scaler.transform(x_val)
    x_te_s = scaler.transform(x_test)
    n_pos = int((y_tr == 1).sum())
    pw = dnn_cfg["pos_weight"]
    if pw is None:  # auto: inverse class ratio (fraud is ~0.17 % of the data)
        pw = (len(y_tr) - n_pos) / max(n_pos, 1)
    pos_weight = torch.tensor(pw, dtype=torch.float32)
    model = FraudDNN(x_train.shape[1], tuple(dnn_cfg["hidden_sizes"]), dnn_cfg["dropout"])
    opt = torch.optim.Adam(model.parameters(), lr=dnn_cfg["learning_rate"],
                           weight_decay=dnn_cfg["weight_decay"])
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    batch = dnn_cfg["batch_size"]
    best_loss, best_state, wait, epochs = float("inf"), None, 0, 0
    t0 = time.time()
    for epoch in range(dnn_cfg["epochs"]):
        model.train()
        perm = torch.randperm(len(x_tr_s), generator=torch.Generator().manual_seed(SEED + epoch))
        for i in range(0, len(x_tr_s), batch):
            idx = perm[i:i + batch]
            xb = torch.as_tensor(x_tr_s[idx], dtype=torch.float32)
            yb = torch.as_tensor(y_tr[idx], dtype=torch.float32)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            val_loss = 0.0
            for i in range(0, len(x_val_s), batch):
                xb = torch.as_tensor(x_val_s[i:i + batch], dtype=torch.float32)
                yb = torch.as_tensor(y_val[i:i + batch], dtype=torch.float32)
                val_loss += float(loss_fn(model(xb), yb)) * len(xb)
            val_loss /= len(x_val_s)
        epochs = epoch + 1
        if val_loss < best_loss - 1e-4:
            best_loss, wait = val_loss, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= dnn_cfg["patience"]:
                break
    model.load_state_dict(best_state)
    model.eval()
    # Operating threshold: the 0.5 cut is wrong for a model trained with a large
    # positive-class weight (it ranks well but over-fires). Pick the threshold that
    # maximises F1 on the validation split and use it for the test metrics and
    # serving; the value is stored in the model bundle.
    with torch.no_grad():
        val_proba = torch.sigmoid(model(torch.as_tensor(x_val_s, dtype=torch.float32))).numpy()
        proba = torch.sigmoid(model(torch.as_tensor(x_te_s, dtype=torch.float32))).numpy()
    best_f1, threshold = -1.0, 0.5
    for t in np.linspace(0.05, 0.99, 95):
        f1 = f1_score(y_val, (val_proba >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1, threshold = f1, float(t)
    entry = {"train_seconds": round(time.time() - t0, 1), "epochs": epochs,
             "best_val_loss": round(best_loss, 4), "threshold": round(threshold, 4),
             "test_metrics": compute_metrics(y_test, (proba >= threshold).astype(int), proba)}
    joblib.dump({"state_dict": {k: v.numpy() for k, v in model.state_dict().items()},
                 "hidden_sizes": list(dnn_cfg["hidden_sizes"]), "dropout": dnn_cfg["dropout"],
                 "threshold": threshold,
                 "scaler": scaler, "features": FEATURE_COLUMNS, "model_name": "dnn"},
                OUT / "dnn.joblib", compress=3)
    return model, entry


def main():
    params = load_params()
    dl = params["dl"]
    start_run("train-dl", {"seed": params["seed"], "dl": dl})
    try:
        train, test = split(load())
        x_train = train[FEATURE_COLUMNS].to_numpy(float)
        y_train = train[LABEL_COLUMN].to_numpy(int)
        x_test = test[FEATURE_COLUMNS].to_numpy(float)
        y_test = test[LABEL_COLUMN].to_numpy(int)
        OUT.mkdir(parents=True, exist_ok=True)
        report = {}
        mlp, report["mlp"] = train_mlp(dl, x_train, y_train, x_test, y_test)
        print("mlp", report["mlp"])
        _, report["dnn"] = train_dnn(dl["dnn"], x_train, y_train, x_test, y_test)
        print("dnn", report["dnn"])
        (OUT / "training_report.json").write_text(json.dumps(report, indent=2))
        log_metrics(report["mlp"]["test_metrics"], prefix="mlp_")
        log_sklearn_model(mlp, artifact_path="model_mlp")
        log_metrics(report["dnn"]["test_metrics"], prefix="dnn_")
        log_artifact(OUT / "dnn.joblib")
        log_artifact(OUT / "mlp.joblib")
        log_artifact(OUT / "training_report.json")
        print(report)
    finally:
        end_run()


if __name__ == "__main__":
    main()

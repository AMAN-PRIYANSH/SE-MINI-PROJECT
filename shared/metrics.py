"""Model-performance metrics (SRS REQ-FD-15, REQ-FD-16; SADS 3.4 metrics.py).

Every value is rounded to four decimal places. ROC-AUC needs both classes in the
labels; when a dataset contains only one class it is undefined and reported as null.
"""
import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)


def compute_metrics(y_true, y_pred, y_proba):
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    roc = None
    if len(np.unique(y_true)) == 2:
        roc = round(float(roc_auc_score(y_true, y_proba)), 4)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": roc,
        "confusion_matrix": {"tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)},
    }

"""Independent metric computation for TC-MET-01 / TC-MET-05.

Deliberately written with plain Python loops and no scikit-learn or shared.metrics code,
so it is an independent reference for the system's metrics.

    python tests/fixtures/reference_metrics.py <labels.csv> <job.json>  -> prints reference JSON
"""
import csv
import json
import sys


def reference(labels, classes, probs):
    tp = sum(1 for y, c in zip(labels, classes) if y == 1 and c == 1)
    tn = sum(1 for y, c in zip(labels, classes) if y == 0 and c == 0)
    fp = sum(1 for y, c in zip(labels, classes) if y == 0 and c == 1)
    fn = sum(1 for y, c in zip(labels, classes) if y == 1 and c == 0)
    n = tp + tn + fp + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    pos = [p for p, y in zip(probs, labels) if y == 1]
    neg = [p for p, y in zip(probs, labels) if y == 0]
    if pos and neg:
        # ROC-AUC = probability that a random fraud row scores above a random legitimate row
        wins = sum(1.0 if a > b else 0.5 if a == b else 0.0 for a in pos for b in neg)
        auc = round(wins / (len(pos) * len(neg)), 4)
    else:
        auc = None
    return {"accuracy": round((tp + tn) / n, 4), "precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "roc_auc": auc, "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn}}


def labels_from_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [int(float(r["Class"])) for r in csv.DictReader(f)]


if __name__ == "__main__":
    job = json.load(open(sys.argv[2]))
    preds = job["predictions"]
    print(json.dumps(reference(labels_from_csv(sys.argv[1]), [p["class"] for p in preds],
                               [p["probability"] for p in preds]), indent=2))

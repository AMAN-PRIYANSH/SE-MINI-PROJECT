"""shared.metrics against hand-computed values (supports TC-MET-01, TC-MET-02, TC-MET-05)."""
from shared.metrics import compute_metrics


def test_hand_computed_example():
    # labels      1    1    0    0    0
    # predicted   1    0    1    0    0   -> tp=1 fn=1 fp=1 tn=2
    m = compute_metrics([1, 1, 0, 0, 0], [1, 0, 1, 0, 0], [0.9, 0.4, 0.6, 0.2, 0.1])
    assert m["confusion_matrix"] == {"tp": 1, "tn": 2, "fp": 1, "fn": 1}
    assert m["accuracy"] == 0.6            # 3 / 5
    assert m["precision"] == 0.5           # 1 / (1 + 1)
    assert m["recall"] == 0.5              # 1 / (1 + 1)
    assert m["f1"] == 0.5
    # ROC-AUC: positive scores {0.9, 0.4}, negative {0.6, 0.2, 0.1}: 5 of 6 pairs ranked right
    assert m["roc_auc"] == round(5 / 6, 4)


def test_single_class_has_null_roc_auc_and_no_division_error():
    m = compute_metrics([0, 0, 0], [0, 0, 0], [0.1, 0.2, 0.3])
    assert m["roc_auc"] is None
    assert m["precision"] == 0 and m["recall"] == 0 and m["accuracy"] == 1


def test_values_have_at_most_four_decimals():
    m = compute_metrics([1, 0, 0, 1, 0, 0, 0], [1, 0, 1, 0, 0, 0, 0], [0.8, 0.1, 0.7, 0.3, 0.2, 0.15, 0.05])
    for k in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert round(m[k], 4) == m[k]

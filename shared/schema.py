"""Documented dataset schema (SRS REQ-FD-02, REQ-FD-03; user manual section 3).

The trained models expect the 28 anonymised PCA features V1..V28 and the
transaction Amount, exactly as in the public Kaggle "Credit Card Fraud Detection"
dataset. The label column is Class (0 = legitimate, 1 = fraud). Any other column
(for example Time) is allowed and ignored.
"""

LABEL_COLUMN = "Class"
FEATURE_COLUMNS = [f"V{i}" for i in range(1, 29)] + ["Amount"]
REQUIRED_COLUMNS = FEATURE_COLUMNS + [LABEL_COLUMN]

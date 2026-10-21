"""Download the public Kaggle credit-card dataset and split it for training.

The dataset ("Credit Card Fraud Detection", ULB Machine Learning Group, 284,807
transactions, features anonymised with PCA) is not committed to the repository.
It is downloaded to training/raw/ (git-ignored).

It also writes tests/data/feature_stats.json: per-class means and covariances of the
features. The test-data generator samples synthetic rows from these statistics, so no
real (even anonymised) transaction is ever shipped with the system (SRS NFR-S03).
"""
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402

RAW = ROOT / "training" / "raw"
CSV = RAW / "creditcard.csv"
# Mirror of the Kaggle file (https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
MIRROR = ("https://raw.githubusercontent.com/nsethi31/"
          "Kaggle-Data-Credit-Card-Fraud-Detection/master/creditcard.csv")
SEED = 404


def load():
    if not CSV.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        print(f"Downloading dataset to {CSV} ...")
        urllib.request.urlretrieve(MIRROR, CSV)
    return pd.read_csv(CSV)


def split(df, test_size=0.2):
    """Stratified train/test split with a fixed seed (same split for every model)."""
    from sklearn.model_selection import train_test_split
    return train_test_split(df, test_size=test_size, stratify=df[LABEL_COLUMN], random_state=SEED)


def write_feature_stats(df):
    stats = {"features": FEATURE_COLUMNS, "classes": {}}
    for cls in (0, 1):
        x = df.loc[df[LABEL_COLUMN] == cls, FEATURE_COLUMNS].to_numpy(dtype=float)
        stats["classes"][str(cls)] = {
            "mean": np.round(x.mean(axis=0), 6).tolist(),
            "cov": np.round(np.cov(x, rowvar=False), 6).tolist(),
            "amount_min": float(x[:, -1].min()),
        }
    out = ROOT / "tests" / "data" / "feature_stats.json"
    out.write_text(json.dumps(stats))
    print(f"wrote {out}")


if __name__ == "__main__":
    data = load()
    print(data.shape, data[LABEL_COLUMN].value_counts().to_dict())
    write_feature_stats(data)

"""Generate the synthetic test datasets listed in STP Section 4 (Test data).

Rows are sampled from per-class multivariate normal distributions whose means and
covariances are stored in tests/data/feature_stats.json, so every value is synthetic
and no real cardholder data exists in any file (SRS NFR-S03, STP TC-SAFE-03).

usage:
    python tests/fixtures/make_datasets.py            # small fixtures -> tests/data/
    python tests/fixtures/make_datasets.py --perf     # also perf_10k, perf_100k
    python tests/fixtures/make_datasets.py --large-mb 400   # large_noclass.csv
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN  # noqa: E402

DATA = ROOT / "tests" / "data"
GENERATED = DATA / "generated"
STATS = json.loads((DATA / "feature_stats.json").read_text())
HEADER = ["Time"] + FEATURE_COLUMNS + [LABEL_COLUMN]


def sample(n, fraud_rate, seed):
    """Return (features, labels) for n synthetic rows."""
    rng = np.random.default_rng(seed)
    n_fraud = int(round(n * fraud_rate))
    labels = np.array([1] * n_fraud + [0] * (n - n_fraud))
    rng.shuffle(labels)
    x = np.zeros((n, len(FEATURE_COLUMNS)))
    for cls in (0, 1):
        idx = np.where(labels == cls)[0]
        if len(idx) == 0:
            continue
        st = STATS["classes"][str(cls)]
        x[idx] = rng.multivariate_normal(st["mean"], st["cov"], size=len(idx), method="eigh")
    x[:, -1] = np.abs(x[:, -1])  # Amount is never negative
    return np.round(x, 6), labels


def rows(n, fraud_rate, seed):
    x, y = sample(n, fraud_rate, seed)
    for i in range(n):
        yield [i] + [f"{v:.6f}" for v in x[i]] + [int(y[i])]


def write(path, header, body, delimiter=","):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delimiter, lineterminator="\n")
        w.writerow(header)
        for r in body:
            w.writerow(r)
    return path


def small():
    write(DATA / "valid_1000.csv", HEADER, rows(1000, 0.03, 1))
    write(DATA / "valid_51.csv", HEADER, rows(51, 0.1, 2))
    write(DATA / "tiny_4row.csv", HEADER, rows(4, 0.5, 3))
    no_class = [r[:-1] for r in rows(200, 0.03, 4)]
    write(DATA / "no_class_column.csv", HEADER[:-1], no_class)
    bad = list(rows(10, 0.2, 5))
    bad[2][-1], bad[5][-1], bad[8][-1] = 2, -1, ""
    write(DATA / "bad_labels.csv", HEADER, bad)
    write(DATA / "header_only.csv", HEADER, [])
    (DATA / "empty.csv").write_bytes(b"")
    write(DATA / "semicolon.csv", HEADER, rows(20, 0.1, 6), delimiter=";")
    nn = list(rows(20, 0.1, 7))
    nn[6][HEADER.index("V5")] = "abc"  # text in a required feature column, data row 7
    write(DATA / "non_numeric.csv", HEADER, nn)
    extra = [r + [f"SYN-REF-{900000 + r[0]:06d}", f"{(r[0] * 7) % 100 / 100:.2f}"]
             for r in rows(100, 0.05, 8)]
    write(DATA / "extra_cols.csv", HEADER + ["card_ref", "merchant_score"], extra)
    # A binary executable header (PE "MZ") plus random bytes, renamed to .csv
    rng = np.random.default_rng(9)
    (DATA / "evil.csv").write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00" + rng.bytes(4096))
    # Sample dataset for users (user manual, demo videos)
    write(ROOT / "data" / "samples" / "sample_transactions.csv", HEADER, rows(2000, 0.02, 10))
    print("small fixtures written to", DATA)


def perf():
    write(GENERATED / "perf_10k.csv", HEADER, rows(10_000, 0.02, 11))
    write(GENERATED / "perf_10k_noclass.csv", HEADER[:-1], (r[:-1] for r in rows(10_000, 0.02, 12)))
    write(GENERATED / "perf_100k.csv", HEADER, rows(100_000, 0.02, 13))
    print("perf fixtures written to", GENERATED)


def large_noclass(megabytes):
    """A big file without the Class column (STP: large_noclass.csv, about 400 MB)."""
    path = GENERATED / "large_noclass.csv"
    block = list(r[:-1] for r in rows(20_000, 0.02, 14))
    target = megabytes * 1024 * 1024
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER[:-1])
        while f.tell() < target:
            w.writerows(block)
    print(f"{path} ({os.path.getsize(path) / 1024 / 1024:.0f} MB)")
    return path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--perf", action="store_true")
    p.add_argument("--large-mb", type=int, default=0)
    a = p.parse_args()
    small()
    if a.perf:
        perf()
    if a.large_mb:
        large_noclass(a.large_mb)

"""Read a dataset from the shared store by its identifier (SADS 3.4: dataset_reader.py).

The microservices only ever read the store (IDatasetStore read-only, SADS 2.1).
The Web Server has already validated the file, so only the needed columns are loaded.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class DatasetNotFound(Exception):
    pass


def dataset_file(store_dir, dataset_id):
    if not isinstance(dataset_id, str) or not UUID_RE.match(dataset_id):
        raise DatasetNotFound(dataset_id)
    path = Path(store_dir) / "datasets" / f"{dataset_id}.csv"
    if not path.is_file():
        raise DatasetNotFound(dataset_id)
    return path


def read_dataset(store_dir, dataset_id):
    """Return (features as float matrix in FEATURE_COLUMNS order, labels as int vector)."""
    path = dataset_file(store_dir, dataset_id)
    df = pd.read_csv(path, usecols=FEATURE_COLUMNS + [LABEL_COLUMN], encoding="utf-8-sig",
                     dtype={c: np.float64 for c in FEATURE_COLUMNS})
    x = df[FEATURE_COLUMNS].to_numpy(dtype=np.float64)
    y = df[LABEL_COLUMN].astype(float).astype(int).to_numpy()
    return x, y

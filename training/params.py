"""Load hyperparameters from the repository-root params.yaml (DVC params).

The values are identical to the ones previously hard-coded in the training
scripts, so models trained through this helper are byte-for-byte the same
as the committed ones. Callers must keep the data split on
training.prepare_data.SEED; load_params() asserts the two seeds agree.
"""
from pathlib import Path

import yaml

from training.prepare_data import SEED

ROOT = Path(__file__).resolve().parent.parent


def load_params(path=None):
    path = Path(path) if path else ROOT / "params.yaml"
    with open(path, encoding="utf-8") as f:
        params = yaml.safe_load(f)
    if params.get("seed") != SEED:
        raise ValueError(
            f"params.yaml seed ({params.get('seed')}) != training/prepare_data.py "
            f"SEED ({SEED}): the train/test split would change."
        )
    return params

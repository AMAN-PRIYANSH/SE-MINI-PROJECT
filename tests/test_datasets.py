"""Checks on the synthetic test datasets (STP Section 4, TC-SAFE-03)."""
import re
from pathlib import Path

import pandas as pd

from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN

DATA = Path(__file__).parent / "data"
SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
CARD_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def test_valid_fixtures_follow_the_schema():
    for name, rows in (("valid_1000.csv", 1000), ("valid_51.csv", 51), ("tiny_4row.csv", 4)):
        df = pd.read_csv(DATA / name)
        assert len(df) == rows
        assert set(FEATURE_COLUMNS + [LABEL_COLUMN]) <= set(df.columns)
        assert set(df[LABEL_COLUMN].unique()) <= {0, 1}
        assert df[LABEL_COLUMN].nunique() == 2, "both classes needed for ROC-AUC"


def test_tc_safe_03_no_card_number_like_values_in_shipped_data():
    files = list(DATA.glob("*.csv")) + list(SAMPLES.glob("*.csv"))
    assert files
    for f in files:
        if f.name == "evil.csv":
            continue
        text = f.read_text(encoding="utf-8")
        # feature values are decimals with 6 places, so a 13-19 digit run would be suspicious
        assert not CARD_NUMBER.search(text.replace(".", " ")), f"card-number-like value in {f.name}"

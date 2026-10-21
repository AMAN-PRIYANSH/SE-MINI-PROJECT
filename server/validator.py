"""Input Validator (SADS 2.1, 3.4; SRS REQ-FD-02 - REQ-FD-04, SR-01, SR-02, BR-01).

File-level checks need only the file name, its size and its first bytes/header, so a
structurally wrong file of any size is rejected within seconds (NFR-07). Row-level
checks then read the required columns in chunks (NFR-01, NFR-03).

Messages name the reason, the column and the data-row number, but never echo a cell
value (SR-04).
"""
import codecs
import csv
import io

from server.errors import validation_error
from shared.schema import FEATURE_COLUMNS, LABEL_COLUMN, REQUIRED_COLUMNS

SNIFF_BYTES = 64 * 1024


def size_limit_text(max_bytes):
    """'500 MB' for the real limit; KB for the small limits used in tests."""
    mb = max_bytes / (1024 * 1024)
    return f"{mb:g} MB" if mb >= 1 else f"{max_bytes / 1024:g} KB"


def size_error(max_bytes):
    return validation_error(f"file exceeds the {size_limit_text(max_bytes)} limit")


# ---------------------------------------------------------------- file level (S1-08)
def check_file_level(stream, filename, size, max_bytes):
    """Validate type, size, encoding, delimiter and required columns. Returns the header."""
    if not filename or not filename.lower().endswith(".csv"):
        raise validation_error("unsupported file type: only .csv files are accepted")
    if size == 0:
        raise validation_error("the file is empty")
    if size > max_bytes:
        raise size_error(max_bytes)

    head = stream.read(SNIFF_BYTES)
    stream.seek(0)
    if b"\x00" in head:
        raise validation_error("unsupported file type: the file is not CSV text")
    try:
        text = codecs.getincrementaldecoder("utf-8-sig")().decode(head, final=False)
    except UnicodeDecodeError:
        raise validation_error("unsupported file type: the file must be UTF-8 encoded CSV text")

    first_line = text.splitlines()[0] if text.splitlines() else ""
    if not first_line.strip():
        raise validation_error("the file has no header row")
    if "," not in first_line and (";" in first_line or "\t" in first_line or "|" in first_line):
        raise validation_error("wrong delimiter: the file must be comma-delimited")

    header = [h.strip() for h in next(csv.reader(io.StringIO(first_line)))]
    seen = set()
    for name in header:
        if name in seen and name in REQUIRED_COLUMNS:
            raise validation_error(f"duplicate column: {name}")
        seen.add(name)
    if LABEL_COLUMN not in seen:
        raise validation_error(f"missing required column: {LABEL_COLUMN}")
    for col in FEATURE_COLUMNS:
        if col not in seen:
            raise validation_error(f"missing required column: {col}")
    return header


# ---------------------------------------------------------------- row level (S1-09)
CHUNK_ROWS = 100_000
VALID_LABELS = {"0", "1", "0.0", "1.0"}


def check_rows(path, max_rows):
    """Validate every data row and return the number of data rows.

    - at least one data row; at most max_rows (REQ-FD-02, REQ-FD-03)
    - Class is 0 or 1 in every row
    - every required feature value is a finite number
    Row numbers in messages count data rows from 1 (the header is not counted).
    """
    import numpy as np
    import pandas as pd

    rows = 0
    try:
        # All columns are read (not usecols) so that a row with extra fields is detected.
        reader = pd.read_csv(path, dtype=str, keep_default_na=False, index_col=False,
                             chunksize=CHUNK_ROWS, encoding="utf-8-sig", skip_blank_lines=True)
        for chunk in reader:
            first_row = rows + 1
            rows += len(chunk)
            if rows > max_rows:
                raise validation_error(f"file exceeds the {max_rows:,} row limit")

            labels = chunk[LABEL_COLUMN].str.strip()
            bad = ~labels.isin(VALID_LABELS)
            if bad.any():
                n = first_row + int(np.argmax(bad.to_numpy()))
                raise validation_error(
                    f"invalid value in column {LABEL_COLUMN} at row {n}: {LABEL_COLUMN} must be 0 or 1")

            for col in FEATURE_COLUMNS:
                values = pd.to_numeric(chunk[col].str.strip(), errors="coerce").to_numpy(dtype=float)
                bad = ~np.isfinite(values)
                if bad.any():
                    n = first_row + int(np.argmax(bad))
                    raise validation_error(f"non-numeric or missing value in column {col} at row {n}")
    except (pd.errors.ParserError, ValueError, UnicodeDecodeError):
        raise validation_error("malformed CSV: the rows do not match the header")

    if rows == 0:
        raise validation_error("the file has no data rows")
    return rows

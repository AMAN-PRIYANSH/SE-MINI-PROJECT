"""Dataset upload - file-level checks (S1-08) and row-level checks (S1-09).

Test-case IDs follow STP v1.1 Section 5.
"""
import io
import time

import pytest

from tests.conftest import DATA
from tests.helpers import assert_error_shape


def upload(client, name, headers=None, filename=None, data=None):
    payload = data if data is not None else (DATA / name).read_bytes()
    return client.post("/api/datasets", headers=headers or {},
                       data={"file": (io.BytesIO(payload), filename or name)},
                       content_type="multipart/form-data")


def stored(app):
    store = app.extensions["ccfd_store"]
    return sorted(p.name for p in store.datasets.iterdir()) + sorted(p.name for p in store.tmp.iterdir())


# ---------------- security cases ----------------
def test_tc_sec_01_upload_without_key_is_401_and_nothing_stored(app, client):
    assert_error_shape(upload(client, "valid_1000.csv"), 401, "E401_AUTH")
    assert stored(app) == []


def test_tc_sec_02_invalid_key_is_401(app, client):
    r = upload(client, "valid_1000.csv", headers={"Authorization": "Bearer invalid-key-123"})
    assert_error_shape(r, 401, "E401_AUTH")
    assert stored(app) == []


def test_tc_sec_05_executable_renamed_csv_rejected(app, client, auth):
    body = assert_error_shape(upload(client, "evil.csv", auth), 400, "E400_VALIDATION")
    assert "unsupported file type" in body["message"]
    assert stored(app) == []


def test_non_csv_extension_rejected(app, client, auth):
    body = assert_error_shape(upload(client, "valid_1000.csv", auth, filename="data.xlsx"), 400, "E400_VALIDATION")
    assert "unsupported file type" in body["message"]


def test_tc_sec_06_oversize_rejected_with_reason(app, client, auth, config):
    # Substitution recorded as allowed by STP TC-SEC-06: limit lowered to 0.1 MB
    config.max_upload_bytes = 100 * 1024
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    body = assert_error_shape(upload(client, "valid_1000.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "file exceeds the 100 KB limit"
    assert stored(app) == []


def test_body_larger_than_request_limit_is_400_not_413(app, client, auth):
    app.config["MAX_CONTENT_LENGTH"] = 1000
    body = assert_error_shape(upload(client, "valid_1000.csv", auth), 400, "E400_VALIDATION")
    assert "file exceeds the 500 MB limit" == body["message"]


# ---------------- functional cases ----------------
def test_tc_api_01_upload_contract(client, auth):
    r = upload(client, "valid_1000.csv", auth)
    assert r.status_code == 201
    assert r.mimetype == "application/json"
    body = r.get_json()
    assert set(body) == {"dataset_id", "rows"}
    assert body["dataset_id"] and body["rows"] == 1000


def test_tc_upl_01_valid_upload_twice_gives_two_ids_within_2s(client, auth):
    t0 = time.perf_counter()
    a = upload(client, "valid_1000.csv", auth)
    assert time.perf_counter() - t0 <= 2
    b = upload(client, "valid_1000.csv", auth)
    assert a.status_code == b.status_code == 201
    assert a.get_json()["dataset_id"] != b.get_json()["dataset_id"]


def test_tc_upl_02_missing_class_column(app, client, auth):
    body = assert_error_shape(upload(client, "no_class_column.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "missing required column: Class"
    assert stored(app) == []


def test_missing_feature_column_named(client, auth):
    text = (DATA / "valid_51.csv").read_text().replace("V17,", "X17,", 1)
    body = assert_error_shape(upload(client, "x.csv", auth, data=text.encode()), 400, "E400_VALIDATION")
    assert body["message"] == "missing required column: V17"


def test_tc_upl_05_empty_file_then_server_still_works(client, auth):
    body = assert_error_shape(upload(client, "empty.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "the file is empty"
    assert upload(client, "valid_1000.csv", auth).status_code == 201


def test_tc_upl_06_semicolon_delimiter(app, client, auth):
    body = assert_error_shape(upload(client, "semicolon.csv", auth), 400, "E400_VALIDATION")
    assert "delimiter" in body["message"]
    assert stored(app) == []


def test_no_file_part(client, auth):
    r = client.post("/api/datasets", headers=auth, data={}, content_type="multipart/form-data")
    assert_error_shape(r, 400, "E400_VALIDATION")


def test_two_files_rejected(client, auth):
    data = {"file": [(io.BytesIO(b"a"), "a.csv"), (io.BytesIO(b"b"), "b.csv")]}
    r = client.post("/api/datasets", headers=auth, data=data, content_type="multipart/form-data")
    body = assert_error_shape(r, 400, "E400_VALIDATION")
    assert "one file" in body["message"]


def test_tc_api_05_get_on_upload_endpoint_is_405(client, auth):
    assert_error_shape(client.get("/api/datasets", headers=auth), 405, "E405_METHOD")


def test_utf8_bom_header_accepted(client, auth):
    data = b"\xef\xbb\xbf" + (DATA / "valid_51.csv").read_bytes()
    r = upload(client, "bom.csv", auth, data=data)
    assert r.status_code == 201, r.get_json()


@pytest.mark.perf
def test_tc_perf_06_large_structurally_invalid_file_rejected_fast(client, auth, tmp_path):
    # CI-sized version of large_noclass.csv (40 MB); the full 400 MB run is in tests/perf
    header = (DATA / "no_class_column.csv").read_text().splitlines()[0]
    line = (DATA / "no_class_column.csv").read_text().splitlines()[1]
    payload = (header + "\n" + "\n".join([line] * 140_000) + "\n").encode()
    t0 = time.perf_counter()
    body = assert_error_shape(upload(client, "large_noclass.csv", auth, data=payload), 400, "E400_VALIDATION")
    assert body["message"] == "missing required column: Class"
    assert time.perf_counter() - t0 < 5


# ---------------- row-level cases (S1-09) ----------------
def test_tc_upl_03_non_binary_class_values(app, client, auth):
    body = assert_error_shape(upload(client, "bad_labels.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "invalid value in column Class at row 3: Class must be 0 or 1"
    assert stored(app) == []


def test_tc_upl_04_header_only(app, client, auth):
    body = assert_error_shape(upload(client, "header_only.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "the file has no data rows"
    assert stored(app) == []


def test_tc_upl_07_non_numeric_feature_names_column_not_value(app, client, auth):
    body = assert_error_shape(upload(client, "non_numeric.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "non-numeric or missing value in column V5 at row 7"
    assert "abc" not in body["message"]  # SR-04: never echo cell values
    assert stored(app) == []


def test_tc_upl_08_extra_columns_accepted(client, auth):
    r = upload(client, "extra_cols.csv", auth)
    assert r.status_code == 201 and r.get_json()["rows"] == 100


def test_row_limit(client, auth, config):
    config.max_rows = 50
    body = assert_error_shape(upload(client, "valid_51.csv", auth), 400, "E400_VALIDATION")
    assert body["message"] == "file exceeds the 50 row limit"


def test_ragged_rows_rejected(client, auth):
    text = (DATA / "valid_51.csv").read_text().splitlines()
    text[5] = text[5] + ",1,2,3"
    body = assert_error_shape(upload(client, "r.csv", auth, data="\n".join(text).encode()), 400, "E400_VALIDATION")
    assert body["message"] == "malformed CSV: the rows do not match the header"


def test_empty_feature_value_rejected(client, auth):
    text = (DATA / "valid_51.csv").read_text().splitlines()
    cells = text[2].split(",")
    cells[3] = ""
    text[2] = ",".join(cells)
    body = assert_error_shape(upload(client, "e.csv", auth, data="\n".join(text).encode()), 400, "E400_VALIDATION")
    assert body["message"] == "non-numeric or missing value in column V3 at row 2"


def test_infinite_value_rejected(client, auth):
    text = (DATA / "valid_51.csv").read_text().splitlines()
    cells = text[4].split(",")
    cells[29] = "inf"  # Amount
    text[4] = ",".join(cells)
    body = assert_error_shape(upload(client, "i.csv", auth, data="\n".join(text).encode()), 400, "E400_VALIDATION")
    assert body["message"] == "non-numeric or missing value in column Amount at row 4"


@pytest.mark.perf
def test_tc_perf_01_and_03_upload_timing(client, auth):
    """NFR-01 (10k rows <= 2 s) and NFR-03 (100k rows <= 60 s), measured in-process."""
    from tests.fixtures.make_datasets import GENERATED, perf
    if not (GENERATED / "perf_100k.csv").exists():
        perf()
    for name, limit, expect in (("perf_10k.csv", 2, 201), ("perf_10k_noclass.csv", 2, 400),
                                ("perf_100k.csv", 60, 201)):
        payload = (GENERATED / name).read_bytes()
        t0 = time.perf_counter()
        r = upload(client, name, auth, data=payload)
        assert r.status_code == expect
        assert time.perf_counter() - t0 <= limit, name

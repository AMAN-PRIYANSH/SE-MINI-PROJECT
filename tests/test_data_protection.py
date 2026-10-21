"""No transaction data in logs, messages or results (S2-06; TC-SEC-08, SR-04, SR-02)."""
import io
import logging

import pandas as pd

from tests.conftest import DATA
from tests.live import wait_for


def distinctive_values():
    df = pd.read_csv(DATA / "extra_cols.csv", dtype=str)
    values = set(df["card_ref"])
    for col in ("V1", "V14", "Amount"):
        values.update(df[col].head(20))
    return {v for v in values if len(v) >= 6}


def test_tc_sec_08_no_field_values_in_logs_or_results(client, auth, ml_service, caplog):
    caplog.set_level(logging.DEBUG)
    payload = (DATA / "extra_cols.csv").read_bytes()
    r = client.post("/api/datasets", headers=auth, data={"file": (io.BytesIO(payload), "extra_cols.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 201
    job = client.post("/api/analyses", headers=auth,
                      json={"dataset_id": r.get_json()["dataset_id"], "model_type": "ml"}).get_json()
    body = wait_for(lambda: (b := client.get(f"/api/analyses/{job['job_id']}", headers=auth).get_json())
                    and b["status"] == "completed" and b)

    # 1. logs (Web Server and microservice, which run in this process) hold no field value
    logged = caplog.text
    for value in distinctive_values():
        assert value not in logged, "a transaction value reached the logs"

    # 2. results carry only row index, predicted class and probability
    assert all(set(p) == {"row", "class", "probability"} for p in body["predictions"])
    text = str(body)
    assert "SYN-REF" not in text and "card_ref" not in text


def test_tc_sec_08_error_names_column_and_row_but_not_the_value(client, auth):
    payload = (DATA / "non_numeric.csv").read_bytes()
    r = client.post("/api/datasets", headers=auth, data={"file": (io.BytesIO(payload), "non_numeric.csv")},
                    content_type="multipart/form-data")
    message = r.get_json()["message"]
    assert "V5" in message and "row 7" in message and "abc" not in message


def test_bad_label_error_does_not_echo_value(client, auth):
    payload = (DATA / "bad_labels.csv").read_bytes()
    r = client.post("/api/datasets", headers=auth, data={"file": (io.BytesIO(payload), "bad_labels.csv")},
                    content_type="multipart/form-data")
    assert "2" not in r.get_json()["message"].replace("row 3", "")

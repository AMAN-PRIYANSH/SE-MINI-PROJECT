"""Retention period end to end (S2-07; TC-SEC-09)."""
import os
import stat
import sys
import time

import pytest

from server.app import create_app
from tests.live import wait_for


@pytest.fixture
def short_app(config):
    # Substitution recorded as allowed by STP TC-SEC-09: 24 h retention lowered to 2 s,
    # purge interval lowered from 10 minutes to 0.2 s
    config.retention_s = 2
    config.purge_interval_s = 0.2
    app = create_app(config, start_background=True)
    yield app
    app.extensions["ccfd_purge"].stop()


def test_tc_sec_09_dataset_job_and_result_deleted_after_retention(short_app, auth, ml_service):
    import io
    from tests.conftest import DATA
    client = short_app.test_client()
    store = short_app.extensions["ccfd_store"]
    r = client.post("/api/datasets", headers=auth,
                    data={"file": (io.BytesIO((DATA / "valid_51.csv").read_bytes()), "valid_51.csv")},
                    content_type="multipart/form-data")
    dataset_id = r.get_json()["dataset_id"]
    job_id = client.post("/api/analyses", headers=auth,
                         json={"dataset_id": dataset_id, "model_type": "ml"}).get_json()["job_id"]
    wait_for(lambda: client.get(f"/api/analyses/{job_id}", headers=auth).get_json().get("status") == "completed")
    assert (store.results / f"{job_id}.json").exists()

    if not sys.platform.startswith("win"):
        for d in (store.root, store.datasets, store.jobs, store.results):
            assert stat.S_IMODE(os.stat(d).st_mode) == 0o700
        for f in (store.datasets / f"{dataset_id}.csv", store.jobs / f"{job_id}.json",
                  store.results / f"{job_id}.json"):
            assert stat.S_IMODE(os.stat(f).st_mode) == 0o600

    time.sleep(2.2)
    wait_for(lambda: not any(store.datasets.iterdir()), timeout=5)
    assert list(store.jobs.iterdir()) == [] and list(store.results.iterdir()) == []
    assert client.get(f"/api/analyses/{job_id}", headers=auth).status_code == 404
    r = client.post("/api/analyses", headers=auth, json={"dataset_id": dataset_id, "model_type": "ml"})
    assert r.status_code == 404

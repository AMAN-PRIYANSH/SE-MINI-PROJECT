"""Dataset store: identifiers, sidecar, permissions and retention (S1-05, SR-05)."""
import os
import stat
import sys

import pytest

from server.store import DatasetStore, is_valid_id, new_id


@pytest.fixture
def store(tmp_path):
    return DatasetStore(tmp_path / "store", retention_s=3600).init()


def _upload(store, text="a,b\n1,2\n"):
    p = store.new_upload_path()
    p.write_text(text)
    return p


def test_register_dataset_creates_file_and_sidecar(store):
    meta = store.register_dataset(_upload(store), rows=1, now=1_000_000)
    assert is_valid_id(meta["dataset_id"])
    assert meta["rows"] == 1
    assert meta["uploaded_at"] == "1970-01-12T13:46:40Z"
    assert meta["expires_at"] == "1970-01-12T14:46:40Z"
    assert store.dataset_path(meta["dataset_id"]).exists()
    assert list(store.tmp.iterdir()) == []


def test_ids_are_random_uuid4():
    ids = {new_id() for _ in range(100)}
    assert len(ids) == 100 and all(is_valid_id(i) for i in ids)


def test_path_traversal_ids_are_rejected(store):
    assert store.dataset_meta("../../etc/passwd") is None
    assert store.load_job("..") is None
    with pytest.raises(ValueError):
        store.dataset_path("../x")


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permission bits")
def test_tc_sec_09_owner_only_permissions(store):
    meta = store.register_dataset(_upload(store), rows=1)
    store.save_job({"job_id": new_id(), "dataset_id": meta["dataset_id"]})
    for d in (store.root, store.datasets, store.jobs, store.results):
        assert stat.S_IMODE(os.stat(d).st_mode) == 0o700
    for f in list(store.datasets.iterdir()) + list(store.jobs.iterdir()):
        assert stat.S_IMODE(os.stat(f).st_mode) == 0o600


def test_retention_removes_dataset_jobs_and_results(store):
    meta = store.register_dataset(_upload(store), rows=1, now=0)
    job_id = new_id()
    store.save_job({"job_id": job_id, "dataset_id": meta["dataset_id"]})
    store.save_result(job_id, {"x": 1})
    assert store.load_job(job_id, now=10) is not None
    assert store.purge_expired(now=10) == []
    assert store.purge_expired(now=3601) == [meta["dataset_id"]]
    assert list(store.datasets.iterdir()) == []
    assert list(store.jobs.iterdir()) == []
    assert list(store.results.iterdir()) == []


def test_expired_dataset_is_invisible_before_purge(store):
    meta = store.register_dataset(_upload(store), rows=1, now=0)
    assert store.dataset_meta(meta["dataset_id"], now=3599) is not None
    assert store.dataset_meta(meta["dataset_id"], now=3600) is None

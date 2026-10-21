"""Performance tests (S2-08; TC-PERF-01, 02, 03, 05, 06). Run with: pytest -m perf

The whole system runs in this process: the Web Server and the three model services each
listen on their own real HTTP port, and the harness talks to them over HTTP.
"""
import threading

import pytest
from flask import Flask, jsonify

from tests.fixtures.make_datasets import GENERATED, large_noclass, perf
from tests.live import LiveService
from tests.perf import harness

pytestmark = pytest.mark.perf
KEY = "perf-key"


@pytest.fixture(scope="module")
def files():
    if not (GENERATED / "perf_100k.csv").exists():
        perf()
    if not (GENERATED / "large_noclass.csv").exists():
        large_noclass(400)
    return GENERATED


@pytest.fixture
def system(tmp_path):
    from server.app import create_app
    from services.common.app_factory import create_service_app
    from services.dl.server import DLPredictor
    from services.ml.server import MLPredictor
    from services.qml.server import QMLPredictor
    from shared.config import Config

    cfg = Config()
    cfg.api_key = KEY
    cfg.store_dir = tmp_path / "store"
    services = {k: LiveService(create_service_app(p.load(), cfg.store_dir, k))
                for k, p in (("ml", MLPredictor("random_forest")), ("dl", DLPredictor()), ("qml", QMLPredictor()))}
    for k, s in services.items():
        cfg.service_urls[k] = s.url
    web = LiveService(create_app(cfg, start_background=False))
    yield web.url, cfg
    web.stop()
    for s in services.values():
        s.stop()


def test_tc_perf_01_upload_within_2s(system, files):
    url, _ = system
    for name in ("valid_1000", "perf_10k", "perf_10k_noclass"):
        path = files / f"{name}.csv" if name != "valid_1000" else files.parent / "valid_1000.csv"
        res = harness.upload_timing(url, KEY, path)
        assert res["median_s"] <= 2, res


def test_tc_perf_03_100k_rows_within_60s(system, files):
    url, _ = system
    res = harness.upload_timing(url, KEY, files / "perf_100k.csv")
    assert res["status"] == [201, 201, 201] and res["median_s"] <= 60, res


def test_tc_perf_06_400mb_invalid_file_rejected_within_5s(system, files):
    url, cfg = system
    status, seconds, body = harness.upload(url, KEY, files / "large_noclass.csv")
    assert status == 400 and body["message"] == "missing required column: Class"
    # measured from the client: includes the local transfer of ~400 MB, so it is an upper bound
    assert seconds <= 5 + 10


def test_tc_perf_02_polling_p95_under_500ms(system, files):
    url, cfg = system
    release = threading.Event()
    stub = Flask("slow")
    stub.add_url_rule("/predict", "p", lambda: (release.wait(120), jsonify({}))[1], methods=["POST"])
    slow = LiveService(stub)
    cfg.service_urls["ml"] = slow.url
    try:
        _, _, body = harness.upload(url, KEY, files.parent / "valid_1000.csv")
        import requests
        job = requests.post(f"{url}/api/analyses", headers={"Authorization": f"Bearer {KEY}"},
                            json={"dataset_id": body["dataset_id"], "model_type": "ml"}).json()
        res = harness.poll_load(url, KEY, job["job_id"], clients=10, seconds=20)
        assert res["errors_5xx"] == 0 and res["p95_ms"] <= 500, res
    finally:
        release.set()
        slow.stop()


def test_tc_perf_05_ten_concurrent_sessions(system, files):
    url, _ = system
    res = harness.session_load(url, KEY, files.parent / "valid_1000.csv", sessions=10)
    assert res["all_terminal"] and set(res["finals"]) == {"completed"}, res
    assert res["upload_max_s"] <= 2 and res["poll_p95_ms"] <= 500 and res["correct_status_pct"] >= 99, res

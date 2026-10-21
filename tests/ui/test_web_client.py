"""Browser tests of the Web Client with Playwright/Chromium (S2-09). Run with: pytest -m ui

The Web Server and the model services run in this process on real HTTP ports and the
browser drives the real page, so these are system tests in the sense of STP Section 4.
"""
import csv
import io
import socket
import time

import pytest
from flask import Flask, jsonify, request

from tests.conftest import DATA
from tests.live import LiveService

pytest.importorskip("playwright")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

pytestmark = pytest.mark.ui
KEY = "ui-test-key"
NOTICE = "Analytical result only — not a financial authorization decision."


@pytest.fixture(scope="module")
def system(tmp_path_factory):
    from server.app import create_app
    from services.common.app_factory import create_service_app
    from services.dl.server import DLPredictor
    from services.ml.server import MLPredictor
    from services.qml.server import QMLPredictor
    from shared.config import Config

    cfg = Config()
    cfg.api_key = KEY
    cfg.store_dir = tmp_path_factory.mktemp("store")
    real = {k: create_service_app(p.load(), cfg.store_dir, k)
            for k, p in (("ml", MLPredictor("random_forest")), ("dl", DLPredictor()), ("qml", QMLPredictor()))}
    services = {k: LiveService(a) for k, a in real.items()}
    for k, s in services.items():
        cfg.service_urls[k] = s.url
    web = LiveService(create_app(cfg, start_background=False))
    yield {"url": web.url, "cfg": cfg, "services": services, "real": real}
    web.stop()
    for s in services.values():
        s.stop()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser, system):
    ctx = browser.new_context(viewport={"width": 1280, "height": 720}, accept_downloads=True)
    pg = ctx.new_page()
    pg.goto(system["url"] + "/")
    yield pg
    ctx.close()


def upload(pg, name):
    pg.fill("[data-testid=api-key]", KEY)
    pg.set_input_files("[data-testid=file-input]", str(DATA / name))
    with pg.expect_response(lambda r: r.url.endswith("/api/datasets")) as resp:
        pg.click("[data-testid=upload-btn]")
    return resp.value


def run(pg, model, timeout=60_000):
    pg.check(f"[data-testid=model-{model}]")
    with pg.expect_response(lambda r: r.url.endswith("/api/analyses") and r.request.method == "POST"):
        pg.click("[data-testid=run-btn]")
    pg.wait_for_function("document.querySelector('[data-testid=status-badge]').textContent === 'queued'")
    pg.wait_for_function(
        "['completed','failed'].includes(document.querySelector('[data-testid=status-badge]').textContent)",
        timeout=timeout)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ------------------------------------------------------------------ model selection
def test_tc_mod_01_run_blocked_without_model(page):
    upload(page, "valid_51.csv")
    sent = []
    page.on("request", lambda r: sent.append(r.url) if "/api/analyses" in r.url else None)
    page.click("[data-testid=run-btn]")
    expect(page.get_by_test_id("model-msg")).to_have_text("Select a model (ML, DL or QML) before running.")
    page.wait_for_timeout(500)
    assert sent == []


# ------------------------------------------------------------------ job lifecycle
def test_tc_job_02_and_tc_res_04_states_in_order_polling_2s_no_reload(page, system):
    """A slow wrapper around the real ML service keeps the job running for ~5 s."""
    real_ml = system["real"]["ml"].test_client()
    slow = Flask("slow-ml")

    @slow.post("/predict")
    def predict():
        time.sleep(5)
        r = real_ml.post("/predict", json=request.get_json())
        return jsonify(r.get_json()), r.status_code

    svc = LiveService(slow)
    system["cfg"].service_urls["ml"] = svc.url
    try:
        upload(page, "valid_1000.csv")
        page.evaluate("""() => { window.__states = [];
            new MutationObserver(() => {
              const t = document.querySelector('[data-testid=status-badge]').textContent;
              if (window.__states[window.__states.length - 1] !== t) window.__states.push(t);
            }).observe(document.querySelector('[data-testid=status-badge]'), {childList: true, subtree: true}); }""")
        nav = []
        page.on("framenavigated", lambda f: nav.append(f.url))
        run(page, "ml")
        states = page.evaluate("window.__states")
        assert states == ["queued", "running", "completed"], states
        polls = page.evaluate("window.__ccfdPolls")
        gaps = [(b - a) / 1000 for a, b in zip(polls, polls[1:])]
        assert gaps and all(1.5 <= g <= 2.5 for g in gaps), gaps
        n = len(polls)
        page.wait_for_timeout(4500)
        assert len(page.evaluate("window.__ccfdPolls")) == n, "polling continued after completion"
        assert nav == []  # no reload
        expect(page.get_by_test_id("predictions-table")).to_be_visible()  # appeared automatically
    finally:
        system["cfg"].service_urls["ml"] = system["services"]["ml"].url
        svc.stop()


def test_tc_job_05_failure_reason_shown_without_results(page, system):
    system["cfg"].service_urls["qml"] = f"http://127.0.0.1:{free_port()}"
    try:
        upload(page, "valid_51.csv")
        run(page, "qml")
        expect(page.get_by_test_id("status-badge")).to_have_text("failed")
        expect(page.get_by_test_id("failure-reason")).to_contain_text(
            "The model service is unavailable; the job was marked failed.")
        assert page.get_by_test_id("predictions-table").count() == 0
        assert page.get_by_test_id("metrics").count() == 0
        expect(page.get_by_test_id("analytical-notice")).to_have_text(NOTICE)
        run(page, "ml")  # a new run is possible and other services work
        expect(page.get_by_test_id("status-badge")).to_have_text("completed")
    finally:
        system["cfg"].service_urls["qml"] = system["services"]["qml"].url


# ------------------------------------------------------------------ results
def table_rows(pg):
    return pg.locator("[data-testid=predictions-table] tbody tr")


def test_tc_res_01_columns_and_20_pages(page):
    upload(page, "valid_1000.csv")
    run(page, "ml")
    headers = page.locator("[data-testid=predictions-table] thead th").all_text_contents()
    assert headers == ["Row index", "Predicted class", "Fraud probability"]
    assert table_rows(page).count() == 50
    expect(page.get_by_test_id("page-info")).to_contain_text("Page 1 of 20")


def test_tc_res_02_51_rows_give_50_plus_1(page):
    upload(page, "valid_51.csv")
    run(page, "ml")
    cells = "[data-testid=predictions-table] tbody tr td:first-child"
    first = [int(t) for t in page.locator(cells).all_text_contents()]
    assert first == list(range(50))
    page.click("[data-testid=page-next]")
    second = [int(t) for t in page.locator(cells).all_text_contents()]
    assert second == [50]
    expect(page.get_by_test_id("page-info")).to_contain_text("Page 2 of 2")
    expect(page.get_by_test_id("analytical-notice")).to_be_visible()  # TC-SAFE-01 on page 2


def test_tc_res_05_error_adjacent_within_1s(page):
    page.fill("[data-testid=api-key]", KEY)
    page.set_input_files("[data-testid=file-input]", str(DATA / "no_class_column.csv"))
    page.evaluate("""() => { window.__msgAt = null;
        new MutationObserver(() => { if (!window.__msgAt) window.__msgAt = Date.now(); })
          .observe(document.querySelector('[data-testid=upload-msg]'), {childList: true}); }""")
    with page.expect_response(lambda r: r.url.endswith("/api/datasets")) as resp:
        page.click("[data-testid=upload-btn]")
    received = page.evaluate("Date.now()")
    expect(page.get_by_test_id("upload-msg")).to_have_text("missing required column: Class")
    assert resp.value.status == 400
    assert page.evaluate("window.__msgAt") - received <= 1000
    # adjacent: the message is inside the upload region, right under the upload control
    assert page.locator("#upload-region [data-testid=upload-msg]").count() == 1
    box_btn = page.get_by_test_id("upload-btn").bounding_box()
    box_msg = page.get_by_test_id("upload-msg").bounding_box()
    assert 0 <= box_msg["y"] - box_btn["y"] <= 150


def test_tc_res_06_csv_download(page):
    upload(page, "valid_1000.csv")
    run(page, "ml")
    with page.expect_download() as d:
        page.click("[data-testid=download-btn]")
    rows = list(csv.reader(io.StringIO(open(d.value.path()).read())))
    assert rows[0] == ["row_index", "predicted_class", "fraud_probability"]
    assert len(rows) - 1 == 1000 and all(len(r) == 3 for r in rows)


def test_tc_res_07_single_page_single_file_help_and_viewport(page, system, browser):
    for tid in ("api-key", "file-input", "upload-btn", "model-ml", "model-dl", "model-qml", "run-btn",
                "results-region", "help-link"):
        expect(page.get_by_test_id(tid)).to_be_attached()
    assert page.get_by_test_id("file-input").get_attribute("multiple") is None
    with pytest.raises(Exception):
        page.set_input_files("[data-testid=file-input]", [str(DATA / "valid_51.csv"), str(DATA / "tiny_4row.csv")])
    expect(page.get_by_test_id("help-link")).to_be_visible()          # idle state
    upload(page, "valid_51.csv")
    run(page, "ml")
    expect(page.get_by_test_id("help-link")).to_be_visible()          # results state
    with page.expect_popup() as pop:
        page.click("[data-testid=help-link]")
    expect(pop.value.get_by_test_id("user-manual")).to_be_visible()
    # 1280x720: every control lies within the page width and is reachable by scrolling
    width = page.evaluate("document.documentElement.clientWidth")
    for tid in ("api-key", "upload-btn", "model-qml", "run-btn", "download-btn", "page-next"):
        page.get_by_test_id(tid).scroll_into_view_if_needed()
        box = page.get_by_test_id(tid).bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= width
    assert page.evaluate("document.documentElement.scrollWidth") <= width  # no horizontal scroll


@pytest.mark.parametrize("model,name", [("ml", "random_forest"), ("dl", "mlp"), ("qml", "vqc_4qubit")])
def test_tc_met_03_metrics_displayed_and_labelled(page, model, name):
    upload(page, "valid_1000.csv")
    with page.expect_response(lambda r: "/api/analyses/" in r.url and r.json().get("status") == "completed",
                              timeout=60_000) as resp:
        run(page, model)
    payload = resp.value.json()
    expect(page.get_by_test_id("model-name")).to_have_text(name)
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert page.get_by_test_id(f"metric-{key}").text_content() == f"{payload['metrics'][key]:.4f}"
    for key in ("tp", "tn", "fp", "fn"):
        assert page.get_by_test_id(f"cm-{key}").locator("strong").text_content() == \
            str(payload["metrics"]["confusion_matrix"][key])
    expect(page.get_by_test_id("analytical-notice")).to_have_text(NOTICE)   # TC-SAFE-01


def test_tc_perf_04_results_render_within_3s(page):
    upload(page, "valid_1000.csv")
    for _ in range(3):
        run(page, "ml")
    times = page.evaluate("window.__ccfdRenderMs")
    assert len(times) == 3 and sorted(times)[1] <= 3000, times


def test_sr_03_key_never_stored_in_browser(page):
    upload(page, "valid_51.csv")
    stored = page.evaluate("JSON.stringify(localStorage) + JSON.stringify(sessionStorage) + document.cookie")
    assert KEY not in stored
    page.reload()
    assert page.get_by_test_id("api-key").input_value() == ""


def test_keyless_upload_blocked_in_ui(page):
    page.set_input_files("[data-testid=file-input]", str(DATA / "valid_51.csv"))
    page.click("[data-testid=upload-btn]")
    expect(page.get_by_test_id("api-key-msg")).to_have_text("Enter the API key first.")

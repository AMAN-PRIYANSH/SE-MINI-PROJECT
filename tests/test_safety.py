"""Safety requirements (S1-17; TC-SAFE-01 static part, TC-SAFE-02)."""

NOTICE = "Analytical result only — not a financial authorization decision."


def test_tc_safe_01_notice_is_part_of_the_results_region(client):
    html = client.get("/").get_data(as_text=True)
    region = html[html.index('id="results-region"'):html.index("</section>", html.index('id="results-region"'))]
    assert "Analytical result only &mdash; not a financial authorization decision." in region


def test_tc_safe_02_no_transaction_initiating_endpoint(app):
    api_routes = sorted((r.rule, tuple(sorted(r.methods - {"HEAD", "OPTIONS"})))
                        for r in app.url_map.iter_rules() if r.rule.startswith("/api/"))
    assert api_routes == [
        ("/api/analyses", ("POST",)),
        ("/api/analyses/<job_id>", ("GET",)),
        ("/api/datasets", ("POST",)),
    ]
    words = ("authori", "transfer", "payment", "block", "charge", "refund")
    for rule in app.url_map.iter_rules():
        assert not any(w in rule.rule.lower() for w in words)


def test_tc_safe_02_no_transaction_controls_in_ui(client):
    html = client.get("/").get_data(as_text=True).lower()
    for word in ("approve", "decline transaction", "block card", "authorize payment", "refund"):
        assert word not in html

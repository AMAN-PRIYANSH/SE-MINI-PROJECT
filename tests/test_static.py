"""Static Web Client assets (S2-05; TC-RES-07 server-side part, REQ-UI-04, REQ-UI-06)."""


def test_help_link_present_and_manual_served(client):
    html = client.get("/").get_data(as_text=True)
    assert 'data-testid="help-link"' in html and 'href="/static/help.html"' in html
    manual = client.get("/static/help.html")
    assert manual.status_code == 200 and "User manual" in manual.get_data(as_text=True)


def test_single_shared_stylesheet(client):
    for page in ("/", "/static/help.html"):
        html = client.get(page).get_data(as_text=True)
        assert html.count('rel="stylesheet"') == 1 and "/static/style.css" in html
        assert "<style" not in html


def test_single_file_upload_control(client):
    html = client.get("/").get_data(as_text=True)
    tag = html[html.index('id="file-input"') - 20:html.index('data-testid="file-input"')]
    assert "multiple" not in tag


def test_static_path_traversal_blocked(client):
    assert client.get("/static/../server/app.py").status_code == 404


def test_user_manual_documents_schema_and_messages(client):
    html = client.get("/static/help.html").get_data(as_text=True)
    for text in ("V1", "V28", "Amount", "Class", "500 MB", "1,000,000", "24 hours",
                 "missing required column", "wrong delimiter", "non-numeric or missing value",
                 "The analysis timed out", "The model service is unavailable"):
        assert text in html, text

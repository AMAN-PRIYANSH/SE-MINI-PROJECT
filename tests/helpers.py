"""Shared helpers for the API tests."""
FORBIDDEN_IN_ERRORS = ("Traceback", "File \"", ".py", "/home/", "\\Users\\", "CCFD_", "api_key")


def assert_error_shape(resp, status, code):
    assert resp.status_code == status, resp.get_data(as_text=True)
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    assert set(body) == {"code", "message"}
    assert body["code"] == code
    assert body["message"]
    text = resp.get_data(as_text=True)
    for s in FORBIDDEN_IN_ERRORS:
        assert s not in text
    return body

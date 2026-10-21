"""API-key authentication (S1-07; SR-03). Endpoint-level cases are in the endpoint tests."""
import pytest
from flask import jsonify

from tests.conftest import TEST_KEY
from tests.helpers import assert_error_shape


@pytest.fixture
def probe_client(app):
    from server.routes import api

    @app.get("/api/_probe")
    def probe():
        return jsonify(ok=True)

    # the probe route is registered outside the blueprint, so apply the same filter
    app.before_request_funcs.setdefault(None, []).append(api.before_request_funcs[None][0])
    return app.test_client()


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer ", "Basic abc", f"Token {TEST_KEY}",
                                    "Bearer invalid-key-123", f"Bearer {TEST_KEY}x"])
def test_missing_or_invalid_key_gives_401(probe_client, header):
    headers = {"Authorization": header} if header is not None else {}
    assert_error_shape(probe_client.get("/api/_probe", headers=headers), 401, "E401_AUTH")


def test_valid_key_passes(probe_client, auth):
    assert probe_client.get("/api/_probe", headers=auth).get_json() == {"ok": True}


def test_empty_configured_key_rejects_everything(app, config):
    config.api_key = ""
    from server.auth import require_api_key
    with app.test_request_context("/api/x", headers={"Authorization": "Bearer "}):
        with pytest.raises(Exception):
            require_api_key()

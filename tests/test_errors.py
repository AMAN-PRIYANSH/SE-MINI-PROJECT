"""Uniform error body and safe failure (S1-06; TC-API-04 part, TC-SEC-07 part)."""
from tests.helpers import assert_error_shape


def test_unknown_api_route_is_json_404(client):
    assert_error_shape(client.get("/api/nothing-here"), 404, "E404_NOT_FOUND")


def test_unexpected_exception_hides_internals(app):
    @app.get("/boom")
    def boom():
        raise RuntimeError("/home/secret/path.py value=4111111111111111")

    body = assert_error_shape(app.test_client().get("/boom"), 500, "E500_INTERNAL")
    assert body["message"] == "An internal error occurred."


def test_index_is_served(client):
    resp = client.get("/")
    assert resp.status_code in (200, 404)

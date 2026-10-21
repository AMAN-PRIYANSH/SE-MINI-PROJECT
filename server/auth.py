"""API-Key Auth Filter (SADS 2.4 item 1; SRS SR-03).

Runs before every REST route. The key must be sent as "Authorization: Bearer <key>"
and is compared with the configured key in constant time. A missing or wrong key
ends the request with HTTP 401 before any processing happens.
"""
import hmac

from flask import current_app, request

from server.errors import ApiError


def presented_key():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def require_api_key():
    expected = current_app.config["CCFD"].api_key
    key = presented_key()
    if not expected or key is None or not hmac.compare_digest(key.encode(), expected.encode()):
        raise ApiError(401, "E401_AUTH")

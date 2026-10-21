"""Error taxonomy and global error handler (SADS 3.3; SRS REQ-API-04, SR-06).

Every error leaves the server as {"code": ..., "message": ...} with a JSON content type.
Messages are fixed, safe texts: never a stack trace, file path, configuration value or
cell value from a dataset. Details of unexpected errors are logged server-side only.
"""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

log = logging.getLogger("ccfd.server")

MESSAGES = {
    "E401_AUTH": "Authentication required: provide a valid API key.",
    "E404_NOT_FOUND": "The requested dataset/job was not found.",
    "E405_METHOD": "Method not allowed for this endpoint.",
    "E500_INTERNAL": "An internal error occurred.",
}


class ApiError(Exception):
    def __init__(self, status, code, message=None):
        super().__init__(message or MESSAGES.get(code, code))
        self.status = status
        self.code = code
        self.message = message or MESSAGES.get(code, code)


def validation_error(message):
    return ApiError(400, "E400_VALIDATION", message)


def error_response(status, code, message=None):
    resp = jsonify({"code": code, "message": message or MESSAGES.get(code, code)})
    resp.status_code = status
    return resp


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e):
        return error_response(e.status, e.code, e.message)

    @app.errorhandler(RequestEntityTooLarge)
    def _too_large(e):
        limit = app.config["CCFD"].max_upload_mb
        return error_response(400, "E400_VALIDATION", f"file exceeds the {limit:g} MB limit")

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if e.code == 404:
            return error_response(404, "E404_NOT_FOUND")
        if e.code == 405:
            return error_response(405, "E405_METHOD")
        if e.code == 400:
            return error_response(400, "E400_VALIDATION", "invalid request")
        if e.code and e.code < 500:
            return error_response(e.code, f"E{e.code}", e.name)
        log.error("HTTP %s on request", e.code)
        return error_response(500, "E500_INTERNAL")

    @app.errorhandler(Exception)
    def _unexpected(e):
        # Logged with the exception type only: the message could contain data values (SR-04)
        log.error("unexpected %s while handling the request", type(e).__name__)
        return error_response(500, "E500_INTERNAL")

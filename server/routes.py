"""REST routes (SADS 3.4: routes.py). Endpoints are added by the backlog items that own them."""
from flask import Blueprint

from server.auth import require_api_key

api = Blueprint("api", __name__, url_prefix="/api")
api.before_request(require_api_key)  # SR-03: every REST endpoint needs the API key


def register(app):
    app.register_blueprint(api)

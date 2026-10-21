"""REST routes (SADS 3.4: routes.py). Endpoints are added by the backlog items that own them."""
from flask import Blueprint

api = Blueprint("api", __name__, url_prefix="/api")


def register(app):
    app.register_blueprint(api)

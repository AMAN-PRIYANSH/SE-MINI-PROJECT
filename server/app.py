"""Flask application factory (SADS 3.4: app.py).

Loads the configuration, prepares the dataset store, registers the REST routes and the
global error handler, and serves the Web Client's static files.
"""
import logging
import sys
import time
from pathlib import Path

from flask import Flask, g, request, send_from_directory

from server.errors import register_error_handlers
from server.jobs import JobManager
from server.store import DatasetStore
from shared.config import Config

CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"
log = logging.getLogger("ccfd.server")


def create_app(config=None, start_background=True):
    config = config or Config.from_env()
    app = Flask(__name__, static_folder=None)
    app.config["CCFD"] = config
    # A little headroom for the multipart envelope; the file itself is checked in the validator.
    app.config["MAX_CONTENT_LENGTH"] = config.max_upload_bytes + 1024 * 1024
    app.json.sort_keys = False

    store = DatasetStore(config.store_dir, retention_s=config.retention_s).init()
    app.extensions["ccfd_store"] = store
    app.extensions["ccfd_jobs"] = JobManager(store, config)
    app.extensions["ccfd_jobs"].recover()

    register_error_handlers(app)
    _register_request_log(app)

    from server import routes
    routes.register(app)

    @app.get("/")
    def index():
        return send_from_directory(CLIENT_DIR, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(CLIENT_DIR, name)

    return app


def _register_request_log(app):
    """Log request metadata only: method, path, status, duration (SR-04: never payloads)."""

    @app.before_request
    def _start():
        g.t0 = time.perf_counter()

    @app.after_request
    def _log(resp):
        if request.path.startswith("/api/"):
            ms = (time.perf_counter() - g.get("t0", time.perf_counter())) * 1000
            log.info("%s %s -> %s (%.1f ms)", request.method, request.path, resp.status_code, ms)
        return resp


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    config = Config.from_env()
    if not config.api_key:
        print("CCFD_API_KEY is not set. Set it (or start through run_all.py) and try again.")
        sys.exit(2)
    app = create_app(config)
    app.run(host=config.host, port=config.port, threaded=True)


if __name__ == "__main__":
    main()

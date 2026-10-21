"""REST routes (SADS 3.4: routes.py). Endpoints are added by the backlog items that own them."""
import logging
import shutil

from flask import Blueprint, current_app, jsonify, request

from server.auth import require_api_key
from server.errors import validation_error
from server.validator import check_file_level, check_rows

log = logging.getLogger("ccfd.server")

api = Blueprint("api", __name__, url_prefix="/api")
api.before_request(require_api_key)  # SR-03: every REST endpoint needs the API key


def _store():
    return current_app.extensions["ccfd_store"]


def _cfg():
    return current_app.config["CCFD"]


@api.post("/datasets")
def upload_dataset():
    """POST /api/datasets - multipart upload with one part named "file" (REQ-API-01)."""
    files = request.files.getlist("file")
    if not files:
        raise validation_error("no file part named 'file' in the upload")
    if len(files) > 1:
        raise validation_error("only one file can be uploaded per request")
    upload = files[0]

    stream = upload.stream
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    # File-level checks run on the received upload before anything is stored (SR-01, NFR-07)
    check_file_level(stream, upload.filename, size, _cfg().max_upload_bytes)

    store = _store()
    tmp_path = store.new_upload_path()
    try:
        with open(tmp_path, "wb") as out:
            shutil.copyfileobj(stream, out, length=1024 * 1024)
        rows = check_rows(tmp_path, _cfg().max_rows)
        meta = store.register_dataset(tmp_path, rows)
    except Exception:
        store.discard(tmp_path)  # a rejected file is never stored
        raise
    log.info("dataset accepted dataset_id=%s rows=%d", meta["dataset_id"], meta["rows"])
    return jsonify({"dataset_id": meta["dataset_id"], "rows": meta["rows"]}), 201


def register(app):
    app.register_blueprint(api)

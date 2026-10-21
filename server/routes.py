"""REST routes (SADS 3.4: routes.py). Endpoints are added by the backlog items that own them."""
import json
import logging
import shutil

from flask import Blueprint, current_app, jsonify, request

from server.auth import require_api_key
from server.errors import ApiError, validation_error
from server.jobs import MODEL_TYPES
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


def _strict_json(required):
    """Parse the body as a JSON object with exactly the required fields (SR-02).

    The payload is never logged or echoed back.
    """
    try:
        body = json.loads(request.get_data(cache=False, as_text=True) or "")
    except (ValueError, UnicodeDecodeError):
        raise validation_error("malformed JSON body")
    if not isinstance(body, dict):
        raise validation_error("the JSON body must be an object")
    for name in required:
        if name not in body:
            raise validation_error(f"missing field: {name}")
    for name in body:
        if name not in required:
            raise validation_error(f"unknown field: {name}")
    return body


@api.post("/analyses")
def start_analysis():
    """POST /api/analyses {dataset_id, model_type} -> 202 {job_id, status: "queued"} (REQ-API-02)."""
    body = _strict_json(("dataset_id", "model_type"))
    if not isinstance(body["dataset_id"], str) or not body["dataset_id"]:
        raise validation_error("dataset_id must be a non-empty string")
    if body["model_type"] not in MODEL_TYPES:
        raise validation_error("invalid model_type: must be one of ml, dl, qml")
    if _store().dataset_meta(body["dataset_id"]) is None:
        raise ApiError(404, "E404_NOT_FOUND")  # unknown or expired dataset: no job is created
    job = current_app.extensions["ccfd_jobs"].create(body["dataset_id"], body["model_type"])
    return jsonify({"job_id": job["job_id"], "status": "queued"}), 202


def register(app):
    app.register_blueprint(api)

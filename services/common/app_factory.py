"""HTTP layer shared by every model microservice (SADS 3.2 IPredict; SRS Section 3.3).

    POST /predict  {"dataset_id": "<id>"} -> 200 {model_name, predictions, metrics}
                   400 E400_VALIDATION (bad body), 404 E404_NOT_FOUND (unknown dataset),
                   500 E500_MODEL (model failure)
    GET  /health   -> 200 {"status": "ok"} or 503 {"status": "not_ready"}

The service binds to 127.0.0.1 only (SADS 2.4 item 6), so it needs no API key.
"""
import logging
import time

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from services.common.dataset_reader import DatasetNotFound, read_dataset
from shared.metrics import compute_metrics


def _error(status, code, message):
    resp = jsonify({"code": code, "message": message})
    resp.status_code = status
    return resp


def create_service_app(predictor, store_dir, name):
    log = logging.getLogger(f"ccfd.{name}")
    app = Flask(name)
    app.json.sort_keys = False
    app.config["ACCESS_LOG"] = []  # (method, path, dataset_id) of every request - used by tests

    @app.before_request
    def _access():
        body = request.get_json(silent=True) if request.method == "POST" else None
        dataset_id = body.get("dataset_id") if isinstance(body, dict) else None
        app.config["ACCESS_LOG"].append((request.method, request.path, dataset_id))

    @app.get("/health")
    def health():
        if predictor.ready:
            return jsonify({"status": "ok"})
        return jsonify({"status": "not_ready"}), 503

    @app.post("/predict")
    def predict():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"dataset_id"} or not isinstance(body["dataset_id"], str):
            return _error(400, "E400_VALIDATION", 'request body must be {"dataset_id": "<id>"}')
        dataset_id = body["dataset_id"]
        if not predictor.ready:
            return _error(500, "E500_MODEL", "The model failed to process the dataset.")
        t0 = time.perf_counter()
        try:
            x, y = read_dataset(store_dir, dataset_id)
        except DatasetNotFound:
            return _error(404, "E404_NOT_FOUND", "The requested dataset/job was not found.")
        try:
            classes, proba = predictor.predict(x)
            metrics = compute_metrics(y, classes, proba)
        except Exception as e:  # never return partial or fabricated results
            log.error("model failure %s on dataset_id=%s", type(e).__name__, dataset_id)
            return _error(500, "E500_MODEL", "The model failed to process the dataset.")
        predictions = [{"row": i, "class": int(c), "probability": float(p)}
                       for i, (c, p) in enumerate(zip(classes, proba))]
        log.info("predicted dataset_id=%s rows=%d in %.2f s", dataset_id, len(predictions),
                 time.perf_counter() - t0)
        return jsonify({"model_name": predictor.model_name, "predictions": predictions, "metrics": metrics})

    @app.errorhandler(HTTPException)
    def _http(e):
        if e.code == 405:
            return _error(405, "E405_METHOD", "Method not allowed for this endpoint.")
        if e.code == 404:
            return _error(404, "E404_NOT_FOUND", "Not found.")
        return _error(e.code or 500, f"E{e.code}", e.name)

    @app.errorhandler(Exception)
    def _unexpected(e):
        log.error("unexpected %s", type(e).__name__)
        return _error(500, "E500_MODEL", "The model failed to process the dataset.")

    return app


def run_service(predictor, name, default_port, port_env):
    """Load the model, then serve on the loopback interface only."""
    import os

    from shared.config import store_dir_from_env

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    predictor.load()
    app = create_service_app(predictor, store_dir_from_env(), name)
    port = int(os.environ.get(port_env, default_port))
    app.run(host="127.0.0.1", port=port, threaded=True)

"""Run model microservices in background threads for integration tests."""
import threading
import time

from werkzeug.serving import make_server


class LiveService:
    def __init__(self, app):
        self.app = app
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.port = self.server.server_port
        self.url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def access_log(self):
        return self.app.config.get("ACCESS_LOG", [])

    def predict_calls(self):
        return [e for e in self.access_log if e[1] == "/predict"]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def wait_for(fn, timeout=30, interval=0.05):
    t0 = time.time()
    while time.time() - t0 < timeout:
        value = fn()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("condition not met within timeout")

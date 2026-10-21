import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import Config  # noqa: E402

TEST_KEY = "test-key-0123456789"
DATA = ROOT / "tests" / "data"


@pytest.fixture
def config(tmp_path):
    c = Config()
    c.api_key = TEST_KEY
    c.store_dir = tmp_path / "store"
    return c


@pytest.fixture
def app(config):
    from server.app import create_app
    a = create_app(config, start_background=False)
    a.testing = False  # exercise the real error handlers
    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {TEST_KEY}"}


@pytest.fixture
def ml_service(config):
    """The real ML microservice (random forest) on a free port, sharing the test store."""
    from services.common.app_factory import create_service_app
    from services.ml.server import MLPredictor
    from tests.live import LiveService
    svc = LiveService(create_service_app(MLPredictor("random_forest").load(), config.store_dir, "ml"))
    config.service_urls["ml"] = svc.url
    yield svc
    svc.stop()


@pytest.fixture
def uploaded(client, auth):
    """Upload a fixture file and return its dataset_id."""
    import io

    def _upload(name="valid_1000.csv"):
        r = client.post("/api/datasets", headers=auth,
                        data={"file": (io.BytesIO((DATA / name).read_bytes()), name)},
                        content_type="multipart/form-data")
        assert r.status_code == 201, r.get_json()
        return r.get_json()["dataset_id"]
    return _upload

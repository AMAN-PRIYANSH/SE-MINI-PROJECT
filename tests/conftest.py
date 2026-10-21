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

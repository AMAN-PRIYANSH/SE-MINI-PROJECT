"""Configuration shared by the Web Server and the model microservices.

Every value comes from an environment variable so that no secret (for example the
API key) is ever written in source code (SADS 2.4, item 1). The defaults match the
single-host deployment of SADS 2.5.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _int(name, default):
    value = os.environ.get(name)
    return int(value) if value not in (None, "") else default


def _float(name, default):
    value = os.environ.get(name)
    return float(value) if value not in (None, "") else default


@dataclass
class Config:
    # Web Server
    api_key: str = ""
    host: str = "127.0.0.1"
    port: int = 5000
    # Dataset store (shared by all four processes)
    store_dir: Path = PROJECT_ROOT / "data_store"
    # Limits (SRS REQ-FD-02)
    max_upload_bytes: int = 500 * 1024 * 1024
    max_rows: int = 1_000_000
    # Jobs (SRS REQ-FD-12, REQ-FD-14)
    job_timeout_s: float = 600.0
    workers: int = 8
    # Retention (SRS SR-05)
    retention_s: float = 24 * 3600.0
    purge_interval_s: float = 600.0
    # Model microservices (SADS 2.5)
    service_urls: dict = field(default_factory=lambda: {
        "ml": "http://127.0.0.1:5001",
        "dl": "http://127.0.0.1:5002",
        "qml": "http://127.0.0.1:5003",
    })

    @classmethod
    def from_env(cls):
        c = cls()
        c.api_key = os.environ.get("CCFD_API_KEY", "")
        c.host = os.environ.get("CCFD_HOST", c.host)
        c.port = _int("CCFD_PORT", c.port)
        c.store_dir = Path(os.environ.get("CCFD_STORE_DIR", str(c.store_dir)))
        c.max_upload_bytes = int(_float("CCFD_MAX_UPLOAD_MB", 500) * 1024 * 1024)
        c.max_rows = _int("CCFD_MAX_ROWS", c.max_rows)
        c.job_timeout_s = _float("CCFD_JOB_TIMEOUT_S", c.job_timeout_s)
        c.workers = _int("CCFD_WORKERS", c.workers)
        c.retention_s = _float("CCFD_RETENTION_S", c.retention_s)
        c.purge_interval_s = _float("CCFD_PURGE_INTERVAL_S", c.purge_interval_s)
        for kind, default_port in (("ml", 5001), ("dl", 5002), ("qml", 5003)):
            c.service_urls[kind] = os.environ.get(
                f"CCFD_{kind.upper()}_URL", f"http://127.0.0.1:{default_port}")
        return c

    @property
    def max_upload_mb(self):
        return self.max_upload_bytes / (1024 * 1024)


def store_dir_from_env():
    """Path of the dataset store, as read by the microservices (read-only use)."""
    return Path(os.environ.get("CCFD_STORE_DIR", str(PROJECT_ROOT / "data_store")))

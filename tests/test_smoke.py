"""Smoke checks that the project imports and its configuration loads."""
from shared.config import Config


def test_config_defaults_match_sads_deployment(monkeypatch):
    monkeypatch.delenv("CCFD_PORT", raising=False)
    c = Config.from_env()
    assert c.port == 5000
    assert c.service_urls["ml"].endswith(":5001")
    assert c.service_urls["dl"].endswith(":5002")
    assert c.service_urls["qml"].endswith(":5003")
    assert c.max_upload_mb == 500
    assert c.job_timeout_s == 600


def test_config_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CCFD_API_KEY", "k")
    monkeypatch.setenv("CCFD_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("CCFD_RETENTION_S", "300")
    c = Config.from_env()
    assert c.api_key == "k"
    assert c.store_dir == tmp_path
    assert c.retention_s == 300

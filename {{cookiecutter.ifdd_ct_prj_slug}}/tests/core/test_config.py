"""Configuration from IFDD_CT_* environment variables."""

import pytest

from ifdd.ct import config
from ifdd.ct.config import Settings
from ifdd.ct.errors import UsageError


def test_urls_lose_their_trailing_slash(monkeypatch):
    monkeypatch.setenv("IFDD_CT_BE_URL", "https://rest.test/")
    assert Settings().be_url == "https://rest.test"


def test_values_are_read_when_settings_are_created(monkeypatch):
    before = Settings()
    monkeypatch.setenv("IFDD_CT_BE_URL", "https://other.test")
    assert before.be_url == "https://rest.test"
    assert Settings().be_url == "https://other.test"


def test_aspects_mapping():
    assert Settings().aspects["products"] == "product"


@pytest.mark.parametrize("raw, expected", [("", {}), ('{"racks": "rack"}', {"racks": "rack"})])
def test_aspects_values(monkeypatch, raw, expected):
    monkeypatch.setenv("IFDD_CT_ASPECTS", raw)
    assert Settings().aspects == expected


@pytest.mark.parametrize("raw, message", [("{nope", "not valid JSON"), ('["a"]', "JSON object")])
def test_bad_aspects(monkeypatch, raw, message):
    monkeypatch.setenv("IFDD_CT_ASPECTS", raw)
    with pytest.raises(UsageError, match=message):
        Settings().aspects


def test_require_names_the_missing_variables(monkeypatch):
    monkeypatch.delenv("IFDD_CT_BE_URL")
    with pytest.raises(UsageError, match="IFDD_CT_BE_URL, IFDD_CT_OIDC_CLIENT_ID"):
        Settings().require("be_url", "schema_url", "oidc_client_id")


def test_secret_is_not_shown_in_repr(monkeypatch):
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", "s3cret")
    assert "s3cret" not in repr(Settings())


def test_timeout_default_and_override(monkeypatch):
    assert Settings().http_timeout == 30
    monkeypatch.setenv("IFDD_CT_HTTP_TIMEOUT", "2.5")
    assert Settings().http_timeout == 2.5


@pytest.mark.parametrize("raw, expected", [
    (None, "WARNING"), ("warn", "WARNING"), ("debug", "DEBUG"), ("ERROR", "ERROR")])
def test_log_level(monkeypatch, raw, expected):
    if raw is not None:
        monkeypatch.setenv("IFDD_CT_LOG_LEVEL", raw)
    assert config.log_level() == expected


def test_plugin_path_is_split_and_defaults(monkeypatch):
    monkeypatch.setenv("IFDD_CT_PLUGIN_PATH", "/a:/b::")
    assert config.plugin_path() == ["/a", "/b"]
    monkeypatch.delenv("IFDD_CT_PLUGIN_PATH")
    monkeypatch.delenv("IFDD_CT_PRIVATE_DIR")
    assert config.plugin_path() == ["/plugins"]
    assert config.private_dir() == "/opt/ifdd-ct/private"

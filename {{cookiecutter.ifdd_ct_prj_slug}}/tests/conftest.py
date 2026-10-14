"""Fixtures for every test.

Every test starts from the same, isolated environment: the IFDD_CT_* variables
below and nothing else, and a fresh plugin discovery. Nothing talks to the
network except the e2e tests, which start their own local server.
"""

import os
import sys
from pathlib import Path

import pytest

# Plugin files are rewritten within the same second in some tests; stale
# bytecode would hide the change. It also keeps __pycache__ out of plugins/.
sys.dont_write_bytecode = True

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
EXAMPLES = ROOT / "data" / "examples" / "json-ld"

ENVIRONMENT = {
    "IFDD_CT_BE_URL": "https://rest.test",
    "IFDD_CT_SCHEMA_URL": "https://schema.test/v1",
    "IFDD_CT_UNIT_URL": "https://unit.test/v1",
    "IFDD_CT_ASPECTS": '{"products": "product", "functions": "function", '
                       '"locations": "location", "organisations": "organisation"}',
    "IFDD_CT_CONTEXT_DIR": str(TESTS / "fixtures" / "contexts"),
    "IFDD_CT_PRIVATE_DIR": str(ROOT / "private"),
    "IFDD_CT_PLUGIN_PATH": str(ROOT / "plugins"),
}


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    for key in [k for k in os.environ if k.startswith("IFDD_CT_")]:
        monkeypatch.delenv(key)
    for key, value in ENVIRONMENT.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(ROOT)
    # the CLI configures its own handler; undo that so caplog sees every test
    import logging

    logger = logging.getLogger("ifdd.ct")
    logger.handlers[:] = []
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    from ifdd.ct import registry

    registry.discover(force=True)


@pytest.fixture
def ctx():
    """A fresh pipeline context with the test environment."""
    from ifdd.ct.context import Context

    return Context()


@pytest.fixture
def http_ctx():
    """Factory: a context whose HTTP goes to a FakeSession.

        session = FakeSession(Response(201))
        run_steps("put", records=[...], ctx=http_ctx(session))
    """
    from ifdd.ct.context import Context
    from ifdd.ct.http import Http

    def make(session):
        context = Context()
        context.__dict__["http"] = Http(context.settings, session=session)
        return context

    return make


@pytest.fixture
def with_auth(monkeypatch):
    """Switch on OIDC client credentials for the test."""
    monkeypatch.setenv("IFDD_CT_OIDC_TOKEN_URL", "https://id.test/token")
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_ID", "ifdd-ct")
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", "s3cret")


@pytest.fixture
def plugin_dir(tmp_path, monkeypatch):
    """Factory: write modules into a fresh local plugin directory and rediscover.

        plugin_dir(mine="from ifdd.ct import plugin ...")
    """
    from ifdd.ct import registry

    directory = tmp_path / "plugins"
    directory.mkdir()
    monkeypatch.setenv("IFDD_CT_PLUGIN_PATH", str(directory))

    def write(**modules: str):
        for name, code in modules.items():
            (directory / f"{name}.py").write_text(code)
        registry.discover(force=True)
        return directory

    return write


@pytest.fixture
def private_dir(tmp_path, monkeypatch):
    """Factory: like plugin_dir, for the private origin."""
    from ifdd.ct import registry

    directory = tmp_path / "private"
    directory.mkdir()
    monkeypatch.setenv("IFDD_CT_PRIVATE_DIR", str(directory))

    def write(**modules: str):
        for name, code in modules.items():
            (directory / f"{name}.py").write_text(code)
        registry.discover(force=True)
        return directory

    return write

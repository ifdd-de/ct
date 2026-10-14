"""Against a real, running ifdd-be with a real Keycloak.

These tests write fake data into the backend they are pointed at. They run
only if IFDD_IT_BE_URL is set and are skipped otherwise, so a plain ``pytest``
never touches a backend. The IFDD_IT_* variables are separate from the
IFDD_CT_* ones on purpose: the test setup clears every IFDD_CT_* variable.

    IFDD_IT_BE_URL                  backend, e.g. https://rest
    IFDD_IT_SCHEMA_URL              schema service, e.g. https://schema/v1
    IFDD_IT_TOKEN_URL               token endpoint of the realm
    IFDD_IT_CLIENT_ID               client with the write role (ifdd-ct)
    IFDD_IT_CLIENT_SECRET           its secret
    IFDD_IT_READONLY_CLIENT_ID      optional: client without the write role
    IFDD_IT_READONLY_CLIENT_SECRET  (e.g. ifdd-api-script)
    IFDD_IT_NOPATTERN_CLIENT_ID     optional: client with the read role but no
    IFDD_IT_NOPATTERN_CLIENT_SECRET context pattern (sees no domain context)
    IFDD_IT_CA_BUNDLE               optional: PEM file with the internal CA
    IFDD_IT_ASPECTS                 optional: JSON, path segment -> aspect

The data is generated with a fixed seed, so a second run against the same
backend finds every document unchanged.
"""

import json
import os

import pytest

ASPECTS = {"products": "product", "functions": "function",
           "locations": "location", "organisations": "organisation"}


def _it(name: str, default: str = "") -> str:
    return os.environ.get(f"IFDD_IT_{name}", default).strip()


def pytest_collection_modifyitems(config, items):
    if _it("BE_URL"):
        return
    skip = pytest.mark.skip(reason="IFDD_IT_BE_URL not set - no backend to test against")
    for item in items:
        if "/integration/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(skip)


@pytest.fixture
def backend(monkeypatch):
    """Point ct at the backend under test, with the write client."""
    missing = [n for n in ("SCHEMA_URL", "TOKEN_URL", "CLIENT_ID", "CLIENT_SECRET") if not _it(n)]
    if missing:
        pytest.fail("set " + ", ".join(f"IFDD_IT_{n}" for n in missing))
    monkeypatch.setenv("IFDD_CT_BE_URL", _it("BE_URL"))
    monkeypatch.setenv("IFDD_CT_SCHEMA_URL", _it("SCHEMA_URL"))
    monkeypatch.setenv("IFDD_CT_ASPECTS", _it("ASPECTS") or json.dumps(ASPECTS))
    monkeypatch.setenv("IFDD_CT_OIDC_TOKEN_URL", _it("TOKEN_URL"))
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_ID", _it("CLIENT_ID"))
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", _it("CLIENT_SECRET"))
    if _it("CA_BUNDLE"):
        monkeypatch.setenv("IFDD_CT_CA_BUNDLE", _it("CA_BUNDLE"))
    # contexts come from the schema service, not from the test fixtures
    monkeypatch.delenv("IFDD_CT_CONTEXT_DIR", raising=False)
    return _it("BE_URL")


def use_client(monkeypatch, prefix: str) -> None:
    """Switch ct to the client IFDD_IT_<prefix>_CLIENT_ID/SECRET, or skip."""
    if not (_it(f"{prefix}_CLIENT_ID") and _it(f"{prefix}_CLIENT_SECRET")):
        pytest.skip(f"IFDD_IT_{prefix}_CLIENT_ID/SECRET not set")
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_ID", _it(f"{prefix}_CLIENT_ID"))
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", _it(f"{prefix}_CLIENT_SECRET"))


@pytest.fixture
def nopattern_client(backend):
    """Call use_client(monkeypatch, "NOPATTERN") inside the test, after writing."""
    if not (_it("NOPATTERN_CLIENT_ID") and _it("NOPATTERN_CLIENT_SECRET")):
        pytest.skip("IFDD_IT_NOPATTERN_CLIENT_ID/SECRET not set")
    return use_client


@pytest.fixture
def readonly_client(monkeypatch, backend):
    if not (_it("READONLY_CLIENT_ID") and _it("READONLY_CLIENT_SECRET")):
        pytest.skip("IFDD_IT_READONLY_CLIENT_ID/SECRET not set")
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_ID", _it("READONLY_CLIENT_ID"))
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", _it("READONLY_CLIENT_SECRET"))

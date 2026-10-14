"""A fake ifdd-be on a free local port, with OIDC client credentials switched on."""

import pytest
from support.fake_backend import CLIENT_ID, CLIENT_SECRET, FakeBackend


@pytest.fixture
def backend(monkeypatch):
    with FakeBackend() as server:
        monkeypatch.setenv("IFDD_CT_BE_URL", server.url)
        monkeypatch.setenv("IFDD_CT_OIDC_TOKEN_URL", f"{server.url}/token")
        monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_ID", CLIENT_ID)
        monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", CLIENT_SECRET)
        monkeypatch.setenv("IFDD_CT_HTTP_TIMEOUT", "5")
        yield server

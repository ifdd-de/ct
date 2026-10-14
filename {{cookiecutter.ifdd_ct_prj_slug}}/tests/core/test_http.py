"""HTTP session: timeout, CA bundle and the OIDC client credentials flow."""

import pytest
from support import FakeSession, Response
from support.fakes import token

from ifdd.ct import http as http_module
from ifdd.ct.config import Settings
from ifdd.ct.errors import CtError, UsageError
from ifdd.ct.http import Http


def client(*answers):
    session = FakeSession(*answers)
    return Http(Settings(), session=session), session


def test_without_client_id_no_token_is_requested():
    http, session = client()
    http.get("https://rest.test/x")
    assert session.token_requests() == []
    assert "Authorization" not in session.calls[0].headers


def test_default_timeout_is_applied(monkeypatch):
    monkeypatch.setenv("IFDD_CT_HTTP_TIMEOUT", "7")
    http, session = client()
    http.get("https://rest.test/x")
    assert session.calls[0].timeout == 7.0


def test_token_is_requested_with_client_credentials(with_auth):
    http, session = client()
    http.get("https://rest.test/x")
    form = session.token_requests()[0].form
    assert form == {"grant_type": "client_credentials", "client_id": "ifdd-ct",
                    "client_secret": "s3cret"}
    assert session.requests()[0].headers["Authorization"] == "Bearer t1"


def test_token_is_reused_while_valid(with_auth):
    http, session = client()
    for _ in range(3):
        http.get("https://rest.test/x")
    assert len(session.token_requests()) == 1


def test_token_is_renewed_shortly_before_it_expires(with_auth, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(http_module.time, "monotonic", lambda: now[0])
    http, session = client(token("first", expires_in=60), Response(200),
                           token("second"), Response(200))
    http.get("https://rest.test/x")
    now[0] += 45  # 15 s left, inside the renewal margin
    http.get("https://rest.test/x")
    assert [c.headers["Authorization"] for c in session.requests()] == \
        ["Bearer first", "Bearer second"]


def test_token_is_renewed_once_on_401(with_auth):
    http, session = client(token("old"), Response(401), token("new"), Response(200))
    assert http.get("https://rest.test/x").status_code == 200
    assert [c.headers["Authorization"] for c in session.requests()] == ["Bearer old", "Bearer new"]


def test_second_401_is_returned_not_retried(with_auth):
    http, session = client(token("a"), Response(401), token("b"), Response(401))
    assert http.get("https://rest.test/x").status_code == 401
    assert len(session.requests()) == 2


def test_401_without_auth_is_not_retried():
    http, session = client(Response(401))
    assert http.get("https://rest.test/x").status_code == 401
    assert len(session.calls) == 1


def test_rejected_token_request(with_auth):
    http, _ = client(Response(401, {"error": "invalid_client"}))
    with pytest.raises(CtError, match="token request failed: 401"):
        http.get("https://rest.test/x")


def test_token_request_needs_complete_configuration(with_auth, monkeypatch):
    monkeypatch.delenv("IFDD_CT_OIDC_CLIENT_SECRET")
    http, _ = client()
    with pytest.raises(UsageError, match="IFDD_CT_OIDC_CLIENT_SECRET"):
        http.get("https://rest.test/x")


def test_connection_errors_become_ct_errors():
    import requests

    class Unreachable(FakeSession):
        def request(self, *args, **kwargs):
            raise requests.ConnectionError("refused")

        def post(self, *args, **kwargs):
            raise requests.ConnectionError("refused")

    http = Http(Settings(), session=Unreachable())
    with pytest.raises(CtError, match="GET https://rest.test/x failed: refused"):
        http.get("https://rest.test/x")


def test_token_connection_error(with_auth):
    import requests

    class Unreachable(FakeSession):
        def post(self, *args, **kwargs):
            raise requests.ConnectionError("no route")

    http = Http(Settings(), session=Unreachable())
    with pytest.raises(CtError, match="token request failed: no route"):
        http.get("https://rest.test/x")


def test_ca_bundle_is_used_for_verification(monkeypatch, tmp_path):
    bundle = tmp_path / "ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n")
    monkeypatch.setenv("IFDD_CT_CA_BUNDLE", str(bundle))
    http, session = client()
    assert session.verify == str(bundle)


def test_missing_ca_bundle_is_an_error(monkeypatch, tmp_path):
    monkeypatch.setenv("IFDD_CT_CA_BUNDLE", str(tmp_path / "missing.pem"))
    with pytest.raises(UsageError, match="IFDD_CT_CA_BUNDLE: file not found"):
        client()


def test_context_creates_the_session_on_first_use(ctx):
    assert "http" not in ctx.__dict__
    assert ctx.http is ctx.http

"""patch: merge each document into the existing node."""

import pytest
from support import FakeSession, Response, doc, envelope, run_steps

from ifdd.ct.errors import CtError


def test_sends_patch_to_backend_plus_path_of_id(http_ctx):
    session = FakeSession(Response(200))
    document = doc(name="new name")
    run_steps("patch", records=[document], ctx=http_ctx(session))
    call = session.requests()[0]
    assert (call.method, call.url) == ("PATCH", "https://rest.test/products/0001")
    assert call.json == envelope(document, "product")


def test_missing_node_is_a_failure(http_ctx):
    session = FakeSession(Response(404, {"detail": "Node not found"}))
    with pytest.raises(CtError, match="PATCH: 1 of 1 records failed"):
        run_steps("patch", records=[doc()], ctx=http_ctx(session))


def test_dry_run(http_ctx):
    session = FakeSession()
    run_steps("patch:dry_run=true", records=[doc()], ctx=http_ctx(session))
    assert session.calls == []

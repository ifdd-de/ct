"""post: send each document to /nodes/ (for backends that offer it)."""

import pytest
from support import FakeSession, Response, doc, envelope, run_steps

from ifdd.ct.errors import CtError


def test_sends_post_to_nodes(http_ctx):
    session = FakeSession()
    document = doc()
    run_steps("post", records=[document], ctx=http_ctx(session))
    call = session.requests()[0]
    assert (call.method, call.url) == ("POST", "https://rest.test/nodes/")
    assert call.json == envelope(document, "product")


def test_backend_without_post_route(http_ctx):
    session = FakeSession(Response(405, {"detail": "Method Not Allowed"}))
    with pytest.raises(CtError, match="POST: 1 of 1 records failed"):
        run_steps("post", records=[doc()], ctx=http_ctx(session))

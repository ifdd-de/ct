"""get: fetch documents from the backend and add them to the records."""

import pytest
from support import FakeSession, Response, doc, run_steps

from ifdd.ct.errors import CtError


def test_a_page_of_a_collection(http_ctx):
    session = FakeSession(Response(200, [doc(key="1"), doc(key="2")]))
    result, _ = run_steps("get:segment=products,start=10,end=20", ctx=http_ctx(session))
    call = session.requests()[0]
    assert (call.method, call.url, call.params) == \
        ("GET", "https://rest.test/products", {"start": 10, "end": 20})
    assert len(result) == 2


def test_default_page(http_ctx):
    session = FakeSession(Response(200, []))
    run_steps("get:segment=/products/", ctx=http_ctx(session))
    assert session.requests()[0].params == {"start": 0, "end": 100}
    assert session.requests()[0].url == "https://rest.test/products"


def test_one_node_by_id(http_ctx):
    session = FakeSession(Response(200, doc()))
    result, _ = run_steps("get:id=https://id.example/products/0001", ctx=http_ctx(session))
    assert session.requests()[0].url == "https://rest.test/products/0001"
    assert result == [doc()]


def test_fetched_documents_are_added_to_incoming_records(http_ctx):
    session = FakeSession(Response(200, [doc(key="2")]))
    result, _ = run_steps("data/examples/json-ld/products", "get:segment=products",
                          ctx=http_ctx(session))
    assert len(result) == 5 and result[-1] == doc(key="2")


@pytest.mark.parametrize("step", ["get", "get:segment=products,id=https://x/products/1"])
def test_exactly_one_of_segment_and_id(http_ctx, step):
    with pytest.raises(CtError, match="exactly one of segment"):
        run_steps(step, ctx=http_ctx(FakeSession()))


def test_error_status(http_ctx):
    session = FakeSession(Response(404, {"detail": "Node not found"}))
    with pytest.raises(CtError, match="GET https://rest.test/products/9 -> 404 Node not found"):
        run_steps("get:id=https://rest.test/products/9", ctx=http_ctx(session))

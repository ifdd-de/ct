"""put: create or replace each document on the backend."""

import pytest
from support import FakeSession, Response, doc, envelope, run_steps

from ifdd.ct.errors import CtError, UsageError


def put(records, ctx, step="put"):
    return run_steps(step, records=records, ctx=ctx)


def test_sends_the_envelope_to_backend_plus_path_of_id(http_ctx):
    session = FakeSession()
    document = doc(name="x")
    put([document], http_ctx(session))
    call = session.requests()[0]
    assert (call.method, call.url) == ("PUT", "https://rest.test/products/0001")
    assert call.json == envelope(document, "product")
    assert call.headers["Content-Type"] == "application/json"


def test_ids_of_another_host_go_to_the_configured_backend(http_ctx):
    session = FakeSession()
    put([{**doc(), "@id": "https://id.example/products/0002"}], http_ctx(session))
    assert session.requests()[0].url == "https://rest.test/products/0002"


def test_every_record_is_sent(http_ctx):
    session = FakeSession()
    put([doc(key=str(i)) for i in range(3)], http_ctx(session))
    assert [c.url.rsplit("/", 1)[-1] for c in session.requests()] == ["0", "1", "2"]


def test_envelopes_from_node_are_accepted(http_ctx):
    session = FakeSession()
    document = doc(segment="racks")
    put([envelope(document, "rack")], http_ctx(session))
    assert session.requests()[0].json == envelope(document, "rack")


def test_aspect_parameter(http_ctx):
    session = FakeSession()
    put([doc(segment="racks")], http_ctx(session), step="put:aspect=rack")
    assert session.requests()[0].json["aspect"] == "rack"


def test_records_are_returned_but_not_printed(http_ctx):
    records = [doc()]
    result, printed = put(records, http_ctx(FakeSession()))
    assert result == records and printed == ""


def test_dry_run_sends_nothing(http_ctx, caplog):
    session = FakeSession()
    put([doc(), doc(key="2")], http_ctx(session), step="put:dry_run=true")
    assert session.calls == []
    assert "dry run: PUT https://rest.test/products/2 (aspect product)" in caplog.text


def test_failures_are_collected_and_reported_at_the_end(http_ctx, caplog):
    session = FakeSession(Response(406, {"message": "@id or @context not found"}),
                          Response(201), Response(500, "Internal Server Error"))
    with pytest.raises(CtError, match="PUT: 2 of 3 records failed"):
        put([doc(key="1"), doc(key="2"), doc(key="3")], http_ctx(session))
    assert len(session.requests()) == 3
    assert "406 @id or @context not found" in caplog.text
    assert "500 Internal Server Error" in caplog.text


def test_uses_the_token_when_auth_is_configured(http_ctx, with_auth):
    session = FakeSession()
    put([doc()], http_ctx(session))
    assert session.requests()[0].headers["Authorization"] == "Bearer t1"


def test_document_with_inline_context_is_refused_before_sending(http_ctx):
    session = FakeSession()
    with pytest.raises(CtError, match="single URL"):
        put([{**doc(), "@context": {"@vocab": "https://x/"}}], http_ctx(session))
    assert session.calls == []


def test_backend_url_is_required(http_ctx, monkeypatch):
    monkeypatch.delenv("IFDD_CT_BE_URL")
    with pytest.raises(UsageError, match="IFDD_CT_BE_URL"):
        put([doc()], http_ctx(FakeSession()))


def test_example_base_documents_carry_their_aspect(http_ctx):
    session = FakeSession()
    run_steps("data/examples/json-ld/base", "put", ctx=http_ctx(session))
    assert len(session.requests()) == 15
    assert {c.json["context"].rsplit("/", 1)[-1] for c in session.requests()} == {"base.jsonld"}


def test_error_detail_of_a_json_body_that_is_not_an_object():
    from ifdd.ct.plugins.backend import _detail

    assert _detail(Response(500, ["unexpected"])) == ""

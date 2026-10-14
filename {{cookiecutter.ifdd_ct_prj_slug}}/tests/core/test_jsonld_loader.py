"""Where JSON-LD contexts come from: local directory first, then HTTP."""

import pytest
from support import FakeSession, Response

from ifdd.ct.errors import CtError
from ifdd.ct.jsonld import DocumentLoader, expand

REMOTE_CONTEXT = {"@context": {"@vocab": "https://remote.test/"}}


def loader_with(http_ctx, *answers):
    session = FakeSession(*answers)
    return DocumentLoader(http_ctx(session)), session


def test_context_from_the_local_directory(http_ctx):
    loader, session = loader_with(http_ctx)
    remote = loader("https://schema.test/v1/product.jsonld")
    assert remote["document"]["@context"]["@vocab"] == "https://type.test/v1/product/"
    assert remote["documentUrl"] == "https://schema.test/v1/product.jsonld"
    assert session.calls == []


def test_unknown_file_name_is_fetched(http_ctx):
    loader, session = loader_with(http_ctx, Response(200, REMOTE_CONTEXT))
    assert loader("https://schema.test/v1/other.jsonld")["document"] == REMOTE_CONTEXT
    assert session.calls[0].url == "https://schema.test/v1/other.jsonld"


def test_without_context_directory_everything_is_fetched(http_ctx, monkeypatch):
    monkeypatch.delenv("IFDD_CT_CONTEXT_DIR")
    loader, session = loader_with(http_ctx, Response(200, REMOTE_CONTEXT))
    loader("https://schema.test/v1/product.jsonld")
    assert len(session.calls) == 1


def test_contexts_are_cached_for_the_run(http_ctx):
    loader, session = loader_with(http_ctx, Response(200, REMOTE_CONTEXT))
    for _ in range(3):
        loader("https://schema.test/v1/other.jsonld")
    assert len(session.calls) == 1


def test_one_loader_per_run(ctx):
    doc = {"@context": "https://schema.test/v1/base.jsonld", "@id": "https://x/1", "name": "n"}
    expand(doc, ctx)
    first = ctx.shared["_jsonld_loader"]
    expand(doc, ctx)
    assert ctx.shared["_jsonld_loader"] is first


def test_unloadable_context_is_a_ct_error(http_ctx):
    ctx = http_ctx(FakeSession(Response(200, "not json")))
    doc = {"@context": "https://schema.test/v1/missing.jsonld", "@id": "https://x/1"}
    with pytest.raises(CtError, match="expand https://x/1"):
        expand(doc, ctx)


def test_the_remote_loader_is_reused_for_further_urls(http_ctx):
    loader, session = loader_with(http_ctx, Response(200, REMOTE_CONTEXT), Response(200, REMOTE_CONTEXT))
    loader("https://schema.test/v1/one.jsonld")
    remote = loader._remote
    loader("https://schema.test/v1/two.jsonld")
    assert loader._remote is remote and len(session.calls) == 2


def test_uncompactable_document_is_a_ct_error(http_ctx):
    from ifdd.ct.jsonld import compact

    ctx = http_ctx(FakeSession(Response(200, "not json")))
    with pytest.raises(CtError, match="compact https://x/1"):
        compact({"@id": "https://x/1"}, "https://schema.test/v1/missing.jsonld", ctx)

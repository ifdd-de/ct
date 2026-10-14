"""Mapping documents onto the backend's node envelope."""

import pytest
from support import doc, envelope

from ifdd.ct.errors import CtError
from ifdd.ct.nodes import aspect_of, document_of, is_node, node_url, segment_of, to_node


@pytest.mark.parametrize("record, expected", [
    (envelope(doc(), "product"), True),
    (doc(), False),
    ({"json": "text", "aspect": "x"}, False),
    ({"json": {}}, False),
    ("text", False),
])
def test_is_node(record, expected):
    assert is_node(record) is expected


def test_document_of_unwraps_envelopes():
    document = doc()
    assert document_of(envelope(document, "product")) is document
    assert document_of(document) is document


@pytest.mark.parametrize("doc_id, segment", [
    ("https://rest.test/products/1", "products"),
    ("https://rest.test/api/v1/locations/7", "locations"),
    ("https://rest.test/1", ""),
    ("", ""),
])
def test_segment_of(doc_id, segment):
    assert segment_of(doc_id) == segment


class TestAspectOrder:
    """The aspect comes from, in this order: parameter, envelope, mapping, field."""

    def test_parameter_wins(self, ctx):
        assert aspect_of(envelope(doc(), "product"), ctx, "custom") == "custom"

    def test_then_the_envelope(self, ctx):
        assert aspect_of(envelope(doc(segment="racks"), "rack"), ctx) == "rack"

    def test_then_the_mapping(self, ctx):
        assert aspect_of(doc(aspect="ignored"), ctx) == "product"

    def test_then_the_aspect_field(self, ctx):
        assert aspect_of(doc(segment="racks", aspect="rack"), ctx) == "rack"

    def test_otherwise_an_error(self, ctx):
        with pytest.raises(CtError, match="segment 'racks'.*IFDD_CT_ASPECTS or pass aspect"):
            aspect_of(doc(segment="racks"), ctx)


def test_to_node_builds_the_envelope(ctx):
    document = doc(name="x")
    assert to_node(document, ctx) == envelope(document, "product")


def test_to_node_keeps_an_expanded_form(ctx):
    node = envelope(doc(), "product", expanded={"@id": "x"})
    assert to_node(node, ctx)["expanded"] == {"@id": "x"}


@pytest.mark.parametrize("missing", ["@id", "@context"])
def test_to_node_needs_id_and_context(ctx, missing):
    document = doc()
    del document[missing]
    with pytest.raises(CtError, match=f"without {missing}"):
        to_node(document, ctx)


def test_to_node_needs_a_single_context_url(ctx):
    with pytest.raises(CtError, match="single URL, got dict"):
        to_node({**doc(), "@context": {"@vocab": "x"}}, ctx)


@pytest.mark.parametrize("doc_id, url", [
    ("https://rest.test/products/1", "https://be.test/products/1"),
    ("https://id.example/products/1", "https://be.test/products/1"),
])
def test_node_url_puts_the_path_on_the_backend(doc_id, url):
    assert node_url(doc_id, "https://be.test/") == url


def test_node_url_needs_a_path():
    with pytest.raises(CtError, match="has no path"):
        node_url("https://rest.test/", "https://be.test")

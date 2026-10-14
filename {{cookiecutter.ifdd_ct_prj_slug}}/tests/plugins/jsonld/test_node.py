"""node: wrap documents in the backend envelope, without sending anything."""

import pytest
from support import doc, envelope, run_steps

from ifdd.ct.errors import CtError


def test_envelope_from_the_aspect_mapping():
    document = doc(name="x")
    assert run_steps("node", records=[document])[0] == [envelope(document, "product")]


def test_envelope_with_explicit_aspect():
    document = doc(segment="racks")
    assert run_steps("node:aspect=rack", records=[document])[0][0]["aspect"] == "rack"


def test_envelope_with_expanded_form():
    result, _ = run_steps("node:expanded=true", records=[doc(name="x")])
    assert result[0]["expanded"]["https://type.test/v1/product/name"] == [{"@value": "x"}]


def test_envelopes_can_be_wrapped_again():
    once, _ = run_steps("node", records=[doc()])
    assert run_steps("node", records=once)[0] == once


def test_example_documents_all_get_an_aspect():
    result, _ = run_steps("data/examples/json-ld", "node")
    assert {r["aspect"] for r in result} == {"product", "function", "location", "organisation"}


def test_document_without_known_aspect():
    with pytest.raises(CtError, match="IFDD_CT_ASPECTS or pass aspect"):
        run_steps("node", records=[doc(segment="racks")])

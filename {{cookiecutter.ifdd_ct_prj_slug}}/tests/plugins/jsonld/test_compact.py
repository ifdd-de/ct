"""compact: JSON-LD compaction against the document's own or a given context."""

import pytest
from support import doc, run_steps

from ifdd.ct.errors import CtError

EXPANDED = {
    "@id": "https://rest.test/products/0001",
    "https://type.test/v1/product/name": [{"@value": "Trafo 1"}],
}


def test_compact_against_the_documents_own_context():
    result, _ = run_steps("compact", records=[doc(name="Trafo 1")])
    assert result[0] == doc(name="Trafo 1")


def test_compact_against_a_given_context():
    step = "compact:context=https://schema.test/v1/product.jsonld"
    result, _ = run_steps(step, records=[EXPANDED])
    assert result[0]["name"] == "Trafo 1"
    assert result[0]["@context"] == "https://schema.test/v1/product.jsonld"


def test_expand_then_compact_is_a_round_trip():
    original = doc(name="Trafo 1", hasPart="https://rest.test/products/2")
    expanded, _ = run_steps("expand", records=[original])
    result, _ = run_steps("compact:context=https://schema.test/v1/product.jsonld",
                          records=expanded)
    assert result[0] == original


def test_compact_needs_a_context():
    with pytest.raises(CtError, match="no @context and no context parameter"):
        run_steps("compact", records=[EXPANDED])


def test_an_inline_context_is_not_replaced_by_its_url():
    inline = {"@context": {"@vocab": "https://example.test/"}, "@id": "https://x/1", "name": "n"}
    result, _ = run_steps("compact", records=[inline])
    assert result[0]["name"] == "n" and result[0]["@context"] == {"@vocab": "https://example.test/"}

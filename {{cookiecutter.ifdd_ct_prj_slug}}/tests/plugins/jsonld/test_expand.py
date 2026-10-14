"""expand: JSON-LD expansion, contexts from tests/fixtures/contexts."""

import pytest
from support import doc, run_steps

from ifdd.ct.errors import CtError

VOCAB = "https://type.test/v1/product/"


def test_terms_become_full_iris():
    result, _ = run_steps("expand", records=[doc(name="Trafo 1")])
    assert result[0]["@id"] == "https://rest.test/products/0001"
    assert result[0][VOCAB + "name"] == [{"@value": "Trafo 1"}]


def test_references_become_ids():
    result, _ = run_steps("expand", records=[doc(hasPart=["https://rest.test/products/2"])])
    assert result[0][VOCAB + "hasPart"] == [{"@id": "https://rest.test/products/2"}]


def test_one_output_per_input():
    records = [doc(key="1", name="a"), doc(key="2", context="base", name="b")]
    result, _ = run_steps("expand", records=records)
    assert [r["@id"] for r in result] == ["https://rest.test/products/1",
                                           "https://rest.test/products/2"]


def test_several_nodes_are_kept_as_a_graph():
    graph = {"@context": {"@vocab": "https://x.test/"},
             "@graph": [{"@id": "https://x.test/1", "a": 1}, {"@id": "https://x.test/2", "a": 2}]}
    result, _ = run_steps("expand", records=[graph])
    assert len(result) == 1 and len(result[0]["@graph"]) == 2


def test_document_without_content_expands_to_an_empty_graph():
    # JSON-LD drops a node that has nothing but an @id
    assert run_steps("expand", records=[doc()])[0] == [{"@graph": []}]


def test_unknown_context_fails(http_ctx):
    from support import FakeSession, Response

    ctx = http_ctx(FakeSession(Response(200, "not json")))
    with pytest.raises(CtError, match="expand https://rest.test/products/0001"):
        run_steps("expand", records=[doc(context="unknown")], ctx=ctx)

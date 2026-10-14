"""The datacenter profile: a small documentation example of a second domain."""

from collections import Counter

import pytest
from support import run_steps

from ifdd.ct.errors import CtError
from ifdd.ct.faker import generate


@pytest.fixture
def docs(ctx):
    return generate("datacenter", ctx, seed=4,
                    counts={"room": 2, "rack": 3, "pdu": 6, "server": 9})


def of_type(docs, kind):
    return [d for d in docs if d["@type"] == kind]


def test_one_document_per_entity(docs):
    assert Counter(d["@type"] for d in docs) == {"Room": 2, "Rack": 3, "Pdu": 6, "Server": 9}
    assert len({d["@id"] for d in docs}) == len(docs)


def test_racks_are_spread_over_the_rooms(docs):
    rooms = {d["@id"]: d for d in of_type(docs, "Room")}
    for rack in of_type(docs, "Rack"):
        assert {"@id": rack["@id"]} in rooms[rack["isPartOf"]["@id"]]["hasPart"]


def test_every_server_is_fed_by_the_pdus_of_its_rack(docs):
    pdus = {d["@id"]: d for d in of_type(docs, "Pdu")}
    for server in of_type(docs, "Server"):
        feeding = {p["@id"] for p in server["fedBy"]}
        assert len(feeding) == 2
        assert all(pdus[p]["isPartOf"] == server["isPartOf"] for p in feeding)


def test_inline_context_with_placeholder_vocabulary(docs):
    assert all(d["@context"] == {"@vocab": "https://example.org/ifdd/datacenter#"} for d in docs)


def test_documents_expand_offline(docs):
    expanded, _ = run_steps("expand", records=docs[:2])
    assert "https://example.org/ifdd/datacenter#name" in expanded[0]


def test_without_racks_nothing_is_linked(ctx):
    docs = generate("datacenter", ctx, seed=1, counts={"room": 1, "rack": 0, "pdu": 2, "server": 2})
    assert all("isPartOf" not in d and "fedBy" not in d for d in docs)


def test_is_not_meant_for_the_backend(docs, http_ctx):
    from support import FakeSession

    with pytest.raises(CtError, match="single URL"):
        run_steps("put:aspect=room", records=docs[:1], ctx=http_ctx(FakeSession()))


def test_racks_without_rooms_are_still_fed(ctx):
    docs = generate("datacenter", ctx, seed=1, counts={"room": 0, "rack": 2, "pdu": 2, "server": 2})
    racks = [d for d in docs if d["@type"] == "Rack"]
    assert len(racks) == 2 and all("isPartOf" not in r for r in racks)

"""The generic faker engine: ids, seeds, links, documents, profile registry."""

import dataclasses

import pytest

from ifdd.ct.errors import UsageError
from ifdd.ct.faker import SEED_ANCHOR, EntityType, Graph, Profile, generate, profiles

THING = EntityType("thing", "things", 2, ("base", "thing"))


def tiny_profile(populate=None, **overrides):
    return Profile(
        name="tiny",
        description="test profile",
        types={"thing": THING},
        make=lambda g, t, e: e.set_all("name", g.fake.word()),
        populate=populate or (lambda g, counts: g.create("thing", counts["thing"])),
        context=lambda namespace, settings: f"https://schema.test/v1/{namespace}.jsonld",
        **overrides,
    )


def graph(seed=1, profile=None):
    from ifdd.ct.config import Settings

    return Graph(profile or tiny_profile(), Settings(), seed)


# -- ids, time and randomness ----------------------------------------------

def test_ids_are_backend_url_segment_and_uuid():
    [thing] = graph().create("thing", 1)
    prefix, uuid = thing.id.rsplit("/", 1)
    assert prefix == "https://rest.test/things" and len(uuid) == 36 and uuid[14] == "4"


def test_seeded_timestamps_are_relative_to_a_fixed_anchor():
    g = graph(seed=3)
    stamps = [g.timestamp(30) for _ in range(20)]
    assert all(s <= SEED_ANCHOR.isoformat() for s in stamps)
    assert graph(seed=3).timestamp(30) == stamps[0]


def test_day_is_a_date_within_range():
    day = graph().day(10)
    assert "2025-12-22" <= day <= "2026-01-01"


def test_unseeded_graphs_differ():
    assert graph(seed=None).create("thing", 1)[0].id != graph(seed=None).create("thing", 1)[0].id


# -- entities and links ----------------------------------------------------

def test_set_all_writes_every_namespace():
    [thing] = graph().create("thing", 1)
    assert thing.fields["base"]["name"] == thing.fields["thing"]["name"]


def test_link_with_inverse_many_and_single():
    g = graph()
    whole, part = g.create("thing", 2)
    g.link(whole, "hasPart", part, inverse="isPartOf", inverse_many=False)
    assert whole.fields["thing"]["hasPart"] == [{"@id": part.id}]
    assert part.fields["thing"]["isPartOf"] == {"@id": whole.id}


def test_links_are_not_duplicated():
    g = graph()
    a, b = g.create("thing", 2)
    g.link(a, "knows", b)
    g.link(a, "knows", b)
    assert a.fields["thing"]["knows"] == [{"@id": b.id}]


def test_documents_one_per_namespace_with_shared_id():
    g = graph()
    g.create("thing", 2)
    docs = g.documents()
    assert len(docs) == 4
    assert [d["@context"].rsplit("/", 1)[-1] for d in docs] == \
        ["base.jsonld", "thing.jsonld"] * 2
    assert docs[0]["@id"] == docs[1]["@id"]


# -- generate() ------------------------------------------------------------

@pytest.fixture
def registered_tiny():
    profile = tiny_profile()
    profiles._profiles["tiny"] = profile
    yield profile
    profiles._profiles.pop("tiny", None)


def test_generate_uses_default_counts(ctx, registered_tiny):
    assert len(generate("tiny", ctx, seed=1)) == 4


def test_generate_accepts_counts_as_text(ctx, registered_tiny):
    assert len(generate("tiny", ctx, seed=1, counts={"thing": "3"})) == 6


def test_generate_checks_required_settings(ctx, registered_tiny, monkeypatch):
    monkeypatch.delenv("IFDD_CT_UNIT_URL")
    registered_tiny.requires = ("be_url", "unit_url")
    with pytest.raises(UsageError, match="IFDD_CT_UNIT_URL"):
        generate("tiny", ctx)


# -- profile registry ------------------------------------------------------

def test_builtin_profiles():
    assert [p.name for p in profiles.all_profiles()] == ["datacenter", "energy-grid"]


def test_registering_a_builtin_name_twice_is_refused():
    copy = dataclasses.replace(profiles.get("energy-grid"), description="copy")
    with pytest.raises(UsageError, match="registered twice"):
        profiles.register(copy)


def test_local_module_can_register_a_profile(plugin_dir, ctx):
    plugin_dir(tiny_local="""
from ifdd.ct.faker import EntityType, Profile, register_profile

register_profile(Profile(
    name="tiny-local", description="one thing",
    types={"thing": EntityType("thing", "things", 2, ("thing",))},
    make=lambda g, t, e: e.set("thing", "name", g.fake.word()),
    populate=lambda g, counts: g.create("thing", counts["thing"]),
    context=lambda ns, settings: {"@vocab": "https://example.org/"},
))
""")
    assert len(generate("tiny-local", ctx, seed=1)) == 2


def test_local_profile_can_be_reloaded(plugin_dir, ctx):
    code = """
from ifdd.ct.faker import EntityType, Profile, register_profile
register_profile(Profile(name="again", description="", types={
    "thing": EntityType("thing", "things", COUNT, ("thing",))},
    make=lambda g, t, e: None, populate=lambda g, c: g.create("thing", c["thing"]),
    context=lambda ns, s: dict()))
"""
    directory = plugin_dir(again=code.replace("COUNT", "1"))
    (directory / "again.py").write_text(code.replace("COUNT", "3"))
    from ifdd.ct import registry

    registry.discover(force=True)
    assert len(generate("again", ctx, seed=1)) == 3


def test_a_further_namespace_takes_only_the_times_the_entity_has():
    [thing] = graph().create("thing", 1)
    thing.fields[thing.type.namespaces[0]] = {"c_created": "2026-01-01T00:00:00Z"}
    thing.add_namespace("extra", {"x": 1})
    assert thing.fields["extra"] == {"x": 1, "c_created": "2026-01-01T00:00:00Z"}

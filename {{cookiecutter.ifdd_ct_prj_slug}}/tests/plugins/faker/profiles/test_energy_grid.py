"""The energy-grid profile: aspects, documents and structure as ifdd-be expects."""

from collections import Counter

import pytest

from ifdd.ct.faker import generate

ASPECTS = ["product", "function", "location", "organisation"]
DOMAINS = ["breaker.grid.example.ifdd.de", "maintenance.ops.example.ifdd.de"]


@pytest.fixture
def docs(ctx):
    return generate("energy-grid", ctx, seed=11,
                    counts={"product": 4, "function": 3, "location": 2, "organisation": 3})


def aspect_docs(docs, aspect):
    """The current documents of one context (without earlier versions)."""
    return [d for d in docs if d["@context"] == f"https://schema.test/v1/{aspect}.jsonld"
            and "c_validNotAfter" not in d]


def earlier_docs(docs):
    return [d for d in docs if "c_validNotAfter" in d]


def by_id(documents):
    return {d["@id"]: d for d in documents}


def test_every_entity_has_a_base_and_an_aspect_document(docs):
    generic = [d for d in docs if "c_validNotAfter" not in d
               and not any(d["@context"].endswith(f"/{name}.jsonld") for name in DOMAINS)]
    per_id = Counter(d["@id"] for d in generic)
    assert set(per_id.values()) == {2}
    assert len(aspect_docs(docs, "base")) == len(per_id)


def test_entity_numbers_include_the_parts(docs):
    # products 4 + 3 parts each, locations 2 + 3 parts each
    assert {a: len(aspect_docs(docs, a)) for a in ASPECTS} == \
        {"product": 16, "function": 3, "location": 8, "organisation": 3}


def test_ids_use_the_rest_segments_of_ifdd_be(docs, ctx):
    segments = {d["@id"].rsplit("/", 2)[-2] for d in docs}
    assert segments == set(ctx.settings.aspects)


@pytest.mark.parametrize("field", ["objName", "description", "objType", "objScope", "c_created",
                                   "c_modified", "c_validNotBefore", "origin"])
def test_common_fields_are_in_both_documents(docs, field):
    base = by_id(aspect_docs(docs, "base"))
    for aspect in ASPECTS:
        for d in aspect_docs(docs, aspect):
            assert d[field] == base[d["@id"]][field]


def test_properties_are_in_the_aspect_document(docs):
    for aspect in ASPECTS:
        for d in aspect_docs(docs, aspect):
            assert d["properties"] and all(p["prop_validity"] == "valid" for p in d["properties"])
    assert all("properties" not in d for d in aspect_docs(docs, "base"))


@pytest.mark.parametrize("aspect", ["product", "location"])
def test_every_whole_has_three_parts_of_its_own(docs, aspect):
    documents = aspect_docs(docs, aspect)
    wholes = [d for d in documents if "hasPart" in d]
    parts = [d for d in documents if "isPartOf" in d]
    assert len(parts) == 3 * len(wholes)
    for whole in wholes:
        children = [p["@id"] for p in whole["hasPart"]]
        assert len(set(children)) == 3
        assert all(by_id(parts)[c]["isPartOf"] == {"@id": whole["@id"]} for c in children)


@pytest.mark.parametrize("aspect, predicate, target, inverse", [
    ("product", "providesFunction", "function", "implementedBy"),
    ("product", "usesFunction", "function", "usedBy"),
    ("product", "containedIn", "location", "containsProduct"),
    ("product", "responsibleOrganisation", "organisation", "productResponsibility"),
    ("function", "responsibleOrganisation", "organisation", "functionalResponsibility"),
    ("organisation", "roleDeliversTo", "organisation", "roleClientOf"),
])
def test_links_point_to_existing_entities_and_have_inverses(docs, aspect, predicate, target, inverse):
    targets = by_id(aspect_docs(docs, target))
    linked = [d for d in aspect_docs(docs, aspect) if predicate in d]
    assert linked
    for d in linked:
        refs = d[predicate] if isinstance(d[predicate], list) else [d[predicate]]
        for ref in refs:
            assert {"@id": d["@id"]} in targets[ref["@id"]][inverse]


def test_organisations_never_deliver_to_themselves(docs):
    for d in aspect_docs(docs, "organisation"):
        assert d["roleDeliversTo"]["@id"] != d["@id"]


def test_zero_counts_leave_links_out(ctx):
    docs = generate("energy-grid", ctx, seed=1,
                    counts={"product": 1, "function": 0, "location": 0, "organisation": 0})
    products = aspect_docs(docs, "product")
    assert len(products) == 4
    assert all("providesFunction" not in d and "containedIn" not in d for d in products)


def test_needs_the_unit_url(ctx, monkeypatch):
    from ifdd.ct.context import Context
    from ifdd.ct.errors import UsageError

    monkeypatch.delenv("IFDD_CT_UNIT_URL")
    with pytest.raises(UsageError, match="IFDD_CT_UNIT_URL"):
        generate("energy-grid", Context())


# --- domain contexts of circuit breakers --------------------------------------------

@pytest.fixture
def grid(ctx):
    """Enough products for circuit breakers among them (seed 42, as the pipeline)."""
    return generate("energy-grid", ctx, seed=42,
                    counts={"product": 20, "function": 8, "location": 5, "organisation": 4})


def current(docs, context_name):
    return aspect_docs(docs, context_name)


def test_circuit_breakers_have_both_domain_documents(grid):
    products = by_id(current(grid, "product"))
    breakers = {i for i, d in products.items() if d["objType"] == "Circuit Breaker"}
    assert breakers
    for name in DOMAINS:
        assert {d["@id"] for d in current(grid, name)} == breakers


def test_domain_documents_have_their_own_source_values(grid):
    products = by_id(current(grid, "product"))
    for d in current(grid, DOMAINS[0]):
        product = products[d["@id"]]
        assert d["objName"] != product["objName"] and d["origin"] != product["origin"]
        assert d["serialNumber"] == product["serial_number"]
        assert d["c_created"] == product["c_created"]


def test_rated_values_are_quantities_with_unit_iris(grid):
    for d in current(grid, DOMAINS[0]):
        voltage, current_ = d["ratedVoltage"], d["ratedCurrent"]
        assert voltage["type"] == "qudt:QuantityValue"
        assert voltage["qudt:unit"] == {"@id": "https://unit.test/v1/unit/KiloV"}
        assert current_["qudt:unit"] == {"@id": "https://unit.test/v1/unit/A"}
        assert isinstance(voltage["qudt:numericValue"], int)


def test_domain_documents_fit_their_contexts(grid):
    """'check' finds no undefined term (contexts: copies of the schema examples)."""
    from support import run_steps

    domain = [d for d in grid if any(d["@context"].endswith(f"/{n}.jsonld") for n in DOMAINS)]
    run_steps("check:fail=true", records=domain)


def test_next_inspection_follows_the_interval(grid):
    for d in current(grid, DOMAINS[1]):
        years = int(d["maintenanceInterval"][1:-1])
        assert int(d["nextInspection"][:4]) - int(d["lastInspection"][:4]) == years


def test_needs_backend_and_schema_url(ctx, monkeypatch):
    from ifdd.ct.context import Context
    from ifdd.ct.errors import UsageError

    monkeypatch.delenv("IFDD_CT_SCHEMA_URL")
    with pytest.raises(UsageError, match="IFDD_CT_SCHEMA_URL"):
        generate("energy-grid", Context())


def test_documents_can_be_expanded_with_the_schema_contexts(docs):
    from support import run_steps

    expanded, _ = run_steps("expand", records=docs[:4])
    assert all(e["@id"] for e in expanded)


# --- c_* source times and earlier versions -------------------------------------------

def test_every_document_has_source_times_in_order(docs):
    for d in docs:
        assert d["c_created"] <= d["c_modified"]
        assert d["c_validNotBefore"] >= d["c_created"]
        assert d["c_created"].endswith("+00:00")


def test_a_tenth_of_the_entities_changed_once(docs):
    """Of 3 + 3*... = 42 entities, round(4.2) = 4 have an earlier version."""
    entities = {d["@id"] for d in docs}
    changed = {d["@id"] for d in earlier_docs(docs)}
    assert len(changed) == round(len(entities) * 0.1) > 0


def test_an_earlier_version_ends_where_the_current_one_starts(docs):
    current = {(d["@id"], d["@context"]): d for d in docs if "c_validNotAfter" not in d}
    for earlier in earlier_docs(docs):
        now = current[(earlier["@id"], earlier["@context"])]
        assert earlier["c_validNotBefore"] == earlier["c_created"]
        assert earlier["c_validNotAfter"] == now["c_validNotBefore"] == now["c_modified"]
        assert earlier["c_validNotBefore"] < earlier["c_validNotAfter"]
        if "description" in now:  # the domain contexts have none
            assert earlier["description"] != now["description"]
        rest = {k: v for k, v in earlier.items() if not k.startswith("c_") and k != "description"}
        assert rest == {k: v for k, v in now.items() if not k.startswith("c_") and k != "description"}


def test_an_earlier_version_comes_first(docs):
    """Versions are listed in time order; the backend does not depend on it
    (their valid times do not overlap), a reader of out/*.json does."""
    seen = set()
    for d in docs:
        key = (d["@id"], d["@context"])
        if "c_validNotAfter" in d:
            assert key not in seen
        seen.add(key)


def test_the_same_seed_gives_the_same_versions(ctx):
    counts = {"product": 2, "function": 1, "location": 1, "organisation": 1}
    assert generate("energy-grid", ctx, seed=3, counts=counts) == \
        generate("energy-grid", ctx, seed=3, counts=counts)


def test_every_kind_of_function_occurs(ctx):
    docs = generate("energy-grid", ctx, seed=2,
                    counts={"product": 0, "function": 12, "location": 0, "organisation": 0})
    kinds = {d.get("objType") for d in docs if d["@context"].endswith("/function.jsonld")}
    assert kinds >= {"Power Generation", "Power Transmission", "Power Distribution",
                     "Grid Control", "Load Balancing", "Fault Protection"}


@pytest.mark.parametrize("day, years, expected", [
    ("2023-05-17", 2, "2025-05-17"),
    ("2024-02-29", 1, "2025-02-28"),
])
def test_years_later(day, years, expected):
    from ifdd.ct.faker.profiles.energy_grid import _years_later

    assert _years_later(day, years) == expected

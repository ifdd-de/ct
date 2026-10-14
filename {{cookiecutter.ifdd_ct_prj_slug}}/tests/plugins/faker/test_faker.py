"""faker as a pipeline step: parameters, source role, errors."""

import pytest
from support import run_steps

from ifdd.ct.errors import UsageError

SMALL = "product=1,function=1,location=0,organisation=0"


def test_default_profile_is_energy_grid():
    result, _ = run_steps(f"faker:seed=1,{SMALL}")
    assert all(r["@context"].startswith("https://schema.test/v1/") for r in result)


def test_counts_are_given_per_entity_type():
    result, _ = run_steps(f"faker:seed=1,{SMALL}")
    ids = {r["@id"].rsplit("/", 2)[-2] for r in result}
    assert ids == {"products", "functions"}
    assert len({r["@id"] for r in result}) == 1 + 3 + 1   # product, its parts, function


def test_profile_parameter():
    result, _ = run_steps("faker:profile=datacenter,seed=1,room=1,rack=1,pdu=0,server=0")
    assert [r["@type"] for r in result] == ["Room", "Rack"]


def test_output_is_printed_as_json():
    _, printed = run_steps(f"faker:seed=1,{SMALL}")
    assert printed.startswith("[\n")


def test_generated_records_are_added_to_incoming_ones():
    generated, _ = run_steps(f"faker:seed=1,{SMALL}")
    result, _ = run_steps("data/examples/json-ld/products", f"faker:seed=1,{SMALL}")
    assert len(result) == 4 + len(generated) and generated == result[4:]


def test_same_seed_same_output():
    assert run_steps(f"faker:seed=5,{SMALL}")[1] == run_steps(f"faker:seed=5,{SMALL}")[1]


def test_without_seed_the_data_differs():
    assert run_steps(f"faker:{SMALL}")[0] != run_steps(f"faker:{SMALL}")[0]


@pytest.mark.parametrize("step, message", [
    ("faker:widget=3", "no entity type 'widget'"),
    ("faker:product=many", "product=many: expected a whole number"),
    ("faker:product=-1", "must not be negative"),
    ("faker:profile=nope", "unknown faker profile 'nope'"),
    ("faker:seed=abc", "'abc' is not a valid int"),
])
def test_bad_parameters(step, message):
    with pytest.raises(UsageError, match=message):
        run_steps(step)


def test_describe_lists_the_profiles():
    from ifdd.ct.registry import resolve

    text = resolve("faker").describe()
    assert "energy-grid: product=10, function=5, location=3, organisation=3" in text
    assert "datacenter: room=2, rack=6, pdu=12, server=24" in text

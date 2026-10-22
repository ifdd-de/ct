"""ts-climate: example samples for the objects of a context."""

import math

import pytest
from support import run_steps

from ifdd.ct.errors import UsageError

BREAKER = "https://schema.test/v1/breaker.grid.example.ifdd.de.jsonld"
END = "2026-10-22T12:00:00Z"


@pytest.fixture(autouse=True)
def type_url(monkeypatch):
    monkeypatch.setenv("IFDD_CT_TYPE_URL", "https://type.test/v1")


def breaker(key):
    return {"@id": f"https://rest.test/products/{key}", "@context": BREAKER, "objName": key}


def climate(records, *params):
    step = "ts-climate:" + ",".join([f"end={END}", *params])
    result, _ = run_steps(step, records=records)
    return result


def test_two_series_per_object_of_the_context():
    other = {"@id": "https://rest.test/products/9", "@context": "https://schema.test/v1/product.jsonld"}
    samples = climate([breaker("1"), breaker("1"), breaker("2"), other], "days=1", "step=3600")
    assert len(samples) == 2 * 2 * 24
    assert {s["ifdd_id"] for s in samples} == {
        "https://rest.test/products/1", "https://rest.test/products/2"}
    first = samples[0]
    assert first == {
        "store": "temperature.ops.example.ifdd.de",
        "name": "temperature",
        "ifdd_id": "https://rest.test/products/1",
        "ifdd_property": "https://type.test/v1/climate.ops.example.ifdd.de/temperature",
        "ifdd_unit": "https://unit.test/v1/unit/DEG_C",
        "time": "2026-10-21T13:00:00.000+00:00",
        "value": first["value"],
    }
    humidity = [s for s in samples if s["name"] == "humidity"]
    assert {s["store"] for s in humidity} == {"humidity.ops.example.ifdd.de"}
    assert {s["ifdd_unit"] for s in humidity} == {"https://unit.test/v1/unit/PERCENT_RH"}
    assert humidity[-1]["time"] == "2026-10-22T12:00:00.000+00:00"


def test_values_stay_within_the_bounds_of_the_vocabulary():
    samples = climate([breaker(str(i)) for i in range(20)], "days=7")
    for sample in samples:
        low, high = (-50, 100) if sample["name"] == "temperature" else (0, 100)
        assert low <= sample["value"] <= high and math.isfinite(sample["value"])
    assert len(samples) == 20 * 2 * 7 * 96


def test_same_seed_same_samples_other_seed_other_values():
    one = climate([breaker("1")], "days=1")
    assert climate([breaker("1")], "days=1") == one
    other = climate([breaker("1")], "days=1", "seed=7")
    assert [s["value"] for s in other] != [s["value"] for s in one]
    assert [s["time"] for s in other] == [s["time"] for s in one]


def test_other_context_and_stores():
    records = [{"@id": "https://rest.test/locations/1",
                "@context": "https://schema.test/v1/location.jsonld"}]
    samples = climate(records, "days=1", "step=43200", "context=location",
                      "temperature_store=t.example", "humidity_store=h.example")
    assert [s["store"] for s in samples] == ["t.example", "t.example", "h.example", "h.example"]


def test_without_matching_objects(caplog):
    assert climate([{"@id": "x"}, "not a dict", {"@context": {"inline": 1}}]) == []
    assert "no record with the context breaker.grid.example.ifdd.de" in caplog.text


def test_end_defaults_to_the_last_full_step():
    (sample,) = [s for s in run_steps("ts-climate:days=1,step=86400",
                                      records=[breaker("1")])[0] if s["name"] == "temperature"]
    assert sample["time"].endswith("T00:00:00.000+00:00")


@pytest.mark.parametrize(
    "params, message",
    [
        (["end=2026-10-22T12:00:00"], "no offset"),
        (["end=noon"], "not an ISO 8601 time"),
        (["days=0"], "days >= 1"),
        (["step=0"], "step >= 1"),
    ],
)
def test_refused_parameters(params, message):
    step = "ts-climate:" + ",".join(params)
    with pytest.raises(UsageError, match=message):
        run_steps(step, records=[breaker("1")])


def test_needs_type_and_unit_url(monkeypatch):
    monkeypatch.delenv("IFDD_CT_TYPE_URL")
    with pytest.raises(UsageError, match="IFDD_CT_TYPE_URL"):
        run_steps("ts-climate", records=[breaker("1")])

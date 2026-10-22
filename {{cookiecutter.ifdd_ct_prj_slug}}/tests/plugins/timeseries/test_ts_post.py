"""ts-post: write sample records to ts-api, per store in lists."""

import pytest
from support import FakeSession, Response, run_steps

from ifdd.ct.errors import CtError, UsageError

API = "https://ts.test/tsapi"


@pytest.fixture(autouse=True)
def ts_api_url(monkeypatch):
    monkeypatch.setenv("IFDD_CT_TS_API_URL", API + "/")


def sample(store="temperature.ops.example.ifdd.de", value=21.5, minute=0):
    return {
        "store": store,
        "name": "temperature",
        "ifdd_id": "https://rest.test/products/1",
        "ifdd_property": "https://type.test/v1/climate.ops.example.ifdd.de/temperature",
        "ifdd_unit": "https://unit.test/v1/unit/DEG_C",
        "time": f"2026-10-22T07:{minute:02d}:00+00:00",
        "value": value,
    }


def post(records, ctx, step="ts-post"):
    return run_steps(step, records=records, ctx=ctx)


def test_samples_go_per_store_to_the_batch_endpoint(http_ctx):
    session = FakeSession()
    records = [sample(minute=0), sample(store="humidity.ops.example.ifdd.de"), sample(minute=15)]
    result, printed = post(records, http_ctx(session))
    assert result == records and printed == ""
    calls = session.requests()
    assert [(c.method, c.url) for c in calls] == [
        ("POST", f"{API}/stores/temperature.ops.example.ifdd.de/samples/batch"),
        ("POST", f"{API}/stores/humidity.ops.example.ifdd.de/samples/batch"),
    ]
    first = calls[0].json["samples"]
    assert [s["time"] for s in first] == ["2026-10-22T07:00:00+00:00", "2026-10-22T07:15:00+00:00"]
    assert "store" not in first[0]
    assert calls[0].headers["Content-Type"] == "application/json"


def test_lists_are_split_at_batch(http_ctx):
    session = FakeSession()
    post([sample(minute=m) for m in range(5)], http_ctx(session), step="ts-post:batch=2")
    assert [len(c.json["samples"]) for c in session.requests()] == [2, 2, 1]


def test_token_of_the_client_is_sent(http_ctx, with_auth):
    session = FakeSession()
    post([sample()], http_ctx(session))
    assert session.token_requests()
    assert session.requests()[0].headers["Authorization"] == "Bearer t1"


def test_refused_lists_are_reported_after_all_were_sent(http_ctx, caplog):
    session = FakeSession(Response(422, {"detail": "samples[0]: bad unit"}), Response(200))
    records = [sample(), sample(store="humidity.ops.example.ifdd.de")]
    with pytest.raises(CtError, match="1 of 2 samples were refused"):
        post(records, http_ctx(session))
    assert len(session.requests()) == 2
    assert "bad unit" in caplog.text


def test_dry_run_sends_nothing(http_ctx, caplog):
    session = FakeSession()
    post([sample(), sample()], http_ctx(session), step="ts-post:dry_run=true")
    assert session.calls == []
    assert f"dry run: POST {API}/stores/temperature.ops.example.ifdd.de/samples/batch (2 samples)" \
        in caplog.text


@pytest.mark.parametrize(
    "record, message",
    [
        ({"name": "x"}, "record 0 has no store"),
        ("text", "record 0 has no store"),
        ({"store": "a.b", "name": "x"}, "record 0 lacks ifdd_id, ifdd_property, ifdd_unit, time, value"),
    ],
)
def test_incomplete_records(http_ctx, record, message):
    session = FakeSession()
    with pytest.raises(CtError, match=message):
        post([record], http_ctx(session))
    assert session.calls == []


def test_needs_the_url_and_a_positive_batch(http_ctx, monkeypatch):
    with pytest.raises(UsageError, match="batch >= 1"):
        post([sample()], http_ctx(FakeSession()), step="ts-post:batch=0")
    monkeypatch.delenv("IFDD_CT_TS_API_URL")
    with pytest.raises(UsageError, match="IFDD_CT_TS_API_URL"):
        post([sample()], http_ctx(FakeSession()))


def test_climate_samples_can_be_posted(http_ctx, monkeypatch):
    monkeypatch.setenv("IFDD_CT_TYPE_URL", "https://type.test/v1")
    breaker = {"@id": "https://rest.test/products/1",
               "@context": "https://schema.test/v1/breaker.grid.example.ifdd.de.jsonld"}
    session = FakeSession()
    run_steps("ts-climate:days=1,end=2026-10-22T00:00:00Z", "ts-post",
              records=[breaker], ctx=http_ctx(session))
    assert [len(c.json["samples"]) for c in session.requests()] == [96, 96]

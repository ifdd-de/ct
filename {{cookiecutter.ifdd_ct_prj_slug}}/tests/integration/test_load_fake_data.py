"""Load energy-grid fake data into a running ifdd-be (see conftest.py)."""

import io
import logging
import re
from pathlib import Path

import pytest
from support import run_steps
from support.runner import Terminal

from ifdd.ct.errors import CtError
from ifdd.ct.pipeline import load_pipeline, run

PIPELINE = Path(__file__).resolve().parents[2] / "data" / "pipelines" / "generate-energy-grid.yaml"

# Small and fixed: the same documents on every run.
FAKER = "faker:profile=energy-grid,seed=20261005,product=2,function=2,location=1,organisation=1"


def _put_answers(caplog):
    """'<status> <message>' the backend gave for every PUT, from ct's log."""
    found = [re.search(r"-> (\d{3}) (.*)$", r.getMessage()) for r in caplog.records
             if r.getMessage().startswith("PUT ")]
    return [f"{m.group(1)} {m.group(2)}" for m in found if m]


def test_generated_documents_fit_the_schema(backend):
    run_steps(FAKER, "check:fail=true")


def test_load_and_read_back(backend):
    generated, _ = run_steps(FAKER, "check:fail=true", "put")
    for doc_id in sorted({d["@id"] for d in generated}):
        fetched, _ = run_steps(f"get:id={doc_id}")
        assert fetched[0]["@id"] == doc_id


def test_loading_again_changes_nothing(backend, caplog):
    """Earlier versions included: they end where the current version starts,
    so neither cuts into the other on a second run. (Skipped up to
    ifdd-be-core 26.10.2, which stored a spurious version on the second PUT.)"""
    run_steps(FAKER, "put")
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="ifdd.ct"):
        generated, _ = run_steps(FAKER, "put")
    answers = _put_answers(caplog)
    assert len(answers) == len(generated)
    assert set(answers) == {"200 No changes detected"}


def test_the_pipeline_file_of_the_instance(backend):
    """What ./adm_02_run.sh -f pipelines/generate-energy-grid.yaml runs."""
    steps = load_pipeline(PIPELINE)
    assert [s.plugin.name for s in steps] == ["faker", "check", "put"]
    records = run(steps, stdin=Terminal(), stdout=io.StringIO())
    assert records


def test_wrong_client_secret(backend, monkeypatch):
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", "wrong")
    with pytest.raises(CtError, match="token request failed: 401"):
        run_steps(FAKER, "put")


def test_without_a_token_the_backend_refuses(backend, monkeypatch):
    monkeypatch.delenv("IFDD_CT_OIDC_CLIENT_ID")
    with pytest.raises(CtError, match="records failed"):
        run_steps(FAKER, "put")


def test_a_client_without_the_write_role_is_refused(readonly_client, caplog):
    with caplog.at_level(logging.ERROR, logger="ifdd.ct"), \
            pytest.raises(CtError, match="records failed"):
        run_steps(FAKER, "put")
    assert caplog.records and all(" -> 403 " in r.getMessage() for r in caplog.records
                                  if r.getMessage().startswith("PUT "))


# --- bitemporal storage of ifdd-be-core -------------------------------------------

PLANNED_ID = "products/00000000-0000-4000-8000-000000002099"


def test_earlier_versions_stay_readable_at_their_time(backend):
    generated, _ = run_steps(FAKER, "put")
    # the domain contexts have no description
    earlier = [d for d in generated if "c_validNotAfter" in d and "description" in d]
    assert earlier, "the fixed seed is expected to give some changed entities"
    for doc in earlier:
        prefix = doc["@context"].rsplit("/", 1)[-1].removesuffix(".jsonld")
        then, _ = run_steps(f"get:id={doc['@id']},at={doc['c_validNotBefore']}")
        now, _ = run_steps(f"get:id={doc['@id']}")
        assert then[0][f"{prefix}:description"] == doc["description"]
        assert now[0][f"{prefix}:description"] != doc["description"]


def test_a_planned_version_is_seen_only_at_its_time(backend):
    doc_id = f"{backend}/{PLANNED_ID}"
    context = f"{_schema(backend)}/product.jsonld"
    today = {"@context": context, "@id": doc_id, "objName": "today",
             "c_validNotBefore": "2020-01-01T00:00:00Z"}
    planned = {**today, "objName": "planned", "c_validNotBefore": "2099-01-01T00:00:00Z"}
    run_steps("put", records=[today, planned])
    now, _ = run_steps(f"get:id={doc_id}")
    later, _ = run_steps(f"get:id={doc_id},at=2099-06-01T00:00:00Z")
    assert now[0]["product:objName"] == "today"
    assert later[0]["product:objName"] == "planned"


def test_lists_carry_the_cache_metadata(backend):
    """Backend terms on every entry, the source terms where the source sent them."""
    generated, _ = run_steps(FAKER, "put")
    faked = {d["@id"] for d in generated if "/products/" in d["@id"]}
    fetched, _ = run_steps("get:segment=products,end=1000")
    assert faked <= {d["@id"] for d in fetched}
    for doc in fetched:
        assert {"c_validNotBefore", "c_cacheCreated", "c_cacheUpdated"} <= set(doc)
        if doc["@id"] in faked:
            assert {"c_created", "c_modified"} <= set(doc)


# --- context access: domain contexts need a context pattern ------------------------

BREAKER = "breaker.grid.example.ifdd.de"
BREAKER_ID = "products/00000000-0000-4000-8000-00000000b001"


def test_a_domain_context_needs_a_context_pattern(backend, nopattern_client, monkeypatch):
    """The write client (pattern of the root) sees the domain context, a client
    with the read role but no pattern sees the product without it
    (ifdd-be-core "Contexts and access")."""
    doc_id = f"{backend}/{BREAKER_ID}"
    product = {"@context": f"{_schema(backend)}/product.jsonld", "@id": doc_id,
               "objName": "Breaker B001", "objType": "Circuit Breaker"}
    breaker = {"@context": f"{_schema(backend)}/{BREAKER}.jsonld", "@id": doc_id,
               "objName": "Q1", "serialNumber": "SN-B001"}
    run_steps("put", records=[product, breaker])
    mine, _ = run_steps(f"get:id={doc_id}")
    assert mine[0][f"{BREAKER}:serialNumber"] == "SN-B001"
    assert BREAKER in mine[0]["@context"]

    nopattern_client(monkeypatch, "NOPATTERN")
    theirs, _ = run_steps(f"get:id={doc_id}")
    assert theirs[0]["product:objName"] == "Breaker B001"
    assert not any(key.startswith(BREAKER) for key in theirs[0])
    assert BREAKER not in theirs[0]["@context"]


def _schema(backend):
    import os

    return os.environ["IFDD_CT_SCHEMA_URL"]

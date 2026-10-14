"""End to end over real HTTP: token, PUT/PATCH/GET against a local fake backend."""

import pytest
from support import run_steps

from ifdd.ct.errors import CtError

SMALL = "product=2,function=2,location=1,organisation=2"


def test_load_the_examples(backend):
    run_steps("data/examples/json-ld", "put")
    assert backend.statuses("PUT") == [201] * 30
    assert backend.statuses("POST") == [200]          # one token for the whole run


def test_loading_again_changes_nothing(backend):
    run_steps("data/examples/json-ld", "put")
    run_steps("data/examples/json-ld", "put")
    assert backend.statuses("PUT")[30:] == [200] * 30
    assert len(backend.store) == 30


def test_generated_data_can_be_fetched_back(backend):
    generated, _ = run_steps(f"faker:seed=3,{SMALL}", "put")
    fetched, _ = run_steps("get:segment=products")
    expected = {d["@id"] for d in generated if d["@context"].endswith("/product.jsonld")}
    assert sorted(d["@id"] for d in fetched) == sorted(expected)  # one per document


def test_cache_metadata_is_not_stored(backend):
    run_steps(f"faker:seed=3,{SMALL}", "put")
    assert not [k for doc in backend.store.values() for k in doc if k.startswith("c_")]


def test_get_passes_an_instant_on(backend):
    run_steps(f"faker:seed=3,{SMALL}", "put")
    run_steps("get:segment=products,at=2030-01-01T00:00:00Z")
    gets = [path for method, path, _ in backend.log if method == "GET"]
    assert gets[-1].endswith("at=2030-01-01T00%3A00%3A00Z")


def test_get_one_node(backend):
    generated, _ = run_steps(f"faker:seed=3,{SMALL}", "put")
    target = generated[1]
    fetched, _ = run_steps(f"get:id={target['@id']}")
    assert fetched[0]["@id"] == target["@id"]


def test_patch_changes_an_existing_node(backend):
    run_steps("data/examples/json-ld/products", "put")
    documents, _ = run_steps("data/examples/json-ld/products", "head:count=1")
    run_steps("patch", records=[{**documents[0], "name": "renamed"}])
    assert backend.statuses("PATCH") == [200]
    key = (documents[0]["@id"], documents[0]["@context"])
    assert backend.store[key]["name"] == "renamed"


def test_patch_of_a_missing_node_fails(backend):
    documents, _ = run_steps("data/examples/json-ld/products", "head:count=1")
    with pytest.raises(CtError, match="PATCH: 1 of 1 records failed"):
        run_steps("patch", records=documents)


def test_wrong_client_secret(backend, monkeypatch):
    monkeypatch.setenv("IFDD_CT_OIDC_CLIENT_SECRET", "wrong")
    with pytest.raises(CtError, match="token request failed: 401"):
        run_steps("data/examples/json-ld/products", "put")
    assert backend.store == {}


def test_without_credentials_the_backend_refuses(backend, monkeypatch):
    monkeypatch.delenv("IFDD_CT_OIDC_CLIENT_ID")
    with pytest.raises(CtError, match="PUT: 4 of 4 records failed"):
        run_steps("data/examples/json-ld/products", "put")
    assert backend.statuses("PUT") == [401] * 4


def test_example_pipeline_file(backend, monkeypatch):
    from ifdd.ct.pipeline import load_pipeline, run
    from support.runner import Terminal

    monkeypatch.chdir("data")  # the container's working directory is /data
    run(load_pipeline("pipelines/load-examples.yaml"), stdin=Terminal())
    assert len(backend.store) == 30


def test_unreachable_backend(monkeypatch):
    monkeypatch.setenv("IFDD_CT_BE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("IFDD_CT_HTTP_TIMEOUT", "2")
    with pytest.raises(CtError, match="PUT http://127.0.0.1:9/products/.* failed"):
        run_steps("data/examples/json-ld/products", "put")

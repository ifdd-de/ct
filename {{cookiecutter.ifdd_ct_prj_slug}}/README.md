# {{ cookiecutter.ifdd_ct_prj_name }} - IFDD Core Tools

`ifdd-ct` chains small plugins over JSON-LD records: read or generate
documents, transform them, load them into the IFDD backend. Generated from
the `ifdd-de/ct` template, version {{ cookiecutter.ifdd_ct_version }}.

## Quick start

```bash
# .env: set IFDD_CT_OIDC_CLIENT_SECRET (from the keycloak instance)
./adm_01_build.sh                                       # or pull the image
./adm_02_run.sh --list                                  # what is there
./adm_02_run.sh examples/json-ld check put:dry_run=true # try without writing
./adm_02_run.sh -f pipelines/generate-energy-grid.yaml  # load generated data
```

## Documentation

Setup, build and release, operations, security, troubleshooting, reference
and pipelines (steps, pipeline files, faker profiles, writing plugins) of
this instance:

- English: [docs/en/index.md](docs/en/index.md)
- Deutsch: [docs/de/index.md](docs/de/index.md)

The pages are Sphinx sources in MyST Markdown, meant to be copied into a
documentation project that covers all services; GitHub shows them as plain
Markdown.

## Honesty notes

Loading fake data (2026-10-05), checked without Docker: PostgreSQL 16, the
Keycloak 26.8.0 distribution (`start-dev`) with the realm of the keycloak
template, ifdd-be-core 26.10.2 started with uvicorn, the contents of the
schema template served over HTTP, and `tests/integration` against them: the
documents fit the schema, are written and read back, the pipeline file runs,
a wrong secret and a missing token are refused, and a client without the
write role gets 403. The run found two problems: `containedIn` was missing in
`product.jsonld` (fixed in the schema template), and the second load of
unchanged documents stores new versions (ifdd-be-core, see *Loading fake
data*). Not checked: the integration job of `template-test.yml` itself (it
needs GitHub Actions and Docker; `actionlint` reports nothing), the image,
and the path through the proxy with TLS.

Bitemporal backend (2026-10-06, second round), checked without Docker:
PostgreSQL 18.4 (zonky binaries from npm), the Keycloak 26.8.0 distribution
(`start-dev`) with the realm of the keycloak template, ifdd-be-core with
be-core-3/-4 under uvicorn, the schema template contents (schemaVersion
0.10.0) over `python -m http.server`: `tests/integration` 10 passed, twice
on the same database (the second run finds every document unchanged,
earlier versions included). The faker output (seed 42, the pipeline counts)
passes `check` against the rendered schemas: 246 documents, 22 of them
earlier versions. The example documents use the schema terms now (`objName`,
`objScope`, `c_created`, `c_modified`); before, all 30 failed `check`, now 4
organisations still use `hasPart`/`isPartOf`, which the organisation schema
does not define (not changed here). The new unit tests fail against the
previous faker and `get`. Not checked: the CI integration job itself and
the image.

Domain contexts (2026-10-12), checked without Docker: PostgreSQL 18.4, the
Keycloak 26.8.0 distribution with the realm of the keycloak template
(keycloak-4: `ifdd-ct` holds the root pattern `ifdd.de`), ifdd-be-core with
be-core-5 and auth on, the schema template contents with the two example
domain contexts over `python -m http.server`: `tests/integration` 11
passed. The new test reads a product with a breaker document as `ifdd-ct`
(sees it) and as a client with the read role but no context pattern
(created with `keycloak_add_client.py`; sees the product without it); it
fails against the previous ifdd-be-core. The pipeline (seed 42) gives 280
documents, 34 of them in the domain contexts (15 breakers), and passes
`check` against the rendered schemas. The fake backend of the tests now
lists only the aspect context of a segment, as ifdd-be does. Not checked:
the CI integration job, which has no client without a pattern (the new test
is skipped there), and the image.

Plugin reference and running in a shell (2026-10-13), checked without Docker
on Python 3.14.6: the tests pass (422 passed, 11 skipped, coverage about 97 %) for
both fixtures of the template and its `cookiecutter_all.yaml`. Against the
previous state, `tests/cli/test_markdown.py` cannot be imported and 15 of
the 18 tests in `tests/core/test_parameter_help.py` fail (the other three
check what stays the same). The page of `--markdown` builds with Sphinx
9.1.0 and myst-parser 5.1.0 with `-W`. The steps of "Running locally in a
shell" (setup chapter) ran in bash 5.2.21 with a fresh venv: install,
loading `.env`, `--list`, `--describe`, `--markdown`, `faker`, and
`examples/json-ld check put:dry_run=true` with local contexts. Not checked:
`--markdown` in the image and through `adm_02_run.sh`, the CI steps, and
reaching the services from the host.

Python 3.13 (2026-10-13): with `requires-python >=3.13`, `requirements.txt`
installs with hash checking on Python 3.13.16, and the tests pass there
(422 passed, 11 skipped). Not checked: the image on 3.13 (it stays on 3.14).

Coverage (2026-10-14): 446 passed, 11 skipped, line and branch coverage
100 % on Python 3.14.6 and 3.13.16 for the instance rendered with
`cookiecutter_all.yaml`. The new tests describe behaviour that was already
there, so they pass against the previous code too; spot checks with five
deliberate faults (29 February, stdin without `isatty`, error body, failing
annotations, version fallback) each make a test fail.

## License

BSD-3-Clause, see `LICENSE`.

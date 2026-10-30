# Changelog

## [26.10.3] - 2026-10-30

- `ifdd_ct_version` 26.10.3.
- Lower bounds in `pyproject.toml` raised to the current releases (e.g. Faker
  40.44, requests 2.34.2, PyYAML 6.0.3, SQLAlchemy 2.1.6, Pint 0.26.2,
  networkx 3.7; development: pytest 9.2, pytest-cov 7.1); `requirements.txt`
  of the image compiled again with `uv pip compile --upgrade` (Faker 40.44.0,
  SQLAlchemy 2.1.6, Pint 0.26.2, cachetools 7.2.7, certifi 2026.10.23 and
  others).
- CI: Keycloak 26.8.1 for the integration tests (was 26.8.0).
- Documentation check: Sphinx 9.2.0 (`tests/docs/requirements.txt`).

- New plugins `ts-climate` (example samples of temperature and relative
  humidity for the circuit breakers of the faker profile `energy-grid`) and
  `ts-post` (writes sample records to ts-api, per store in lists), module
  `ifdd.ct.plugins.timeseries`; pipeline `data/pipelines/generate-time-series.yaml`.
- New shared variable `ifdd_ts_api_url` (`IFDD_CT_TS_API_URL`), checked by the
  pre-generation hook. `.env` and `data/` are on the skip list: existing
  instances add `IFDD_CT_TS_API_URL` to `.env` and copy the pipeline by hand.
- `IFDD_CT_TYPE_URL` is used now (base of the property IRIs of `ts-climate`).

## [26.10.2] - 2026-10-14

- `ifdd-ct --markdown`, parameter help texts with `Annotated`, `.env`
  loadable by a shell and the documentation of running ct in a shell (see
  the instance CHANGELOG).
- The pre-generation hook rejects a single quote in `ifdd_be_aspects`
  (`.env` holds the value in single quotes).
- Template CI: sources the rendered `.env` and checks the JSON, checks that
  the hook rejects a single quote, builds the page of `ifdd-ct --markdown`
  with Sphinx (`-W`, without `tests/docs/conf.py`, so broken links fail) and
  runs `--markdown` in the image.
- Documentation of the instance in `docs/en` and `docs/de` (see the instance
  CHANGELOG). Template CI: `tests/check_docs.py` checks that both languages
  match and build without warnings (`tests/docs/conf.py`,
  `tests/docs/requirements.txt`).

## [26.10.1] - 2026-10

First release of the template `ifdd-de/ct`. See the instance CHANGELOG
(`{{cookiecutter.ifdd_ct_prj_slug}}/CHANGELOG.md`) for the content.

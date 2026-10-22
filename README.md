# ifdd-de/ct - Core Tools template

Cookiecutter/cruft template for an IFDD Core Tools instance: a container with
the `ifdd-ct` CLI, which chains plugins over JSON-LD records - read or generate
documents, transform them, load them into ifdd-be.

The generated instance's documentation (`docs/`, see below) is the user
documentation; this file covers the template.

## Create an instance

```bash
cruft create --checkout v26.10.1 https://github.com/ifdd-de/ct
# or with the organisation's meta file
cruft create --no-input --config-file cookiecutter_all.yaml --checkout v26.10.1 https://github.com/ifdd-de/ct
```

## Variables

| Variable | Default | Used for |
|---|---|---|
| `ifdd_ct_prj_name` | `CT` | display name |
| `ifdd_ct_prj_slug` | from the name | directory, image name |
| `ifdd_ct_version` | `26.10.1` | package version, image tag |
| `ifdd_ct_log_level` | `WARNING` | `IFDD_CT_LOG_LEVEL` |
| `ifdd_be_url` | `https://rest` | `IFDD_CT_BE_URL`, `@id`s of example and generated data |
| `ifdd_be_aspects` | products/functions/locations/organisations | `IFDD_CT_ASPECTS` |
| `ifdd_schema_url` | `https://schema/v1` | `IFDD_CT_SCHEMA_URL`, contexts of example data |
| `ifdd_type_url` | `https://type/v1` | `IFDD_CT_TYPE_URL` |
| `ifdd_unit_url` | `https://unit/v1` | `IFDD_CT_UNIT_URL` |
| `ifdd_ts_api_url` | `https://ts/tsapi` | `IFDD_CT_TS_API_URL` (plugin `ts-post`) |
| `ifdd_oidc_token_url` | placeholder | `IFDD_CT_OIDC_TOKEN_URL` |
| `ifdd_keycloak_ct_client_id` | `ifdd-ct` | `IFDD_CT_OIDC_CLIENT_ID`; the same variable names the client in the keycloak template |
| `ifdd_proxy_network` | `proxy-net` | external Docker network |
| `ifdd_registry_url` | `ghcr.io/ifdd-de` | image name in compose and build script |

All of them except `ifdd_ct_version` already exist in the organisation's
`cookiecutter_all.yaml` under these names (shared with be, schema, type,
unit and proxy). Add `ifdd_ct_version: 26.10.1` there if the version should
come from the meta file as well.

The client secret is deliberately not a template variable: copy
`IFDD_KEYCLOAK_CT_CLIENT_SECRET` from the `.env` of the keycloak instance into
`IFDD_CT_OIDC_CLIENT_SECRET` of this instance's `.env`. Up to 26.10.1 the
post-generation hook made up a random client id and secret, which no realm
knew.

## What the instance owns

`private/`, `plugins/`, `data/`, `certs/` and `.env` are on the cruft skip
list (`[tool.cruft]` in the instance's `pyproject.toml`). Template updates
never touch them. Everything else - CLI, built-in plugins, faker profiles,
Dockerfile, compose files - comes from the template and is updated with
`cruft update`.

## Documentation of the instance (`docs/`)

Every instance carries its operating documentation as Sphinx sources in
MyST Markdown, in English (`docs/en`) and German (`docs/de`), with the same
files, labels and headings in both. The pages follow the work around the
service: `index` (purpose, architecture), `setup`, `build-release`,
`operations`, `security`, `troubleshooting`, `reference`, plus `pipelines`
(steps, pipeline files, `check`, faker profiles, writing plugins).
cookiecutter fills in the values of the instance. The instance README is
only an entry point that links to them; `docs` is in `.dockerignore`.

The pages have no `conf.py` of their own: they are meant to be copied into a
Sphinx project that documents all services. That project needs `myst_parser`
and `sphinxcontrib.mermaid`. Labels start with `ifdd-ct-`; references to
`ifdd-instances-ct` (the instance chapter of the meta repository) resolve
only there.

Rules for editing the pages in the template:

- change both languages in the same commit;
- no Jinja syntax in examples (`{{`, `{%`, `{#`); wrap such text in
  `{% raw %}`;
- the placeholder check of the CI greps the rendered instance for the text
  `cookiecutter` followed by a dot; do not write it literally.

`tests/check_docs.py` checks a rendered instance: same files, labels and
headings per level in both languages, every label with the prefix, every
reference to an own label resolvable, and a Sphinx build of each language
with `-W` (configuration `tests/docs/conf.py`, versions
`tests/docs/requirements.txt`).

## Checks

* `template-test.yml` renders the fixtures in `tests/fixtures/`, checks that
  no placeholder and no legacy name is left and that the client id comes from
  the template, that a shell can source the rendered `.env` and that the
  hook rejects a single quote in `ifdd_be_aspects`, runs the instance tests,
  checks and builds the documentation (`tests/check_docs.py`), builds the
  page of `ifdd-ct --markdown` with Sphinx, builds the image (also running
  `--markdown` in it) and validates the compose files. Its `integration` job renders the keycloak, schema and ct
  templates with `tests/integration/stack.yaml`, starts PostgreSQL, Keycloak
  with the generated realm, the backend from `ifdd-de/be-core` and the schema
  contents, and runs the instance's `tests/integration` against them. It
  checks out `ifdd-de/be-core`, `ifdd-de/keycloak` and `ifdd-de/schema` and
  needs read access to them while they are private.
* `template-update-test.yml` generates an instance from the latest tag and
  applies the current template with `cruft update`; it fails on `.rej` files.
* Generated instances inherit `ci.yml` (tests, image, compose, cruft drift)
  and `release.yml` (image to ghcr.io on a `v*` tag).

## Honesty notes

The tests of the instance content are described in the honesty notes of the
instance README.

Documentation `docs/` (2026-10-13): rendered with cookiecutter 2.7.1 for
both fixtures and with the `cookiecutter_all.yaml` of the meta repository;
`tests/check_docs.py` passes for each (Sphinx 9.1.0, myst-parser 5.1.0,
sphinxcontrib-mermaid 2.1.1, on Python 3.13 and 3.14.6) and the placeholder
check finds nothing. The workflow file passes actionlint 1.7.12; the
workflow itself has not run. Content: taken from the previous instance
README, `dotenv.dist`, the compose files, the `Dockerfile` and the
workflows. Also checked (2026-10-13): one Sphinx project per language with
the pages of all ten service templates (rendered with `cookiecutter_all.yaml`),
the instance chapter of the meta repository and ifdd-be-core with its
OpenAPI document builds with `-W` and no suppressed warnings, so every cross
reference resolves; the Mermaid diagrams of all services, and of the option
variants of the fixtures, render in headless Chromium 141.0.7390.37
(Playwright 1.56.0, Mermaid 11.12.1 served locally).

`.env` loadable by a shell and the plugin reference (2026-10-13): rendered
with cookiecutter 2.7.1 for both fixtures and with `cookiecutter_all.yaml`.
`set -a; . ./.env; set +a` in bash 5.2.21 leaves valid JSON in
`IFDD_CT_ASPECTS` (before: `product,: command not found`, empty value);
`docker compose config` (v5.5.1) reads the same value with and without the
quotes; the hook rejects a single quote. Both checks fail against the
previous template. The page of `ifdd-ct --markdown` builds with Sphinx 9.1.0
and myst-parser 5.1.0 with `-W` for each rendered instance, and inside the
full documentation of all services in en and de; a broken label fails that
build. The workflow files pass actionlint 1.7.12; they have not run.

## Related

`ifdd-de/tools-fakedata` is superseded by the `faker` plugin of this template
and is to be archived.

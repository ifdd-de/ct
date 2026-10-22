(ifdd-ct-reference)=
# Reference

The variables of the template and their values in this instance are listed
in {ref}`ifdd-instances-ct`. This page lists what is not a template
variable.

## Command line

```text
ifdd-ct [-v|-vv|-q] STEP [STEP ...]
ifdd-ct [-v|-vv|-q] -f PIPELINE.yaml
ifdd-ct --list | --describe PLUGIN | --markdown | --version
```

| Step | Meaning |
|---|---|
| `name` | run a plugin |
| `name:key=value,key2=value2` | with parameters; a `,` inside a value is written `%2C` |
| `path/file.json` (`.jsonld`, `.yaml`) | first step: read it; last step: write it |
| `path/directory` | first step: read every `.json`/`.jsonld`/`.yaml` below it |

Exit codes: `0` ok, `1` a step failed, `2` wrong command line or pipeline
file.

## Built-in plugins

| Plugin | Role | Purpose |
|---|---|---|
| `faker` | source | generate documents from a profile (`profile=`, `seed=`, counts per type) |
| `get` | source | fetch documents from the backend (`segment=products` or `id=...`; `at=` an instant in valid time, default now) |
| `put` | sink | create or replace nodes: PUT to backend + path of `@id` |
| `patch` | sink | merge into existing nodes: PATCH to backend + path of `@id` |
| `post` | sink | POST to `/nodes/` (prefer `put`) |
| `node` | | wrap documents in the backend envelope, to see what would be sent |
| `check` | | report terms the `@context` does not define (warns; `fail=true` stops) |
| `expand`, `compact` | | JSON-LD expansion and compaction |
| `head`, `tail` | | keep the first/last `count` records |
| `where` | | keep records whose `key` equals `value` |
| `count` | | print the number of records to standard error |
| `stdout` | sink | print the records between two steps |

`ifdd-ct --describe NAME` shows parameters, types, defaults and help
texts; `ifdd-ct --markdown` all plugins at once (below). `put`, `patch` and
`post` accept `dry_run=true`.

## Plugin reference as Markdown

`ifdd-ct --markdown` writes one MyST Markdown page to standard output: the
`--help` text and, for every plugin found, its origin and module, its role,
the names it answers to, how to call it, its docstring, a table of its
parameters (type, default, help text) and generated details such as the
faker profiles. Modules that failed to load are listed at the end.

```bash
./adm_02_run.sh --markdown > plugins.md            # built-in, private and local plugins
ifdd-ct --markdown > plugins.md                    # in a shell, see the setup chapter
IFDD_CT_PLUGIN_PATH= ifdd-ct --markdown > plugins.md   # without the local plugins
```

The page has the label `ifdd-ct-plugins`, each plugin the label
`ifdd-ct-plugin-<origin>-<name>`, for example `ifdd-ct-plugin-builtin-faker`.
Copied into the documentation project and added to a toctree, it can be
linked with `{ref}`. It is generated, in English only, and not part of the
repository: generate it again after a plugin changes. Its text comes from
the plugins themselves ({ref}`ifdd-ct-pipelines`, "Writing plugins").

```{note}
Not tested: `./adm_02_run.sh --markdown` with Docker. Checked: the page
from a shell builds with Sphinx 9.1.0 and myst-parser 5.1.0 without a
warning.
```

## Plugin locations

| Directory | Name | In the container |
|---|---|---|
| built-in | `builtin.<name>` | in the package |
| `private/` | `private.<name>` | `/opt/ifdd-ct/private`, built into the image |
| `plugins/` | `local.<name>` | `/plugins`, mounted read-only at run time |

## Environment (`.env`)

| Variable | Default here | Used by | Meaning |
|---|---|---|---|
| `IFDD_CT_LOG_LEVEL` | `{{ cookiecutter.ifdd_ct_log_level|upper }}` | all | log level without `-v`/`-q` |
| `IFDD_CT_BE_URL` | `{{ cookiecutter.ifdd_be_url }}` | backend, faker | backend base URL; also the base of generated `@id`s; required |
| `IFDD_CT_SCHEMA_URL` | `{{ cookiecutter.ifdd_schema_url }}` | faker `energy-grid` | base of the context URLs |
| `IFDD_CT_UNIT_URL` | `{{ cookiecutter.ifdd_unit_url }}` | faker `energy-grid` | base of the unit IRIs in quantity values |
| `IFDD_CT_TYPE_URL` | `{{ cookiecutter.ifdd_type_url }}` | `ts-climate` | base of the property IRIs of the example samples |
| `IFDD_CT_TS_API_URL` | `{{ cookiecutter.ifdd_ts_api_url }}` | `ts-post` | time series API (ts-api) |
| `IFDD_CT_ASPECTS` | `{{ cookiecutter.ifdd_be_aspects }}` | backend | JSON: path segment -> aspect |
| `IFDD_CT_OIDC_TOKEN_URL` | `{{ cookiecutter.ifdd_oidc_token_url }}` | backend | token endpoint |
| `IFDD_CT_OIDC_CLIENT_ID` | `{{ cookiecutter.ifdd_keycloak_ct_client_id }}` | backend | client; empty for a backend without authentication |
| `IFDD_CT_OIDC_CLIENT_SECRET` | empty | backend | client secret, set by hand |
| `IFDD_CT_CA_BUNDLE` | `/certs/ca.crt` | all HTTP | PEM file with the internal CA; empty: system trust store |
| `IFDD_CT_HTTP_TIMEOUT` | `30` | all HTTP | seconds per request |
| `IFDD_CT_CONTEXT_DIR` | empty | expand, compact, node | local JSON-LD contexts, by file name |
| `IFDD_CT_UID`, `IFDD_CT_GID` | `1000` | compose | user and group the container runs as |

Set in the image, not in `.env`: `IFDD_CT_PRIVATE_DIR=/opt/ifdd-ct/private`
and `IFDD_CT_PLUGIN_PATH=/plugins` (`:`-separated). In a shell, set them
yourself ({ref}`ifdd-ct-setup`).

## Mounts

| Host | Container | |
|---|---|---|
| `data/` | `/data` (working directory) | read-write |
| `plugins/` | `/plugins` | read-only |
| `certs/` | `/certs` | read-only |
| `src/`, `private/` | `/opt/ifdd-ct/src`, `/opt/ifdd-ct/private` | read-only, development only |

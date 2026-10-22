# Changelog

## [Unreleased]

- Plugins `ts-climate` and `ts-post`, pipeline `generate-time-series.yaml`,
  setting `IFDD_CT_TS_API_URL` (see the template CHANGELOG). Documentation:
  `pipelines` (loading example time series), `reference`.

## [26.10.2] - 2026-10-14

Tests and coverage:

- Tests: line and branch coverage of `ifdd.ct` is 100 % (was 97 %): new tests
  for `python -m ifdd.ct` in-process, the version of an uninstalled source
  tree, unexpected errors with `-vv`, plugins without docstring, unresolvable
  annotations, `*args`, unions without `None`, a module name in two plugin
  directories, the reuse of the remote context loader, compaction errors and
  inline contexts, non-object error bodies, stdin without `isatty`, racks
  without rooms, all kinds of functions and 29 February in the faker. Four
  defensive or version-dependent lines carry `pragma: no cover`/`no branch`
  with the reason. `fail_under` is 95 (was 75).
- `--markdown`: sets `color = False` on the parser unconditionally (older
  Pythons ignore it), so there is no version-dependent branch.

Python 3.13:

- `requires-python >=3.13` (was 3.14). The image stays on
  `python:3.14-slim`; `requirements.txt` is still resolved for 3.14 and
  installs on 3.13 too. Documentation (setup, build and release) names 3.13
  as the lowest version.

Plugin documentation:

- `ifdd-ct --markdown` prints the `--help` text and every plugin found
  (built-in, private, local) as one MyST Markdown page for Sphinx: origin,
  module, role, addresses, call syntax, docstring, parameter table and
  `describe_extra`; modules that failed to load are listed. Labels
  `ifdd-ct-plugins` and `ifdd-ct-plugin-<origin>-<name>`. Fixed width and no
  colour, so the output does not depend on the terminal (`markdown.py`).
- Parameters can carry a help text: `typing.Annotated[type, "help"]`. The
  registry takes the type from the first argument (conversion unchanged) and
  the first string as help; `--describe` shows it. Every parameter of the
  built-in plugins and of `plugins/example_stamp.py` has one; the parameter
  lines moved from the docstrings of `faker`, `get` and `check` into them.
- Tests: `tests/cli/test_markdown.py`, `tests/core/test_parameter_help.py`.
  CI builds the image and checks `--markdown` there too.

Running without Docker:

- `.env`: `IFDD_CT_ASPECTS` in single quotes, so that a shell can source the
  file (`set -a; . ./.env; set +a`); unquoted, the shell broke the JSON at
  its spaces. docker compose reads the same value. `.env` belongs to the
  instance: existing instances add the quotes by hand.
- Documentation: setup, "Running locally in a shell" (loading `.env`, the CA
  bundle and the plugin directories outside the container, step by step);
  reference, `--markdown`; pipelines, help texts with `Annotated`.

Documentation:

- `docs/en` and `docs/de` (Sphinx sources, MyST Markdown): index, setup,
  build and release, operations, security, troubleshooting, reference,
  pipelines. The README is now an entry point with a quick start, the links,
  the honesty notes and the license; its former sections moved into the
  documentation.
- `docs` in `.dockerignore`, `docs/_build/` in `.gitignore`.

Context access of ifdd-be-core (domain contexts):

- Faker `energy-grid`: circuit breakers get a document in each example
  domain context (`breaker.grid.example.ifdd.de`,
  `maintenance.ops.example.ifdd.de`) with their own source values; rated
  voltage and current are QUDT quantity values with unit IRIs of the unit
  service. The profile now needs `IFDD_CT_UNIT_URL`. Generic engine:
  `Entity.add_namespace`, `Entity.namespaces`; earlier versions and their
  times cover every namespace of an entity.
- Integration tests: optional `IFDD_IT_NOPATTERN_CLIENT_ID/SECRET`, a client
  with the read role but no context pattern; it must not see a domain
  context.
- The same seed gives other data than before (more random draws).

For the bitemporal storage of ifdd-be-core and the c_* terms of the schemas
(`schemaVersion` 0.10.0):

- Faker `energy-grid`: `c_created`, `c_modified`, `c_validNotBefore` instead
  of `created`; a tenth of the entities get an earlier version (another
  description), bounded by `c_validNotAfter` so a second load changes
  nothing. Generic engine: `Graph.set_times`, `Graph.add_past_version`,
  `Graph.moment`, `Graph.between`.
- `get` takes `at=` (instant in valid time).
- Example documents: `created`/`modified` -> `c_created`/`c_modified`,
  `name`/`scope` -> `objName`/`objScope` (the terms the schemas define).
- Test backend (`tests/support/fake_backend.py`) strips c_* before storing
  and comparing.
  It now logs a request before answering it: the e2e tests read the log
  as soon as they have the answer and failed now and then.
- Integration tests: the second load must change nothing (skipped before);
  earlier versions readable at their time; a planned version only at its
  time; lists carry the c_* terms. CI job on `postgres:18`.

## [26.10.1] - 2026-10

First release as `ifdd-de/ct`, successor of the previous CT tool.

### Changed
- Package `ifdd.ct`, CLI `ifdd-ct`, variables `ifdd_ct_*` / `IFDD_CT_*`.
- Plugin mechanism rebuilt around the same idea: plugins are functions
  `(records, ctx, **params)` registered with `@plugin`; parameters, types and
  help come from the signature. Short names (`put`) instead of dotted paths.
- Plugins are discovered from three origins - built-in, `private/` (in the
  image) and `/plugins` (mounted) - and only those can be called.
- Files and directories as first/last step; stdin is read automatically,
  the result printed automatically; logs on stderr; pipeline files (`-f`).
- Faker is generic with profiles (`energy-grid`, `datacenter`) and a seed
  that makes ids, values and timestamps reproducible. Replaces
  `ifdd-de/tools-fakedata`.
- Backend steps send plain JSON-LD documents without a conversion step, with
  OIDC client credentials, CA bundle, timeouts and a summary of failures.
- Container: Python 3.14, multi-stage, non-root, read-only root file system,
  `ENTRYPOINT ifdd-ct`, dependencies pinned with hashes.
- Tests in a topic hierarchy (`tests/core`, `tests/plugins/<group>`, `tests/cli`,
  `tests/e2e`, `tests/private`) with one file per built-in plugin, shared
  helpers in `tests/support`, and end-to-end tests over real HTTP against a
  local fake backend. Coverage is measured on every run; below 75 % it fails.
- Example data under `data/examples/json-ld` with `.jsonld` extension;
  scope marker `ifdd_ct_testdata`.

### Added
- `check`: reports terms a document's `@context` does not define (and which
  JSON-LD expansion would drop silently), missing or unloadable contexts and
  invalid JSON-LD. Warns by default; `check:fail=true` stops the pipeline.
  Tested in pytest and, in the container, in the CI workflows.

### Fixed (compared to the previous version)
- Running outside the container failed without a hand-set PYTHONPATH.
- Files as first/last step never worked (the CLI stopped before reaching them).
- Names that were not plugins (e.g. `len`, a module) were silently skipped.
- Log output and data were both written to stdout.
- Parameter values containing `=` could not be passed.
- Duplicate plugins in one chain confused first/last detection.
- `head`/`tail` failed on a single object.
- Importing the faker module failed without environment variables, which
  also made any plugin listing impossible.
- Faker: parts were assigned from overlapping index ranges, so parts were
  shared, `isPartOf` overwritten and about two thirds of them orphaned.
- `post` failed on faker output (`KeyError: 'expanded'`), `patch` read `@id`
  from the wrong level, `put` built its payload and did not send it.
- HTTP requests had no timeout.

### Removed
- `json-ld.Convert` based on rdflib (the pyld variant remains as `expand`/`compact`/`node`).
- The four debug counters `--dm/--dp/--de/--ds` (three of them had no effect).

(ifdd-ct-pipelines)=
# Pipelines

## Steps and records

A chain is a list of steps; between them flows a **list of records** (JSON
objects). Three rules keep chains short:

- If the first step is not a *source* and data is piped in, standard input
  is read first: `cat docs.json | ifdd-ct head:count=3`.
- If the last step is not a *sink*, the records are printed to standard
  output as JSON: `ifdd-ct faker:product=1 | jq length`.
- Logs go to standard error only.

The step syntax and the built-in plugins are listed in
{ref}`ifdd-ct-reference`.

Example, one product as JSON-LD, nothing written:

```bash
./adm_02_run.sh faker:profile=energy-grid,seed=42,product=1,function=0,location=0,organisation=0 head:count=2 stdout
```

It prints the base and the product document of one product. The other
entity types are set to 0 because the profile has default counts for them,
and `head:count=2` is needed because `energy-grid` creates three parts per
product; the product document refers to them with `hasPart`.

## Pipeline files

The same steps as YAML, versioned next to the data in `data/pipelines/`:

```yaml
steps:
  - faker: {profile: energy-grid, seed: 42, product: 20}
  - put: {dry_run: true}
  - out/generated.json
```

A step is a string in command-line syntax or a one-key mapping
`plugin: {parameters}`. Relative paths start at the working directory
(`/data`). Run it with `./adm_02_run.sh -f pipelines/<file>.yaml`.

## Checking documents against their context

JSON-LD expansion silently drops every term the `@context` does not define,
so a typo such as `nmae` for `name` would get lost. `check` reports those
terms before anything is sent, and passes the records on unchanged:

```bash
./adm_02_run.sh examples/json-ld check put              # warn, then load anyway
./adm_02_run.sh examples/json-ld check:fail=true put    # stop before loading
```

Also reported: a missing `@context`, a context that cannot be loaded,
invalid JSON-LD. In a pipeline file: `- check: {fail: true}`.

Limits: if a context uses `@vocab`, every term counts as defined and nothing
is reported. Values are not checked against their declared type, and
required fields or cardinalities are not checked; that needs SHACL, which is
planned.

## Writing to the backend

`put`, `patch` and `post` take plain JSON-LD documents (with `@id` and a
single `@context` URL) and send the envelope the backend expects:

```json
{"id": "<@id>", "context": "<@context>", "aspect": "<aspect>", "json": {"...": "..."}}
```

The aspect comes from `aspect=...`, from an envelope made by `node`, from
`IFDD_CT_ASPECTS` (path segment of `@id`, `/products/...` -> `product`), or
from an `aspect` field in the document, in that order. The target URL is
`IFDD_CT_BE_URL` plus the path of `@id`. The backend creates nodes with
`PUT /{segment}/{id}` (create or replace, with history) and has no
`POST /nodes/`; `post` is kept for backends that offer it.

## Faker profiles

`faker` is generic; a *profile* describes a domain. Same seed, same data,
including ids and timestamps.

| Profile | Types (defaults) | Notes |
|---|---|---|
| `energy-grid` | product=10, function=5, location=3, organisation=3 | a `base` and an aspect document per entity; every product and location gets 3 parts; circuit breakers also get two domain documents |
| `datacenter` | room=2, rack=6, pdu=12, server=24 | documentation example only: inline `@context`, no schemas, not loadable into the backend |

Every `energy-grid` entity carries the source times of the schemas:
`c_created` (within a year before the anchor), `c_modified` and
`c_validNotBefore` (= `c_created`). A tenth of the entities changed once:
they come with an earlier version first, which ends where the current one
starts. The backend keeps both; read the earlier one with
`get:id=...,at=<its c_validNotBefore>`.

Every product of the kind "Circuit Breaker" also gets one document in each
example domain context of the schema service,
`breaker.grid.example.ifdd.de` and `maintenance.ops.example.ifdd.de`. Rated
voltage and current are QUDT quantity values whose unit is an IRI below
`{{ cookiecutter.ifdd_unit_url }}`. The backend gives domain documents only to
clients with a matching context pattern; `{{ cookiecutter.ifdd_keycloak_ct_client_id }}`
has the pattern of the root in the realm of the keycloak template.

A private or local module can add a profile with
`ifdd.ct.faker.register_profile(Profile(...))`; `profiles/datacenter.py` in
the source is the smallest complete example.

### Loading fake data into the backend

```bash
./adm_01_build.sh                                       # once, and after updates
./adm_02_run.sh -f pipelines/generate-energy-grid.yaml
```

The pipeline generates the energy grid with a fixed seed, checks every
document against its `@context` from the schema service (`check` with
`fail: true`: nothing is written if a term is undefined there) and loads the
documents with `put`. Loading the same data again changes nothing.

## Writing plugins

A plugin is a function that gets the records and a context and returns the
new records. Parameters come from its signature; annotations set the types:

```python
from typing import Annotated

from ifdd.ct import CtError, plugin

@plugin
def only_type(
    records, ctx,
    obj_type: Annotated[str, "value of objType to keep"],
    limit: Annotated[int, "keep at most this many; 0: all"] = 0,
):
    """Keep documents with objType == OBJ_TYPE (at most LIMIT, 0 = all)."""
    kept = [r for r in records if r.get("objType") == obj_type]
    return kept[:limit] if limit else kept
```

The plugin documents itself: the first line of the docstring is its summary
in `--list`, the rest is shown as written. `Annotated[type, "help"]` adds a
help text to a parameter; the type works as without it. A function
`describe_extra` attached to the plugin (`only_type.describe_extra = ...`)
adds generated text, as the faker profiles do. `--describe` and
`--markdown` show all of it.

`@plugin(source=True)` marks a step that produces data (standard input is
not read in front of it), `@plugin(sink=True)` one that consumes it (nothing
is printed after it). Raise `CtError` for a clean error message. The context
offers `ctx.settings` (configuration), `ctx.log` (logger, standard error),
`ctx.http` (requests with timeout, CA bundle and token) and `ctx.shared` (a
dict for the run).

Put plugins of this instance into `private/` (built into the image) and
experiments into `plugins/` (mounted, no build needed). `plugins/example_stamp.py`
is a working example. A package (directory with `__init__.py`) works too;
inside it use relative imports.

## Coming from the previous CT

Plugins now get `(records, ctx, **params)` instead of
`(call_params, runtime_infos)` and `trans()`. The built-in plugins have short
names (`put`, `head`, `faker`) instead of dotted paths, files are steps of
their own, and loading data needs no conversion step:
`ifdd-ct examples/json-ld put`. The faker of `ifdd-de/tools-fakedata` is
replaced by `faker`.

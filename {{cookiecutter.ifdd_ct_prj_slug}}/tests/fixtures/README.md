# tests/fixtures/

Static test data.

`contexts/` holds minimal stand-in JSON-LD contexts, used through
IFDD_CT_CONTEXT_DIR so that tests run offline. They are NOT the real schemas
of the schema service - they only map every term into a test vocabulary and
declare `hasPart`/`isPartOf` as references. `strict.jsonld` has no `@vocab`
and defines only `name`, `size` and `hasPart`, so undefined terms are dropped
and the `check` plugin can report them.

`breaker.grid.example.ifdd.de.jsonld` and
`maintenance.ops.example.ifdd.de.jsonld` are copies of the example domain
contexts of ifdd-de/schema (namespace rendered as `https://type.test/v1`),
so `check` can tell whether the faker's domain documents fit them.

`documents/` holds small JSON-LD files, e.g. `check-clean.jsonld` (no
findings) and `check-typo.jsonld` (one undefined term, `nmae`). The container
test in `.github/workflows/ci.yml` uses them as well.

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

## AI assistance

Some parts of the template `ifdd-de/ct` this instance was generated
from, in particular the tests, the test data and the documentation, were
developed or improved with the help of large language models (LLMs). All
changes were reviewed and released by the maintainer.

## License

BSD-3-Clause, see `LICENSE`.

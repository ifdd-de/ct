(ifdd-ct-build-release)=
# Build and release

## Image

One image holds the command line, the built-in plugins, the libraries for
planned plugins and the plugins in `private/`. `Dockerfile` builds in two
stages from `python:3.14-slim` (`PYTHON_IMAGE`): the first installs
`requirements.txt` and the package, the second copies the result and
`private/`, and runs as an unprivileged user (UID 10001; compose overrides it
with `IFDD_CT_UID`/`IFDD_CT_GID`).

```bash
./adm_01_build.sh
```

The script builds with `--pull` and tags
`{{ cookiecutter.ifdd_registry_url }}/{{ cookiecutter.ifdd_ct_prj_slug }}:{{ cookiecutter.ifdd_ct_version }}`,
the image the production compose file runs. For reproducible builds pin the
base image by digest (`PYTHON_IMAGE=python:3.14-slim@sha256:...`). Rebuild
after every change of `src/`, `private/` or `requirements.txt`; `plugins/` is
mounted and needs no build.

## Dependencies

`requirements.txt` pins every dependency with hashes, resolved for Python
3.14 on Linux x86_64 (the image); it also installs on Python 3.13, the
lowest version the package accepts. After changing the dependencies in `pyproject.toml`,
regenerate it with the command in its header (`uv pip compile ...`).

## Versions

| Value | Here | Source |
|---|---|---|
| version of the instance | `{{ cookiecutter.ifdd_ct_version }}` | template variable `ifdd_ct_version`; package version, image tag, `ifdd-ct --version` |

The scheme is `YY.MM.N`.

## Tests

```bash
pytest                      # offline; fails below 95 % coverage
```

The tests are laid out by topic: one file per built-in plugin under
`tests/plugins/`, core behaviour under `tests/core/`, the command line under
`tests/cli/`, real HTTP against a local fake backend under `tests/e2e/`.
Tests for the plugins of this instance go into `tests/private/` (on the
skip list). See `tests/README.md`.

`tests/integration/` runs against a real, running backend and **writes fake
data into it**. It is skipped unless `IFDD_IT_BE_URL` is set; the variables
are listed in `tests/integration/conftest.py`. Against this node, behind the
proxy:

```bash
IFDD_IT_BE_URL={{ cookiecutter.ifdd_be_url }} IFDD_IT_SCHEMA_URL={{ cookiecutter.ifdd_schema_url }} \
IFDD_IT_TOKEN_URL={{ cookiecutter.ifdd_oidc_token_url }} \
IFDD_IT_CLIENT_ID={{ cookiecutter.ifdd_keycloak_ct_client_id }} IFDD_IT_CLIENT_SECRET=<secret> \
IFDD_IT_CA_BUNDLE=certs/ca.crt pytest --no-cov tests/integration
```

## CI of the instance

`.github/workflows/ci.yml` runs on every push and pull request:

- **tests** on Python 3.14 with the pinned, hash-checked dependencies;
- **image and compose files**: builds the image, lists the plugins, runs the
  faker without any service, checks that `check` warns by default and fails
  with `fail=true`, validates both compose files;
- **template drift**: `cruft check` and `cruft diff`, informational.

## Release

`.github/workflows/release.yml` builds the image and pushes it to
`ghcr.io/<owner>/<repository>` when a tag `v*` is pushed. The local image
name above (`{{ cookiecutter.ifdd_registry_url }}/...`) is independent of
it.

```{note}
Not tested here: the image build and the release workflow. The template CI
builds the image; the honesty notes in the README list what was run.
```

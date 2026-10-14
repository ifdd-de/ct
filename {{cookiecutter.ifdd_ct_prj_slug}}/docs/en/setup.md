(ifdd-ct-setup)=
# Setup

## Prerequisites

| What | Why |
|---|---|
| Docker with Compose | ct runs as a container |
| the external network `{{ cookiecutter.ifdd_proxy_network }}` and a running proxy instance | ct reaches every service through it |
| the proxy lists the hosts of the backend, the schema service and Keycloak in `ifdd_proxy_internal_hosts` | inside the container those names must lead to Traefik |
| the client `{{ cookiecutter.ifdd_keycloak_ct_client_id }}` in the realm, and its secret | the keycloak template creates the client; its secret is `IFDD_KEYCLOAK_CT_CLIENT_SECRET` in the `.env` of the keycloak instance |
| the CA certificate of the proxy, if it uses a CA of its own | `certs/ca.crt` of the proxy instance |

## Create the instance

Usually the meta repository creates every instance in one go
(`.adm_meta_01_all.sh`, step `.adm_01_create_services.sh`): it runs
`cruft create` with the shared variable file `.cookiecutter_all.yaml`,
copies the CA of the proxy into `certs/` and the client secret into `.env`.

By hand, from the directory that holds the instances:

```bash
cruft create --no-input --config-file .cookiecutter_all.yaml \
  https://github.com/ifdd-de/ct
cp proxy/certs/ca.crt {{ cookiecutter.ifdd_ct_prj_slug }}/certs/
```

`.env`, `certs`, `data`, `plugins`, `private` and `tests/private` belong to
the instance; `pyproject.toml` lists them under `[tool.cruft]`, so template
updates never touch them.

## Configuration

The post-generation hook writes `.env` from `dotenv.dist`. All settings are
environment variables, read when a step needs them; `--list` works without
any. The full list is in {ref}`ifdd-ct-reference`; the values that come
from the template variables are explained in {ref}`ifdd-instances-ct`.

To be set by hand:

| Entry | What |
|---|---|
| `IFDD_CT_OIDC_CLIENT_SECRET` | the secret of `{{ cookiecutter.ifdd_keycloak_ct_client_id }}`, from `IFDD_KEYCLOAK_CT_CLIENT_SECRET` of the keycloak instance; the template leaves it empty |
| `IFDD_CT_CA_BUNDLE` | `/certs/ca.crt` (default): only this file is trusted. Empty: the system trust store of the image, for publicly trusted certificates |
| `IFDD_CT_UID`, `IFDD_CT_GID` | your user and group (`id -u`, `id -g`), so that files written to `data/` belong to you |

Leave `IFDD_CT_OIDC_CLIENT_ID` empty only for a backend without
authentication.

## First run

```bash
./adm_01_build.sh                    # build the image, or pull it from the registry
./adm_02_run.sh --list               # the plugins
./adm_02_run.sh examples/json-ld check put:dry_run=true
```

`adm_02_run.sh` is `docker compose run --rm ct ...` with this instance's
`.env`, `./data` (as `/data`, the working directory), `./plugins` (as
`/plugins`) and `./certs` (as `/certs`), on the network
`{{ cookiecutter.ifdd_proxy_network }}`.
`IFDD_CT_COMPOSE=development ./adm_02_run.sh ...` uses the development
compose file, which builds the image locally and mounts `src/` and
`private/` over the installed copies.

## Local development

```bash
python3 -m venv .venv && . .venv/bin/activate   # Python 3.13 or later
pip install --require-hashes -r requirements.txt
pip install --no-deps -e . && pip install pytest pytest-cov
pytest                      # measures coverage, fails below 95 %
IFDD_CT_PRIVATE_DIR=./private IFDD_CT_PLUGIN_PATH=./plugins ifdd-ct --list
```

## Running locally in a shell

ct also runs without Docker, from a virtual environment (Python 3.13 or
later). Three things that the container sets up are then up to you:

1. **Configuration.** docker compose reads `.env`, a shell does not. Load
   it with `set -a; . ./.env; set +a`. `IFDD_CT_ASPECTS` stands in single
   quotes so that the JSON survives this; in an instance generated before
   that change, add the quotes by hand:
   `IFDD_CT_ASPECTS='{"products": "product", ...}'`.
2. **CA bundle.** `IFDD_CT_CA_BUNDLE=/certs/ca.crt` is the path inside the
   container. In the shell, point it to `certs/ca.crt` of the instance;
   otherwise every step that calls a service stops with
   `IFDD_CT_CA_BUNDLE: file not found`. Empty: the system trust store.
3. **Plugin directories.** The defaults `/opt/ifdd-ct/private` and
   `/plugins` are paths in the image. Set `IFDD_CT_PRIVATE_DIR` and
   `IFDD_CT_PLUGIN_PATH` to `private/` and `plugins/` of the instance; an
   empty `IFDD_CT_PLUGIN_PATH` leaves out the local plugins. `private/` is
   not part of the installed package.

Step by step, in the directory of the instance:

```bash
python3 -m venv .venv && . .venv/bin/activate   # Python 3.13 or later
pip install --require-hashes -r requirements.txt
pip install --no-deps .        # or -e . while you change src/
set -a; . ./.env; set +a
export IFDD_CT_CA_BUNDLE=$PWD/certs/ca.crt
export IFDD_CT_PRIVATE_DIR=$PWD/private IFDD_CT_PLUGIN_PATH=$PWD/plugins
ifdd-ct --list
cd data                        # the working directory of the container
ifdd-ct examples/json-ld check put:dry_run=true
```

The paths are absolute, so `ifdd-ct` works from any directory afterwards.
In a new shell, activate the environment, load `.env` and set the three
variables again.

```{note}
Not tested: reaching the services from the host. The host names in the
URLs of `.env` (here `{{ cookiecutter.ifdd_be_url }}`,
`{{ cookiecutter.ifdd_schema_url }}` and the token URL) must resolve on the
host to the proxy, for example through `/etc/hosts`, and the proxy must
route them. Checked in a shell: installing, `--list`, `--describe`,
`--markdown` and `faker`.
```

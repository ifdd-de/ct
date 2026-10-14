(ifdd-ct-index)=
# {{ cookiecutter.ifdd_ct_prj_name }} (ct)

The core tools of an IFDD node: the command `ifdd-ct` chains small plugins
over JSON-LD records. It reads or generates documents, transforms and checks
them, and loads them into the backend. ct is a job container, not a
service: it starts, runs its steps and exits. This chapter describes the
instance `{{ cookiecutter.ifdd_ct_prj_slug }}`, generated from the template
`ifdd-de/ct`, from the point of view of the people who set it up, build, run
and secure it.

| | |
|---|---|
| Version | `{{ cookiecutter.ifdd_ct_version }}` |
| Image | `{{ cookiecutter.ifdd_registry_url }}/{{ cookiecutter.ifdd_ct_prj_slug }}:{{ cookiecutter.ifdd_ct_version }}` |
| Backend | `{{ cookiecutter.ifdd_be_url }}` |
| Contexts, units | `{{ cookiecutter.ifdd_schema_url }}`, `{{ cookiecutter.ifdd_unit_url }}` |
| Token endpoint, client | `{{ cookiecutter.ifdd_oidc_token_url }}`, `{{ cookiecutter.ifdd_keycloak_ct_client_id }}` |
| Network | `{{ cookiecutter.ifdd_proxy_network }}` |

## What the instance contains

The Python package `ifdd.ct` (`src/`) with the command line, the built-in
plugins and the faker profiles; the `Dockerfile` and two compose files; the
scripts `adm_01_build.sh` (build the image) and `adm_02_run.sh` (run a
chain). Four directories belong to the instance and are on the cruft skip
list:

| Directory | Content |
|---|---|
| `data/` | the working directory in the container: example documents, pipeline files, results |
| `private/` | plugins of this instance, built into the image |
| `plugins/` | local plugins, mounted at run time |
| `certs/` | the CA certificate for internal certificates |

## Architecture

```{mermaid}
flowchart LR
  Op[operator] -->|adm_02_run.sh| CT[ct: job container]
  CT -->|reads, writes| Data[(data/)]
  CT -->|loads| Plugins[plugins/]
  CT -->|client credentials| Proxy[proxy: Traefik]
  Proxy --> KC[Keycloak]
  Proxy --> BE[be]
  Proxy --> Schema[schema]
```

ct calls every service under its public URL through the proxy, from inside
the network `{{ cookiecutter.ifdd_proxy_network }}`.

| ct calls | For |
|---|---|
| Keycloak (`{{ cookiecutter.ifdd_oidc_token_url }}`) | an access token with client credentials |
| be (`{{ cookiecutter.ifdd_be_url }}`) | reading (`get`) and writing (`put`, `patch`, `post`) documents |
| schema (`{{ cookiecutter.ifdd_schema_url }}`) | the contexts of the documents, for `check`, `expand`, `compact` |

The unit and type URLs only appear in generated data and in planned plugins;
ct does not call them today.

## Chapters

```{toctree}
:maxdepth: 2

setup
build-release
operations
security
troubleshooting
reference
pipelines
```

The values of the variables of this instance and how they relate to the
other services are listed in the chapter on the service instances
({ref}`ifdd-instances-ct`).

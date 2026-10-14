(ifdd-ct-security)=
# Security

## The client

ct signs in with the OAuth 2.0 client credentials grant as
`{{ cookiecutter.ifdd_keycloak_ct_client_id }}`. In the realm of the
keycloak template that client has the read and the write role and the
context pattern of the root: whoever holds its secret can write every
document of the node. ct reuses a token until shortly before it expires and
renews it once on a 401.

- The secret is in `.env` only (`IFDD_CT_OIDC_CLIENT_SECRET`), never a
  template variable, never in Git or `.cruft.json`.
- `put`, `patch` and `post` accept `dry_run=true`: try a chain without
  writing first.

## TLS

Certificate verification is never switched off. With
`IFDD_CT_CA_BUNDLE=/certs/ca.crt` only that CA is trusted; empty, the system
trust store of the image is used.

## Plugins

Only plugins from three places can be called: the built-in ones, `private/`
(built into the image) and `plugins/` (mounted at run time); there are no
arbitrary Python paths. A plugin runs with the rights of the client, so
whoever can write to `private/` or `plugins/` can write to the backend.

## Container

| Measure | Setting |
|---|---|
| user | the calling user (`IFDD_CT_UID`, `IFDD_CT_GID`); the image defaults to UID 10001 |
| file system | read-only root, `/tmp` as tmpfs (production); `plugins/` and `certs/` read-only, `data/` writable |
| privileges | `no-new-privileges` |
| network | `{{ cookiecutter.ifdd_proxy_network }}` only, no published ports |

`.dockerignore` keeps `.env`, `data`, `plugins`, `certs` and `tests` out of
the image.

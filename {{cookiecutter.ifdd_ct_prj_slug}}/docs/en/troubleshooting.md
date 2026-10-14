(ifdd-ct-troubleshooting)=
# Troubleshooting

Start with `-v` (each step) or `-vv` (debug output and tracebacks).

## Start

| Symptom | Cause | Remedy |
|---|---|---|
| `.env missing - cp dotenv.dist .env` | no `.env` | create it from `dotenv.dist` and fill in the secret |
| `set IFDD_CT_BE_URL in .env` | the backend URL is missing | set it |
| exit code 2 | wrong command line or pipeline file | `ifdd-ct --describe <plugin>` shows the parameters |
| a plugin is listed under "not available" | its module failed to import (for example a missing library) | `-vv` shows why; the other plugins keep working |
| a plugin name is ambiguous | two origins define the same short name | qualify it: `builtin.head`, `local.head` or `<module>.head` |
| a `,` inside a parameter value splits it | `,` separates parameters | write it as `%2C` |

## Backend and services

| Symptom | Cause | Remedy |
|---|---|---|
| 401 from the backend | no or wrong client secret, wrong token endpoint | `IFDD_CT_OIDC_CLIENT_SECRET` from the keycloak instance; `IFDD_CT_OIDC_TOKEN_URL` |
| 403 from the backend | the client lacks the write role, or a context pattern for a domain context | check the client in the realm |
| certificate errors | the CA of the proxy is not in `certs/`, or `IFDD_CT_CA_BUNDLE` points elsewhere | copy `certs/ca.crt` of the proxy instance; check the variable |
| a service is unreachable from the container, or ct reaches itself | its host is not a network alias of the proxy | add it to `ifdd_proxy_internal_hosts` of the proxy instance |
| `post` fails | the backend has no `POST /nodes/` | use `put` |
| `No changes detected` for every document | the documents are unchanged | expected |

## Data

| Symptom | Cause | Remedy |
|---|---|---|
| `check` reports `undefined terms` | the document uses terms its `@context` does not define (a typo, or a schema that lacks them) | fix the document or the schema; `check:fail=true` stops before writing |
| `check` reports nothing although a term is wrong | the context uses `@vocab`, so every term counts as defined | expected; `check` cannot help there |
| a context cannot be loaded | the schema service is unreachable, or the URL is wrong | check `IFDD_CT_SCHEMA_URL`; `IFDD_CT_CONTEXT_DIR` uses local copies instead |
| files in `data/` belong to another user | `IFDD_CT_UID`/`IFDD_CT_GID` do not match you | set them to `id -u` and `id -g` |
| a relative path is not found | relative paths start at `/data` in the container | give paths below `data/` without the `data/` prefix |

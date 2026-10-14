#!/usr/bin/env bash
# Run ifdd-ct in the container with this instance's .env, data, plugins and certs.
#   ./adm_02_run.sh --list
#   ./adm_02_run.sh examples/json-ld put
#   ./adm_02_run.sh -f pipelines/load-examples.yaml
#   IFDD_CT_COMPOSE=development ./adm_02_run.sh --list
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo ".env missing - cp dotenv.dist .env" >&2; exit 1; }

exec docker compose -f "docker-compose-${IFDD_CT_COMPOSE:-production}.yml" run --rm ct "$@"

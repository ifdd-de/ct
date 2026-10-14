#!/usr/bin/env bash
# Build the image of this instance: {{ cookiecutter.ifdd_registry_url }}/{{ cookiecutter.ifdd_ct_prj_slug }}:{{ cookiecutter.ifdd_ct_version }}
set -euo pipefail
cd "$(dirname "$0")"

IMAGE="{{ cookiecutter.ifdd_registry_url }}/{{ cookiecutter.ifdd_ct_prj_slug }}:{{ cookiecutter.ifdd_ct_version }}"

command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "docker daemon not reachable" >&2; exit 1; }

docker build --pull --build-arg VERSION="{{ cookiecutter.ifdd_ct_version }}" --tag "$IMAGE" .
echo "built $IMAGE"

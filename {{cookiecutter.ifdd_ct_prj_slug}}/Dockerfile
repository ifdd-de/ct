# syntax=docker/dockerfile:1
# IFDD Core Tools - one image with the CLI, the built-in plugins, the
# libraries for planned plugins and this instance's private plugins.
#
# For reproducible builds pin the base image by digest, e.g.
#   python:3.14-slim@sha256:<digest>

ARG PYTHON_IMAGE=python:3.14-slim

FROM ${PYTHON_IMAGE} AS build
WORKDIR /build
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps --prefix=/install .

FROM ${PYTHON_IMAGE}
ARG VERSION=dev
LABEL org.opencontainers.image.title="ifdd-ct" \
      org.opencontainers.image.description="IFDD Core Tools - plugin pipeline for JSON-LD data" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.version="${VERSION}"

COPY --from=build /install /usr/local
COPY private /opt/ifdd-ct/private

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    IFDD_CT_PRIVATE_DIR=/opt/ifdd-ct/private \
    IFDD_CT_PLUGIN_PATH=/plugins

# Runs as an unprivileged user; compose overrides the uid/gid so that files
# written to the mounted ./data belong to the calling user.
RUN useradd --system --uid 10001 --no-create-home ct \
 && mkdir -p /data /plugins /certs \
 && chown ct /data
USER ct
WORKDIR /data

ENTRYPOINT ["ifdd-ct"]
CMD ["--help"]

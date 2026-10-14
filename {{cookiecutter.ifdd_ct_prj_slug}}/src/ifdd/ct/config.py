"""Run-time configuration, read from IFDD_CT_* environment variables.

Values are read when a step needs them, never at import time: listing the
plugins works without any configuration.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .errors import UsageError

DEFAULT_PRIVATE_DIR = "/opt/ifdd-ct/private"
DEFAULT_PLUGIN_PATH = "/plugins"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _url(name: str) -> str:
    return _env(name).rstrip("/")


@dataclass
class Settings:
    be_url: str = field(default_factory=lambda: _url("IFDD_CT_BE_URL"))
    schema_url: str = field(default_factory=lambda: _url("IFDD_CT_SCHEMA_URL"))
    type_url: str = field(default_factory=lambda: _url("IFDD_CT_TYPE_URL"))
    unit_url: str = field(default_factory=lambda: _url("IFDD_CT_UNIT_URL"))
    aspects_raw: str = field(default_factory=lambda: _env("IFDD_CT_ASPECTS"))
    oidc_token_url: str = field(default_factory=lambda: _env("IFDD_CT_OIDC_TOKEN_URL"))
    oidc_client_id: str = field(default_factory=lambda: _env("IFDD_CT_OIDC_CLIENT_ID"))
    oidc_client_secret: str = field(
        default_factory=lambda: _env("IFDD_CT_OIDC_CLIENT_SECRET"), repr=False
    )
    ca_bundle: str = field(default_factory=lambda: _env("IFDD_CT_CA_BUNDLE"))
    http_timeout: float = field(
        default_factory=lambda: float(_env("IFDD_CT_HTTP_TIMEOUT", "30") or 30)
    )
    context_dir: str = field(default_factory=lambda: _env("IFDD_CT_CONTEXT_DIR"))

    def require(self, *names: str) -> None:
        """Fail with a clear message if a setting a step needs is empty."""
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            env = ", ".join(f"IFDD_CT_{n.upper()}" for n in missing)
            raise UsageError(f"missing configuration: {env}")

    @property
    def aspects(self) -> dict[str, str]:
        """REST path segment -> aspect name, e.g. {"products": "product"}."""
        if not self.aspects_raw:
            return {}
        try:
            mapping = json.loads(self.aspects_raw)
        except ValueError as err:
            raise UsageError(f"IFDD_CT_ASPECTS is not valid JSON: {err}") from None
        if not isinstance(mapping, dict):
            raise UsageError("IFDD_CT_ASPECTS must be a JSON object")
        return {str(k): str(v) for k, v in mapping.items()}


def private_dir() -> str:
    return _env("IFDD_CT_PRIVATE_DIR", DEFAULT_PRIVATE_DIR)


def plugin_path() -> list[str]:
    raw = _env("IFDD_CT_PLUGIN_PATH", DEFAULT_PLUGIN_PATH)
    return [p for p in raw.split(os.pathsep) if p]


def log_level() -> str:
    level = _env("IFDD_CT_LOG_LEVEL", "WARNING").upper()
    return "WARNING" if level == "WARN" else level

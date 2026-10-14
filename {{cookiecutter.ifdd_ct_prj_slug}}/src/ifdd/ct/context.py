"""The object every plugin receives as its second argument."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import Any

from .config import Settings


class Context:
    """Shared state of one pipeline run.

    ``settings``  configuration from IFDD_CT_* variables (read on first use)
    ``log``       logger of the running step; output goes to stderr
    ``shared``    a dict the steps of one run can use to pass hints along
    ``http``      a requests session with timeout, CA bundle and OIDC token
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings
        self.shared: dict[str, Any] = {}
        self.log = logging.getLogger("ifdd.ct")

    @cached_property
    def settings(self) -> Settings:
        return self._settings or Settings()

    @cached_property
    def http(self):
        from .http import Http

        return Http(self.settings)

    def for_step(self, name: str) -> "Context":
        self.log = logging.getLogger(f"ifdd.ct.{name}")
        return self

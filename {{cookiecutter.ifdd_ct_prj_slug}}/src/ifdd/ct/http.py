"""HTTP access for plugins: one session, one timeout, one token.

* TLS: IFDD_CT_CA_BUNDLE points to a PEM file with the CA of internal
  certificates. Certificate verification is never switched off.
* Auth: with IFDD_CT_OIDC_CLIENT_ID set, a token is fetched with the OAuth 2.0
  client credentials grant from IFDD_CT_OIDC_TOKEN_URL, cached until shortly
  before it expires and renewed once if the server answers 401.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import requests

from .config import Settings
from .errors import CtError, UsageError

log = logging.getLogger("ifdd.ct.http")

_RENEW_MARGIN = 30  # seconds before expiry


class Http:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.settings = settings
        self.session = session or requests.Session()
        if settings.ca_bundle:
            if not Path(settings.ca_bundle).is_file():
                raise UsageError(f"IFDD_CT_CA_BUNDLE: file not found: {settings.ca_bundle}")
            self.session.verify = settings.ca_bundle
        self._token: str | None = None
        self._expires = 0.0

    # -- auth -------------------------------------------------------------

    @property
    def auth_enabled(self) -> bool:
        return bool(self.settings.oidc_client_id)

    def _fetch_token(self) -> str:
        self.settings.require("oidc_token_url", "oidc_client_id", "oidc_client_secret")
        try:
            response = self.session.post(
                self.settings.oidc_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.oidc_client_id,
                    "client_secret": self.settings.oidc_client_secret,
                },
                timeout=self.settings.http_timeout,
            )
        except requests.RequestException as err:
            raise CtError(f"token request failed: {err}") from err
        if response.status_code != 200:
            raise CtError(
                f"token request failed: {response.status_code} {response.text[:200]}"
            )
        body = response.json()
        self._token = body["access_token"]
        self._expires = time.monotonic() + float(body.get("expires_in", 60))
        log.debug("fetched access token, expires in %ss", body.get("expires_in"))
        return self._token

    def _auth_header(self, renew: bool = False) -> dict[str, str]:
        if not self.auth_enabled:
            return {}
        if renew or self._token is None or time.monotonic() > self._expires - _RENEW_MARGIN:
            self._fetch_token()
        return {"Authorization": f"Bearer {self._token}"}

    # -- requests ---------------------------------------------------------

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Send a request; renew the token once on 401."""
        headers = dict(kwargs.pop("headers", {}) or {})
        kwargs.setdefault("timeout", self.settings.http_timeout)
        for attempt in (0, 1):
            try:
                response = self.session.request(
                    method, url, headers={**headers, **self._auth_header(renew=attempt == 1)},
                    **kwargs,
                )
            except requests.RequestException as err:
                raise CtError(f"{method} {url} failed: {err}") from err
            if response.status_code != 401 or not self.auth_enabled or attempt == 1:
                return response
            log.info("401 from %s - renewing token", url)
        return response  # pragma: no cover - loop always returns

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, **kwargs)

"""JSON-LD processing with a controlled document loader.

Contexts are looked up in IFDD_CT_CONTEXT_DIR first (file name = last path
segment of the context URL, e.g. ``product.jsonld``), then fetched over the
shared HTTP session. Fetched contexts are cached for the run. This makes
offline work and tests possible without touching pyld's global state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .errors import CtError


class DocumentLoader:
    def __init__(self, ctx):
        self.ctx = ctx
        self._cache: dict[str, dict[str, Any]] = {}
        self._remote = None

    def __call__(self, url: str, options: dict | None = None) -> dict[str, Any]:
        if url in self._cache:
            return self._cache[url]
        document = self._local(url)
        if document is None:
            document = self._fetch(url, options or {})
        self._cache[url] = document
        return document

    def _local(self, url: str) -> dict[str, Any] | None:
        directory = self.ctx.settings.context_dir
        if not directory:
            return None
        name = Path(urlparse(url).path).name
        path = Path(directory) / name
        if not name or not path.is_file():
            return None
        return {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "documentUrl": url,
            "document": json.loads(path.read_text(encoding="utf-8")),
        }

    def _fetch(self, url: str, options: dict) -> dict[str, Any]:
        if self._remote is None:
            from pyld.documentloader.requests import RequestsDocumentLoader

            self._remote = RequestsDocumentLoader(
                session=self.ctx.http.session, timeout=self.ctx.settings.http_timeout
            )
        return self._remote(url, options)


def _loader(ctx) -> DocumentLoader:
    loader = ctx.shared.get("_jsonld_loader")
    if loader is None:
        loader = ctx.shared["_jsonld_loader"] = DocumentLoader(ctx)
    return loader


def expand(doc: dict[str, Any], ctx, on_dropped=None) -> list[dict[str, Any]]:
    """Expand DOC. ``on_dropped(term)`` is called for every term the context
    does not define and that expansion therefore drops."""
    from pyld import jsonld

    kwargs = {"on_property_dropped": on_dropped} if on_dropped else {}
    try:
        return jsonld.expand(doc, options={"documentLoader": _loader(ctx)}, **kwargs)
    except jsonld.JsonLdError as err:
        raise CtError(f"expand {doc.get('@id', '?')}: {err}") from err


def compact(doc: dict[str, Any], context: Any, ctx) -> dict[str, Any]:
    from pyld import jsonld

    try:
        return jsonld.compact(
            doc,
            context,
            options={"documentLoader": _loader(ctx), "graph": False, "compactArrays": True},
        )
    except jsonld.JsonLdError as err:
        raise CtError(f"compact {doc.get('@id', '?')}: {err}") from err

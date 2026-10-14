"""Read from and write to the IFDD backend (ifdd-be).

Configuration: IFDD_CT_BE_URL, IFDD_CT_ASPECTS and, if the backend requires
authentication, IFDD_CT_OIDC_TOKEN_URL, IFDD_CT_OIDC_CLIENT_ID and
IFDD_CT_OIDC_CLIENT_SECRET (client credentials grant).

The write steps accept plain JSON-LD documents (with @id and @context) or
envelopes made by ``node``. Every record is sent; failures are logged and
reported together at the end, so one bad document does not hide the others.
"""

from __future__ import annotations

import json
from typing import Annotated

from ifdd.ct import CtError, plugin
from ifdd.ct.nodes import AspectParam, document_of, node_url, to_node

DryRun = Annotated[bool, "log what would be sent, send nothing"]


def _send(records, ctx, method: str, aspect: str, dry_run: bool, url_of):
    ctx.settings.require("be_url")
    failures = []
    for record in records:
        envelope = to_node(record, ctx, aspect or None)
        url = url_of(envelope)
        if dry_run:
            ctx.log.warning("dry run: %s %s (aspect %s)", method, url, envelope["aspect"])
            continue
        response = ctx.http.request(
            method, url, data=json.dumps(envelope), headers={"Content-Type": "application/json"}
        )
        detail = _detail(response)
        if response.status_code >= 400:
            ctx.log.error("%s %s -> %s %s", method, envelope["id"], response.status_code, detail)
            failures.append(envelope["id"])
        else:
            ctx.log.info("%s %s -> %s %s", method, envelope["id"], response.status_code, detail)
    if failures:
        raise CtError(f"{method}: {len(failures)} of {len(records)} records failed")
    return records


def _detail(response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict):
        return str(body.get("message") or body.get("detail") or "")
    return ""


@plugin(sink=True)
def put(records, ctx, aspect: AspectParam = "", dry_run: DryRun = False):
    """Create or replace each document: PUT to IFDD_CT_BE_URL + path of its @id.

    The backend keeps history: an unchanged document is reported as
    'No changes detected' and not stored again.
    """
    base = ctx.settings.be_url
    return _send(records, ctx, "PUT", aspect, dry_run, lambda e: node_url(e["id"], base))


@plugin(sink=True)
def patch(records, ctx, aspect: AspectParam = "", dry_run: DryRun = False):
    """Merge each document into the existing node: PATCH to IFDD_CT_BE_URL + path of @id."""
    base = ctx.settings.be_url
    return _send(records, ctx, "PATCH", aspect, dry_run, lambda e: node_url(e["id"], base))


@plugin(sink=True)
def post(records, ctx, aspect: AspectParam = "", dry_run: DryRun = False):
    """Send each document as a new node: POST to IFDD_CT_BE_URL/nodes/.

    Kept for backends that offer POST /nodes/. The ifdd-be versions reviewed
    for this release create nodes with PUT only - prefer 'put'.
    """
    base = ctx.settings.be_url
    return _send(records, ctx, "POST", aspect, dry_run, lambda e: f"{base}/nodes/")


@plugin(source=True)
def get(records, ctx,
        segment: Annotated[str, "collection to read a page of, e.g. products"] = "",
        id: Annotated[str, "@id or URL of one node, compacted by the backend"] = "",
        start: Annotated[int, "first item of the page (as in the REST API)"] = 0,
        end: Annotated[int, "end of the page (as in the REST API)"] = 100,
        at: Annotated[str, "ISO 8601 instant in valid time; empty: now, as the backend"] = ""):
    """Fetch documents from the backend and add them to the records.

    Give exactly one of segment=... (a page of a collection) or id=... (one
    node).
    """
    ctx.settings.require("be_url")
    base = ctx.settings.be_url
    if bool(segment) == bool(id):
        raise CtError("get needs exactly one of segment=... or id=...")
    if id:
        url = node_url(id, base)
        params = {}
    else:
        url = f"{base}/{segment.strip('/')}"
        params = {"start": start, "end": end}
    if at:
        params["at"] = at
    response = ctx.http.get(url, params=params or None)
    if response.status_code >= 400:
        raise CtError(f"GET {url} -> {response.status_code} {_detail(response)}")
    fetched = response.json()
    fetched = fetched if isinstance(fetched, list) else [fetched]
    ctx.log.info("GET %s -> %d documents", url, len(fetched))
    return [*records, *fetched]


__all__ = ["put", "patch", "post", "get", "document_of"]

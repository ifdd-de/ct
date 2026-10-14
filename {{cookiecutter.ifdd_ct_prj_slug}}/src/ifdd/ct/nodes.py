"""The backend's node envelope and how a document is mapped onto it.

The backend (ifdd-be) stores each JSON-LD document as a node:

    {"id": <@id>, "context": <@context>, "aspect": <aspect>, "json": <document>}

``aspect`` is taken, in this order, from: an explicit plugin parameter, an
envelope that already carries it, IFDD_CT_ASPECTS (path segment of @id, e.g.
``/products/...`` -> ``product``), a top-level ``aspect`` field in the document.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlparse

from .errors import CtError

# Parameter type of the steps that build envelopes (node, put, patch, post).
AspectParam = Annotated[
    str, "aspect of every document; empty: from an envelope, IFDD_CT_ASPECTS or the document"
]


def is_node(record: Any) -> bool:
    return isinstance(record, dict) and isinstance(record.get("json"), dict) and "aspect" in record


def document_of(record: dict[str, Any]) -> dict[str, Any]:
    return record["json"] if is_node(record) else record


def segment_of(doc_id: str) -> str:
    parts = [p for p in urlparse(doc_id).path.split("/") if p]
    return parts[-2] if len(parts) >= 2 else ""


def aspect_of(record: dict[str, Any], ctx, override: str | None = None) -> str:
    if override:
        return override
    if is_node(record) and record.get("aspect"):
        return str(record["aspect"])
    doc = document_of(record)
    segment = segment_of(str(doc.get("@id", "")))
    mapping = ctx.settings.aspects
    if segment in mapping:
        return mapping[segment]
    if isinstance(doc.get("aspect"), str) and doc["aspect"]:
        return doc["aspect"]
    raise CtError(
        f"{doc.get('@id', '?')}: cannot tell the aspect of path segment '{segment}' - "
        "add it to IFDD_CT_ASPECTS or pass aspect=..."
    )


def to_node(record: dict[str, Any], ctx, aspect: str | None = None) -> dict[str, Any]:
    doc = document_of(record)
    for key in ("@id", "@context"):
        if key not in doc:
            raise CtError(f"document without {key}: {str(doc)[:120]}")
    if not isinstance(doc["@context"], str):
        raise CtError(
            f"{doc['@id']}: the backend needs @context as a single URL, "
            f"got {type(doc['@context']).__name__}"
        )
    envelope = {
        "id": doc["@id"],
        "context": doc["@context"],
        "aspect": aspect_of(record, ctx, aspect),
        "json": doc,
    }
    if is_node(record) and "expanded" in record:
        envelope["expanded"] = record["expanded"]
    return envelope


def node_url(doc_id: str, be_url: str) -> str:
    """URL of a node on the configured backend: IFDD_CT_BE_URL + path of @id."""
    path = urlparse(doc_id).path
    if not path.strip("/"):
        raise CtError(f"@id '{doc_id}' has no path")
    return be_url.rstrip("/") + path

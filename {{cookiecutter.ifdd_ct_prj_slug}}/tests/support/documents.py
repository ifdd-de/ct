"""Small JSON-LD documents for tests.

The URLs match the test environment set up in ``tests/conftest.py``:
backend https://rest.test, schemas https://schema.test/v1.
"""

from __future__ import annotations

from typing import Any

BE_URL = "https://rest.test"
SCHEMA_URL = "https://schema.test/v1"


def doc(segment: str = "products", key: str = "0001", context: str = "product", **fields: Any) -> dict:
    """A document with @id BE_URL/SEGMENT/KEY and @context SCHEMA_URL/CONTEXT.jsonld."""
    return {
        "@context": f"{SCHEMA_URL}/{context}.jsonld",
        "@id": f"{BE_URL}/{segment}/{key}",
        **fields,
    }


def envelope(document: dict, aspect: str, **extra: Any) -> dict:
    """The backend envelope around DOCUMENT, as the node plugin builds it."""
    return {
        "id": document["@id"],
        "context": document["@context"],
        "aspect": aspect,
        "json": document,
        **extra,
    }

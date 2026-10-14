"""Generic steps that work on any records."""

from __future__ import annotations

import json
import sys
from typing import Annotated

from ifdd.ct import plugin


@plugin
def head(records, ctx, count: Annotated[int, "number of records to keep"] = 4):
    """Keep the first COUNT records."""
    return records[:count]


@plugin
def tail(records, ctx, count: Annotated[int, "number of records to keep"] = 4):
    """Keep the last COUNT records."""
    return records[-count:] if count > 0 else []


@plugin
def where(records, ctx, key: Annotated[str, "top-level key of a record"],
          value: Annotated[str, "value to keep, compared as text"]):
    """Keep records whose top-level KEY equals VALUE (compared as text)."""
    return [r for r in records if isinstance(r, dict) and str(r.get(key)) == value]


@plugin
def count(records, ctx):
    """Print the number of records to stderr and pass them on unchanged."""
    print(f"{len(records)} records", file=sys.stderr)
    return records


@plugin(sink=True)
def stdout(records, ctx, pretty: Annotated[bool, "indent the JSON; false: one line"] = True):
    """Print the records as JSON and pass them on (useful between steps)."""
    json.dump(records, sys.stdout, indent=2 if pretty else None, ensure_ascii=False)
    sys.stdout.write("\n")
    return records

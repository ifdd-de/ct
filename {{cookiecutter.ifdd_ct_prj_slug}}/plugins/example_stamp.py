"""Example of a local plugin - see plugins/README.md."""

from typing import Annotated

from ifdd.ct import plugin


@plugin
def stamp(records, ctx, key: Annotated[str, "field to set"] = "note",
          value: Annotated[str, "value to set"] = "example"):
    """Set KEY to VALUE in every record (example of a local plugin)."""
    return [{**record, key: value} for record in records]

# plugins/

Local plugins, mounted at run time as `/plugins` (IFDD_CT_PLUGIN_PATH).
Every module here is loaded at start-up; plugins show up as `local.<name>`.
Change a file and run again - no image build needed.

A plugin is a function that takes the records and the context and returns
the new records:

```python
from ifdd.ct import plugin

@plugin
def stamp(records, ctx, source: str = "manual"):
    """Add a 'source' field to every record."""
    return [{**r, "source": source} for r in records]
```

Parameters come from the signature (`stamp:source=import-2026`); their
annotations decide the type. `Annotated[str, "help"]` (from `typing`) adds
a help text. `ifdd-ct --describe stamp` shows the docstring and the help
texts, `ifdd-ct --markdown` all plugins as one Markdown page.

A package (directory with `__init__.py`) works too; inside it use relative
imports (`from . import helpers`).

`example_stamp.py` is a working example; delete it when you no longer need it.

"""ifdd-ct - Core Tools: a plugin pipeline for JSON-LD data.

Plugins are plain functions registered with :func:`plugin`. The CLI chains
them: the records returned by one step are the input of the next.
"""

from .errors import CtError, UsageError
from .registry import plugin

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("ifdd-ct")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"

__all__ = ["CtError", "UsageError", "plugin", "__version__"]

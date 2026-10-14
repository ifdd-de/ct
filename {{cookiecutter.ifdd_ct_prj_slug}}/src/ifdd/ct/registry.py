"""Plugin registration, discovery and name resolution.

A plugin is a function ``fn(records, ctx, **params)`` decorated with
:func:`plugin`. Its parameters are taken from the signature, so type
conversion, validation and ``--describe`` come for free::

    from ifdd.ct import plugin

    @plugin
    def head(records, ctx, count: int = 4):
        \"\"\"Keep the first COUNT records.\"\"\"
        return records[:count]

A parameter can carry a one-line help text with ``typing.Annotated``; it is
shown by ``--describe`` and in ``--markdown``::

    def head(records, ctx, count: Annotated[int, "number of records to keep"] = 4):

Plugins come from three origins. A short name must be unique across all of
them; if it is not, the CLI asks you to qualify it:

* ``builtin`` - modules in ``ifdd.ct.plugins`` shipped with the image,
* ``private`` - modules in IFDD_CT_PRIVATE_DIR, baked into this instance's image,
* ``local``   - modules in IFDD_CT_PLUGIN_PATH, mounted at run time.

A plugin can be addressed as ``name``, ``origin.name``, ``module.name`` or
``origin.module.name``. Nothing outside these origins can be called.
"""

from __future__ import annotations

import difflib
import importlib
import importlib.util
import inspect
import logging
import pkgutil
import sys
import types
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import config
from .errors import UsageError

log = logging.getLogger("ifdd.ct")

ORIGINS = ("builtin", "private", "local")
_EXT_PACKAGE = "ifdd_ct_ext"
_MISSING = inspect.Parameter.empty


@dataclass
class Param:
    name: str
    type: Any
    default: Any = _MISSING
    help: str = ""

    @property
    def required(self) -> bool:
        return self.default is _MISSING

    @property
    def type_name(self) -> str:
        return _type_name(self.type)

    def describe(self) -> str:
        type_name = _type_name(self.type)
        if self.required:
            return f"{self.name}: {type_name} (required)"
        return f"{self.name}: {type_name} = {self.default!r}"


@dataclass
class Plugin:
    name: str
    func: Callable[..., Any]
    origin: str
    module: str
    source: bool = False
    sink: bool = False
    params: list[Param] = field(default_factory=list)
    extra_params: bool = False

    @property
    def qualified(self) -> str:
        return f"{self.origin}.{self.name}"

    @property
    def addresses(self) -> set[str]:
        return {
            self.name,
            f"{self.origin}.{self.name}",
            f"{self.module}.{self.name}",
            f"{self.origin}.{self.module}.{self.name}",
        }

    @property
    def summary(self) -> str:
        doc = inspect.getdoc(self.func) or ""
        return doc.splitlines()[0] if doc else ""

    def describe(self) -> str:
        lines = [f"{self.qualified}  ({self.origin} module '{self.module}')"]
        role = [r for r, on in (("source", self.source), ("sink", self.sink)) if on]
        if role:
            lines.append(f"role: {', '.join(role)}")
        doc = inspect.getdoc(self.func)
        if doc:
            lines += ["", doc]
        extra = getattr(self.func, "describe_extra", None)
        if callable(extra):
            lines += ["", extra()]
        lines += ["", "parameters:"]
        if self.params or self.extra_params:
            width = max((len(p.describe()) for p in self.params if p.help), default=0)
            for p in self.params:
                text = p.describe()
                lines.append(f"  {text:<{width}}  {p.help}" if p.help else f"  {text}")
            if self.extra_params:
                lines.append("  ... further KEY=VALUE parameters are accepted (see above)")
        else:
            lines.append("  (none)")
        return "\n".join(lines)

    def bind(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Convert raw parameter values to the declared types."""
        known = {p.name: p for p in self.params}
        bound: dict[str, Any] = {}
        for key, value in raw.items():
            if key in known:
                bound[key] = convert(value, known[key].type, f"{self.name}:{key}")
            elif self.extra_params:
                bound[key] = value
            else:
                valid = ", ".join(known) or "none"
                raise UsageError(
                    f"plugin '{self.name}' has no parameter '{key}' (valid: {valid})"
                )
        missing = [p.name for p in self.params if p.required and p.name not in bound]
        if missing:
            raise UsageError(f"plugin '{self.name}' needs: {', '.join(missing)}")
        return bound


# --------------------------------------------------------------------------
# registration

_plugins: list[Plugin] = []
_unavailable: list[tuple[str, str, str]] = []  # (origin, module, reason)
_current: tuple[str, str] | None = None  # (origin, module) during discovery
_discovered = False
_builtin_loaded = False


def plugin(
    func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    source: bool = False,
    sink: bool = False,
):
    """Register a function as a pipeline step.

    ``source=True``: the step produces records and does not need input, so the
    CLI will not read stdin in front of it. ``sink=True``: the step consumes
    records (writes, uploads), so the CLI will not print them afterwards.
    """

    def register(fn: Callable[..., Any]) -> Callable[..., Any]:
        origin, module = _current or _origin_of(fn)
        params, extra = _params_of(fn)
        entry = Plugin(
            name=name or fn.__name__.replace("_", "-"),
            func=fn,
            origin=origin,
            module=module,
            source=source,
            sink=sink,
            params=params,
            extra_params=extra,
        )
        clash = [p for p in _plugins if p.qualified == entry.qualified]
        if clash:
            raise UsageError(
                f"plugin '{entry.qualified}' is defined twice "
                f"(modules '{clash[0].module}' and '{entry.module}')"
            )
        _plugins.append(entry)
        return fn

    return register(func) if func is not None else register


def _origin_of(fn: Callable[..., Any]) -> tuple[str, str]:
    mod = fn.__module__ or ""
    if mod.startswith("ifdd.ct.plugins."):
        return "builtin", mod.rsplit(".", 1)[-1]
    parts = mod.split(".")
    if parts[0] == _EXT_PACKAGE and len(parts) >= 3:
        return parts[1], parts[2]
    return "local", parts[-1]


def _params_of(fn: Callable[..., Any]) -> tuple[list[Param], bool]:
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception:  # unresolvable annotations: fall back to strings
        hints = {}
    positional = [
        p
        for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) < 2:
        raise TypeError(f"plugin {fn.__name__} must accept (records, ctx, ...)")
    params: list[Param] = []
    extra = False
    for p in list(sig.parameters.values())[2:]:
        if p.kind is p.VAR_KEYWORD:
            extra = True
        elif p.kind is p.VAR_POSITIONAL:
            continue
        else:
            tp, help_text = _unwrap(hints.get(p.name, str))
            params.append(Param(p.name, tp, p.default, help_text))
    return params, extra


def _unwrap(hint: Any) -> tuple[Any, str]:
    """Split ``Annotated[T, "help", ...]`` into T and its first string."""
    if typing.get_origin(hint) is typing.Annotated:
        tp, *metadata = typing.get_args(hint)
        texts = [m for m in metadata if isinstance(m, str)]
        return tp, " ".join(texts[0].split()) if texts else ""
    return hint, ""


# --------------------------------------------------------------------------
# type conversion

_TRUE = {"1", "true", "yes", "on", "y"}
_FALSE = {"0", "false", "no", "off", "n"}
_NONE = {"", "none", "null"}


def convert(value: Any, tp: Any, where: str) -> Any:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        if value is None or (isinstance(value, str) and value.lower() in _NONE):
            if type(None) in args:
                return None
        inner = [a for a in args if a is not type(None)]
        if len(inner) == 1:
            return convert(value, inner[0], where)
        return value
    try:
        if tp is bool:
            if isinstance(value, bool):
                return value
            text = str(value).lower()
            if text in _TRUE:
                return True
            if text in _FALSE:
                return False
            raise ValueError(value)
        if tp in (int, float, str):
            return tp(value)
        if tp is Path:
            return Path(str(value))
    except (TypeError, ValueError):
        raise UsageError(
            f"parameter {where}: '{value}' is not a valid {_type_name(tp)}"
        ) from None
    return value


def _type_name(tp: Any) -> str:
    if typing.get_origin(tp) in (typing.Union, types.UnionType):
        return " | ".join(_type_name(a) for a in typing.get_args(tp))
    if tp is type(None):
        return "None"
    return getattr(tp, "__name__", str(tp))


# --------------------------------------------------------------------------
# discovery


def discover(force: bool = False) -> None:
    """Import every plugin module of every origin exactly once."""
    global _discovered, _current, _builtin_loaded
    if _discovered and not force:
        return
    if force:
        # Built-in modules stay loaded; private and local ones are read again.
        _plugins[:] = [p for p in _plugins if p.origin == "builtin"]
        _unavailable[:] = [u for u in _unavailable if u[0] == "builtin"]
        for mod in [m for m in sys.modules if m.startswith(_EXT_PACKAGE + ".")]:
            del sys.modules[mod]
    _discovered = True

    if not _builtin_loaded:
        _builtin_loaded = True
        from . import plugins as builtin_package

        for info in pkgutil.iter_modules(builtin_package.__path__):
            if info.name.startswith("_"):  # pragma: no cover - the package has none
                continue
            _current = ("builtin", info.name)
            try:
                importlib.import_module(f"{builtin_package.__name__}.{info.name}")
            except Exception as err:  # pragma: no cover  # noqa: BLE001 - report, never crash discovery
                _unavailable.append(("builtin", info.name, _reason(err)))
            finally:
                _current = None

    _ensure_package(_EXT_PACKAGE)
    for origin, dirs in (("private", [config.private_dir()]), ("local", config.plugin_path())):
        _ensure_package(f"{_EXT_PACKAGE}.{origin}")
        for directory in dirs:
            if Path(directory).is_dir():
                _load_directory(origin, Path(directory))


def _load_directory(origin: str, directory: Path) -> None:
    global _current
    for info in sorted(pkgutil.iter_modules([str(directory)]), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        full = f"{_EXT_PACKAGE}.{origin}.{info.name}"
        if full in sys.modules:
            _unavailable.append(
                (origin, info.name, f"module name used twice ({directory})")
            )
            continue
        path = directory / info.name
        location = path / "__init__.py" if info.ispkg else path.with_suffix(".py")
        spec = importlib.util.spec_from_file_location(
            full,
            location,
            submodule_search_locations=[str(path)] if info.ispkg else None,
        )
        if spec is None or spec.loader is None:  # pragma: no cover - defensive, .py and packages only
            _unavailable.append((origin, info.name, "cannot be loaded"))
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        _current = (origin, info.name)
        try:
            spec.loader.exec_module(module)
        except Exception as err:  # noqa: BLE001
            del sys.modules[full]
            _unavailable.append((origin, info.name, _reason(err)))
        finally:
            _current = None


def _ensure_package(name: str) -> None:
    if name not in sys.modules:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package


def _reason(err: Exception) -> str:
    return f"{type(err).__name__}: {err}"


# --------------------------------------------------------------------------
# lookup


def all_plugins() -> list[Plugin]:
    discover()
    order = {o: i for i, o in enumerate(ORIGINS)}
    return sorted(_plugins, key=lambda p: (order.get(p.origin, 9), p.name))


def unavailable() -> list[tuple[str, str, str]]:
    discover()
    return list(_unavailable)


def resolve(address: str) -> Plugin:
    """Find exactly one plugin for a name as typed by the user."""
    discover()
    matches = [p for p in _plugins if address in p.addresses]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = ", ".join(sorted(f"{p.origin}.{p.module}.{p.name}" for p in matches))
        raise UsageError(f"'{address}' is ambiguous, use one of: {options}")
    names = sorted({a for p in _plugins for a in (p.name, p.qualified)})
    hint = difflib.get_close_matches(address, names, n=3)
    message = f"unknown plugin or file '{address}'"
    if hint:
        message += f" - did you mean: {', '.join(hint)}?"
    if _unavailable:
        message += " (some plugin modules failed to load, see --list)"
    raise UsageError(message)

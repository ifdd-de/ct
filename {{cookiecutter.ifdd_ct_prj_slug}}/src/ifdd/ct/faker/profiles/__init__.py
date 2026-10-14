"""Registry of faker profiles.

Built-in profiles live in this package. Private and local plugin modules can
add more with :func:`ifdd.ct.faker.register_profile`; they are registered
when plugin discovery imports those modules.
"""

from __future__ import annotations

import importlib
import pkgutil

from ...errors import UsageError

_profiles: dict = {}
_builtin_loaded = False


def register(profile):
    existing = _profiles.get(profile.name)
    if existing is not None and existing is not profile and not _reloadable(existing):
        raise UsageError(f"faker profile '{profile.name}' is registered twice")
    _profiles[profile.name] = profile
    return profile


def _reloadable(profile) -> bool:
    """Profiles from private/local modules may be replaced when they are read again."""
    return str(getattr(profile.populate, "__module__", "")).startswith("ifdd_ct_ext.")


def _load() -> None:
    global _builtin_loaded
    if not _builtin_loaded:
        _builtin_loaded = True
        for info in pkgutil.iter_modules(__path__):
            importlib.import_module(f"{__name__}.{info.name}")
    from ...registry import discover

    discover()  # private/local modules may register profiles


def all_profiles() -> list:
    _load()
    return [_profiles[k] for k in sorted(_profiles)]


def get(name: str):
    _load()
    if name not in _profiles:
        raise UsageError(f"unknown faker profile '{name}' (available: {', '.join(sorted(_profiles))})")
    return _profiles[name]

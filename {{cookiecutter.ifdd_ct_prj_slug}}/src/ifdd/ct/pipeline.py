"""Parse steps and run them as a chain.

A step is either a plugin call or a file:

``name``                 plugin without parameters
``name:key=value,k2=v2`` plugin with parameters; ',' in a value as %2C
``path/to/file.json``    first step: read it; last step: write to it
``path/to/directory``    first step: read every .json/.jsonld/.yaml below it

Between the steps flows a list of records (JSON objects). If the first step
is not a source and data is piped in, stdin is read first. If the last step
is not a sink, the records are printed to stdout as JSON.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import unquote

import yaml

from .context import Context
from .errors import CtError, UsageError
from .registry import Plugin, resolve

log = logging.getLogger("ifdd.ct")

DATA_SUFFIXES = {".json", ".jsonld", ".yaml", ".yml"}


@dataclass
class Step:
    text: str
    plugin: Plugin | None = None
    params: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @property
    def label(self) -> str:
        return self.plugin.name if self.plugin else str(self.path)


# --------------------------------------------------------------------------
# parsing


def parse_step(text: str, params: dict[str, Any] | None = None) -> Step:
    """Turn one command-line argument (or pipeline entry) into a Step."""
    text = text.strip()
    if not text:
        raise UsageError("empty step")
    if params is None and _looks_like_path(text):
        return Step(text, path=Path(text))
    name, _, raw = text.partition(":")
    parsed = dict(params or {})
    if raw:
        for item in raw.split(","):
            if not item:
                continue
            key, sep, value = item.partition("=")
            if not sep or not key:
                raise UsageError(
                    f"bad parameter '{item}' in '{text}' - use name:key=value,key2=value2"
                )
            parsed[key.strip()] = unquote(value)
    found = resolve(name)
    return Step(text, plugin=found, params=found.bind(parsed))


def _looks_like_path(text: str) -> bool:
    path = Path(text)
    if path.exists():
        return True
    return ":" not in text and ("/" in text or path.suffix in DATA_SUFFIXES)


def load_pipeline(path: str | Path) -> list[Step]:
    """Read a pipeline file: a list of steps, optionally under 'steps:'."""
    file = Path(path)
    if not file.is_file():
        raise UsageError(f"pipeline file not found: {file}")
    try:
        content = yaml.safe_load(file.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise UsageError(f"{file}: invalid YAML: {err}") from None
    entries = content.get("steps") if isinstance(content, dict) else content
    if not isinstance(entries, list) or not entries:
        raise UsageError(f"{file}: expected a non-empty list of steps")
    steps: list[Step] = []
    for entry in entries:
        if isinstance(entry, str):
            steps.append(parse_step(entry))
        elif isinstance(entry, dict) and len(entry) == 1:
            (name, params), = entry.items()
            if params is not None and not isinstance(params, dict):
                raise UsageError(f"{file}: parameters of '{name}' must be a mapping")
            steps.append(parse_step(str(name), params or {}))
        else:
            raise UsageError(f"{file}: cannot read step {entry!r}")
    return steps


# --------------------------------------------------------------------------
# files


def read_path(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        files = sorted(
            p for p in path.rglob("*")
            if p.is_file() and p.suffix in DATA_SUFFIXES
            and not any(part.startswith(".") for part in p.relative_to(path).parts)
        )
        if not files:
            raise CtError(f"no .json/.jsonld/.yaml files below {path}")
        records: list[dict[str, Any]] = []
        for file in files:
            records.extend(read_path(file))
        return records
    if not path.is_file():
        raise UsageError(f"file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except (ValueError, yaml.YAMLError) as err:
        raise CtError(f"{path}: {err}") from None
    return normalize(data, str(path))


def write_path(path: Path, records: list[dict[str, Any]]) -> None:
    if path.is_dir():
        raise UsageError(f"{path} is a directory - give a file name to write to")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        if path.suffix in (".yaml", ".yml"):
            yaml.safe_dump(records, fh, sort_keys=False, allow_unicode=True)
        else:
            json.dump(records, fh, indent=2, ensure_ascii=False)
            fh.write("\n")


def normalize(data: Any, where: str) -> list[dict[str, Any]]:
    """The one rule for what flows between steps: a list of objects."""
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise CtError(f"{where} produced {type(data).__name__}, expected a list of objects")


# --------------------------------------------------------------------------
# running


def run(
    steps: list[Step],
    ctx: Context | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> list[dict[str, Any]]:
    if not steps:
        raise UsageError("no steps given - try --list")
    ctx = ctx or Context()
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    for index, step in enumerate(steps):
        if step.path is not None and 0 < index < len(steps) - 1:
            raise UsageError(
                f"'{step.text}': files can only be the first (read) or last (write) step"
            )

    records: list[dict[str, Any]] = []
    first = steps[0]
    if first.plugin is not None and not first.plugin.source and _has_input(stdin):
        text = stdin.read()
        if text.strip():
            try:
                records = normalize(json.loads(text), "stdin")
            except ValueError as err:
                raise CtError(f"stdin is not JSON: {err}") from None
        log.info("read %d records from stdin", len(records))

    total = len(steps)
    for index, step in enumerate(steps, 1):
        if step.path is not None:
            if index == 1:
                records = read_path(step.path)
                log.info("step %d/%d read %s: %d records", index, total, step.path, len(records))
            else:
                write_path(step.path, records)
                log.info("step %d/%d wrote %d records to %s", index, total, len(records), step.path)
            continue
        log.info("step %d/%d %s: %d records in", index, total, step.plugin.name, len(records))
        log.debug("step %d/%d %s: parameters %s", index, total, step.plugin.qualified, step.params)
        result = step.plugin.func(records, ctx.for_step(step.plugin.name), **step.params)
        records = normalize(result, f"plugin '{step.plugin.name}'")

    last = steps[-1]
    if last.plugin is not None and not last.plugin.sink:
        json.dump(records, stdout, indent=2, ensure_ascii=False)
        stdout.write("\n")
    log.info("done: %d records", len(records))
    return records


def _has_input(stdin: TextIO) -> bool:
    try:
        return not stdin.isatty()
    except (AttributeError, ValueError):
        return False

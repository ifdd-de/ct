"""Plugin reference as Markdown: ``ifdd-ct --markdown``.

Writes one MyST Markdown page for Sphinx (myst-parser): the command line help
and every plugin found in this environment (built-in, private, local), each
with its docstring, its parameters and how to call it. Plugins document
themselves with Python means only:

* the first docstring line is the summary, the rest is shown as written;
* parameters come from the signature: name, type, default, and an optional
  help text given with ``typing.Annotated[type, "help"]``;
* ``describe_extra`` (a function returning text) adds generated details,
  e.g. the faker profiles.

Labels start with ``ifdd-ct-`` so that the page fits into the full
documentation: ``ifdd-ct-plugins`` for the page, ``ifdd-ct-plugin-<origin>-<name>``
for each plugin. Text from docstrings goes into ``text`` blocks verbatim;
text in tables and paragraphs is escaped.
"""

from __future__ import annotations

import argparse
import functools
import inspect
import re

from . import __version__
from .registry import Plugin, all_plugins, unavailable

HELP_WIDTH = 80
REF = "{ref}"  # MyST role (kept out of f-strings: the template renders braces)
_ESCAPE = re.compile(r"([\\`*_{}\[\]<>|#$~])")
_LABEL_CHARS = re.compile(r"[^a-z0-9-]+")


def escape(text: str) -> str:
    """Escape Markdown punctuation in running text and table cells."""
    return _ESCAPE.sub(r"\\\1", " ".join(str(text).split()))


def code(text: str, table: bool = False) -> str:
    """Inline code; in a table cell its pipes are escaped."""
    text = str(text)
    ticks = "`" * (max((len(m) for m in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    span = f"{ticks}{pad}{text}{pad}{ticks}"
    return span.replace("|", "\\|") if table else span


def block(text: str, lang: str = "text") -> list[str]:
    """A fenced block, longer than any backtick run inside the text."""
    fence = "`" * max(3, max((len(m) for m in re.findall(r"`+", text)), default=0) + 1)
    return [f"{fence}{lang}", text.rstrip("\n"), fence]


def label(plugin: Plugin) -> str:
    name = _LABEL_CHARS.sub("-", f"{plugin.origin}-{plugin.name}".lower()).strip("-")
    return f"ifdd-ct-plugin-{name}"


def usage(plugin: Plugin) -> str:
    """Call syntax of a step, e.g. ``where:key=STR,value=STR`` or ``head[:count=INT]``.

    Optional parameters are in brackets; any of them can be left out.
    """
    def part(p) -> str:
        names = [n for n in p.type_name.split(" | ") if n != "None"] or ["VALUE"]
        return f"{p.name}={'|'.join(names).upper()}"

    required = [part(p) for p in plugin.params if p.required]
    optional = [part(p) for p in plugin.params if not p.required]
    if plugin.extra_params:
        optional.append("KEY=VALUE...")
    if required:
        return f"{plugin.name}:{','.join(required)}" + "".join(f"[,{o}]" for o in optional)
    return f"{plugin.name}[:{','.join(optional)}]" if optional else plugin.name


def cli_help(parser: argparse.ArgumentParser) -> str:
    """The --help text with a fixed width and without colour."""
    parser.formatter_class = functools.partial(parser.formatter_class, width=HELP_WIDTH)
    parser.color = False  # Python 3.14+ colours help; older versions ignore it
    return parser.format_help()


def _default(p) -> str:
    return "(required)" if p.required else code(repr(p.default), table=True)


def plugin_section(plugin: Plugin) -> list[str]:
    doc = inspect.getdoc(plugin.func) or ""
    summary, _, rest = doc.partition("\n")
    role = ", ".join(r for r, on in (("source", plugin.source), ("sink", plugin.sink)) if on)
    lines = [f"({label(plugin)})=", f"### {code(plugin.qualified)}", ""]
    if summary:
        lines += [escape(summary), ""]
    lines.append(f"- Origin: {plugin.origin}, module {code(plugin.module)}")
    if role:
        lines.append(f"- Role: {role}")
    addresses = sorted(plugin.addresses, key=lambda a: (len(a), a))
    lines += [
        "- Address: " + ", ".join(code(a) for a in addresses),
        f"- Call: {code(usage(plugin))}",
        "",
    ]
    if rest.strip():
        lines += [*block(rest.strip("\n")), ""]
    if plugin.params or plugin.extra_params:
        lines += ["| Parameter | Type | Default | Description |", "|---|---|---|---|"]
        for p in plugin.params:
            lines.append(
                f"| {code(p.name, True)} | {code(p.type_name, True)} | {_default(p)} "
                f"| {escape(p.help)} |"
            )
        if plugin.extra_params:
            lines.append("| `KEY=VALUE` | | | further parameters are accepted (see above) |")
    else:
        lines.append("No parameters.")
    lines.append("")
    extra = getattr(plugin.func, "describe_extra", None)
    if callable(extra):
        lines += [*block(str(extra())), ""]
    return lines


def render(parser: argparse.ArgumentParser) -> str:
    plugins = all_plugins()
    problems = unavailable()
    lines = [
        "(ifdd-ct-plugins)=",
        "# Plugin reference",
        "",
        f"Generated by `ifdd-ct --markdown` (ifdd-ct {escape(__version__)}) from the",
        "plugins found in that environment: built-in, private",
        "(`IFDD_CT_PRIVATE_DIR`) and local (`IFDD_CT_PLUGIN_PATH`). Generate it",
        "again instead of editing it.",
        "",
        "## Command line",
        "",
        *block(cli_help(parser)),
        "",
        "## Plugins",
        "",
        "| Plugin | Role | Summary |",
        "|---|---|---|",
    ]
    for p in plugins:
        role = "source" if p.source else "sink" if p.sink else ""
        lines.append(f"| {REF}`{p.qualified} <{label(p)}>` | {role} | {escape(p.summary)} |")
    lines.append("")
    for p in plugins:
        lines += plugin_section(p)
    if problems:
        lines += [
            "## Not available",
            "",
            "Modules that failed to load; their plugins are missing above.",
            "",
            "| Origin | Module | Reason |",
            "|---|---|---|",
        ]
        lines += [f"| {o} | {code(m, True)} | {escape(r)} |" for o, m, r in problems]
        lines.append("")
    return "\n".join(lines)

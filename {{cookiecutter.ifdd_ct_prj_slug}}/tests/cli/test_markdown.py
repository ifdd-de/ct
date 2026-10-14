"""ifdd-ct --markdown: the plugin reference as one MyST Markdown page.

Whether the page builds with Sphinx is checked by the template CI (it needs
Sphinx, which the instance does not install).
"""

import re

import pytest

from ifdd.ct import registry
from ifdd.ct.cli import main
from ifdd.ct.markdown import block, code, escape, label, usage

LABEL = re.compile(r"^\(([^)]+)\)=$", re.MULTILINE)


def markdown(capsys) -> str:
    assert main(["--markdown"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    return out


def test_page_has_label_title_help_and_every_plugin(capsys):
    page = markdown(capsys)
    assert page.startswith("(ifdd-ct-plugins)=\n# Plugin reference\n")
    assert "## Command line\n\n```text\nusage: ifdd-ct " in page
    for p in registry.all_plugins():
        assert f"({label(p)})=\n### `{p.qualified}`" in page
        assert "{ref}" + f"`{p.qualified} <{label(p)}>`" in page
    assert "(ifdd-ct-plugin-local-stamp)=" in page  # plugins/ of the instance


def test_labels_are_unique_and_prefixed(capsys):
    labels = LABEL.findall(markdown(capsys))
    assert len(labels) == len(set(labels))
    assert all(name.startswith("ifdd-ct-") for name in labels)


def test_plugin_section_with_parameters_and_extra_text(capsys):
    page = markdown(capsys)
    section = page.split("(ifdd-ct-plugin-builtin-faker)=")[1].split("\n(ifdd-ct-plugin-")[0]
    assert "- Role: source" in section
    assert "- Call: `faker[:profile=STR,seed=INT,KEY=VALUE...]`" in section
    assert "| `seed` | `int \\| None` | `None` | same seed, same data" in section
    assert "| `KEY=VALUE` |" in section
    assert "energy-grid: product=" in section  # describe_extra: the profiles


def test_required_parameters(capsys):
    section = markdown(capsys).split("(ifdd-ct-plugin-builtin-where)=")[1]
    assert "- Call: `where:key=STR,value=STR`" in section
    assert "| `key` | `str` | (required) | top-level key of a record |" in section


def test_output_does_not_depend_on_the_terminal(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("FORCE_COLOR", "1")
    wide = markdown(capsys)
    monkeypatch.setenv("COLUMNS", "40")
    narrow = markdown(capsys)
    assert wide == narrow
    assert "\x1b[" not in wide
    help_text = wide.split("```text\n", 1)[1].split("\n```", 1)[0]
    assert max(len(line) for line in help_text.splitlines()) <= 80


def test_modules_that_failed_are_listed(capsys, plugin_dir):
    plugin_dir(broken="import nope\n")
    page = markdown(capsys)
    assert "## Not available" in page
    assert "| local | `broken` | ModuleNotFoundError: No module named 'nope' |" in page


def test_no_section_for_unavailable_modules_when_all_load(capsys):
    assert "## Not available" not in markdown(capsys)


def test_text_from_plugins_cannot_break_the_page(capsys, plugin_dir):
    plugin_dir(odd='''
from typing import Annotated

from ifdd.ct import plugin

@plugin(name="odd_name!")
def odd(records, ctx, pattern: Annotated[str, "a|b or *c* <d>"] = "x|y"):
    """Keep a | b and *c* {d}.

    ```
    a fence inside the docstring
    ```
    """
    return records
''')
    page = markdown(capsys)
    section = page.split("(ifdd-ct-plugin-local-odd-name)=")[1]
    assert "Keep a \\| b and \\*c\\* \\{d\\}." in section
    assert "| `pattern` | `str` | `'x\\|y'` | a\\|b or \\*c\\* \\<d\\> |" in section
    assert "````text\n```\na fence inside the docstring\n```\n````" in section


@pytest.mark.parametrize("text, expected", [
    ("plain", "`plain`"),
    ("a`b", "``a`b``"),
    ("`x", "`` `x ``"),
])
def test_code_spans(text, expected):
    assert code(text) == expected


def test_code_spans_in_tables_escape_pipes():
    assert code("int | None", table=True) == "`int \\| None`"
    assert code("int | None") == "`int | None`"


def test_escape_folds_whitespace_and_escapes_punctuation():
    assert escape("a  *b*\n_c_ #1") == "a \\*b\\* \\_c\\_ \\#1"


def test_block_fence_is_longer_than_any_inside():
    assert block("x ```` y") == ["`````text", "x ```` y", "`````"]


def test_usage_forms(plugin_dir):
    plugin_dir(forms='''
from ifdd.ct import plugin

@plugin
def nothing(records, ctx):
    return records

@plugin
def mixed(records, ctx, key: str, limit: int | None = None, **rest):
    return records
''')
    assert usage(registry.resolve("nothing")) == "nothing"
    assert usage(registry.resolve("mixed")) == "mixed:key=STR[,limit=INT][,KEY=VALUE...]"


def test_plugin_without_docstring(capsys, plugin_dir):
    plugin_dir(bare="from ifdd.ct import plugin\n"
                    "@plugin\ndef bare(records, ctx):\n    return records\n")
    section = markdown(capsys).split("(ifdd-ct-plugin-local-bare)=")[1]
    assert section.startswith("\n### `local.bare`\n\n- Origin: local, module `bare`")

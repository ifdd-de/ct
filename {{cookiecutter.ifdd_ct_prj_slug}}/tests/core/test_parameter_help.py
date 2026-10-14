"""Help texts of parameters, given with typing.Annotated."""

import pytest

from ifdd.ct import registry

ANNOTATED_PLUGIN = '''
from typing import Annotated

from ifdd.ct import plugin

@plugin
def scale(records, ctx,
          factor: Annotated[int, "multiply by this"] = 2,
          unit: Annotated[str, 42, "first   string\\n  counts"] = "m",
          plain: bool = False,
          bare: Annotated[str, 7] = ""):
    """Scale the numbers."""
    return [r * factor for r in records]
'''


@pytest.fixture
def scale(plugin_dir):
    plugin_dir(scaling=ANNOTATED_PLUGIN)
    return registry.resolve("scale")


def test_help_text_and_type_come_from_annotated(scale):
    factor, unit, plain, bare = scale.params
    assert (factor.type, factor.help) == (int, "multiply by this")
    assert (unit.type, unit.help) == (str, "first string counts")  # whitespace folded
    assert (plain.type, plain.help) == (bool, "")
    assert (bare.type, bare.help) == (str, "")  # no string in the metadata


def test_annotated_values_are_converted_like_plain_ones(scale):
    assert scale.bind({"factor": "5"}) == {"factor": 5}


def test_describe_shows_the_help_next_to_the_parameter(scale):
    text = scale.describe()
    assert "  factor: int = 2  multiply by this" in text
    assert "  plain: bool = False\n" in text


def test_annotated_works_with_postponed_annotations(plugin_dir):
    plugin_dir(late="from __future__ import annotations\n" + ANNOTATED_PLUGIN)
    assert registry.resolve("scale").params[0].help == "multiply by this"


@pytest.mark.parametrize("plugin", [
    p for p in registry.all_plugins() if p.origin == "builtin"
], ids=lambda p: p.name)
def test_every_builtin_parameter_has_a_help_text(plugin):
    assert [p.name for p in plugin.params if not p.help] == []

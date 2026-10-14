"""Conversion of textual parameters to the types declared by a plugin."""

from pathlib import Path
from typing import Optional

import pytest

from ifdd.ct import registry
from ifdd.ct.errors import UsageError
from ifdd.ct.registry import convert


@pytest.mark.parametrize("value, type_, expected", [
    ("42", int, 42),
    (42, int, 42),
    ("2.5", float, 2.5),
    ("text", str, "text"),
    (7, str, "7"),
    ("true", bool, True),
    ("Yes", bool, True),
    ("on", bool, True),
    ("1", bool, True),
    ("false", bool, False),
    ("no", bool, False),
    ("0", bool, False),
    (True, bool, True),
    ("out/x.json", Path, Path("out/x.json")),
    ("5", int | None, 5),
    ("", int | None, None),
    ("none", Optional[int], None),
    (None, int | None, None),
    ("anything", list, "anything"),  # unknown types are passed through
])
def test_convert(value, type_, expected):
    assert convert(value, type_, "p:x") == expected


@pytest.mark.parametrize("value, type_", [("many", int), ("x", float), ("maybe", bool)])
def test_invalid_values_are_usage_errors(value, type_):
    with pytest.raises(UsageError, match=f"'{value}' is not a valid {type_.__name__}"):
        convert(value, type_, "p:x")


def test_bind_converts_known_parameters():
    assert registry.resolve("head").bind({"count": "3"}) == {"count": 3}


def test_bind_rejects_unknown_parameters_and_lists_valid_ones():
    with pytest.raises(UsageError, match="has no parameter 'lines' \\(valid: count\\)"):
        registry.resolve("head").bind({"lines": "3"})


def test_bind_requires_parameters_without_default():
    with pytest.raises(UsageError, match="needs: key, value"):
        registry.resolve("where").bind({})


def test_bind_passes_extra_parameters_when_accepted():
    bound = registry.resolve("faker").bind({"seed": "3", "product": "7"})
    assert bound == {"seed": 3, "product": "7"}


def test_none_text_stays_text_when_the_union_has_no_none():
    assert convert("none", int | str, "p:x") == "none"

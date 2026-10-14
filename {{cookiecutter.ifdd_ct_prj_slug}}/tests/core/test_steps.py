"""Parsing command-line steps and pipeline files."""

import pytest

from ifdd.ct.errors import UsageError
from ifdd.ct.pipeline import load_pipeline, parse_step


# -- command-line steps ----------------------------------------------------

@pytest.mark.parametrize("text, name, params", [
    ("head", "head", {}),
    ("head:count=2", "head", {"count": 2}),
    ("head:count=2,", "head", {"count": 2}),
    ("where:key=@id,value=https://x/a=b%2Cc", "where", {"key": "@id", "value": "https://x/a=b,c"}),
    ("  head  ", "head", {}),
    ("builtin.head:count=1", "head", {"count": 1}),
])
def test_plugin_steps(text, name, params):
    step = parse_step(text)
    assert (step.plugin.name, step.params, step.path) == (name, params, None)


@pytest.mark.parametrize("text, message", [
    ("", "empty step"),
    ("head:count", "bad parameter 'count'"),
    ("head:=3", "bad parameter '=3'"),
    ("head:lines=3", "no parameter 'lines'"),
    ("nope", "unknown plugin or file 'nope'"),
])
def test_bad_steps(text, message):
    with pytest.raises(UsageError, match=message):
        parse_step(text)


@pytest.mark.parametrize("text", [
    "data/examples/json-ld",           # existing directory
    "data/pipelines/load-examples.yaml",  # existing file
    "out/result.json",                 # new file, recognised by its suffix
    "out/result.jsonld",
    "out/result.yml",
    "somewhere/new",                   # contains a slash
])
def test_file_steps(text):
    step = parse_step(text)
    assert step.plugin is None and str(step.path) == text and step.label == text


def test_parameters_given_separately_are_merged():
    step = parse_step("head", {"count": "5"})
    assert step.params == {"count": 5}


# -- pipeline files --------------------------------------------------------

def write(tmp_path, text):
    file = tmp_path / "pipeline.yaml"
    file.write_text(text)
    return file


def test_steps_as_strings_and_mappings(tmp_path):
    steps = load_pipeline(write(tmp_path, """
steps:
  - faker: {seed: 1, product: 1}
  - head:count=3
  - count:
  - out.json
"""))
    assert [s.label for s in steps] == ["faker", "head", "count", "out.json"]
    assert steps[0].params == {"seed": 1, "product": 1}
    assert steps[1].params == {"count": 3}


def test_plain_list_without_steps_key(tmp_path):
    assert load_pipeline(write(tmp_path, "- count\n"))[0].plugin.name == "count"


def test_yaml_types_are_accepted(tmp_path):
    step = load_pipeline(write(tmp_path, "- put: {dry_run: true}\n"))[0]
    assert step.params == {"dry_run": True}


def test_example_pipelines_of_the_instance_are_valid():
    for name in ("load-examples", "generate-energy-grid", "datacenter-example"):
        assert load_pipeline(f"data/pipelines/{name}.yaml")


@pytest.mark.parametrize("text, message", [
    ("steps: [", "invalid YAML"),
    ("steps: []", "non-empty list"),
    ("just text", "non-empty list"),
    ("- 42", "cannot read step"),
    ("- {a: 1, b: 2}", "cannot read step"),
    ("- head: [1, 2]", "must be a mapping"),
])
def test_bad_pipeline_files(tmp_path, text, message):
    with pytest.raises(UsageError, match=message):
        load_pipeline(write(tmp_path, text))


def test_missing_pipeline_file():
    with pytest.raises(UsageError, match="pipeline file not found"):
        load_pipeline("nowhere.yaml")

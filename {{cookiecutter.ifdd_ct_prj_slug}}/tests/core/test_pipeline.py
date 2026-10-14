"""Running a chain of steps: input, output, files and the record rules."""

import json

import pytest
import yaml
from support import run_steps
from support.runner import Pipe, printed_json

from ifdd.ct.errors import CtError, UsageError
from ifdd.ct.pipeline import parse_step, run

TWO = [{"a": 1}, {"a": 2}]
NO_ENTITIES = "product=0,function=0,location=0,organisation=0"


# -- stdin and stdout ------------------------------------------------------

def test_piped_input_is_read_before_a_transform():
    result, printed = run_steps("head:count=1", records=TWO)
    assert result == printed_json(printed) == [{"a": 1}]


def test_no_piped_input_means_no_records():
    result, printed = run_steps("count")
    assert result == [] and printed_json(printed) == []


def test_sources_leave_stdin_alone():
    result, _ = run_steps(f"faker:seed=1,{NO_ENTITIES}", records=TWO)
    assert result == []  # the piped records were not read


def test_empty_stdin_is_no_records(capsys):
    assert run([parse_step("count")], stdin=Pipe("  \n")) == []


def test_stdin_that_is_not_json_fails():
    with pytest.raises(CtError, match="stdin is not JSON"):
        run([parse_step("count")], stdin=Pipe("nope"))


def test_result_of_a_sink_is_not_printed():
    _, printed = run_steps("put:dry_run=true", records=[])
    assert printed == ""


@pytest.mark.parametrize("data, expected", [
    ({"a": 1}, [{"a": 1}]),
    ([{"a": 1}], [{"a": 1}]),
    (None, []),
])
def test_input_is_normalised_to_a_list(data, expected):
    assert run_steps("count", records=data)[0] == expected


def test_steps_share_the_context(plugin_dir):
    plugin_dir(share="""
from ifdd.ct import plugin

@plugin
def remember(records, ctx):
    ctx.shared["seen"] = len(records)
    return records

@plugin
def recall(records, ctx):
    return [{"seen": ctx.shared["seen"]}]
""")
    assert run_steps("remember", "recall", records=TWO)[0] == [{"seen": 2}]


def test_plugin_result_must_be_a_list_of_objects(plugin_dir):
    plugin_dir(bad="from ifdd.ct import plugin\n@plugin\ndef bad(records, ctx):\n    return 42\n")
    with pytest.raises(CtError, match="plugin 'bad' produced int"):
        run_steps("bad")


def test_no_steps():
    with pytest.raises(UsageError, match="no steps"):
        run([])


# -- files -----------------------------------------------------------------

def save(target, records):
    """Pipe RECORDS in and write them with a file as last step."""
    run_steps("head:count=100", str(target), records=records)


def test_a_single_file_step_reads(tmp_path):
    source = tmp_path / "in.json"
    source.write_text('[{"a": 1}]')
    assert run_steps(str(source), records=[{"ignored": True}])[0] == [{"a": 1}]


def test_read_a_directory_recursively():
    result, _ = run_steps("data/examples/json-ld")
    assert len(result) == 30
    assert all("@id" in r for r in result)


def test_hidden_files_and_other_suffixes_are_ignored(tmp_path):
    (tmp_path / "a.json").write_text('{"a": 1}')
    (tmp_path / "notes.txt").write_text("ignored")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "b.json").write_text('{"b": 1}')
    assert run_steps(str(tmp_path))[0] == [{"a": 1}]


def test_directory_without_data_files(tmp_path):
    with pytest.raises(CtError, match="no .json/.jsonld/.yaml files"):
        run_steps(str(tmp_path) + "/")


@pytest.mark.parametrize("suffix", [".json", ".jsonld", ".yaml", ".yml"])
def test_write_and_read_back(tmp_path, suffix):
    target = tmp_path / f"out{suffix}"
    save(target, TWO)
    assert run_steps(str(target))[0] == TWO


def test_written_json_is_readable_text(tmp_path):
    target = tmp_path / "out.json"
    save(target, [{"name": "Ümspannwerk"}])
    assert "Ümspannwerk" in target.read_text(encoding="utf-8")
    assert json.loads(target.read_text()) == [{"name": "Ümspannwerk"}]


def test_written_yaml_keeps_key_order(tmp_path):
    target = tmp_path / "out.yaml"
    save(target, [{"z": 1, "a": 2}])
    assert list(yaml.safe_load(target.read_text())[0]) == ["z", "a"]


def test_missing_parent_directories_are_created(tmp_path):
    target = tmp_path / "deep" / "er" / "out.json"
    save(target, TWO)
    assert target.exists()


def test_writing_to_a_directory_is_refused(tmp_path):
    with pytest.raises(UsageError, match="is a directory"):
        run_steps("head", str(tmp_path), records=TWO)


def test_reading_a_missing_file(tmp_path):
    with pytest.raises(UsageError, match="file not found"):
        run_steps(str(tmp_path / "missing.json"), "count")


def test_reading_a_broken_file(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{nope")
    with pytest.raises(CtError, match="broken.json"):
        run_steps(str(broken))


def test_reading_a_file_that_holds_no_objects(tmp_path):
    scalar = tmp_path / "scalar.json"
    scalar.write_text("42")
    with pytest.raises(CtError, match="expected a list of objects"):
        run_steps(str(scalar))


def test_files_only_first_or_last(tmp_path):
    with pytest.raises(UsageError, match="first \\(read\\) or last \\(write\\)"):
        run_steps("head", str(tmp_path / "x.json"), "count")


def test_read_transform_write(tmp_path):
    target = tmp_path / "products.json"
    run_steps("data/examples/json-ld/products", "head:count=2", str(target))
    assert len(json.loads(target.read_text())) == 2


def test_normalize_none_is_no_records():
    from ifdd.ct.pipeline import normalize

    assert normalize(None, "step") == []


@pytest.mark.parametrize("stream", [object(), "closed"])
def test_stdin_without_a_usable_isatty_is_no_input(stream):
    import io

    from ifdd.ct.pipeline import _has_input

    if stream == "closed":
        stream = io.StringIO()
        stream.close()
    assert _has_input(stream) is False

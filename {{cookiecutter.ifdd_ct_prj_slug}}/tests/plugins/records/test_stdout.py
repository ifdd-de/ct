"""stdout: print the records as JSON, pass them on."""

import json

from support import run_steps

TWO = [{"a": 1}, {"a": 2}]


def test_stdout_prints_pretty_json_by_default(capsys):
    run_steps("stdout", records=TWO)
    out = capsys.readouterr().out
    assert json.loads(out) == TWO
    assert "\n  " in out


def test_stdout_compact(capsys):
    run_steps("stdout:pretty=false", records=TWO)
    assert capsys.readouterr().out == '[{"a": 1}, {"a": 2}]\n'


def test_stdout_as_last_step_prints_once(capsys):
    _, printed = run_steps("stdout", records=TWO)
    assert printed == ""                           # no automatic second print
    assert capsys.readouterr().out.count('"a": 1') == 1


def test_stdout_between_steps_passes_records_on(capsys):
    result, printed = run_steps("stdout", "head:count=1", records=TWO)
    assert json.loads(capsys.readouterr().out) == TWO
    assert json.loads(printed) == result == [{"a": 1}]


def test_stdout_keeps_non_ascii(capsys):
    run_steps("stdout:pretty=false", records=[{"name": "Umspannwerk Süd"}])
    assert "Süd" in capsys.readouterr().out

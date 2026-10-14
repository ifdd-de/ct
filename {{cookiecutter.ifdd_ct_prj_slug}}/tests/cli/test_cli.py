"""The command line: options, output channels and exit codes.

Most tests call ``main()`` in-process (fast, counted by coverage); the last
ones start a real process to check the installed entry point.
"""

import io
import json
import os
import subprocess
import sys

import pytest

from ifdd.ct.cli import main


@pytest.fixture
def stdin(monkeypatch):
    """Set what the CLI reads from stdin; default is a terminal (nothing piped)."""

    class Pipe(io.StringIO):
        def isatty(self):
            return False

    def pipe(text: str):
        monkeypatch.setattr(sys, "stdin", Pipe(text))

    class Terminal(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdin", Terminal())
    return pipe


def run_cli(capsys, *args):
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


# -- normal runs -----------------------------------------------------------

def test_data_on_stdout_logs_on_stderr(capsys, stdin):
    stdin('[{"a": 1}, {"a": 2}]')
    code, out, err = run_cli(capsys, "-v", "head:count=1")
    assert code == 0
    assert json.loads(out) == [{"a": 1}]
    assert "step 1/1 head: 2 records in" in err


def test_pipeline_file(capsys, stdin, tmp_path):
    pipeline = tmp_path / "p.yaml"
    pipeline.write_text("steps:\n  - data/examples/json-ld/products\n  - count\n")
    code, out, err = run_cli(capsys, "-f", str(pipeline))
    assert code == 0 and "4 records" in err and len(json.loads(out)) == 4


@pytest.mark.parametrize("flags, shown, hidden", [
    ([], [], ["INFO", "DEBUG"]),
    (["-v"], ["INFO"], ["DEBUG"]),
    (["-vv"], ["INFO", "DEBUG"], []),
])
def test_verbosity(capsys, stdin, flags, shown, hidden):
    code, _, err = run_cli(capsys, *flags, "faker:seed=1,product=0,function=1,location=0,organisation=0")
    assert code == 0
    assert all(level in err for level in shown)
    assert not any(level in err for level in hidden)


def test_log_level_from_environment(capsys, stdin, monkeypatch):
    monkeypatch.setenv("IFDD_CT_LOG_LEVEL", "INFO")
    _, _, err = run_cli(capsys, "count")
    assert "INFO" in err


def test_quiet_shows_errors_only(capsys, stdin, monkeypatch):
    monkeypatch.setenv("IFDD_CT_LOG_LEVEL", "DEBUG")
    code, _, err = run_cli(capsys, "-q", "put:dry_run=true")
    assert code == 0 and err == ""


# -- information -----------------------------------------------------------

def test_list_shows_origins_roles_and_summaries(capsys):
    code, out, _ = run_cli(capsys, "--list")
    lines = {line.split()[0]: line for line in out.splitlines() if line.strip()}
    assert code == 0
    assert "source" in lines["builtin.faker"] and "sink" in lines["builtin.put"]
    assert "Keep the first COUNT records." in lines["builtin.head"]
    assert "local.stamp" in lines


def test_list_reports_modules_that_failed(capsys, plugin_dir):
    plugin_dir(broken="import nope\n")
    _, out, _ = run_cli(capsys, "--list")
    assert "not available:" in out and "local/broken: ModuleNotFoundError" in out


def test_describe(capsys):
    code, out, _ = run_cli(capsys, "--describe", "where")
    assert code == 0 and "key: str (required)" in out


def test_version(capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    assert capsys.readouterr().out.startswith("ifdd-ct ")


# -- errors and exit codes -------------------------------------------------

@pytest.mark.parametrize("args, code, message", [
    (["nope"], 2, "unknown plugin or file 'nope'"),
    (["head:lines=2"], 2, "no parameter 'lines'"),
    (["-f", "missing.yaml"], 2, "pipeline file not found"),
    (["-f", "data/pipelines/load-examples.yaml", "count"], 2, "either -f PIPELINE or steps"),
    ([], 2, "no steps given"),
    (["--describe", "nope"], 2, "unknown plugin"),
    (["data/examples/json-ld/products", "put:aspect=product"], 1, None),
])
def test_exit_codes(capsys, stdin, monkeypatch, args, code, message):
    monkeypatch.setenv("IFDD_CT_BE_URL", "http://127.0.0.1:9")  # nothing listens here
    monkeypatch.setenv("IFDD_CT_HTTP_TIMEOUT", "2")
    result, _, err = run_cli(capsys, *args)
    assert result == code
    if message:
        assert message in err


@pytest.mark.parametrize("step, code", [("check", 0), ("check:fail=true", 1)])
def test_check_warns_by_default_and_fails_on_request(capsys, stdin, step, code):
    result, _, err = run_cli(capsys, "tests/fixtures/documents/check-typo.jsonld", step)
    assert result == code
    assert "typo-1: undefined terms: nmae" in err


def test_stdin_that_is_not_json(capsys, stdin):
    stdin("not json")
    code, _, err = run_cli(capsys, "count")
    assert code == 1 and "stdin is not JSON" in err


def test_unexpected_errors_are_short_without_vv(capsys, stdin, plugin_dir):
    plugin_dir(crash="from ifdd.ct import plugin\n"
                     "@plugin\ndef crash(records, ctx):\n    raise KeyError('boom')\n")
    code, _, err = run_cli(capsys, "crash")
    assert code == 1
    assert "KeyError: 'boom'" in err and "run with -vv for the traceback" in err
    assert "Traceback" not in err


def test_tracebacks_with_vv(capsys, stdin, plugin_dir):
    plugin_dir(crash="from ifdd.ct import plugin, CtError\n"
                     "@plugin\ndef crash(records, ctx):\n    raise CtError('clean')\n")
    code, _, err = run_cli(capsys, "-vv", "crash")
    assert code == 1 and "Traceback" in err


def test_interrupt(capsys, stdin, plugin_dir):
    plugin_dir(stop="from ifdd.ct import plugin\n"
                    "@plugin\ndef stop(records, ctx):\n    raise KeyboardInterrupt\n")
    code, _, err = run_cli(capsys, "stop")
    assert code == 130 and "interrupted" in err


# -- a real process --------------------------------------------------------

def process(*args, stdin=""):
    return subprocess.run([sys.executable, "-m", "ifdd.ct", *args], input=stdin,
                          capture_output=True, text=True, timeout=60,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def test_module_entry_point():
    result = process("head:count=1", stdin='[{"a": 1}, {"a": 2}]')
    assert result.returncode == 0 and json.loads(result.stdout) == [{"a": 1}]


def test_console_script_is_installed():
    from importlib.metadata import entry_points

    [script] = [e for e in entry_points(group="console_scripts") if e.name == "ifdd-ct"]
    assert script.value == "ifdd.ct.cli:main"


def test_unexpected_errors_with_vv_show_the_traceback_without_the_hint(capsys, stdin, plugin_dir):
    plugin_dir(crash="from ifdd.ct import plugin\n"
                     "@plugin\ndef crash(records, ctx):\n    raise KeyError('boom')\n")
    code, _, err = run_cli(capsys, "-vv", "crash")
    assert code == 1 and "Traceback" in err and "run with -vv" not in err


def test_module_entry_point_in_process(capsys, monkeypatch):
    import runpy

    monkeypatch.setattr(sys, "argv", ["ifdd-ct", "--version"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("ifdd.ct", run_name="__main__")
    assert stop.value.code == 0 and capsys.readouterr().out.startswith("ifdd-ct ")


def test_version_of_a_source_tree_without_install(monkeypatch):
    import importlib
    import importlib.metadata

    import ifdd.ct

    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    try:
        assert importlib.reload(ifdd.ct).__version__ == "0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(ifdd.ct)
    assert ifdd.ct.__version__ != "0+unknown"

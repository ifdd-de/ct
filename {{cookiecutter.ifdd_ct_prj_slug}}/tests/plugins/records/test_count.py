"""count: report the number of records on stderr, pass them on."""

from support import run_steps

TWO = [{"a": 1}, {"a": 2}]


def test_count_prints_to_stderr(capsys):
    run_steps("count", records=TWO)
    assert capsys.readouterr().err == "2 records\n"


def test_count_passes_records_on_unchanged():
    result, printed = run_steps("count", records=TWO)
    assert result == TWO
    assert '"a": 1' in printed  # count is no sink: the records are still printed


def test_count_between_steps(capsys):
    result, _ = run_steps("count", "head:count=1", "count", records=TWO)
    assert capsys.readouterr().err == "2 records\n1 records\n"
    assert result == [{"a": 1}]

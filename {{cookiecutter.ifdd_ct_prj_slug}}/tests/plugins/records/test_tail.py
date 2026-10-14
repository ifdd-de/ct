"""tail: keep the last COUNT records."""

import pytest
from support import run_steps

FIVE = [{"n": i} for i in range(5)]


@pytest.mark.parametrize("step, expected", [
    ("tail", [1, 2, 3, 4]),          # default count is 4
    ("tail:count=2", [3, 4]),
    ("tail:count=9", [0, 1, 2, 3, 4]),
    ("tail:count=0", []),
])
def test_tail(step, expected):
    result, _ = run_steps(step, records=FIVE)
    assert [r["n"] for r in result] == expected


def test_tail_of_nothing():
    assert run_steps("tail", records=[])[0] == []

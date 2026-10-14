"""head: keep the first COUNT records."""

import pytest
from support import run_steps

FIVE = [{"n": i} for i in range(5)]


@pytest.mark.parametrize("step, expected", [
    ("head", [0, 1, 2, 3]),          # default count is 4
    ("head:count=2", [0, 1]),
    ("head:count=1", [0]),
    ("head:count=9", [0, 1, 2, 3, 4]),
    ("head:count=0", []),
])
def test_head(step, expected):
    result, _ = run_steps(step, records=FIVE)
    assert [r["n"] for r in result] == expected


def test_head_of_nothing():
    assert run_steps("head", records=[])[0] == []


def test_head_of_a_single_object():
    assert run_steps("head:count=1", records={"n": 0})[0] == [{"n": 0}]

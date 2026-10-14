"""where: keep records whose top-level KEY equals VALUE, compared as text."""

import pytest
from support import run_steps

from ifdd.ct.errors import UsageError

RECORDS = [
    {"objType": "Cable", "size": 3},
    {"objType": "Switch", "size": 3},
    {"objType": "Cable", "size": 5},
    {"size": 3},
]


@pytest.mark.parametrize("step, expected", [
    ("where:key=objType,value=Cable", [RECORDS[0], RECORDS[2]]),
    ("where:key=objType,value=Transformer", []),
    ("where:key=size,value=3", [RECORDS[0], RECORDS[1], RECORDS[3]]),   # numbers as text
    ("where:key=objType,value=None", [RECORDS[3]]),                    # missing key is "None"
])
def test_where(step, expected):
    assert run_steps(step, records=RECORDS)[0] == expected


def test_where_needs_key_and_value():
    with pytest.raises(UsageError, match="needs: key, value"):
        run_steps("where")

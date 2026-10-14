"""Run a pipeline in-process, the way the CLI does, and capture its output.

    result, printed = run_steps("head:count=1", records=[{"a": 1}, {"a": 2}])

``records`` is piped in as stdin (as JSON); leave it out to simulate a
terminal, i.e. no piped input.
"""

from __future__ import annotations

import io
import json
from typing import Any

from ifdd.ct.context import Context
from ifdd.ct.pipeline import parse_step, run


class Pipe(io.StringIO):
    def isatty(self) -> bool:
        return False


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def run_steps(*steps: str, records: Any = None, ctx: Context | None = None) -> tuple[list, str]:
    stdin = Terminal() if records is None else Pipe(json.dumps(records))
    stdout = io.StringIO()
    result = run([parse_step(s) for s in steps], ctx=ctx, stdin=stdin, stdout=stdout)
    return result, stdout.getvalue()


def printed_json(text: str) -> Any:
    return json.loads(text) if text.strip() else None

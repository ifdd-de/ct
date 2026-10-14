"""Exceptions with a defined meaning for the CLI.

Plugins raise these instead of calling ``exit()``: the CLI turns them into a
short message and an exit code, and shows the traceback only with ``-vv``.
"""


class CtError(Exception):
    """A step failed at run time (exit code 1)."""

    exit_code = 1


class UsageError(CtError):
    """The command line or pipeline file is wrong (exit code 2)."""

    exit_code = 2

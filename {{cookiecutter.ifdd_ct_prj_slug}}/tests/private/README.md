# tests/private/

Tests for this instance's own plugins (`private/` and `plugins/`). This
directory is on the cruft skip list: template updates never touch it.

Use the fixtures from `tests/conftest.py` and the helpers from `tests/support/`,
e.g. `run_steps("my-plugin:x=1", records=[...])`.

`test_example_stamp.py` tests the example plugin `plugins/example_stamp.py`;
delete both together.

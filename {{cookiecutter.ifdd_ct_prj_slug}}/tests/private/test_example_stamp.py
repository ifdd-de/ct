"""stamp (plugins/example_stamp.py): the example of a local plugin."""

from support import run_steps


def test_stamp_sets_a_field_in_every_record():
    result, _ = run_steps("stamp:key=source,value=import", records=[{"a": 1}, {"a": 2}])
    assert result == [{"a": 1, "source": "import"}, {"a": 2, "source": "import"}]


def test_stamp_defaults():
    assert run_steps("stamp", records=[{}])[0] == [{"note": "example"}]


def test_stamp_is_a_local_plugin():
    from ifdd.ct.registry import resolve

    assert resolve("stamp").qualified == "local.stamp"

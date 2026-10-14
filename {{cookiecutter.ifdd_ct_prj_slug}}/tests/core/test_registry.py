"""Plugin registration, discovery and name resolution."""

import pytest

from ifdd.ct import registry
from ifdd.ct.errors import UsageError

BUILTIN = ["head", "tail", "where", "count", "stdout", "expand", "compact", "node", "check",
           "put", "patch", "post", "get", "faker"]

SIMPLE_PLUGIN = """
from ifdd.ct import plugin

@plugin
def {name}(records, ctx):
    \"\"\"{doc}\"\"\"
    return records
"""


def simple(name, doc="a test plugin"):
    return SIMPLE_PLUGIN.format(name=name, doc=doc)


# -- built-in plugins ------------------------------------------------------

@pytest.mark.parametrize("name", BUILTIN)
def test_every_builtin_plugin_is_registered(name):
    assert registry.resolve(name).origin == "builtin"


def test_builtin_modules_all_load():
    assert [u for u in registry.unavailable() if u[0] == "builtin"] == []


def test_list_is_ordered_by_origin_then_name(plugin_dir, private_dir):
    plugin_dir(aaa=simple("aaa"))
    private_dir(zzz=simple("zzz"))
    origins = [p.origin for p in registry.all_plugins()]
    assert origins == sorted(origins, key=registry.ORIGINS.index)


# -- discovery of private and local plugins --------------------------------

def test_private_directory_is_discovered(private_dir):
    private_dir(tools=simple("clean_up"))
    found = registry.resolve("clean-up")
    assert (found.origin, found.module) == ("private", "tools")


def test_local_directory_is_discovered(plugin_dir):
    plugin_dir(tools=simple("clean_up"))
    assert registry.resolve("clean-up").origin == "local"


def test_several_local_directories(tmp_path, monkeypatch):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir(), second.mkdir()
    (first / "one.py").write_text(simple("one"))
    (second / "two.py").write_text(simple("two"))
    monkeypatch.setenv("IFDD_CT_PLUGIN_PATH", f"{first}:{second}")
    registry.discover(force=True)
    assert registry.resolve("one") and registry.resolve("two")


def test_missing_directories_are_ignored(monkeypatch):
    monkeypatch.setenv("IFDD_CT_PLUGIN_PATH", "/does/not/exist")
    monkeypatch.setenv("IFDD_CT_PRIVATE_DIR", "/does/not/exist/either")
    registry.discover(force=True)
    assert registry.resolve("head").origin == "builtin"


def test_packages_with_relative_imports(plugin_dir):
    directory = plugin_dir()
    package = directory / "toolkit"
    package.mkdir()
    (package / "helpers.py").write_text("PREFIX = 'x-'\n")
    (package / "__init__.py").write_text(
        "from ifdd.ct import plugin\nfrom .helpers import PREFIX\n\n"
        "@plugin\ndef prefixed(records, ctx):\n    return [PREFIX]\n")
    registry.discover(force=True)
    assert registry.resolve("prefixed").func(None, None) == ["x-"]


def test_files_starting_with_underscore_are_skipped(plugin_dir):
    plugin_dir(_hidden=simple("hidden"))
    with pytest.raises(UsageError):
        registry.resolve("hidden")


def test_rediscovery_sees_changed_files(plugin_dir):
    directory = plugin_dir(mine=simple("first"))
    (directory / "mine.py").write_text(simple("second"))
    registry.discover(force=True)
    assert registry.resolve("second")
    with pytest.raises(UsageError):
        registry.resolve("first")


# -- problems are reported, not fatal --------------------------------------

@pytest.mark.parametrize("code, reason", [
    ("import module_that_does_not_exist\n", "module_that_does_not_exist"),
    ("raise RuntimeError('boom')\n", "boom"),
    ("from ifdd.ct import plugin\n@plugin\ndef lonely(records):\n    return records\n",
     "must accept (records, ctx"),
])
def test_broken_module_is_listed_as_unavailable(plugin_dir, code, reason):
    plugin_dir(broken=code)
    problems = {module: why for _, module, why in registry.unavailable()}
    assert reason in problems["broken"]
    assert registry.resolve("head").origin == "builtin"


def test_same_plugin_twice_in_one_origin(plugin_dir):
    plugin_dir(first=simple("twin"), second=simple("twin"))
    problems = {module: why for _, module, why in registry.unavailable()}
    assert "defined twice" in problems["second"]


def test_local_module_does_not_shadow_the_standard_library(plugin_dir):
    plugin_dir(json=simple("shout"))
    import json

    assert json.dumps({}) == "{}"
    assert registry.resolve("shout").module == "json"


# -- resolving names -------------------------------------------------------

@pytest.mark.parametrize("address", ["stamp", "local.stamp", "example_stamp.stamp",
                                     "local.example_stamp.stamp"])
def test_all_address_forms_find_the_same_plugin(address):
    # plugins/example_stamp.py of the instance is on the plugin path
    assert registry.resolve(address).qualified == "local.stamp"


def test_clash_between_origins_must_be_qualified(plugin_dir):
    plugin_dir(mine=simple("head"))
    with pytest.raises(UsageError, match="ambiguous.*builtin.records.head.*local.mine.head"):
        registry.resolve("head")
    assert registry.resolve("builtin.head").origin == "builtin"
    assert registry.resolve("local.head").origin == "local"


@pytest.mark.parametrize("name", ["len", "os.path.join", "shutil.rmtree", "ifdd.ct.cli.main",
                                  "ifdd.ct.plugins.records.head"])
def test_nothing_outside_the_plugin_origins_can_be_called(name):
    with pytest.raises(UsageError, match="unknown plugin"):
        registry.resolve(name)


def test_typo_gets_a_suggestion():
    with pytest.raises(UsageError, match="did you mean: faker"):
        registry.resolve("fakr")


def test_unknown_name_points_to_failed_modules(plugin_dir):
    plugin_dir(broken="import nope\n")
    with pytest.raises(UsageError, match="failed to load, see --list"):
        registry.resolve("whatever")


# -- metadata from the function --------------------------------------------

def test_name_defaults_to_function_name_with_dashes(plugin_dir):
    plugin_dir(mine=simple("make_it_so"))
    assert registry.resolve("make-it-so").name == "make-it-so"


def test_explicit_name_source_and_sink(plugin_dir):
    plugin_dir(mine="from ifdd.ct import plugin\n"
                    "@plugin(name='gen', source=True)\ndef a(records, ctx):\n    return []\n"
                    "@plugin(name='dump', sink=True)\ndef b(records, ctx):\n    return records\n")
    assert registry.resolve("gen").source and not registry.resolve("gen").sink
    assert registry.resolve("dump").sink


def test_summary_is_first_docstring_line(plugin_dir):
    plugin_dir(mine=simple("documented", doc="First line.\n\n    More text."))
    assert registry.resolve("documented").summary == "First line."


def test_describe_shows_role_doc_and_parameters():
    text = registry.resolve("head").describe()
    assert "builtin.head" in text
    assert "Keep the first COUNT records." in text
    assert "count: int = 4" in text


def test_describe_marks_required_and_extra_parameters():
    assert "key: str (required)" in registry.resolve("where").describe()
    assert "further KEY=VALUE parameters" in registry.resolve("faker").describe()


def test_describe_without_parameters(plugin_dir):
    plugin_dir(mine=simple("bare"))
    assert "(none)" in registry.resolve("bare").describe()


# -- details of registration -------------------------------------------------

@pytest.mark.parametrize("module, expected", [
    ("ifdd.ct.plugins.records", ("builtin", "records")),
    ("ifdd_ct_ext.private.tools", ("private", "tools")),
    ("somewhere.else.mine", ("local", "mine")),
])
def test_origin_of_a_function_registered_outside_discovery(module, expected):
    def step(records, ctx):
        return records

    step.__module__ = module
    assert registry._origin_of(step) == expected


def test_describe_without_docstring(plugin_dir):
    plugin_dir(bare="from ifdd.ct import plugin\n"
                    "@plugin\ndef bare(records, ctx):\n    return records\n")
    assert registry.resolve("bare").describe() == (
        "local.bare  (local module 'bare')\n\nparameters:\n  (none)")


def test_unresolvable_annotations_fall_back_to_text(plugin_dir):
    plugin_dir(odd="from ifdd.ct import plugin\n"
                   "@plugin\ndef odd(records, ctx, size: 'NoSuchType' = '1'):\n    return records\n")
    [param] = registry.resolve("odd").params
    assert param.type is str


def test_star_args_are_not_parameters(plugin_dir):
    plugin_dir(star="from ifdd.ct import plugin\n"
                    "@plugin\ndef star(records, ctx, *rest, n: int = 1):\n    return records\n")
    assert [p.name for p in registry.resolve("star").params] == ["n"]


def test_same_module_name_in_two_local_directories(tmp_path, monkeypatch):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir(), second.mkdir()
    (first / "same.py").write_text(simple("one"))
    (second / "same.py").write_text(simple("two"))
    monkeypatch.setenv("IFDD_CT_PLUGIN_PATH", f"{first}:{second}")
    registry.discover(force=True)
    problems = {module: why for _, module, why in registry.unavailable()}
    assert "module name used twice" in problems["same"]
    assert registry.resolve("one")

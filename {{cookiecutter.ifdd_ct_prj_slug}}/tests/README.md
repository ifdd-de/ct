# tests/

```
tests/
  conftest.py   isolated environment for every test, shared fixtures
  support/      helpers: run_steps(), FakeSession, doc(), fake backend server
  fixtures/     static data (offline JSON-LD contexts)
  core/         registry, parameters, steps, pipeline, config, http, nodes, loader
  plugins/      one file per built-in plugin, grouped like src/ifdd/ct/plugins
  cli/          the command line, in-process and as a real process
  e2e/          real HTTP against a local fake backend (token, PUT, PATCH, GET)
  integration/  against a real, running ifdd-be and Keycloak; writes data,
                skipped unless IFDD_IT_BE_URL is set (see its conftest.py)
  private/      tests of this instance's plugins (cruft skip list)
```

Run: `pytest` (coverage is measured; the build fails below 95 %).

Conventions:

* A test name says what is expected: `test_dry_run_sends_nothing`.
* Tables of cases use `pytest.mark.parametrize`.
* Tests run a step the way the CLI does: `run_steps("head:count=1", records=[...])`.
* HTTP goes to `FakeSession` (`http_ctx` fixture) - except in `e2e/`.
* Plugins written on the fly go through the `plugin_dir` / `private_dir` fixtures.

A new built-in plugin gets a new file in the matching `plugins/` folder.

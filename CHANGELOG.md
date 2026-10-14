# Changelog

## [26.10.2] - 2026-10-14

- `ifdd-ct --markdown`, parameter help texts with `Annotated`, `.env`
  loadable by a shell and the documentation of running ct in a shell (see
  the instance CHANGELOG).
- The pre-generation hook rejects a single quote in `ifdd_be_aspects`
  (`.env` holds the value in single quotes).
- Template CI: sources the rendered `.env` and checks the JSON, checks that
  the hook rejects a single quote, builds the page of `ifdd-ct --markdown`
  with Sphinx (`-W`, without `tests/docs/conf.py`, so broken links fail) and
  runs `--markdown` in the image.
- Documentation of the instance in `docs/en` and `docs/de` (see the instance
  CHANGELOG). Template CI: `tests/check_docs.py` checks that both languages
  match and build without warnings (`tests/docs/conf.py`,
  `tests/docs/requirements.txt`).

## [26.10.1] - 2026-10

First release of the template `ifdd-de/ct`. See the instance CHANGELOG
(`{{cookiecutter.ifdd_ct_prj_slug}}/CHANGELOG.md`) for the content.

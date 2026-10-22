"""Validate the template variables before anything is generated."""

import json
import re
import sys

SLUG = "{{ cookiecutter.ifdd_ct_prj_slug }}"
LOG_LEVEL = "{{ cookiecutter.ifdd_ct_log_level }}"
ASPECTS = r"""{{ cookiecutter.ifdd_be_aspects }}"""

errors = []

# The slug names the directory, the compose project and the image.
if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", SLUG):
    errors.append(
        f"ifdd_ct_prj_slug '{SLUG}' must be lower case letters, digits, '-' or '_' "
        "and start with a letter or digit."
    )

if LOG_LEVEL.upper() not in {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"}:
    errors.append(f"ifdd_ct_log_level '{LOG_LEVEL}' is not a logging level.")

try:
    mapping = json.loads(ASPECTS)
    if not isinstance(mapping, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
    ):
        raise ValueError
except ValueError:
    errors.append("ifdd_be_aspects must be a JSON object mapping path segment to aspect.")

# .env holds the value in single quotes (sourceable by a shell).
if "'" in ASPECTS:
    errors.append("ifdd_be_aspects must not contain a single quote (').")

for url_var, value in {
    "ifdd_be_url": "{{ cookiecutter.ifdd_be_url }}",
    "ifdd_schema_url": "{{ cookiecutter.ifdd_schema_url }}",
    "ifdd_type_url": "{{ cookiecutter.ifdd_type_url }}",
    "ifdd_unit_url": "{{ cookiecutter.ifdd_unit_url }}",
    "ifdd_ts_api_url": "{{ cookiecutter.ifdd_ts_api_url }}",
}.items():
    if not re.match(r"https?://", value):
        errors.append(f"{url_var} '{value}' must start with http:// or https://.")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    sys.exit(1)

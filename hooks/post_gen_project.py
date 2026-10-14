"""Post-generation hook for cookiecutter/cruft templates.

Creates the runtime environment files of a freshly generated project from
their templates and replaces every secret placeholder with a newly generated
random value:

    dotenv.dist  ->  .env
    envs.dist/   ->  envs/      (only if the template has it)

Placeholder syntax, usable anywhere in these files (comments included):

    !!!SECRET!!!
    !!!SECRET length=64 chars=alnum!!!
    !!!SECRET length=32 chars=lower,upper,digit,punct min_each=2!!!
    !!!SECRET ref=db length=48!!!
    !!!SECRET ref=db!!!

Parameters:

    length    number of characters, MIN_LENGTH..MAX_LENGTH (default 64)
    chars     comma separated character classes (default alnum):
              lower, upper, digit, punct, hex; alnum = lower,upper,digit
    min_each  minimum number of characters from each class (default 0)
    ref       share one value between several placeholders. All placeholders
              with the same ref get the same value, in all files. Quality
              parameters may be given on any of them; where given, they must
              be identical, otherwise the hook aborts.

Safety rules:

    * An existing target (.env, envs/) is never touched.
    * Every placeholder is validated before anything is written. Any error
      aborts the hook with a non-zero exit code, which makes cookiecutter
      abort the generation.
    * Generated files are written atomically with mode 0600.
    * Secrets are never printed.

Requires Python 3.13 or later and the standard library only.
cookiecutter renders hook scripts with Jinja, so this file must not contain
Jinja delimiters.
"""

from __future__ import annotations

import contextlib
import os
import re
import secrets
import string
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

# (template file, target file), relative to the generated project
ENV_FILES = [("dotenv.dist", ".env")]

# (template directory, target directory); every file below is processed
ENV_DIRS = [("envs.dist", "envs")]

# lines that must be present in .gitignore
GITIGNORE_ENTRIES = [".env", "envs/*"]

MIN_LENGTH = 8
MAX_LENGTH = 4096
DEFAULT_LENGTH = 64
DEFAULT_CHARS = "alnum"
SECRET_FILE_MODE = 0o600

# Punctuation that is harmless unquoted in .env files, in docker compose
# interpolation and when the file is sourced by a POSIX shell.
# Deliberately excluded: quotes, backslash, $, `, #, !, ~, whitespace and the
# shell metacharacters ( ) [ ] { } < > | & ; * ?
# Not URL-safe (% / : @), so use alnum for values embedded in URLs.
SAFE_PUNCTUATION = "%+,-./:=@^_"

CHAR_CLASSES = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digit": string.digits,
    "punct": SAFE_PUNCTUATION,
    "hex": "0123456789abcdef",
}
CHAR_ALIASES = {"alnum": ("lower", "upper", "digit")}

QUALITY_KEYS = {"length", "chars", "min_each"}
ALLOWED_KEYS = QUALITY_KEYS | {"ref"}

PLACEHOLDER_RE = re.compile(r"!!!SECRET(?P<args>(?:[ \t][^!\n]*)?)!!!")
REF_RE = re.compile(r"[A-Za-z0-9_.-]+")

# Markers that must not survive: a malformed new placeholder or an old one.
LEFTOVER_MARKERS = ("!!!SECRET", "!!!SET ")

if sys.version_info < (3, 13):
    sys.stderr.write("post_gen_project.py requires Python 3.13 or later.\n")
    sys.exit(1)


class HookError(Exception):
    """A problem that aborts the project generation."""


# --------------------------------------------------------------------------
# Placeholder parsing
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SecretSpec:
    length: int
    classes: tuple[str, ...]
    min_each: int

    def describe(self) -> str:
        return (
            f"length={self.length} chars={','.join(self.classes)} "
            f"min_each={self.min_each}"
        )


@dataclass(frozen=True)
class Placeholder:
    location: str
    spec: SecretSpec
    explicit: bool
    ref: str | None
    start: int
    end: int


def parse_int(key: str, value: str, location: str) -> int:
    if not value.isdecimal() or not value.isascii():
        raise HookError(f"{location}: {key}={value!r} is not a whole number")
    return int(value)


def parse_classes(value: str, location: str) -> tuple[str, ...]:
    classes: set[str] = set()
    for name in value.split(","):
        name = name.strip()
        if name in CHAR_ALIASES:
            classes.update(CHAR_ALIASES[name])
        elif name in CHAR_CLASSES:
            classes.add(name)
        else:
            known = ", ".join(sorted([*CHAR_CLASSES, *CHAR_ALIASES]))
            raise HookError(
                f"{location}: unknown character class {name!r} (known: {known})"
            )
    return tuple(sorted(classes))


def parse_placeholder(args: str, location: str) -> tuple[SecretSpec, bool, str | None]:
    """Return (spec, explicit, ref) for the argument part of a placeholder."""
    params: dict[str, str] = {}
    for token in args.split():
        key, sep, value = token.partition("=")
        if not sep or not key or not value:
            raise HookError(f"{location}: expected key=value, got {token!r}")
        if key not in ALLOWED_KEYS:
            allowed = ", ".join(sorted(ALLOWED_KEYS))
            raise HookError(f"{location}: unknown parameter {key!r} (allowed: {allowed})")
        if key in params:
            raise HookError(f"{location}: parameter {key!r} given twice")
        params[key] = value

    length = parse_int("length", params.get("length", str(DEFAULT_LENGTH)), location)
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise HookError(
            f"{location}: length={length} is outside {MIN_LENGTH}..{MAX_LENGTH}"
        )

    classes = parse_classes(params.get("chars", DEFAULT_CHARS), location)

    min_each = parse_int("min_each", params.get("min_each", "0"), location)
    if min_each * len(classes) > length:
        raise HookError(
            f"{location}: min_each={min_each} for {len(classes)} classes "
            f"needs more than length={length} characters"
        )

    ref = params.get("ref")
    if ref is not None and not REF_RE.fullmatch(ref):
        raise HookError(f"{location}: invalid ref {ref!r} (allowed: A-Z a-z 0-9 _ . -)")

    explicit = bool(QUALITY_KEYS & params.keys())
    return SecretSpec(length, classes, min_each), explicit, ref


def find_placeholders(text: str, source: str) -> list[Placeholder]:
    found = []
    for match in PLACEHOLDER_RE.finditer(text):
        location = f"{source}:{line_of(text, match.start())}"
        spec, explicit, ref = parse_placeholder(match.group("args"), location)
        found.append(Placeholder(location, spec, explicit, ref, match.start(), match.end()))
    return found


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


# --------------------------------------------------------------------------
# Secret generation
# --------------------------------------------------------------------------


def generate_secret(spec: SecretSpec) -> str:
    """Random string of spec.length characters drawn from spec.classes.

    The min_each characters per class are drawn first, the rest from the
    union of all classes, and the result is shuffled.
    """
    alphabet = "".join(sorted(set("".join(CHAR_CLASSES[c] for c in spec.classes))))
    chars = [
        secrets.choice(CHAR_CLASSES[c]) for c in spec.classes for _ in range(spec.min_each)
    ]
    chars += [secrets.choice(alphabet) for _ in range(spec.length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def resolve_values(placeholders: list[Placeholder]) -> dict[Placeholder, str]:
    """Generate one value per placeholder; placeholders sharing a ref share it."""
    ref_specs: dict[str, tuple[SecretSpec, str]] = {}
    for ph in placeholders:
        if ph.ref is None or not ph.explicit:
            continue
        known = ref_specs.get(ph.ref)
        if known is None:
            ref_specs[ph.ref] = (ph.spec, ph.location)
        elif known[0] != ph.spec:
            raise HookError(
                f"ref={ph.ref!r} has conflicting quality parameters:\n"
                f"  {known[1]}: {known[0].describe()}\n"
                f"  {ph.location}: {ph.spec.describe()}"
            )

    ref_values: dict[str, str] = {}
    values: dict[Placeholder, str] = {}
    for ph in placeholders:
        if ph.ref is None:
            values[ph] = generate_secret(ph.spec)
            continue
        if ph.ref not in ref_values:
            spec = ref_specs.get(ph.ref, (ph.spec, ""))[0]
            ref_values[ph.ref] = generate_secret(spec)
        values[ph] = ref_values[ph.ref]
    return values


# --------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------


@dataclass
class Job:
    source: Path
    target: Path
    label: str
    text: str
    placeholders: list[Placeholder]


def read_text(path: Path, label: str) -> str:
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except UnicodeDecodeError as exc:
        raise HookError(f"{label}: not valid UTF-8 ({exc.reason})") from None


def plan_jobs(project_dir: Path) -> tuple[list[Job], list[Path]]:
    """Collect the files to create and the directories they need."""
    jobs: list[Job] = []
    dirs: list[Path] = []

    for source_name, target_name in ENV_FILES:
        source, target = project_dir / source_name, project_dir / target_name
        if not source.is_file():
            continue
        if target.exists():
            info(f"{target_name} exists, left unchanged")
            continue
        jobs.append(make_job(source, target, source_name))

    for source_name, target_name in ENV_DIRS:
        source, target = project_dir / source_name, project_dir / target_name
        if not source.is_dir():
            continue
        if target.exists():
            info(f"{target_name}/ exists, left unchanged")
            continue
        dirs.append(target)
        for path in sorted(source.rglob("*")):
            rel = path.relative_to(source)
            if path.is_dir():
                dirs.append(target / rel)
            elif path.is_file():
                jobs.append(make_job(path, target / rel, f"{source_name}/{rel.as_posix()}"))

    return jobs, dirs


def make_job(source: Path, target: Path, label: str) -> Job:
    text = read_text(source, label)
    return Job(source, target, label, text, find_placeholders(text, label))


def render(job: Job, values: dict[Placeholder, str]) -> str:
    parts, pos = [], 0
    for ph in job.placeholders:
        parts += [job.text[pos : ph.start], values[ph]]
        pos = ph.end
    parts.append(job.text[pos:])
    rendered = "".join(parts)

    for marker in LEFTOVER_MARKERS:
        index = rendered.find(marker)
        if index >= 0:
            # Generated values contain no "!", so the position maps back to
            # a line of the template that holds a malformed placeholder.
            line = line_of(rendered, index)
            raise HookError(f"{job.label}:{line}: malformed or outdated placeholder")
    return rendered


def write_private(path: Path, text: str) -> None:
    """Write text atomically to path with SECRET_FILE_MODE."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, SECRET_FILE_MODE)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def ensure_gitignore(project_dir: Path, entries: list[str]) -> None:
    path = project_dir / ".gitignore"
    existing = read_text(path, ".gitignore") if path.exists() else ""
    present = {line.strip() for line in existing.splitlines()}
    missing = [entry for entry in entries if entry not in present]
    if not missing:
        return
    separator = "" if not existing or existing.endswith("\n") else "\n"
    with open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(separator + "\n".join(missing) + "\n")


# --------------------------------------------------------------------------
# Console output
# --------------------------------------------------------------------------


def use_color(stream) -> bool:
    return "NO_COLOR" not in os.environ and hasattr(stream, "isatty") and stream.isatty()


def emit(stream, color: str, label: str, message: str) -> None:
    if use_color(stream):
        stream.write(f"\x1b[{color}m[{label}]\x1b[0m {message}\n")
    else:
        stream.write(f"[{label}] {message}\n")


def info(message: str) -> None:
    emit(sys.stdout, "1;33", "INFO", message)


def success(message: str) -> None:
    emit(sys.stdout, "1;32", "SUCCESS", message)


def error(message: str) -> None:
    emit(sys.stderr, "1;31", "ERROR", message)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def run(project_dir: Path) -> None:
    jobs, dirs = plan_jobs(project_dir)

    # validate and render everything before the first write
    placeholders = [ph for job in jobs for ph in job.placeholders]
    values = resolve_values(placeholders)
    rendered = [(job, render(job, values)) for job in jobs]

    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
    for job, text in rendered:
        write_private(job.target, text)
        target = job.target.relative_to(project_dir).as_posix()
        info(f"created {target} ({len(job.placeholders)} secrets)")

    ensure_gitignore(project_dir, GITIGNORE_ENTRIES)


def main(project_dir: Path | None = None) -> int:
    try:
        run(project_dir or Path.cwd())
    except HookError as exc:
        error(str(exc))
        error("project generation aborted")
        return 1
    success("project initialized")
    return 0


if __name__ == "__main__":
    sys.exit(main())

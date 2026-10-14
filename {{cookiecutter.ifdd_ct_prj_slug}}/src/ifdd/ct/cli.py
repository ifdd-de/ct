"""Command line: ifdd-ct [options] STEP [STEP ...]"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from . import __version__, config, markdown
from .errors import CtError, UsageError
from .pipeline import load_pipeline, parse_step, run
from .registry import all_plugins, resolve, unavailable

log = logging.getLogger("ifdd.ct")

EPILOG = """\
steps:
  name                   run a plugin
  name:key=value,k=v     run a plugin with parameters (',' in a value: %2C)
  FILE                   first step: read JSON/YAML, last step: write it
  DIRECTORY              first step: read every .json/.jsonld/.yaml below it

examples:
  ifdd-ct --list
  ifdd-ct --markdown > plugins.md
  ifdd-ct faker:profile=energy-grid,product=5,seed=42
  ifdd-ct examples/json-ld put
  ifdd-ct -f pipelines/load-examples.yaml
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ifdd-ct",
        description="Core Tools: chain plugins over JSON-LD records.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("steps", nargs="*", metavar="STEP", help="plugin, file or directory")
    parser.add_argument("-f", "--file", metavar="PIPELINE", help="run the steps of a YAML pipeline file")
    parser.add_argument("-l", "--list", action="store_true", help="list available plugins and exit")
    parser.add_argument("-d", "--describe", metavar="PLUGIN", help="show a plugin's parameters and exit")
    parser.add_argument("--markdown", action="store_true",
                        help="print this help and every plugin as Markdown (MyST) and exit")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="more log output on stderr (-vv: debug)")
    parser.add_argument("-q", "--quiet", action="store_true", help="errors only")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def setup_logging(verbose: int, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = getattr(logging, config.log_level(), logging.WARNING)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger("ifdd.ct")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False


def print_list() -> None:
    plugins = all_plugins()
    width = max((len(p.qualified) for p in plugins), default=10)
    for p in plugins:
        role = "source" if p.source else "sink" if p.sink else ""
        print(f"{p.qualified:<{width}}  {role:<6}  {p.summary}")
    problems = unavailable()
    if problems:
        print("\nnot available:")
        for origin, module, reason in problems:
            print(f"  {origin}/{module}: {reason}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose, args.quiet)
    try:
        if args.list:
            print_list()
            return 0
        if args.describe:
            print(resolve(args.describe).describe())
            return 0
        if args.markdown:
            sys.stdout.write(markdown.render(build_parser()))
            return 0
        if args.file and args.steps:
            raise UsageError("give either -f PIPELINE or steps, not both")
        steps = load_pipeline(args.file) if args.file else [parse_step(s) for s in args.steps]
        if not steps:
            build_parser().print_usage(sys.stderr)
            raise UsageError("no steps given - try --list or --help")
        run(steps)
        return 0
    except CtError as err:
        log.error("%s", err, exc_info=log.isEnabledFor(logging.DEBUG))
        return err.exit_code
    except KeyboardInterrupt:
        log.error("interrupted")
        return 130
    except Exception as err:  # noqa: BLE001 - last line of defence, keep it short
        log.error("%s: %s", type(err).__name__, err, exc_info=log.isEnabledFor(logging.DEBUG))
        if not log.isEnabledFor(logging.DEBUG):
            log.error("run with -vv for the traceback")
        return 1

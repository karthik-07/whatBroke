"""Command-line entry point."""

from whatbroke.collectors.errors import collect_errors, boot_selector
from whatbroke.reporting.errors import render_errors

from whatbroke.analysis.correlate import correlate
from whatbroke.reporting.correlate import render_correlation
from whatbroke.analysis.compare import collect_comparison
from whatbroke.reporting.compare import render_comparison

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from whatbroke.collectors.pacman import collect_pacman
from whatbroke.collectors.journal import collect_boots
from whatbroke.reporting.boots import render_boots
from whatbroke.distros.arch.pacman import resolve_log_path
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.packages import render_packages


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="whatbroke",
        description="Inspect Linux package and boot history (early development).",
        epilog="Temporal package candidates are investigation leads, not proven causes.",
    )
    try:
        package_version = version("whatbroke")
    except PackageNotFoundError:
        package_version = "development (uninstalled source)"
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version}")
    commands = parser.add_subparsers(dest="command")
    packages = commands.add_parser("packages", help="inspect Pacman package history and log availability")
    packages.add_argument("--log-file", type=Path, help="read a supplied plain-text Pacman log")
    packages.add_argument("--limit", type=positive_integer, default=20,
                          help="number of final events to display (default: 20)")
    boots = commands.add_parser("boots", help="inspect available system journal boot history")
    boots.add_argument("--limit", type=positive_integer, default=20,
                       help="number of final boots to display (default: 20)")
    errors = commands.add_parser("errors", help="inspect error-or-higher records for one boot")
    errors.add_argument("--boot", type=boot_selector, default="current",
                        help="current (default), journal index, or 32-character boot ID")
    errors.add_argument("--limit", type=positive_integer, default=20,
                        help="number of final errors displayed (default: 20)")
    compare = commands.add_parser("compare", help="compare error signatures across boots")
    compare.add_argument("--boot", type=boot_selector, default="current",
                         help="target boot: current (default), index, or boot ID")
    compare.add_argument("--previous", type=positive_integer, default=5,
                         help="number of earlier visible boots to compare (default: 5)")
    compare.add_argument("--log-file", type=Path, help="Pacman log for package-change correlation")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "compare":
        result = collect_comparison(args.boot, args.previous)
        print(render_comparison(result))
        status = result.status
        if any(f.classification == 'newly observed' for f in result.findings):
            location = resolve_log_path() if args.log_file is None else None
            packages = collect_pacman(args.log_file if args.log_file is not None else location.path)
            if location and location.warning:
                packages.warnings.append(location.warning)
            correlation = correlate(result, packages)
            print(render_correlation(correlation))
            if correlation.status != SourceStatus.AVAILABLE:
                status = SourceStatus.PARTIAL
        return 0 if status == SourceStatus.AVAILABLE else 1
    if args.command == "errors":
        result = collect_errors(args.boot)
        print(render_errors(result, args.limit))
        return 0 if result.status == SourceStatus.AVAILABLE else 1
    if args.command == "boots":
        result = collect_boots()
        print(render_boots(result, args.limit))
        return 0 if result.status == SourceStatus.AVAILABLE else 1
    warning = None
    path = args.log_file
    if path is None:
        location = resolve_log_path()
        path, warning = location.path, location.warning
    result = collect_pacman(path)
    if warning:
        result.warnings.append(warning)
    print(render_packages(result, args.limit))
    return 0 if result.status == SourceStatus.AVAILABLE else 1

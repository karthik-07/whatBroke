"""Command-line entry point."""

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
        epilog="Boot comparison and failure diagnosis are not implemented yet.",
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
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
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

"""Command-line entry point."""

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from whatbroke.collectors.pacman import collect_pacman
from whatbroke.distros.arch.pacman import resolve_log_path
from whatbroke.models.packages import SourceStatus
from whatbroke.reporting.packages import render_packages


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="whatbroke",
        description="Inspect Linux package history (early development).",
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
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
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

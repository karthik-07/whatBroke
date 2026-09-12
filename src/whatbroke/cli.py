"""Informational command-line entry point for the development scaffold."""

import argparse
from importlib.metadata import PackageNotFoundError, version


def main() -> int:
    """Display scaffold information without accessing system logs."""
    parser = argparse.ArgumentParser(
        prog="whatbroke",
        description="Investigate what changed before Linux failures (in development).",
        epilog="Log collection and diagnosis are not implemented yet.",
    )
    try:
        package_version = version("whatbroke")
    except PackageNotFoundError:
        package_version = "development (uninstalled source)"
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version}")
    parser.parse_args()
    print("What Broke? is in early development. Log collection and diagnosis are not implemented yet.")
    return 0

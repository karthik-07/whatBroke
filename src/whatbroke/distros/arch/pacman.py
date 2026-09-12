"""Resolve Pacman's log location using its own configuration reader."""

from dataclasses import dataclass
from pathlib import Path
import subprocess

DEFAULT_LOG = Path("/var/log/pacman.log")


@dataclass(frozen=True)
class LogLocation:
    path: Path
    warning: str | None = None


def resolve_log_path() -> LogLocation:
    """Respect Includes and defaults via pacman-conf; disclose fallback use."""
    try:
        result = subprocess.run(
            ["pacman-conf", "LogFile"], capture_output=True, text=True,
            check=True, timeout=5,
        )
        value = result.stdout.strip()
        if not value or "\n" in value or not Path(value).is_absolute():
            raise ValueError("unexpected LogFile output")
        return LogLocation(Path(value))
    except (OSError, subprocess.SubprocessError, ValueError):
        return LogLocation(
            DEFAULT_LOG,
            "Could not resolve configuration using pacman-conf; trying the default "
            "path. Use --log-file if Pacman logs elsewhere.",
        )

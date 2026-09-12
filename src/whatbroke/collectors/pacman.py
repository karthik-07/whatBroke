"""Read Pacman package history without modifying logs or requesting privileges."""

from datetime import datetime
from pathlib import Path
import re

from whatbroke.models.packages import PackageCollection, PackageEvent, SourceStatus

RECORD = re.compile(r"^\[(?P<time>[^]]+)\] (?:\[(?P<source>[^]]+)\] )?(?P<message>.*)$")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:?\d{2}|Z)| \d{2}:\d{2})")
ACTION = re.compile(r"^(installed|upgraded|downgraded|reinstalled|removed)(?:\s|$)")
CHANGE = re.compile(
    r"^(?P<action>installed|upgraded|downgraded|reinstalled|removed) "
    r"(?P<package>[a-zA-Z0-9@_+][a-zA-Z0-9@._+\-]*) "
    r"\((?P<versions>[^()]+)\)$"
)


def _malformed(result: PackageCollection, line_number: int) -> None:
    result.malformed_lines += 1
    if len(result.malformed_examples) < 5:
        result.malformed_examples.append(line_number)


def _parse_line(result: PackageCollection, raw: str, line_number: int) -> None:
    if not raw.strip():
        result.ignored_lines += 1
        return
    record = RECORD.fullmatch(raw)
    if record is None or "\ufffd" in raw:
        _malformed(result, line_number)
        return
    try:
        timestamp_text = record["time"]
        if TIMESTAMP.fullmatch(timestamp_text) is None:
            raise ValueError("unsupported timestamp")
        timestamp = datetime.fromisoformat(timestamp_text)
    except ValueError:
        _malformed(result, line_number)
        return
    # Old Pacman logs omit timezone information. Never guess the historical zone.
    history = result.history if timestamp.tzinfo else result.local_history
    history.include(timestamp)
    message = record["message"]
    if record["source"] not in (None, "ALPM") or not ACTION.match(message):
        result.ignored_lines += 1
        return
    change = CHANGE.fullmatch(message)
    if change is None:
        _malformed(result, line_number)
        return
    action, package, versions = change.group("action", "package", "versions")
    old_version = new_version = None
    parts = versions.split(" -> ")
    if action in ("upgraded", "downgraded"):
        if len(parts) != 2 or any(not p or any(c.isspace() for c in p) for p in parts):
            _malformed(result, line_number)
            return
        old_version, new_version = parts
    else:
        if len(parts) != 1 or any(c.isspace() for c in versions):
            _malformed(result, line_number)
            return
        if action in ("removed", "reinstalled"):
            old_version = versions
        if action in ("installed", "reinstalled"):
            new_version = versions
    result.events.append(PackageEvent(
        timestamp, action, package, old_version, new_version,
        result.path, line_number, raw,
    ))


def collect_pacman(path: str | Path) -> PackageCollection:
    """Collect one plain-text log; history bounds do not imply continuous coverage."""
    result = PackageCollection(path=Path(path))
    try:
        with result.path.open(encoding="utf-8", errors="replace") as stream:
            for line_number, line in enumerate(stream, 1):
                result.total_lines += 1
                _parse_line(result, line.rstrip("\r\n"), line_number)
    except PermissionError:
        result.status = SourceStatus.PERMISSION_DENIED
        result.error = "Permission denied while reading the package log."
    except FileNotFoundError:
        result.status = SourceStatus.NOT_FOUND
        result.error = "Package log not found. Check its configured location."
    except OSError as error:
        result.status = SourceStatus.ERROR
        result.error = f"Could not read the package log: {error.strerror or type(error).__name__}."
    if result.status == SourceStatus.AVAILABLE and result.malformed_lines:
        result.status = SourceStatus.PARTIAL
    if result.local_history.earliest:
        result.warnings.append(
            "Legacy records have no timezone; their local history is reported separately."
        )
    return result

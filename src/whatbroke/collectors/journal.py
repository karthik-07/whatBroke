"""Read available system boot history through journalctl."""

from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess

from whatbroke.models.boots import Boot, BootCollection
from whatbroke.models.sources import SourceStatus

COMMAND = ["journalctl", "--system", "--list-boots", "--no-pager", "--utc", "--output=json"]
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _timestamp(value: object) -> datetime:
    if type(value) is not int or value < 0:
        raise ValueError("expected nonnegative microseconds since epoch")
    return EPOCH + timedelta(microseconds=value)


def parse_boots(output: str) -> BootCollection:
    """Parse journalctl's JSON table; preserve valid rows if other rows fail."""
    result = BootCollection()
    if not output.strip():
        return result
    try:
        rows = json.loads(output)
        if not isinstance(rows, list):
            raise ValueError("expected a JSON array")
    except (ValueError, TypeError):
        result.status = SourceStatus.ERROR
        result.error = "Could not parse journalctl boot-list JSON. This journalctl version may not support it."
        return result
    seen_ids = set()
    seen_indices = set()
    for row in rows:
        try:
            if not isinstance(row, dict):
                raise ValueError("expected object")
            index, boot_id = row["index"], row["boot_id"]
            if type(index) is not int or not isinstance(boot_id, str):
                raise ValueError("invalid boot index or ID")
            if not re.fullmatch(r"[0-9a-fA-F]{32}", boot_id):
                raise ValueError("invalid boot ID")
            boot_id = boot_id.lower()
            first, last = _timestamp(row["first_entry"]), _timestamp(row["last_entry"])
            if last < first or boot_id in seen_ids or index in seen_indices:
                raise ValueError("inconsistent boot record")
        except (KeyError, ValueError, TypeError, OverflowError):
            result.malformed_records += 1
            continue
        result.boots.append(Boot(index, boot_id, first, last))
        seen_ids.add(boot_id)
        seen_indices.add(index)
    result.boots.sort(key=lambda boot: boot.index)
    if result.malformed_records:
        result.status = SourceStatus.PARTIAL
    return result


def collect_boots() -> BootCollection:
    """Query once without sudo; keep privilege hints even on successful commands."""
    environment = dict(os.environ, LC_ALL="C", LANG="C", SYSTEMD_COLORS="0", SYSTEMD_URLIFY="0")
    try:
        completed = subprocess.run(COMMAND, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=30,
                                   env=environment, check=False)
    except FileNotFoundError:
        return BootCollection(status=SourceStatus.UNSUPPORTED,
                              error="journalctl was not found. Systemd journal collection is unavailable.")
    except PermissionError:
        return BootCollection(status=SourceStatus.ERROR,
                              error="Could not execute journalctl: permission denied. Check executable permissions.")
    except subprocess.TimeoutExpired:
        return BootCollection(status=SourceStatus.ERROR, error="journalctl timed out after 30 seconds.")
    except OSError as error:
        return BootCollection(status=SourceStatus.ERROR,
                              error=f"Could not execute journalctl: {error.strerror or type(error).__name__}.")
    result = parse_boots(completed.stdout)
    result.diagnostics = [line for line in completed.stderr.splitlines() if line.strip()]
    diagnostic = completed.stderr.lower()
    result.access_limited = any(hint in diagnostic for hint in (
        "permission denied", "insufficient permissions", "operation not permitted",
        "not seeing messages from other users", "not seeing messages from other users and the system",
    ))
    if result.access_limited:
        result.status = SourceStatus.PARTIAL if result.boots else SourceStatus.PERMISSION_DENIED
    elif completed.returncode:
        result.status = SourceStatus.ERROR
        result.error = result.error or f"journalctl exited with status {completed.returncode}."
    elif result.status == SourceStatus.AVAILABLE:
        if "no journal files were found" in diagnostic and not result.boots:
            result.status = SourceStatus.NOT_FOUND
            result.error = "No system journal files were found. Earlier history may not have been retained."
        elif result.diagnostics:
            result.status = SourceStatus.PARTIAL
        elif not result.boots:
            result.status = SourceStatus.NOT_FOUND
            result.error = "No boot records are available in the readable system journal."
    return result

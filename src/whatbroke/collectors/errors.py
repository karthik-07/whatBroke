"""Collect error-or-higher system journal records for a resolved boot."""
import json
import os
from pathlib import Path
import re
import subprocess

from whatbroke.collectors.journal import collect_boots, _timestamp
from whatbroke.models.boots import BootCollection
from whatbroke.models.errors import ErrorCollection, ErrorEvent
from whatbroke.models.sources import SourceStatus


def boot_selector(value: str) -> str:
    if value == 'current' or re.fullmatch(r'-?\d+|[0-9a-fA-F]{32}', value):
        return value.lower()
    raise ValueError('use current, a journal boot index, or a 32-character boot ID')


def _text(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError('ambiguous or non-text field')
    return value


def parse_errors(output: str, result: ErrorCollection) -> None:
    """Retain valid JSON lines and disclose invalid or unexpected records."""
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('expected object')
            stamp = row['__REALTIME_TIMESTAMP']
            if not isinstance(stamp, str) or not stamp.isascii() or not stamp.isdecimal():
                raise ValueError('invalid timestamp')
            timestamp = _timestamp(int(stamp))
            priority = row['PRIORITY']
            if priority not in ('0', '1', '2', '3'):
                raise ValueError('unexpected priority')
            if result.boot is None or row['_BOOT_ID'] != result.boot.boot_id:
                raise ValueError('unexpected boot')
            message = _text(row, 'MESSAGE')
            if message is None:
                raise ValueError('missing message')
            event = ErrorEvent(timestamp, row['_BOOT_ID'], int(priority), message,
                               _text(row, '_SYSTEMD_UNIT'), _text(row, 'SYSLOG_IDENTIFIER'),
                               _text(row, '_TRANSPORT'), _text(row, '__CURSOR'), row)
        except (KeyError, ValueError, TypeError, OverflowError):
            result.malformed_records += 1
            continue
        result.events.append(event)
    if result.malformed_records and result.status == SourceStatus.AVAILABLE:
        result.status = SourceStatus.PARTIAL


def collect_errors(selector: str = 'current', *, history: BootCollection | None = None) -> ErrorCollection:
    selector = boot_selector(selector)
    result = ErrorCollection(selector)
    if history is None:
        history = collect_boots()
    result.status, result.access_limited = history.status, history.access_limited
    result.diagnostics = list(history.diagnostics)
    result.error = history.error
    if history.malformed_records:
        result.diagnostics.append(f'Boot discovery skipped {history.malformed_records} invalid records.')
    target_id = None
    if selector == 'current':
        try:
            target_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip().replace('-', '').lower()
            if not re.fullmatch(r'[0-9a-f]{32}', target_id):
                raise ValueError('invalid current boot ID')
        except (OSError, ValueError):
            result.status = SourceStatus.ERROR
            result.error = 'Could not determine the current boot ID; select an explicit --boot index or ID.'
            return result
    elif re.fullmatch(r'[0-9a-f]{32}', selector):
        target_id = selector
    if target_id is not None:
        result.boot = next((b for b in history.boots if b.boot_id == target_id), None)
    else:
        index = int(selector)
        # Positive journal offsets count from the beginning, starting at 1.
        result.boot = (history.boots[index - 1] if 0 < index <= len(history.boots) else
                       next((b for b in history.boots if b.index == index), None) if index <= 0 else None)
    if result.boot is None:
        if result.status == SourceStatus.AVAILABLE:
            result.status = SourceStatus.NOT_FOUND
        result.error = result.error or 'Selected boot is not present in the visible journal history.'
        return result
    command = ['journalctl', '--system', f'--boot={result.boot.boot_id}', '--priority=0..3',
               '--output=json', '--all', '--no-pager']
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                                   errors='replace', timeout=30, check=False,
                                   env=dict(os.environ, LC_ALL='C', LANG='C', SYSTEMD_COLORS='0', SYSTEMD_URLIFY='0'))
    except FileNotFoundError:
        result.status, result.error = SourceStatus.UNSUPPORTED, 'journalctl was not found.'
        return result
    except (OSError, subprocess.TimeoutExpired) as error:
        result.status = SourceStatus.ERROR
        result.error = ('journalctl timed out after 30 seconds.' if isinstance(error, subprocess.TimeoutExpired)
                        else 'Could not execute journalctl; check executable availability and permissions.')
        return result
    parse_errors(completed.stdout, result)
    result.diagnostics.extend(line for line in completed.stderr.splitlines() if line.strip())
    diagnostic = completed.stderr.lower()
    restricted = any(hint in diagnostic for hint in ('permission denied', 'insufficient permissions',
                         'operation not permitted', 'not seeing messages from other users'))
    result.access_limited |= restricted
    if restricted:
        result.status = SourceStatus.PARTIAL if result.events else SourceStatus.PERMISSION_DENIED
    elif completed.returncode:
        result.status = SourceStatus.ERROR
        result.error = f'journalctl exited with status {completed.returncode}.'
    elif 'no journal files were found' in diagnostic:
        result.status = SourceStatus.NOT_FOUND
        result.error = 'Journal files are no longer available for this query.'
    elif completed.stderr.strip() and result.status == SourceStatus.AVAILABLE:
        result.status = SourceStatus.PARTIAL
    return result

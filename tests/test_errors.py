"""Portable per-boot journal error tests."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from whatbroke.cli import main
from whatbroke.collectors.errors import collect_errors, parse_errors, boot_selector
from whatbroke.collectors.journal import parse_boots
from whatbroke.models.errors import ErrorCollection
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.errors import render_errors

FIXTURES = Path(__file__).parent / 'fixtures/journal'
ERRORS = (FIXTURES / 'errors.jsonl').read_text()


class ErrorTests(unittest.TestCase):
    def history(self):
        return parse_boots((FIXTURES / 'boots.json').read_text())

    def collect(self, output=ERRORS, stderr='', code=0, selector='-1', history=None):
        with patch('whatbroke.collectors.errors.collect_boots', return_value=history or self.history()), patch(
                'whatbroke.collectors.errors.subprocess.run', return_value=
                subprocess.CompletedProcess([], code, output, stderr)) as run:
            result = collect_errors(selector)
            return result, run

    def test_fields_and_precise_timestamps(self):
        result, run = self.collect()
        self.assertEqual(result.status, SourceStatus.AVAILABLE)
        self.assertEqual(len(result.events), 2)
        first, second = result.events
        self.assertEqual(first.timestamp.isoformat(), '2026-01-01T00:00:00.000001+00:00')
        self.assertEqual(first.unit, 'example.service')
        self.assertEqual(first.cursor, 'synthetic-1')
        self.assertEqual(second.transport, 'kernel')
        self.assertEqual(second.message, 'example_wifi: driver timeout')
        self.assertEqual(second.raw['SYSLOG_IDENTIFIER'], 'kernel')
        command = run.call_args.args[0]
        self.assertIn('--boot=' + '1' * 32, command)
        self.assertIn('--priority=0..3', command)
        self.assertIn('--all', command)
        self.assertNotIn('--quiet', command)

    def test_current_uses_actual_id_not_latest_boot(self):
        with patch.object(Path, 'read_text', return_value='11111111-1111-1111-1111-111111111111'):
            history = parse_boots('[{"index": -1, "boot_id": "11111111111111111111111111111111", "first_entry": 1, "last_entry": 2}]')
            result, _ = self.collect(selector='current', history=history)
        self.assertEqual(result.boot.index, -1)

    def test_current_id_read_failure_does_not_guess(self):
        history = self.history()
        with patch('whatbroke.collectors.errors.collect_boots', return_value=history), patch.object(
                Path, 'read_text', side_effect=PermissionError), patch('whatbroke.collectors.errors.subprocess.run') as run:
            result = collect_errors()
        self.assertEqual(result.status, SourceStatus.ERROR)
        run.assert_not_called()

    def test_explicit_id_and_positive_offset(self):
        for selector in ('1' * 32, '1'):
            result, _ = self.collect(selector=selector)
            self.assertEqual(result.boot.boot_id, '1' * 32)

    def test_missing_boot_does_not_query_errors(self):
        result, run = self.collect(selector='-9')
        self.assertEqual(result.status, SourceStatus.NOT_FOUND)
        self.assertNotIn('No matching errors observed', render_errors(result))
        self.assertNotIn('sudo', render_errors(result))
        run.assert_not_called()

    def test_empty_available_boot_is_not_missing_history(self):
        result, _ = self.collect(output='')
        self.assertEqual(result.status, SourceStatus.AVAILABLE)
        self.assertIn('No matching errors observed', render_errors(result))

    def test_discovery_restrictions_survive_empty_result(self):
        history = self.history()
        history.status = SourceStatus.PARTIAL
        history.access_limited = True
        result, _ = self.collect(output='', history=history)
        self.assertEqual(result.status, SourceStatus.PARTIAL)
        self.assertIn('sudo', render_errors(result))
        self.assertNotIn('No matching errors observed', render_errors(result))

    def test_unavailable_discovery_preserves_status(self):
        history = self.history()
        history.boots = []
        history.status = SourceStatus.UNSUPPORTED
        history.error = 'journalctl unavailable'
        result, run = self.collect(history=history)
        self.assertEqual(result.status, SourceStatus.UNSUPPORTED)
        run.assert_not_called()

    def test_malformed_wrong_boot_and_unsupported_fields(self):
        row = json.loads(ERRORS.splitlines()[0])
        bad = ['garbage', '{}', 'null']
        for key, value in (('PRIORITY', '4'), ('_BOOT_ID', '2' * 32),
                           ('MESSAGE', None), ('MESSAGE', ['a', 'b']),
                           ('__REALTIME_TIMESTAMP', '-1'), ('__REALTIME_TIMESTAMP', '9' * 100),
                           ('_SYSTEMD_UNIT', ['a.service', 'b.service'])):
            bad.append(json.dumps(dict(row, **{key: value})))
        result, _ = self.collect(output='\n'.join(bad) + '\n' + ERRORS)
        self.assertEqual(result.status, SourceStatus.PARTIAL)
        self.assertEqual(result.malformed_records, 10)
        self.assertEqual(len(result.events), 2)

    def test_all_included_priorities(self):
        row = json.loads(ERRORS.splitlines()[0])
        result, _ = self.collect(output='\n'.join(json.dumps(dict(row, PRIORITY=str(p))) for p in range(4)))
        self.assertEqual([e.priority for e in result.events], [0, 1, 2, 3])

    def test_diagnostics_and_exit_failures(self):
        for output, stderr, code, expected, sudo in (
                ('', 'Permission denied', 1, SourceStatus.PERMISSION_DENIED, True),
                (ERRORS, 'Hint: You are currently not seeing messages from other users and the system.', 0, SourceStatus.PARTIAL, True),
                ('', 'No journal files were found.', 0, SourceStatus.NOT_FOUND, False),
                (ERRORS, 'corrupt file', 0, SourceStatus.PARTIAL, False),
                (ERRORS, 'I/O error', 1, SourceStatus.ERROR, False)):
            with self.subTest(stderr=stderr):
                result, _ = self.collect(output, stderr, code)
                self.assertEqual(result.status, expected)
                self.assertEqual('sudo' in render_errors(result), sudo)

    def test_execution_failures(self):
        for error, status in ((FileNotFoundError(), SourceStatus.UNSUPPORTED),
                              (PermissionError(), SourceStatus.ERROR),
                              (subprocess.TimeoutExpired('journalctl', 30), SourceStatus.ERROR)):
            with self.subTest(error=error), patch('whatbroke.collectors.errors.collect_boots', return_value=self.history()), patch(
                    'whatbroke.collectors.errors.subprocess.run', side_effect=error):
                self.assertEqual(collect_errors('-1').status, status)

    def test_limit_and_control_character_escaping(self):
        row = json.loads(ERRORS.splitlines()[0])
        row['MESSAGE'] = 'line1\n\x1b[31mline2'
        result, _ = self.collect(output=ERRORS + json.dumps(row))
        report = render_errors(result, 1)
        self.assertIn('Error-or-higher records: 3', report)
        self.assertIn('Last 1 errors', report)
        self.assertNotIn('\x1b', report)
        self.assertEqual(result.events[-1].message, row['MESSAGE'])

    def test_cli_selection_limit_and_status(self):
        result, _ = self.collect()
        with patch('whatbroke.cli.collect_errors', return_value=result) as collect, redirect_stdout(StringIO()):
            self.assertEqual(main(['errors', '--boot', '-1', '--limit', '1']), 0)
        collect.assert_called_once_with('-1')
        result.status = SourceStatus.PARTIAL
        with patch('whatbroke.cli.collect_errors', return_value=result), redirect_stdout(StringIO()):
            self.assertEqual(main(['errors']), 1)

    def test_invalid_selectors_and_limits(self):
        for args in (['--boot', 'all'], ['--boot', 'nonsense'], ['--limit', '0']):
            with self.subTest(args=args), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
                main(['errors', *args])
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()

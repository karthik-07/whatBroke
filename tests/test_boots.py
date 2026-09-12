"""Boot collector tests with synthetic journalctl output only."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from whatbroke.cli import main
from whatbroke.collectors.journal import collect_boots, parse_boots
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.boots import render_boots

FIXTURE = (Path(__file__).parent / 'fixtures/journal/boots.json').read_text()


class BootTests(unittest.TestCase):
    def collect(self, output=FIXTURE, error='', code=0):
        with patch('whatbroke.collectors.journal.subprocess.run', return_value=
                   subprocess.CompletedProcess([], code, output, error)):
            return collect_boots()

    def test_boot_ids_indices_and_microsecond_utc_timestamps(self):
        result = parse_boots(FIXTURE)
        self.assertEqual(result.status, SourceStatus.AVAILABLE)
        self.assertEqual([b.index for b in result.boots], [-1, 0])
        self.assertEqual(result.boots[0].boot_id, '1' * 32)
        self.assertEqual(result.boots[0].first_entry.isoformat(), '2026-01-01T00:00:00.000001+00:00')
        self.assertEqual(result.boots[-1].last_entry.isoformat(), '2026-01-02T01:00:00+00:00')

    def test_malformed_and_duplicate_rows_preserve_valid_boots(self):
        rows = json.loads(FIXTURE)
        rows.extend([{}, None, rows[0], dict(rows[1], boot_id='invalid'),
                     dict(rows[1], index=True), dict(rows[1], first_entry=-1),
                     dict(rows[1], last_entry=10**100), dict(rows[1], first_entry='123'),
                     dict(rows[1], last_entry=0)])
        result = parse_boots(json.dumps(rows))
        self.assertEqual(len(result.boots), 2)
        self.assertEqual(result.malformed_records, 9)
        self.assertEqual(result.status, SourceStatus.PARTIAL)

    def test_invalid_json_and_unsupported_text_output(self):
        for output in ('not json', '{}', 'null'):
            with self.subTest(output=output):
                result = self.collect(output)
                self.assertEqual(result.status, SourceStatus.ERROR)
                self.assertNotIn('sudo', render_boots(result))

    def test_empty_history(self):
        for output, error in (('[]', ''), ('', ''), ('', 'No journal files were found.')):
            with self.subTest(output=output, error=error):
                result = self.collect(output, error)
                self.assertEqual(result.status, SourceStatus.NOT_FOUND)
                self.assertNotIn('sudo', render_boots(result))

    def test_privilege_hint_even_on_success_marks_partial(self):
        result = self.collect(error='Hint: You are currently not seeing messages from other users and the system.')
        self.assertEqual(result.status, SourceStatus.PARTIAL)
        self.assertEqual(len(result.boots), 2)
        self.assertIn('sudo', render_boots(result))

    def test_permission_denied_with_no_boots(self):
        result = self.collect('', 'No journal files were opened due to insufficient permissions.', 1)
        self.assertEqual(result.status, SourceStatus.PERMISSION_DENIED)
        self.assertTrue(result.access_limited)

    def test_permission_denied_takes_precedence_over_missing_hint(self):
        result = self.collect('', 'Permission denied\nNo journal files were found.')
        self.assertEqual(result.status, SourceStatus.PERMISSION_DENIED)

    def test_other_warning_is_partial_without_sudo(self):
        result = self.collect(error='Journal file is truncated, ignoring file.')
        self.assertEqual(result.status, SourceStatus.PARTIAL)
        self.assertNotIn('sudo', render_boots(result))

    def test_nonzero_preserves_valid_output_but_reports_error(self):
        result = self.collect(code=1, error='I/O error')
        self.assertEqual(result.status, SourceStatus.ERROR)
        self.assertEqual(len(result.boots), 2)
        self.assertNotIn('sudo', render_boots(result))

    def test_unavailable_command_and_execution_failures(self):
        for error, status in ((FileNotFoundError(), SourceStatus.UNSUPPORTED),
                              (PermissionError(), SourceStatus.ERROR),
                              (OSError('failed'), SourceStatus.ERROR),
                              (subprocess.TimeoutExpired('journalctl', 30), SourceStatus.ERROR)):
            with self.subTest(error=error), patch('whatbroke.collectors.journal.subprocess.run', side_effect=error):
                result = collect_boots()
                self.assertEqual(result.status, status)
                self.assertNotIn('sudo', render_boots(result))

    def test_command_preserves_warnings_and_forces_stable_locale(self):
        with patch('whatbroke.collectors.journal.subprocess.run', return_value=
                   subprocess.CompletedProcess([], 0, FIXTURE, '')) as run:
            collect_boots()
        args, kwargs = run.call_args
        self.assertIn('--system', args[0])
        self.assertIn('--no-pager', args[0])
        self.assertNotIn('--quiet', args[0])
        self.assertEqual(kwargs['env']['LC_ALL'], 'C')
        self.assertEqual(kwargs['timeout'], 30)

    def test_limit_does_not_shorten_total_history(self):
        report = render_boots(parse_boots(FIXTURE), 1)
        self.assertIn('Visible boots: 2', report)
        self.assertIn('2026-01-01T00:00:00.000001', report)
        self.assertNotIn('1' * 32, report)
        self.assertIn('2' * 32, report)

    def test_terminal_controls_in_diagnostics_are_escaped(self):
        result = self.collect(error='Warning: \x1b[31m bad journal')
        self.assertNotIn('\x1b', render_boots(result))

    def test_cli_success_and_partial_exit_codes(self):
        for result, expected in ((self.collect(), 0), (self.collect(error='Permission denied'), 1)):
            with patch('whatbroke.cli.collect_boots', return_value=result), redirect_stdout(StringIO()) as output:
                self.assertEqual(main(['boots', '--limit', '1']), expected)
                self.assertIn('Last 1 visible boots', output.getvalue())

    def test_invalid_cli_limit(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            main(['boots', '--limit', '0'])
        self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()

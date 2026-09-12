"""Package candidates must precede new failures and disclose uncertain history."""
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import timedelta, timezone
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from test_compare import collection, NOW
from whatbroke.analysis.compare import compare_collections
from whatbroke.analysis.correlate import correlate
from whatbroke.collectors.pacman import collect_pacman
from whatbroke.models.packages import PackageCollection
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.correlate import render_correlation
from whatbroke.cli import main

FIXTURE = Path(__file__).parent / 'fixtures/pacman/correlation.log'


class CorrelationTests(unittest.TestCase):
    def comparison(self):
        target = collection(0, ['new', 'new'])
        target.events = [replace(target.events[0], timestamp=NOW + timedelta(hours=4)),
                         replace(target.events[1], timestamp=NOW + timedelta(hours=2))]
        target.boot = replace(target.boot, first_entry=NOW + timedelta(hours=1, minutes=15),
                              last_entry=NOW + timedelta(hours=4))
        return compare_collections(target, [collection(-1)], 1)

    def packages(self):
        return collect_pacman(FIXTURE)

    def test_strict_window_earliest_failure_and_original_versions(self):
        result = correlate(self.comparison(), self.packages())
        finding = result.findings[0]
        self.assertEqual(finding.start, NOW + timedelta(hours=1))
        self.assertEqual(finding.end, NOW + timedelta(hours=2))
        self.assertEqual([e.package for e in finding.candidates], ['linux'])
        self.assertEqual(finding.candidates[0].old_version, '1-1')
        self.assertEqual(finding.candidates[0].new_version, '2-1')
        self.assertIn('boundary', ' '.join(finding.limitations))

    def test_nearest_earlier_baseline_by_boot_order(self):
        comparison = self.comparison()
        old = collection(-2)
        old.boot = replace(old.boot, last_entry=NOW)
        comparison.previous.insert(0, old)
        comparison.findings[0].previous_counts.insert(0, 0)
        finding = correlate(comparison, self.packages()).findings[0]
        self.assertEqual(finding.baseline_boot_id, comparison.previous[-1].boot.boot_id)

    def test_clock_overlap_does_not_infer_window(self):
        comparison = self.comparison()
        comparison.previous[0].boot = replace(comparison.previous[0].boot, last_entry=NOW + timedelta(hours=3))
        result = correlate(comparison, self.packages())
        self.assertEqual(result.findings[0].candidates, [])
        self.assertIn('clock ordering', ' '.join(result.findings[0].limitations))

    def test_missing_and_permission_denied_history(self):
        for status in (SourceStatus.NOT_FOUND, SourceStatus.PERMISSION_DENIED):
            result = correlate(self.comparison(), PackageCollection(Path('/missing'), status))
            self.assertEqual(result.status, SourceStatus.PARTIAL)
            self.assertEqual(result.findings[0].candidates, [])
            self.assertEqual('sudo' in render_correlation(result), status == SourceStatus.PERMISSION_DENIED)

    def test_partial_log_preserves_candidates_and_discloses_skips(self):
        packages = self.packages()
        packages.status = SourceStatus.PARTIAL
        packages.malformed_lines = 2
        result = correlate(self.comparison(), packages)
        self.assertEqual(len(result.findings[0].candidates), 1)
        self.assertIn('Skipped package-log records: 2', render_correlation(result))

    def test_history_bounds_do_not_silently_cover_window(self):
        packages = self.packages()
        packages.history.earliest = NOW + timedelta(hours=1, minutes=15)
        packages.history.latest = NOW + timedelta(hours=1, minutes=45)
        notes = ' '.join(correlate(self.comparison(), packages).findings[0].limitations)
        self.assertIn('start after', notes)
        self.assertIn('may simply have been idle', notes)

    def test_naive_timestamps_are_excluded(self):
        packages = self.packages()
        packages.events = [replace(packages.events[1], timestamp=NOW.replace(tzinfo=None) + timedelta(hours=1, minutes=30))]
        result = correlate(self.comparison(), packages)
        self.assertEqual(result.findings[0].candidates, [])
        self.assertIn('without a timezone', ' '.join(result.findings[0].limitations))

    def test_offsets_are_compared_as_instants(self):
        packages = self.packages()
        packages.events = [replace(packages.events[1], timestamp=(NOW + timedelta(hours=1, minutes=30)).astimezone(timezone(timedelta(hours=-5))))]
        self.assertEqual(len(correlate(self.comparison(), packages).findings[0].candidates), 1)

    def test_recurring_and_variants_not_correlated(self):
        comparison = self.comparison()
        for label in ('recurring', 'recurring failure — new variant', 'insufficient history'):
            comparison.findings[0].classification = label
            self.assertEqual(correlate(comparison, self.packages()).findings, [])

    def test_cli_explicit_log_and_partial_exit(self):
        with patch('whatbroke.cli.collect_comparison', return_value=self.comparison()), patch(
                'whatbroke.cli.resolve_log_path') as resolve, redirect_stdout(StringIO()) as output:
            self.assertEqual(main(['compare', '--log-file', str(FIXTURE)]), 1)
        resolve.assert_not_called()
        self.assertIn('PACKAGE-CHANGE CORRELATION', output.getvalue())
        self.assertIn('upgraded linux', output.getvalue())

    def test_cli_skips_package_reads_for_recurring_findings(self):
        comparison = self.comparison()
        comparison.findings[0].classification = 'recurring failure — new variant'
        with patch('whatbroke.cli.collect_comparison', return_value=comparison), patch(
                'whatbroke.cli.collect_pacman') as collect, redirect_stdout(StringIO()) as output:
            self.assertEqual(main(['compare']), 0)
        collect.assert_not_called()
        self.assertNotIn('Package correlation not attempted', output.getvalue())
        self.assertNotIn('Package logs were not checked', output.getvalue())

    def test_covered_window_without_candidates_is_explicit(self):
        packages = self.packages()
        packages.events = []
        result = correlate(self.comparison(), packages)
        self.assertEqual(result.status, SourceStatus.AVAILABLE)
        self.assertIn('does not rule out', render_correlation(result))


if __name__ == '__main__':
    unittest.main()

"""Summary grouping preserves totals, uncertainty, and access to exact evidence."""
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from test_compare import collection
from test_families import wifi
from whatbroke.analysis.compare import compare_collections
from whatbroke.analysis.correlate import Correlation, CorrelationReport
from whatbroke.cli import main
from whatbroke.models.errors import ErrorCollection
from whatbroke.models.packages import PackageCollection, PackageEvent
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.summary import groups, overall_status, render_report


def iwd(index, number, error='org.freedesktop.DBus.Error.NotFound: No matching method found'):
    return collection(index, [f'<error> [1789160536.6679] device (/net/connman/iwd/{number}): '
                              f'.Set failed: GDBus.Error:{error}'])


class SummaryTests(unittest.TestCase):
    def test_iwd_variants_group_without_merging_error_types(self):
        target = iwd(0, 0)
        target.events += iwd(0, 1).events * 2
        target.events += iwd(0, 2, 'net.connman.iwd.Failed: Operation failed').events
        result = compare_collections(target, [collection(-1)], 1)
        grouped = groups(result)
        self.assertEqual(len(result.findings), 3)
        self.assertEqual([g.count for g in grouped], [3, 1])
        self.assertEqual(sum(g.count for g in grouped), len(target.events))
        self.assertNotIn('/net/connman/iwd/1', render_report(result))
        self.assertIn('/net/connman/iwd/1', render_report(result, verbose=True))

    def test_existing_family_recurrence_and_counts_not_double_counted(self):
        target = wifi(0, 'wlan0')
        target.events += wifi(0, 'wlan2').events * 2
        result = compare_collections(target, [wifi(-1, 'wlan0')], 1)
        grouped = groups(result)
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0].count, 3)
        self.assertEqual(grouped[0].classification, 'Recurring')

    def test_new_iwd_pattern_recurrence_changes_classification(self):
        finding = compare_collections(iwd(0, 12), [iwd(-1, 0)], 1).findings[0]
        self.assertEqual(finding.classification, 'recurring failure — new variant')
        self.assertEqual(finding.previous_counts, [0])
        self.assertEqual(finding.family_previous_counts, [1])

    def test_near_matches_and_sources_do_not_group(self):
        for change in ('method', 'path', 'error', 'source'):
            target = iwd(0, 0)
            event = iwd(0, 1).events[0]
            if change == 'method':
                event = replace(event, message=event.message.replace('.Set', '.Get'))
            elif change == 'path':
                event = replace(event, message=event.message.replace('/iwd/1', '/other/1'))
            elif change == 'error':
                event = replace(event, message=event.message + ' with extra detail')
            else:
                event = replace(event, unit='other.service', identifier='other')
            target.events.append(event)
            self.assertEqual(len(groups(compare_collections(target, [collection(-1)], 1))), 2, change)

    def test_connect_aborted_rule_preserves_other_errors(self):
        text = '<error> [1789160536.6679] device (wlan0): Activation: (wifi) Network.Connect failed: GDBus.Error:net.connman.iwd.Aborted: Operation aborted'
        target = collection(0, [text, text.replace('wlan0', 'wlan12'), text.replace('Operation aborted', 'Different detail')])
        grouped = groups(compare_collections(target, [collection(-1)], 1))
        self.assertEqual(len(grouped), 2)
        self.assertEqual(sorted(g.count for g in grouped), [1, 2])

    def test_incomplete_variant_history_remains_visible(self):
        prior = iwd(-1, 0)
        prior.status = SourceStatus.PARTIAL
        result = compare_collections(iwd(0, 1), [prior], 1)
        self.assertIn('variant history incomplete', render_report(result))
        self.assertEqual(overall_status(result, None), SourceStatus.PARTIAL)

    def test_no_baseline_does_not_become_new_group(self):
        result = compare_collections(iwd(0, 0), [], 5)
        self.assertEqual(groups(result)[0].classification, 'Insufficient history')

    def test_correlation_deduplicates_candidates_and_limitations(self):
        result = compare_collections(iwd(0, 0), [collection(-1)], 1)
        event = PackageEvent(result.target.events[0].timestamp, 'upgraded', 'linux', '1', '2', Path('log'), 3, 'raw')
        finding = Correlation(result.findings[0].key, candidates=[event], limitations=['Unverified tail coverage.'])
        report = CorrelationReport(PackageCollection(Path('log')), [finding, finding], SourceStatus.PARTIAL)
        text = render_report(result, report)
        self.assertTrue(text.startswith('Overall status: partial'))
        self.assertEqual(text.count('Unverified tail coverage.'), 1)
        self.assertEqual(text.count('upgraded linux'), 1)
        self.assertIn('1 unique candidate changes', text)

    def test_verbose_and_summary_have_same_status_and_cli_reads(self):
        result = compare_collections(collection(0, ['recurring']), [collection(-1, ['recurring'])], 1)
        for flags in ([], ['--verbose']):
            with patch('whatbroke.cli.collect_comparison', return_value=result) as collect, redirect_stdout(StringIO()) as output:
                self.assertEqual(main(['compare', *flags]), 0)
            collect.assert_called_once_with('current', 5)
            self.assertTrue(output.getvalue().startswith('Overall status: available'))
            self.assertEqual('Evidence:' in output.getvalue(), bool(flags))

    def test_errors_and_permissions_not_hidden_by_summary(self):
        target = ErrorCollection('current', SourceStatus.PERMISSION_DENIED, error='Permission denied', access_limited=True)
        result = compare_collections(target, [], 5)
        text = render_report(result)
        self.assertIn('absence of errors cannot be established', text)
        self.assertIn('sudo', text)
        self.assertIn('permission_denied', text)

    def test_source_and_message_controls_are_escaped(self):
        target = collection(0, ['error\x1b[31m'])
        target.events[0] = replace(target.events[0], unit='bad\x1b[0m')
        result = compare_collections(target, [collection(-1)], 1)
        self.assertNotIn('\x1b', render_report(result))

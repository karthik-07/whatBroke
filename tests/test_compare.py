"""Regression scenarios for evidence-based boot comparison."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from io import StringIO
import unittest
from unittest.mock import patch

from whatbroke.analysis.compare import signature, compare_collections, collect_comparison
from whatbroke.cli import main
from whatbroke.models.boots import Boot, BootCollection
from whatbroke.models.errors import ErrorEvent, ErrorCollection
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.compare import render_comparison
from whatbroke.reporting.errors import render_errors

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def collection(index, messages=(), status=SourceStatus.AVAILABLE):
    boot = Boot(index, f'{index+100:032x}', NOW, NOW + timedelta(hours=1))
    return ErrorCollection(str(index), status, boot, [
        ErrorEvent(NOW, boot.boot_id, 3, text, 'NetworkManager.service', 'NetworkManager', None, None, {})
        for text in messages])


class ComparisonTests(unittest.TestCase):
    def test_variable_timestamp_and_pointer_are_recurring(self):
        target = collection(0, ['<error> [1789160536.6679] iwd-manager[0x561a959cff90]: failed'] * 2)
        baseline = collection(-1, ['<error> [1789150000.1234] iwd-manager[0x123456789abc]: failed'])
        result = compare_collections(target, [baseline], 1)
        self.assertEqual(result.findings[0].classification, 'recurring')
        self.assertEqual(result.findings[0].count, 2)
        self.assertEqual(result.findings[0].previous_counts, [1])
        self.assertEqual(result.findings[0].example.message, target.events[0].message)

    def test_new_and_recurring_per_boot_counts(self):
        result = compare_collections(collection(0, ['old', 'new', 'new']),
                                     [collection(-2, ['old'] * 3), collection(-1)], 2)
        self.assertEqual([f.classification for f in result.findings], ['newly observed', 'recurring'])
        self.assertEqual(result.findings[0].previous_counts, [0, 0])
        self.assertEqual(result.findings[1].previous_counts, [3, 0])

    def test_no_baseline_never_claims_new(self):
        result = compare_collections(collection(0, ['error']), [], 5)
        self.assertEqual(result.findings[0].classification, 'insufficient history')
        self.assertEqual(result.status, SourceStatus.PARTIAL)

    def test_incomplete_baseline_or_target_blocks_new(self):
        for target_status, prior_status in ((SourceStatus.AVAILABLE, SourceStatus.PARTIAL),
                                           (SourceStatus.PARTIAL, SourceStatus.AVAILABLE),
                                           (SourceStatus.AVAILABLE, SourceStatus.PERMISSION_DENIED)):
            result = compare_collections(collection(0, ['new'], target_status), [collection(-1, (), prior_status)], 1)
            self.assertEqual(result.findings[0].classification, 'insufficient history')

    def test_positive_evidence_in_partial_baseline_is_recurring(self):
        result = compare_collections(collection(0, ['error']), [collection(-1, ['error'], SourceStatus.PARTIAL)], 1)
        self.assertEqual(result.findings[0].classification, 'recurring')
        self.assertIn('1 observed (incomplete)', render_comparison(result))

    def test_fewer_available_boots_are_disclosed(self):
        result = compare_collections(collection(0, ['new']), [collection(-1)], 5)
        self.assertEqual(result.findings[0].classification, 'newly observed')
        self.assertEqual(result.status, SourceStatus.PARTIAL)
        self.assertIn('requested 5; selected 1', render_comparison(result))

    def test_devices_paths_codes_and_sources_remain_distinct(self):
        event = collection(0, ['wlan0 /usr/bin/iw errno 19 0x1234']).events[0]
        for message in ('wlan1 /usr/bin/iw errno 19 0x1234', 'wlan0 /usr/bin/ip errno 19 0x1234',
                        'wlan0 /usr/bin/iw errno 20 0x1234', 'wlan0 /usr/bin/iw errno 19 0x5678'):
            self.assertNotEqual(signature(event), signature(replace(event, message=message)))
        self.assertNotEqual(signature(event), signature(replace(event, unit='other.service')))

    def test_unknown_sources_are_not_aggressively_normalized(self):
        event = collection(0, ['object[0x123456789abc]']).events[0]
        event = replace(event, unit='other.service', identifier='other')
        self.assertNotEqual(signature(event), signature(replace(event, message='object[0x999999999999]')))

    def test_empty_messages_are_excluded_and_labelled(self):
        target = collection(0, ['', '   '])
        result = compare_collections(target, [collection(-1)], 1)
        self.assertEqual(result.empty_records, 2)
        self.assertEqual(result.findings, [])
        self.assertIn('[empty message]', render_errors(target))

    def test_missing_target_returns_source_failure(self):
        target = ErrorCollection('current', SourceStatus.NOT_FOUND, error='missing')
        result = compare_collections(target, [], 5)
        self.assertEqual(result.status, SourceStatus.NOT_FOUND)
        self.assertIn('missing', render_comparison(result))

    def test_selected_boot_uses_only_earlier_boots_and_one_discovery(self):
        collections = [collection(i) for i in range(-4, 1)]
        history = BootCollection(boots=[c.boot for c in collections])
        def collect(selector, *, history):
            return next(c for c in collections if selector in (c.selector, c.boot.boot_id))
        with patch('whatbroke.analysis.compare.collect_boots', return_value=history) as discovery, patch(
                'whatbroke.analysis.compare.collect_errors', side_effect=collect):
            result = collect_comparison('-1', 2)
        discovery.assert_called_once()
        self.assertEqual([c.boot.index for c in result.previous], [-3, -2])

    def test_cli_default_and_custom_previous(self):
        result = compare_collections(collection(0), [collection(-1)], 1)
        with patch('whatbroke.cli.collect_comparison', return_value=result) as collect, redirect_stdout(StringIO()):
            self.assertEqual(main(['compare']), 0)
            collect.assert_called_with('current', 5)
            main(['compare', '--boot', '-1', '--previous', '15'])
            collect.assert_called_with('-1', 15)

    def test_cli_invalid_previous(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            main(['compare', '--previous', '0'])
        self.assertEqual(caught.exception.code, 2)

    def test_output_escapes_evidence_and_only_suggests_sudo_for_access(self):
        target = collection(0, ['error\x1b[31m'])
        result = compare_collections(target, [collection(-1)], 1)
        self.assertNotIn('\x1b', render_comparison(result))
        self.assertNotIn('sudo', render_comparison(result))
        target.access_limited = True
        self.assertIn('sudo', render_comparison(result))


if __name__ == '__main__':
    unittest.main()

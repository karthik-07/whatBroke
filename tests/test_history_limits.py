"""History bounds must describe discovery, regardless of display or boot selection."""
from pathlib import Path
import unittest
from unittest.mock import patch

from whatbroke.analysis.compare import compare_collections
from whatbroke.collectors.errors import collect_errors
from whatbroke.collectors.journal import parse_boots
from whatbroke.reporting.boots import render_boots
from whatbroke.reporting.compare import render_comparison
from whatbroke.reporting.errors import render_errors


class HistoryLimitTests(unittest.TestCase):
    def test_display_limit_does_not_change_discovered_bounds(self):
        history = parse_boots((Path(__file__).parent / 'fixtures/journal/boots.json').read_text())
        for limit in (1, 200, 500):
            report = render_boots(history, limit)
            self.assertIn('History limit: 2 boots visible; earliest record: 2026-01-01', report)
            self.assertIn('Increasing --limit only displays more available boots', report)

    def test_missing_selected_boot_keeps_global_history_in_reports(self):
        history = parse_boots((Path(__file__).parent / 'fixtures/journal/boots.json').read_text())
        with patch('whatbroke.collectors.errors.subprocess.run') as run:
            result = collect_errors('-200', history=history)
        run.assert_not_called()
        for report in (render_errors(result), render_comparison(compare_collections(result, [], 5))):
            self.assertIn('History limit: 2 boots visible; earliest record: 2026-01-01', report)
            self.assertIn('Earlier history is unavailable to this query', report)

    def test_empty_history_does_not_invent_a_date(self):
        report = render_boots(parse_boots('[]'))
        self.assertIn('no readable boot records were returned', report)
        self.assertNotIn('earliest record:', report)

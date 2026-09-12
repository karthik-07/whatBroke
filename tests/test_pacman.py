"""Portable regression tests: no live system logs, Arch install, or root needed."""

from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from whatbroke.cli import main
from whatbroke.collectors.pacman import collect_pacman
from whatbroke.distros.arch.pacman import DEFAULT_LOG, resolve_log_path
from whatbroke.models.packages import SourceStatus
from whatbroke.reporting.packages import render_packages

FIXTURES = Path(__file__).parent / "fixtures" / "pacman"


class CollectorTests(unittest.TestCase):
    def collect_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pacman.log"
            path.write_text(text)
            return collect_pacman(path)

    def test_all_actions_and_evidence(self):
        result = collect_pacman(FIXTURES / "transactions.log")
        self.assertEqual(result.status, SourceStatus.AVAILABLE)
        self.assertEqual([event.action for event in result.events],
                         ["installed", "upgraded", "downgraded", "reinstalled", "removed"])
        self.assertEqual([(event.old_version, event.new_version) for event in result.events],
                         [(None, "1:1.0-1"), ("1:1.0-1", "1:2.0-1"),
                          ("1:2.0-1", "1:1.0-1"), ("1:1.0-1", "1:1.0-1"), ("1:1.0-1", None)])
        self.assertEqual(result.events[0].line_number, 3)
        self.assertIn("installed example", result.events[0].raw)
        self.assertEqual(result.events[0].source, FIXTURES / "transactions.log")
        self.assertEqual(result.ignored_lines, 4)
        self.assertEqual(result.history.earliest.isoformat(), "2026-02-01T08:00:00+00:00")
        self.assertEqual(result.history.latest.isoformat(), "2026-02-07T08:00:00+00:00")

    def test_malformed_records_do_not_hide_later_events(self):
        result = collect_pacman(FIXTURES / "malformed.log")
        self.assertEqual(result.status, SourceStatus.PARTIAL)
        self.assertEqual(result.malformed_lines, 4)
        self.assertEqual(result.malformed_examples, [2, 3, 4, 5])
        self.assertEqual(len(result.events), 2)
        self.assertNotIn("sudo", render_packages(result))

    def test_history_uses_chronological_bounds_and_offsets(self):
        result = self.collect_text(
            "[2026-02-02T01:00:00+0200] [ALPM] transaction started\n"
            "[2026-02-01T23:30:00+0000] [ALPM] transaction completed\n"
            "[2026-01-01T00:00:00Z] [PACMAN] unrelated\n")
        self.assertEqual(result.history.earliest, datetime.fromisoformat("2026-01-01T00:00:00+00:00"))
        self.assertEqual(result.history.latest, datetime.fromisoformat("2026-02-01T23:30:00+00:00"))

    def test_legacy_timestamps_have_separate_bounds(self):
        result = self.collect_text(
            "[2014-01-01 12:00] installed old (1-1)\n"
            "[2016-01-01 12:00] [ALPM] upgraded old (1-1 -> 2-1)\n"
            "[2026-01-01T12:00:00+0000] [ALPM] removed old (2-1)\n")
        self.assertEqual(len(result.events), 3)
        self.assertIsNone(result.events[0].timestamp.tzinfo)
        self.assertEqual(result.local_history.earliest.year, 2014)
        self.assertEqual(result.local_history.latest.year, 2016)
        self.assertEqual(result.history.earliest.year, 2026)
        self.assertIn("timezone unknown", render_packages(result))

    def test_empty_file_has_no_coverage(self):
        result = self.collect_text("")
        self.assertEqual(result.status, SourceStatus.AVAILABLE)
        self.assertIsNone(result.history.earliest)
        self.assertIn("no readable, valid timestamps", render_packages(result))
        self.assertIn("does not establish system health", render_packages(result))

    def test_missing_file_does_not_suggest_sudo(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_pacman(Path(directory) / "absent")
        self.assertEqual(result.status, SourceStatus.NOT_FOUND)
        self.assertNotIn("sudo", render_packages(result))

    def test_permission_denied_suggests_sudo(self):
        with patch.object(Path, "open", side_effect=PermissionError):
            result = collect_pacman("restricted.log")
        self.assertEqual(result.status, SourceStatus.PERMISSION_DENIED)
        self.assertIn("sudo", render_packages(result))

    def test_other_io_error_is_not_a_permission_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_pacman(directory)
        self.assertEqual(result.status, SourceStatus.ERROR)
        self.assertNotIn("sudo", render_packages(result))

    def test_read_failure_preserves_collected_events(self):
        class FailingStream(StringIO):
            def __next__(self):
                if self.tell():
                    raise OSError("disk read failed")
                return super().__next__()
        with patch.object(Path, "open", return_value=FailingStream(
                "[2026-02-01T08:00:00+0000] [ALPM] installed good (1-1)\n")):
            result = collect_pacman("broken.log")
        self.assertEqual(result.status, SourceStatus.ERROR)
        self.assertEqual(len(result.events), 1)

    def test_bad_encoding_is_disclosed_and_parsing_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            path.write_bytes(b'\xff\n[2026-02-01T08:00:00+0000] [ALPM] installed good (1-1)\n')
            result = collect_pacman(path)
        self.assertEqual(result.malformed_lines, 1)
        self.assertEqual(len(result.events), 1)

    def test_malformed_examples_are_bounded(self):
        result = self.collect_text("garbage\n" * 20)
        self.assertEqual(result.malformed_lines, 20)
        self.assertEqual(len(result.malformed_examples), 5)

    def test_terminal_controls_are_escaped(self):
        result = self.collect_text("[2026-02-01T08:00:00+0000] [ALPM] installed good (1\x1b[31m)\n")
        self.assertNotIn("\x1b", render_packages(result))


class DiscoveryTests(unittest.TestCase):
    def test_configured_path(self):
        with patch("whatbroke.distros.arch.pacman.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 0, "/custom path/packages.log\n", "")) as run:
            result = resolve_log_path()
        self.assertEqual(result.path, Path("/custom path/packages.log"))
        self.assertIsNone(result.warning)
        self.assertEqual(run.call_args.args[0], ["pacman-conf", "LogFile"])

    def test_discovery_failures_disclose_fallback(self):
        for error in (FileNotFoundError(), PermissionError(),
                      subprocess.CalledProcessError(1, "pacman-conf"),
                      subprocess.TimeoutExpired("pacman-conf", 5)):
            with self.subTest(error=error), patch(
                    "whatbroke.distros.arch.pacman.subprocess.run", side_effect=error):
                result = resolve_log_path()
                self.assertEqual(result.path, DEFAULT_LOG)
                self.assertIn("--log-file", result.warning)

    def test_invalid_config_output_discloses_fallback(self):
        for output in ("", "relative.log", "/one\n/two"):
            with self.subTest(output=output), patch(
                    "whatbroke.distros.arch.pacman.subprocess.run", return_value=
                    subprocess.CompletedProcess([], 0, output, "")):
                self.assertIsNotNone(resolve_log_path().warning)


class CliTests(unittest.TestCase):
    def test_explicit_file_bypasses_discovery_and_limits_output(self):
        output = StringIO()
        with patch("whatbroke.cli.resolve_log_path") as resolve, redirect_stdout(output):
            code = main(["packages", "--log-file", str(FIXTURES / "transactions.log"), "--limit", "1"])
        resolve.assert_not_called()
        self.assertEqual(code, 0)
        self.assertIn("Last 1 package events", output.getvalue())
        self.assertNotIn("  2026-02-01", output.getvalue())

    def test_partial_results_return_nonzero(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["packages", "--log-file", str(FIXTURES / "malformed.log")]), 1)

    def test_nonpositive_limit_is_rejected(self):
        from contextlib import redirect_stderr
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            main(["packages", "--limit", "0"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

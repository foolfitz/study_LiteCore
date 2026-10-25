#!/usr/bin/env python3
"""Exercise report setup for normal and W-D modes without starting a browser."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

RUNNER = Path(__file__).resolve().parents[1] / "tools" / "run_v23_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("run_v23_diagnostic_setup", RUNNER)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class ReachedBrowserBoundary(Exception):
    """Raised before common setup can start a browser or service."""


class StopAtBrowserLock:
    def __enter__(self):
        raise ReachedBrowserBoundary

    def __exit__(self, exc_type, exc, tb):
        return False


class RunnerReportSetupTests(unittest.TestCase):
    def exercise_report_setup(self, wd):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "plain-grapheme.odt"
            fixture.write_bytes(b"fixture")
            base_input = root / "base-instrument.js"
            base_input.write_text("base instrument")
            wd_input = root / "wd-instrument.js"
            wd_input.write_text("wd instrument")
            output = root / "out"
            mirror_calls = []

            def mirror(target, fixture_path):
                target.mkdir(parents=True, exist_ok=False)
                (target / "v23-diagnostic-wd.js").write_text("wd mirror")
                mirror_calls.append((target, fixture_path))

            wd_instrument_files = mock.Mock(return_value=[wd_input])
            fake_wd_cases = types.SimpleNamespace(instrument_files=wd_instrument_files)
            argv = [
                "run_v23_diagnostic.py",
                "--profile", "e2-editor-v23-diag-r2",
                "--wasm-sha256", "a" * 64,
                "--fixture", str(fixture),
                "--output", str(output),
                "--browser", "chrome",
                "--rounds", "1",
            ]
            if wd:
                argv.extend(("--arm", "wd", "--case-id", "d1"))
            else:
                argv.extend(("--arm", "all"))

            with (
                mock.patch.object(runner, "PROJECT", root),
                mock.patch.object(runner, "identity", return_value={"probe.wasm": "pinned"}),
                mock.patch.object(runner, "instrument_files", return_value=[base_input]) as base_instruments,
                mock.patch.object(runner, "sha", return_value="instrument-sha"),
                mock.patch.object(runner, "served_instruments", return_value={}),
                mock.patch.object(runner, "mirror", side_effect=mirror),
                mock.patch.object(runner.common, "browser_lock", side_effect=lambda _name: StopAtBrowserLock()),
                mock.patch.dict(sys.modules, {"v23_wd_cases": fake_wd_cases}),
                mock.patch.object(sys, "argv", argv),
            ):
                with self.assertRaises(ReachedBrowserBoundary):
                    runner.main()

            self.assertEqual(1, base_instruments.call_count)
            self.assertEqual(1 if wd else 0, wd_instrument_files.call_count)
            self.assertEqual(1, len(mirror_calls))
            self.assertTrue((output / "mirror" / "v23-diagnostic-wd.js").is_file())

    def test_normal_report_setup_reaches_browser_boundary(self):
        self.exercise_report_setup(wd=False)

    def test_wd_report_setup_reaches_browser_boundary(self):
        self.exercise_report_setup(wd=True)


if __name__ == "__main__":
    unittest.main()

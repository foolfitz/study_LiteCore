from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from build_finding_016_scheduler_profile import build_profile  # noqa: E402


class Finding016SchedulerTest(unittest.TestCase):
    def test_profile_is_isolated_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="finding-016-scheduler-") as temporary:
            root = Path(temporary)
            source = root / "source.json"
            loader = root / "input.js"
            wasm = root / "input.wasm"
            worker = root / "worker.js"
            output = root / "output"
            source.write_text(json.dumps({
                "sdkVersion": "test",
                "profile": "writer-review",
                "artifactFiles": {"probe.js": "old.js", "probe.wasm": "old.wasm"},
                "capabilities": ["open-odt"],
            }), encoding="utf-8")
            loader.write_bytes(b"loader")
            wasm.write_bytes(b"wasm")
            worker.write_bytes(b"worker")

            manifest = build_profile(source, loader, wasm, worker, output)

            self.assertEqual(manifest["profile"], "finding-016-scheduler")
            self.assertEqual(
                manifest["diagnostic"]["experiment"],
                "finding-016-scheduler-drain",
            )
            self.assertIn("finding-016-scheduler-probe", manifest["capabilities"])
            self.assertFalse(manifest["diagnostic"]["productionArtifactReplaced"])
            self.assertFalse(manifest["diagnostic"]["rawCallbackExposed"])
            self.assertFalse(manifest["diagnostic"]["automaticRetry"])

    def test_diagnostic_sources_do_not_expose_raw_callback_or_retry(self) -> None:
        app = (PROJECT / "web" / "finding-016-scheduler-app.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("resultPayload", app)
        self.assertNotIn("retry", app.lower())
        self.assertIn("drainScheduler", app)


if __name__ == "__main__":
    unittest.main()

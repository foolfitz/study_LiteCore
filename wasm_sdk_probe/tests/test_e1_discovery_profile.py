from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from build_e1_discovery_profile import build_profile  # noqa: E402


class E1DiscoveryProfileTest(unittest.TestCase):
    def test_profile_is_isolated_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e1-profile-") as temporary:
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
            self.assertEqual(manifest["profile"], "e1-editor-discovery")
            self.assertEqual(manifest["diagnostic"]["scope"], "e1-odt-editing-discovery")
            self.assertFalse(manifest["diagnostic"]["productionArtifactReplaced"])
            self.assertFalse(manifest["diagnostic"]["rawCallbackExposed"])
            self.assertFalse(manifest["diagnostic"]["automaticRetry"])
            self.assertEqual(
                manifest["diagnostic"]["selectionBarrier"],
                "verified-single-writer-unit-v1",
            )
            self.assertFalse(manifest["diagnostic"]["stateWordCountUsedForCompletion"])
            self.assertTrue(manifest["diagnostic"]["boundaryRejectionRequiresFreshWorker"])
            self.assertIn("verified-selection-delete", manifest["capabilities"])
            self.assertEqual((output / "probe.js").read_bytes(), b"loader")
            self.assertEqual((output / "probe.wasm").read_bytes(), b"wasm")


if __name__ == "__main__":
    unittest.main()

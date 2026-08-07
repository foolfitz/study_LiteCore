from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from build_e1_b_profile import EDITOR_ACTIONS, build_profile  # noqa: E402


class E1BProfileTest(unittest.TestCase):
    def test_product_profile_is_narrow_and_not_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e1-b-profile-") as temporary:
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
                "capabilities": ["open-odt", "undo"],
                "diagnostic": {"scope": "must-be-removed"},
            }), encoding="utf-8")
            loader.write_bytes(b"loader")
            wasm.write_bytes(b"wasm")
            worker.write_bytes(b"worker")
            manifest = build_profile(source, loader, wasm, worker, output)

            self.assertEqual(manifest["profile"], "e1-editor-v1")
            self.assertNotIn("diagnostic", manifest)
            self.assertIn("narrow-editor-v1", manifest["capabilities"])
            self.assertNotIn("editor-discovery-closed-actions", manifest["capabilities"])
            contract = manifest["editorContract"]
            self.assertEqual(contract["version"], 1)
            self.assertEqual(contract["abiVersion"], 1)
            self.assertEqual(contract["actions"], EDITOR_ACTIONS)
            self.assertTrue(contract["boundaryRejectionRequiresFreshWorker"])
            self.assertFalse(contract["automaticRetry"])
            self.assertFalse(contract["rawCallbackExposed"])
            self.assertFalse(contract["arbitraryKeyCodeAccepted"])
            self.assertFalse(contract["arbitraryUnoCommandAccepted"])
            self.assertFalse(contract["diagnosticOperationsExposed"])
            self.assertEqual((output / "probe.js").read_bytes(), b"loader")
            self.assertEqual((output / "probe.wasm").read_bytes(), b"wasm")
            self.assertEqual((output / "sdk-worker.js").read_bytes(), b"worker")


if __name__ == "__main__":
    unittest.main()

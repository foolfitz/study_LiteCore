from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.validate_r7_corpus import validate_manifest  # noqa: E402


class R7CorpusValidatorTest(unittest.TestCase):
    def test_frozen_project_manifest_passes(self) -> None:
        project = Path(__file__).resolve().parent.parent
        result = validate_manifest(project / "test-docs" / "r7" / "manifest.json")
        self.assertTrue(result["pass"], result)
        self.assertEqual(len(result["documents"]), 5)

    def test_hash_mismatch_is_rejected_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r7-corpus-test-") as temporary:
            root = Path(temporary)
            fixture = root / "unknown.bin"
            fixture.write_bytes(b"safe test payload")
            actual_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
            manifest = {
                "schemaVersion": 1,
                "limits": {
                    "maxFileBytes": 1024,
                    "maxZipEntries": 10,
                    "maxUncompressedBytes": 1024,
                    "maxCompressionRatio": 10,
                },
                "documents": [
                    {
                        "id": "unknown",
                        "path": "unknown.bin",
                        "bytes": fixture.stat().st_size,
                        "sha256": "0" * 64,
                        "mediaType": "application/octet-stream",
                        "source": {"path": "generated", "license": "MPL-2.0"},
                        "expectedOpen": "typed-failure",
                        "mutationPolicy": "discovery-copy-only",
                        "pageClass": "short",
                        "anchors": [],
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            original = json.dumps(manifest)
            manifest_path.write_text(original, encoding="utf-8")

            result = validate_manifest(manifest_path)

            self.assertFalse(result["pass"])
            self.assertIn("exact bytes or SHA-256 mismatch", result["documents"][0]["errors"])
            self.assertEqual(result["documents"][0]["sha256"], actual_hash)
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()

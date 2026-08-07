from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from validate_e1_corpus import validate  # noqa: E402


class E1CorpusTest(unittest.TestCase):
    def test_generator_is_deterministic_and_valid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e1-corpus-") as temporary:
            output = Path(temporary)
            command = [
                sys.executable,
                str(PROJECT / "tools" / "create_e1_corpus.py"),
                "--output", str(output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            first = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            result = validate(output / "manifest.json")
            self.assertTrue(result["pass"])
            subprocess.run(command + ["--force"], check=True, capture_output=True, text=True)
            second = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [(item["id"], item["bytes"], item["sha256"]) for item in first["fixtures"]],
                [(item["id"], item["bytes"], item["sha256"]) for item in second["fixtures"]],
            )


if __name__ == "__main__":
    unittest.main()

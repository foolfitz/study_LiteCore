from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from build_finding_016_selection_barrier_profile import build_profile  # noqa: E402
from validate_finding_016_selection_barrier import (  # noqa: E402
    EXPECTED_BOUNDARY_CASES,
    EXPECTED_OUTPUT_NAMES,
    EXPECTED_POSITIVE_CASES,
    decide,
    evaluate_desktop_roundtrip,
)


def passing_result(browser: str) -> dict[str, object]:
    repetitions = [
        {
            "status": "passed",
            "completion": "verified-selection-delete",
            "changed": True,
            "revisionDelta": 1,
            "selectedTextMatches": True,
            "exactMutation": True,
            "undoRestored": True,
        }
        for _ in range(3)
    ]
    return {
        "browser": browser,
        "browserVersion": "test",
        "complete": True,
        "rawCallbackExposed": False,
        "automaticRetry": False,
        "manifest": {
            "profile": "finding-016-selection-barrier",
            "diagnostic": {
                "stateWordCountUsedForCompletion": False,
                "boundaryRejectionRequiresFreshWorker": True,
            },
        },
        "positiveCases": [
            {"id": case_id, "repetitions": repetitions}
            for case_id in EXPECTED_POSITIVE_CASES
        ],
        "boundaryCases": [
            {
                "id": case_id,
                "status": "rejected",
                "code": "EDITOR_BOUNDARY_UNSUPPORTED",
                "revisionDelta": 0,
                "contentUnchanged": True,
            }
            for case_id in EXPECTED_BOUNDARY_CASES
        ],
        "outputs": [
            {
                "zip": True,
                "crc": True,
                "xml": True,
                "anchorsPreserved": True,
            },
        ] * 5,
    }


class Finding016SelectionBarrierTest(unittest.TestCase):
    def test_profile_is_isolated_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="finding-016-selection-") as temporary:
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

            self.assertEqual(manifest["profile"], "finding-016-selection-barrier")
            self.assertIn("finding-016-selection-barrier", manifest["capabilities"])
            self.assertNotIn("comments", manifest["capabilities"])
            self.assertNotIn("tracked-changes", manifest["capabilities"])
            self.assertNotIn("provider-contract-1.0", manifest["capabilities"])
            self.assertFalse(manifest["diagnostic"]["productionArtifactReplaced"])
            self.assertFalse(manifest["diagnostic"]["rawCallbackExposed"])
            self.assertFalse(manifest["diagnostic"]["automaticRetry"])
            self.assertFalse(
                manifest["diagnostic"]["stateWordCountUsedForCompletion"]
            )
            self.assertEqual(
                manifest["diagnostic"]["boundaryReadbackDeadlineMs"], 250
            )
            self.assertFalse(
                manifest["diagnostic"]["deadlineCanDeclareMutationSuccess"]
            )
            self.assertTrue(
                manifest["diagnostic"]["boundaryRejectionRequiresFreshWorker"]
            )

    def test_two_browser_evidence_passes(self) -> None:
        summary = decide([passing_result("chrome"), passing_result("firefox")])
        self.assertTrue(summary["complete"])
        self.assertTrue(summary["pass"])
        self.assertEqual(
            summary["decision"],
            "SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART",
        )

    def test_missing_boundary_fails_closed(self) -> None:
        chrome = passing_result("chrome")
        chrome["boundaryCases"] = chrome["boundaryCases"][:-1]
        summary = decide([chrome, passing_result("firefox")])
        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "STOP_OR_RESCOPE")

    def test_desktop_roundtrip_requires_both_browsers_and_ten_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="finding-016-roundtrip-") as temporary:
            root = Path(temporary)
            results = []
            for browser in ("chrome", "firefox"):
                result = passing_result(browser)
                outputs = []
                for name in EXPECTED_OUTPUT_NAMES:
                    source = root / browser / name
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_bytes(f"{browser}:{name}".encode())
                    outputs.append({
                        "name": name,
                        "path": str(source),
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "zip": True,
                        "crc": True,
                        "xml": True,
                        "anchorsPreserved": True,
                    })
                result["outputs"] = outputs
                results.append(result)

            def fake_converter(source: Path, output: Path) -> dict[str, object]:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"%PDF-test")
                return {"pdf": str(output), "pass": True}

            roundtrip = evaluate_desktop_roundtrip(
                results, root / "roundtrip", converter=fake_converter
            )
            self.assertTrue(roundtrip["complete"])
            self.assertTrue(roundtrip["pass"])
            self.assertEqual(len(roundtrip["documents"]), 10)
            self.assertTrue(all(item["pass"] for item in roundtrip["documents"]))

            results[1]["outputs"] = results[1]["outputs"][:-1]
            incomplete = evaluate_desktop_roundtrip(
                results, root / "incomplete", converter=fake_converter
            )
            self.assertFalse(incomplete["pass"])

    def test_sources_do_not_use_state_word_count_or_retry(self) -> None:
        app = (PROJECT / "web" / "finding-016-selection-barrier-app.js").read_text(
            encoding="utf-8"
        )
        engine = (PROJECT / "src" / "probe_engine.cpp").read_text(encoding="utf-8")
        self.assertNotIn("StateWordCount", app)
        self.assertIn("automaticRetry: false", app)
        self.assertNotIn("retryOperation", app)
        self.assertIn("OXSDK_FINDING_016_SELECTION_BARRIER", engine)
        self.assertIn("verified-selection-delete", engine)
        self.assertIn("UnitVerificationQueued", engine)
        self.assertIn("FinalVerificationQueued", engine)
        self.assertIn("EditorSelectionBarrierStep", engine)
        self.assertIn("wait_until", engine)
        self.assertNotIn("selectionBarrierDeadlineElapsed", engine)


if __name__ == "__main__":
    unittest.main()

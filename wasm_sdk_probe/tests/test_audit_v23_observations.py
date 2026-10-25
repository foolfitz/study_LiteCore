#!/usr/bin/env python3
"""Focused causal-red tests for the read-only R2 observation auditor."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "audit_v23_observations.py"
SPEC = importlib.util.spec_from_file_location("audit_v23_observations", TOOL)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

IDENTITY = {
    "probe.js": "js-hash",
    "probe.wasm": "wasm-hash",
    "sdk-worker.js": "worker-hash",
    "sdk-manifest.json": "manifest-hash",
}


def valid_page():
    return {
        "schema": 1,
        "profile": audit.PROFILE,
        "arm": "frame",
        "complete": True,
        "fatal": None,
        "artifacts": dict(IDENTITY),
        "requests": [{"generation": 4, "at": 1, "requestId": 8,
                      "operation": "open", "payload": {"url": "fixture.odt"}}],
        "responses": [{"generation": 4, "at": 2, "message": {"requestId": 8,
                       "ok": True, "result": {"documentHandle": 21}}}],
        "events": [{"generation": 4, "at": 2.5, "message": {"event": "editor-state",
                     "documentHandle": 21,
                     "a11y": {"unavailable": audit.A11Y_UNAVAILABLE}}}],
    }


class ObservationAuditTests(unittest.TestCase):
    def result(self, page):
        return audit.audit_page(page, IDENTITY, "unit-page")

    def assert_red(self, page, code):
        result = self.result(page)
        self.assertIn(code, {item["code"] for item in result["problems"]}, result)

    def test_same_generation_handle_state_event_passes(self):
        self.assertEqual([], self.result(valid_page())["problems"])

    def test_state_event_between_open_request_and_response_passes(self):
        page = valid_page()
        page["events"][0]["at"] = 1.5
        self.assertEqual([], self.result(page)["problems"])

    def test_nested_message_request_shape_passes(self):
        page = valid_page()
        req = page["requests"][0]
        req["message"] = {"operation": req.pop("operation"),
                           "requestId": req.pop("requestId"),
                           "payload": req.pop("payload")}
        self.assertEqual([], self.result(page)["problems"])

    def test_missing_state_witness_red(self):
        page = valid_page()
        page["events"] = []
        self.assert_red(page, "state-witness-missing")

    def test_cross_generation_state_red(self):
        page = valid_page()
        page["events"][0]["generation"] = 5
        self.assert_red(page, "state-wrong-generation")

    def test_wrong_document_handle_red(self):
        page = valid_page()
        page["events"][0]["message"]["documentHandle"] = 22
        self.assert_red(page, "state-wrong-handle")

    def test_wrong_a11y_status_red(self):
        page = valid_page()
        page["events"][0]["message"]["a11y"]["unavailable"] = "unknown"
        self.assert_red(page, "a11y-status")

    def test_failed_open_reply_red(self):
        page = valid_page()
        page["responses"][0]["message"]["ok"] = False
        self.assert_red(page, "open-response")

    def test_artifact_hash_mutation_red(self):
        page = valid_page()
        page["artifacts"]["sdk-worker.js"] = "wrong"
        self.assert_red(page, "artifact-identity")

    def test_ordinary_proof_event_red(self):
        page = valid_page()
        page["events"].append({"generation": 4, "at": 3, "message": {
            "event": "diagnostic", "detail": {"type": "v23-proof-absent",
            "requestId": 9, "count": 1, "callback": "UNO_COMMAND_RESULT"}}})
        self.assert_red(page, "ordinary-proof-event")

    def test_proof_arm_requires_actual_kind_two_request_and_attributed_event(self):
        page = valid_page()
        page["arm"] = "proof"
        page["requests"].append({"generation": 4, "at": 3, "requestId": 9,
                                 "operation": "v23Diagnostic", "payload": {"kind": 2}})
        page["events"].append({"generation": 4, "at": 4, "message": {
            "event": "diagnostic", "detail": {"type": "v23-proof-absent",
            "requestId": 9, "count": 1, "callback": "UNO_COMMAND_RESULT"}}})
        self.assertEqual([], self.result(page)["problems"])
        page["events"][-1]["message"]["detail"]["requestId"] = 10
        self.assert_red(page, "proof-attribution")

    def test_unknown_schema_unclean_and_no_open_red(self):
        page = valid_page()
        page["schema"] = 999
        page["complete"] = False
        page["requests"] = []
        result = self.result(page)
        codes = {item["code"] for item in result["problems"]}
        self.assertTrue({"unknown-schema", "unclean-page", "no-open"} <= codes)

    def test_sinit_cell_sha_and_missing_r2_page_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cell = {"profile": audit.PROFILE, "fatal": None}
            raw = json.dumps(cell).encode()
            (base / "cell.json").write_bytes(raw)
            report = {"runs": [{"path": "cell.json", "sha256": hashlib.sha256(raw).hexdigest()}]}
            (base / "report.json").write_text(json.dumps(report))
            result = audit.audit_reports([base / "report.json"], IDENTITY)
            self.assertEqual("FAIL", result["verdict"])
            self.assertIn("r2-cell-page-missing", {p["code"] for p in result["problems"]})
            report["runs"][0]["sha256"] = "0" * 64
            (base / "report.json").write_text(json.dumps(report))
            result = audit.audit_reports([base / "report.json"], IDENTITY)
            self.assertIn("cell-sha256", {p["code"] for p in result["problems"]})

    def test_v22_is_skipped_only_inside_sinit_index(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            raw = json.dumps({"page": {"profile": audit.V22_PROFILE}}).encode()
            (base / "cell.json").write_bytes(raw)
            (base / "report.json").write_text(json.dumps({"runs": [
                {"path": "cell.json", "sha256": hashlib.sha256(raw).hexdigest()}]}))
            result = audit.audit_reports([base / "report.json"], IDENTITY)
            self.assertEqual("FAIL", result["verdict"])
            self.assertEqual(1, result["counts"]["skippedV22SinitCells"])
            self.assertIn("zero-r2-pages", {p["code"] for p in result["problems"]})


if __name__ == "__main__":
    unittest.main()

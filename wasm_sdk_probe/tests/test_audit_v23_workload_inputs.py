#!/usr/bin/env python3
"""Causal-red tests for literal timing workload input verification."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location(
    "audit_v23_workload_inputs", TOOLS / "audit_v23_workload_inputs.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
from create_long_document import build


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class WorkloadInputAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.mirror = self.root / "mirror"
        self.mirror.mkdir()
        self.long_bytes = build(60)
        (self.mirror / "long60.odt").write_bytes(self.long_bytes)
        self.text = ("a" * audit.MARKDOWN_BYTES)
        self.page = {
            "complete": True,
            "arm": "workload",
            "markdown": {"bytes": len(self.text.encode()), "sha256": sha(self.text.encode())},
            "requests": [{"operation": "pasteMarkdown", "payload": {
                "text": self.text, "textUtf8Bytes": len(self.text.encode())}}],
            "fixtures": {"long60": {"bytes": len(self.long_bytes), "sha256": sha(self.long_bytes)}},
        }
        self.report = {
            "schema": 1,
            "profile": "e2-editor-v23-diag-r2",
            "fixtures": {"long60": sha(self.long_bytes)},
            "runs": [{"browser": "chrome", "round": 1, "arm": "workload", "page": self.page}],
        }
        self.path = self.root / "report.json"
        self.write_report()

    def tearDown(self):
        self.temp.cleanup()

    def write_report(self):
        self.path.write_text(json.dumps(self.report))

    def codes(self):
        self.write_report()
        return {problem["code"] for problem in audit.audit_reports([self.path])["problems"]}

    def test_literal_64k_and_actual_60_page_package_pass(self):
        result = audit.audit_reports([self.path])
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual(1, result["pageCount"])
        self.assertEqual([], result["problems"])
        member_rows = result["reports"][0]["pages"][0]["long60"]["members"]
        self.assertTrue(all(row["matches"] for row in member_rows))

    def test_coherently_relabelled_short_paste_is_rejected(self):
        text = "short but coherently relabelled"
        raw = text.encode("utf-8")
        payload = self.page["requests"][0]["payload"]
        payload["text"] = text
        payload["textUtf8Bytes"] = len(raw)
        self.page["markdown"] = {"bytes": len(raw), "sha256": sha(raw)}
        self.assertIn("paste-literal-size", self.codes())

    def test_payload_must_match_page_markdown_hash(self):
        self.page["requests"][0]["payload"]["text"] = "different bytes"
        self.page["requests"][0]["payload"]["textUtf8Bytes"] = len(b"different bytes")
        self.assertIn("paste-markdown-binding", self.codes())

    def test_payload_byte_count_cannot_be_mislabeled(self):
        self.page["requests"][0]["payload"]["textUtf8Bytes"] -= 1
        self.assertIn("paste-recorded-size", self.codes())

    def test_six_page_package_with_coherently_updated_hashes_is_rejected(self):
        short_bytes = build(6)
        (self.mirror / "long60.odt").write_bytes(short_bytes)
        digest = sha(short_bytes)
        self.report["fixtures"]["long60"] = digest
        self.page["fixtures"]["long60"] = {"bytes": len(short_bytes), "sha256": digest}
        self.assertIn("long60-package-members", self.codes())

    def test_zip_metadata_changes_do_not_change_member_identity(self):
        source = zipfile.ZipFile(io.BytesIO(self.long_bytes))
        rewritten = io.BytesIO()
        with zipfile.ZipFile(rewritten, "w", zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 2, 3, 4, 6))
                target.writestr(info, source.read(name), compress_type=zipfile.ZIP_DEFLATED)
        rewritten_bytes = rewritten.getvalue()
        (self.mirror / "long60.odt").write_bytes(rewritten_bytes)
        digest = sha(rewritten_bytes)
        self.report["fixtures"]["long60"] = digest
        self.page["fixtures"]["long60"] = {"bytes": len(rewritten_bytes), "sha256": digest}
        self.write_report()
        self.assertEqual("PASS", audit.audit_reports([self.path])["verdict"])

    def test_extra_package_member_is_rejected(self):
        rewritten = io.BytesIO()
        with zipfile.ZipFile(rewritten, "w") as target:
            with zipfile.ZipFile(io.BytesIO(self.long_bytes)) as source:
                for name in source.namelist():
                    target.writestr(name, source.read(name))
            target.writestr("extra.xml", b"unexpected")
        raw = rewritten.getvalue()
        (self.mirror / "long60.odt").write_bytes(raw)
        digest = sha(raw)
        self.report["fixtures"]["long60"] = digest
        self.page["fixtures"]["long60"] = {"bytes": len(raw), "sha256": digest}
        self.assertIn("long60-package-members", self.codes())

    def test_empty_or_nonworkload_reports_are_rejected(self):
        self.report["runs"] = [{"browser": "chrome", "round": 1, "arm": "smoke", "page": {}}]
        self.assertIn("workload-pages-missing", self.codes())


if __name__ == "__main__":
    unittest.main()

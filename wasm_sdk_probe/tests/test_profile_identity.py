"""X1's checker (`tools/check_profile_identity.py`), offline, before the v19 link.

The green case is SYNTHETIC: v18's profile copied into a temporary `e2-editor-v19` directory with a stand-in
probe.wasm / probe.js (a few bytes) and the manifest's name, version and two link hashes rewritten to match.
The red cases change one thing each; one is real (v16 against v18: another CJK and base pack).

    python3 -m unittest tests.test_profile_identity
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_profile_identity as x  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
V18 = HERE / "dist/profiles/e2-editor-v18"
V16 = HERE / "dist/profiles/e2-editor-v16"
EXPORTS = HERE / "build/archive/e2-editor-v15-ad3f68bb-worker-00882139/exports.txt"


@unittest.skipUnless(V18.is_dir() and V16.is_dir() and EXPORTS.is_file(), "v16/v18 profiles or v15 archive absent")
class ProfileIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="x1-"))
        self.v19 = self.tmp / "e2-editor-v19"
        self.v19.mkdir()
        shutil.copy(V18 / "sdk-worker.js", self.v19)
        (self.v19 / "probe.wasm").write_bytes(b"\0asm stand-in for a new link")
        (self.v19 / "probe.js").write_bytes(b"// stand-in loader")
        manifest = json.loads((V18 / "sdk-manifest.json").read_text())
        manifest["profile"] = "e2-editor-v19"
        manifest["sdkVersion"] = manifest["sdkVersion"].replace("e2-editor-v18", "e2-editor-v19")
        manifest["editorContract"]["wasmSha256"] = self.sha("probe.wasm")
        manifest["editorContract"]["loaderSha256"] = self.sha("probe.js")
        self.write(manifest)
        self.exports = self.tmp / "exports.txt"
        shutil.copy(EXPORTS, self.exports)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def sha(self, name):
        return hashlib.sha256((self.v19 / name).read_bytes()).hexdigest()

    def write(self, manifest):
        (self.v19 / "sdk-manifest.json").write_text(json.dumps(manifest, indent=1))

    def manifest(self):
        return json.loads((self.v19 / "sdk-manifest.json").read_text())

    def run_check(self, candidate=None):
        return x.check(candidate or self.v19, V18, self.exports, EXPORTS)

    def test_green(self):
        code, lines = self.run_check()
        self.assertEqual((code, lines[-1]), (0, "VERDICT PASS"), "\n".join(lines))
        self.assertIn("differs (recorded, 32.1)", "\n".join(lines))

    def test_red_v16_against_v18(self):
        code, lines = x.check(V16, V18, EXPORTS, EXPORTS)
        self.assertEqual(code, 1)
        self.assertIn("manifest", lines[-1])
        self.assertIn("wasm", lines[-1])          # v16 and v18 share v15's wasm: not a new link

    def test_red_the_same_wasm(self):
        (self.v19 / "probe.wasm").unlink()
        (self.v19 / "probe.wasm").symlink_to(V18 / "probe.wasm")
        manifest = self.manifest()
        manifest["editorContract"]["wasmSha256"] = self.sha("probe.wasm")
        self.write(manifest)
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['wasm']")

    def test_red_a_manifest_hash_that_is_not_the_file(self):
        manifest = self.manifest()
        manifest["editorContract"]["loaderSha256"] = "0" * 64
        self.write(manifest)
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['loader']")

    def test_red_one_worker_byte(self):
        worker = self.v19 / "sdk-worker.js"
        worker.write_bytes(worker.read_bytes() + b"\n")
        manifest = self.manifest()
        manifest["editorContract"]["workerSha256"] = self.sha("sdk-worker.js")
        self.write(manifest)
        code, lines = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("worker", lines[-1])

    def test_red_another_pack(self):
        manifest = self.manifest()
        manifest["resourcePacks"][1]["sha256"] = "0" * 64
        self.write(manifest)
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['manifest']")

    def test_red_a_new_field(self):
        manifest = self.manifest()
        manifest["editorContract"]["pollMs"] = 15
        self.write(manifest)
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['manifest']")

    def test_red_a_withheld_action_opened(self):
        # Review 2026-10-08 (codex B6): `select-all` is withheld as `gestures: []`; without the key the worker
        # never sends its mask and the engine leaves it fully permitted.
        manifest = self.manifest()
        self.assertEqual(manifest["editorContract"]["actions"]["select-all"]["gestures"], [])
        for change in (lambda a: a.pop("gestures"), lambda a: a.update(gestures={})):
            with self.subTest():
                manifest = self.manifest()
                change(manifest["editorContract"]["actions"]["select-all"])
                self.write(manifest)
                self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['manifest']")

    def test_red_the_old_name(self):
        manifest = self.manifest()
        manifest["sdkVersion"] = json.loads((V18 / "sdk-manifest.json").read_text())["sdkVersion"]
        self.write(manifest)
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['profile']")

    def test_red_another_export_list(self):
        self.exports.write_text(self.exports.read_text() + "_oxsdk_extra\n")
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['exports']")

    def test_red_an_extra_file(self):
        (self.v19 / "probe.wasm.map").write_text("{}")
        self.assertEqual(self.run_check()[1][-1], "VERDICT FAIL: ['files']")

    def test_a_missing_file_is_not_done(self):
        (self.v19 / "probe.js").unlink()
        self.assertEqual(self.run_check()[0], 3)


if __name__ == "__main__":
    unittest.main()

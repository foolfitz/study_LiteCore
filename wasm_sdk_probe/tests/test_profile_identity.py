"""X1's checker (`tools/check_profile_identity.py`), offline, before the v19 link.

The green case is SYNTHETIC: v18's profile copied into a temporary `e2-editor-v19` directory with a stand-in
probe.wasm / probe.js (a few bytes) and the manifest's name, version and two link hashes rewritten to match.
The red cases change one thing each; one is real (v16 against v18: another CJK and base pack).

`DeclaredDeltas` is the v20 use (ruling 6 condition 49): a SYNTHETIC e2-editor-v20 (v18's directory, a stand-in worker
that differs from v18's, a stand-in wasm and loader, the manifest leaf `.editorContract.pageRectangles`, the export
list plus `_oxsdk_document_page_rectangles`), judged with the three declared deltas -- one green and the seven red
cases of condition 49 (d), plus a few more.  With no flags the existing class above is the byte-identical-behaviour
test; the real one is findings/evidence/link-batch/v20-part3/x1/default-identity-vs-v19-post-link.diff.

    python3 -m unittest tests.test_profile_identity
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
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


LEAF = ".editorContract.pageRectangles"
LEAF_VALUE = "document-sdk-page-rectangles"
EXPORT = "_oxsdk_document_page_rectangles"


@unittest.skipUnless(V18.is_dir() and EXPORTS.is_file(), "v18 profile or v15 archive absent")
class DeclaredDeltas(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="x1-v20-"))
        self.v20 = self.tmp / "e2-editor-v20"
        self.v20.mkdir()
        (self.v20 / "sdk-worker.js").write_bytes((V18 / "sdk-worker.js").read_bytes() + b"\n// v20 stand-in\n")
        (self.v20 / "probe.wasm").write_bytes(b"\0asm stand-in for a new link")
        (self.v20 / "probe.js").write_bytes(b"// stand-in loader")
        manifest = json.loads((V18 / "sdk-manifest.json").read_text())
        manifest["profile"] = "e2-editor-v20"
        manifest["sdkVersion"] = manifest["sdkVersion"].replace("e2-editor-v18", "e2-editor-v20")
        manifest["editorContract"]["wasmSha256"] = self.sha("probe.wasm")
        manifest["editorContract"]["loaderSha256"] = self.sha("probe.js")
        manifest["editorContract"]["workerSha256"] = self.sha("sdk-worker.js")
        manifest["editorContract"]["pageRectangles"] = LEAF_VALUE
        self.write(manifest)
        self.exports = self.tmp / "exports.txt"
        self.exports.write_bytes(EXPORTS.read_bytes() + f"{EXPORT}\n".encode())
        self.worker = self.sha("sdk-worker.js")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def sha(self, name):
        return hashlib.sha256((self.v20 / name).read_bytes()).hexdigest()

    def write(self, manifest):
        (self.v20 / "sdk-manifest.json").write_text(json.dumps(manifest, indent=1))

    def manifest(self):
        return json.loads((self.v20 / "sdk-manifest.json").read_text())

    def run_check(self, worker=None, leaves=((LEAF, LEAF_VALUE),), exports=(EXPORT,)):
        return x.check(self.v20, V18, self.exports, EXPORTS,
                       (self.worker,) if worker is None else (worker,) if worker else (),
                       tuple(leaves), tuple(exports))

    def verdict(self, **kwargs):
        return self.run_check(**kwargs)[1][-1]

    def test_green_three_declared_deltas(self):
        code, lines = self.run_check()
        self.assertEqual((code, lines[-1]), (0, "VERDICT PASS"), "\n".join(lines))
        self.assertIn("declared leaf .editorContract.pageRectangles", "\n".join(lines))

    def test_the_same_candidate_with_no_flags_is_red_by_design(self):
        code, lines = x.check(self.v20, V18, self.exports, EXPORTS)
        self.assertEqual(code, 1)
        self.assertEqual(lines[-1], "VERDICT FAIL: ['manifest', 'worker', 'exports']")
        self.assertIn(f"['{LEAF}', '.editorContract.workerSha256']", lines[1])

    # condition 49 (d), the seven red cases
    def test_red_1_an_undeclared_fourth_leaf(self):
        manifest = self.manifest()
        manifest["editorContract"]["pollMs"] = 15
        self.write(manifest)
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['manifest']")

    def test_red_2_declared_worker_is_not_the_actual_one(self):
        self.assertEqual(self.verdict(worker="0" * 64), "VERDICT FAIL: ['worker']")

    def test_red_3_declared_worker_is_the_references_and_the_candidate_kept_it(self):
        ref_worker = hashlib.sha256((V18 / "sdk-worker.js").read_bytes()).hexdigest()
        shutil.copy(V18 / "sdk-worker.js", self.v20 / "sdk-worker.js")
        manifest = self.manifest()
        manifest["editorContract"]["workerSha256"] = ref_worker
        self.write(manifest)
        self.assertEqual(self.verdict(worker=ref_worker), "VERDICT FAIL: ['worker']")

    def test_red_4_declared_leaf_already_in_the_reference(self):
        reference = dict(x.leaves(json.loads((V18 / "sdk-manifest.json").read_text())))
        path = ".editorContract.abiVersion"
        self.assertIn(path, reference)
        self.assertEqual(self.verdict(leaves=((LEAF, LEAF_VALUE), (path, reference[path]))),
                         "VERDICT FAIL: ['declared-leaf']")

    def test_red_5_declared_leaf_with_another_value(self):
        self.assertEqual(self.verdict(leaves=((LEAF, "something-else"),)), "VERDICT FAIL: ['declared-leaf']")

    def test_red_6_an_undeclared_export(self):
        self.exports.write_bytes(self.exports.read_bytes() + b"_oxsdk_extra\n")
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['exports']")

    def test_red_7_a_declared_export_that_is_absent(self):
        self.exports.write_bytes(EXPORTS.read_bytes())
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['exports']")

    # more reds that follow from "each declared delta moved exactly as declared"
    def test_red_a_declared_leaf_the_candidate_does_not_have(self):
        manifest = self.manifest()
        del manifest["editorContract"]["pageRectangles"]
        self.write(manifest)
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['declared-leaf']")

    def test_red_a_declared_export_that_was_already_in_the_reference(self):
        symbol = EXPORTS.read_text().splitlines()[0]
        self.exports.write_bytes(EXPORTS.read_bytes() + f"{symbol}\n".encode())
        self.assertEqual(self.verdict(exports=(symbol,)), "VERDICT FAIL: ['exports']")

    def test_red_exports_appended_in_another_order(self):
        self.exports.write_bytes(EXPORTS.read_bytes() + f"_b\n{EXPORT}\n".encode())
        self.assertEqual(self.verdict(exports=(EXPORT, "_b")), "VERDICT FAIL: ['exports']")
        self.assertEqual(self.verdict(exports=("_b", EXPORT)), "VERDICT PASS")

    def test_red_a_new_worker_without_declaring_it(self):
        code, lines = self.run_check(worker="")
        self.assertEqual(lines[-1], "VERDICT FAIL: ['manifest', 'worker']")

    def test_red_the_manifest_worker_hash_is_not_the_worker(self):
        manifest = self.manifest()
        manifest["editorContract"]["workerSha256"] = "0" * 64
        self.write(manifest)
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['worker']")

    def test_red_a_declared_leaf_of_another_json_type(self):
        manifest = self.manifest()
        manifest["editorContract"]["pageRectangles"] = 1
        self.write(manifest)
        self.assertEqual(self.verdict(leaves=((LEAF, True),)), "VERDICT FAIL: ['declared-leaf']")
        self.assertEqual(self.verdict(leaves=((LEAF, 1),)), "VERDICT PASS")

    def test_the_other_clauses_still_run_under_declared_deltas(self):
        (self.v20 / "probe.wasm.map").write_text("{}")
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['files']")

    def test_flag_parsing(self):
        self.assertEqual(x.parse_leaf(f"{LEAF}={LEAF_VALUE}"), (LEAF, LEAF_VALUE))
        self.assertEqual(x.parse_leaf(".a=true"), (".a", True))
        self.assertEqual(x.parse_leaf('.a="123"'), (".a", "123"))
        for bad in ("a=1", ".a", ".a="):
            with self.assertRaises(SystemExit):
                x.parse_leaf(bad)

    def test_the_command_line(self):
        base = [sys.executable, str(HERE / "tools/check_profile_identity.py"), "--candidate", str(self.v20),
                "--reference", str(V18), "--candidate-exports", str(self.exports),
                "--reference-exports", str(EXPORTS)]
        flags = ["--declared-worker", self.worker, "--declared-new-leaf", f"{LEAF}={LEAF_VALUE}",
                 "--declared-export", EXPORT]
        green = subprocess.run(base + flags, capture_output=True, text=True)
        self.assertEqual((green.returncode, green.stdout.splitlines()[-1]), (0, "VERDICT PASS"), green.stdout)
        red = subprocess.run(base + flags[:-2], capture_output=True, text=True)
        self.assertEqual((red.returncode, red.stdout.splitlines()[-1]), (1, "VERDICT FAIL: ['exports']"))
        none = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(none.returncode, 1)


V20 = HERE / "dist/profiles/e2-editor-v20"
V20_EXPORTS = HERE / "build/archive/e2-editor-v20-313b08d5-worker-478d0da1/exports.txt"
ABI = ".editorContract.abiVersion"
PASTE_LEAF = ".editorContract.pasteMarkdown"
PASTE_VALUE = "document-sdk-paste-markdown"
PASTE_EXPORT = "_oxsdk_document_paste_markdown"
NEW_ACTIONS = {"move-document-start": 22, "move-document-end": 23}


@unittest.skipUnless(V20.is_dir() and V20_EXPORTS.is_file(), "v20 profile or v20 archive absent")
class DeclaredChangedLeaf(unittest.TestCase):
    """SPEC-M3-link-batch-v21 11.3 X1-cl: `--declared-changed-leaf PATH OLD NEW`, and the I1 shape it exists for.

    A SYNTHETIC e2-editor-v21 from the real v20 profile: a stand-in wasm, loader and worker, `abiVersion` 4 -> 5,
    the two new actions (six new leaves), `pasteMarkdown`, and the v20 export list plus the paste export.  Green
    with every delta declared; the six red cases of X1-cl each change one thing."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="x1-v21-"))
        self.v21 = self.tmp / "e2-editor-v21"
        self.v21.mkdir()
        (self.v21 / "sdk-worker.js").write_bytes((V20 / "sdk-worker.js").read_bytes() + b"\n// v21 stand-in\n")
        (self.v21 / "probe.wasm").write_bytes(b"\0asm stand-in for the v21 link")
        (self.v21 / "probe.js").write_bytes(b"// stand-in loader")
        manifest = json.loads((V20 / "sdk-manifest.json").read_text())
        manifest["profile"] = "e2-editor-v21"
        manifest["sdkVersion"] = manifest["sdkVersion"].replace("e2-editor-v20", "e2-editor-v21")
        contract = manifest["editorContract"]
        contract["wasmSha256"] = self.sha("probe.wasm")
        contract["loaderSha256"] = self.sha("probe.js")
        contract["workerSha256"] = self.sha("sdk-worker.js")
        contract["abiVersion"] = 5
        for name, wire in NEW_ACTIONS.items():
            contract["actions"][name] = {"id": wire, "gestures": ["collapsed"], "limits": ["no-extend-selection"]}
        contract["pasteMarkdown"] = PASTE_VALUE
        self.write(manifest)
        self.exports = self.tmp / "exports.txt"
        self.exports.write_bytes(V20_EXPORTS.read_bytes() + f"{PASTE_EXPORT}\n".encode())
        self.worker = self.sha("sdk-worker.js")
        self.new_leaves = [(PASTE_LEAF, PASTE_VALUE)]
        for name, wire in NEW_ACTIONS.items():
            self.new_leaves += [(f".editorContract.actions.{name}.id", wire),
                                (f".editorContract.actions.{name}.gestures[0]", "collapsed"),
                                (f".editorContract.actions.{name}.limits[0]", "no-extend-selection")]

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def sha(self, name):
        return hashlib.sha256((self.v21 / name).read_bytes()).hexdigest()

    def write(self, manifest):
        (self.v21 / "sdk-manifest.json").write_text(json.dumps(manifest, indent=1))

    def manifest(self):
        return json.loads((self.v21 / "sdk-manifest.json").read_text())

    def run_check(self, changes=((ABI, 4, 5),)):
        return x.check(self.v21, V20, self.exports, V20_EXPORTS, (self.worker,), tuple(self.new_leaves),
                       (PASTE_EXPORT,), tuple(changes))

    def verdict(self, **kwargs):
        return self.run_check(**kwargs)[1][-1]

    def test_green_every_delta_declared(self):
        code, lines = self.run_check()
        self.assertEqual((code, lines[-1]), (0, "VERDICT PASS"), "\n".join(lines))
        self.assertIn("declared changed leaf .editorContract.abiVersion: 4 -> 5: reference has 4, candidate 5",
                      "\n".join(lines))
        self.assertIn("declared-changed-leaf: ok", lines)

    # X1-cl, the six red cases
    def test_red_1_an_undeclared_change(self):
        self.assertEqual(self.verdict(changes=()), "VERDICT FAIL: ['manifest']")

    def test_red_2_declared_but_not_changed(self):
        manifest = self.manifest()
        manifest["editorContract"]["abiVersion"] = 4
        self.write(manifest)
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['declared-changed-leaf']")
        # Declaring OLD == NEW is the same claim and is refused the same way.
        self.assertEqual(self.verdict(changes=((ABI, 4, 4),)), "VERDICT FAIL: ['declared-changed-leaf']")

    def test_red_3_old_wrong(self):
        self.assertEqual(self.verdict(changes=((ABI, 3, 5),)), "VERDICT FAIL: ['declared-changed-leaf']")

    def test_red_4_new_wrong(self):
        self.assertEqual(self.verdict(changes=((ABI, 4, 6),)), "VERDICT FAIL: ['declared-changed-leaf']")

    def test_red_5_a_leaf_that_does_not_exist(self):
        code, lines = self.run_check(changes=((ABI, 4, 5), (".editorContract.noSuchLeaf", 4, 5)))
        self.assertEqual(lines[-1], "VERDICT FAIL: ['declared-changed-leaf']")
        # Present only in the candidate is a NEW leaf, not a changed one.
        self.assertEqual(self.verdict(changes=((ABI, 4, 5), (PASTE_LEAF, "x", PASTE_VALUE))),
                         "VERDICT FAIL: ['declared-changed-leaf']")

    def test_red_6_a_value_of_another_json_type(self):
        self.assertEqual(self.verdict(changes=((ABI, "4", 5),)), "VERDICT FAIL: ['declared-changed-leaf']")
        self.assertEqual(self.verdict(changes=((ABI, 4, "5"),)), "VERDICT FAIL: ['declared-changed-leaf']")
        self.assertEqual(self.verdict(changes=((ABI, 4, 5.0),)), "VERDICT FAIL: ['declared-changed-leaf']")

    # what else the I1 shape must still catch
    def test_red_one_new_action_leaf_undeclared(self):
        self.new_leaves = [leaf for leaf in self.new_leaves if not leaf[0].endswith("move-document-end.limits[0]")]
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['manifest']")

    def test_red_an_inherited_action_changed_beside_the_declared_ones(self):
        manifest = self.manifest()
        manifest["editorContract"]["actions"]["select-all"]["gestures"] = ["collapsed"]
        self.write(manifest)
        self.assertEqual(self.verdict(), "VERDICT FAIL: ['manifest']")

    def test_flag_parsing(self):
        self.assertEqual(x.parse_change([ABI, "4", "5"]), (ABI, 4, 5))
        self.assertEqual(x.parse_change([".a", '"4"', "x->y"]), (".a", "4", "x->y"))
        for bad in (["a", "4", "5"], [".a", "", "5"], [".a", "4", ""]):
            with self.assertRaises(SystemExit):
                x.parse_change(bad)

    def test_the_command_line(self):
        base = [sys.executable, str(HERE / "tools/check_profile_identity.py"), "--candidate", str(self.v21),
                "--reference", str(V20), "--candidate-exports", str(self.exports),
                "--reference-exports", str(V20_EXPORTS), "--declared-worker", self.worker,
                "--declared-export", PASTE_EXPORT]
        for path, value in self.new_leaves:
            base += ["--declared-new-leaf", f"{path}={value}"]
        green = subprocess.run(base + ["--declared-changed-leaf", ABI, "4", "5"], capture_output=True, text=True)
        self.assertEqual((green.returncode, green.stdout.splitlines()[-1]), (0, "VERDICT PASS"), green.stdout)
        red = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual((red.returncode, red.stdout.splitlines()[-1]), (1, "VERDICT FAIL: ['manifest']"))


if __name__ == "__main__":
    unittest.main()

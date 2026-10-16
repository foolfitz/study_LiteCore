"""What the ABI-5 builder (link batch v21) claims, checked.

SPEC-M3-link-batch-v21 4.1, 4.2, 9.10: ids 1-21 inherited verbatim, 22 and 23
appended as caret moves, `pasteMarkdown` declared only when told and only for
an artifact that exports the symbol, and the v4 builder left exactly as it was
-- in its bytes (finding 042) and in the process that imported both.
"""

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_e2_b_profile as v2  # noqa: E402
import build_e2_editor_v4_profile as v4  # noqa: E402
import build_e2_editor_v5_profile as v5  # noqa: E402

PRODUCT = ("_oxsdk_editor_action", "_oxsdk_editor_get_state",
           "_oxsdk_editor_select_range", "_oxsdk_editor_place_caret",
           "_oxsdk_editor_abi_version", "_oxsdk_editor_set_action_gestures",
           "_oxsdk_document_redo")


class Inputs:
    """A packaging run on stand-in bytes: v2.build_profile copies the loader,
    the wasm and the worker and hashes them, so their content is irrelevant
    here.  The source manifest is the real one the v19/v20 rules use."""

    def __init__(self, case: unittest.TestCase, *symbols: str):
        self.dir = Path(tempfile.mkdtemp(prefix="v5-builder-"))
        case.addCleanup(shutil.rmtree, self.dir, True)
        for name, data in (("probe.js", b"loader"), ("probe.wasm", b"\0asm"),
                           ("sdk-worker.js", b"worker")):
            (self.dir / name).write_bytes(data)
        self.exports = self.dir / "exports.txt"
        self.exports.write_text("\n".join(symbols) + "\n", encoding="utf-8")

    def argv(self, output: str, *extra: str, profile: str = "e2-editor-v21"):
        args = ["builder",
                "--source-manifest", str(ROOT / "sdk/v18-writer-review-manifest.json"),
                "--loader", str(self.dir / "probe.js"),
                "--wasm", str(self.dir / "probe.wasm"),
                "--worker", str(self.dir / "sdk-worker.js"),
                "--exports", str(self.exports),
                "--output", str(self.dir / output),
                "--inline-range-gestures", "all", "--page-rectangles", *extra]
        if profile is not None:
            args += ["--profile", profile]
        return args

    def manifest(self, output: str) -> dict:
        return json.loads((self.dir / output / "sdk-manifest.json")
                          .read_text(encoding="utf-8"))


def run_v5(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = v5.main(argv)
    return code, out.getvalue()


def run_v4(argv):
    saved = sys.argv
    sys.argv = argv
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            return v4.main(), out.getvalue()
    finally:
        sys.argv = saved


class InheritedVerbatim(unittest.TestCase):

    def test_the_twenty_one_inherited_actions_keep_their_wire_ids(self):
        old = v4.action_map()
        new = v5.action_map()
        for name, spec in old.items():
            self.assertIn(name, new, f"v5 dropped inherited action {name}")
            self.assertEqual(new[name], spec, f"v5 changed {name}")

    def test_the_two_new_actions_are_22_and_23_caret_only(self):
        new = v5.action_map()
        self.assertEqual(sorted(spec["id"] for spec in new.values()),
                         list(range(1, 24)))
        self.assertEqual(new["move-document-start"],
                         {"id": 22, "gestures": [v2.COLLAPSED],
                          "limits": ["no-extend-selection"]})
        self.assertEqual(new["move-document-end"],
                         {"id": 23, "gestures": [v2.COLLAPSED],
                          "limits": ["no-extend-selection"]})

    def test_abi_version_is_five_and_v4_is_still_four(self):
        self.assertEqual(v5.ABI_VERSION, 5)
        self.assertEqual(v4.ABI_VERSION, 4)


class TheBuild(unittest.TestCase):
    """End to end on stand-in bytes, against v4's own output for the same
    inputs: the differences are exactly the declared ones (what I1's X1 run
    will be asked to see on the real artifacts)."""

    def test_v5_differs_from_v4_by_the_declared_leaves_only(self):
        inputs = Inputs(self, *PRODUCT, "_oxsdk_document_page_rectangles",
                        v5.PASTE_MARKDOWN_EXPORT)
        code, printed = run_v5(inputs.argv("v5", "--paste-markdown"))
        self.assertEqual(code, 0)
        code4, _ = run_v4(inputs.argv("v4"))
        self.assertEqual(code4, 0)
        new, old = inputs.manifest("v5"), inputs.manifest("v4")
        new_contract, old_contract = new.pop("editorContract"), old.pop("editorContract")
        self.assertEqual(new, old, "a difference outside editorContract")
        self.assertEqual(new_contract.pop("abiVersion"), 5)
        self.assertEqual(old_contract.pop("abiVersion"), 4)
        self.assertEqual(new_contract.pop("pasteMarkdown"),
                         "document-sdk-paste-markdown")
        new_actions, old_actions = new_contract.pop("actions"), old_contract.pop("actions")
        self.assertEqual(new_contract, old_contract,
                         "an undeclared difference inside editorContract")
        self.assertEqual({k: v for k, v in new_actions.items()
                          if k not in v5.NEW_ACTIONS}, old_actions)
        self.assertEqual(sorted(set(new_actions) - set(old_actions)),
                         ["move-document-end", "move-document-start"])
        # The digest printed is the final manifest's, not v4's intermediate one.
        summary = json.loads(printed)
        digest = hashlib.sha256((inputs.dir / "v5" / "sdk-manifest.json")
                                .read_bytes()).hexdigest()
        self.assertEqual(summary["manifestSha256"], digest)
        self.assertEqual(summary["abiVersion"], 5)
        self.assertEqual(summary["actions"], 23)
        self.assertEqual(summary["pasteMarkdown"], "document-sdk-paste-markdown")
        self.assertEqual(summary["withheld"], ["select-all"])

    def test_without_the_flag_nothing_is_declared(self):
        inputs = Inputs(self, *PRODUCT, "_oxsdk_document_page_rectangles",
                        v5.PASTE_MARKDOWN_EXPORT)
        code, printed = run_v5(inputs.argv("v5"))
        self.assertEqual(code, 0)
        self.assertNotIn("pasteMarkdown", inputs.manifest("v5")["editorContract"])
        self.assertIsNone(json.loads(printed)["pasteMarkdown"])

    def test_v4_is_restored_after_a_build_and_after_a_refusal(self):
        original = v4.action_map
        inputs = Inputs(self, *PRODUCT, "_oxsdk_document_page_rectangles",
                        v5.PASTE_MARKDOWN_EXPORT)
        run_v5(inputs.argv("v5", "--paste-markdown"))
        self.assertIs(v4.action_map, original)
        self.assertEqual(v4.ABI_VERSION, 4)
        # A refusal raised inside v4.main (its own page-rectangles guard).
        bare = Inputs(self, *PRODUCT, v5.PASTE_MARKDOWN_EXPORT)
        with self.assertRaises(SystemExit):
            run_v5(bare.argv("v5", "--paste-markdown"))
        self.assertIs(v4.action_map, original)
        self.assertEqual(v4.ABI_VERSION, 4)
        self.assertEqual(sorted(s["id"] for s in v4.action_map().values()),
                         list(range(1, 22)))


class PasteMarkdownIsToldNotGuessed(unittest.TestCase):
    """The refusal comes before anything is built: the stand-in output
    directory must not exist afterwards."""

    def test_refused_without_the_export(self):
        inputs = Inputs(self, *PRODUCT, "_oxsdk_document_page_rectangles")
        with self.assertRaises(SystemExit) as raised:
            run_v5(inputs.argv("v5", "--paste-markdown"))
        self.assertIn("refusing to declare pasteMarkdown", str(raised.exception))
        self.assertIn(v5.PASTE_MARKDOWN_EXPORT, str(raised.exception))
        self.assertFalse((inputs.dir / "v5").exists())

    def test_refused_without_an_inventory(self):
        self.assertEqual(len(v5.paste_markdown_problems(Path("no/such.txt"))), 1)
        self.assertEqual(len(v5.paste_markdown_problems(None)), 1)

    def test_the_declaration_is_the_string_the_gates_read(self):
        for relative in ("sdk/sdk-worker.js", "sdk/document-sdk.js",
                         "editor-shell-v2/narrow-editor-v2-client.js"):
            with self.subTest(relative):
                self.assertIn(f'"{v5.PASTE_MARKDOWN_DECLARATION}"',
                              (ROOT / relative).read_text(encoding="utf-8"))

    def test_the_export_is_the_c_function_sdk_api_defines(self):
        self.assertIn(f"int32_t {v5.PASTE_MARKDOWN_EXPORT.lstrip('_')}(",
                      (ROOT / "src/sdk_api.cpp").read_text(encoding="utf-8"))


class TheGuardsFireWhenTheyShould(unittest.TestCase):

    def test_no_profile_is_refused(self):
        inputs = Inputs(self, *PRODUCT, "_oxsdk_document_page_rectangles")
        with self.assertRaises(SystemExit) as raised:
            run_v5(inputs.argv("v5", profile=None))
        self.assertIn("--profile is required", str(raised.exception))

    def test_the_frozen_v4_name_is_refused(self):
        inputs = Inputs(self, *PRODUCT, "_oxsdk_document_page_rectangles")
        with self.assertRaises(SystemExit):
            run_v5(inputs.argv("v5", profile=v4.PROFILE))

    def test_renumbering_an_inherited_action_is_refused(self):
        saved = dict(v5.NEW_ACTIONS)
        try:
            v5.NEW_ACTIONS["move-document-end"] = {"id": 7, "gestures": [],
                                                   "limits": []}
            with self.assertRaises(SystemExit):
                v5.action_map()
            v5.NEW_ACTIONS.clear()
            v5.NEW_ACTIONS.update(saved)
            v5.NEW_ACTIONS["set-bold"] = {"id": 24, "gestures": [], "limits": []}
            with self.assertRaises(SystemExit):
                v5.action_map()
        finally:
            v5.NEW_ACTIONS.clear()
            v5.NEW_ACTIONS.update(saved)
        self.assertEqual(v5.action_map()["move-document-end"]["id"], 23)

    def test_a_gap_in_the_id_range_is_refused(self):
        saved = dict(v5.NEW_ACTIONS)
        try:
            v5.NEW_ACTIONS["move-document-end"] = {"id": 24, "gestures": [],
                                                   "limits": []}
            with self.assertRaises(SystemExit):
                v5.action_map()
        finally:
            v5.NEW_ACTIONS.clear()
            v5.NEW_ACTIONS.update(saved)


if __name__ == "__main__":
    unittest.main()

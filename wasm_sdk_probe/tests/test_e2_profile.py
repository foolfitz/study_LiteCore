#!/usr/bin/env python3
"""Static checks for the isolated E2 format discovery profile."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from build_e2_discovery_profile import (  # noqa: E402
    WORKER_BARRIER_BEFORE,
    WORKER_GATE_BEFORE,
    WORKER_MESSAGE_BEFORE,
    write_e2_worker,
)

# e1-editor-v1 was re-frozen on 2026-08-06: finding 022 (a silent no-op reachable
# in the shipped editor) was fixed in probe_engine.cpp, so the artifact had to be
# rebuilt.  The pre-fix hashes were 94b38437.../45c31f32... (sdk-worker.js is
# unchanged, the fix is engine-side).  Everything else here is untouched.
FROZEN = {
    "writer-review/probe.ba257beb038b6a2d.wasm":
        "ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6",
    "e1-editor-discovery/probe.wasm":
        "679def61e7848a6d678b6bcc2b4fad7acb37904cdcd0e615afb3405fb5afb634",
    "e1-editor-v1/probe.wasm":
        "835b453dd85adebbfcc6ada30fd47cdd7d5679a6abaaff3f1faebf47b484979d",
    "e1-editor-v1/probe.js":
        "1fe83aedcc6d57d80757abadb3d36e7e4d5c6c253bbe1c47d69a248e0cfc42de",
    "e1-editor-v1/sdk-worker.js":
        "e4f37ffe11963259f184c159b6c94a851eca5aa5bf8b8f72b38b17575029b761",
}


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestSharedWorkerUntouched(unittest.TestCase):
    """E2 must diverge on its own copy, never on the file others build from."""

    def test_shared_worker_has_no_e2_scope(self):
        text = (PROJECT / "sdk" / "sdk-worker.js").read_text(encoding="utf-8")
        self.assertNotIn("e2-paragraph-format-discovery", text)

    def test_patch_anchors_still_match_exactly_once(self):
        text = (PROJECT / "sdk" / "sdk-worker.js").read_text(encoding="utf-8")
        for name, anchor in (
            ("gate", WORKER_GATE_BEFORE),
            ("message", WORKER_MESSAGE_BEFORE),
            ("barrier", WORKER_BARRIER_BEFORE),
        ):
            with self.subTest(anchor=name):
                self.assertEqual(text.count(anchor), 1)

    def test_patch_fails_loudly_when_anchor_is_gone(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "worker.js"
            source.write_text("nothing to patch here\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                write_e2_worker(source, Path(directory) / "out.js")


class TestFrozenArtifacts(unittest.TestCase):
    """E2 discovery must not replace any artifact an earlier release validated."""

    def test_frozen_hashes(self):
        for relative, expected in FROZEN.items():
            path = PROJECT / "dist" / "profiles" / relative
            if not path.is_file():
                self.skipTest(f"{relative} not built in this workspace")
            with self.subTest(artifact=relative):
                self.assertEqual(sha256(path), expected)


class TestE2Profile(unittest.TestCase):
    def setUp(self):
        self.profile = PROJECT / "dist" / "profiles" / "e2-format-discovery"
        if not (self.profile / "sdk-manifest.json").is_file():
            self.skipTest("e2-format-discovery profile not built")
        self.manifest = json.loads((self.profile / "sdk-manifest.json").read_text(encoding="utf-8"))

    def test_scope_and_capability(self):
        self.assertEqual(self.manifest["diagnostic"]["scope"], "e2-paragraph-format-discovery")
        self.assertIn("verified-format-state", self.manifest["capabilities"])

    def test_result_verdict_fields_are_not_used_for_completion(self):
        diagnostic = self.manifest["diagnostic"]
        self.assertTrue(diagnostic["formatCompletionRequiresCommandResultAndState"])
        self.assertFalse(diagnostic["formatResultVerdictFieldsUsedForCompletion"])

    def test_no_raw_escape_hatch(self):
        diagnostic = self.manifest["diagnostic"]
        self.assertFalse(diagnostic["rawCallbackExposed"])
        self.assertFalse(diagnostic["arbitraryUnoCommandAccepted"])
        self.assertFalse(diagnostic["arbitraryKeyCodeAccepted"])
        self.assertFalse(diagnostic["automaticRetry"])
        self.assertFalse(diagnostic["productionArtifactReplaced"])

    def test_declared_hashes_match_files(self):
        diagnostic = self.manifest["diagnostic"]
        self.assertEqual(sha256(self.profile / "probe.wasm"), diagnostic["wasmSha256"])
        self.assertEqual(sha256(self.profile / "probe.js"), diagnostic["loaderSha256"])
        self.assertEqual(sha256(self.profile / "sdk-worker.js"), diagnostic["workerSha256"])

    def test_profile_worker_accepts_only_the_two_diagnostic_scopes(self):
        text = (self.profile / "sdk-worker.js").read_text(encoding="utf-8")
        self.assertIn("e2-paragraph-format-discovery", text)
        self.assertIn("e1-odt-editing-discovery", text)
        self.assertIn("result.formatBarrier = event.formatBarrier;", text)


def strip_js_comments(text: str) -> str:
    """Drop // and /* */ comments so code can be checked without prose."""
    import re

    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestSchedulerAttributionProfile(unittest.TestCase):
    """The attribution profile must stay separate from the A2 measurement one."""

    def setUp(self):
        self.profile = PROJECT / "dist" / "profiles" / "e2-scheduler-attribution"
        if not (self.profile / "sdk-manifest.json").is_file():
            self.skipTest("e2-scheduler-attribution profile not built")
        self.manifest = json.loads((self.profile / "sdk-manifest.json").read_text(encoding="utf-8"))

    def test_distinct_scope_and_drain_capability(self):
        self.assertEqual(self.manifest["diagnostic"]["scope"], "e2-scheduler-attribution")
        self.assertIn("finding-016-scheduler-probe", self.manifest["capabilities"])

    def test_does_not_replace_the_a2_profile(self):
        a2 = PROJECT / "dist" / "profiles" / "e2-format-discovery" / "sdk-manifest.json"
        if not a2.is_file():
            self.skipTest("e2-format-discovery profile not built")
        other = json.loads(a2.read_text(encoding="utf-8"))
        self.assertNotEqual(
            other["diagnostic"]["wasmSha256"], self.manifest["diagnostic"]["wasmSha256"]
        )
        self.assertNotIn("finding-016-scheduler-probe", other["capabilities"])


class TestMainLoopAttributionProfile(unittest.TestCase):
    """Finding 021 candidate 1: main-loop engine, and provably no unit pump."""

    def setUp(self):
        self.profile = PROJECT / "dist" / "profiles" / "e2-mainloop-attribution"
        if not (self.profile / "sdk-manifest.json").is_file():
            self.skipTest("e2-mainloop-attribution profile not built")
        self.manifest = json.loads((self.profile / "sdk-manifest.json").read_text(encoding="utf-8"))

    def test_scope_and_engine_loop(self):
        self.assertEqual(self.manifest["diagnostic"]["scope"], "e2-mainloop-attribution")
        self.assertEqual(self.manifest["diagnostic"]["engineLoop"], "lok-runloop-unipoll")
        self.assertIn("mainloop-engine", self.manifest["capabilities"])

    def test_no_drain_capability(self):
        # The point of this profile is that freshness needs no pump at all, so
        # the unit-test drain must not even be reachable.
        self.assertNotIn("finding-016-scheduler-probe", self.manifest["capabilities"])

    def test_other_profiles_keep_blocking_loop(self):
        for name in ("e2-format-discovery", "e2-scheduler-attribution"):
            other = PROJECT / "dist" / "profiles" / name / "sdk-manifest.json"
            if not other.is_file():
                continue
            manifest = json.loads(other.read_text(encoding="utf-8"))
            with self.subTest(profile=name):
                # None means the profile predates the field; both readings say
                # "not the main-loop engine", which is the invariant.
                self.assertIn(
                    manifest["diagnostic"].get("engineLoop"),
                    (None, "blocking-command-loop"),
                )

    def test_does_not_replace_the_other_e2_profiles(self):
        for name in ("e2-format-discovery", "e2-scheduler-attribution"):
            other = PROJECT / "dist" / "profiles" / name / "sdk-manifest.json"
            if not other.is_file():
                continue
            manifest = json.loads(other.read_text(encoding="utf-8"))
            with self.subTest(profile=name):
                self.assertNotEqual(
                    manifest["diagnostic"]["wasmSha256"],
                    self.manifest["diagnostic"]["wasmSha256"],
                )


class TestFormatDispatchForm(unittest.TestCase):
    """Finding 030: the bare command name is a toggle, not a setter.

    A closed set-list(...) enum that dispatches `.uno:DefaultBullet` with no
    arguments asks core for the opposite of whatever is there, so the second
    press undoes the first.  The explicit-mode parameter is what makes it a
    setter, and losing it again would be invisible at every other layer -- the
    action name, the manifest and the client code all stay identical.
    """

    @classmethod
    def setUpClass(cls):
        source = (PROJECT / "src" / "probe_engine.cpp").read_text(encoding="utf-8")
        start = source.index("void startFormatBarrierActionResolved(const Command &command,\n"
                             "                                      std::uint32_t action, "
                             "const char *name) {")
        cls.body = source[start:source.index("\n}\n", start)]
        cls.source = source

    def segment(self, action: str) -> str:
        start = self.body.index(f"case {action}:")
        return self.body[start:self.body.index("break;", start)]

    def test_list_actions_dispatch_the_explicit_mode_form(self):
        for action in ("OXSDK_EDITOR_SET_LIST_UNORDERED",
                       "OXSDK_EDITOR_SET_LIST_ORDERED"):
            with self.subTest(action=action):
                self.assertIn("barrier.arguments = kListOnArguments;",
                              self.segment(action))

    def test_the_explicit_mode_argument_says_on_true(self):
        # Measured against native 26.8, not assumed: svx/sdi/svx.sdi declares
        # `On` as FN_PARAM_1 and txtnum.cxx uses it as the mode when present.
        self.assertIn('const char *const kListOnArguments = "{\\"On\\":{\\"type\\":\\"boolean\\","\n'
                      '                                     "\\"value\\":true}}";',
                      self.source)

    def test_remove_bullets_is_dispatched_bare_on_purpose(self):
        # FN_NUM_BULLET_OFF forwards to FN_NUM_BULLET_ON with On=false and then
        # calls DelNumRules, so it is already a setter.  Pinned so that adding
        # arguments here becomes a deliberate change rather than a tidy-up.
        segment = self.segment("OXSDK_EDITOR_SET_LIST_NONE")
        self.assertIn('barrier.command = ".uno:RemoveBullets";', segment)
        self.assertNotIn("barrier.arguments =", segment)


class TestFormatDiscoveryClient(unittest.TestCase):
    def test_closed_action_list(self):
        text = (PROJECT / "e2" / "format-discovery-client.js").read_text(encoding="utf-8")
        for action in (
            "set-list-none",
            "set-list-unordered",
            "set-list-ordered",
            "set-paragraph-body",
            "set-paragraph-heading",
        ):
            self.assertIn(f'"{action}"', text)

    def test_no_uno_command_string_in_client_code(self):
        # The engine owns the command strings.  Comments may name them when
        # explaining why (finding 019); executable code may not carry them.
        for relative in ("e2/format-discovery-client.js", "web/e2-format-discovery-app.js"):
            with self.subTest(file=relative):
                code = strip_js_comments((PROJECT / relative).read_text(encoding="utf-8"))
                self.assertNotIn(".uno:", code)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Static checks for the isolated E2 format discovery profile."""

from __future__ import annotations

import json
import sys
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from build_e2_discovery_profile import (  # noqa: E402
    WORKER_BARRIER_BEFORE,
    WORKER_GATE_BEFORE,
    WORKER_LOK_TRACE_BEFORE,
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

    def test_lok_trace_anchor_still_matches_exactly_once(self):
        text = (PROJECT / "sdk" / "sdk-worker.js").read_text(encoding="utf-8")
        self.assertEqual(text.count(WORKER_LOK_TRACE_BEFORE), 1)

    def test_lok_trace_is_off_by_default_and_only_adds_forwarding(self):
        """Finding 037.

        The traced profile's whole value is that it measures the shipped
        artifact rather than a rebuilt one, which only holds if the trace is
        additive and opt-in.  A default that quietly forwarded the callback
        stream would change what every other profile reports.
        """
        import tempfile

        source = PROJECT / "sdk" / "sdk-worker.js"
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory) / "plain.js"
            traced = Path(directory) / "traced.js"
            write_e2_worker(source, plain)
            write_e2_worker(source, traced, lok_trace=True)
            plain_text = plain.read_text(encoding="utf-8")
            traced_text = traced.read_text(encoding="utf-8")
            self.assertNotIn("lok-trace", plain_text)
            self.assertIn("lok-trace", traced_text)
            # Line count, not set difference: `if (debugEnabled)` already
            # appears elsewhere in the worker, so a set difference would report
            # one added line and quietly pass a patch that added ten.
            self.assertEqual(
                len(traced_text.split("\n")) - len(plain_text.split("\n")), 2)
            # Removing the two added lines must give the untraced worker back:
            # anything else means the patch edited something it did not declare.
            self.assertEqual(
                traced_text.replace(
                    '      if (debugEnabled)\n'
                    '        postEvent("diagnostic", { level: "lok-trace", detail: event });\n',
                    ""),
                plain_text)


class TestFrozenArtifacts(unittest.TestCase):
    """E2 discovery must not replace any artifact an earlier release validated."""

    def test_frozen_hashes(self):
        for relative, expected in FROZEN.items():
            path = PROJECT / "dist" / "profiles" / relative
            if not path.is_file():
                self.skipTest(f"{relative} not built in this workspace")
            with self.subTest(artifact=relative):
                self.assertEqual(sha256(path), expected)

    def test_the_wedge_trace_profile_is_the_shipped_artifact(self):
        """Finding 037.

        Every conclusion the wedge trace supports is a conclusion about the
        engine the verdicts are bound to, and that is only true while the two
        profiles carry the same wasm byte for byte.  A rebuilt diagnostic would
        be answering a different artifact's question (finding 027).
        """
        traced = PROJECT / "dist" / "profiles" / "e2-wedge-trace" / "probe.wasm"
        shipped = PROJECT / "dist" / "profiles" / "e2-format-discovery" / "probe.wasm"
        if not traced.is_file() or not shipped.is_file():
            self.skipTest("wedge-trace or format-discovery profile not built")
        self.assertEqual(sha256(traced), sha256(shipped))


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


class TestFormatBarrierSelectionAttribution(unittest.TestCase):
    """Finding 033: what may advance the barrier, and by which dispatch path.

    Two properties are pinned here because both were learned by breaking them,
    and neither is visible from any other layer.

    The advance out of AwaitingSelection must require this barrier's own select
    command result *and* a non-empty selection.  Accepting any non-empty
    selection is the original defect: a caller's search selects its match, and
    the barrier would read that paragraph instead.

    The select step must be one dispatch.  It was two (GoToStartOfPara +
    EndOfParaSel) and that shape had two faults, each learned by breaking it:
    dispatching them with different notify flags reordered their effects (A5
    styled-list attempt-04 read back `<p>D-END</p>` for a paragraph reading
    `E1-STYLED-END`, a selection anchored mid-word), and the pair escaped to the
    neighbouring paragraph whenever the caret already sat at a paragraph edge
    (finding 034).  A single dispatch has neither fault available to it, so the
    test pins the count as well as the name.
    """

    @classmethod
    def setUpClass(cls):
        cls.source = (PROJECT / "src" / "probe_engine.cpp").read_text(encoding="utf-8")

    def selection_dispatch(self) -> str:
        start = self.source.index("void postFormatBarrierParagraphSelection() {")
        return self.source[start:self.source.index("\n}\n", start)]

    def test_the_select_step_is_exactly_one_dispatch(self):
        body = self.selection_dispatch()
        self.assertEqual(body.count("postUnoCommand("), 1)
        self.assertIn("kFormatBarrierSelectCommand, nullptr, true)", body)
        # notify=true is what makes the command result exist to attribute with;
        # a false here would leave AwaitingSelection with nothing to advance on
        # and every dispatch would end at the deadline instead.
        self.assertNotIn("false)", body)
        # The pair is gone, not merely unreferenced by name.
        self.assertNotIn("GoToStartOfPara", body)
        self.assertNotIn("EndOfParaSel", body)

    def test_the_advance_requires_the_result_and_the_selection(self):
        start = self.source.index("void maybeAdvanceFormatBarrierSelection() {")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn("!gFormatBarrier.selectionResultSeen ||", body)
        self.assertIn("gEditorState.selectionRectangles.empty()", body)

    def test_attribution_matches_the_command_name(self):
        # The action's own command also returns a result, so "a result arrived"
        # would attribute the wrong one.  .uno:SelectText returns one on every
        # dispatch (native 26.8, 10/10, selecttext-result/), which is what makes
        # the name comparison work after the switch.
        self.assertIn('const char *const kFormatBarrierSelectCommand = ".uno:SelectText";',
                      self.source)
        self.assertIn("commandResultMatches(payload, kFormatBarrierSelectCommand)",
                      self.source)

    def test_caret_movers_are_refused_while_a_barrier_is_in_flight(self):
        # Search is a caret mover -- .uno:ExecuteSearch selects its match --
        # and is the path A5's crosstalk case actually takes, so it is gated
        # alongside the selection command rather than treated as a read.
        for operation in ('"editor-select"', '"editor-action"', '"search"'):
            with self.subTest(operation=operation):
                index = self.source.index(
                    f'emitCommandError(command, {operation}, "BUSY",\n'
                    f'                     "a verified format-state action is still in flight");')
                guard = self.source.rindex("if (formatBarrierActive()) {", 0, index)
                self.assertLess(index - guard, 200)


class TestFormatBarrierRefusesWhatItCannotJudge(unittest.TestCase):
    """Finding 034: the three ways the barrier now declines to have an opinion.

    Each corresponds to a shape that was measured, not imagined:

    * multi-block -- .uno:SelectText on an empty paragraph mid-document selects
      it *and* the paragraph after it (native 26.8), so the markup carries two
      block tags and the first-tag scan would describe an unknown mixture as if
      it were one paragraph.
    * containment -- the readback describes whatever is selected, and nothing
      else ties that to the paragraph the command changed.  The pre-change build
      reported `verified-format-readback` on a run whose markup carried the
      neighbour's text (caret-offset-discriminator/chrome/styled-list).
    * deadline -- at the document's last paragraph, if empty, the select command
      returns its result and no selection callback ever arrives (native 26.8,
      selectionType 0).  Nothing would ever advance the barrier, and the BUSY
      gate turns that into a wedged document handle.

    All three report one code.  The caller's decision is identical in all three
    -- do not replay -- and a code per shape would invite branching on a
    distinction the caller cannot act on.
    """

    @classmethod
    def setUpClass(cls):
        cls.source = (PROJECT / "src" / "probe_engine.cpp").read_text(encoding="utf-8")

    def finish_body(self) -> str:
        start = self.source.index("void finishFormatBarrierAfterRestore() {")
        return self.source[start:self.source.index("\n}\n", start)]

    def test_the_block_counts_say_whether_they_were_observed(self):
        """Finding 046: a default reported as an observation, twice.

        `preBlockCount` is assigned only where the selection rectangles are
        non-empty (the range routes) and `postBlockCount` only in the cross
        route's check, so on the collapsed route both read 0 -- including on a
        barrier that succeeded.  Two rounds of evidence and one whole
        native-versus-browser "disagreement" were built on reading that zero as
        a measurement.

        Whole lines, not substrings: the lesson this file already records is
        that `if (false && ...)` satisfies a substring check.
        """
        lines = self.source.splitlines()
        for counter, flag in (("preBlockCount", "preBlockCountObserved"),
                              ("postBlockCount", "postBlockCountObserved")):
            # Assignments through an object, not the struct's own default:
            # `barrier.preBlockCount = ...` / `gFormatBarrier.postBlockCount = ...`.
            assignments = [index for index, line in enumerate(lines)
                           if line.strip().endswith(";")
                           and f".{counter} =" in line
                           and "Observed" not in line]
            self.assertEqual(len(assignments), 1,
                             f"{counter} is assigned in {len(assignments)} "
                             f"places; the flag below assumes exactly one")
            following = lines[assignments[0] + 1].strip()
            self.assertIn(f"{flag} = true;", following,
                          f"{counter} is written without setting {flag} on the "
                          f"next line, so the record cannot say whether the "
                          f"count is an observation")
        # And both flags have to reach the evidence, or they are a comment.
        self.assertIn('<< ",\\"preBlocksObserved\\":"', self.source)
        self.assertIn('<< ",\\"postBlocksObserved\\":"', self.source)

    def test_multi_block_is_computed_from_both_counts(self):
        start = self.source.index("FormatReadback parseFormatReadback(")
        body = self.source[start:self.source.index("\n}\n", start)]
        # Two block tags is the plain two-paragraph read; two <li> is the same
        # thing inside a single <ul>, where the block count alone would be 2 as
        # well but the list shape is what makes it legible.
        self.assertIn("readback.blockCount > 1 || readback.itemCount > 1", body)

    def test_the_three_unknown_outcomes_share_one_code(self):
        self.assertIn(
            'const char *const kFormatMutationOutcomeUnknown = "MUTATION_OUTCOME_UNKNOWN";',
            self.source)
        body = self.finish_body()
        # Five, not two: M2 split the single "unknown tag" outcome into three
        # channels -- a footnote or endnote apparatus (measured, and refused on
        # purpose), a tag nobody has measured, and markup that is not shaped
        # like any sample.  They report one code because the caller's decision
        # is the same in all of them; they carry different failure shapes
        # because the person reading the telemetry has to be able to tell "the
        # cross-paragraph guard fired" from "a user touched a footnote".
        # Six since finding 037 added the selection-type guard, which is the
        # same kind of answer as the other five: the action was dispatched and
        # nobody could check what it did.
        #
        # Eight since the pre-dispatch cross-paragraph route landed (8879d71,
        # 2026-08-15): that route judges itself and never reaches the checks
        # below, so it brings its own two channels.
        #
        # Counted by SHAPE, not by number.  As a bare count this assertion went
        # stale the day the route landed and stayed red for a day with nobody
        # running it, and all it could report was "8 != 6" -- which cannot tell
        # a new channel that carries its own shape (fine) from a second exit
        # reusing an existing shape (not fine: the telemetry can no longer say
        # which one fired).  The list is what the test is for.
        # Pair every exit with the shape assigned immediately before it, so the
        # question asked is "which shapes report the unknown code", not "how
        # many times does this token appear".
        exits = []
        for match in re.finditer(r"failFormatBarrier\(\s*([^,\n]+)", body):
            before = body[:match.start()]
            shape_matches = re.findall(r'failureShape =([^;]*);', before, re.S)
            named = re.findall(r'"([^"]+)"', shape_matches[-1]) if shape_matches else []
            exits.append((match.group(1).strip(), named))
        unknown_named = [name for code, names in exits
                         if code == "kFormatMutationOutcomeUnknown"
                         for name in names]
        unknown_shapes = [
            "block-extraction-failed",          # cross route, unreadable
            "block-count-changed",              # cross route, selection resized
            "selection-type-not-readable",      # finding 037's guard
            "footnote-apparatus-readback",      # measured, refused on purpose
            "unknown-structural-tag",
            "malformed-readback-nesting",
            "multi-block-readback",
            "selection-does-not-contain-restore-point",
            # Ninth, and it arrived without being declared here.
            #
            # Finding 046's fix (commit 7461800, "barrier 不再驗錯段落") added
            # this exit to the engine and did not add it to this list, so
            # `make test-e2-a-static` went red and stayed red -- that target is
            # not in the handoff's routine command list, so nobody ran it.
            # Found 2026-08-23 by running `unittest discover` over the whole
            # tests/ directory rather than the modules the Makefile names.
            #
            # THE COUNT ASSERTION BELOW IS WHAT CAUGHT IT, which is the answer
            # to the comment further up arguing that counting is the wrong
            # question: the shape-by-shape assertions can only check the shapes
            # somebody remembered to list, so the count is the only term that
            # notices a NEW exit. Both are needed; neither is redundant.
            "readback-is-a-different-paragraph",
        ]
        # "block-text-mismatch" rides the same exit as "block-count-changed"
        # (one ternary, two shapes), so the exit count and the shape count are
        # not the same number and neither is asserted against the other.
        for shape in unknown_shapes + ["block-text-mismatch"]:
            self.assertIn(shape, unknown_named, shape)
        self.assertEqual(body.count("kFormatMutationOutcomeUnknown"),
                         len(unknown_shapes))
        # Distinct among the unknown-code exits: two of them sharing a shape
        # would leave telemetry unable to say which one fired, and a count can
        # never see that.  `postcondition-not-met` is deliberately shared by
        # the two POSTCONDITION_FAILED exits -- same meaning, different route,
        # and the route travels in the payload -- so it is not in this set.
        self.assertEqual(len(unknown_named), len(set(unknown_named)),
                         unknown_named)
        start = self.source.index("void failFormatBarrierAtDeadline() {")
        self.assertIn("kFormatMutationOutcomeUnknown",
                      self.source[start:self.source.index("\n}\n", start)])

    def test_postcondition_failed_keeps_its_narrow_meaning(self):
        # It must be reached only after both "is this one paragraph" questions
        # have been answered yes; otherwise a two-paragraph read that happens to
        # start with the right tag would be judged as a postcondition.
        body = self.finish_body()
        # The guards are matched whole, not by substring.  A mutation that
        # disabled the multi-block check with `if (false && ...)` left every
        # substring in place and every ordering unchanged, and an earlier
        # version of this test passed on it -- a check that survives the thing
        # it checks being switched off is not a check.
        self.assertIn("  if (gFormatBarrier.readback.multiBlock) {", body)
        self.assertIn(
            "  if (gFormatBarrier.containmentChecked && !gFormatBarrier.containmentHeld) {",
            body)
        multi = body.index("readback.multiBlock")
        contain = body.index("containmentChecked")
        judged = body.index("formatBarrierReadbackSatisfied()")
        self.assertLess(multi, judged)
        self.assertLess(contain, judged)
        # TWO since the cross-paragraph route landed (8879d71), and the second
        # one has to keep the same narrow meaning on its own route: it is
        # reached only after that route has answered ITS two questions -- was
        # the selection readable at all (crossChecked + selectionTypeReadable)
        # and is it still the same selection (crossIdentityHeld).  Asserting
        # the count alone would have accepted a second exit reached with
        # neither.
        # Whole lines again, for the `if (false && ...)` reason above.
        self.assertIn("    if (!gFormatBarrier.crossStateHeld) {", body)
        self.assertIn("    if (!gFormatBarrier.crossIdentityHeld) {", body)
        self.assertIn("        !gFormatBarrier.selectionTypeReadable) {", body)
        cross_checked = body.index("    if (!gFormatBarrier.crossChecked ||")
        cross_identity = body.index("    if (!gFormatBarrier.crossIdentityHeld) {")
        cross_state = body.index("    if (!gFormatBarrier.crossStateHeld) {")
        self.assertLess(cross_checked, cross_state)
        self.assertLess(cross_identity, cross_state)
        self.assertEqual(body.count("EDITOR_FORMAT_POSTCONDITION_FAILED"), 2)

    def test_the_html_read_is_reachable_only_through_the_selection_type_guard(self):
        """Finding 037.

        getTextSelection(..., "text/html", ...) does not return on a selection
        containing an as-char image, and the engine thread dies inside it, so
        the 5000ms stage deadline cannot fire -- it is only consulted when the
        command queue is empty.  There is no timeout that rescues this; the
        call must not be made.  The whole fix is one `if`, which makes it
        exactly the kind of thing a later edit removes without noticing.
        """
        # The definition, not the forward declaration above it.
        start = self.source.index(
            "void handleFormatBarrierStep(const Command &command) {")
        body = self.source[start:self.source.index("\n}\n", start)]
        # Matched whole, with the call on its own indented line: a substring
        # test would pass on `if (false && formatBarrierSelectionIsReadable())`.
        self.assertIn(
            "    if (formatBarrierSelectionIsReadable())\n"
            "      readFormatBarrierPostcondition();\n",
            body)
        # And nowhere else, in the whole engine, is the read called unguarded:
        # its definition plus this one call site.
        self.assertEqual(self.source.count("readFormatBarrierPostcondition()"), 2)
        # Counted on the call, not on the string: `"text/html"` also appears in
        # the comment explaining why the guard exists, and a test that broke
        # when someone wrote a comment would get the comment deleted.
        read_start = self.source.index("void readFormatBarrierPostcondition() {")
        read_body = self.source[read_start:self.source.index("\n}\n", read_start)]
        self.assertEqual(read_body.count('"text/html"'), 1)
        # Every call site, each named with the guard that stands in front of it.
        #
        # This used to be `assertEqual(count, 2)`, and it went stale the moment
        # the pre-dispatch routing landed (8879d71, 2026-08-15) -- two new call
        # sites, both correctly guarded, and a test that could only say "the
        # number changed".  Nobody ran it for a day, and when it was finally
        # run it could not tell a safe addition from an unsafe one.  A count is
        # not the property; the property is that no call is reachable without
        # the type having been read first.
        #
        # So: the count still has to be updated deliberately (a new call site
        # must be added here), but each entry now carries the guard, and the
        # guard is checked to appear BEFORE the call inside its own function.
        # Matched WHOLE, never as a substring: `if (false && <guard>)` keeps
        # every substring and every ordering, and this file has already been
        # bitten by exactly that (see the multi-block note above).
        guarded_call_sites = {
            # The guard's own implementation: it reads the type and returns it.
            "SelectionReadback readSelection() {":
                "    if (readback.type == LOK_SELTYPE_TEXT)\n",
            # Pre-dispatch routing refuses anything that is not TEXT before it
            # ever reads html (finding 037's newest call site).
            "bool routeFormatBarrier(":
                "    if (selection.type != LOK_SELTYPE_TEXT) {\n",
            # The cross-paragraph postcondition: early return on an unreadable
            # selection.
            "void checkFormatBarrierCrossParagraph() {":
                "  if (!formatBarrierSelectionIsReadable())\n",
        }
        for signature, guard in guarded_call_sites.items():
            start = self.source.index(signature)
            body = self.source[start:self.source.index("\n}\n", start)]
            self.assertIn(guard, body, signature)
            self.assertLess(body.index(guard), body.index("pClass->getTextSelection("),
                            signature)
        # readFormatBarrierPostcondition() carries no guard of its own; its
        # single caller does, and that pairing is asserted whole above.
        self.assertEqual(self.source.count("pClass->getTextSelection("),
                         len(guarded_call_sites) + 1)

    def test_the_guard_accepts_only_a_plain_text_selection(self):
        # LOK_SELTYPE_LARGE_TEXT is documented in LibreOfficeKitEnums.h as
        # "unused (same as LOK_SELTYPE_COMPLEX)", so accepting it would be
        # accepting a value core does not produce; NONE has nothing to read.
        start = self.source.index("bool formatBarrierSelectionIsReadable() {")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn("selection.type == LOK_SELTYPE_TEXT", body)
        for rejected in ("LOK_SELTYPE_COMPLEX", "LOK_SELTYPE_LARGE_TEXT",
                         "LOK_SELTYPE_NONE"):
            self.assertNotIn(rejected, body)
        # The type it read is recorded whether or not it refused, so ordinary
        # sweep evidence answers "what would this guard refuse?".
        self.assertIn("gFormatBarrier.selectionType = selection.type", body)
        self.assertIn('"selectionType\\":" << barrier.selectionType', self.source)

    def test_the_unreadable_selection_is_judged_before_every_readback_shape(self):
        # When the guard refuses there is no readback at all: parsed is false
        # and every count is zero.  Judged anywhere later, the refusal would be
        # reported as "the document is not in the state you asked for", which
        # is a claim about the document made by a build that did not look at it.
        body = self.finish_body()
        self.assertIn("  if (!gFormatBarrier.selectionTypeReadable) {", body)
        self.assertEqual(body.count('"selection-type-not-readable"'), 1)
        guard = body.index("selectionTypeReadable")
        for later in ("readback.footnoteApparatus", "readback.unknownTag",
                      "readback.malformedNesting", "readback.multiBlock",
                      "containmentChecked", "formatBarrierReadbackSatisfied()"):
            self.assertLess(guard, body.index(later),
                            f"the selection-type guard must be judged before {later}")

    def test_an_aborted_scan_is_judged_before_the_counts_it_truncated(self):
        # The three abort cases stop the scan where they are met, so blockCount
        # and itemCount stop there too.  Judged after multiBlock, a footnote
        # would be reported as a cross-paragraph read -- a fact about where the
        # scan gave up, dressed as a fact about the document.
        body = self.finish_body()
        self.assertIn("  if (gFormatBarrier.readback.footnoteApparatus) {", body)
        self.assertIn("  if (gFormatBarrier.readback.unknownTag) {", body)
        self.assertIn("  if (gFormatBarrier.readback.malformedNesting) {", body)
        for guard in ("footnoteApparatus", "unknownTag", "malformedNesting"):
            self.assertLess(body.index(guard), body.index("readback.multiBlock"),
                            f"{guard} must be judged before multiBlock")
            self.assertLess(body.index(guard), body.index("containmentChecked"))
        for shape in ("footnote-apparatus-readback", "unknown-structural-tag",
                      "malformed-readback-nesting", "multi-block-readback"):
            self.assertEqual(body.count(f'"{shape}"'), 1,
                             f"{shape} must be one channel, used once")

    def test_the_readback_predicate_cannot_pass_an_aborted_scan(self):
        # Ordering in the caller is not the only defence.  A future caller that
        # reordered the guards must not be able to reach satisfaction from a
        # scan that stopped early.
        # Finding 037's guard is in the same list and is the strongest case:
        # when it refuses, no scan happened at all.
        satisfied_start = self.source.index("bool formatBarrierReadbackSatisfied() {")
        satisfied = self.source[
            satisfied_start:self.source.index("\n}\n", satisfied_start)]
        self.assertIn("!gFormatBarrier.selectionTypeReadable", satisfied)
        start = self.source.index("bool formatBarrierReadbackSatisfied() {")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn(
            "  if (!gFormatBarrier.selectionTypeReadable || !readback.parsed ||\n"
            "      readback.unknownTag || readback.malformedNesting ||\n"
            "      readback.footnoteApparatus)\n    return false;",
            body)

    def test_the_footnote_signature_reads_the_id_and_covers_endnotes(self):
        # sw/source/filter/html/htmlftn.cxx writes "sdendnote" for endnotes and
        # "sdfootnote" for footnotes.  Matching only the latter would drop every
        # endnote paragraph into the unmeasured-tag channel, which is the exact
        # pollution the separate channels exist to prevent.  And the same writer
        # emits <div> from six other places, so the id has to be read: a blanket
        # rule on body-level <div> would mislabel all of them.
        start = self.source.index("bool formatDivIsFootnoteApparatus(")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn('attributes.find("id=\\"")', body)
        self.assertIn('"sdfootnote"', body)
        self.assertIn('"sdendnote"', body)

    def test_structural_tags_are_counted_at_every_depth(self):
        # The rule filters non-structural tags by depth and structural tags not
        # at all.  Reversed -- "once inside a block, ignore everything" -- <li>
        # and the <p> inside a list item both vanish, itemCount and blockCount
        # go to zero, and finding 034's guard goes with them.
        start = self.source.index("FormatReadback parseFormatReadback(")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn("    if (depth > 0 || closing)\n      continue;", body)
        structural = body.index("if (formatTagIsStructural(tag)) {")
        filtered = body.index("    if (depth > 0 || closing)")
        self.assertLess(structural, filtered,
                        "structural tags must be handled before the depth filter")
        # The counters are matched whole and carry no depth condition.  Adding
        # one is exactly how this fix would be undone.
        self.assertIn(
            "      if (formatTagIsBlock(tag)) {\n"
            "        ++readback.blockCount;\n"
            "        if (readback.blockTag.empty())\n"
            "          readback.blockTag = tag;\n"
            "      } else if (tag == \"li\") {\n"
            "        ++readback.itemCount;\n"
            "      }\n",
            body)

    def test_containment_runs_before_the_restore_collapses_the_selection(self):
        # Anchored inside the step handler: the stage-name table above also
        # contains a line starting "  case FormatBarrierStage::ReadQueued:",
        # and slicing from the first match measured that instead.
        handler = self.source.index("void handleFormatBarrierStep(const Command &command) {")
        start = self.source.index("  case FormatBarrierStage::ReadQueued:", handler)
        body = self.source[start:self.source.index("    return;", start)]
        self.assertLess(body.index("checkFormatBarrierContainment()"),
                        body.index("postFormatBarrierRestore()"))

    def test_containment_records_why_it_did_not_check(self):
        # "The selection did not cover the caret" and "we never worked out where
        # either was" must not both surface as a bare false.
        start = self.source.index("void checkFormatBarrierContainment() {")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn("gFormatBarrier.containmentChecked = false;", body)
        self.assertIn("gFormatBarrier.containmentChecked = true;", body)
        finish = self.finish_body()
        self.assertIn("gFormatBarrier.containmentChecked && !gFormatBarrier.containmentHeld",
                      finish)


class TestFormatBarrierDeadline(unittest.TestCase):
    """Finding 033's open gap, closed because finding 034's repair reopens it."""

    @classmethod
    def setUpClass(cls):
        cls.source = (PROJECT / "src" / "probe_engine.cpp").read_text(encoding="utf-8")

    def test_the_deadline_is_its_own_number(self):
        # Explicitly not the selection barrier's 250ms: that was measured for a
        # different question, and reusing a nearby number is how a measurement
        # turns into a habit.
        self.assertIn("constexpr int FormatBarrierStageDeadlineMs = 5000;", self.source)

    def test_every_awaiting_stage_arms_it(self):
        for marker in (
            "barrier.stage = FormatBarrierStage::AwaitingResult;",
            "gFormatBarrier.stage = FormatBarrierStage::AwaitingSelection;",
            "gFormatBarrier.stage = FormatBarrierStage::AwaitingRestore;",
        ):
            with self.subTest(stage=marker):
                index = self.source.index(marker)
                following = self.source[index:index + 400]
                self.assertIn("armFormatBarrierDeadline();", following)

    def test_the_deadline_can_only_fail(self):
        start = self.source.index("void failFormatBarrierAtDeadline() {")
        body = self.source[start:self.source.index("\n}\n", start)]
        self.assertIn("failFormatBarrier(", body)
        self.assertNotIn("completeFormatBarrier", body)
        # getTextSelection returns markup at the document-end empty paragraph
        # even with no selection (490 bytes, a single <p>), so a fallback read
        # would satisfy the set-paragraph-body postcondition out of nothing.
        self.assertNotIn("readFormatBarrierPostcondition", body)

    def test_the_synthesised_step_reproves_the_barrier_it_belongs_to(self):
        start = self.source.index("void handleFormatBarrierStep(const Command &command) {")
        body = self.source[start:self.source.index("\n  switch (gFormatBarrier.stage)", start)]
        self.assertIn("command.correlation != gFormatBarrier.serial", body)
        self.assertIn("if (command.values[0] == 1) {", body)
        # And again inside, because the barrier can advance between the wait
        # returning and the step running.
        deadline = self.source.index("void failFormatBarrierAtDeadline() {")
        self.assertIn("gFormatBarrier.stageDeadlineArmed",
                      self.source[deadline:self.source.index("\n}\n", deadline)])

    def test_both_engine_loops_carry_it(self):
        # The main-loop profile shares this barrier code; leaving it without a
        # deadline would give two profiles different failure behaviour from one
        # source.
        #
        # Matched on the whole guard.  Searching for the field name inside a
        # window passed on a branch prefixed with `if (false && ...)`, because
        # every substring was still present -- the same way the multi-block
        # ordering test failed, and worth stating twice.
        for loop, guard in (
            ("void engineLoop(Command initialReady) {",
             "        if (formatBarrierActive() && gFormatBarrier.stageDeadlineArmed) {"),
            ("int mainLoopDrainCommands() {",
             "        if (!synthetic && formatBarrierActive() &&\n"
             "            gFormatBarrier.stageDeadlineArmed &&"),
        ):
            with self.subTest(loop=loop):
                start = self.source.index(loop)
                body = self.source[start:start + 6000]
                self.assertIn(guard, body)
                self.assertIn("command.values[0] = 1;", body)


class TestLocaleAttributionProfile(unittest.TestCase):
    """Finding 031: the UI language is a build-level experiment, not a surface."""

    PROFILE = PROJECT / "dist" / "profiles" / "e2-locale-attribution"

    def test_only_the_locale_profile_compiles_a_language_in(self):
        for name in ("e2-format-discovery", "e2-scheduler-attribution",
                     "e2-mainloop-attribution", "e2-mainloop-pei-attribution"):
            manifest = PROJECT / "dist" / "profiles" / name / "sdk-manifest.json"
            if not manifest.is_file():
                continue
            with self.subTest(profile=name):
                diagnostic = json.loads(manifest.read_text(encoding="utf-8"))["diagnostic"]
                # None means the profile predates the field; both readings say
                # "this build does not ask LOK for a language".
                self.assertIsNone(diagnostic.get("uiLanguage"))

    def test_locale_profile_declares_the_language_it_was_built_with(self):
        manifest = self.PROFILE / "sdk-manifest.json"
        if not manifest.is_file():
            self.skipTest("locale attribution profile not built")
        diagnostic = json.loads(manifest.read_text(encoding="utf-8"))["diagnostic"]
        self.assertEqual(diagnostic["scope"], "e2-locale-attribution")
        self.assertEqual(diagnostic["uiLanguage"], "zh-TW")


class TestPostconditionResolvesAutomaticStyles(unittest.TestCase):
    """A paragraph that is both a heading and a list item carries P2, not Heading_20_1.

    Joining a list gives the paragraph an automatic style inheriting from the
    named one, so comparing the raw text:style-name answers "no" for a document
    that is in fact correct.  This bit the native analyzer first and then the
    browser runner, in the same day, because the fix was not carried across --
    so it is pinned in both places now.
    """

    # A real document from the run that exposed this: the anchor paragraph is a
    # Heading 1 *and* a list item, so its text:style-name is P2.
    EVIDENCE = (PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery"
                / "state-readback" / "wasm" / "chrome" / "attempt-10"
                / "after-heading-on-repeat-2.odt")

    def test_a_heading_inside_a_list_resolves_to_heading(self):
        import run_e2_discovery  # noqa: PLC0415

        if not self.EVIDENCE.is_file():
            self.skipTest("evidence document not present")
        inspection = run_e2_discovery.inspect_target_paragraph(
            self.EVIDENCE, "E1-STYLED-END")
        self.assertTrue(inspection["found"])
        self.assertTrue(inspection["insideList"])
        # The raw name is an automatic style; the resolved one is the answer.
        self.assertEqual(inspection["paragraphStyle"], "P2")
        self.assertEqual(inspection["resolvedParagraphStyle"], "Heading_20_1")

    def test_postconditions_are_keyed_on_the_resolved_style(self):
        import run_e2_discovery  # noqa: PLC0415

        for label in ("heading-on", "heading-on-repeat-1", "heading-on-repeat-2"):
            with self.subTest(label=label):
                expected = run_e2_discovery.EXPECTED_POSTCONDITIONS[label]
                # The raw name is not the style once a list is involved, so a
                # postcondition keyed on it is only right by accident.
                self.assertNotIn("paragraphStyle", expected)
                self.assertEqual(expected["resolvedParagraphStyle"], "Heading_20_1")

    def test_analyzer_and_runner_agree_on_the_rule(self):
        import analyze_e2_a_native_reissue as analyzer  # noqa: PLC0415

        source = (PROJECT / "tools" / "run_e2_discovery.py").read_text(encoding="utf-8")
        self.assertIn("parent-style-name", source)
        self.assertIn("parent-style-name",
                      (PROJECT / "tools" / "analyze_e2_a_native_reissue.py")
                      .read_text(encoding="utf-8"))
        self.assertIn("resolvedStyle", analyzer.describe.__code__.co_consts)


class TestFrozenMatrixMatchesTheEngine(unittest.TestCase):
    """The matrix is the frozen contract; drift makes it decoration.

    It was revised on 2026-08-11 for finding 030 and route C, deliberately and
    with the superseded values kept.  These check the engine still dispatches
    and judges what the revised matrix says -- the failure mode being guarded
    against is a later code change that quietly leaves the matrix behind.
    """

    MATRIX = json.loads(
        (PROJECT / "e2" / "discovery-matrix-v1.json").read_text(encoding="utf-8"))
    ENGINE = (PROJECT / "src" / "probe_engine.cpp").read_text(encoding="utf-8")

    def test_list_actions_carry_the_on_parameter_in_both_places(self):
        for action in ("set-list-unordered", "set-list-ordered"):
            with self.subTest(action=action):
                self.assertEqual(
                    self.MATRIX["dispatchMap"][action]["arguments"], {"On": True})
        self.assertIn('"\\"value\\":true}}"', self.ENGINE)

    def test_completion_requires_the_readback_not_the_broadcast(self):
        rule = self.MATRIX["completionRule"]
        self.assertIn("document-readback-postcondition", rule["requires"])
        self.assertNotIn("expected-state-postcondition", rule["requires"])
        self.assertIn("verified-format-readback", self.ENGINE)

    def test_changed_is_not_claimed(self):
        # A repeat press lands on an already-correct document and reads back the
        # same thing, so claiming changed:true would assert what nothing checked.
        self.assertIn("null", self.MATRIX["completionRule"]["changedClaim"])
        self.assertIn('\\"changed\\":null', self.ENGINE)

    def test_the_revision_keeps_what_it_replaced(self):
        revision = self.MATRIX["revisions"][0]
        self.assertEqual(revision["date"], "2026-08-11")
        superseded = revision["superseded"]
        self.assertIsNone(superseded["dispatchMap"]["set-list-unordered"]["arguments"])
        self.assertIn("expected-state-postcondition",
                      superseded["completionRule"]["requires"])
        self.assertIn("fail-closed-unknown-precondition",
                      superseded["requiredProperties"])

    def test_thresholds_were_not_relaxed(self):
        thresholds = self.MATRIX["thresholds"]
        self.assertEqual(thresholds["positiveRepetitionsPerBrowser"], 3)
        self.assertEqual(thresholds["negativeRepetitionsPerBrowser"], 1)
        self.assertEqual(thresholds["callbackBarrierMs"], 10000)
        self.assertEqual(thresholds["operationTimeoutMs"], 30000)
        self.assertEqual(thresholds["roundtripDocumentsPerBrowser"], 3)


class TestFinding031Tripwire(unittest.TestCase):
    """Fails when the latent defect in finding 031 becomes reachable.

    The barrier matches the paragraph style postcondition against the whole
    strings "Heading 1" and "Body Text", which core draws from a table keyed by
    UI language.  Today that is harmless only because the shipped WASM
    filesystem image carries no message catalogs at all -- zh-TW is selectable
    from the registry langpacks and there is nothing to select.  Adding
    translations is a prerequisite for a zh-TW product and is exactly the moment
    the comparison silently stops matching, which is also the moment nobody
    would think to re-check a format barrier.  So notice it here instead.
    """

    IMAGE = (PROJECT.parent / "wasm-lite" / "build-headless-probe" / "workdir"
             / "CustomTarget" / "static" / "emscripten_fs_image"
             / "soffice.data.js.metadata")

    def test_shipped_image_still_carries_no_message_catalogs(self):
        if not self.IMAGE.is_file():
            self.skipTest("wasm-lite filesystem image metadata not present")
        files = [entry["filename"]
                 for entry in json.loads(self.IMAGE.read_text(encoding="utf-8"))["files"]]
        catalogs = [name for name in files if name.endswith(".mo")]
        self.assertEqual(catalogs, [], msg=(
            "translations are now packaged, so the UIName table is no longer "
            "English-only and the paragraph-style postcondition strings in "
            "probe_engine.cpp will stop matching -- see finding 031 before "
            "deleting this test"))


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

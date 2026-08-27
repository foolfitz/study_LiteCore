"""Every mutation in the product path must still apply to the tree it mutates.

Written 2026-08-22, after `cut-swallows-its-failure` was found dead.

Its `find` named `session.action("delete-backward", {})` inside the cut
handler, and the ABI 4 link work replaced that line with a ternary on
`offers("delete-selection")`.  The pattern then matched `dist/` **zero** times.
`apply_mutation` fails loudly on that -- but only for somebody who runs the
mutation, and nobody ran it between the link and the day it was noticed.

So the mutation had silently stopped being evidence that its check can fail,
which is the same silence the mutation exists to break.  A mutation is a check's
only proof that it is capable of going red; one that cannot be applied is worth
nothing and looks exactly like one that is fine.

This is deliberately a STATIC test.  It costs a file read per mutation and it
runs in `make test-e2-c-static`, so the rot is caught on the commit that causes
it rather than on the next run that happens to name that mutation -- which for
this one would have been an unbounded wait.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_e2_c_product_path as probe  # noqa: E402

DIST = ROOT / "dist"


def _specs() -> dict:
    return {name: spec for name, spec in probe.MUTATIONS.items()
            if isinstance(spec, dict) and "find" in spec}


class DiagnosticMirrorsStillApply(unittest.TestCase):
    """The same claim, for the mirrors that are not mutations.

    `--barrier-details-diagnostic` (2026-08-26) patches one anchor in the
    product page so a rejection's TYPED payload survives instead of only the
    message the user is shown.  The runner refuses to patch when the anchor is
    gone -- but only for somebody who runs it, which is how
    `cut-swallows-its-failure` came to be dead for weeks.
    """

    def test_the_worker_projection_anchor_is_still_in_every_profile_it_can_aim_at(self):
        """The worker the PAGE loads is the profile's copy, not `dist/sdk/`.

        `--barrier-details-diagnostic` widens `productFormatBarrier` there so
        the engine's whole barrier object survives the product's allowlist --
        which is where finding 082's answer was going. Checked on both profiles
        this runner can be pointed at today, because `--profile` decides which
        copy gets patched at run time.
        """
        for profile in ("e2-editor-v8", "e2-editor-v9"):
            with self.subTest(profile=profile):
                worker = DIST / "profiles" / profile / "sdk-worker.js"
                self.assertTrue(worker.is_file(), f"{profile} has no worker")
                hits = worker.read_text(encoding="utf-8").count(
                    probe.WORKER_BARRIER_ANCHOR)
                self.assertEqual(
                    hits, 1,
                    f"--barrier-details-diagnostic widens productFormatBarrier "
                    f"and found {hits} of its anchor in {profile}'s worker.")

    def test_the_barrier_details_anchor_is_still_in_the_page(self):
        page = DIST / "e2-editor-app.js"
        self.assertTrue(page.is_file())
        hits = page.read_text(encoding="utf-8").count(probe.BARRIER_DETAILS_ANCHOR)
        self.assertEqual(
            hits, 1,
            "--barrier-details-diagnostic patches run()'s catch and found "
            f"{hits} of it in dist/e2-editor-app.js. The page moved under the "
            "diagnostic; fix the anchor, not the count.")

    def test_the_caret_source_anchor_is_still_in_the_page(self):
        """Finding 084's instrument, asked before a run pays for it.

        The diagnostic patches `moveSinkToCaret` twice from one anchor -- a
        module-scope probe before it and an applied-log inside it -- so a page
        that moved under it costs a run to discover otherwise.
        """
        page = DIST / "e2-editor-app.js"
        self.assertTrue(page.is_file())
        hits = page.read_text(encoding="utf-8").count(probe.CARET_SOURCE_ANCHOR)
        self.assertEqual(
            hits, 1,
            "--caret-source-diagnostic patches moveSinkToCaret and found "
            f"{hits} of it in dist/e2-editor-app.js. The page moved under the "
            "diagnostic; fix the anchor, not the count.")

    def test_the_caret_source_patch_produces_a_page_that_parses(self):
        """The patch, run and handed to a JavaScript parser.

        An anchor that still matches says the patch APPLIED, not that what it
        produced is a page. A syntax error in the inserted text costs a browser
        run to find otherwise, and the run is minutes long.
        """
        node = shutil.which("node")
        if node is None:
            self.skipTest("no node to parse the patched page with")
        page = (DIST / "e2-editor-app.js").read_text(encoding="utf-8")
        patched = probe.caret_source_page(page)
        self.assertIn("window.__ppCaretEngine", patched)
        self.assertIn("window.__pp.announcements", patched)
        self.assertIn("caretBelieved", patched)
        self.assertIn("caretApplied", patched)
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "patched-page.mjs"
            target.write_text(patched, encoding="utf-8")
            done = subprocess.run([node, "--check", str(target)],
                                  capture_output=True, text=True)
        self.assertEqual(done.returncode, 0,
                         "--caret-source-diagnostic produced a page node "
                         f"refuses to parse:\n{done.stderr}")

    def test_the_announcement_anchor_is_still_in_the_page(self):
        """The page's onEvent, which is where `source` is still readable."""
        page = (DIST / "e2-editor-app.js").read_text(encoding="utf-8")
        hits = page.count(probe.CARET_ANNOUNCE_ANCHOR)
        self.assertEqual(
            hits, 1,
            "--caret-source-diagnostic records every engine announcement from "
            f"the page's onEvent and found {hits} of its anchor.")

    def test_the_page_state_anchor_is_still_in_the_page(self):
        """Both diagnostics patch it, and each demands exactly one."""
        page = DIST / "e2-editor-app.js"
        hits = page.read_text(encoding="utf-8").count(probe.PAGE_STATE_ANCHOR)
        self.assertEqual(
            hits, 1,
            "--barrier-details-diagnostic and --caret-source-diagnostic both "
            f"patch updateState and found {hits} of its anchor in "
            "dist/e2-editor-app.js.")


class MutationsStillApply(unittest.TestCase):

    def test_every_mutation_matches_its_target_exactly_once(self):
        """The same count `apply_mutation` demands, asked before the run."""
        for name, spec in sorted(_specs().items()):
            with self.subTest(mutation=name):
                target = DIST / spec["path"]
                self.assertTrue(target.is_file(),
                                f"{name} mutates a file that is not in dist")
                hits = target.read_text(encoding="utf-8").count(spec["find"])
                self.assertEqual(
                    hits, 1,
                    f"{name} expects one occurrence of its pattern in "
                    f"dist/{spec['path']} and found {hits}. The tree moved "
                    f"under the mutation; fix the pattern, not the count.")

    def test_every_mutation_actually_changes_the_file(self):
        """A find equal to its replace is a mutation that mutates nothing.

        Cheap to write by accident while editing a pattern, and it would leave
        the run reporting a green check under a mutation that changed no bytes
        -- which reads as "the check cannot be fooled" and means "the check was
        never tested".
        """
        for name, spec in sorted(_specs().items()):
            with self.subTest(mutation=name):
                self.assertNotEqual(spec["find"], spec["replace"], name)

    def test_every_mutation_names_a_check_the_run_can_produce(self):
        """`mustGoRed` has to name a check id that exists.

        A mutation pointed at a renamed check reports that the check did not go
        red, because no check by that name ever reported anything -- and that
        is indistinguishable from a product that survived the mutation.
        """
        source = (ROOT / "tools" / "run_e2_c_product_path.py").read_text(
            encoding="utf-8")
        for name, spec in sorted(_specs().items()):
            for cid in [spec["check"], *spec.get("alsoRed", [])]:
                with self.subTest(mutation=name, check=cid):
                    self.assertIn(f'check("{cid}"', source,
                                  f"{name} names a check id nothing emits")
    def test_a_mutation_that_needs_a_flag_names_one_the_runner_has(self):
        """`requiresFlag` must name an option this runner actually accepts.

        Some checks cannot be established without a diagnostic arm -- the
        refusal one needs `--refusal-diagnostic`, because on the shipped
        manifest the cut succeeds and there is no refusal to judge.  A mutation
        for such a check reports "the product survived it" when run without the
        flag, which is exactly what a DEAD mutation reports.  So the dependency
        is declared, and a renamed flag fails here rather than in a run nobody
        reads.
        """
        source = (ROOT / "tools" / "run_e2_c_product_path.py").read_text(
            encoding="utf-8")
        for name, spec in sorted(_specs().items()):
            flag = spec.get("requiresFlag")
            if flag is None:
                continue
            with self.subTest(mutation=name, flag=flag):
                self.assertIn(f'parser.add_argument("{flag}"', source,
                              f"{name} requires {flag}, which this runner does "
                              f"not define")


if __name__ == "__main__":
    unittest.main()

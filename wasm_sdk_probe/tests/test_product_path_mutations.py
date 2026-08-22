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
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_e2_c_product_path as probe  # noqa: E402

DIST = ROOT / "dist"


def _specs() -> dict:
    return {name: spec for name, spec in probe.MUTATIONS.items()
            if isinstance(spec, dict) and "find" in spec}


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


if __name__ == "__main__":
    unittest.main()

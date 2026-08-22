#!/usr/bin/env python3
"""`caret_from_columns` must not report a position it did not measure.

Written 2026-08-21, after the Firefox arm of the product path passed
`the-caret-lands-where-the-click-was` on a caret it had never located.

The oracle reads one band twice.  The column that GAINS ink is the caret's
second position and the one that LOSES it is the first, so `gained` and `lost`
are argmax/argmin over the per-column delta.  When one of the two reads does not
find the caret, that read contributes no non-zero delta -- the extremum is 0 and
argmax/argmin return **index 0**, the leftmost column of the canvas, purely by
tie-break.  Measured on Firefox (mutation none): strokeGained 24, strokeLost 0,
and the fraction was computed from that index anyway as (0 - 101) / 442 =
-0.229.  The check asks for near < 0.25.  It passed.

Why this is a unit test and not a page mutation: the defect is in the harness's
own arithmetic, and the state that triggers it -- caret drawn on the second
click but not the first -- is one that NO mutation in the suite produces.  The
`caret` mutation zeroes both reads, and `past > 0.75` catches that.  A pure
function can be shown the exact shape; a page cannot be asked to produce it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from run_e2_c_product_path import caret_from_columns  # noqa: E402

HEIGHT = 46
WIDTH = 20
GLYPH = 10          # dark rows a text column carries in both reads
CARET = 12          # dark rows the caret adds to the column it sits in
TEXT = range(5, 16)  # the line's own ink: columns 5..15 inclusive


def read(caret_column: int | None) -> dict:
    """One band read: text ink everywhere in TEXT, plus a caret if given."""
    columns = [0] * WIDTH
    for x in TEXT:
        columns[x] = GLYPH
    if caret_column is not None:
        columns[caret_column] += CARET
    return {"columns": columns, "width": WIDTH, "band": {"y": 0, "h": HEIGHT}}


class CaretFromColumns(unittest.TestCase):

    def test_both_reads_find_the_caret(self):
        """The case the oracle was written for: two real positions."""
        caret = caret_from_columns(read(6), read(14))
        self.assertTrue(caret["available"])
        self.assertEqual((caret["inkLeft"], caret["inkRight"]), (5, 15))
        self.assertEqual(caret["strokeLost"], CARET)
        self.assertEqual(caret["strokeGained"], CARET)
        self.assertAlmostEqual(caret["fractionNearStart"], 0.1)
        self.assertAlmostEqual(caret["fractionPastEnd"], 0.9)

    def test_only_the_second_read_finds_it(self):
        """Firefox, 2026-08-21.  `near` must be withheld, not invented.

        Before the fix this returned fractionNearStart = (0 - 5) / 10 = -0.5,
        which satisfies the check's `near < 0.25` -- so the check passed
        BECAUSE the caret was missing.  The assertion below is the whole point
        of this file.
        """
        caret = caret_from_columns(read(None), read(14))
        self.assertTrue(caret["available"])
        self.assertEqual(caret["strokeLost"], 0)
        self.assertIsNone(caret["fractionNearStart"])
        self.assertIsNone(caret["caretAfterClickNearStart"])
        # The half that WAS measured is still reported.
        self.assertEqual(caret["strokeGained"], CARET)
        self.assertAlmostEqual(caret["fractionPastEnd"], 0.9)

    def test_only_the_first_read_finds_it(self):
        """The mirror image, which no browser has shown but the maths allows."""
        caret = caret_from_columns(read(6), read(None))
        self.assertEqual(caret["strokeGained"], 0)
        self.assertIsNone(caret["fractionPastEnd"])
        self.assertIsNone(caret["caretAfterClickPastEnd"])
        self.assertEqual(caret["strokeLost"], CARET)
        self.assertAlmostEqual(caret["fractionNearStart"], 0.1)

    def test_neither_read_finds_it(self):
        """`--mutate caret`: the product draws none.  Both withheld."""
        caret = caret_from_columns(read(None), read(None))
        self.assertEqual((caret["strokeGained"], caret["strokeLost"]), (0, 0))
        self.assertIsNone(caret["fractionNearStart"])
        self.assertIsNone(caret["fractionPastEnd"])

    def test_a_caret_that_never_moved_is_not_two_positions(self):
        """Same column in both reads: the deltas cancel and nothing is claimed.

        This is the limit the surviving check already declares out loud -- "a
        caret pinned to a constant column reads the same as one that is never
        drawn".  Asserted here so that the declaration and the arithmetic
        cannot drift apart.
        """
        caret = caret_from_columns(read(6), read(6))
        self.assertEqual((caret["strokeGained"], caret["strokeLost"]), (0, 0))
        self.assertIsNone(caret["fractionNearStart"])
        self.assertIsNone(caret["fractionPastEnd"])

    def test_a_band_with_no_text_ink_is_not_measurable(self):
        """The pre-existing NOT_ESTABLISHED route, kept working."""
        blank = {"columns": [0] * WIDTH, "width": WIDTH,
                 "band": {"y": 0, "h": HEIGHT}}
        self.assertFalse(caret_from_columns(blank, blank)["available"])

    def test_a_full_height_column_is_a_border_not_a_glyph(self):
        """Finding 060's other half: the page frame is not the line's ink."""
        a, b = read(6), read(14)
        a["columns"][0] = b["columns"][0] = HEIGHT
        a["columns"][WIDTH - 1] = b["columns"][WIDTH - 1] = HEIGHT
        caret = caret_from_columns(a, b)
        self.assertEqual((caret["inkLeft"], caret["inkRight"]), (5, 15))


if __name__ == "__main__":
    unittest.main()

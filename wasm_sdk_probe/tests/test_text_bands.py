"""`text_bands` must not let a caret merge two lines into one.

Measured 2026-08-22: on the v3 artifact the recovery inducer read four bands,
on v4 it read three, with the first two merged across a ten-row gap. The
document, the fixture and the pre-inducer bands were identical. What changed
was finding 068's fix -- the caret is now drawn where it belongs instead of a
commit behind, which put it in that gap. The harness aims its drag from these
bands, so a correct caret moved the aim and the inducer stopped inducing.

The density filter already rejects a caret on its own (one pixel over a
one-pixel extent scores 1.0, above the 0.9 ceiling). What it could not do is
run before the merge.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from run_e2_c_product_path import text_bands, CARET_MAX_EXTENT  # noqa: E402


def scan_of(rows: dict[int, tuple[int, int, int]], height: int = 200) -> dict:
    """{y: (count, first, last)} for inked rows; every other row is blank."""
    counts, firsts, lasts = [0] * height, [-1] * height, [-1] * height
    for y, (count, first, last) in rows.items():
        counts[y], firsts[y], lasts[y] = count, first, last
    return {"counts": counts, "firsts": firsts, "lasts": lasts,
            "height": height}


def line(top: int, bottom: int, first: int = 80, last: int = 300,
         ink: int = 120) -> dict:
    return {y: (ink, first, last) for y in range(top, bottom + 1)}


class ACaretDoesNotMergeTwoLines(unittest.TestCase):
    def test_two_lines_with_a_gap_are_two_bands(self):
        """The control. Without it the test below proves nothing."""
        scan = scan_of({**line(20, 34), **line(50, 64)})
        bands = text_bands(scan)
        self.assertEqual([(b["top"], b["bottom"]) for b in bands],
                         [(20, 34), (50, 64)])

    def test_a_caret_in_the_gap_still_leaves_two_bands(self):
        caret = {y: (1, 150, 150) for y in range(36, 49)}
        scan = scan_of({**line(20, 34), **caret, **line(50, 64)})
        bands = text_bands(scan)
        self.assertEqual([(b["top"], b["bottom"]) for b in bands],
                         [(20, 34), (50, 64)],
                         "a one-pixel caret bridged the gap and merged the "
                         "lines, which is the defect this guard exists for")

    def test_the_excluded_run_is_reported_not_merely_dropped(self):
        """'The caret was here and was excluded' is a different statement from
        'there was nothing there', and only the first is checkable later."""
        caret = {y: (1, 150, 150) for y in range(36, 49)}
        scan = scan_of({**line(20, 34), **caret, **line(50, 64)})
        excluded = text_bands(scan)[0]["thinRunsExcluded"]
        self.assertEqual(excluded, [(36, 48, 1)])

    def test_an_anti_aliased_caret_two_columns_wide_is_still_excluded(self):
        # The caret is one pixel at a fractional x, so it lands on two columns.
        caret = {y: (2, 150, 151) for y in range(36, 49)}
        scan = scan_of({**line(20, 34), **caret, **line(50, 64)})
        self.assertEqual([(b["top"], b["bottom"]) for b in text_bands(scan)],
                         [(20, 34), (50, 64)])


class TheGuardIsNarrowerThanAnyRealLine(unittest.TestCase):
    # These use gaps WIDER than BAND_MERGE_GAP on purpose. The caret tests
    # above use narrow ones, because bridging a mergeable gap is the defect
    # they are about; here the question is only whether a narrow run survives
    # the extent filter, so the merge must be kept out of the answer.
    def test_a_narrow_line_of_text_survives(self):
        """The threshold must not eat a short line. The narrowest glyph on the
        fixture is about nine pixels, three times the ceiling."""
        narrow = line(50, 62, first=150, last=150 + 9, ink=6)
        scan = scan_of({**line(20, 34), **narrow, **line(80, 94)})
        tops = [(b["top"], b["bottom"]) for b in text_bands(scan)]
        self.assertIn((50, 62), tops,
                      "a nine-pixel-wide line was thrown away as a caret")

    def test_the_threshold_is_where_it_says_it_is(self):
        self.assertEqual(CARET_MAX_EXTENT, 3)
        # Extent CARET_MAX_EXTENT + 1: the first width that must NOT be taken
        # for a caret.
        survivor = line(50, 62, first=150, last=150 + CARET_MAX_EXTENT, ink=2)
        scan = scan_of({**line(20, 34), **survivor, **line(80, 94)})
        self.assertEqual(len(text_bands(scan)), 3,
                         "a run one pixel wider than the ceiling must survive")

    def test_and_one_pixel_narrower_is_taken_for_a_caret(self):
        """The pair that makes the threshold a measurement rather than a
        number: one either side of it, same geometry."""
        caret = line(50, 62, first=150, last=150 + CARET_MAX_EXTENT - 1, ink=2)
        scan = scan_of({**line(20, 34), **caret, **line(80, 94)})
        self.assertEqual(len(text_bands(scan)), 2)


if __name__ == "__main__":
    unittest.main()

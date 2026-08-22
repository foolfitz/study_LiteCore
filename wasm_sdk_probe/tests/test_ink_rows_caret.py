"""Finding 072: the drawn caret must leave the ink scan before rows are counted.

This runs the ACTUAL `INK_ROWS` string out of `run_e2_c_product_path.py` under
node, against a synthetic canvas, rather than re-implementing it here.  The
first remedy for this finding passed seven unit tests and changed nothing on the
page, because those tests were about a re-stated rule ("a thin standalone run is
dropped") and not about the string that runs in the browser.

The second version of THIS file made the same mistake one level down.  It drew
the caret as two columns of pure black and it read `INK_ROWS` off the disk with
a regex, and both of those hid a real defect:

  * `\\u0027` in the JS is a valid escape in JavaScript AND in Python, so the
    file parsed as JS while the string Python actually built had a bare
    apostrophe in it -- a SyntaxError in the browser, an empty scan, and every
    band-aimed check reading nothing.  Fixed by IMPORTING the constant.
  * the real caret is ONE nominal backing pixel wide at devicePixelRatio 1,
    drawn at fractional coordinates, so its alpha in a column is the product of
    the horizontal and vertical coverage.  The solidity test used to be taken
    over the sink's whole row window and declined on real geometry -- reporting
    "stale sink" at the caret it was looking straight at.  Two columns of pure
    black can never show that, so the fixture here renders coverage.

The fixture is the shape the finding measured: two lines of text ten rows
apart, and a caret standing in the gap.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_e2_c_product_path as probe  # noqa: E402

WIDTH, HEIGHT = 600, 400
# 400 rows, not 100.  A column is called a page border when it carries ink down
# more than 20% of the canvas, and on a 100-row canvas a 32-row glyph column
# clears that -- so the whole line was classified as border and the fixture
# measured nothing.  A real page is a thousand rows tall and its glyph columns
# score under 3%.
BAND_A = (10, 25)          # rows
GAP = (26, 35)             # rows -- ten of them, and text_bands() merges any
                           # separation of eight or fewer.  The separation it
                           # computes here is 36 - 25 = 11, so these two lines
                           # stay apart unless something bridges them.
BAND_B = (36, 51)          # rows
GLYPHS = (100, 400)        # columns
BORDERS = (50, 450)        # columns, inked down 45% of the height

# The caret, in the page's own terms.  `web/e2-editor-app.js` draws
# fillRect(x, y, max(1, round(scaleX * 15)), height) in BACKING pixels with
# fillStyle #1a1a1a, and at devicePixelRatio 1 on an A4 page that width rounds
# to ONE.  The coordinates are fractional because they come from twips.
CARET_X, CARET_W = 250.256, 1.0
CARET_Y, CARET_H = 24.125, 15.5942
CARET_INK = 26             # #1a1a1a


def _overlap(index: int, start: float, length: float) -> float:
    return max(0.0, min(index + 1, start + length) - max(index, start))


def _canvas(with_caret: bool = True, caret_x: float = CARET_X,
            caret_w: float = CARET_W) -> list[list[int]]:
    """The canvas as a sparse list of [x, y, channel] over a white page."""
    pixels: dict[tuple[int, int], int] = {}
    for low, high in (BAND_A, BAND_B):
        for y in range(low, high + 1):
            for x in range(*GLYPHS):
                # `(x + y)`, not `x`.  Keyed on the column alone, every third
                # column is inked down the WHOLE line height -- which makes the
                # fixture a picket fence of little carets, and an earlier
                # version of this file duly reported that a line of text was a
                # caret.  Text is dense per ROW and sparse per COLUMN; that
                # asymmetry is the whole reason a caret can be told from a
                # glyph, so the fixture has to have it.
                if (x + y) % 3 == 0:
                    pixels[(x, y)] = 0
    for x in BORDERS:
        for y in range(0, int(HEIGHT * 0.45)):
            pixels[(x, y)] = 0
    if with_caret:
        # Coverage antialiasing, the way a canvas fills a rectangle at
        # fractional coordinates: alpha is the product of the two overlaps, and
        # the channel is that alpha composited over what is underneath.
        for x in range(int(caret_x) - 2, int(caret_x + caret_w) + 3):
            fx = _overlap(x, caret_x, caret_w)
            if fx <= 0:
                continue
            for y in range(int(CARET_Y) - 1, int(CARET_Y + CARET_H) + 2):
                fy = _overlap(y, CARET_Y, CARET_H)
                if fy <= 0:
                    continue
                under = pixels.get((x, y), 255)
                alpha = fx * fy
                pixels[(x, y)] = round(under + (CARET_INK - under) * alpha)
    return [[x, y, value] for (x, y), value in pixels.items()]


def _run(pixels, sink, exclude=True, css=None) -> dict:
    """Run the shipped INK_ROWS over a stubbed canvas.

    `css` is the canvas's DISPLAYED size.  When it differs from the backing
    size the scan has to convert the sink's box, which is the arithmetic eight
    lines of comment in the source are about and which no arm exercised until
    an adversarial review pointed at it.
    """
    js = probe.INK_ROWS.replace("ARG_EXCLUDE_CARET",
                                "true" if exclude else "false")
    stub = """
const WIDTH = %(w)d, HEIGHT = %(h)d;
const CSS = %(css)s;
const data = new Uint8ClampedArray(WIDTH * HEIGHT * 4);
for (let i = 0; i < data.length; i += 4) {
  // An unpainted canvas reads (0,0,0,0); this one is painted white.
  data[i] = 255; data[i+1] = 255; data[i+2] = 255; data[i+3] = 255;
}
for (const [x, y, v] of %(pixels)s) {
  const i = (y * WIDTH + x) * 4;
  data[i] = v; data[i+1] = v; data[i+2] = v; data[i+3] = 255;
}
const sink = %(sink)s;
globalThis.document = { querySelector(selector) {
  if (selector === '#canvas') return {
    width: WIDTH, height: HEIGHT,
    getContext: () => ({ getImageData: () => ({ data }) }),
    getBoundingClientRect: () => ({ left: 0, top: 0,
                                    width: CSS[0], height: CSS[1] }),
  };
  if (selector === '#sink') return sink === null ? null : {
    getBoundingClientRect: () => sink,
  };
  return null;
} };
console.log(JSON.stringify(%(js)s));
""" % {"w": WIDTH, "h": HEIGHT, "pixels": json.dumps(pixels),
       "css": json.dumps(list(css or (WIDTH, HEIGHT))),
       "sink": json.dumps(sink), "js": js}
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(stub)
        path = handle.name
    try:
        done = subprocess.run(["node", path], capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)
    finally:
        pathlib.Path(path).unlink(missing_ok=True)


def _sink(caret_x: float = CARET_X, scale: float = 1.0) -> dict:
    """`#sink` where moveSinkToCaret would put it, in CSS pixels.

    The page rounds each edge separately and sets a HEIGHT rather than a
    bottom, so the box is reproduced that way rather than by dividing the
    backing rectangle.
    """
    left = round(caret_x / scale)
    top = round(CARET_Y / scale)
    height = max(1, round(CARET_H / scale))
    return {"left": left, "top": top, "right": left + 1, "bottom": top + height}


class InkRowsCaretTest(unittest.TestCase):

    def gap_ink(self, scan) -> int:
        return sum(scan["counts"][y] for y in range(GAP[0], GAP[1] + 1))

    def bands(self, scan) -> list[tuple[int, int]]:
        return [(b["top"], b["bottom"]) for b in probe.text_bands(scan)]

    # ---------------------------------------------------------------- the defect

    def test_the_caret_bridges_the_two_lines_when_it_is_left_in(self):
        """The defect itself, reproduced, IN THE UNIT THE FINDING IS ABOUT.

        Finding 072 is about a BAND COUNT, so this asserts a band count.  An
        earlier version of this file asserted ink in the gap and never called
        text_bands at all -- which meant raising BAND_MERGE_GAP to 12 would
        have made the remedy pointless while every test still passed.
        """
        scan = _run(_canvas(), _sink(), exclude=False)
        self.assertEqual(self.bands(scan), [(10, 51)])
        self.assertGreater(self.gap_ink(scan), 0)
        self.assertIsNotNone(scan["caret"])
        self.assertFalse(scan["caretRemoved"])

    def test_the_caret_is_taken_out_and_the_two_lines_come_apart(self):
        scan = _run(_canvas(), _sink(), exclude=True)
        self.assertEqual(self.bands(scan), [(10, 25), (36, 51)])
        self.assertEqual(self.gap_ink(scan), 0)
        self.assertTrue(scan["caretRemoved"])
        self.assertIsNone(scan["caretWhy"])

    def test_the_antialiased_ends_do_not_make_it_decline(self):
        """The defect an adversarial review found in the FIRST version of this.

        The bar is one nominal backing pixel wide at fractional coordinates, so
        its alpha in a column is the product of the horizontal and vertical
        coverage: on this geometry column 250 is dark for 14 rows inside a
        16-row sink window.  A solidity ratio taken over all sixteen wants 14.4
        and declines -- at the caret it is looking straight at -- and then
        reports a stale sink.  Taken over the interior rows it is 14 of 14.
        """
        scan = _run(_canvas(), _sink(), exclude=True)
        self.assertIsNotNone(scan["caret"])
        self.assertEqual(scan["caret"]["rowsTested"], 14)
        self.assertEqual(scan["caret"]["x"], 250)
        self.assertEqual(scan["caret"]["width"], 1)

    # -------------------------------------------------- what it must not remove

    def test_the_text_either_side_survives_the_exclusion(self):
        """Taking the caret out must not take the lines out with it."""
        with_caret = _run(_canvas(), _sink(), exclude=True)
        without = _run(_canvas(with_caret=False), _sink(), exclude=True)
        for low, high in (BAND_A, BAND_B):
            for y in range(low, high + 1):
                # The caret sat over a glyph column inside these rows, and that
                # glyph was painted over on the real canvas before the harness
                # ever read it -- so a small difference here is the truth, and
                # a large one would mean the exclusion ate a line.
                self.assertLessEqual(
                    abs(with_caret["counts"][y] - without["counts"][y]), 1,
                    f"row {y}")
            self.assertGreater(with_caret["counts"][low + 1], 50)

    def test_a_stale_sink_position_excludes_nothing(self):
        """paint() moves the sink only when it DRAWS a caret.

        During a range selection it draws none, so the sink sits where the
        caret last was.  Excluding that rectangle would delete real glyphs from
        the scan, so the pixels have to agree before anything is removed.
        """
        scan = _run(_canvas(with_caret=False), _sink(), exclude=True)
        self.assertIsNone(scan["caret"])
        self.assertFalse(scan["caretRemoved"])
        self.assertIn("stale sink", scan["caretWhy"])

    def test_a_line_of_glyphs_is_not_mistaken_for_a_caret(self):
        """The sink pointed at ordinary text: dense per row, sparse per column."""
        sink = {"left": GLYPHS[0] + 3, "top": BAND_A[0],
                "right": GLYPHS[0] + 4, "bottom": BAND_A[1] + 1}
        scan = _run(_canvas(with_caret=False), sink, exclude=True)
        self.assertIsNone(scan["caret"])

    def test_a_page_border_under_a_stale_sink_is_not_a_caret(self):
        """A border is inked down the whole page and passes any stroke test.

        With no caret drawn anywhere, a stale sink parked on -- or within the
        rounding slack of -- a border column used to report a caret found, with
        `caretWhy` null.  That field is the positive control for this remedy,
        so satisfying it with a page rule is worse than declining.
        """
        for offset in (0, 2, -2):
            with self.subTest(offset=offset):
                sink = _sink()
                sink["left"] = BORDERS[0] + offset
                sink["right"] = sink["left"] + 1
                scan = _run(_canvas(with_caret=False), sink, exclude=True)
                self.assertIsNone(scan["caret"], scan["caretWhy"])

    # ------------------------------------------------------ the coordinate math

    def test_the_sink_is_converted_from_css_pixels_to_backing_pixels(self):
        """devicePixelRatio 2: the sink's box is half the backing rectangle.

        Every earlier arm ran with the displayed size EQUAL to the backing
        size, so the conversion -- eight lines of comment in the source -- was
        never executed with a scale of anything but one.
        """
        scan = _run(_canvas(), _sink(scale=2.0), exclude=True,
                    css=(WIDTH / 2, HEIGHT / 2))
        self.assertIsNotNone(scan["caret"], scan["caretWhy"])
        self.assertEqual(scan["caret"]["x"], 250)
        self.assertEqual(self.bands(scan), [(10, 25), (36, 51)])

    def test_the_bar_is_found_when_the_sink_lands_columns_off(self):
        """CSS pixels are rounded; backing pixels are what was drawn.

        Converting the sink's box back can miss by 0.5*devicePixelRatio + 0.5
        columns -- two on this harness's own ratio-3 arm.  If the search had to
        be exact it would decline there and look exactly like a page with no
        caret on it.
        """
        for offset in (-3, -2, -1, 1, 2, 3):
            with self.subTest(offset=offset):
                sink = _sink()
                sink["left"] += offset
                sink["right"] += offset
                scan = _run(_canvas(), sink, exclude=True)
                self.assertIsNotNone(scan["caret"], scan["caretWhy"])
                self.assertEqual(scan["caret"]["x"], 250)
                self.assertEqual(self.bands(scan), [(10, 25), (36, 51)])

    # ------------------------------------------- when there is nothing to remove

    def test_a_bar_that_fell_between_two_columns_is_not_ink_and_not_a_bridge(self):
        """The other half of the one-pixel-wide problem.

        A 1px fill centred on a column boundary splits into two half-covered
        columns, and neither reaches the darkness threshold.  There is then no
        caret to find -- and, crucially, nothing bridging the two lines either,
        so declining is the right answer rather than a missed remedy.  This is
        also why finding 072 is INTERMITTENT and why a single run that shows
        the lines apart is not evidence that the remedy fired.
        """
        pixels = _canvas(caret_x=250.5)
        scan = _run(pixels, _sink(caret_x=250.5), exclude=True)
        self.assertIsNone(scan["caret"])
        self.assertEqual(self.gap_ink(scan), 0)
        self.assertEqual(self.bands(scan), [(10, 25), (36, 51)])

    def test_no_sink_at_all_is_reported_rather_than_assumed(self):
        scan = _run(_canvas(), None, exclude=True)
        self.assertIsNone(scan["caret"])
        self.assertIn("#sink", scan["caretWhy"])
        self.assertEqual(self.bands(scan), [(10, 51)])


if __name__ == "__main__":
    unittest.main()

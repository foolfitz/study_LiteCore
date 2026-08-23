# Finding 075 — the accessibility core writes uninitialised memory into the
# canvas margins, and the harness reads 31 of those pixels as text

Captured 2026-08-23 by `wasm_sdk_probe/tools/capture_canvas_edges.py`, one run
per core, two shots per run. The two cores differ in the core build only: the
probe engine sources and the shell are identical, and `a11y-gate0` carries no
engine change from this round at all.

## Files

| file | what it is |
|---|---|
| `e2-editor-v4-at-rest.png` | shipped core, freshly opened, before any caret |
| `e2-editor-v4-after-caret.png` | shipped core, one caret placement later |
| `a11y-gate0-at-rest.png` | accessibility core, same moment |
| `a11y-gate0-after-caret.png` | accessibility core, one caret placement later |
| `*-top-2x.png` | rows 0-140 of the after-caret shots at 2x, where it is visible |
| `*-capture.json` | band counts measured live beside each shot |

Open the two `-top-2x.png` side by side. On the shipped core the area around
the page is flat. On the accessibility core it is coloured noise.

## What the pixels say

Off-page columns only (x < 14 and x >= 710), 26,941 pixels per shot:

| shot | alpha == 0 | alpha > 128 | passes the ink test | distinct alphas |
|---|---|---|---|---|
| v4 at rest | 21,563 | 0 | 0 | 47 |
| v4 after caret | 21,595 | **0** | **0** | 33 |
| a11y at rest | 21,559 | 3 | 0 | 46 |
| a11y after caret | 19,236 | **290** | **31** | **184** |

The shipped core's surround is TRANSPARENT, so the harness's ink test
(`alpha > 128 && r,g,b < 100`) never sees it. The accessibility core's surround
after a repaint is uninitialised memory: alpha takes 184 different values, 290
pixels come back opaque, and 31 of those are dark enough to be ink.

The PNG is the cheapest tell: same document, same dark-pixel count (4,368 vs
4,424), and the accessibility shot is **90,538 bytes against 42,434**. Noise
does not compress.

## How 31 pixels lose two paragraphs

They land one to three per row in the gaps BETWEEN lines, at both margins.

1. `text_bands()` merges runs separated by <= 8 rows. The gap between the first
   two lines drops from 12 rows to 2, so they merge into one 40-row band.
2. The band's horizontal extent is taken from the outermost ink in it, which is
   now a margin pixel: 157 columns becomes 634.
3. `density = maxInk / extent` = 84 / 634 = **0.133**, just under the 0.15
   floor, and the band is discarded without appearing in the return value.

Nine paragraphs, nine bands, seven reported. Every check that aims by band
index then aims a paragraph off; `format_arm` presses a toggle once and relies
on alternation, so bold comes back INVERTED rather than absent.

**The ink never disappeared and neither did the text.** `inkAtTopBand` is true
at +4, +8 and +16 seconds. What was lost was the classification.

## Why the exclusion that exists did not fire

`INK_ROWS` already clips to the page, using columns inked DARK down more than
20% of the canvas height. Replayed offline against all four canvases, that test
finds **one** column and `clipped` is **false** every time, on both cores in
both states. It has been inert on this fixture throughout; the shipped core was
safe for an unrelated reason.

## The remedy, and why it is not a threshold tuned to this data

The page is drawn OPAQUE and its surround is not, in both states on both cores.
Clipping to the outermost columns that are more than 20% opaque:

| shot | bands, before | bands, after |
|---|---|---|
| v4 at rest | 9 | 9 |
| v4 after caret | 9 | 9 |
| a11y at rest | 9 | 9 |
| a11y after caret | **7** | **9** |

All four canvases agree on the same page range, **15..709**. Page columns are
at least 96.9% opaque; off-page columns reach at most 7.6% even with the
garbage in them — 13x of daylight in the worst case, against 968,783,638x on
the shipped core, where the surround is exactly transparent.

On the shipped core it drops **0** pixels on every canvas measured. That is not
a hope about a threshold, it is what "the surround is transparent" means.

`BAND_MERGE_GAP` and the density floor are unchanged. Moving either would have
been fitting the instrument to one core's noise.

## What is NOT established here

* **That accessibility causes it.** The core build under test is
  `--with-wasm-module writer calc` with accessibility left in; the shipped one
  is writer-only with accessibility stripped. Two differences, one measurement.
  Calc changing the heap layout is not excluded.
* **Whether a user sees it.** The garbage is in the canvas, so a human looking
  at this build should see coloured noise around the page. Nobody has looked
  yet. That is a question for the operator, not for another probe.
* **Whether the product is otherwise sound on this core.** This explains why
  the harness is red. It does not make the product green.

## Repeats, 2026-08-23 — and a positive control that is NOT in them

`capture_canvas_edges.py --after-action set-paragraph-heading`, five rounds per
core, three states each:

| core | n | at rest | after a caret | after the edit |
|---|---|---|---|---|
| `e2-editor-v4` (shipped) | 5 | 9 x4, **10 x1** | 9 x5 | 9 x5 |
| `e2-editor-v5` (accessibility) | 5 | 9 x5 | 9 x5 | 9 x5 |

The accessibility core is 15/15. The one anomalous count belongs to the SHIPPED
core, at rest — so the `bands: 10 for 9 lines` seen once in a product-path run
is a repaint caught in flight, which `stable_bands` can still miss when two
successive scans agree on a shape that is itself mid-repaint. That is a named
limit of the instrument, not a property of either core.

**These 30 cells do not demonstrate that the page clip works.** `offPageInk` is
0 in every one of them: the garbage did not occur during any of these runs, so
the exclusion was never exercised. What they show is that the band count is
stable, which is a different claim.

The positive control for the clip is offline, on the canvas that DOES carry the
garbage (`a11y-gate0-after-caret.png`, 31 dark off-page pixels): replaying the
classification with the clip on gives 9 bands and with it off gives 7. One
canvas, one difference, both directions measured.

The garbage is therefore INTERMITTENT as well. Its rate is not established --
it was present in the two captures taken for this finding and absent in the ten
taken afterwards, and nobody has looked for what makes the difference.

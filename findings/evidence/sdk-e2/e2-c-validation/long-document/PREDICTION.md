# Long documents: where the wall is, predicted before anything was measured

Written 2026-08-19. **No arm of the sweep described here has been run.** The
corpus generator, the canvas-limit probe and the runner cell do not exist yet;
this file is committed first so the numbers below can be wrong in public.

Subject: the shipped product page (`web/e2-editor.html` + `web/e2-editor-app.js`)
on shell v17, artifact `d538ce0b91478426…`. The question the checklist row
`edit-a-real-length-document` asks is not "can it do twenty pages" — it is
**where does it stop, and does it say so**.

## The arithmetic, and where each input comes from

`layoutCanvas()` (`web/e2-editor-app.js:158-172`):

```
cssWidth      = min(desk.clientWidth - 40, 900)
backingWidth  = min(MAX_BACKING_WIDTH, round(cssWidth * devicePixelRatio))
canvas.height = round(backingWidth * heightTwips / widthTwips)
```

`MAX_BACKING_WIDTH` is 2400 (`:53`).

`heightTwips` is the height of the WHOLE DOCUMENT, not of one page. Confirmed in
core's source: `doc_getDocumentSize` (`desktop/source/lib/init.cxx:4572`) →
`SwXTextDocument::getDocumentSize` (`sw/source/uibase/uno/unotxdoc.cxx:3396`) =
`GetDocSize() + 2 * DOCUMENTBORDER`, and the layout stacks pages in one column
with a gap between each (`sw/source/core/layout/pagechg.cxx:2423`).

There is already a measurement to calibrate it with, from a round that was
asking something else: `findings/evidence/sdk-r6/discovery/summary.json` records
1 page at 17,406 twips and 22 pages at 376,968 twips. That is **17,122 twips per
additional page**, against A4's own 16,838 — so the gap is real and A4's paper
size is the wrong number to compute with.

Per-page height ratio used below: `17,122 / 12,459 = 1.374` canvas pixels of
height per pixel of width, per page.

**This harness's own viewport** is the other input, and it is not a free
parameter: `list-contexts` was measured at a backing width of **725 px** at
devicePixelRatio 1 on 2026-08-19, so `desk.clientWidth` is about 765 and the
900 cap never binds here.

## Prediction 1 — the dimension wall, per devicePixelRatio

Assuming a per-dimension canvas cap of 32,767 px (the value both engines are
widely said to use — **to be measured locally, not cited**):

| devicePixelRatio | backingWidth | canvas height per page | wall (pages) |
|---|---|---|---|
| 1 | 725 | 996 | **32.9** |
| 2 | 1450 | 1,992 | **16.4** |
| 3 | 2175 | 2,988 | **11.0** |
| 4 | 2400 (capped) | 3,297 | **9.9** |

**The wall moves by a factor of 3.3 across ordinary displays, and the harness
stands on the most forgiving square.** Measuring only at dpr 1 in headless would
record a 33-page wall for a user who hits one at 10. This is the harness-path /
user-path shape again, and it is why this cell must sweep dpr rather than
report a single number.

## Prediction 2 — which wall arrives first

Four candidates, and they are ordered here on purpose:

1. **Stale geometry after reflow — fires FIRST, and at every length.**
   `DocumentHandle.heightTwips` is assigned once, from the open metadata
   (`sdk/document-sdk.js:374`). `document-invalidated` calls `renderDocument()`
   and nothing else (`web/e2-editor-app.js:622-623`): no metadata re-read, no
   `layoutCanvas()`. So after any edit that changes the page count, the canvas
   and the render region both describe the document as it was when it was
   opened. **Predicted: an edit that adds a page leaves the new page undrawn,
   at ANY document length, including two pages.** This wall has no threshold,
   which is why a test that only types at the top of a one-page fixture would
   never see it.

2. **Redraw latency — arrives well before any dimension limit.** Every edit
   repaints the whole document (`renderDocument()` renders one region covering
   it all). Cost is linear in page count. Pre-registered threshold below.

3. **Tile allocation.** `render()` must return `backingWidth * canvasHeight`
   RGBA bytes. At dpr 1 and 33 pages that is 725 x 32,767 x 4 = **95 MB**; at
   dpr 4 and 10 pages, 2400 x 32,767 x 4 = **314 MB** — through a WASM heap.
   Predicted to fail *before* the dimension cap at dpr >= 2.

4. **The canvas dimension cap itself.** Predicted to be reached only at dpr 1,
   because 3 is predicted to bite first everywhere else.

## Prediction 3 — the latency threshold, registered before the measurement

The number a user feels is **keystroke to visible ink**. Registered now:

* **Threshold: 1,000 ms.** Above it this cell is RED regardless of whether the
  document still renders. `renderDocument()` allows itself a 60-second timeout,
  so without a pre-registered number this cell would pass while every keystroke
  took half a minute.
* **Slope: linear in pages.** A full-document repaint per edit is linear; if
  the measurement comes back super-linear, something worse than the obvious is
  happening and that is its own finding.
* **Predicted per-page cost at dpr 1: 150-250 ms.** Basis: the 1-page fixture's
  own measured operation latencies on this artifact are tens of milliseconds for
  a caret move and about 200 ms for a save, and a full render is the expensive
  end of that range.
* **Therefore predicted usability wall: 4 to 7 pages at dpr 1** — five times
  earlier than the dimension wall in Prediction 1, and earlier still at higher
  dpr.

If the per-page cost comes back below 25 ms, Prediction 3 is wrong and the
latency wall is not the first one; say so plainly rather than rescuing it.

## What the cell will judge (not "twenty pages must work")

Two things, both of which can fail on their own:

* **Honesty.** At a length where rendering has broken, the product must SAY so.
  Handing back a blank or truncated canvas in silence is a failure. Finding 058
  is the precedent: data arriving is not the same as anything being drawn, and
  nine checks stayed green on a page that painted nothing.
* **Usability.** The 1,000 ms threshold above.

If the measurement shows a silent failure, that is a finding of its own and this
cell is declared KNOWN_RED against it — it may not be `done`.

## Falsifier for the cell itself

Shrinking `MAX_BACKING_WIDTH` must MOVE the measured wall, and the cell must
follow it. A cell that reports the same page count with a different backing
width is measuring a constant somebody typed, not a wall.

## What this file does NOT predict

* The local canvas cap. It is to be measured by bisection in both browsers on
  this machine; the 32,767 above is used only to make Prediction 1 concrete and
  is flagged wherever it is used.
* Firefox. Every number here is Chrome's. Finding 014 was mis-attributed to
  Firefox for six days; nothing in this file may be read as describing it.

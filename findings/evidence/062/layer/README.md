# Finding 062 — which layer loses the pixels

Round of 2026-08-19, Chrome, the **shipped artifact** (`d538ce0b91478426…`)
served from a symlink mirror of `dist/` so the engine, worker and wasm are byte
for byte the ones the product loads.

The question this answers was the only thing standing between finding 062 and a
fix: above a canvas height of about 32,767 the product paints a blank page and
reports success, and from the product's seat that is consistent with the engine
returning an empty tile OR the page losing a good one. **Which one it is decides
whether the fix needs a link**, and 040 and 048 are why it was measured instead
of named.

## Answer: the page side. No link is needed.

Every step of the chain was asked separately, on the same artifact, at heights
straddling the wall.

### 1. The engine returns a correct tile, with ink, at every height

`tools/run_f062_render_limit.py` calls `document.render()` directly, through the
same engine factory the product uses (`web/e2-editor-app.js:585`), on a 17-page
document (291,358 twips tall):

```
31048: 725x31048 bytes=90039200 (expected 90039200) dark=70505 imageData=true
32590: 725x32590 bytes=94511000 (expected 94511000) dark=76569 imageData=true
32767: 725x32767 bytes=95024300 (expected 95024300) dark=69203 imageData=true
32768: 725x32768 bytes=95027200 (expected 95027200) dark=69203 imageData=true
32889: 725x32889 bytes=95378100 (expected 95378100) dark=69203 imageData=true
34847: 725x34847 bytes=101056300 (expected 101056300) dark=63458 imageData=true
```

Every buffer is exactly `width x height x 4` bytes, every buffer carries dark
pixels, nothing throws, and `new ImageData(...)` builds from all of them —
including at 34,847, which is well past the height at which the product goes
blank on the very same document.

Six renders in one session, at increasing sizes, all correct: so this is not a
first-render result that a later one would contradict.

### 2. `putImageData` paints them, attached or detached

Same round, per height, on a fresh canvas of the tile's size:

```
31048  detachedCols=694  attachedCols=694
32590  detachedCols=694  attachedCols=694
32767  detachedCols=489  attachedCols=489
32768  detachedCols=489  attachedCols=489
32889  detachedCols=489  attachedCols=489
34847  detachedCols=489  attachedCols=489
```

`Cols` is the number of inked columns in the top 400 rows. It steps from 694 to
489 because a fixed document stretched over a taller canvas puts fewer lines in
the top strip — that is the content moving, not the paint failing. **Nothing is
blank.** Both variants were measured because the first version of this probe
tested only a detached canvas, which would have left "the product's canvas is
attached and displayed" as an untested difference.

### 3. The product's own canvas, in its blank state, takes pixels fine

`tools/probe_f062_product_canvas.py` drives the product until the canvas is
blank, then paints a solid block onto **that same canvas** from the harness:

```
pages=17  canvas=725x16934  productInkCols=694  harnessFill dark=36270 of expected 36250
pages=35  canvas=725x34847  productInkCols=1    harnessFill dark=36250 of expected 36250
```

At 35 pages the product's own ink is **one column** — blank — and a block
painted by the harness lands **36,250 of 36,250 expected pixels**, exact.

## What that leaves

* the engine produced a correct tile ✓
* `ImageData` built from it ✓
* `putImageData` painted it onto a canvas that size ✓
* the product's canvas accepts pixels at that size ✓
* **the product never put the tile there** ✗

So the defect is in the product page's own render-and-paint path. It is
shell/page-side, it needs no relink, and it does not belong in the blocked link
queue.

## What is still NOT established — the step

This round says *which layer*, not *which line*. Two candidates, both named as
candidates because neither has been measured:

* `paint()` returns early on `if (!lastTile) return;`, and `layoutCanvas()` sets
  `lastTile = null` (`web/e2-editor-app.js:171`). Anything that re-runs
  `layoutCanvas()` after a render clears both the canvas and the cached tile —
  and a canvas tens of thousands of pixels tall changes whether the desk has a
  scrollbar, which changes `el.desk.clientWidth`, which is what `layoutCanvas()`
  reads.
* `renderDocument()` coalesces with `renderAgain`, so a repaint that arrives
  while one is in flight replaces rather than follows it.

Naming either without measuring it would be the thing this round exists to
avoid. The follow-on is `queue-long-document-blank-page-is-page-side`.

## Files

* `render-limit.json` — the full per-height report from the SDK probe
* `product-canvas.txt` — the product-canvas fill test

## Not established

* **Firefox.** Every number here is Chrome's.
* **Whether the same holds after editing.** Both probes render a freshly opened
  document; the product's blank state was reached the same way, so nothing here
  depends on an edit, but nothing here rules out a second mechanism that only
  appears after one.

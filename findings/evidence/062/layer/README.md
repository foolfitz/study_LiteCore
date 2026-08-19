# Finding 062 — which layer loses the pixels

> **CORRECTED 2026-08-19, same day.** The first version of this file concluded
> **page side**. That was wrong, and the way it was wrong is worth more than the
> conclusion was: every probe run swept an ASCENDING LADDER of canvas heights
> inside one engine session, so the first render was always below the limit and
> painted, and the later over-limit renders came back carrying content. Asking
> for a single over-limit height in a cold session — which is what the product
> actually does — returns an unpainted buffer every time.
>
> **The answer is the ENGINE side**, and the limit is exactly 2^15 - 1.
> The superseded reasoning is kept at the end, because the mistake is the
> reusable part.

Round of 2026-08-19, Chrome, the **shipped artifact** (`d538ce0b91478426…`)
served from a symlink mirror of `dist/` so the engine, worker and wasm are byte
for byte the ones the product loads.

## The answer

**A cold render of a tile taller than 32,767 px comes back correctly sized,
entirely zero, and reported as a success.**

One render per page load, nothing before it:

| width | height | buffer | painted |
|---|---|---|---|
| 362 | 32,767 | 45.2 MB | **yes** — 41,762 dark, 347 inked columns |
| 362 | **32,768** | 45.2 MB | **no** — 0 dark, 0 columns |
| 362 | 32,800 | 45.3 MB | no |
| 362 | 34,847 | 48.1 MB | no |
| 362 | 65,000 | 89.8 MB | no |
| 725 | 32,767 | 90.6 MB | **yes** — 70,209 dark, 694 inked columns |
| 725 | 34,847 | 96.4 MB | no |
| 725 | 65,000 | 179.8 MB | no |

**It is the HEIGHT, not the size.** The two widths flip at the same height while
their buffers differ by a factor of two — 45 MB paints at 32,767 and 45 MB is
blank at 32,768. A memory ceiling cannot do that. 32,767 = 2^15 - 1.

Every one of these is the first render in a fresh worker. The buffer always
comes back at exactly `width x height x 4` bytes, `new ImageData(...)` always
builds from it, and `render()` never throws or reports an error.

## It is not the page, and each page-side step was measured separately

* **The product's paint is faithful.** Wrapping
  `CanvasRenderingContext2D.prototype.putImageData` from the harness shows the
  product handing the canvas a 725x34,847 image of **101,056,300 bytes with
  2,105,295 of 2,105,340 sampled pixels fully transparent** — it paints exactly
  the nothing it was given. At 16,934 the same wrapper shows 13,544 dark pixels
  in and 13,544 on the canvas afterwards.
* **The canvas is not at fault.** With the product sitting in its blank state, a
  block painted onto that same canvas by the harness lands 36,250 of 36,250
  expected pixels.
* **The request is not at fault.** Wrapping `Worker.prototype.postMessage`
  shows the product sending
  `{"operation":"paint","payload":{"documentHandle":1,"xTwips":0,"yTwips":0,"widthTwips":12474,"heightTwips":599554,"canvasWidthPx":725,"canvasHeightPx":34847}}`
  — byte for byte the request this evidence's own probe sends.
* **Not the canvas element's own cap**, which was measured at 65,535 in both
  Chrome and Firefox (`tools/probe_canvas_limit.py`).

## What follows for the fix

The defect is engine-side, but **the product does not have to wait for a link**:
nothing forces it to ask for one tile as tall as the whole document. Rendering
in strips no taller than 32,767 — or using the `TileScheduler` that
`editor-session.js` already imports — avoids the limit entirely and is a
page-side change.

So this does not block the next link. What it does mean is that "the engine
paints anything you ask for" is not true, and the page is the only place that
currently knows how tall a request it is making.

## Not established

* **Where in the engine.** That a 2^15 boundary in a paint path is a signed
  16-bit quantity is an inference from the number, not a measurement; nothing
  here reads core or the engine's source at that point.
* **What a warmed session actually returns above the limit.** After smaller
  renders in the same session, an over-limit render comes back with non-zero
  content — and its top-strip inked-column count is *identical* to the previous,
  smaller render (464 and 464, where a fixed document at different heights
  otherwise gives 694 / 443 / 464). That is consistent with a reused buffer that
  was never repainted, i.e. a silently STALE image rather than a blank one,
  which would be a worse defect than this one. Suggestive; not established.
* **Firefox.** Every number here is Chrome's.

## Files

* `render-limit.json` — the per-height report from the first (laddered) round
* `product-canvas.txt` — the product-canvas fill test

## Superseded: why the first version said "page side"

It ran `tools/run_f062_render_limit.py` with a list of heights and rendered them
in ascending order **in one session**, starting below the limit. Every arm came
back inked, including the over-limit ones, so the engine looked innocent and the
loss looked page-side. Three page-side steps were then measured and each was
fine, which made the conclusion feel well supported — it was well supported and
wrong, because the thing it exonerated had been warmed up by the probe's own
earlier arms.

**The reusable lesson: a probe that sweeps a parameter inside one session can
carry state between its arms, and an ascending sweep is exactly the order that
hides a cold-start limit.** The control that broke it open was one render per
page load. The same shape appears in this tree's own history — a probe that
killed the thing it was observing (finding 038) — and it is worth the same
suspicion here: *what did my earlier arms do to the thing this arm is asking?*

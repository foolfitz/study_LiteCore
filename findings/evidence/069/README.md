# The input sink at the bottom of the document

Arm `sink-does-not-drag-the-page`
(`wasm_sdk_probe/tools/probe_064_format_reaches_typing.py`), Chrome,
2026-08-22. `evidenceClass: "diagnostic"`.

## What it measures

`#sink` is the hidden `<textarea>` that receives keystrokes. It was
`position: absolute` with **no `top`/`left`**, so it sat at its static position
— directly after a `<canvas>` the height of the whole document. When an IME
begins composing, the browser scrolls the focused element into view, and that
took the whole desk to the bottom of the page.

## Result

| | sink `top` | scrolling it into view consumes |
|---|---|---|
| parked at its old static position (control) | **929** = canvas height | **99.5%** of the scrollable room |
| with the fix | **228** = the caret | **15%** |

The remaining 15% is not the defect. The desk in this run is 139px tall and
the caret is 228px down, so it is genuinely below the fold; scrolling to it is
what an editor should do.

## The criterion is a fraction, and the first version was a pixel count

The check originally demanded the fixed case scroll less than **50px**. It
scrolled **125** and the arm said FAIL — correctly by its own rule, and
uselessly. A pixel threshold cannot separate "scrolled to the caret" from
"scrolled past it to the end of the document"; where the scroll lands as a
fraction of the available room separates them cleanly (15% against 99.5%).

Recorded because the failing version is the useful part: the first run of a new
check is worth what it is red about, and this one was red about its own
threshold rather than about the product.

## The control is a mutation, not a second reading

`top: auto` puts the sink back at its static position and the same scan must
then report the drag. Without it, "the page did not scroll" and "this arm
cannot see scrolling" are the same green — and the arm returns
`NOT_ESTABLISHED`, not `PASS`, when the control fails to fire.

## Files

- `f069-sink.json` — the run with the pixel-count criterion (FAIL, and the
  reason the criterion changed)
- `f069-sink1.json`, `f069-sink2.json` — the fraction criterion, both PASS with
  the control firing at 99.5%

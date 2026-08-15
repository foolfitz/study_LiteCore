# E2-C phase D3 — the list cells, and which round is which

Predictions were registered in `PREDICTION.md` before the harness existed, and
`PREDICTION-caret.md` records the caret arm that had to be measured before any
of the list cells could be scored.  `tools/analyze_e2_c_d3.py` applies the
criteria offline; the page judges nothing.

| directory | what it is | usable as evidence for |
|---|---|---|
| `e2-editor-v2-572035ac/` | the FIRST execution, `before=save`.  Every cell died `stage-deadline:awaiting-selection` without dispatching | finding 047 |
| `run-1b-before-skip/` | the second, `before=skip`.  Dispatched, but all eight cells acted on the document's FIRST paragraph | finding 048 |
| `caret-probe/` | the caret arms: unpainted, painted, after a real selection, four fixed settles, and the polled latency | finding 048 (see `findings/evidence/048/README.md`) |
| `run-2/` | the list cells positioned by a zero-width `selectRange`, Chrome and Firefox | the eight predictions |
| **`run-3/`** | **the canonical round**: the PRODUCT's click, with the landing proved by a readback before dispatch, Chrome and Firefox | **the eight predictions** |

`run-3` is canonical because SPEC E2-C 9.5.6 measured that the gesture changes
the answer -- a caret formed by a zero-width `selectRange` and a caret formed by
a click are different states as far as the format barrier is concerned.  A phase
that drives the product's paths with the non-product gesture measures a
different product.  `run-2` is kept because it is the independent check.

## What the rounds agree on

All nine saved documents -- the eight cells plus the `L6C` no-action control --
have byte-identical `<office:body>` across `run-2` (both browsers), `run-3`
(both browsers) and `caret-probe/click-poll`.  Two positioning gestures, two
browsers, five rounds, one answer.

Six of the eight predictions held.  L2 and L5 are recorded as FAILED predictions
with acceptable behaviour: both are the same adjacency rule -- a paragraph joins
an adjacent list of the type it was asked for, and opens a new one when there
is none -- which nobody had written down beforehand.  Scoring them as passes
because the behaviour is reasonable would be deciding after the round what we
had predicted.

L7 is the cell SPEC E2-000 section 10's stop condition points at (a list switch
causing silent ODT structure loss).  It did not fire: the list split, all three
items survived, and the second fragment carries
`text:continue-numbering="true"`.  Every cell reports `textLost: []`.

## The caret gate

Each cell records the caret rectangle before and after the positioning gesture
and refuses to dispatch when the caret is not within half a line pitch (195
twips) of the anchor; the analyzer recomputes that from the recorded rectangle
rather than trusting the page's boolean.  Pointed at `run-1b-before-skip`, it
refuses all eight cells -- including the four that reported
`verified-format-readback` -- which is the check working on the data that
motivated it.

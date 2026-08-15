# Predictions for the product fix's acknowledgement signal

Registered 2026-08-16, before `web/e2-c-caret-ack-app.js` existed.

## Why this is being measured

The fix for finding 048 must replace a predicate that does not depend on the
click with one that does.  Two candidate signals are available to the PRODUCT
profile (the `editor-state` push event carries `source: "visible-cursor"`, but
the worker forwards it only when `editorDiscoveryEnabled()`, so the product
cannot subscribe to it):

* **geometry** -- compare the caret rectangle against the clicked point.  Cannot
  be made airtight: the measured landings sit up to 119 twips ABOVE the caret
  rectangle's top, so the click point can fall in the gap between two line
  boxes, and the previous line's box extended by that much would swallow it.  A
  rule loose enough to accept every real landing also accepts the line above.
* **acknowledgement** -- `sourceSequence`, which the engine increments for every
  callback that changed editor state, and which IS in the product's
  `editorGetStateV2` result.  If every click produces one, then "wait for the
  sequence to advance" is exact and needs no geometry at all.

The acknowledgement signal is only usable if it fires even when the click does
not move the caret.  Otherwise a click on the line the caret is already on would
wait out the whole deadline.

## Predictions

| # | claim | confidence |
|---|---|---|
| P-A1 | A click that lands on a DIFFERENT line advances `sourceSequence` | high |
| P-A2 | A click that lands on the line the caret is ALREADY on also advances it -- LOK re-emits the cursor rectangle whenever the cursor is set, not only when it moves | **medium-high** |
| P-A3 | An idle session with no input does not advance `sourceSequence` | high |
| P-A4 | The advance per click is small and bounded (1-3), not a stream | medium |

## What each answer means

* **P-A2 holds** -- the fix is "click, then wait for the sequence to advance",
  with no geometric constant anywhere, and the caret you read afterwards is the
  click's result whatever it is.
* **P-A2 fails** -- the acknowledgement cannot distinguish "the click did
  nothing because it was already there" from "the click has not been processed",
  and the fix has to combine signals: accept immediately when the pre-click
  caret already covers the clicked point, otherwise wait for the change.  That
  is weaker, and the weakness has to be written into the product, not hidden.
* **P-A3 fails** -- `sourceSequence` moves on its own, so an advance is not
  evidence of anything and the whole approach is out.

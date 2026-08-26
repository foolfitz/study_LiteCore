# Prediction, written while the run was in flight and before its report was read

Written 2026-08-26, after widening the worker's `productFormatBarrier`
projection and starting the run, before opening its output.

## Why this can be answered without touching the engine

The engine's barrier payload already carries `readback.html` — the markup of
the selection the postcondition read described — and the containment geometry
(`selectionTop`, `selectionBottom`, `restoreCentre`). **JavaScript throws them
away**: `productFormatBarrier` in `sdk-worker.js` is an allowlist, and its own
comment says "this allowlist is where engine fields go to be forgotten".

So finding 082's open question ("which paragraph did the readback describe")
needs no fingerprints in the payload and no relink. It needs the projection
widened in a mirror, which is what `--barrier-details-diagnostic` now also does
(in the **profile's** worker, which is the copy the page loads).

## The mechanism this is testing

`postFormatBarrierRestore()` clicks at a **document coordinate captured before
the dispatch** — `restorePoint.y + height/2`, the middle of the caret's line box
as it was — and only then does `.uno:SelectText` select "the paragraph". The
engine's own comment beside it says the residual out loud:

> "the point is in document coordinates and the dispatch may have changed the
> paragraph's height or indent, so an extreme reflow could still land
> elsewhere."

`set-paragraph-body` on a heading makes that paragraph **shorter**. Half of the
old heading's line height, measured from the old top, can therefore land below
the shrunken paragraph — in the next one.

That also explains the arm that passes: `set-paragraph-heading` makes the
paragraph **taller**, so the old mid-line point is still inside it.

And it explains why `containment` HELD while the identity gate fired: the
containment check asks whether the selection covers the restore point, and if
the restore point moved into the next paragraph then the selection of *that*
paragraph contains it by construction. Containment cannot see this failure; the
identity gate is the only thing that can.

## What the widened payload should show, on the `內文` arm

1. **`engineRaw.readback.html` does NOT contain `E1-LC-HEADING`** — the marker of
   the paragraph the action was dispatched on. Most likely it contains
   `E1-LC-ISOLATED`, which is the next paragraph down and the one arm 1 has just
   turned into a heading.
2. `engineRaw.containment.restoreCentre` sits between `selectionTop` and
   `selectionBottom` (containment held, so this is near-tautological) — the
   point is that those two describe a *different* band from the dispatch
   paragraph's.
3. `engineRaw.dispatchSelectionCollapsed` is `true`: the caret was collapsed
   when the action went out, so this is not a range-route artefact.
4. `engineRaw.stage` is `awaiting-restore` (the barrier got all the way to the
   verdict; it did not time out).

## What would refute it

**`readback.html` containing `E1-LC-HEADING`.** Then the read really was of the
right paragraph, the two fingerprints differ for some other reason, and the
suspect becomes the fingerprint derivation or the a11y focus — not the restore
geometry. The finding would have to be rewritten, not extended.

A weaker refutation: `readback.html` empty or absent, which would mean the
projection reached the page but the engine never recorded the markup — no
answer either way, and the next step would be the engine after all.

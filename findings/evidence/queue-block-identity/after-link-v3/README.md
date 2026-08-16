# After the v3 link — one half works, and the other half was never switched on

Artifact `4dbe9b74d3c55f92…` (linked 2026-08-17), shell bundle v11
`3425b311…`, Firefox.  Judged by
`tools/analyze_block_identity_link.py` (self-test: 10 checks) against the
predictions registered **before** the link, in
[`research/DESIGN-2026-08-16-caret-by-block-and-offset.md`](../../../../research/DESIGN-2026-08-16-caret-by-block-and-offset.md).

| prediction | outcome |
|---|---|
| **D-BI-1** (the answer comes in under 200 ms) | **FAILED** — 251 ms |
| **D-BI-1, substance** (bounded and small, not 30 s) | **HELD** |
| **D-BI-2** (the paragraph datum is fresh) | **FAILED** — it is not stale, it is *absent* |
| **D-BI-3 control** (no false positive on ordinary paragraphs) | **HELD** |
| **D-BI-3 empty** (the new failure shape fires) | **FAILED** — the comparison could not fire |

## What works: the click now answers

| click | elapsed | how it answered |
|---|---|---|
| first, far below the text | **39 ms** | `documented-callback-visible-cursor` |
| second, same point | **251 ms** | `verified-caret-readback` |
| third, same point | **251 ms** | `verified-caret-readback` |

The second and third clicks change nothing — no callback is coming, ever — and
**the call still answers**, through the deadline path E1-D built for the same
shape.  That is the thirty-second wait finding 052's residual was made of,
replaced by a bounded answer.

**D-BI-1 fails by 51 ms and it is recorded as failed.**  The appendix to the
design, written before the link, says why: the implementation's deadline is
250 ms, chosen because a click takes 22–28 ms to take effect on this engine, and
**the threshold was not moved to make the prediction pass**.  The 200 was a guess
made before the implementation existed; it was wrong, and it stays on the record
as wrong.

## What does not work: the fingerprint is inert in the product build

Every paragraph came back with the same fingerprint — `14650fb0739d0383` — while
the caret moved from y 1999 to 2795 to 4812.  That value is **the hash of an
empty string**, so the reply was not naming paragraphs at all.

The cause, found by reading after the measurement pointed at it:
`refreshEditorAccessibility()` — the only thing that calls
`setAccessibilityState(..., true)` — had exactly one call site, and it sits
inside `#ifdef OXSDK_EDITOR_DISCOVERY` **and** `#ifndef
OXSDK_FINDING_016_SELECTION_BARRIER`.  The product profile defines both.  **So
the product has never enabled accessibility**, and `getA11yFocusedParagraph()`
has always returned an empty focused paragraph there.

Which means the whole block-identity half of this link — the barrier comparison
and the paragraph in the caret answer — **is inert on the shipped build**, and
its two predictions could not have held.

This is the tree's own lesson one level in, and it is mine: **my four native
rounds enabled accessibility themselves.**  They measured a capability the
product does not switch on, and I built a design on it without ever asking
whether the shipped engine asks for it.  "What the harness does" standing in for
"what the product does", again.

A second, smaller thing the same measurement caught: the FNV-1a offset basis was
typed one digit short (`1469598103934665603` for `14695981039346656037`) — a
serviceable hash that was not the algorithm its comment named.  It was visible
only because every paragraph reported it.

## The barrier: the control is the half that matters

`d-bi-3-control` — a list action on an ordinary paragraph — still comes back
`verified-format-readback`, with containment checked and held.  So the new
comparison introduces **no false positive**.

But that is weaker evidence than it looks, and the run says so: with every
fingerprint equal, the comparison **cannot fire either way**.  The control will
have to be re-read once accessibility is on.

The empty-paragraph cell reported `multi-block-readback`
(`readbackBlockCount: 2`, containment held) — caught by the pre-existing
multi-block check, not by the new one.  Worth noting on its own: on this
artifact finding 046's cell no longer reports `postcondition-not-met`.

## What this costs

**A second link.**  The fix — call `refreshEditorAccessibility()` at document
open, where every profile reaches it — is engine-side, so it can only ship
through a link.  It is written and compiled; the queue carries it.

The honest accounting of the first link: **the placeCaret half shipped and
works; the fingerprint half shipped and does nothing.**

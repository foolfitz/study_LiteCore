# Finding 046 — why core and the shipped build disagree about an empty paragraph.  Registered before the harness existed.

Written 2026-08-16.  This is the measurement relink queue item **3b** is blocked
on, and it is a measurement, not a decision.

## The disagreement, stated exactly

Same fixture on both sides: `test-docs/e1/empty-paragraph.odt`
(`E1-EMPTY-BEFORE`, an empty paragraph, `E1-EMPTY-AFTER`, an empty paragraph).
Same target: the empty paragraph after `E1-EMPTY-BEFORE`.  Same gesture in
principle: place the caret, then `set-list-unordered`, which arms the format
barrier and its selection pair (`.uno:GoToStartOfPara` + `.uno:EndOfParaSel`).

| | what it reports |
|---|---|
| **core**, natively (`findings/evidence/046/native/`) | the pair walks the caret UP (1807 → 1418) and reads back **`E1-EMPTY-BEFORE`, 495 bytes, blockCount 1** |
| **the shipped v2 build** (`d2-refused-no-mutation-engine`, six recorded rounds, both browsers) | **`preBlocks: 0`, `postBlocks: 0`**, shape `multi-block-readback` in some rounds and `postcondition-not-met` in others |

Until that is explained, a shape called `empty-readback` would be named after a
symptom whose mechanism is unknown, and naming it is what 3b would do.

## What is NOT in dispute, and must stay excluded

The D3 `L1`–`L6` cells also carry `preBlocks: 0, postBlocks: 0`, but their shape
is `stage-deadline:awaiting-selection` — **those barriers never read anything**.
Zero there means "never set", not "read and found nothing".  They are not
evidence of a zero readback and are excluded from this round.

## The four candidate explanations, each with something that kills it

1. **The caret was never on the empty paragraph.** Every recorded browser round
   of this cell predates finding 048's fix, so its click was confirmed by a
   condition that was already true before the click. *Killed by:* re-running the
   cell with the product's own confirmed click (`placeCaret` now waits for the
   engine) and reading the caret back at dispatch time.
2. **The selection covers two paragraphs in the browser, one natively.** That
   would explain `multi-block-readback` with zero blocks: two list items after
   the bullet is `itemCount 2, blockCount 0` in the engine's own parser, which
   is `multiBlock` with no block in it. *Killed by:* the item count — which the
   shipped worker does not project (that projection is a v3 queue item), so on
   v2 it can only be inferred from the shape, and this round says so rather than
   pretending otherwise.
3. **The readback is empty in the browser** (`parsed=false`, hence blockCount 0)
   because `getTextSelection` is read before core has finished selecting — the
   finding 048 family, one layer down. *Killed by:* the control arm below.  If a
   paragraph WITH text also reads back zero blocks in the browser, the field is
   not describing content at all.
4. **`preBlocks` never gets set in the browser for any document.** *Killed by:*
   the same control arm.

## Arms

All on the **shipped, frozen `e2-editor-v2`** — no rebuild, no relink.

| arm | what it does |
|---|---|
| `A1-empty-click` | caret on the empty paragraph by the product's confirmed click, then `set-list-unordered` |
| `A2-empty-selectrange` | the same target, caret formed by a zero-width `selectRange` (SPEC E2-C 9.5.6's other gesture) |
| `A3-text-click` (**control**) | caret on `E1-EMPTY-BEFORE`, a paragraph WITH text, same action |
| `A4-last-empty-click` | the last (empty) paragraph, the position the native round measured second |

Each arm records: the caret the product reports before dispatch, the whole
`formatBarrier` projection, the session state afterwards, and the saved document
when the state allows a save.

## Predictions

- **P-046B-1** — the control `A3-text-click` comes back with **`preBlocks >= 1`**.
  If it does not, nothing else in this round means anything, because the field
  would not be reporting content at all.
- **P-046B-2** — with the caret confirmed on the empty paragraph, `A1` still
  reports **`preBlocks: 0`**, i.e. the disagreement survives the 048 fix.
  (Registered this way round because the recorded rounds are consistent about
  it; a prediction that the fix explains everything would be the comfortable
  one.)
- **P-046B-3** — `A1` and `A2` produce **the same** `preBlocks`, differing at
  most in `failureShape`.  Natively the two gestures were identical in caret
  position, selection type and markup, so a difference here would be a
  browser-only property.
- **P-046B-4** — `A4` behaves like `A1`, because natively both empty positions
  behaved identically.
- **P-046B-5** — no arm reaches a successful action; every arm ends in a
  dispatched failure with the document changed, matching what the native round
  proved (the bullet does apply).

## The decision rule, written before the data

- **P-046B-1 fails** → the round says only "the projection is not usable for
  this question on v2", and 3b stays blocked on a different, sharper thing.
- **P-046B-2 holds** (the disagreement survives) → the next controlled variable
  is the readback's *content*, which the shipped worker does not expose.  That
  needs the diagnostic profile, and **that profile's engine now contains the
  queued fixes**, so it would be a different engine — which must be declared,
  not glossed.
- **P-046B-2 fails** (the browser now reports blocks) → the disagreement was an
  unlanded click, i.e. finding 048 again, and 3b's criterion can be written on
  top of a confirmed caret.  The six recorded rounds would then be re-read as
  measurements of the pre-048 harness, not of the engine.
- Either way, **nothing named `empty-readback` is written into the engine in
  this round.**

## Addendum A1 (2026-08-16, after the smoke run, before any recorded round)

A single Firefox smoke run — harness validation, written to a scratch directory,
**not** evidence — came back before the rounds below were recorded, and it broke
the round's own control:

**`A3-text-click` SUCCEEDED (`verified-format-readback`) and still reported
`preBlocks: 0, postBlocks: 0`.**  A paragraph with text in it, a barrier that
completed, and both count fields zero.

P-046B-1 is therefore **FAILED as registered**, and it failed in the most
useful possible way: it says the fields are not reporting readback content on
this route.  The source says why, and the two agree:

- `preBlockCount` is assigned in exactly one place (`probe_engine.cpp:3329`),
  inside the branch that runs when the selection rectangle list is **not**
  empty — i.e. on the two RANGE routes.  On the collapsed route it is never
  written.
- `postBlockCount` is assigned in exactly one place
  (`probe_engine.cpp:3368`), inside `checkFormatBarrierCrossParagraph()` — the
  **cross** route only.

Every cell in this argument, on both sides, ran on `route: "collapsed"`.

So one arm is added before any round is recorded, to turn "the field is never
set" into "the field is set on these routes and not those":

- **A5-text-range** — a `selectRange` inside one text paragraph, which is the
  range-single route by construction, then the same action.

- **P-046B-6** — `A5` reports **`preBlocks >= 1`** and **`postBlocks: 0`**, and
  its route is `range-single`.  If `preBlocks` is zero here too, the field is
  not written anywhere a product path can reach and the claim gets stronger,
  not weaker.

**What this already does to the disagreement**: core's number was a measurement
of markup; the shipped build's number was **a field that is zero by
construction on that route**.  Those were never in contradiction, and 046's
argument rested on comparing them.  The rounds below are recorded to show this
in both browsers rather than from one smoke run and a source reading.

## What voids the round

- The fixture's empty paragraph is not where `anchorY + 390` puts it: the arm is
  recorded as void rather than retried at a different offset until it agrees.
- An arm fails for a reason unrelated to the barrier (fixture fetch, anchor not
  found): recorded, not retried.
- The artifact hashes do not match the frozen four.

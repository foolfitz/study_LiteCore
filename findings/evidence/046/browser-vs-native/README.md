# Finding 046 — the disagreement dissolves: the browser's number was never a readback

Criteria in `PREDICTION.md` (P-046B-1..5 registered before the harness;
P-046B-6 in addendum A1, after a scratch smoke run and before any recorded
round).  Judged by `tools/analyze_f046_browser.py`; self-test 9/9.

Four recorded rounds (two browsers × two runs), all on the **frozen
`e2-editor-v2`** — no rebuild, no relink, nothing edited to obtain them.

## What relink queue item 3b was blocked on

> core's readback for an empty paragraph is **the paragraph above, with one
> block in it**.  The shipped build reports **zero** blocks for the same gesture
> on an empty paragraph.  Those disagree, and until that is explained, a shape
> named `empty-readback` would be named after a symptom whose mechanism is
> unknown.

## The answer

**They were never comparable.**  `preBlocks` and `postBlocks` are not written on
the route these cells take.

- `preBlockCount` is assigned in exactly one place, `probe_engine.cpp:3329`,
  inside the branch that runs when the selection rectangle list is **not**
  empty — the two RANGE routes.  On `collapsed` it is never written.
- `postBlockCount` is assigned in exactly one place,
  `probe_engine.cpp:3368`, inside `checkFormatBarrierCrossParagraph()` — the
  **cross** route only.

Every cell in the argument, on both sides, ran on `route: "collapsed"`.  So core
reported a measurement of markup and the browser reported **a field that is zero
by construction**, and 046 compared them.

The round does not rest on that source reading.  It rests on the control:

| arm | route | accepted | preBlocks | postBlocks | shape |
|---|---|---|---|---|---|
| `A3-text-click` (**control**, a paragraph WITH text) | collapsed | **yes**, `verified-format-readback` | **0** | 0 | — |
| `A1-empty-click` | collapsed | no | 0 | 0 | `multi-block-readback` |
| `A2-empty-selectrange` | collapsed | no | 0 | 0 | `multi-block-readback` |
| `A4-last-empty-click` | collapsed | no | 0 | 0 | `stage-deadline:awaiting-selection` |
| `A5-text-range` | **range-single** | **yes** | **1** | 0 | — |

Identical in Chrome and Firefox, in both runs.

**A barrier that SUCCEEDED over a paragraph with text in it reports zero
blocks.**  That is the whole argument in one row: zero cannot mean "read and
found nothing" when the read demonstrably worked.  And `A5` shows the field is
not simply dead — on a range route it reads 1.

## Predictions, scored as written

| id | result |
|---|---|
| P-046B-1 — the control reports `preBlocks >= 1` | **FAILED** — and this failure is the finding |
| P-046B-2 — with the caret confirmed on the empty line, `preBlocks` is still 0 | **held** — caret confirmed at y=1807, the empty line, in every arm |
| P-046B-3 — the click and the zero-width selectRange read the same | **held** |
| P-046B-4 — the last empty paragraph behaves like the first | **FAILED** — it reaches `stage-deadline:awaiting-selection` instead: the barrier never got its selection callback there |
| P-046B-5 — no arm reaches a successful action | **FAILED** — the two arms that were never about the empty paragraph both succeed |
| P-046B-6 — a range arm reports `preBlocks >= 1`, `postBlocks 0`, route range-single | **held** |

## Two things this changes

**1. 3b's blocker is gone, and 3b's question moved.**  There is no
native/WASM contradiction to explain.  What 3b still needs is a way for a host
to tell "nothing was read" from "only list items were read", and the engine's
own record has it (`readback.parsed`, `readback.blockCount`,
`readback.itemCount`) while the product projection carries **none of the first
two** — `itemCount` arrives in v3, `parsed` and `blockCount` do not.  That is a
projection decision, and it belongs in the relink.

**2. A new queue item, of the same family as item 3.**  Item 3 exists because
the barrier reported a route it had not classified — a default presented as an
observation.  `preBlocks`/`postBlocks` do it twice more: they are zero on routes
where nothing assigned them, and the evidence has been read as measurements for
two rounds.  Either populate them on every route, or rename them so "not read"
cannot be mistaken for "read zero".

## Also recorded

- **The two gestures now agree.**  D2's rounds had click →
  `postcondition-not-met` and selectRange → `multi-block-readback` on this
  paragraph.  With finding 048's confirmed caret, **both** reach
  `multi-block-readback` in both browsers.  The difference D2 recorded was a
  property of an unconfirmed click.
- **The last empty paragraph is different.**  Same document, same gesture, and
  the barrier does not even reach a readback — `stage-deadline:awaiting-selection`
  in both browsers.  Not chased here; recorded because it was measured.
- Saved documents are kept per arm (`saved/`), the same proof the native round
  used: the bullet does reach the document.

## Layout

```
e2-editor-v2-572035ac/{chrome,firefox}/   round 1
run-2/e2-editor-v2-572035ac/{...}/        round 2, after the runner's
                                          attribution lookup learned to read a
                                          page that is not D0-shaped (round 1's
                                          `attribution.consistent` is false for
                                          that reason alone; its own inventory
                                          block matches the frozen hashes)
verdict.json                              the offline judgement
```

```
python3 tools/analyze_f046_browser.py $(find <this dir> -name result.json -printf '%h\n')
python3 tools/analyze_f046_browser.py --self-test <the same list>
```

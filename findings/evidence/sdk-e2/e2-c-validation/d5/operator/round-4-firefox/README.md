# D5, fourth operator round (Firefox, 2026-08-16) — the first cells to PASS

Preserved exactly as exported, with the operator's own final document beside it.

## Verdict: PARTIAL — and **two cells established**

| cell | status | why |
|---|---|---|
| `d5-pointer-drag-single` | **PASS** | 68 trusted events, revision 0 → 1, document captured |
| `d5-pointer-drag-cross` | **PASS** | 86 trusted events, revision 1 → 2, document captured |
| `d5-ime-commit` | NOT_ESTABLISHED | the cell recorded **no events** (see below) |
| `d5-clipboard` | NOT_ESTABLISHED | a real Ctrl+C and Ctrl+V, and the document **did not change** |

The first D5 cells to reach PASS on a human's gestures, on the shipped v2
artifact.

## The saved documents, checked by hand

The frozen oracle says "…**and the saved ODT shows it**".  The analyzer only
checks that a document was *captured*, not what is in it — an analyzer weaker
than its matrix, recorded here rather than quietly fixed after the fact.  So the
content was read directly:

| document | `<text:list>` count |
|---|---|
| pristine `list-contexts.odt` | **2** |
| after `d5-pointer-drag-single` | **3** |
| after `d5-pointer-drag-cross` | **4** |

Both bullets are in the saved bytes.  The oracle is met in substance, not only
in form.

**The auto-save worked**: all four cells captured a document
(12.8–13.0 KB, `pressedBy: "harness"`), after this step had failed in all three
previous rounds as a human instruction.

## `d5-ime-commit`: the document moved, the cell did not record it

The cell's window holds **zero events**, yet its `stripBefore`/`stripAfter` show
revision 1 → 3, and its captured document contains
**`E1-LC-BULLET-TWO 你好中文項目`** — the Chinese commit landed.

So the input happened; the harness attributed it elsewhere.  The cell was opened
second and stayed open while another cell was begun, and `endCell` only claims
events whose `cell` field is its own.  A redo of **this cell alone** settles it —
nothing else in the round needs repeating.

(Round 3 already established the part that needed a browser comparison:
Firefox delivers `compositionend` trusted, so the criterion is reachable here.)

## `d5-clipboard`: a real paste that changes nothing — now three times

One trusted `copy`, one trusted `paste`, revision **3 → 3**, and the captured
document is **byte-identical in `<office:body>`** to the previous cell's.

| round | browser | copy/paste | revision |
|---|---|---|---|
| 1 | Chrome | 3 / 2 | 11 → **13** |
| 2 | Chrome | 1 / 1 | 3 → 3 |
| 3 | Firefox | 1 / 1 | 3 → 3 |
| **4** | **Firefox** | **1 / 1** | **3 → 3** |

Round 1 is the only one where a paste moved the document, and it is also the
only one with three copies and two pastes.  **Not diagnosed here**, and the
controls that exist are recorded rather than reasoned past:

- four consecutive `session.commitText()` calls all advance the revision
  (0→1→2→3→4), so the shell's commit path is not dropping work;
- the adapter's `handlePaste` reads `clipboardData.getData("text/plain")` and
  commits it, so an empty read would produce exactly this — a paste event that
  commits nothing;
- **the adapter's own trace is discarded by the product**
  (`EditorSession` accepts `onInputTrace`; `web/e2-editor-app.js` passes none),
  so the layer where this happens is the one layer nobody records.

Next controlled variable, unchanged from round 3: wire `onInputTrace` and
`onClipboardTrace` into a page an operator can drive, and repeat this cell.

## What remains for a full D5

Two cells, one short session:

1. `d5-ime-commit` on Firefox — begin, do the commits, end, without opening
   another cell in between;
2. `d5-clipboard` — after the trace question above is answered, because a fourth
   round of the same result would measure nothing new.

## Addendum, 2026-08-16 — the strengthened criterion, applied to this round

The gap recorded above ("the analyzer only checks that a document was
*captured*") is now implemented as a criterion:
`tools/analyze_e2_c_d5.py --criteria round-two` counts `<text:list>` in the
document each drag cell saved, against the document saved immediately before it.

Re-judged with it, **both drag cells still PASS** — 2 → 3 → 4, the counts read
by hand above, now read by the judge.

One thing this round taught the implementation: the baseline must follow the
**save order**, not the cell order.  This operator opened `d5-ime-commit` second
while `d5-pointer-drag-cross` was run third, so a judge that walked the cells in
matrix order compared the cross-drag against the IME cell's document and made
its own false negative.  Measured here, fixed before the criterion was recorded.

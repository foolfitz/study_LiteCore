# The confound resolves, and B' breaks twice

**Date** 2026-08-15. Native, `build-native-26-8`, three rounds, three arms,
**all nine records identical within each arm**.
Prediction (round-1 body and round-2 addendum):
[`../PREDICTION.md`](../PREDICTION.md), both committed before their runs.

## The three arms

| arm | range | blocks (html) | text equal after dispatch | items after |
|---|---|---|---|---|
| `cross-paragraph` | whole ¶1 → into ¶2 | 2 | **false** | 2 |
| `single-paragraph-control` | **partial**, inside ¶1 | 1 | true | **0** |
| `single-paragraph-whole` | whole ¶1 | 1 | true | 1 |

Every arm applied the bullet — the saved documents say so
(`dispatchApplied: true` in all nine) — and **one `.uno:Undo` restored every
paragraph signature in all nine**.

## Check 1 — substrate: PASS

`getTextSelection("text/html")` returned in 0 ms, 630 bytes for the
cross-paragraph selection, and the markup carries **2** block elements against
**1** for both single-paragraph arms. It can be enumerated per block, and the
count discriminates.

## Check 3 — undo: PASS

Judged on documents, not on return values. One undo restores. Nine for nine.

## Check 2 — survival: the selection survives, the equality gate does not

The selection is still there after the dispatch (`type 1`, non-empty) in every
arm. What fails is the **comparison** SPEC E2-B 9.7 adopted.

**Break one — the readback injects list decoration across a paragraph
boundary.** Cross-paragraph, before: `"E1-MULTI-START alpha\n第二段中文"`.
After: `"    • E1-MULTI-START alpha\n    • 第二段中文"`. The round-2 addendum
predicted the mechanism before this ran, and `single-paragraph-whole` confirms
it: a whole paragraph that becomes a list item reads back with **no** marker
(`textEqual: true`) while its html shows `items: 1`. **The marker tracks
crossing a paragraph boundary, not becoming a list.**

So byte-equality of plain text fails on **every successful cross-paragraph list
dispatch** — precisely the case B' exists to verify. B' would fall back always,
which is check 2's own disqualifier.

**Break two, which neither the adjudication nor the prediction anticipated — a
partial selection reads back with no list structure at all.** The control's
paragraph *is* a list item after the dispatch (the document says so), and its
html readback reports `items: 0`, `blocks: 1`. **Verification driven by the
surviving user selection is a false negative whenever that selection is
partial** — and a partial range is the ordinary result of dragging.

The shipped barrier does not hit this because it discards the user's selection
and re-selects the whole paragraph with `.uno:SelectText` — which is exactly the
call that selects only one paragraph, and therefore the reason G3 fails. So the
two halves of the problem are the same call: **whole-paragraph readback is what
makes verification honest, and one-paragraph-only is what makes it incomplete.**

## What this does not say

- It does not measure the WASM artifact.
- It does not say B' is impossible — it says the construction as adjudicated is
  broken in two specific ways, both of which are about what a readback of a
  selection can see.
- Timings are from a fixed-sleep probe and are citable only within a run.

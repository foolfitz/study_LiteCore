# E2-C D3, cells L1–L8 — predictions, written before the harness ran

Registered 2026-08-15, **before** `web/e2-c-d3-app.js` existed. Corrections go in
a dated section at the bottom, struck through rather than rewritten.

## Why these cells exist

Round one's D3 would have driven the list actions at `E1-LC-ISOLATED`, a
paragraph with **no list on either side** — so "D3 covered the list actions"
would have meant "the list actions were dispatched next to no lists". The
adversarial review caught it; the frozen matrix now names eight target cells,
each bound to an anchor **and a pre-state**.

L6 and L7 are the two the upper spec's stop condition points at
(SPEC E2-000 section 10: "a list switch causes silent ODT structure loss").

## Predictions

| cell | anchor | pre-state | action | prediction | confidence |
|---|---|---|---|---|---|
| L1 | `E1-LC-ISOLATED` | plain, no list either side | `set-list-unordered` | becomes a `<text:list-item>` in a **new** list; the heading before and the plain paragraph after are untouched | high |
| L2 | `E1-LC-END` | plain, last paragraph | `set-list-ordered` | becomes a numbered item in a new list | high |
| L3 | `E1-LC-BULLET-TWO` | second item of a 2-item bullet list | `set-list-none` | leaves the list; `E1-LC-BULLET-ONE` stays a bullet item | high |
| L4 | `E1-LC-NUMBER-TWO` | second item of a 2-item numbered list | `set-list-none` | leaves the list; `E1-LC-NUMBER-ONE` stays numbered | high |
| L5 | `E1-LC-BULLET-ONE` | first item of a bullet list | `set-list-ordered` | **converts in place**: the paragraph ends up in a numbered list, and no third list appears | **medium** — conversion could also split the bullet list in two around it |
| L6 | `E1-LC-NUMBER-ONE` | already numbered | `set-list-ordered` again | **`<office:body>` byte-identical**: asking for the state it is already in changes nothing | **medium-high** — finding 030 made these setters rather than toggles, but "setter" and "idempotent" are different claims and only the first was measured |
| L7 | `E2-LS-MID` | **interior** item of a 3-item numbered list | `set-list-none` | the list splits: `E2-LS-ONE` in one list, `E2-LS-THREE` in another, `E2-LS-MID` a plain paragraph between them, **no item lost** | **medium** |
| L8 | `E1-LC-BETWEEN` | plain paragraph with a **bullet list before and a numbered list after** | `set-list-unordered` | **merges with the bullet list before it**, giving one 3-item bullet list; the numbered list after stays separate | **low-medium** — this is the cell that exists because nobody knows |

## What each answer would mean

* **L6 fails** (the body changes on a repeat) — the actions are still not
  idempotent, and the upper spec's "explicit closed enum, not a toggle"
  (SPEC E2-000 8.1) is not satisfied even after finding 030's fix. That would be
  a new engine queue item for the same relink.
* **L7 fails by losing an item** — that is the silent-structure-loss stop
  condition firing, and E2 stops rather than narrows.
* **L7 fails by not splitting** (the whole list dissolves, say) — not
  necessarily a defect, but the contract has to say so, and the manifest's
  `limits` would owe a line.
* **L8's outcome is not a pass/fail** in the ordinary sense: merging and not
  merging are both acceptable behaviour. What is not acceptable is deciding
  afterwards which one we expected. The prediction above is the commitment.

## What these cells deliberately do not cover

* Nested lists, mixed numbering, and lists inside tables: the corpus has none,
  and D3's inventory pins that as a blind spot rather than leaving it implied
  (SPEC E2-C 8.1).
* Cross-paragraph list actions: those are D1's, and the one uncovered cell E2-B
  named (`set-list-ordered` across two already-numbered paragraphs) passed there.

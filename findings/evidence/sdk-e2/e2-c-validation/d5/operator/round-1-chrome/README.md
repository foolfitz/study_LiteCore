# D5, first operator round (Chrome, 2026-08-16) — the gestures were real; the round is void on an instruction I never wrote

Preserved exactly as exported.  No cell was re-run, and nothing was edited to
make a criterion pass.

**Verdict: PARTIAL, all four cells `NOT_ESTABLISHED`** — and for reasons that
are mostly not about the product.

## What the operator actually produced

832 events, all captured with their `isTrusted` flag.

| cell | events | revision | synthetic |
|---|---|---|---|
| `d5-pointer-drag-single` | 2 down, 84 moves, 2 up | 0 → **1** | 0 |
| `d5-pointer-drag-cross` | 4 down, 211 moves, 4 up | 1 → 1 | 0 |
| `d5-ime-commit` | 2 composition sequences, 14 updates, 8 keydown | 1 → **3** | **2** |
| `d5-clipboard` | **3 copy, 2 paste**, 9 down, 281 moves | 11 → **13** | 0 |

**The product did the work.**  The clipboard cell's revision advanced twice, so
**the pastes landed** — the operator reported "it looks like it cannot paste",
and what they were seeing was this build painting no caret and no selection.
The IME cell's revision advanced twice as well, so **both Chinese commits
landed**, including the one over a selection.

## Why all four are NOT_ESTABLISHED

### 1. No saved document, in any cell — my omission

`savedDocumentCaptured` fails for all four.  The frozen matrix's oracle for the
two drag cells says "**and the saved ODT shows it**", so a save is part of the
criterion — and `handoff/RUNBOOK-operator-d5.md` never told the operator to
press **儲存 ODT**.  The round was void before it started, on an instruction
that was missing rather than wrong.

(Cells 3 and 4's frozen oracles do not mention a save; the analyzer requires one
for all four.  That is an analyzer-over-matrix overreach, recorded here rather
than quietly fixed.)

### 2. The IME cell: `compositionend` arrives UNTRUSTED — measured

Both composition sequences look like this:

```
compositionstart   isTrusted=true   ''
compositionupdate  isTrusted=true   'ㄋ'
compositionupdate  isTrusted=true   'ㄋㄧ'
…
compositionupdate  isTrusted=true   '你好'
compositionend     isTrusted=FALSE  '你好'
```

Start and all fourteen updates are trusted.  **Only `compositionend` is not**,
both times, with the correct committed text (`你好`, `取代`), and the document
revision advanced for both.

So the input was a person at a keyboard using Fcitx5 Chewing, and D5's rule —
"one synthetic event anywhere in a cell disqualifies the cell" — rejects it.
**On this platform the IME cell cannot pass, and not because the gesture was
fake.**

This is the criterion failing to describe reality, the same shape as the first
round's "27 cells used a gesture the product does not use".  It is **not** fixed
by relaxing the rule after seeing the data.  What it needs:

- **a Firefox control** — is this Chromium-specific?  One IME cell in Firefox
  answers it, and nothing else in the round has to be repeated;
- then a **criterion decision for matrix v2** (still a draft): judge composition
  trust on `compositionstart` + `compositionupdate`, and record why
  `compositionend`'s flag is not usable — or keep the strict rule and record
  that this cell is unobtainable on this platform.

Either way the decision is registered before the next round, not after it.

### 3. The cross-paragraph drag never advanced the revision

`d5-pointer-drag-cross` ends with the strip still at revision 1 and state
`busy`: the bullet press did not complete inside the cell's window.  Recorded as
measured; the cell simply needs redoing with the format button pressed and the
state back at `ready` before "這一格做完了".

## What was fixed after this round

- The runbook now says to press **儲存 ODT** in every cell, and the live readout
  shows whether a save has been captured for the cell in progress.
- The readout shows where the keyboard focus is, because a real Ctrl+V that
  lands on a button in the harness panel does nothing and reports nothing.

## What this round does establish

- The harness records real gestures faithfully, with per-event trust, in a real
  browser driven by a person — 832 events, 0 synthetic outside the two
  `compositionend`s.
- The product's paste and IME commit paths **work on the shipped v2 artifact**,
  by the revision counter, even though the screen shows nothing.

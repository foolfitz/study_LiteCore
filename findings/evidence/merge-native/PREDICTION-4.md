# Paragraph merge, native, fourth round — predictions (written 2026-10-06, before the round ran)

The owner chose **B′** (2026-10-06): before deciding how Backspace at a paragraph's start should behave, measure whether option **B** can work — press the user's own key and prove what it did from the undo stack — instead of option A (delete the barrier's one-unit selection, which skips Writer's first step at indented paragraphs and outline headings; rounds D, E and the multi-press rounds).

## What B would be, as measured here

The engine keeps the selection barrier for every delete inside a paragraph (a unit with no separator: verified as today). Only when the unit shows a boundary does B take over:

1. **The unit is one step across a paragraph separator** (`[10]`, or a label-decorated LF): take the step back with the opposite arrow *without* Shift, check the caret is where it was, press the user's own key, and read the undo stack: one more action = Writer did something (its comment says what); no change = Writer did nothing.
2. **Nothing was selected** (a document's start or end): no step to take back; Writer's key does nothing there (round 1: C29, C30).
3. **Anything else** (a table selected whole): refuse, as today.

The fourth-round probe (`tools/merge_native_boundaries.cpp`, this commit) adds to every case:

- arm **b**: B's sequence above — unit selection, the unshifted opposite arrow (only when something was selected), readback of where the caret is (`restored`), the user's key, the undo stack before and after, save;
- the undo stack (`getCommandValues(".uno:UndoCount")` and `".uno:Undo"`) around the select arm's dispatch and around every key-arm press;
- optional TSV fields `occurrence` (the n-th copy of the anchor) and `offset` (move the caret n characters after the checked placement).

Reader `tools/analyze_merge_undo.py`: per press, did `content.xml` change (and the block reduction), did the undo stack change, do they agree; for arm b, did the caret come back to the placed caret, and does its document equal the key arm's first press.

Shakedowns before this file (not counted, `scratchpad`): Shift + the opposite arrow brought the caret back but the key that followed changed nothing (the empty selection kept its mark); the unshifted arrow fixed C01, C02, G01 and broke C29 (nothing selected, the arrow moved the caret, Backspace deleted "M") and C15 (a table selected whole cannot be stepped back). Both are why the sequence above has three branches.

## Cases (3 rounds each)

- `boundaries.fodt` + `round-g-boundaries.cases.tsv`, PRESSES=3: C01 (control), C02, C03, C08, C09, C15, C16, C17, C27, C29, C30, and **G01**: the caret two characters into "M02 plain beta", Backspace three times (two characters, then the paragraph boundary).
- `boundaries-indent.fodt` + `round-g-indent.cases.tsv`, PRESSES=3: D01 (control), D04, D08, D12.
- The owner's PMPC document + `round-g-pmpc.cases.tsv`, PRESSES=3, under `wasm_sdk_probe/build/`: E01 (control), E02, E05, E10, E12, and **T01**: the end of the table of contents' title 「目次」 — inside a protected section.
- `undo-grouping.fodt` + `round-g-grouping.cases.tsv`, PRESSES=25: G12 (control: Backspace through 25 distinct characters), **G10** (Backspace through 25 of a run of 30 "a"), **G11** (Delete through the same run).

## Predictions

From `sw/source/core/undo/undel.cxx`: a delete's comment is "Delete" plus the deleted text shortened to 20 characters (`ShortenString`, `nUndoStringLength = 20`, front and back kept); consecutive single-character deletes in one paragraph are folded into one action (`SwUndoDelete::CanGrouping`); a delete that spans two paragraphs is never folded, either way (it has an end string, and the new range crosses nodes).

| What | Prediction |
|---|---|
| Arm b, paragraph boundaries (C01, C02, C03, C08, C09, C27, D01, D04, D08, D12, E01, E02, E05, E10, E12, G01) | caret back at the placed caret; document **equals the key arm's first press**; one new undo action |
| Arm b, C29, C30 | nothing selected, no restore key; caret where it was placed; the key changes nothing; stack unchanged |
| Arm b, C15, C16, C17 | the caret does **not** come back to the placed caret (the unit is a table); recorded, not acted on — B refuses these |
| Key arm, every press | the undo stack changes **exactly** when `content.xml` does, except the grouping cases below |
| Merges | comment "Delete paragraph" (shakedown), a new action each time |
| C03, D04, E05 (heading not counted), C09, E12 (list header), D08, E10, D12 (indents) | a new action of another kind on press 1; comment unknown |
| C15, C16, C17, C29, C30, T01 | no press changes the document or the stack |
| G01 | presses 1–2 fold into one action ("Delete “0”" → "Delete “M0”": count unchanged, comment changes); press 3 (the boundary) adds a new action |
| G12 | count stays 1 after press 1; the comment changes on every press (the deleted text grows at its front, which `ShortenString` keeps) — agree 25/25 |
| **G10, G11** | the comment stops changing once the folded text is longer than 20 characters ("aaaaaaaa…aaaaaaaa" is the same string every time): from about press 21 on, **the document changes and the stack does not**. This is why B is used only at boundaries, where nothing folds |
| Select arm, T01 | the barrier's proof holds (`success: true`, collapsed selection) while nothing changes — and the undo stack does not change either, so the stack catches what the barrier's proof missed |

What would change the decision:

- Arm b ≠ key at any paragraph boundary, or the caret not back where it was: B's sequence is not Writer's key there, and B is not ready.
- A boundary press where the stack and the document disagree: the undo stack cannot be B's proof.
- G10/G11 agreeing everywhere: the source reading about the comment is wrong, which matters for the in-paragraph path only.
- What this round cannot say: the order of a posted key and the engine's next step on WASM (native LibreOffice runs its own main loop; the probe waits fixed times). That is a WASM question for the engine's design, not settled here.

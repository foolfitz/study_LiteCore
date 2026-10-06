# Paragraph merge, native, sixth round — predictions (written 2026-10-06, before the round ran)

Round four's C08 (Delete at a body's end before a bullet item) is the one paragraph boundary where B's restore failed: the unshifted Left that should take the caret back to the body's end stopped **in front of the item's label**, and the key that followed removed the number instead of merging (0/3). Round four measured arm b at no other boundary whose **next** paragraph carries a label. If C08 is the shape, B refuses every Delete at the end of a paragraph that is followed by a list item or a numbered heading — in the owner's document that is every paragraph introducing one of its 11 lists and every list item but the last of each. The spec cannot be written without knowing which.

## What the source says (`sw/source/core/crsr/crsrsh.cxx:326–380`, `SwCursorShell::LeftRight`)

Case 2: a Left at the start of a paragraph with visible numbering or a bullet (`HasVisibleNumberingOrBullet`), with no mark and not already in front of its label, **only sets the in-front-of-label flag** — the caret does not leave the paragraph. Case 3: any other Left resets the flag and moves normally. So after B's Shift+Right has selected `LF + label`, the unshifted Left (which drops the mark first) lands in front of the next paragraph's label; **a second Left is a normal move, to the end of the paragraph the caret started in**. Going the other way (Backspace, restore with Right) case 1 only resets a flag that is not set, which is why round four's C09 and E12 came back in one press. An unlabelled heading's empty number format is not visible numbering, which is why E01 came back in one press.

## Instrument (this commit)

`tools/merge_native_boundaries.cpp`, arm b: `MERGE_RESTORE_PRESSES` (default 1, so earlier rounds are unchanged) lets the restore arrow be pressed again, up to that many presses in all, **only while the caret is not back at the placed caret**; every intermediate readback is recorded (`restoreSteps`), and `restorePresses` says how many were used. The key is pressed after the last restore press whatever its result, so a restore that never comes back is still measured against the key arm. The reader prints `restore=ok/2` when two presses were used. The runner records the setting in `restore-presses.txt`.

Run with `MERGE_RESTORE_PRESSES=2`, PRESSES=1, 3 rounds:

- `boundaries.fodt` + `round-i-boundaries.cases.tsv`: C01 (control), **I02** (Delete at a body's end before the numbered heading "1. M03"), **C08**, **C10** (bullet item before bullet item), C11 (Backspace, bullet item after bullet item), C12 (Delete, bullet item before body), C13 (Backspace, body after bullet item), **I03** (Delete at a body's end before a numbered item), **I01** (numbered item before numbered item), C14 (Backspace, numbered item after numbered item).
- The owner's PMPC document + `round-i-pmpc.cases.tsv`, under `wasm_sdk_probe/build/`: E01 (control), **P27** (indented body before the WW8Num3 numbered list), **E13** (numbered item before numbered item), E15 (numbered item before indented body), **P62** (indented body before the WW8Num4 bullet list — the shape the handoff proposed for re-pinning the production-UI runner's refusal arms), **P63** (bullet item before bullet item).

## Predictions

| Cases | Restore | Arm b vs the key arm | Undo comment |
|---|---|---|---|
| C01, E01, C12, E15 (Delete, next paragraph unlabelled) | 1 press | equal (merge) | `Delete paragraph` |
| C11, C13, C14 (Backspace) | 1 press | equal | C11, C14 `Number On/Off` (list header first, as rounds 1 and E); C13 `Delete paragraph` |
| **I02, C08, C10, I03, I01, P27, E13, P62, P63** (Delete, next paragraph labelled) | **press 1 stops in front of the label (caret ≠ placed), press 2 reaches the placed caret** | **equal (merge)** | `Delete paragraph` |

Every arm's undo stack agrees with `content.xml` (0 disagreements), as in rounds four and five.

What would change the decision:

- The second press does not come back, or comes back and the key then differs from Writer's: B refuses every Delete before a labelled paragraph. In the owner's document that is a common edit, and with finding 109's handling each refusal costs a checkpoint save and a reopen with the caret at the document's start. The spec would then have to choose between living with that, option A for forward Delete (round 1 and E: deleting the selection equals the key at every such boundary measured, but the barrier's selection cannot tell a label from a small table), or another restore.
- It comes back in two presses everywhere predicted: B's restore becomes "the opposite arrow, at most twice, until the caret is back", and the second press is used only where the caret did not come back from the first.
- P62 merges under B: it cannot serve as the production-UI runner's refusal arm, and that arm needs another boundary B still refuses (document start, a table, or one found by measurement).

Not covered: a caret that is already in front of a label when the user presses Delete (the user pressed Left at an item's start first); nested lists; a label that is a picture.

## 6b: tables and the document's ends with two restore presses (added before 6b ran; 6a's results are in the README)

Why: with a second restore press allowed, a table boundary that failed in one press (round four C15, C16) might come back in two, and then B would press the key there. Case file `round-i-tables.cases.tsv`: C15, C16, C17, C29, C30, boundaries.fodt, `MERGE_RESTORE_PRESSES=2`, PRESSES=1, 3 rounds.

Round four's readbacks show where one press went: C15 (Delete at a body's end before a table) from the body's line (y 6848) to inside the table's row (7352, 7266); C16 (Backspace at the start of the body after the table) from (1418, 7542) to the first cell's start (1418, 7266). A second press moves inside the table again (case 3, a normal move, or `GoPrevCell`/`GoNextCell` if the selection left the cursor in table mode).

| Case | Prediction |
|---|---|
| C15, C16 | two presses, **neither at the placed caret** — B refuses before the key. (The probe presses the key anyway; inside a cell it may delete a character, which is why the engine must not.) |
| C17 | one press, back (as round four); the key changes nothing, the stack does not change |
| C29, C30 | nothing selected, no restore press; the key changes nothing |

If C15 or C16 comes back in two presses: B presses Delete/Backspace there; round 1's key arm changed nothing at both, so the outcome is a no-op that reaches the deadline — slower than a refusal, not wrong.

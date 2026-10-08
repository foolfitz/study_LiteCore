# Paragraph merge, native round R-host — references for the host arms of R (written 2026-10-09, before the round ran)

Why: R (`specs/SPEC-M3-paragraph-merge.md` §4.4, `specs/SPEC-M3-production-ui.md` §13) re-binds `check_m3_production_ui.py`'s boundary arms to v19, where B-del and B-bs are no longer refusals. Three things the host arms need are not in any earlier native round:

1. **B-bs's boundary from the body side.** B-bs presses Backspace at the start of the first body paragraph (after the heading 「一、序言」). R0c has that boundary only from the heading side (E02, Delete). Round E's rule for this document says Writer's first Backspace there does not merge (`TryRemoveIndent`, as E10's `Apply attributes`), so the host arm presses twice and the reference is the key arm's second save.
2. **The document's two ends.** On v19 the only refusals left on this document are at its ends (`nothing-selected`, §8 of the merge spec). The document starts with the heading 「一、序言」 and ends with a one-line bullet item (`P16`, "Deputy Chairman, … (2020~2022)"); no table, so no C15–C17 shape exists in it.
3. **Where those places are on v19.** The 109 calibration (`findings/evidence/109/README.md`) was made on v8, whose document is 18551 CSS px tall at 900 wide (≈257,000 twips); v19's is 12474 × 308480 twips (`v19/x6-v5`, finding 114's fix). The old fractions land on other lines. v19's caret equals native's on this document (X6: 11 of 11 cells, x and y to the twip), so the native caret of each case gives the host arm's click.

## Instrument (unchanged)

`tools/merge_native_boundaries.cpp` as R0c ran it (`MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z`), PRESSES=2 (the key arm presses twice, saving `-key.odt` then `-key2.odt`; with PRESSES>1 the key arm types no follow text, the b arm still does). Cases: `wasm_sdk_probe/test-docs/merge/r-host-pmpc.cases.tsv` (this commit).

From `wasm_sdk_probe/`:

    MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z tools/run_merge_native.sh build/merge-native-pmpc/r-host 3 \
        build/scratch-m3-production-ui/PMPC指南.odt test-docs/merge/r-host-pmpc.cases.tsv 2

Saved documents stay under `build/` (the owner's document is not in the repository); `arms.jsonl` and `inputs.sha256` are copied to `r-host/`. Then `tools/check_merge_eshape.py <round dir>`. **Its exit status will be 1 by construction**: it requires every class to occur in a round, and this list has no refusal case. Read its per-case decisions, not its exit.

## Predictions (every round the same)

| Case | b arm (v19's E shape) | key arm, press 1 | key arm, press 2 |
|---|---|---|---|
| E02 heading end, Delete | merge; `content.xml` = key arm's | `Delete paragraph`; `content.xml` byte-equal to R0c's `r1-E02-key.odt` | another `Delete paragraph` (the merged paragraph joins the next one); not used |
| Q01 body start, Backspace | merge decision (K1 selects the `\n`); `content.xml` = key arm press 1 | `Apply attributes` (indent removed); paragraph text sequence equal to the original's | `Delete paragraph`; paragraph text sequence equal to E02's press 1 (「一、序言」 and the body joined into one paragraph) |
| Q02 document start, Backspace | nothing-selected (no key) | Writer acts on the heading's numbering (`Number On/Off`, as E05), or nothing; recorded, not used | recorded, not used |
| Q03 document end, Delete | nothing-selected (no key) | nothing (undo count unchanged); recorded, not used | nothing |

Placement: `placementOk` true in every arm. Carets (twips; x, y, height): E02 (2858, 1658, 521) as R0c; Q01 (1898, 2377, 348) — the body's first line, after its first-line indent, as E02's unit rectangle `1417, 2377, 481, 347` says; Q02 (1418, 1658, 521); Q03 on the last page, height 348 or smaller (Latin text in a bullet item), y below 308480 − 1417.

Uncertain, said in advance: (i) Q01 press 2 might keep the body's paragraph attributes instead of the heading's; the text sequence is the same either way, and only the text sequence is used. (ii) Q02's key arm could do something other than the numbering toggle (no case has measured Backspace at the start of a document); it is not a reference for anything. (iii) Q03's caret height: if the bullet's font is CJK the line is 348.

## What would change the design

- Q01's b arm not a merge decision, or press 1 not `Apply attributes`: K-bs is redesigned before any host run (the arm's meaning depends on press 1 being Writer's intermediate step).
- Q02 or Q03 not `nothing-selected`: that end is not a refusal on v19; the refusal arm moves or is dropped, and the R section says which.
- E02's press 1 not byte-equal to R0c's: the native reference is not stable across sessions; the host comparison stays on paragraph text (it is anyway) and this is recorded.

## Results

(appended after the round)

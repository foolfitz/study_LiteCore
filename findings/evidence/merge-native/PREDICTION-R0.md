# Paragraph merge, native reference round R0 — instruments and predictions (written 2026-10-06, before R0 ran)

R0 is the native reference the WASM criteria of `specs/SPEC-M3-paragraph-merge.md` are measured against (section 4.2 as corrected in 10.2 and 12). It reruns rounds four and six on the **`.odt` bytes WASM will load**, classifies every case into the list a WASM criterion runs, and adds what the reviews asked for: the text typed after the key (where the caret is), "type, then Delete at once" (M2-1b), manual line breaks folded into an earlier delete (10.1(c)), and the undo limit at its default (M2-4).

## Inputs

| File | sha256 | Made from |
|---|---|---|
| `test-docs/merge/odt/boundaries.odt` | `3c17c870…` | `boundaries.fodt`, native `soffice --headless --convert-to odt` (26.8 native build, throwaway profile), once |
| `test-docs/merge/odt/boundaries-indent.odt` | `95009f10…` | `boundaries-indent.fodt`, same |
| `test-docs/merge/odt/line-break-grouping.odt` | `06ce0d85…` | `line-break-grouping.fodt` (new), same |
| `test-docs/merge/odt/undo-limit-105.odt` | `09b5ced0…` | `undo-limit-105.fodt` (new: S01 and 106 empty paragraphs), same |
| the owner's `PMPC指南.odt` (not in the repository) | `7b336879…` | `wasm_sdk_probe/build/scratch-m3-production-ui/`, as rounds E and six |

Full hashes: `sha256sum test-docs/merge/odt/*.odt`; each round also writes `inputs.sha256`.

## Population

`tools/merge_r0_cases.py` writes the case files as the **union of the case files rounds four and six ran** (conflicting rows for one id are an error), plus R0's typed cases; `--check` fails if a written file is stale.

- `r0-boundaries.cases.tsv` (22): `round-g-boundaries`, `round-i-boundaries`, `round-i-tables`, `round-r0-typed` — C01 C02 C03 C08 C09 C15 C16 C17 C27 C29 C30 G01 I02 C10 C11 C12 C13 I03 I01 C14 Y01 Y02.
- `r0-indent.cases.tsv` (4): `round-g-indent` — D01 D04 D08 D12.
- `r0-pmpc.cases.tsv` (11): `round-g-pmpc`, `round-i-pmpc` — E01 E02 E05 E10 E12 T01 P27 E13 E15 P62 P63.
- Separately, not classified: `round-r0-limit` (H03), `round-r0-grouping-g13` (G13), `round-r0-grouping-g14` (G14).

This is a hand population (spec section 8): what R0 says about B stops at these shapes.

## Instruments (this commit)

- **Probe** `tools/merge_native_boundaries.cpp`: an 8th TSV field `pretype` (ASCII typed with key events in every arm right after the checked placement; the b arm's restore then aims at where the typing left the caret, `typedAt`); `MERGE_FOLLOW_TEXT` (typed after the b arm's and the key arm's press, saved again as `-b-follow.odt` / `-key-follow.odt`; the key arm only when PRESSES is 1). Nothing else in the arms changed; the select arm gains one extra selection readback, which changes no state.
- **Runner** `tools/run_merge_native.sh`: writes `follow-text.txt` beside the round.
- **Comparator** `tools/odt_paragraphs.py`: the paragraph text sequence (spans unwrapped, `text:s` expanded, line break as U+2028). Red cases, `--self-test`, run: a character moved inside its paragraph → red; a paragraph split in two → red; a lost line break → red; the same text in other markup → equal. 4/4.
- **Classifier** `tools/classify_merge_r0.py`: classes nothing-selected / barrier / restore-refused / key-noop / merge / typed-merge, in that order of tests; STOP on a missing, fatal, misplaced or unsaved arm, on select and b units differing, on class or restore press count differing between rounds, on a restored B unit whose b arm differs from the key arm (bytes; paragraph text when typed), on follow text landing elsewhere, and on any class empty across all inputs. Run on round six's committed evidence (dry run, not R0): nothing-selected 2, restore-refused 2, key-noop 1, merge 10, and STOP for the two classes that evidence cannot fill (barrier, typed-merge) — as it should. Red cases, run on scratch copies of `restore/round-20261006T090017Z`: one b arm line removed (C12, round 2) → `STOP C12 round 2: arm b missing`; C11 round 1's b document replaced by its select document (select ≠ key for a Backspace at a list item) → `STOP C11 round 1: restore came back but b arm content.xml != key arm`.

## Runs

From `wasm_sdk_probe/`, one at a time (never edit the probe or the runner while one is queued — each run recompiles):

1. `MERGE_RESTORE_PRESSES=2 MERGE_FOLLOW_TEXT=Z tools/run_merge_native.sh ../findings/evidence/merge-native/r0 3 test-docs/merge/odt/boundaries.odt test-docs/merge/r0-boundaries.cases.tsv 1`
2. the same with `boundaries-indent.odt` and `r0-indent.cases.tsv`
3. the same with the owner's document and `r0-pmpc.cases.tsv`, output under `build/merge-native-pmpc/r0` (only arms and summaries are copied into this directory)
4. `MERGE_UNDO_STEPS=100 MERGE_RESTORE_PRESSES=2 tools/run_merge_native.sh build/merge-native-r0-limit 3 test-docs/merge/odt/undo-limit-105.odt test-docs/merge/round-r0-limit.cases.tsv 105` (Steps set to the default explicitly, so the reader's "the count reached the limit" check applies)
5. `tools/run_merge_native.sh build/merge-native-r0-grouping 3 test-docs/merge/odt/line-break-grouping.odt test-docs/merge/round-r0-grouping-g13.cases.tsv 34`, then the same with `round-r0-grouping-g14.cases.tsv` and `2`

Then `classify_merge_r0.py` over runs 1–3 (and 4's round, which classifies H03's first press), `analyze_merge_undo.py` over 4 and 5.

## Predictions

| What | Prediction |
|---|---|
| Classes, boundaries | merge: C01 C02 C03 C08 C09 C10 C11 C12 C13 C14 C27 I01 I02 I03 (14); restore-refused: C15 C16; key-noop: C17; nothing-selected: C29 C30; barrier: G01; typed-merge: Y01 Y02 |
| Classes, indent and owner's document | merge: D01 D04 D08 D12; E01 E02 E05 E10 E12 T01 P27 E13 E15 P62 P63 |
| H03 | merge (its first press) |
| Restore presses | 2 for I02 C08 C10 I03 I01 Y02 P27 E13 P62 P63 (next paragraph labelled); 1 for every other restored case; equal across the three rounds |
| Comments | as rounds four and six (`Delete paragraph`, `Number On/Off`, `Apply attributes`, `Delete One line break`, `Delete Paragraphs`) |
| `.odt` instead of `.fodt` | no class changes; byte equality b = key wherever it held |
| Follow text `Z` | lands at the same paragraph and position after the b arm as after the key arm, every merge and typed-merge case |
| Y01, Y02 | the typed `x` survives and the paragraphs merge after it; Y02 needs 2 restore presses like C08 |
| H03 (Steps=100, 105 presses) | count 1…100, then 100; the payload changes on every press (at the limit the list shifts; it could only stay the same if all 100 entries were identical); 0 disagreements |
| G13 (34 presses) | presses 1–19 change the payload; 20–30 (full stops) do not while the document does (as G10/G11: the shortened comment stops changing); 31 and 32 (first and second line break, folded into the same action) change it; **33 (third line break) does not** — the comment is `“…”3 line breaks` shortened to 9 front and 8 back characters (`ShortenString`, `nUndoStringLength` 20, `UndoCore.hxx:247`; `DenoteSpecialCharacters`, `undel.cxx`), identical to press 32's; 34 (a letter, not folded) changes it |
| G14 (2 presses) | both change the payload (`Delete “ ”`, then the space and the line break folded under a new comment) |

What would change the decision:

- Any STOP from the classifier: B's sequence is not Writer's key on that shape, or R0 is incomplete; nothing goes to WASM until it is explained.
- G13 press 33 as predicted: a document change B cannot prove (10.1(c)) → v15 gives a key-deadline refusal there (honest under 10.1(d), a false refusal). If instead 31–33 never fold, 10.1(c)'s registration is withdrawn.
- H03 with any disagreement: the whole-payload proof fails at the default limit.
- Y01 or Y02 not typed-merge: the native reference for M2-1b does not exist in that shape.

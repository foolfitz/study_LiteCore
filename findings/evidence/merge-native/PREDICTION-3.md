# Paragraph merge, native, third round — predictions (written 2026-10-06, before the round ran)

Round D (`round-20261006T073255Z`) came out exactly as `PREDICTION-2.md` said: every boundary reads back `[10]`, Delete at a paragraph's end equals the key everywhere, and Backspace at the start of an unlabelled heading or of an indented paragraph differs from the key (Writer marks the heading not counted, or removes the indent, instead of merging). The first round's C03/C09/C11/C14 differ for the same family of reasons (numbered heading, list items).

The question this round answers: **where Writer's first Backspace does something other than merge, does pressing it again reach the document the select arm's single delete gives?** If yes, a merge on Backspace is "Writer's end state with the intermediate presses skipped", and the spec can say exactly that; if not, merging there produces a document Writer would never produce.

Same probe with a 7th argument `PRESSES=3` (`tools/merge_native_boundaries.cpp`): the key arm presses its key three times and saves after each press (`-key.odt`, `-key2.odt`, `-key3.odt`). The select arm is unchanged. The reader reports `keyPressesToMatchSelect` per round: the first press after which the key's document equals the select arm's (1 = the first press already did), or `null` if none of the three did.

Cases (3 rounds each, every case's positive control first):

- `boundaries.fodt` with `boundaries.backspace.cases.tsv`: C01 (control), C02, C03, C09, C11, C14.
- `boundaries-indent.fodt` with `boundaries-indent.backspace.cases.tsv`: D01 (control), D03, D04, D07, D08, D10, D11, D12, D14.
- The owner's PMPC document with `pmpc.backspace.cases.tsv`: E01 (control) and the E cases that round E finds differing (predicted: E03, E04, E05, E07, E09, E10, E12, E14, E16, E17). Run under `wasm_sdk_probe/build/`, as round E.

## Predictions, from the source read in `PREDICTION-2.md`

Press 1 does Writer's first step; the paragraph is then not counted (headings, list items) or has a smaller indent. A not-counted paragraph's next Backspace goes to `TryRemoveIndent`; when there is nothing left to remove, the key falls through to the plain backspace, which merges. When the merge happens, the merged paragraph keeps the upper paragraph's attributes, as the select arm's does, so the documents are equal.

| Case | Writer's steps (prediction) | presses to match |
|---|---|---|
| C01, D01 (⌦), C02, D03 | merge | 1 |
| C03 numbered heading | not counted → merge | 2 |
| C09, C11, C14 list items (no paragraph indent) | list header → merge | 2 |
| D04, D07 unlabelled heading | not counted → merge | 2 |
| D08, D10, D14 first-line indent | indent removed → merge | 2 |
| D11 left margin | margin removed → merge | 2 |
| D12 hanging indent | first line folded into the margin → margin removed → merge | 3 |
| E03, E04, E10 first-line indent | as D08 | 2 |
| E05, E07, E09 unlabelled heading | as D04 | 2 |
| E16 indented body under a numbered item | as D08 | 2 |
| E12, E14 numbered items whose paragraph style has no indent (WW8Num3, parent "Text body (user)") | as C11 | 2 |
| E17 bullet items whose paragraph style has a first-line indent (WW8Num4, parent "First line indent (user)") | list header → indent removed → merge, **if** the style's indent reaches `TryRemoveIndent` for a list paragraph; unknown | 3, or 2 |

Undo is not exercised in this round's key arm (the select arm still undoes and is still checked).

What would change the design: any `null` (three presses never reach the merged document), or a case that matches at 1 although round D/E said "differs" (the instrument changed under us).

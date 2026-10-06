# Paragraph merge, native, second round — predictions (written 2026-10-06, before the round ran)

Closes the fixture gap named in `handoff/HANDOFF-2026-10-06d-paragraph-merge-measured-natively.md` (next step 2): the owner's `PMPC指南.odt` is built from two shapes the first fixture did not have.

- **Headings in an outline whose number format is empty** (PMPC: all ten levels `style:num-format=""`, label followed by a tab; "一、序言" is typed text). The first fixture's headings were outline-numbered `1.`.
- **Body paragraphs with an indent** (PMPC: "First line indent (user)", `fo:text-indent="0.847cm"`, on nearly every body paragraph). The first fixture's body paragraphs had none.

Same probe, now taking its cases from a file (`tools/merge_native_boundaries.cpp`, 6th argument); same runner (`tools/run_merge_native.sh OUT ROUNDS FIXTURE CASES`); 3 rounds each.

- Round **D**: `wasm_sdk_probe/test-docs/merge/boundaries-indent.fodt` with `boundaries-indent.cases.tsv` (15 cases). Everything is committed.
- Round **E**: a per-round copy of the owner's `PMPC指南.odt` (sha256 `7b336879…`, not in the repository) with `pmpc.cases.tsv` (18 cases). The round runs under `wasm_sdk_probe/build/` because every arm saves a copy of the owner's 550 KB document; `arms.jsonl`, `inputs.sha256` and the reader's summary are copied here.

The reader (`tools/analyze_merge_native.py`) now also sees a heading's `text:is-list-header`, the indents an automatic paragraph style sets, and bookmarks; soft page breaks are dropped. Re-run on the first counted round (`round-20261006T065130Z`) it gives the same verdicts, undo results and unit signatures for all 29 cases; the only change is C03's detail, which now shows what the key did: `listHeader=true` on the heading.

## What the source says, and so what I expect

Read in `libreoffice-26-8` before writing this:

- `SwEditWin::KeyInput`, `KEY_BACKSPACE` (`sw/source/uibase/docvw/edtwin.cxx:2048–2130`): at a paragraph's start with no selection, if the paragraph has **no numbering rule**, Writer first calls `SwWrtShell::TryRemoveIndent` (`sw/source/uibase/wrtsh/delete.cxx:64`), which zeroes a positive first-line indent, or folds a negative one into the left margin, or zeroes a left margin, and if it did any of that **the key is done** — nothing merges. If the paragraph **has a rule** and is counted, Writer calls `NumOrNoNum(false)` — the paragraph stops being counted — and nothing merges. A heading in the outline has the outline rule even when its format is empty.
- `.uno:SwBackspace` / `.uno:Delete` on a selection (`sw/source/uibase/shells/basesh.cxx:233–300`) just delete the selection; neither path above runs. The select arm will merge wherever it dispatches.
- `KEY_DELETE` has only an in-front-of-label case; at a paragraph's end it merges.
- The plain-text readback of the selection (`sw/source/filter/ascii/ascatr.cxx:262–293`) writes a label for a paragraph with a numbering rule, **except** for the outline rule, where it writes only `GetNumString()` — empty when the format is empty. So an unlabelled heading adds nothing to the unit's text.

Consequence, as a prediction: **Backspace at the start of an unlabelled heading or of an indented paragraph will read back exactly `[10]` and still differ from the key.** If that holds, "the unit is exactly one U+000A" is not enough to merge on Backspace, and in the owner's document it would be wrong at almost every paragraph start. Delete (⌦) at a paragraph's end is predicted unaffected.

"Unknown" below is a prediction that I do not know.

## Round D (synthetic)

| Case | Key | Boundary | Unit (prediction) | select = key? | Why |
|---|---|---|---|---|---|
| D01 | ⌦ | body\|body (positive control) | `[10]` | yes | as C01 |
| D02 | ⌦ | unlabelled heading\|body | `[10]` | yes | Delete merges |
| D03 | ⌫ | unlabelled heading\|body (at the body's start) | `[10]` | yes | body has no rule and no indent; as C05 |
| D04 | ⌫ | body\|unlabelled heading (at the heading's start) | `[10]` — the empty label writes nothing | **no** | the key marks the heading not counted (`listHeader=true`), nothing visible changes; the select arm merges |
| D05 | ⌦ | body\|unlabelled heading (at the body's end) | `[10]` | yes | |
| D06 | ⌦ | unlabelled H1\|H2 | `[10]` | yes | |
| D07 | ⌫ | unlabelled H1\|H2 (at H2's start) | `[10]` | **no** | as D04 |
| D08 | ⌫ | body\|first-line-indented (at its start) | `[10]` | **no** | the key zeroes the first-line indent |
| D09 | ⌦ | body\|first-line-indented (at the body's end) | `[10]` | yes | |
| D10 | ⌫ | indented\|indented | `[10]` | **no** | as D08 |
| D11 | ⌫ | indented\|left-margin (at its start) | `[10]` | **no** | the key zeroes the left margin |
| D12 | ⌫ | left-margin\|hanging (at its start) | `[10]` | **no** | the key folds the negative first line into the left margin |
| D13 | ⌫ | hanging\|body (at the body's start) | `[10]` | yes | the indent is on the paragraph above; the one at the caret has none |
| D14 | ⌫ | unlabelled heading\|indented (at the indented start) | `[10]` | **no** | as D08 |
| D15 | ⌦ | unlabelled heading\|indented (at the heading's end) | `[10]` | yes | |

Undo restores in every dispatched arm. Rectangle counts: unknown, 1–4 as before.

## Round E (the owner's document)

| Case | Key | Boundary | Unit (prediction) | select = key? |
|---|---|---|---|---|
| E01 | ⌦ | indented body\|H1 (positive control) | `[10]` | yes |
| E02 | ⌦ | H1\|indented body | `[10]` | yes |
| E03, E04 | ⌫ | H1\|indented body, H2\|indented body (at the body's start) | `[10]` | **no** (indent removed) |
| E05 | ⌫ | indented body\|H1 (at the heading's start) | `[10]` | **no** (heading not counted) |
| E06 | ⌦ | H1\|H1 | `[10]` | yes |
| E07 | ⌫ | H1\|H1 (at the second's start) | `[10]` | **no** (not counted) |
| E08 | ⌦ | H1\|H2 | `[10]` | yes |
| E09 | ⌫ | H1\|H2 (at H2's start) | `[10]` | **no** (not counted) |
| E10 | ⌫ | indented\|indented | `[10]` | **no** (indent removed) |
| E11 | ⌦ | indented\|indented | `[10]` | yes |
| E12 | ⌫ | indented body\|numbered item (at the item's start) | LF + the item's label (`1.` with leading spaces) | **no** (as C09: list header) |
| E13 | ⌦ | numbered item\|numbered item | label + LF + label | yes (as C10) |
| E14 | ⌫ | numbered item\|numbered item (at the second's start) | label + LF + label | **no** (as C11/C14) |
| E15 | ⌦ | last numbered item\|indented body | label + LF | yes (as C12) |
| E16 | ⌫ | last numbered item\|indented body (at the body's start) | label + LF | **no** — unlike C13, whose body had no indent |
| E17 | ⌫ | bullet item\|bullet item (at the second's start) | label + LF + label | **no** (as C11) |
| E18 | ⌦ | indented body\|H2 | `[10]` | yes |

Undo restores in every dispatched arm. The headings' `__RefHeading___Toc…` bookmarks (used by the document's table of contents) are kept by both arms where both merge — predicted, not known.

## What would change the design

- If D04/D07/D08/D10–D12/D14 and E03–E05/E07/E09/E10 come out **same**, the source reading is wrong somewhere and the first round's direction (accept `[10]`) stands.
- If they come out **differs** with a `[10]` unit, the barrier cannot tell them from a mergeable boundary by the unit's text. Backspace at a paragraph's start then needs another readback before dispatch (whether the paragraph is in a numbering rule and counted, whether it has an indent), or a narrower rule (merge only on Delete; on Backspace, do what Writer does or refuse) — the spec's question, not this round's.
- Instrument risks: the search may not land on the long CJK anchors; the placement self-check (caret-to-edge text equals the anchor) says so per arm. The document is large; if loads or searches outrun the probe's fixed waits, the self-check and the per-round agreement say so.

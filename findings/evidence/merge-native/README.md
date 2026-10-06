# Paragraph merge, native — what the barrier would see and do at every boundary kind

Owner's request (2026-10-06): a delete at a paragraph boundary should merge the paragraphs instead of being refused (finding 109's option C). Before any engine change, this measures on native LibreOffice 26.8 (`native-lok-26-8`, `SAL_USE_VCLPLUGIN=svp`, no relink) what the shipped selection barrier would see at each boundary kind and what deleting that selection does, against the user's own key. Predictions were committed first (`PREDICTION.md`, `da0d59eb`).

Probe `wasm_sdk_probe/tools/merge_native_boundaries.cpp`, runner `tools/run_merge_native.sh`, reader `tools/analyze_merge_native.py`, fixture `wasm_sdk_probe/test-docs/merge/boundaries.fodt` (29 cases, one anchor each). Per case and round: arm **select** = Shift+Left/Right (the barrier's one-unit selection), readback, `.uno:SwBackspace` / `.uno:Delete` on the selection, save, `.uno:Undo`, save; arm **key** = Backspace / Delete on the collapsed caret, save. Saved documents are reduced to block lists (resolved paragraph style, outline level, list membership and type, break-before, tables, sections, line-break and frame markers) and compared.

## The counted round: `round-20261006T065130Z/`

3 rounds × 29 cases × 2 arms. Inputs' sha256 in `inputs.sha256` (fixture `a926268d…`, probe `df936cb5…`). `summary.json` is the reader's output; `docs/` holds every saved document.

Checks on the instrument, all passing: the positive control (Writer's own Delete at C01 changes the document) holds; every arm's placement self-check holds (caret-to-paragraph-edge text equals the anchor); every case gives the same unit signature and the same verdict in all three rounds; every dispatched `.uno:Delete` / `.uno:SwBackspace` reported `success: true` and left a collapsed selection (81/81).

| Case | Key | Boundary | Unit selected (type 1 = text; code points) | Delete of the selection vs the key |
|---|---|---|---|---|
| C01, C02 | ⌦, ⌫ | body\|body | `[10]` | same |
| C04, C05 | ⌦, ⌫ | numbered heading\|body | `[10]` | same |
| C06, C07 | ⌦, ⌫ | body\|empty, empty\|body | `[10]` | same |
| C19, C20 | ⌦, ⌫ | body\|body with a paragraph-anchored frame | `[10]` | same |
| C21, C22 | ⌦, ⌫ | body\|body with a page break | `[10]` | same |
| C23–C26 | ⌦, ⌫ | into and out of a section | `[10]` | same |
| C27, C28 | ⌦, ⌫ | line break inside a paragraph | `[10]` | same |
| C08 | ⌦ | body\|bullet item | `[10, 32×4, 8226, 32]` (LF + the item's label) | same |
| C10 | ⌦ | bullet item\|bullet item | label + LF + label | same |
| C12, C13 | ⌦, ⌫ | bullet item\|body | label + LF | same |
| C03 | ⌫ at a numbered heading's start | body\|numbered heading | `[10, 49, 46, 32]` (LF + "1. ") | **differs**: the key removes the heading's number; the select arm merges the heading into the paragraph above |
| C09, C11, C14 | ⌫ at a list item's start | body\|bullet, bullet\|bullet, number\|number | LF with labels | **differs**: the key turns the item into a list header (label gone, paragraph kept); the select arm merges |
| C15, C16 | ⌦ before / ⌫ after a table | body\|table, table\|body | **the whole table's text** (`"\nM17 cell one\tM17b cell two\n"`) | **differs, destructively**: the select arm deletes the entire table and merges the paragraphs around it; the key changes nothing |
| C17 | ⌦ at a cell's end | cell\|cell | the whole row's text | **differs, destructively**: the select arm empties both cells; the key changes nothing |
| C29, C30 | ⌫ at the document start, ⌦ at its end | — | nothing (type 0) | not dispatched; the key changes nothing |

Rectangle counts of the unit selection vary between 1 and 4 for the same code points (`[10]`: 1 to 4), so the shipped barrier's "exactly one rectangle" cannot be part of a merge rule.

One `.uno:Undo` restored the original document in every dispatched arm (81/81), **although `.uno:Undo` reported `success: false` every time**: its command result is not evidence of whether it undid anything.

### Against the predictions

Right: `[10]` for the plain kinds; select = key for them; the list/heading Backspace cases differ because the key removes the label first; undo restores; nothing selected at the document's ends. Wrong: the unit's text at list and numbered-heading boundaries carries the label characters (predicted plain `[10]`); the table cases select the whole table (predicted "unknown, maybe `[10]`"), and deleting it is destructive; sections behave like plain paragraphs (predicted unknown).

## What this says for the design

- A unit selection whose text is **exactly one U+000A** can be deleted on the barrier's existing proof (command success + collapsed selection) and gives Writer's own result in every kind measured: plain, heading, empty, anchored frame, page break, section, line break.
- **Tables must stay refused**, and they are recognisable before dispatch: their unit is the table's text, never `[10]`.
- Label-decorated units are a second step: Delete at an item's end merges as the key does; Backspace at an item's (or numbered heading's) start must not merge — Writer removes the label instead.
- Not measured here: the WASM engine (same core, but the shipped engine reads through the same API on a different build), the a11y core's semantic precheck, nested lists, tracked changes, fields, footnotes, right-to-left text, and documents other than this fixture (the owner's `PMPC指南.odt` included).

## Rounds that do not count

- `round-20261006T063607Z-instrument-fault/`: the caret was placed with `.uno:GoToEndOfPara` straight after a search whose hit already ended at the paragraph's end, which moves on to the next paragraph's end (C01 measured P2's boundary). Stopped; placement now goes to the start first, then the end, and checks itself.
- `round-20261006T063803Z-read-only-fault/`: the killed run above left `.~lock.boundaries.fodt#` beside the fixture, so every load was read-only; every save equalled the original and `.uno:Delete` reported `success: false`. The unit signatures it recorded match the counted round. The runner now loads a per-round copy, and the reader fails unless the positive control changed the document (it fails on this round, as it should). Saved documents of both faulty rounds were removed; their `arms.jsonl` are kept.

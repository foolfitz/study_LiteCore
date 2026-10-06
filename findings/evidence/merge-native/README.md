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

## Second round, D: unlabelled headings and indents (`round-20261006T073255Z/`)

Why: the owner's `PMPC指南.odt` is made of two shapes the first fixture did not have — headings in an outline whose number format is empty (no visible label), and body paragraphs with a first-line indent. Predictions first (`PREDICTION-2.md`, `c35d350c`), written from a source read: Writer's Backspace at a paragraph's start marks a numbered paragraph not counted (`NumOrNoNum`) or removes an indent (`SwWrtShell::TryRemoveIndent`) before it ever merges, and the plain-text readback writes nothing for an empty outline label.

Fixture `wasm_sdk_probe/test-docs/merge/boundaries-indent.fodt`, cases `boundaries-indent.cases.tsv` (15), 3 rounds. Reader as above plus three things it now sees: a heading's `text:is-list-header`, the indents an automatic paragraph style sets, and bookmarks (re-run on the first counted round it gives the same verdicts for all 29 cases; only C03's detail gains `listHeader=true` — what the key did there).

Checks: positive control D01 changed the document; placement self-check held on every arm; one unit signature and one verdict per case across all three rounds; 45/45 dispatches `success: true` with a collapsed selection; 45/45 undos restored the original.

| Case | Key | Boundary | Unit | Delete of the selection vs the key |
|---|---|---|---|---|
| D01 | ⌦ | body\|body (control) | `[10]` | same |
| D02, D05, D06, D09, D15 | ⌦ | unlabelled heading\|body, body\|unlabelled heading, H1\|H2, body\|indented, unlabelled heading\|indented | `[10]` | same |
| D03, D13 | ⌫ | unlabelled heading\|body, hanging\|body — the paragraph at the caret has no rule and no indent | `[10]` | same |
| D04, D07 | ⌫ at an unlabelled heading's start | body\|heading, H1\|H2 | `[10]` | **differs**: the key marks the heading not counted (`listHeader=true`, nothing visible changes); the select arm merges |
| D08, D10, D14 | ⌫ at a first-line-indented paragraph's start | | `[10]` | **differs**: the key sets the first-line indent to 0 |
| D11 | ⌫ at a left-margin paragraph's start | | `[10]` | **differs**: the key sets the left margin to 0 |
| D12 | ⌫ at a hanging-indent paragraph's start | | `[10]` | **differs**: the key folds the negative first line into the left margin (1 cm − 0.5 cm) |

Every prediction held. **A unit of exactly `[10]` is enough to merge on Delete, not on Backspace**: at a paragraph's start, what Writer's key does depends on the numbering and indent of the paragraph at the caret, which the readback does not show.

## Round E, first attempt, does not count (`wasm_sdk_probe/build/merge-native-pmpc/round-20261006T073914Z-second-search-fault/`, not in the repository)

The owner's document (sha256 `7b336879…`), `pmpc.cases.tsv`. Stopped after 80 arms. **The select arm searched for its anchor twice** — once for the placement self-check, once more to place the caret — and the second search went on from the first hit. Every heading in the document has a copy in the table of contents at its end, so for the heading cases (E02, E05–E09) the self-check passed on the heading while the unit was selected in the table of contents; the key arm, which searched once, measured the heading. Visible in the unit rectangles: E02 and E05, two different boundaries, report the same rectangle at y ≈ 276,582 twips (page 17), and both arms' documents disagree in ways no boundary explains. Anchors that occur once (every case of the first round and of round D, and E's body paragraphs) are not affected: a second search can only find the same paragraph.

Fixed in `9d5c2448`: the caret is placed from the document's start with one search, checked, and returned to with a move that cannot leave the paragraph; the key arm checks itself the same way; both arms record the drawn caret (`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`) and the reader requires the two to be equal. A one-round shakedown on E01/E02/E05 (not counted) put both arms' caret at the same place on page 1.

What this attempt still shows, and is followed up in the fourth round: in the table of contents (a protected section) `.uno:Delete` / `.uno:SwBackspace` on a `[10]` selection reported `success: true` and left a collapsed selection — **the shipped barrier's whole completion proof** — while the saved document equalled the original byte for byte in the reduction. Nothing changed, and the proof could not tell.

The runner was edited while this attempt was running (to add `PRESSES`); bash reads a script as it runs, so after the probe was killed the runner died with `unexpected EOF` and its cleanup did not run (the profile, the binary and the lock file were removed by hand). Do not edit a runner while it runs.

## Round E, the owner's document (`pmpc-round-20261006T075511Z/`; saved documents under `wasm_sdk_probe/build/merge-native-pmpc/`, not in the repository)

`PMPC指南.odt` (sha256 `7b336879…`), `pmpc.cases.tsv` (18), 3 rounds, probe `f1860939…` (`9d5c2448`, the one-search placement), PRESSES=3 (the first press is the round-E protocol; the later two serve the multi-press question below). Positive control E01; both arms' caret drawn at the same place in every case and round; one signature and one verdict per case; 54/54 undos restored.

| Case | Key | Boundary | Unit | vs the key | presses to match |
|---|---|---|---|---|---|
| E01, E02, E06, E08, E11, E18 | ⌦ | indented body\|H1, H1\|indented body, H1\|H1, H1\|H2, indented\|indented, indented\|H2 | `[10]` | same | 1 |
| E13, E15 | ⌦ | numbered item\|item, item\|indented body | label + LF (+ label) | same | 1 |
| E03, E04, E10 | ⌫ at an indented paragraph's start | H1\|body, H2\|body, body\|body | `[10]` | differs (indent removed) | 2 |
| E05, E07, E09 | ⌫ at a heading's start | body\|H1, H1\|H1, H1\|H2 | `[10]` | differs (heading not counted) | 2 |
| E12, E14 | ⌫ at a numbered item's start (paragraph style without indent) | body\|item, item\|item | LF with labels | differs (list header) | 2 |
| E16 | ⌫ at an indented body's start under a list | | label + LF | differs (indent removed) | 2 |
| E17 | ⌫ at a bullet item's start whose paragraph style has a first-line indent | | labels + LF | differs (list header, then indent removed) | **3** |

Every prediction in `PREDICTION-2.md` held, and E17 came out on the "3" side of "3, or 2". In the owner's document, **every Backspace at a paragraph's start that was measured differs from the key**; every Delete at a paragraph's end equals it. Where a heading's table-of-contents bookmark sat at the boundary (E02, E06, E08), both arms did the same thing to it.

## Multi-press rounds (`presses/round-20261006T074710Z/`, `presses/round-20261006T075024Z/`)

Predictions `PREDICTION-3.md` (`076ac980`); probe `f1860939…`, PRESSES=3: the key arm presses its key three times and saves after each. Cases `boundaries.backspace.cases.tsv` (C01, C02, C03, C09, C11, C14) and `boundaries-indent.backspace.cases.tsv` (D01, D03, D04, D07, D08, D10, D11, D12, D14). Same checks as above, all passing.

| Case | Writer's steps | presses until the key's document equals the select arm's |
|---|---|---|
| C01, C02, D01, D03 | merge | 1, 1, 1 |
| C03 (numbered heading), D04, D07 (unlabelled heading) | not counted → merge | 2, 2, 2 |
| C09, C11, C14 (list items) | list header → merge | 2, 2, 2 |
| D08, D10, D14 (first-line indent), D11 (left margin) | indent removed → merge | 2, 2, 2 |
| D12 (hanging indent) | first line folded into the margin → margin removed → merge | 3, 3, 3 |

With round E: **deleting the barrier's selection at a paragraph's start gives Writer's own document after two presses (three for a hanging indent or an indented list item), in every shape measured**; it never gives a document Writer cannot reach. That is option A's exact cost: it skips the intermediate state(s).

## Fourth round: option B's sequence and the undo stack (`undo/`)

Why: the owner chose **B′** (2026-10-06) — measure whether option B can work before choosing between it and A. B = keep the selection barrier for deletes inside a paragraph; at a boundary, take the unit selection back, press the user's own key, and prove what it did from the undo stack (`getCommandValues(".uno:UndoCount")`, `".uno:Undo"`). Predictions `PREDICTION-4.md` (`202153b5`). Probe as committed there: arm **b** (unit selection → the opposite arrow *without* Shift, only when something was selected → the user's key), the undo stack around every dispatch and press, TSV fields `occurrence` and `offset`. Reader `tools/analyze_merge_undo.py`.

Shakedowns before the predictions (not counted): Shift + the opposite arrow brings the caret back but leaves the empty selection's mark, and the key that follows changes nothing; an unshifted arrow when nothing was selected (document start) moves the caret, and Backspace then deleted "M".

### `undo/round-20261006T081216Z/` (boundaries.fodt, 12 cases) and `undo/round-20261006T082156Z/` (boundaries-indent.fodt, 4 cases), PRESSES=3

Placement held on every arm (all three arms' caret drawn at the same place), one unit signature per case, select-vs-key verdicts as in rounds 1 and D.

| Case | Arm b: caret back at the placed caret | Arm b = key arm's first press | Undo comment |
|---|---|---|---|
| C01, C02, D01 (merge) | 3/3 | 3/3, **content.xml byte-identical** | `Delete paragraph` |
| C27 (line break) | 3/3 | 3/3, identical | `Delete One line break` |
| C03 (numbered heading), D04 (unlabelled heading), C09 (list item) | 3/3 | 3/3, identical | `Number On/Off` |
| D08 (first-line indent), D12 (hanging indent) | 3/3 | 3/3, identical | `Apply attributes` |
| G01 (two characters, then the boundary) | 3/3 | 3/3, identical | `Delete “0”` (press 1; presses 1–2 fold, press 3 the join is a new action) |
| **C08** (Delete at a body's end before a bullet item) | **0/3** — the unshifted Left lands in front of the item's label, not at the body's end | 0/3: the key then did `Number On/Off` where Writer's own key merges | — |
| C15, C16 (table) | 0/3 (the unit is the table) | the key changed nothing either way | — |
| C17 (cell end), C29, C30 (document start, end) | 3/3 | the key changes nothing; stack unchanged | — |

Undo stack against `content.xml`, every press of every arm: **234 presses, 0 disagreements** — the stack changed exactly when the document did, including every "nothing changed" press.

### `undo/round-20261006T082510Z/` (undo-grouping.fodt, 3 cases, PRESSES=25)

| Case | Presses where the document changed and the stack did not |
|---|---|
| G12, Backspace through distinct characters (control) | none, 3 rounds (one folded action; its comment changes on every press) |
| **G10**, Backspace through a run of "a" | **20–25**, all 3 rounds |
| **G11**, Delete through the same run | **20–25**, all 3 rounds |

The comment of a folded delete is the deleted text shortened to `aaaaaaaa...aaaaaaa`; from press 20 it is the same string, the count stays 1, and the stack no longer shows the change. As predicted from `ShortenString` — and the reason B cannot replace the barrier inside a paragraph. At a boundary nothing folds (G01: the join after two folded deletes is a new action).

### `undo/pmpc-round-20261006T083157Z/` (the owner's document, 6 cases, PRESSES=3; saved documents under `wasm_sdk_probe/build/`)

| Case | Arm b: caret back | Arm b = key (content.xml bytes) | Undo comment |
|---|---|---|---|
| E01 (⌦ indented body\|H1), E02 (⌦ H1\|indented body, a TOC bookmark at the boundary) | 3/3 | 3/3 | `Delete paragraph` |
| E05 (⌫ at an unlabelled heading's start) | 3/3 | 3/3 | `Number On/Off` |
| E10 (⌫ at an indented paragraph's start) | 3/3 | 3/3 | `Apply attributes` |
| E12 (⌫ at a numbered item's start) | 3/3 | 3/3 | `Number On/Off` |
| T01 (⌦ at the end of the table of contents' title 「目次」) | 3/3 | 3/3 | `Delete Paragraphs` |

90 presses, 0 stack-vs-content disagreements. **T01 was predicted wrong**: the prediction called the whole table of contents protected, and Writer's own Delete merges its title 「目次」 into the first entry (23 → 22 index paragraphs; the block reduction treats the index as one opaque block and could not see it — `content.xml` and the undo stack did). The no-op that the first round-E attempt recorded happened between two index *entries*, not at the title. So round four does not re-measure the barrier's proof failing on a no-op; a fifth round that wants to must aim at an index entry (whose text carries a tab, which the TSV cannot hold today).

## What the four rounds say for B

- At every paragraph boundary measured — plain, line break, numbered and unlabelled headings, list items, first-line, left and hanging indents, headings with table-of-contents bookmarks, in the fixtures and in the owner's document — B's sequence produced **the same `content.xml` as Writer's own key, 3/3**, and the caret came back to where it was placed before the key.
- The undo stack changed **exactly** when the document did on every press at a boundary or on a no-op (324 presses across the three boundary batches: 174 + 60 + 90); it fails only for a long run of identical characters deleted one by one inside a paragraph (G10, G11 from press 20), where B is not used.
- Where the step cannot be taken back (C08: Delete before a bullet item lands in front of the label; C15, C16: a table selected whole), the caret check fails every time, so B can refuse there before pressing anything.
- Not measured here, and needed before B ships: the order of a posted key and the engine's undo readback on WASM; the undo stack at its limit (the count saturates; the whole payload must be compared); a delete on a real no-op inside a protected index entry.

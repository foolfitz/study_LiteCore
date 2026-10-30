# The 083 path, ruling 3 Q5.2: native arm for a second selection after `select-text-returned-none`

**Results, by `tool/read_q52.py out` (`out/reader-output.json`), against `PREDICTION.md`.** The criteria were registered and committed (`15cd044a1`) before the counted run. Amendment 1 (after the smoke) changed nothing.

| verdict | result |
|---|---|
| **V1**: SelectAll, rule ONE, the blank one-paragraph document | **`ONE-BLOCK-DOES-NOT-VERIFY`** -- fail closed: SelectAll selects nothing there |
| action scope on one-paragraph documents | not read (V1 does not hold); all five actions recorded `OUT-OF-SCOPE` for the same reason |
| **V2**: SelectAll, rule LAST, multi-paragraph | **`LAST-HOLDS`**: covered a4, a7, a8, s1, s2; tables refused (fail closed); shams safe |
| **V3**: CharLeftSel, rule LAST, multi-paragraph | **`LAST-HOLDS`**: covered a4, a7, a8, s1, s2; the table cell refused (fail closed); shams safe |

No round anywhere has a rule satisfied while the saved paragraph does not match (`ONE-BLOCK-UNSAFE` and `LAST-UNSAFE` are both empty).

## What was run

- **Harness** `tool/f083_native.cpp`: 176's `f176_native.cpp` (sha `cb4d9f41...`) plus op H. H is G (v27's collapsed order) followed by, only when the `.uno:SelectText` read is NONE:
  - the fallback command;
  - its synchronous read;
  - the full `text/html` if TEXT;
  - then G's restore and read.
- **Build**: `build-01/build-receipt.json`. A single-file g++ build, 1.73 s; source sha `0ed34947...`, binary sha `b3b4d293...`. The binary is not committed.
- **Runner**: `../native/tool/run_cells.py`, unedited, with the cell table in `tool/run_cells_q52.py`. `out/identity.json` and `out/identity-q52.json` carry the sources and fixtures.
- **Core**: `native-lok-26-8`, buildid 671c848b (the N1/176 core).
- **Mode**: uni1ai. 27 cells x 5 rounds = 135 processes, 2026-10-30 09:20-09:49Z, all exit 0, load1 <= 0.59.
- **Fixtures**: `tool/make_fixtures_q52.py`, `fixtures/SHA256SUMS`. `blank-one.odt` is the host's blank template (`7e6221b6...`).
- **Ground truth**: the last paragraph of each round's saved FODT (`out/<cell>/rN.fodt.gz`).

## Findings

### 1. The blank document has no selection to read

**The observation.** In `sa-a5` (the host's blank template) `.uno:SelectAll` reports `success: true` and the read after it is NONE, with empty text and no markup, 5/5. The same holds:
- after the four other paragraph actions (`sa-num`, `sa-head`, `sa-none`, `sa-body`);
- for the sham (`sa-n5`);
- for the already-bulleted no-op (`sa-r1`);
- for CharLeftSel at the document start (`cl-a5`).

**Why.** A document whose only paragraph is empty has no non-collapsed selection, so `getSelectionTypeAndText` returns NONE.

**Consequence.** The ruling's premise for the owner's case ("`.uno:SelectAll` on a one-paragraph document yields exactly one block") does not hold. That document is the only one-paragraph 083 case, because a one-paragraph document with text is not on the 083 path. No selection-based readback can verify an action there.

### 2. On a multi-paragraph document, the last block of the readback is the dispatch paragraph

**SelectAll and CharLeftSel both read TEXT.** The last block-level tag's list context and tag equal the saved last paragraph in every clean round of every covered cell:

| cell | SelectAll blocks | CharLeftSel blocks | first block | last block | saved |
|---|---|---|---|---|---|
| a4: text, empty last | 2 | 2 | none/p | ul/p | bullet |
| a7: End, Enter at the last paragraph | 3 | 2 | none/p | ul/p | bullet |
| a8: a bullet item, empty last | 2 | 2 | ul/p | ul/p | bullet |
| s1: a section before it | 2 | 2 | none/p | ul/p | bullet |
| s2: the empty last paragraph in a section | 2 | 2 | none/p | ul/p | bullet |
| n4: sham | 2 | 2 | none/p | none/p | not in a list |
| n8: sham after a bullet item | 2 | 2 | **ul/p** | none/p | not in a list |
| ns2: sham in a section | 2 | -- | none/p | none/p | not in a list |

- **The first block is the wrong block here.** Rule FIRST (the existing predicate without the multi-block refusal) has two failures:
  - it would report `postcondition-not-met` on every applied cell except a8;
  - it is **satisfied on the n8 sham**, under both fallbacks, while the paragraph is not in a list.

  So on this path the judgement needs a last-block field, not the existing first-block one.
- **Sections are invisible to the markup.** No `<div>` was emitted for a section in any readback.
- **The predicted section-only SelectAll did not show.** In s2 SelectAll selected the whole document, not the section: an empty paragraph that is the section's only content is already at both section ends, so `bIsFullSel` is true (`select.cxx:150-167`).

### 3. Tables fail closed

| cell | read | engine parser |
|---|---|---|
| t1, SelectAll | the table as a body-level `<table>` | `unknownTag: table` |
| t2, SelectAll (the body starts with a table; ExtendedSelectAll by source) | the same | `unknownTag: table` |
| t1, CharLeftSel | goes back into the table and covers the whole cell (text `"\nCell text\n    • "`), the same `<table>` | `unknownTag: table` |

The existing parser refuses every one of these, so the toast would stay, as it does today.

### 4. SelectAll fails closed on any document above 10,000 characters

- **The observation.** In `sa-long-300` (300 lines, 16,800 characters plus line breaks, then the empty paragraph), the read after SelectAll is type **3** (`LOK_SELTYPE_COMPLEX`), with no text, 5/5.
- **The source.** `doc_getSelectionTypeAndText` returns COMPLEX when the selection's plain text exceeds 10,000 characters (`desktop/source/lib/init.cxx:6023-6024`).
- **Consequence.** SelectAll can only ever cover short documents.
- **CharLeftSel is not limited the same way.** Its selection is the paragraph break: 561-581 bytes of markup in every CharLeftSel cell without a table (765 with the table cell). **It was not run on the long document** (no cell was registered for it); that is predicted by construction, not measured.

### 5. The restore clears both fallbacks

P3 holds in every clean round of every cell. That is 135 of 135, including the cells that are not deciding: the read after the Q restore is NONE, and the locator finds the caret in the empty last paragraph.

### 6. Recorded: the undo stack on the blank document

The undo stack is synchronous and dispatch-scoped, as `../native/` found:
- each applied action adds one top action at return: `Number On/Off` (bullet and number alike), `Apply Styles: Heading 1`, `Delete numbering`, `Apply Styles: Body Text`;
- the sham and the already-bulleted no-op add nothing.

This is the observable that ruling 3 Q5.1 declined "alone". This run does not change its standing.

### 7. Recorded: costs (native wall time, not WASM)

| step | median |
|---|---|
| the fallback post | 0.0-0.3 ms |
| the html call | 0.8-1.0 ms |

Every fallback's `UNO_COMMAND_RESULT` says `success: true`, including the ones that selected nothing. So the command result cannot tell "nothing to select" apart.

## Reader and its red cases

`tool/read_q52.py --self-test out` (`out/self-test.json`): **`ALL_AS_EXPECTED`, 36 cases.**

- **How the cases are built.** Each verdict case starts from a forced holding baseline built in the reader, so it moves exactly one verdict:
  - V1 HOLDS is reachable (sa-a5 reads one `<ul>` block, sa-n5 one `<p>`);
  - from it, each of these breaks V1: a sham reading `<ul>`, an unclean round, a P0 failure, a restore failure, two blocks, a body-level table;
  - `ONE-BLOCK-UNSAFE` is checked in a non-deciding cell (sa-r1).
- **Scope.** IN-SCOPE and OUT-OF-SCOPE are both reachable for number and for heading.
- **V2 and V3:**
  - HOLDS is reachable, and stays HOLDS with a table cell refused in every round;
  - PARTIAL with one refused round, a restore failure, a locator with text, or a sham saved in a list;
  - UNSAFE with the n8 sham's last block in a `<ul>`;
  - NOT-ESTABLISHED with one unclean round.
- **The parser port**, tested directly:
  - first and last fields; nested lists (the innermost list wins);
  - footnote apparatus refused; a body-level close tag is malformed; a comment is skipped;
  - FIRST is fooled where LAST is not; a type other than TEXT is refused by every rule.
- **Non-vacuity**: 27 cells x 5 rounds were read.

**Fixed by execution (counted):** the self-test's scope cases first indexed the verdict object instead of its `actions` (a `KeyError` on the first scope case). Fixed before any self-test result was recorded.

## Not measured here

- **WASM and the product path.** That includes the a11y paragraph-identity check, declined on empty paragraphs (finding 074).
- **CharLeftSel on the long document.** Its constant size is predicted, not measured.
- **Images and frames, and findings 037 and 038.** A whole-document read reaches them; CharLeftSel's two-paragraph read reaches only the previous paragraph's end.
- **Other caret positions and selections:** the caret in a table cell, a frame or a footnote; a previous paragraph that ends in an as-char frame; hidden tracked changes.
- **The other four actions on multi-paragraph documents.** Only the bullet was run there; the five actions were run only on one-paragraph documents, where nothing can be read.

## Amendment 2: the four other paragraph actions on the multi-paragraph last line (CL + rule LAST)

`tool/run_cells_q52_actions.py`: 8 cells x 5 = 40 processes, 10:20-10:28Z, all exit 0. Fixtures in `fixtures-actions/`, output in `out-actions/`.

**Judged** by `tool/read_q52_actions.py out-actions` (`out-actions/reader-output.json`): **V4 = `LAST-UNSAFE`**, as registered (UNSAFE is judged first). In `cl-nbody-sham-heading-last`, rule LAST was satisfied for body in 5/5 while the saved last paragraph is `text:h`. Self-test: `out-actions/self-test.json`, `ALL_AS_EXPECTED`, 10 cases, including correction 1's case.

**The cause, measured.** The heading fixtures (176's markup, with no `office:styles`) load as a **pseudo-heading**: an automatic style `P1` with parent Standard and a direct outline level 1. LibreOffice's own save shows it that way.
- It is `text:h` to the ground truth.
- It is not a Heading 1 to the HTML export, which writes `<p>` both in the last block of `cl-nbody` and in the first block of `cl-nhead-after-heading` (the trap's `Heading before`).
- So both heading/body negatives tested a paragraph whose two notions of "heading" disagree, and the body "unsafe" is that disagreement.

**Recorded, not a verdict: the per-action rule applied to the other cells.**

| action | applied cell | negative cell | per-action rule |
|---|---|---|---|
| number | LAST `ol`, saved number | the trap after a number item: first block `ol` (FIRST fooled), LAST `none` | met |
| none | LAST `none`, saved out of a list | the no-op on a bullet: LAST `ul`, saved bullet | met |
| heading | Heading 1 applied, LAST `h1` | invalid fixture | -- |
| body | -- | invalid fixture | -- |

All of them: 5/5, P0 and P3 in every round.

## Amendment 3: real Heading 1 paragraphs

`tool/run_cells_q52_headings.py`: 6 cells x 5 = 30 processes, 10:45-10:52Z, all exit 0. Fixtures in `fixtures-headings/`, with `Heading_20_1` defined in `office:styles`. Output in `out-headings/`; the smoke is in `smoke-headings/`.

**Judged** by `tool/read_q52_headings.py out-headings out-actions` (`out-headings/reader-output.json`):
- **The fixture precondition holds**: the untouched real Heading 1 reads `<h1>` in every round, as the CL last block and as the SelectText first block.
- **V5: heading IN-SCOPE, body IN-SCOPE.**
  - heading: the A cell is amendment 2's `cl-head-empty-last`; the trap after a real `Heading before` reads LAST `p`, not satisfied, saved `text:p`.
  - body: the real empty last heading becomes `Text_20_body` and reads LAST `p`; the sham leaves `Heading_20_1` and reads LAST `h1`, not satisfied.
- Self-test: `out-headings/self-test.json`, `ALL_AS_EXPECTED`, 8 cases.

**Recorded: the v27 route** (rule FIRST on the SelectText readback, as v27 judges it). These cells' target is paragraph 1:

| cell | SelectText readback | FIRST | saved paragraph 1 |
|---|---|---|---|
| body on a real empty Heading 1, mid-document | 2 blocks, first `p` | satisfied | `Text_20_body` |
| the same, sham | first `h1` | not satisfied | `Heading_20_1` |
| a **pseudo-heading with text**, sham | 1 block `<p>Pseudo heading</p>` | **satisfied** | `text:h`, style `P1` |

5/5 each.

- **The first two close a premise gap in 176's Q6.3.** b1's "body on an empty heading" started from a pseudo-heading. On a real Heading 1 the v27 route verifies body, and refuses the sham.
- **The third is a limitation of the heading/body postcondition that predates v28.** The HTML heading is the style's, so a paragraph whose outline level comes only from direct formatting reads as body text whatever the dispatch did. It shows only when the dispatch leaves such a paragraph unchanged. In 176's b1 a real `Text body` dispatch did turn the pseudo-heading into `text:p`. It is not introduced by CL or the last-block field. Named here **L-pseudo-heading-reads-as-body**.

**Fixed by execution (counted):** `read_q52_headings.py` first read the LAST saved paragraph for the mid-document cells (`read_q52.extract`'s rule, right only for the 083 cells). It now reads paragraph 1. V5 did not depend on those fields.

## Scope on the multi-paragraph last line, all amendments together

- **bullet**: V3 (`LAST-HOLDS`).
- **number** and **none**: amendment 2, recorded per-action rule met.
- **heading** and **body**: V5 IN-SCOPE.
- **Tables before the last line**: refused (fail closed).
- **The blank document**: nothing to read (V1).

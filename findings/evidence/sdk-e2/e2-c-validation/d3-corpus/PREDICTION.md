# E2-C phase D3, the corpus half — registered before the harness existed

Written 2026-08-16.  The list half of D3 (cells L1–L8) is done and lives in
`../d3-lists/`.  This is the other half: **does an ordinary edit at a named
anchor leave the rest of these documents intact.**

The oracle is not invented here.  `e2/validation-matrix-v1.json` froze it on
2026-08-15, before any of D3 ran:

> open, edit at the named anchor, save; required anchors present, ZIP CRC and
> XML valid, forbidden content absent, desktop reopen and PDF export succeed

with two additions the matrix names per fixture: `d3-l1-review` adds "and
comments and tracked changes survive", and `d3-list-contexts` / `d3-list-split`
say "as d3-l0-t1, carrying cells L1–L6 and L8" / "carrying cell L7".

What this file adds is the part the matrix left open on purpose: **which
anchor, which action, and what counts as proof that the edit happened at all.**

## Two cells need no new browser round

`d3-list-contexts` and `d3-list-split` are worded as *carrying* the L cells.
The documents those cells saved already exist
(`../d3-lists/run-4-fixed-shell/`), and re-running them would produce a second
record of the same measurement rather than new evidence.  So the structural
criteria are applied **offline, to those saved documents**.  If they fail, the
list round's verdict is unaffected and this round's fixture cell is what fails —
the two answer different questions about the same bytes.

## The eight cells that do

One fresh document per cell; two cells in one document would make the second
one's pre-state whatever the first left behind.

| cell | fixture | anchor (searched for, not guessed) |
|---|---|---|
| `c-l0-t1` | `l0-t1-plain-zh.odt` | `Final line：ODT round-trip 完整性檢查。` |
| `c-l0-t2` | `l0-t2-styled.odt` | `文件結尾：請確認表格、圖片、註解與標題樣式均保留。` |
| `c-l0-t3-first` | `l0-t3-long.odt` | `第 1 頁：長文件記憶體與效能測試` |
| `c-l0-t3-middle` | `l0-t3-long.odt` | `第 11 頁：長文件記憶體與效能測試` |
| `c-l0-t3-last` | `l0-t3-long.odt` | `第 22 頁：長文件記憶體與效能測試` |
| `c-l1-review` | `l1-review.odt` | `Lorem ipsum` |
| `c-l4-stress` | `l4-stress-100.odt` | `R7 stress page 050 頁面錨點` |
| `c-l4-stress-last` | `l4-stress-100.odt` | `R7 stress page 100 頁面錨點` |

Deviations from a literal reading of SPEC E2-C section 5, both deliberate:

- The spec says `l0-t3` gets "first / middle / last".  The corpus manifest only
  names pages 1 and 22, so "middle" would have been an anchor nobody promised.
  Page 11 is used instead **after checking that the corpus really carries a
  per-page anchor for every page** — measured, not assumed.
- The spec says `l4-stress-100` gets a "fixed page text anchor", singular.  Two
  are used: page 050 because a 100-page document's interesting case is not its
  first page, and page 100 because the last page is where a truncating save
  would show.  Additional coverage, never less.

## The action: `set-list-unordered`, everywhere

One action across all eight cells, on purpose:

- **A difference is then attributable to the document**, not to the action.
  Seven fixtures times seven actions would measure something, but not this.
- **It mutates.**  A round where the document is not actually changed proves
  nothing about content preservation, which is the whole point of this half.
- **Its postcondition is a specific XML shape** — the anchor's paragraph ends up
  inside a `<text:list>` — so "the edit happened" is checkable in the saved
  bytes rather than inferred from a completion code.  Finding 048 is what
  inferring costs: eight cells reported success while acting on the wrong
  paragraph.
- **It is the same action the list half measured**, so the two halves are
  comparable.

## The caret is formed the product's way

Search locates the anchor and returns its rectangle; the caret is then placed by
the **product's click**, polled until the engine acknowledges it and the caret
is on the clicked line (`web/e2-c-caret.js`, the path finding 048's fix put in).
Search is a locator, not a gesture: SPEC E2-C 9.5.6 measured that a caret formed
by a zero-width `selectRange` and one formed by a click are different states as
far as the format barrier is concerned, and the matrix's second round requires
the product's gesture.

**A cell whose caret cannot be proved to be at the anchor does not dispatch.**
It records `CARET_NOT_AT_ANCHOR` and fails.  A cell that dispatches somewhere
else measures nothing and — worse — looks like a result.

## What is checked, offline, on the saved bytes

Judged by `tools/analyze_e2_c_d3_corpus.py`, which never opens a browser.

1. **The edit happened**: the anchor's paragraph is inside a `<text:list>` in
   the saved document and was not in one before.
2. **Required anchors**: every anchor the corpus manifest names for that
   fixture is still present, with the **same count**.  For `l0-t3` and
   `l4-stress-100` that means every per-page anchor, not just the named ones —
   a save that dropped pages 12–22 would keep both named anchors of `l0-t3`.
3. **ZIP CRC and XML**: every entry's CRC verifies and `content.xml`,
   `styles.xml`, `meta.xml` parse.
4. **Structure survives**, per fixture and counted before and after:
   tables, images (`draw:frame`), comments (`office:annotation`), tracked
   changes (`text:tracked-changes`), and headings.
5. **Forbidden content**: no string beginning `E2C-` appears in the saved
   document.  The harness never types, so any such string means a harness
   marker leaked into a corpus document.
6. **Desktop reopen and PDF export** via `soffice --convert-to pdf`, on the
   saved document.
7. **Both browsers produce the same verdict per cell**, and the `<office:body>`
   of the two saves is byte-identical.

## Predictions

Scored as written.  "Reasonable behaviour" is not a pass.

- **P-C1** — all eight cells dispatch, with the caret proved at the anchor.
- **P-C2** — every cell keeps every required anchor at the same count.
- **P-C3** — `l0-t2` keeps its table, image and comment counts; `l1-review`
  keeps its comment and tracked-change counts.
- **P-C4** — every saved document reopens in desktop LibreOffice and exports a
  non-empty PDF.
- **P-C5** — Chrome and Firefox agree cell by cell, and the `<office:body>`
  bytes match between them.
- **P-C6** — the two carried fixtures (`list-contexts`, `list-split`) pass the
  same structural criteria on the documents the L cells already saved.

## What voids the round

- The anchor search fails on a fixture: the cell is recorded as
  `ANCHOR_NOT_FOUND` and the round does not get to say anything about that
  document.  It is not scored as a pass.
- A cell times out: recorded, not retried.  SPEC E2-C section 3 forbids
  automatic retry, and a retried cell measures the retry.
- The saved document is byte-identical to the fixture on disk: that would mean
  no edit happened, and the L round already established that the comparison
  against a corpus-generator-written fixture is not the comparison to make (see
  `../d3-lists/README.md`, L6).  Here it is a **failure**, not a subtlety: this
  round's action is supposed to change the document.

# Product-path net for the 0.2.26 release — predictions (written 2026-10-17, before any product-path run on v21)

0.2.26 = engine **v21** (item 1 only: Ctrl/Cmd+Home/End, finding 142), shell **v74** (the page `605cf24b…`: findings 150 and 151's page fixes, item 2's entry hidden by the shell), host `3c01876` (finding 154's host rule), engine package `f5f0df762e1855f2`. Everything in `../../release-0.2.24/product-path/PREDICTION.md` is carried. That net ran in the 0.2.24 chain and its count held (`RESULT-0.2.24.md`).

The reader is `judge.py` here (0.2.24's copy: plain arm v20 → v21, the two page constants moved; see its docstring). The runner differs from 0.2.24's `9d1f44c6…` only in one mutation's `find` (`712f955a`); 42 checks stand. **This net has never run on v21**; a first-contact round may run before the count (`../../link-batch-v21/first-contact/`), and its reports are not this release's.

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v21 reports: entrypoint `605cf24b…`, no candidate keys; v8 reports: source before repointing `605cf24b…`, rest of shell equals source, entrypoint `ea3b6bad…`, profile e2-editor-v8, `pinBefore db3408f55316bf67` |
| P3 | 0 red cells under §23 + row 1′ |
| P4 | descriptive: the cells that differ between the arms are NE-only, as 0.2.23's and 0.2.24's were, or none |

## The changes since 0.2.24, and the cells that could see them

| Change | Where it lives | Cells that touch it | Prediction |
|---|---|---|---|
| **Item 1** (finding 142): Ctrl/Cmd+Home/End move to the document start/end through the engine (actions 22/23) | engine v21, page `605cf24b…` | None: no cell sends Ctrl+Home/End. Home/End are unmodified, and the Ctrl keys the runner sends are b/u/z/a | no cell moves |
| **Finding 150**: a move key pressed while a delete is in flight no longer takes the range path | page | Only a cell that presses a move key while a delete is unanswered. The runner waits for quiet between most steps | no cell turns red; a fast-sequence cell may move between PASS and NE inside row 1′'s window. Any move is listed under P4, not judged |
| **Finding 151** (part): actions 22/23 do not save a checkpoint | page (session) | none: no cell sends 22/23 | no cell moves |
| **Item 2 withheld**: `paste-markdown` is in the toolbar but `hidden`, and its click returns at once | page, shell | none: no cell presses it or pastes Markdown | no cell moves |
| **ABI 5** / v21 manifest (new leaves for 22/23 and `pasteMarkdown`) | engine | the v8 arm runs the v21 page on the v8 engine, which declares none of them. The page offers the keys only when the manifest declares them (D5/E0) | the v8 arm behaves as on 0.2.24 for every cell |
| **Finding 154's host rule** | host template | none: this net runs without the host | no cell moves |

**Watch item (carried)**: Chrome `clear-format-removes-every-inline-format` NE in ≥ 2 of the 6 Chrome runs (either arm) means the product-path verdict is not read until that is diagnosed.

Before the verdict is read, the reader is made red once on scratch copies, as in 0.2.12 (`../../release-0.2.12/product-path/judge-red-offline.txt`):
- a flipped v21 cell where v8 passes → P3 MISS;
- a wrong v21 entrypoint → P2 MISS.

The verdict is the `SUMMARY` line (§34.7).

# Selection collector preparation 05 (uncounted): covering sweep, click+End anchor

Uncounted Chrome preparation with `--keep-going` over 13 cells: `shift-Up@doc-end` (lost to the export overflow in 04) and the twelve covering cells preparation 03 never reached. The paint-digest observer (`4efcf8d9`) was in effect: cells are 2.5–3.1 MB instead of 300–370 MB, and every export completed. Receipt `runner.command.json` (exit 1, 360 s); foreign CPU guard passed; `postConfig` equals `config`.

| Cell | Runner's reader | Current reader |
| --- | --- | --- |
| `shift-Left@cjk-mid`, `shift-End@doc-end`, `shift-Home@doc-start`, `shift-Right@empty-para`, `shift-Down@heading-mid`, `shift-Home@list-mid` | PASS | PASS |
| drags `shift-Right@range-bwd`, `shift-End@range-fwd`, `shift-Up@range-one`, `plain-Left@range-cross` | PASS | PASS |
| keyboard range `plain-Down@range-kbd` | PASS | PASS |
| `shift-Up@doc-end` | S1 FAIL `moving endpoint differs from independent control`; S2 PASS | same |
| `shift-End@wrap-line-end` | S1 FAIL `collapsed selection with distinct logical endpoints`; S2, S3 PASS | **PASS**, logical anchor (4, 101) |

`shift-Up@doc-end` is the fifth table-selection member predicted in preparation 03. Writer jumps the whole table upward, and the product's selected text equals the native reference text. Its S1 disposition is the pending owner-requested fable ruling.

## The wrap-line-end FAIL was the reader's

The click+End shape clicks the first displayed line's start (`w.l1start`, x 1418) and presses End, leaving a collapsed caret at the line end (`w.l1end`, x 10948). Native Writer's Shift+End there selects nothing (all three rounds empty, cursor unchanged), and so does the product: reference and candidate both stay at (10948, 2522), collapsed.

The reader took the Shift anchor from the source row's `anchorPointName`, which for this shape is the click point (`w.l1start`), not where the caret sat before the key. For a collapsed shape the Shift anchor is the caret itself, the moving point. This shape is the only one whose click point differs from its moving point, so all six wrap-line-end S1 members were affected.

Disposition: the reader uses the anchor point for range shapes and the moving point for collapsed shapes, including the reported logical anchor. A control built from this real page makes the candidate's selection anchored at the click point instead (consistently in page record, call result and wire reply). The current reader reads FAIL. The pre-fix reader reads that wrong product as PASS and the real page as FAIL.

The reader now also accepts a paint record carrying the full bytes, which is a superset of the digest. Preparations 02–04 therefore still re-read; `selection-prep-02` reads PASS under the current reader.

# Selection collector preparation 03 (uncounted): table-selection premise

Uncounted Chrome preparation over a 14-case covering list (one per source shape, all six keys, Table2 plain moves, all four setup methods). Receipt `runner.command.json` (exit 1, 104 s). The runner stops at its first nonpassing cell, so only two cells ran:

| Cell | Reader verdict |
| --- | --- |
| `shift-Down@caret-mid` | PASS (S1, S2) |
| `shift-Up@cell-end` | **FAIL** S1 `moving endpoint differs from independent control`; S2 PASS |

Raw cells: `chrome-shift-Down@caret-mid.json.gz` (`3bf884bc…9b11`) and `chrome-shift-Up@cell-end.json.gz` (`86e048b0…ed91`), each equal before compression and after decompression.

## What the FAIL is

Moving point `p8.end`: end of `A1 cell text`, the first cell of the fixture's 2×2 table, which sits directly below `List item one`.

- Reference arm (plain Up, the S1 independent control): the caret leaves the table to y 4344, x 2511. The independent mapping places it in paragraph 7 (`List item one`) at offset 4.
- Candidate arm (Shift+Up): selection `A1 cell text`, caret at the cell start (x 1418, y 4620), anchor at the cell end (x 2537). The reply, the delayed engine read and the active selection agree; S2 is clean.
- Native Writer (`extend-signatures/run-20261013T095104Z`, all three rounds): selection `A1 cell text`, cursor `1418, 4618`, selection end `2537, 4618`.

The product therefore matches native Writer. What fails is the S1 premise that a Shift extension's moving endpoint equals the same-browser unshifted move. In a table, Writer's Shift extension uses cell/table selection semantics, which differ from plain caret movement.

## Census of the premise over all 84 Shift members (prediction, from native data only)

Eight members involve the table, judged by the moving point being in a cell paragraph or the native selection containing cell text. Native outcomes, identical in all three rounds:

| Member | Native outcome | Plain move (expected) | Premise |
| --- | --- | --- | --- |
| `shift-Up@cell-end` | `A1 cell text`, cursor at A1 start | leaves the table upward | **measured false** |
| `shift-Down@cell-end` | A1+A2 cells, cursor A2 start | A2 at the same column | predicted false |
| `shift-Right@cell-end` | A1+B1 row, cursor B1 end | B1 start | predicted false |
| `shift-Down@list-mid` | jumps the whole table to `Final paragr…` | enters A1 | predicted false |
| `shift-Up@doc-end` | jumps the whole table to the list paragraph | enters B2 | predicted false |
| `shift-Home@cell-end`, `shift-End@cell-end`, `shift-Left@cell-end` | within A1 | within A1 | predicted to hold |

The rows marked predicted are being measured in preparation 04. No criterion has been changed. The disposition of S1 for these members is an open decision, recorded in the session handoff.

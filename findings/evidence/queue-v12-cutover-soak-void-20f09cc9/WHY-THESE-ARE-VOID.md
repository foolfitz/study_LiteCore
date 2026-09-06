# Ten soak runs, three diagnostic runs and one verdict, on a page that no longer exists

Runs and diagnostics of the `e2-editor-v12` cutover soak, taken 2026-09-05 to
2026-09-06, against candidate page sha
`20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95`.

They are **void for the count and retained untouched**, the same disposition
the seven runs in `../queue-v12-cutover-soak-void-3dfdcfef/` received on
2026-09-05, and the five unsplit-v11 runs received in
`../queue-v11-cutover-soak-not-started/` before that.

## What voided them

`handoff/HANDOFF-2026-09-06-the-page-moved-twice-and-the-4b-instrument-broke.md`
records that the shipping shell was changed twice on 2026-09-06. The fix for
finding 088 (the doubled-paragraph residue: every non-heading paragraph spoken
twice, ~117 ms apart) landed in `wasm_sdk_probe/web/e2-editor-app.js`, one of
the shell bundle's thirteen `included` paths, moving the candidate page's sha
from `20f09cc9…` to
**`39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e`**. The
frozen shell generation moved from v44 to **v45** (`bundleSha256
a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578`) in the same
change, per ruling E-1 of that handoff ("a changed shell needs a new
generation, landed in the same commit as the change").

`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, ruling 1 (2026-08-28),
states the rule this pays for: **"the count restarts on the day the page
changes."** The banked runs below are valid for page `20f09cc9…` and for no
other.

## What moved, and each file's page identity

| file | `candidateCutover.pageSha256` |
|---|---|
| `soak-run-01-candidate.json` … `soak-run-10-candidate.json` (10 files) | `20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95` |
| `diagnostic-01-caret12.json` | `20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95` |
| `diagnostic-02-caret12.json` | `20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95` |
| `diagnostic-03-caret12.json` | `20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95` |
| `VERDICT-condition-2-on-20f09cc9.json` (was `VERDICT-condition-2.json`) | `expected.pageSha256` and every entry under `runs[]` and `terms["1-identity"].detail[]`: `20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95` |

The verdict file was renamed on the move, the same way its 2026-09-05
predecessor (`VERDICT-condition-2-on-3dfdcfef.json`) was: `check_soak_bank.py`
and `check_caret_diagnostics.py` glob `VERDICT-*.json` and `diagnostic-*.json`
respectively out of the live bank directory, so a `VERDICT-condition-2.json`
left in this void directory with its original name would not collide with
anything today, but a bare `VERDICT-condition-2.json` sitting among files named
`*-on-<sha>.json` would be the one file here that does not say which page it
judged.

`check_caret_diagnostics.py` term 1 requires `candidate.pageSha256 ==
expect_sha` of every complete run given to it; all three diagnostic reports
here carry `20f09cc9…`, which is no longer `check_caret_diagnostics.py`'s
`DEFAULT_SHA` as of this commit. What they still assert is unchanged and worth
keeping: 36 committed rounds across the three runs, 0 dropped, and the guard
refusing a stale write 0, 9 and 4 times (max 9) — the finding-084-class
measurement on page `20f09cc9…`.

## Files that stayed, and why

* `interrupted-2026-08-29-0050-partial.json` — carries `candidateCutover.pageSha256
  == 3dfdcfef4abfe6b723b573f35e8ec8f885dcc42a8ed4d8338ad2381eb386f50f`, a
  different and older page than the one this directory voids. It is unrelated
  to today's move and stays in `../queue-v12-cutover-soak/`.
* `RUNS.md` — the bank's running ledger; append-only, stays in
  `../queue-v12-cutover-soak/` with a new dated entry recording this void.
* `RESULT-condition-2.md` — already carries one precedent of this exact
  situation (the `3dfdcfef…` void of 2026-09-05, recorded in place as an
  appended section rather than by moving the file); it stays in
  `../queue-v12-cutover-soak/` with a further appended section recording this
  second void, naming where the three diagnostic reports and the verdict it
  described have gone.

## Why they are kept

Evidence in this tree is not destroyed. These ten runs and three diagnostics
are the only record that the product path ran clean ten-of-twelve times in a
row, and that the caret-diagnostic condition passed all four terms, on *some*
page — which is what makes "the net is capable of a clean run" a measurement
rather than a hope. Nothing about them was wrong; they measured bytes that will
not ship.

Disposition and the handoff that records it:
`handoff/HANDOFF-2026-09-06-the-page-moved-twice-and-the-4b-instrument-broke.md`
and `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, task T0.

# Witness (§34.4): the diag tool refused the V6e record run on a stale page pin

Committed **before** the tool is changed.

- **Run:** `diag_v21_dirty_move.py --browser chrome --variants v6e --rounds 3 --fix none --out …/evidence/v6e --wait-lock 600`, 2026-10-17 06:38, under the S-9 lock. No browser was started: the check runs right after the mirror is built.
- **What the tool printed:** `the v21 page (before any fix) is 605cf24b3dff5a2d, not 3d5112161b23b060, or the patch is not alone` (exit 1; `run-chrome-pin-refusal.log`).
- **What it read** (`report-chrome-20261017T063848.json`, `v21PageCheck`): served `605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f`, `identityOk: true`, `expectedPrefix: 3d5112161b23b060`, `matches: false`.

## Why this is a tool fault, not a page fault

- The tool builds its v21 page with the item-1 runner's `Pages.base("v21")`, which calls `v21_shakedown_common.build_mirror` with no `source_page`. That repoints the **tree's** `web/e2-editor-app.js` (`wasm_sdk_probe/tools/v21_shakedown_common.py`, `build_mirror`; `run_v21_shakedown_item1.py`, `Pages.base`).
- The tree moved at `712f955a` (fixes 1 and 2, item 2's entry off). The served page is now `605cf24b…` (results README §3), and `v21_shakedown_common.EXPECTED` was re-pinned at `f5f60ac1`. The report's own `identityOk: true` is that check.
- `V21_PAGE_PREFIX = "3d5112161b23b060"` (`diag_v21_dirty_move.py:134`) is the pre-fix pin from `ARMS.md` §1. It was not moved with the others.

## The fix (next commit)

Only the pin: `V21_PAGE_PREFIX` becomes `605cf24b3dff5a2d`, the page that `v21_shakedown_common.EXPECTED` and `--expect-page` name. The check itself is unchanged, and it still refuses any other page. Tally: modified because of execution +1.

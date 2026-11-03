# Handoff: hosts 0.2.53 and 0.2.54 installed and measured; Calc undo measured natively

Checkpoint **2026-11-03 14:30**. Supersedes `HANDOFF-2026-11-03d-gen88-holds-hosts-0253-0254-ready.md` for what is next; its cautions still stand. K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). **Installed on the own stack: 0.2.54** (host `8c95b50`, engine `89860962782b3a21`, Writer `e2-editor-v32`, generation 88). The owner has hand-tested neither 0.2.52, 0.2.53 nor 0.2.54.
- Host repo (`/home/jiajun/Projects/Nextcloud_Apps/litecore`): `main` = `8c95b50` (fast-forwarded through `6b1660c` 0.2.53). **Nothing pushed**; the owner pushes.
- The own stack is up; nothing of ours is running.

## Done this session

- **Host 0.2.53** (batch 5, page only), `findings/evidence/host-0.2.53/README.md`: red first on 0.2.52 on the three cells it should be; gate, package (`89860962`), `DELTA_HOLDS`, `PACKAGE_HOLDS`, installed; `H5_HOLDS` 10/10, T6, Files 52/52, host batch, layout, capture-after.
- **Host 0.2.54** (batch 6, host source only, the same engine bytes), `findings/evidence/host-0.2.54/README.md`: release tools derived by `derive_host_0254.py`; the gate adds G1 to G3 and re-runs G1 and G3 on the candidate before packaging; red first on 0.2.53 on `new-menu/*` and `create-ods/*` only; installed; `H6_HOLDS` 12/12 on both browsers, and the four regressions hold.
- **Calc undo, native measurement NU** (`specs/SPEC-P-calc-undo.md` sections 2 and 3, `findings/evidence/calc-undo/native-01.md`): every page write takes one engine undo except single-cell bold and italic, **three each** (the bridge's op 2 and 3 call `setPropertyValue` once per script), and Ctrl+B over a pending draft, four. Predictions committed before the run; both controls and both observers hold.

## Next, in order

1. **The owner's hand test on 0.2.54**: the batch 4 list in `handoff/RUNBOOK-relink-v32.md`, plus: select a word and press Enter (paragraph break, two undos to go back); Ctrl+C on a caret (a sentence); `+ 新增` shows 新文字文件 and 新試算表 with LibreOffice's icons; a new spreadsheet opens in Calc; upload an .ods through Files and click it.
2. **Calc undo, the link design** (append to `SPEC-P-calc-undo.md`, criteria before code), for the next link batch: op 2 and 3 in `src/calc_cell_bridge.cpp` written as one `setPropertyValues` (as op 7 to 9 are), the undo capability in the Calc build, a new Calc profile (`ods-editor-v4`), the page's buttons and Ctrl+Z/Y. Open questions for the design: redo; what the page shows while the engine undoes a write the page has not re-read (row heights after a format undo, the formula bar); whether a pending draft is committed or dropped by Ctrl+Z. The link is the owner's. Bundle it with other engine work (owner's 08-17 rule).
3. Not started: C, the ordered-commands product arms. The owner's demo list (11-02): zoom, Calc sheet-tab scrolling, opening Microsoft documents.

## Cautions

- `host_batch6.py`'s two fixes (its docstring, and `host-0.2.54/README.md`): a cell that wants a route must take the href string `wait_until` returns, not its truthiness; the editor route redirects to `/r/<buildId>-<hash>/<page>`. Other host tools that test `bool(landed)` on an `/apps/litecore/r/<page>` suffix would be vacuous the same way; `host_layout.go` waits on the page name and does not read the result.
- `host_batch5.py` clears the toast with its own `CLEAR`; `run_e2_c_product_path.CLEAR_TOAST` leaves `.bad`, so a `RED` read after it sees `''` from an earlier refusal.
- `probe_calc_undo_native.py` must run without `-I` (it imports its neighbours). It copies the fixture per arm (an aborted LOK run leaves `.~lock`).
- Two Bash calls in one message may not keep each other's `cd`: a run landed in `tool-fixes/` once and never started. Use absolute paths for evidence runs.
- `rollback-package.sh` for 0.2.54 restores the same bytes; batch 6 is host source.

## Section 34.4

Since the previous handoff.

- **Fixed-by-execution: 2.** `host_batch5.py`'s toast clear; `host_batch6.py`'s vacuous `landed`.
- **Fixed-by-review: 1.** `host_batch6.py` recorded nothing for `create-ods` when the New spreadsheet entry was missing (read before its first run).
- **Fable rulings: 0.** Codex: not used.
- Wrong statements, corrected: 0 on record.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` and the link stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never. Codex through `codex exec` only.

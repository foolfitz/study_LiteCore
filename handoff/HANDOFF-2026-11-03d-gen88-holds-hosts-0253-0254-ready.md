# Handoff: generation 88 holds; hosts 0.2.53 and 0.2.54 are ready to package, nothing installed past 0.2.52

Checkpoint **2026-11-03 12:45**. Supersedes `HANDOFF-2026-11-03c-demo-batch-4-done-0252-installed.md` for what is next; its sections on batch 4, finding 183 and the cautions still stand. K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). **Installed on the own stack: 0.2.52** (host `c657aba`, engine `21985315`, Writer `e2-editor-v32`, generation 87). The owner's hand test on 0.2.52 has not happened yet (the owner could not test today).
- **The tree is at generation 88** (`97c3da29` was 87; 88 froze `web/e2-editor-app.js` with batch 5). `dist/` serves generation 88's page. The host still runs 87's page.
- **Nothing of ours is running. Nothing is pushed.** Host repo (`/home/jiajun/Projects/Nextcloud_Apps/litecore`): `main` = `c657aba` (0.2.52, live), local branches `host-0.2.53` (`6b1660c`, version bump only) and `host-0.2.54` (`8c95b50`, batch 6), worktrees under `wasm_sdk_probe/build/host-0.2.5{3,4}/litecore`. The owner pushes.

## Done this session (after the reboot)

- **The own stack survives a reboot now.** A stale `/var/tmp/logpipe` left supervisord waiting forever (502). `host-stack/web-config/web-entrypoint.d/clear-stale-logpipe.sh`; `specs/SPEC-M3-own-stack.md` last section. The stack still does not start by itself (`restart: "no"`): `docker compose --env-file litecore.env up -d` in `wasm_sdk_probe/host-stack`.
- **Finding 151 closed** on 0.2.52, with a 0.2.24 red control (`findings/evidence/151-on-0252/`).
- **Census**: 16 of 21 findings with open-looking headers are fixed (`research/RESEARCH-2026-11-03-open-findings-census-0.2.52.md`). Still open, none on the typing path: 169, 147, 163, 148.
- **Calc has no document undo** (`findings/evidence/calc-undo/README.md`). The owner put it on the to-do list; it needs a link.
- **Demo batch 5** (`specs/SPEC-P-demo-batch-5.md`, `findings/evidence/demo-batch-5/README.md`): Enter over a selection = Delete then Enter, measured on seven shapes; the empty-copy sentence. Generation 88 holds everywhere.
- **Demo batch 6** (`specs/SPEC-P-demo-batch-6.md`), host only: New spreadsheet in Files' New menu (30 blank spreadsheets from `tools/make_new_spreadsheet_templates.py`, G1 to G3 hold with red cases, `findings/evidence/host-0.2.54/static/`), LibreOffice's MPL-2.0 icons for New document and New spreadsheet (the owner chose them, `research/RESEARCH-2026-11-03-odt-ods-icons.md`), upload-and-open of .ods the way Collabora does it (Files' own upload, then the file action; measured, not changed).

## Next, in order

1. **Host 0.2.53** (batch 5, page only). Tools derived in `findings/evidence/host-0.2.53/` (`derive_host_0253.py` already run). With `host-stack/bin` first on PATH, from that directory:
   - `python3 -I host_batch5.py --out h5-red-on-0252` on the installed 0.2.52: must read `H5_RED` (Enter refused, raw copy code).
   - `python3 -I prepare-release.py --gate-only`, then `prepare-release.py`, `check-delta.py`, `offline-package-check.py <build/host-0.2.53/litecore>`, `install-0.2.53.py --offline-only`, `--preflight-only`, then the install, then `bash h5.sh`. Template: `host-0.2.52/README.md`. `check-delta.py` expects exactly `e2-editor-app.js` changed and no profile move.
2. **Host 0.2.54** (batch 6, host source only, the engine package identical to 0.2.53's). Its release tools are not derived yet: derive from 0.2.53's once 0.2.53 has a buildId. Differences to carry: the parent is `6b1660c`; the host source delta is the declared list (info.xml, `blank-ods/`, `img/`, `LICENSES/MPL-2.0.txt`, `l10n/zh_TW.*`, the three PHP files), not only info.xml; the dist delta is empty, so `check-delta.py`'s `fewer` red case has no file to act on and goes; the gate adds G1 to G3 from `host-0.2.54/static/`. Then `host_batch6.py --out h6-red-on-0253` on 0.2.53 (must be red on `H6/new-menu/*` and `H6/create-ods/*`), install, `host_batch6.py`, Files workflow, `host_batch.py`, `host_layout.py`, `host_calc_theme.py`, capture-after.
3. **The owner's hand test** on 0.2.54: the batch 4 list in `handoff/RUNBOOK-relink-v32.md`, plus: select a word and press Enter (it becomes a paragraph break, two undos to go back); Ctrl+C on a caret (a sentence); `+ 新增` shows 新文字文件 and 新試算表 with LibreOffice's icons; a new spreadsheet opens in Calc; upload an .ods and click it.
4. To do, not started: **Calc undo** (next link batch: the capability bit in the Calc build, a new Calc profile, the page's buttons and Ctrl+Z/Y; measure natively first which Calc writes take more than one undo). C, the ordered-commands product arms.

## Cautions

- `host_batch6.py` has never run. Its first red is the tool's until shown otherwise; it reads the expected blank spreadsheet with `php -r` on the live host's `BlankDocument::chooseSpreadsheet`, which does not exist on 0.2.53 (the red run records an error there, by design).
- `host_batch6.py` and `host_batch5.py` import `host-0.2.52/host_batch4.py` for their helpers; do not edit that file.
- The tools that use a mirror refuse to run together (`browser_lock`); the host tools do not take that lock, so do not run them during a chain with timing arms (F4).
- `wait()`/`save()` in the mirror tools return on a timeout without raising; an unsaved page holds the next navigation (`beforeunload`, 180 s in CDP). Save before moving on.

## Section 34.4

Since the previous handoff.

- **Fixed-by-execution: 8.** P5's E3 save and E5 walk, P5's rsid reading (its red case caught a dropped newline), the Calc undo probe twice (a reader import, then keys that never reached a cell), `host_batch6.py`'s stray import, `diag_v32.py` as a thin wrapper rather than an edit of the bound tool, the read-cost save.
- **Fixed-by-review: 0.** No review round: batch 5 and 6 went straight from spec to measurement.
- **Fable rulings: 0.**
- Wrong statements, corrected: 0 on record.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` and the link stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never. Codex through `codex exec` only.

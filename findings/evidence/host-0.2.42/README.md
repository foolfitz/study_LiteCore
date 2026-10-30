# Host 0.2.42 preparation: Writer on profile e2-editor-v26 with shell generation 80 (Ctrl+A select-all, findings 174 and 175)

## Declared before packaging, 2026-10-30

Spec `specs/SPEC-M3-select-all-v26.md` 5.9 and append 1 (finding 175). No relink: wasm, loader and exports are the v25 archive's bytes (page pin `44cb15ea8d36f0e0` unchanged); `e2-editor-v26` is a manifest successor of v25 with a one-hunk worker change (spec 4.1, 4.2).

**Live predecessor** (verified read-only by the main session, 2026-10-30): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **2bb5718** (0.2.41), clean; its engine is archived as `wasm_sdk_probe/build/archive/host-0.2.41-engine-829a988e199ebc43` (bound by `host-0.2.41/archive.sha256`). `prepare-release.py` re-checks the live engine against that archive; `install-0.2.42.py` re-checks it file by file before anything changes.

**Candidate scope**: isolated worktree `wasm_sdk_probe/build/host-0.2.42/litecore`, branch **host-0.2.42**, whose only source change against 2bb5718 is `appinfo/info.xml` 0.2.41 -> 0.2.42 (the commit is recorded in `release.json` by `prepare-release.py`). Package the current three-page closure from `dist/` with the canonical packager. The editor page is generation 80's (identity `wasm_sdk_probe/tools/v80_four_arms_identity.py`, profile `e2-editor-v26`); viewer v3, Calc v2 and the 0.2.38 dark-theme HTML retained.

**Expected delta against 0.2.41** (`prepare-release.py` refuses anything else; `check-delta.py` re-derives it from the two archived MANIFEST files):

- changed, exactly three: `e2-editor-app.js`, `editor-shell-v2/narrow-editor-v2-client.js`, `editor-shell-v2/narrow-editor-v2-session.js`;
- added, exactly four: `profiles/e2-editor-v26/{probe.js,probe.wasm,sdk-manifest.json,sdk-worker.js}`;
- removed, exactly four: `profiles/e2-editor-v25/{the same four}`; checked first that `e2-editor.html` is the only page of the 0.2.41 package on `e2-editor-v25`;
- the added `probe.wasm` and `probe.js` equal the removed ones (sha256 and byte count); the added `sdk-manifest.json` and `sdk-worker.js` differ from them.

`check-delta.py` red cases: one more changed record, one fewer, an added record, a removed record, the v26 `probe.wasm` differing from the removed v25 one; plus one per clause added for 0.2.42 (v26 `probe.js` differing, v26 worker equal to v25's, another 0.2.41 page on v25, the new editor page still on v25). Each must be red.

**Evidence gate** (`prepare-release.py` refuses otherwise): 0.2.41's gate unchanged (carried-over v24 counts; v25 F1, F2, F3 `read-02`, F4, section 9 reader; spec v79's U1, U2, shell tests, B1, F3-79 both readings, F4-79, V0', E1-C) plus spec v26's, all under `findings/evidence/select-all-v26/`:

| criterion | file(s) | holds when |
|---|---|---|
| P1 | `p1/dist-profile.json`, `p1/red/red-cases.json` | `P1_HOLDS`, `RED_CASES_HOLD` |
| U1, U2, U3, U4 | `uN/red-before.txt`, `uN/green-after.txt` | last `ℹ fail K` line: K > 0 before; K = 0 after, with last `ℹ pass N` N > 0 |
| whole shell suite | `suite-after-175.txt` | last `ℹ fail` 0, last `ℹ pass` > 0 |
| S2 | `s2/run-02/report.json` | `S2_HOLDS` (run-01 does not count: the page changed after it, append 1) |
| S1 | `s1/run-01/report.json`, `s1/self-test.json` | `S1_HOLDS`, `selfTest` `ALL_RED` |
| F3-80 | `f3/read-01.json`, `f3/equal-01.json` | `F3_HOLDS`, `F3_80_EQUAL` |
| F4-80 | `f4/aggregate-judge.json` | no problems, 24 rows, every arm PASS |
| V0' | `v0/v0-prime.json` | `V0_PRIME_HOLDS` |
| E1-C | `v0/e1-c-after-put-back.json` | `intact: true` |

When these scripts were written (2026-10-30 ~02:15 +0800), F3-80, F4-80, V0' and E1-C did not exist yet and S1 / S2 `run-02` were being produced; the script names every missing file and refuses, and refuses any file that is present with the wrong result. That refusal is the gate, not a defect.

**Scripts** (each derived from its 0.2.41 counterpart, which is not edited; the closed list of differences is in each docstring or header): `prepare-release.py`, `check-delta.py`, `offline-package-check.py` (docstring only), `install-0.2.42.py` (docstring and candidate path only; `--offline-only` and `--preflight-only` kept), `rollback-package.sh` (exact 0.2.41 engine, label stays 0.2.42), `capture-after.py` (docstring only; 0.2.41's named limit -- it gates on the Files runner's summary `ok`, not on the cells -- is inherited, spec 5.9). Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

**DDEV**: not touched by any step before the install (`prepare-release.py`, `check-delta.py`, `offline-package-check.py` and `install-0.2.42.py --offline-only` read only git, files and the archives). The install needs a NEW owner slot with an explicit no-site answer, recorded as `slot.json` in this directory (same fields as `host-0.2.41/slot.json`: `start`, `end`, `ownerNoSite`, `sharedDdevCoordinated`, `purpose`, `ownerAnswer`); fgp-nc and nc-bridge stay stopped by the owner's choice. No slot, no install: 0.2.41 stays the daily uncounted candidate.

After install: the Files workflow, `capture-after.py <install-dir> <workflow-dir>` (both positional arguments), then the owner's hand test (spec 5.9): (a) a new document, bullet -> the toast is not the red error box and has no English; (b) an existing document, **click into the document first**, Ctrl+A -> the highlight covers the whole document -> type to replace -> Ctrl+Z twice returns the original text; (c) a new document, click, Ctrl+A -> 「全選沒有選到任何內容」.

Not in this package: K. Nominal shipped host stays 0.2.26.

## Correction to the gate table above (2026-10-30 ~07:30 +0800, spec v26 append 2)

The F3-80 row above ("`F3_HOLDS`, `F3_80_EQUAL`") is superseded. F3-80 moved three Chrome cells because the bound product-path runner reads the copy toast's `U+` list, which finding 175 removed (`../select-all-v26/f3/MOVED-CELLS.md`); fable ruled B modified on the owner's authority (`../select-all-v26/f3/RULING-fable-2026-10-30.md`). `prepare-release.py` was edited before its first run (commit `92d54b1a6`, docstring names the change) to require: `f3/read-01.json` = `F3_RED` with exactly the three problems; `f3/equal-01.json` = `F3_80_MOVED` with exactly the three moves (chrome 46/43, firefox 46/46); `f3/append2-read-01.json` = `F3_80_HOLDS_UNDER_APPEND_2`; `f3/append2-self-test.json` = `ALL_RED`.

## Offline results (2026-10-30 ~07:33-07:37 +0800)

- Host worktree `wasm_sdk_probe/build/host-0.2.42/litecore`, branch `host-0.2.42`, commit **93b1ebc** (from 2bb5718; `appinfo/info.xml` 0.2.41 -> 0.2.42 only).
- `prepare-release.py` (`package-run-01.*`, exit 0, ~160 s): engine **01e6c3fb62626d16**. Against 0.2.41: 39 records unchanged; changed exactly `e2-editor-app.js`, `editor-shell-v2/narrow-editor-v2-client.js`, `editor-shell-v2/narrow-editor-v2-session.js`; added the four `profiles/e2-editor-v26/` files; removed the four `profiles/e2-editor-v25/` files. Every v25, v79 and v26 gate holds (`release.json` `v26Gates`; `f3_80Verdicts` = `F3_RED` / `F3_80_MOVED` / `F3_80_HOLDS_UNDER_APPEND_2`). Archive `wasm_sdk_probe/build/archive/host-0.2.42-engine-01e6c3fb62626d16` (not in git), 94 members bound by `archive.sha256`.
- `check-delta.py` -> `check-delta.json`: **DELTA_HOLDS**, no problems; all nine red cases red.
- `offline-package-check.py wasm_sdk_probe/build/host-0.2.42/litecore` -> `offline-package-check.json`: **PACKAGE_HOLDS**, zero problems, **22/22** red cases red.
- `install-0.2.42.py --offline-only` -> `offline-install-preflight.json`: **OFFLINE_INSTALL_READY** (parent 2bb5718, candidate 93b1ebc, `liveMutation: false`).

Next: an owner slot with an explicit no-site answer (`slot.json`); then `install-0.2.42.py --preflight-only`, `install-0.2.42.py`, the Files workflow, `capture-after.py <install-dir> <workflow-dir>`, and the owner's hand tests (a)-(c) plus (d) Ctrl+A then Ctrl+C shows 「已複製 N 字」.

## Live installation (owner slot, `slot.json`; first slot `slot-01-expired.json`)

The owner answered the slot question "A" (install now, no site during the install). Only litecore and the router ran throughout (`ddev-before-01.json`, `ddev-before.json`, `ddev-after-slot.json`); fgp-nc and nc-bridge stay stopped by the owner's earlier choice.

- **First slot (07:55-08:45), install not started.** `install-0.2.42.py --preflight-only` -> LIVE_PREFLIGHT_READY (`install-20261030T075540+0800/`, `live-preflight-01.*`), but its snapshot held one `oc_files_lock` row (admin, file 25696, `LiteCore Calc 手動驗收 2026-10-25 203756/新文字文件.odt`, created 01:11) where 0.2.41's preflight had none. Re-read at 08:01: the row's `ttl` had grown 24526 -> 24887, and the container's Apache log showed a `LOCK` refresh of that file every 60 s from the owner's desktop Firefox: an editor tab from the owner's 0.2.41 hand test was still open. The installer requires the lock rows equal before and after, so a refresh during the install would fail it after the mutation, and an open tab breaks the no-site agreement. The main session did not touch the row; it asked the owner to close the tab.
- **Session slip, recorded.** The main session could not close one tab of a Wayland Firefox from a shell. To confirm which content process held the tab, it sent `kill -STOP` to Firefox content process 2138220 (the one with 8 DOM workers and ~980 MB, started 23:32), intending `kill -CONT` 95 s later; the owner rejected that tool call mid-run, so the STOP took effect and the CONT did not (the last refresh was 09:42:07). The owner then closed the tab by hand. At 09:52 the process was still stopped (`T`); the main session sent `kill -CONT`, the process exited at once, and the tab's unload sent its `UNLOCK` (three, 09:53:07). `oc_files_lock` was empty afterwards and no request came from the browser after 09:53:07.
- **Second slot (09:53:31-10:38:31, `slot.json`; owner: "我回來了，我手動關掉了").** `install-0.2.42.py --preflight-only` -> **LIVE_PREFLIGHT_READY** (`install-20261030T095452+0800/`): protected documents 24674/24920/25391 read 200; `oc_files_lock` **zero rows**.
- `install-0.2.42.py` -> **CANDIDATE_INSTALLED** (`install-20261030T095504+0800/`, `install.*`): fast-forward 2bb5718..93b1ebc (info.xml only), exact engine rsync, `occ upgrade` to 0.2.42; protected documents and full lock rows equal before/after; e2-editor/ods-viewer/ods-editor unauthenticated routes all **401**.
- **Files workflow** `files-workflow-01/` (unchanged `run_calc_editor_host.py`, Chrome + Firefox): **52/52 PASS**, `ok: true`; cleanup: no owned unlocks, no cleanup errors; every entry landed on `/r/01e6c3fb62626d16…`. Same stated limit as 0.2.41's run: the Writer arm inserts through the page's insert-text field; Ctrl+A and findings 174/175 are established on the mirror (S1, S2, U3, U4), not re-measured on this host -- the owner's hand test is that measurement.
- `capture-after.py install-20261030T095504+0800 files-workflow-01` (absolute paths) -> `post-install-identity.json` **holds: true** (host 93b1ebc clean, installed_version 0.2.42, buildId 01e6c3fb62626d16, engine equals the archive, documents and lock rows equal the installer's after-state, owned folder 404, temporary user absent, build id in every entry).
- Red cases (`post-install-red/`), built as 0.2.41's were: the first workflow check flipped with the report's `ok` recomputed as the runner does -> exit 1 (`failed: ['owned-folder']`); the predecessor build id `829a988e199ebc43` in the first Writer entry -> exit 1 (`buildIdInEveryEntry: false`). The inherited named limit (the script gates on the summary `ok`, not the cells) is unchanged.

Status: **0.2.42 is installed as the daily uncounted candidate**, superseding 0.2.41. Nominal shipped host stays **0.2.26**; K has not run. Rollback, if needed: `rollback-package.sh` (exact 0.2.41 engine; needs a slot). Next: the owner's hand tests (spec 5.9 a-c, and d: Ctrl+A then Ctrl+C shows 「已複製 N 字」).

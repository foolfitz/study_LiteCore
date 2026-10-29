# Host 0.2.40 preparation: Writer v25 (findings 171/172 fixed), viewer and Calc retained

Declared before packaging, 2026-10-29 (spec v25 sections 8 step 7, 14-16; handoff 10-29f step 5).

**Live predecessor** (verified 2026-10-29 ~18:08 +0800): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **4a8b3cd** (label 0.2.39), clean, with the **exact 0.2.38 engine** (`host-0.2.38-engine-5ad1f70a8c5f7d2f`, all 93 files equal) after this morning's rollback. So the candidate's parent is 4a8b3cd and its predecessor archive is the 0.2.38 one, not the 0.2.39 one.

**Candidate scope**: isolated worktree `wasm_sdk_probe/build/host-0.2.40/litecore`, branch **host-0.2.40**, commit **ae1f9db** (only `appinfo/info.xml` 0.2.39 -> 0.2.40). Package the current three-page closure from `dist/` with the canonical packager; the editor must be v25 (`e2-editor-v25`, page `6e66c930`, frozen shell 78), viewer v3, Calc v2 and the 0.2.38 dark-theme HTML retained. Archive exact bytes; keep the exact 0.2.38 rollback.

**Evidence gate** (`prepare-release.py` refuses otherwise): the carried-over v24 counts (`V24_SELECTION_COUNTS_HOLD`, A4-v24 24/24; owner's carry-over, spec v25 section 14) and v25's own checks by their recorded verdicts: F1 `F1_HOLDS`, F2 `F2_HOLDS`, F3 `F3_HOLDS` (**`read-02.json`**, spec 16.1), F4 24/24 PASS, section 9 reader `CONFINED_V25_HOLDS`.

**Scripts** (each derived from its 0.2.39 counterpart, which is not edited; the closed list of differences is in each docstring): `prepare-release.py`, `offline-package-check.py`, `install-0.2.40.py`, `rollback-package.sh` (exact 0.2.38 engine, label stays 0.2.40), `capture-after.py`. Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

**DDEV**: the owner said at ~18:05 that DDEV can be used now and asked to stop the other DDEV containers; fgp-nc and nc-bridge were stopped at 18:06 (`ddev stop`), litecore left running. The installer additionally needs `slot.json` with the owner's no-site agreement and window; it is not written until the owner confirms those (the request to use DDEV is not, by itself, a no-site answer).

Not in this package: K (needs its own 8-10 h no-site window and the settled control protocol). Nominal shipped host stays 0.2.26.

## Offline results (18:42-18:45 +0800)

- `prepare-release.py` (`package-run-01.*`, exit 0, 156 s; canonical packager 152.2 s): engine **a08bc6ecb7241448**, 46 files (525,967,154 raw bytes). Against the live 0.2.38 predecessor: **38 complete records identical**; four changed modules (`e2-editor-app.js`, narrow-v2 client and session, `sdk/document-sdk.js` -- the same four as 0.2.39's delta against 0.2.38); the four `e2-editor-v25` profile files added; the four `e2-editor-v22` files removed. Viewer/Calc page identities and the 0.2.38 dark-theme HTML unchanged. Both codings decode to the exact current `dist/` bytes. Evidence gate (`release.json` `v25Gates`): F1, F2, F3 (`read-02`), F4, section 9 all hold.
- Archive `wasm_sdk_probe/build/archive/host-0.2.40-engine-a08bc6ecb7241448` (not in git), MANIFEST sha256 `2eebdc71…`, all 94 members bound by `archive.sha256`.
- `offline-package-check.json`: **PACKAGE_HOLDS**, zero problems, **22/22** red cases red.
- `offline-install-preflight.json`: **OFFLINE_INSTALL_READY** (parent 4a8b3cd, candidate ae1f9db).

## Live installation (owner slot 18:45:50-19:30 +0800, `slot.json`)

The owner answered the slot question "A: install once ready; I will not open litecore.ddev.site" and chose to keep fgp-nc and nc-bridge stopped afterwards (they were stopped at 18:06 at the owner's request). Only litecore and the router ran throughout (`ddev-after-coordination.json`, `ddev-after-slot.json`).

- `install-0.2.40.py --preflight-only` -> **LIVE_PREFLIGHT_READY** (`install-20261029T184555+0800/`): protected documents 24674/24920/25391 read 200; `oc_files_lock` **zero rows**.
- `install-0.2.40.py` -> **CANDIDATE_INSTALLED** (`install-20261029T184615+0800/`): fast-forward 4a8b3cd..ae1f9db (info.xml only), exact engine rsync, `occ upgrade` to 0.2.40; protected documents and full lock rows equal before/after; maintenance off, no pending DB upgrade; e2-editor/ods-viewer/ods-editor unauthenticated routes all **401**.
- **Files workflow** `files-workflow-01/` (unchanged `run_calc_editor_host.py`, Chrome + Firefox, 18:46:40-18:48:25): **52/52 PASS**; cleanup: no owned unlocks, share and user removed, folder DELETE 204; every entry landed on `/r/a08bc6ecb724…`. Same coverage and the same stated limit as 0.2.39's run: the Writer arm inserts through the page's insert-text field, not real keys; the 171/172 fixes are established on the mirror (F1-F4), not re-measured on this host.
- `capture-after.py` -> `post-install-identity.json` **holds: true** (host ae1f9dbc clean, installed_version 0.2.40, buildId a08bc6ecb7241448, engine equals the archive, documents and lock rows equal the installer's after-state, owned folder 404, temporary user absent). Red cases (`post-install-red/`): one flipped workflow check -> exit 1 (`failed: ['owned-folder']`); the predecessor build id in one Writer entry -> exit 1 (`buildIdInEveryEntry: false`).

Status: **0.2.40 is installed as the daily uncounted candidate**, superseding 0.2.39-label-with-0.2.38-engine. Nominal shipped host stays **0.2.26**; K has not run. Rollback, if needed: `rollback-package.sh` (exact 0.2.38 engine; needs a slot).

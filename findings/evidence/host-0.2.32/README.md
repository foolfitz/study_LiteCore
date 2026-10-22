# Host 0.2.32 — the package carrying ods-viewer-v2, its offline checks, and the way back

Written 2026-10-23 01:3x CST, BEFORE anything on the live instance was touched (SPEC-M4-viewer-v2 §10).

## The package

- Host: branch `host-0.2.32` (`bffc7dc`) of `~/Projects/Nextcloud_Apps/litecore` = 0.2.31 (`421f4b8`) + `<version>0.2.32</version>`. No host code changed.
- Built from study_LiteCore `dist/` at `bd3e1b5b` (the viewer page re-pointed at v2 in `ffb6fe57`, staged with `make ods-viewer-assets`) by `tools/package_m3_engine.py --app <scratch worktree of host-0.2.32>`, schema `litecore-engine/3`: buildId **`80349a1a24cecb17`**, 35 files, 340,275,823 B decoded, 116,503,128 B gzip, 83,956,258 B zstd, 1 min 37 s.
- Page table: `e2-editor.html` → `e2-editor-v22` (wasm `f7a40bcc…`, module `3b96cb16…`), `ods-viewer.html` → **`ods-viewer-v2`** (wasm `aa576ce7…`, module `c2159481…`).
- Against 0.2.29-0.2.31's package `1b4d6a1fc905fb8a`, file by file (`manifest-diff.txt`): 25 files identical (the editor page and profile, the shared SDK, tile scheduler and CJK pack); 4 changed (`ods-viewer-app.js`, `viewer-shell/ods-document-sdk.js`, `viewer-shell/ods-viewer-session.js`, `viewer-shell/w7-adapter.js`); the six `profiles/ods-viewer-v1/` files replaced by six `profiles/ods-viewer-v2/` files, byte-identical to `build/archive/ods-viewer-v2-aa576ce7-worker-9c85043a/`. `ods-viewer.html` is unchanged.
- Largest gzip: the viewer wasm, 47,971,896 (cap 52,428,800). Largest zstd: the same file, 36,048,845 (cap 45,000,000).
- Archived at `wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17/` (+ `ATTRIBUTION.md`); `diff -rq` against the worktree's `engine/` was empty after the copy.

## Offline checks

- `package_m3_engine.py --selftest`: 13/13.
- `offline-package-check.py <worktree>` (this directory; the package half of `check_m3_assets.py --red-cases`, on an app directory): K0/Z0/H5-1 **0 problems**, **22/22** package red cases red (`offline-package-check.txt`).
- Negative control, same script on the live app dir (0.2.31, package `1b4d6a1f`) against the re-pinned `BUILD_ID` and today's `dist/`: exit 1, 22 problems — K0-1 ×1, K0-2 ×10, Z0-1 ×10, Z0-4 ×1 (`offline-package-check-control-live-0.2.31.txt`).
- `check_m3_assets.BUILD_ID` is re-pinned to `80349a1a24cecb17` (as 0.2.29 did when its package changed): a binding, not a check change.

## Pre-check before the install, observed 2026-10-23 01:30

`diff -rq ~/Projects/Nextcloud_Apps/litecore/engine wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a` → only `ATTRIBUTION.md`. The live `engine/` IS the 0.2.29 archive, so that archive is the way back. (`engine.old` in the app dir is 0.2.27/0.2.28's `817413d5`, untouched.) `install-0.2.32.sh`'s pre-check block, run alone with its log in the scratchpad: all hold (01:30). A guard was then added for the container: `ddev list` at 01:34 showed `litecore` **paused** and `fgp-nc` running, and `occ upgrade` on a paused project would stop the script after the code and the package had already moved. The re-run of the pre-check block at 01:35 stopped on exactly that line (`STOP: ddev project litecore is 'paused', not running`) -- the guard's red case, on the real state.

## The way back (the package only)

0.2.32's code is 0.2.31's plus the version, so restoring the package is the whole functional rollback; the code may stay at 0.2.32 and Nextcloud keeps the label 0.2.32 (no `occ` needed):

```bash
rsync -a --delete --exclude ATTRIBUTION.md /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a/ ~/Projects/Nextcloud_Apps/litecore/engine/
diff -rq ~/Projects/Nextcloud_Apps/litecore/engine /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a   # only ATTRIBUTION.md
```

Each switch of the package makes warm browsers fetch the engine files once more (a new buildId is a new address).

## Not done here

The install (`install-0.2.32.sh`) and Phase H (`chain-phase-h.sh`): both touch ddev, which is shared; they wait for a slot the owner names. Runbook: `handoff/RUNBOOK-install-host-0.2.32.md`.

## The slot's run (2026-10-23 01:39 onward; appended after the run)

- The owner named the slot at 01:39 (stopped fgp-nc, started litecore). Step 0 at 01:40:12: `ddev list` running set {litecore} (nc-bridge paused, the rest stopped); KWallet `Locked` = `b false`; load 0.45.
- **Install** (`install-0.2.32.sh`, 01:40:41-01:40:55, `install.txt`): every pre-check held; `merge --ff-only` → host HEAD `bffc7dc`; `rsync --delete` → live buildId `80349a1a24cecb17`, differs from the archive only by `ATTRIBUTION.md`; `occ upgrade` → `litecore: 0.2.32`, maintenance off; both routes 401 to the unauthenticated curl.
- **Phase H** (`chain-phase-h.sh` with `WINDOW_END='2026-10-23 02:45'`, 01:41:14-01:49:40, `chain.log`; every step exit 0, no guard refusal):
  - `h-viewer`: `findings/evidence/m4-ods/phase-h/shakedown/2026-10-22T174116+0000.json` -- **VIEWER HOST HOLDS**, no problems (H1, H2 + positive control + lock-taking red arm, H3, H6).
  - The served engine is v2: `access-log-viewer-engine.txt` -- the container's Apache log in the window has the six `profiles/ods-viewer-v2/` files, once per arm, all 200, and no `ods-viewer-v1` request (the H report does not record the profile; the log does).
  - `h155-chrome`, `h155-firefox`: H-154c, H-154o, H-155 PASS, 3 rounds each (`judge-h155.txt`, `h155/`).
  - `host-entry`: HOST_ENTRY LANDS (`findings/evidence/m3-host-entry/shakedown/2026-10-22T174406Z.json`).
- SPEC-M3-production-ui §17.27 residual 1: the H runner's Chrome (`EventChrome`, a `ChromeSession`, `--password-store=basic`) logged in on both arms (200 → dashboard) and its cookie-borne DAV GETs answered 200.
- Reading (SPEC-M4-viewer-v2 §10.3, first row): 0.2.32 replaces 0.2.31 as the uncounted daily candidate. H7 is the owner's.

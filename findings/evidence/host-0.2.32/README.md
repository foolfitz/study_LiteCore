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

`diff -rq ~/Projects/Nextcloud_Apps/litecore/engine wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a` → only `ATTRIBUTION.md`. The live `engine/` IS the 0.2.29 archive, so that archive is the way back. (`engine.old` in the app dir is 0.2.27/0.2.28's `817413d5`, untouched.) `install-0.2.32.sh`'s pre-check block, run alone with its log in the scratchpad: all hold.

## The way back (the package only)

0.2.32's code is 0.2.31's plus the version, so restoring the package is the whole functional rollback; the code may stay at 0.2.32 and Nextcloud keeps the label 0.2.32 (no `occ` needed):

```bash
rsync -a --delete --exclude ATTRIBUTION.md /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a/ ~/Projects/Nextcloud_Apps/litecore/engine/
diff -rq ~/Projects/Nextcloud_Apps/litecore/engine /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a   # only ATTRIBUTION.md
```

Each switch of the package makes warm browsers fetch the engine files once more (a new buildId is a new address).

## Not done here

The install (`install-0.2.32.sh`) and Phase H (`chain-phase-h.sh`): both touch ddev, which is shared; they wait for a slot the owner names. Runbook: `handoff/RUNBOOK-install-host-0.2.32.md`.

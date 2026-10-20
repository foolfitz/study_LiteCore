# Host 0.2.29 — the package, the way back, and the witness for the check changes

Written 2026-10-20 night, BEFORE anything on the live instance was touched (fable's ruling of
2026-10-20 23:30, SPEC-M4 addendum 9, condition Q1-3).

## The package

- Built from study_LiteCore `dist/` at `b70c12b2` by `tools/package_m3_engine.py` (schema
  `litecore-engine/3`): buildId **`1b4d6a1fc905fb8a`**, 35 files, 340,254,512 B decoded,
  116,501,319 B gzip, 83,955,910 B zstd. Page table: `e2-editor.html` → `e2-editor-v22`
  (wasm `f7a40bcc…`), `ods-viewer.html` → `ods-viewer-v1` (wasm `f6ab3cdb…`).
- Archived at `wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a/` (192 MB on disk;
  `ATTRIBUTION.md` beside it). Built in the scratch worktree of branch `host-0.2.29` (`9a349f6`).
- Offline: `package_m3_engine.py --selftest` 13/13; `check_m3_assets.py` K0/Z0/H5-1 **clean** on this
  package, 22/22 package red cases (the three H5 cases — a one-page manifest, a page whose wasm is not
  packaged, a schema-2 manifest — red); `validate_manifest()` empty.

## Pre-check (Q1-3), observed 2026-10-20 23:4x

`diff -rq ~/Projects/Nextcloud_Apps/litecore/engine wasm_sdk_probe/build/archive/host-0.2.27-engine-817413d5ad5bd502`
→ "Only in …/host-0.2.27-engine-817413d5ad5bd502: ATTRIBUTION.md", nothing else. The live `engine/` IS
the 0.2.27 archive (0.2.28 did not touch the engine), so the archive is the restore source.

## The way back (three commands; Nextcloud keeps the label 0.2.29, the bytes are 0.2.28's)

```bash
git -C ~/Projects/Nextcloud_Apps/litecore checkout 0870695 -- .     # or: git revert 9a349f6
rm -rf ~/Projects/Nextcloud_Apps/litecore/engine && cp -r /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/archive/host-0.2.27-engine-817413d5ad5bd502 ~/Projects/Nextcloud_Apps/litecore/engine && rm -f ~/Projects/Nextcloud_Apps/litecore/engine/ATTRIBUTION.md
cd ~/Projects/Nextcloud_Apps/litecore && ddev occ upgrade
```
Then `git -C ~/Projects/Nextcloud_Apps/litecore status --short` must show only the restored files,
and `diff -rq engine/ …/host-0.2.27-engine-817413d5ad5bd502` only ATTRIBUTION.md again.

## Witness for the check changes (§34, fable Q3-2)

`check_m3_assets.py` and `probe_m3_assets.py` changed because execution forced it: the 0.2.29 package
cannot be scored by the pre-change tools. Stated from the diff `f0351130..b70c12b2` (the pre-change
tools were NOT run against the package in this session — the attempt was refused by the session's
permission mode; the facts below are static):

- pre-change `check_m3_assets.py` line 100: `ENGINE_SCHEMA = "litecore-engine/2"` and `BUILD_ID =
  "f5f0df762e1855f2"`; the package says `litecore-engine/3` / `1b4d6a1fc905fb8a` → **Z0-4 red** by
  the clause's own text (`manifest.get("schema") != ENGINE_SCHEMA or manifest.get("buildId") != BUILD_ID`).
- pre-change `probe_m3_assets.closure()` derives the editor page's closure only (22 files; it reads
  `PAGE_MODULE = "e2-editor-app.js"` and one workerUrl); the package lists 35 → **K0-1 red** (`set(listed)
  != set(pkg["derived"])`, 13 viewer-only files).
- After the change: K0-1 compares against the union of both pages' closures and matches; Z0-4 binds
  schema 3 and the new build id; H5-1 is new (two red cases).

The old `old-tool-red.txt` was not produced; this section is the witness.

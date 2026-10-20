# Runbook: install host 0.2.29 (the ODS viewer) on the owner's ddev instance

> **What happened (2026-10-20/21):** steps 1–4 ran as `findings/evidence/host-0.2.29/install-0.2.29.sh`
> (the old package went to `engine.old`, which is git-ignored, not `engine.0.2.28`). 0.2.29 answered 500 on
> every route (finding 161) and 0.2.30 on the viewer document (finding 162); `install-0.2.30.sh` and
> `install-0.2.31.sh` in the same directory moved the code only. ddev runs **0.2.31** (`421f4b8`) on this
> package. The way back is `findings/evidence/host-0.2.29/README.md`. The rest of this file is as written.

Written 2026-10-20 night, before any install. Whoever runs this (the owner, or a session in a slot
the owner or fable's ruling allows) follows it line by line; nothing here compiles.

## What exists before the install

- The host repo `~/Projects/Nextcloud_Apps/litecore` is on `main` at `0870695` (0.2.28) and IS the
  directory the live ddev instance serves (`ddev-litecore-web`).
- Branch `host-0.2.29` (commit `9a349f6`) holds 0.2.29, checked out in the worktree
  `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/6b8e0baf-72b8-4cf1-bc4e-16d6fd7e6ae9/scratchpad/litecore-0.2.29`
  (a scratch path: if it is gone, the branch is still in the repo; only the built `engine/` must be
  re-made, step 2b).
- That worktree's `engine/` is the schema-3 package: buildId `1b4d6a1fc905fb8a`, 35 files, gzip
  116,501,319 B, zstd 83,955,910 B; K0/Z0/H5-1 clean offline, 22/22 red cases
  (study_LiteCore `b70c12b2`).
- study_LiteCore `dist/` has the viewer page and shell staged (`make ods-viewer-assets`, cp only).

## 1. Switch the app's code (seconds; the editor route 500s until step 2 is done)

```bash
git -C ~/Projects/Nextcloud_Apps/litecore status --short      # must be empty
git -C ~/Projects/Nextcloud_Apps/litecore merge --ff-only host-0.2.29
```

From this moment the controller demands a schema-3 package; the old `engine/` (schema 2) makes every
`r/` request answer 500 "the engine is not packaged for this host". Do step 2 at once.

## 2. Put the schema-3 package in place

2a. Fast path (the worktree's `engine/` exists): keep the old package aside, copy the new one.

```bash
mv ~/Projects/Nextcloud_Apps/litecore/engine ~/Projects/Nextcloud_Apps/litecore/engine.0.2.28
rsync -a /tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/6b8e0baf-72b8-4cf1-bc4e-16d6fd7e6ae9/scratchpad/litecore-0.2.29/engine/ ~/Projects/Nextcloud_Apps/litecore/engine/
python3 -c "import json;print(json.load(open('/home/jiajun/Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json'))['buildId'])"
```
Expect `1b4d6a1fc905fb8a`.

2b. Slow path (no worktree `engine/`): repackage from dist (2–3 minutes of gzip -9 + zstd 19):

```bash
python3 /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/package_m3_engine.py
```
It writes `~/Projects/Nextcloud_Apps/litecore/engine/` and prints the same buildId (the codings are
deterministic for a given zlib and libzstd).

## 3. Tell Nextcloud about the version

```bash
cd ~/Projects/Nextcloud_Apps/litecore && ddev occ upgrade && ddev occ app:list | grep -A1 -i litecore
```
Expect `litecore: 0.2.29`, maintenance false. (The host scripts are served as `?v=md5(version)`,
immutable: the version bump is what makes browsers fetch the new `litecore-files.mjs`.)

## 4. Smoke (one minute, no browser)

```bash
cd ~/Projects/Nextcloud_Apps/litecore && B=$(ddev describe -j | python3 -c "import json,sys;print(json.load(sys.stdin)['raw']['primary_url'])")
curl -sk -o /dev/null -w '%{http_code} %{redirect_url}\n' "$B/index.php/apps/litecore/r/ods-viewer.html?fileId=0"
```
Expect `302` to `.../r/1b4d6a1fc905fb8a-<8 hex>/ods-viewer.html?fileId=0` (a login redirect is also
possible for an unauthenticated curl — then the Location is the login page; the point is "not 500").

## 5. Phase H, mechanical half

```bash
python3 /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m4_host_viewer.py --label shakedown
```
Two arms: `plain` (H1, H2 with its positive control, H3) and `lock-taking-host` (H2's red case);
H6 on the wire. Report under `findings/evidence/m4-ods/phase-h/shakedown/`. **The first red is the
measurement**: the Files action-menu selectors in `row_actions()` were written from the Nextcloud
33 Files markup without a run; if H1 reports "the row's menu was not read", read the recorded
`actions` list before touching anything.

Then H4: the 0.2.28 host arms on 0.2.29 (`check_m3_host_entry.py --label shakedown`, the H-154/H-155
arms as 10-20c ran them) — the editor must be unchanged.

## 6. If something is red on the product and the owner is away

Leave 0.2.29 installed (the viewer failing does not affect the editor route; the editor's package
bytes are the same as 0.2.28's), record, and stop. To roll back instead:

```bash
git -C ~/Projects/Nextcloud_Apps/litecore reset --hard 0870695
rm -rf ~/Projects/Nextcloud_Apps/litecore/engine && mv ~/Projects/Nextcloud_Apps/litecore/engine.0.2.28 ~/Projects/Nextcloud_Apps/litecore/engine
```
Nextcloud keeps `0.2.29` as the installed version in appconfig (it never downgrades); the code and
package are 0.2.28's again and serve as before.

## 7. Afterwards

```bash
git -C ~/Projects/Nextcloud_Apps/litecore worktree remove /tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/6b8e0baf-72b8-4cf1-bc4e-16d6fd7e6ae9/scratchpad/litecore-0.2.29
rm -rf ~/Projects/Nextcloud_Apps/litecore/engine.0.2.28      # once 0.2.29 is kept
```

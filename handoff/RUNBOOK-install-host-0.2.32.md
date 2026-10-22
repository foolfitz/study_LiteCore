# Runbook: install host 0.2.32 (the viewer on ods-viewer-v2) on the owner's ddev instance, then Phase H

Written 2026-10-23 01:3x CST, before any install. Spec: `specs/SPEC-M4-viewer-v2.md` §10 (package, way back, Phase H criteria and readings, all pinned before any run). Evidence and the way back: `findings/evidence/host-0.2.32/README.md`. Nothing here compiles. **ddev is shared: run this only in a slot the owner names** (memory `ddev-is-shared-do-not-occupy`).

## What exists before the install

- `~/Projects/Nextcloud_Apps/litecore` is on `main` at `421f4b8` (0.2.31) and IS the directory the live ddev instance serves; its `engine/` is package `1b4d6a1fc905fb8a` (= `wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a/` + nothing; checked 01:30).
- Branch `host-0.2.32` (`bffc7dc`) = 0.2.31 + the version. Its scratch worktree (`/tmp/claude-1000/…/scratchpad/litecore-0.2.32`) may be gone; nothing needs it: the package is archived at `wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17/`.
- Offline gates green: packager selftest 13/13, K0/Z0/H5-1 clean, 22/22 package red cases (§10.1).

## 0. Before the first ddev command (read-only)

```bash
ddev list                                   # record the running set; expect {litecore}
busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked   # `b false`; the chain's guard refuses on `b true`
```
If another project is running, stop and ask the owner (the chain's guard would refuse anyway).

## 1–4. Install (seconds)

```bash
bash /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.32/install-0.2.32.sh
```
Pre-checks (tree clean, HEAD `421f4b8`, branch `bffc7dc` on `421f4b8`, live `engine/` = the 0.2.29 archive, new archive's buildId) → `merge --ff-only host-0.2.32` → `rsync --delete` the archived package into `engine/` → `ddev occ upgrade` → curl both routes. Expect in `install.txt`: `live buildId now 80349a1a24cecb17`, the diff line only `ATTRIBUTION.md`, `litecore: 0.2.32`, both routes 401 (unauthenticated, no `html` in Accept) or a login redirect — **not 500**. Any `STOP:` line: nothing after it ran; read it.

If the session's own call is refused by the auto-mode classifier ("Production Deploy"), say so at once and hand the owner the one line above (memory `short-commands-run-them-yourself`).

## 5. Phase H (about 10 minutes)

```bash
WINDOW_END='YYYY-MM-DD HH:MM' bash /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.32/chain-phase-h.sh
```
Steps, each behind the window / `ddev list` / wallet guard: `h-viewer` (`check_m4_host_viewer.py --label shakedown`: H1, H2 + positive control + `lock-taking-host` red arm, H3, H6; report under `findings/evidence/m4-ods/phase-h/shakedown/`), `h155-chrome`, `h155-firefox` (H4: H-154c/H-154o/H-155, 3 rounds each, judged with `--require-h155` into `judge-h155.txt`), `host-entry` (`check_m3_host_entry.py --label shakedown`; report under `findings/evidence/m3-host-entry/shakedown/`). The chain's log is `findings/evidence/host-0.2.32/chain.log`; each step's stdout is `<step>.log` beside it.

The `h-viewer` step is the first host Chrome runner under `--password-store=basic`: it is the witness for SPEC-M3-production-ui §17.27's residual 1. Record whether it started without a wallet prompt.

## 6. Reading (pinned in §10.3)

- All of H1–H4, H6 hold → 0.2.32 replaces 0.2.31 as the uncounted daily candidate; tell the owner how to do H7 (below).
- Any red → read the raw inputs first (the first red is the measurement), change no tool inside the slot, run the way back (README: one `rsync --delete` from the 0.2.29 archive; the code may stay at 0.2.32), record, stop before H7.
- Only NOT_ESTABLISHED → leave 0.2.32 installed, register it, the owner decides.

## 7. H7 (the owner, after 6 holds)

Upload `wasm_sdk_probe/test-docs/ods/ladder/three-sheets-distinct.ods`, click it in Files: the viewer, tabs Alpha/Beta/Gamma, Beta switches the sheet. The first open of an .ods downloads the v2 engine once (~41.7 MB zstd); the first ODT open after the install re-downloads the editor's engine files once (new buildId). What changed for the owner to see (release text draft `handoff/RELEASE-TEXT-DRAFT-0.2.32.md`): `upstream/date-time-functions.ods` and `upstream/functions.ods` now show values where 0.2.31 showed `#VALUE!` (159); `upstream/fdo67682-2.ods`'s hidden sheets are disabled tabs instead of clickable-and-refused (157); `upstream/tdf134161.ods` is still refused `FORM_CONTROLS_UNSUPPORTED` (158-A).

## 8. Afterwards

```bash
git -C ~/Projects/Nextcloud_Apps/litecore worktree remove --force /tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/d3e84330-87a0-41ea-a659-43ca30bc872c/scratchpad/litecore-0.2.32   # if it still exists; --force because engine/ is untracked in it
```

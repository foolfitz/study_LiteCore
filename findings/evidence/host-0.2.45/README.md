# Host 0.2.45 preparation: Writer on profile e2-editor-v29 with shell generation 83 and the icon toolbar

## Declared before packaging, 2026-11-01

Spec `specs/SPEC-M3-v29-tick-pacing.md` append 6. A relink: `e2-editor-v29` was linked on the owner's word on 2026-11-01 (wasm `e61e5890...`, worker `a5df83db...` = v28's bytes, archive `build/archive/e2-editor-v29-e61e5890-worker-a5df83db`).

**Live predecessor** (read-only): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **a97724f** (0.2.44), clean. Its engine is the 0.2.44 archive `host-0.2.44-engine-dacdfa20fd4ff1ea`.

**This is the first release on the own stack** (`specs/SPEC-M3-own-stack.md`). No owner slot: the slot existed because ddev was shared. The install checks instead that `ddev` is the adapter answering for the running stack.

**Candidate.** Isolated worktree `wasm_sdk_probe/build/host-0.2.45/litecore`, branch **host-0.2.45**, from a97724f. The only source change is `appinfo/info.xml` 0.2.44 -> 0.2.45.

**Expected delta against 0.2.44**, computed from `closure(dist)` against the archived MANIFEST (`prepare-release.py` refuses anything else; `check-delta.py` re-derives it from the two archived MANIFEST files):
- changed, exactly two: `e2-editor-app.js` and `e2-editor.html`;
- added, exactly four: `profiles/e2-editor-v29/{probe.js,probe.wasm,sdk-manifest.json,sdk-worker.js}`;
- removed, exactly four: the same four under `profiles/e2-editor-v28/`;
- `sdk-worker.js` the same bytes as v28's; the other three different. 0.2.44's scripts demanded all four differ and would have refused this.

**Scripts**, each derived from its 0.2.44 counterpart (not edited), by `../v29-177/derive/derive_host_0245.py` and `derive_host_0245_prepare.py` (each replacement must match its count); the closed list is in each docstring or header.

`p-contract.txt`: `check_v29_tick_pacing_contract.py --manifest ... --exports ...`, re-run here because the link's own receipt is not in the tree: `v29 preconditions hold`. `withheld` is empty, 23 actions, ABI 6.

## Offline results (2026-11-01 ~22:07-22:11 +0800)

- **`prepare-release.py`**, package-run-01, exit 0, 148 s: engine **623f51d295ff6030**, candidate **eeac22c**, archive `wasm_sdk_probe/build/archive/host-0.2.45-engine-623f51d295ff6030` (not in git), bound by `archive.sha256`. 40 records unchanged; the declared two changed, four added, four removed; worker bytes equal (`release.json` `profileSuccessor`).
- **`gate-red-cases.py`** -> `gate-red-cases.json`: **GATE_RED_CASES_HOLD**. The unchanged run passes the gates; 24 cases, each a real evidence read changed in memory, each refused by the v29 gate itself. It ran before the install because the gate needs the host on 0.2.44. Its first run reported two `held`: both were refused, by earlier gates, because its suffix match also hit `v28-083/s4/...` and `shell-v79-173/v0/...`. The harness was at fault, the targets were made exact.
- **`check-delta.py`** -> `check-delta.json`: **DELTA_HOLDS**, all nine red cases red, `worker_moved` among them.
- **`offline-package-check.py`** -> `offline-package-check.json`: **PACKAGE_HOLDS**, 22/22 red cases red.
- **`install-0.2.45.py --offline-only`**: **OFFLINE_INSTALL_READY**. **`--preflight-only`** through the adapter: `LIVE_PREFLIGHT_READY`; without the adapter on PATH: refused, `not the own stack`.

## Live installation (2026-11-01 22:12 +0800)

**`install-0.2.45.py`** (`install.*`, `install-20261101T*/`): **`CANDIDATE_INSTALLED`**. Host main a97724f -> **eeac22c**, engine `623f51d2...`, `installed_version` 0.2.45, `preservedDocumentsAndLocks: true`, `globalLockWrites: false`, the three routes 401 unauthenticated.

**Files workflow** (`files-workflow-01/`, unchanged `run_calc_editor_host.py`, Chrome and Firefox): **52/52**, `ok: true`, cleanup clean.

**`capture-after.py`** -> `post-install-identity.json`: **`holds: true`**: host clean, engine equals the archive, protected documents and lock rows equal the installer's after-state, temporary user absent.

**First look** (`first-look/`, not a gate): the icon toolbar inside Nextcloud, both browsers. 14 visible buttons of 22, all 32 x 34, icons 20, nothing past the right edge at a 780 px viewport, tooltip `粗體 (Ctrl+B)` by real pointer, typing lands in the document. The script's own defects, not the product's: navigating away after typing timed out in Chrome (inferred, not checked: the page's guard for unsaved work), so Chrome's lock stayed and Firefox correctly showed the another-window banner; a pointer target past Firefox's 682 px viewport. The lock was left to expire and the scratch folder then removed, 204, lock table empty.

**Section 7**: `section-7/README.md`.

**Pending: the owner's hand tests** (typing, the toolbar), then the owner's decision whether 0.2.45 replaces 0.2.44 as the daily uncounted candidate. Rollback, if wanted: `rollback-package.sh` with `host-stack/bin` first on PATH (exact 0.2.44 engine, label stays 0.2.45). Accumulated uncounted engine changes since 0.2.26: v22-v29.

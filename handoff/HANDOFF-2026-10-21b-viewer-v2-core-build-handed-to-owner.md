# Handoff, 2026-10-21b: viewer v2 — the core build is the owner's next command; engine, shell, builder and Phase E readings are in the tree, unlinked

**First line, in SPEC-M3-link-batch-v22 §13.1's shapes:**
- **(a) installed:** unchanged — ddev runs host **0.2.31** on package `1b4d6a1fc905fb8a`; `engine.old` still in the app dir (kept until H7).
- **(b) built and archived, uncounted:** nothing new. No v2 core, no v2 link yet.
- **(c) bound / counted:** nothing. Nominal shipped version still **0.2.26**; K batched.
- **(d) accumulated-uncounted list:** unchanged from 10-21 (d). The v2 batch (159, 158-B, 157, 160) is source-only so far.

Spec: **`specs/SPEC-M4-viewer-v2.md`** (§0–§2 core, §3 engine/shell/profile, §3.8 Phase E readings, §4 the v2 criteria; all pinned before any v2 link or run). SPEC-M4 addendum 11 points to it. Previous handoff: `HANDOFF-2026-10-21-host-0231-phase-h-holds.md`.

## What happened

| | what | record |
| --- | --- | --- |
| 1 | **Finding 163 resolved by reading:** the four UNLOCKs are the host's design — `release()` sends two keepalive copies per call, called from `beforeunload` and `pagehide` (exp10 V3; the Firefox cache rows). The host-side "send once" fix is withdrawn (it would bring 105 back); the 500 is `files_lock`'s uncaught `LockNotFoundException` (upstream, on hold) | finding 163 |
| 2 | **Instance clean-up (owner chose A):** the 16 Phase H fixtures deleted by WebDAV (204 ×9, in admin's trash); `ddev list` running {litecore}, nothing started/stopped | `findings/evidence/host-0.2.29/README.md` (end) |
| 3 | **Owner: 158-B stays in v2** ("重編其實無所謂") after I reported that Emscripten forces DB connectivity off in two places in `configure.ac` | spec §0, D-1 |
| 4 | Two source patches in `libreoffice-26-8` (shared tree), snapshotted; all eight pass `git apply --check --reverse` | `wasm-lite/patches/INVENTORY.md` |
| 5 | **159 measured offline before any build:** gate0's build-side `wasmbridgegen` reproduces the core's outputs byte for byte; with scaddins 55 → 80 signatures incl. `didddi`/`diiii`/`diiiii`/`diiiiii`. Corrected 159's `didddd` (wrong, and a substring check would have "found" it in `didddddd`) | `findings/evidence/m4-ods/phase-e/159-diagnosis/bridgegen-offline/` |
| 6 | New core tree prepared (`wasm-lite/build-ods-viewer-v2`: gate0's autogen.input + 4 lines), K-1/K-2 checker with red cases on gate0, one-line build script | `17c5d50b`; `handoff/RUNBOOK-ods-viewer-v2-core-build.md` |
| 7 | Engine/worker/SDK/adapter/session/page for 157, 160, 158-B; v2 profile builder; Makefile rule `ods-viewer-v2`; carrier declared | `99d06192`; spec §3 |
| 8 | Phase E runner/harness readings for v2; selftest 43/43; exercised on v1 on the mirror (E1–E6 PASS, 12 records) | `b042461c`; `…/viewer-v2/pre-link/v1-shakedown-new-shell/` |

## Next, in order

1. **The owner runs the core build** (handed over in the chat, not yet started at 10:38):
   `bash /home/jiajun/LibreOffice/study_LiteCore/handoff/ods-viewer-v2/build-core.sh` — autogen, K-1, `make -j12`, K-2; it prints `DONE: …` or `STOP: …`. Read `findings/evidence/m4-ods/viewer-v2/core/` and the build dir's `configure.log`/`build.log` yourself.
   - `STOP` in a DB-connectivity module (forms, connectivity, dbtools…) → **F-1**: register the failing target as a finding, then 159-only on gate0 (`rm` the three files in `build-a11y-gate0/workdir/CustomTarget/bridges/gcc3_wasm/`, owner's `make` there — note it re-runs autogen once first), link v2 with `ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0`.
2. After K-2: fill `handoff/RUNBOOK-link-ods-viewer-v2.md` §0 items 5–10 (test-e2-c-static must turn green once the tree is configured; the builder's `--check` on the v2 core and **read the base diff into spec §5**; `check_core_build_provides --capability calc-spreadsheet`; `make -n` token diff vs v1; the frozen set). Then hand the link to the owner.
3. After the link: runbook §3 (archive at once), then Phase E on v2: `run_ods_viewer_phase_e.py --profile ods-viewer-v2` — ladder + 157/158/159 files first; E6's B again on v2; then full corpus ×3 for V2-160. F-2 (gzip > 52,428,800) and F-3 (forms do not paint) fall back to 159-only.
4. **H7 (owner)** is still open from 10-21: click `three-sheets-distinct.ods` in Files on 0.2.31.
5. K stays batched.

## Hazards

- **Both core patches change the shared source tree.** The next `make` in `build-headless-probe` or `build-a11y-gate0` re-runs autogen once by itself (`config_host.mk` depends on `configure.ac`); compare `config_host.mk`/`config_host/*.h` before going further there.
- **`test-e2-c-static` is red until the v2 tree is configured** (`config_features.h` not found for ODS_VIEWER_V2's objects). That is a real red, not one to route around; the witness is committed.
- **Evidence runners write committed evidence by default.** `findings/evidence/m4-ods/W9-viewer-draft/red-cases.py` takes no options; I ran it with `--help`, it ran and overwrote `red-cases.{json,txt}` (restored from git). Read a runner's head before invoking it. Its M31–M35 anchors have been stale since 158-A (`f0351130`) — registered, not fixed.
- The new shell on **v1's** engine reports `part-visibility-unknown` (by design, spec §3.2): any v1 mirror run with today's shell is `evidenceClass: diagnostic`.
- `cd` moved the primary working directory twice this session (into `libreoffice-26-8`, `wasm_sdk_probe`); absolute paths and subshells everywhere else.

## §34.4

- This stretch: **because of execution +1** (`tests/sdk_worker_ods_viewer_mutations.py`'s `reply-forwarded-whole` anchor drifted with the worker's part-text literal; witness `findings/evidence/m4-ods/viewer-v2/pre-link/sdk-worker-mutations-red-anchor-drift.txt`). **Because of review +0.** Running total since 10-14b: **45 / 27.**
- Not counted as fixes: the Phase E runner's v2 readings (pinned in spec §4 first, no misjudged report) and the carrier line (a new rule's declaration, witness committed).
- Tools never reviewed: `package_m3_engine.py --selftest`, `check_m4_host_viewer.py`, the H5-1 clause in `check_m3_assets.py`, **`check_ods_viewer_v2_core.py`**, **`build_ods_viewer_v2_profile.py`**, and the v2 increment of `run_ods_viewer_phase_e.py` (decide before its first counted run whether it needs the one review §34 allows).

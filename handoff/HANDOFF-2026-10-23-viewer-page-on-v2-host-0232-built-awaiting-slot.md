# Handoff, 2026-10-23: the viewer page names v2, E4b/E9 hold on it; host 0.2.32 is built and checked offline; the install and Phase H wait for an owner-named ddev slot

**First line, in SPEC-M3-link-batch-v22 §13.1's shapes:**
- **(a) installed:** unchanged -- ddev runs host **0.2.31** on package `1b4d6a1fc905fb8a` (viewer `ods-viewer-v1` `f6ab3cdb`). At 01:34 `litecore` was **paused** and `fgp-nc` running.
- **(b) built and archived, uncounted:** **host 0.2.32** -- branch `host-0.2.32` (`bffc7dc`) of `~/Projects/Nextcloud_Apps/litecore`, engine package **`80349a1a24cecb17`** (`wasm_sdk_probe/build/archive/host-0.2.32-engine-80349a1a24cecb17/`), viewer `ods-viewer-v2` `aa576ce7`, editor `e2-editor-v22` `f7a40bcc` unchanged.
- **(c) bound / counted:** nothing counted. `check_m3_assets.BUILD_ID` re-pinned to `80349a1a24cecb17` (a binding). Nominal shipped version still 0.2.26; K batched.
- **(d) accumulated-uncounted list** gains: the viewer page re-pointed at v2 (findings 157/159/160 fixed in the viewer), host 0.2.32; `L-ods-editor-redownload-once` will happen again at the 0.2.32 install.

Spec: `specs/SPEC-M4-viewer-v2.md` **§9** (page re-pointed; E4b/E9) and **§10** (package, way back, Phase H criteria and readings -- pinned before any install or run). Previous handoff: `HANDOFF-2026-10-22c-…`.

## What happened

| when (CST, 10-23) | what | record |
| --- | --- | --- |
| 01:1x | §9.1-9.3 written first; `web/ods-viewer-app.js`'s one worker literal → `ods-viewer-v2`; `make ods-viewer-assets` (cp; dist's viewer page and shell were 0.2.29's); shell unit tests 57/57; `make -k test-e2-c-static` exit 0; `run_ods_viewer_e4b_e9.py --profile` (default v1, selftest 16/16) | `ffb6fe57` |
| 01:19-01:20 | **E4b PASS 2/2, E9 PASS** on the product page (reference: `aa576ce7`'s first full-corpus report, same wasm checked); no-refit red case reproduced (the 12 px) | §9.4, `bd3e1b5b`, `160-fix-phase-e/e4b-e9/` |
| 01:2x | host branch `host-0.2.32` in a scratch worktree, version only; package `80349a1a24cecb17` (35 files; editor's 25 byte-identical to `1b4d6a1f`'s; viewer page + 3 shell files + v2's six profile files); packager selftest 13/13; K0/Z0/H5-1 0 problems + 22/22 red cases; negative control on the live package: 22 problems; archived | §10.1, `a27255bc`, `findings/evidence/host-0.2.32/` |
| 01:3x | install script, way back (package only: one `rsync --delete` from the 0.2.29 archive), Phase H chain, runbook, release text draft; `ddev list`: litecore paused → the install script now refuses unless litecore runs (its pre-check re-run stopped on that line) | `a27255bc`, `be84f7e9` |

## Next, in order

1. **Ask the owner for a ddev slot** (fgp-nc was running at 01:34). In the slot: runbook `handoff/RUNBOOK-install-host-0.2.32.md` §0 (`ddev list`, wallet), owner's `ddev start` for litecore if paused, `bash findings/evidence/host-0.2.32/install-0.2.32.sh` (seconds; if the auto-mode classifier refuses it, say so at once with the one line), then `WINDOW_END='…' bash findings/evidence/host-0.2.32/chain-phase-h.sh` (~10 min: H1/H2/H3/H6, H4 = H-154c/H-154o/H-155 x2 browsers x3 + host-entry). Read per §10.3; any red → the way back (README), stop before H7.
2. The `h-viewer` step is the witness for SPEC-M3-production-ui §17.27's residual 1 (host Chrome under `--password-store=basic`): record it.
3. After H holds: tell the owner H7 (runbook §7; release text `handoff/RELEASE-TEXT-DRAFT-0.2.32.md` §6), append the results to the spec (§10.4) and the README, remove the scratch worktree (runbook §8).
4. Still open: H7 on 0.2.31 is superseded by H7 on 0.2.32; 158-B as its own work item (finding 158); finding 164's intra-open growth; the Phase H fixture clean-up on the instance (10-21 Next 2); finding 163 (UNLOCK 500s).

## Hazards

- `package_m3_engine.py`'s default `--app` is the LIVE app dir: always pass `--app`.
- The pre-link tools `run_ods_viewer_step1.py` and `run_ods_viewer_draft_smoke.py` now refuse (they retarget from v1's literal, which the page no longer has) -- intended (§9.2).
- Every ODS runner's default `--out` is still v1's counted directory: always pass `--out`.
- The four Chrome launchers outside `ChromeSession` still have no `--password-store=basic`.
- The scratch worktree `…/scratchpad/litecore-0.2.32` may vanish; nothing needs it (branch + archive).

## §34.4

- This stretch: because of execution **+0**, because of review **+0** (`--profile` on the E4b/E9 runner is an option, the judges unchanged -- 10-22b's precedent; the BUILD_ID re-pin is a binding). Running total since 10-14b: **46 / 27.**
- New, unreviewed: `findings/evidence/host-0.2.32/offline-package-check.py` (a one-off reader of check_m3_assets' own package scorer; its red cases are the existing 22 PACKAGE_CASES plus the live-package negative control), `chain-phase-h.sh` (0.2.29's chain with substitutions and two added steps), the install script's container guard (shown red on the real paused state).

---

## Addendum (01:50): the owner named the slot; 0.2.32 is installed and Phase H holds

**First line now:** (a) **installed: host 0.2.32** (`bffc7dc`, main) on package **`80349a1a24cecb17`** (viewer `ods-viewer-v2` `aa576ce7`) -- it replaces 0.2.31 as the uncounted daily candidate; (b) archived as above; (c) nothing counted; (d) unchanged from the first line, `L-ods-editor-redownload-once` realised by this install.

| when (CST) | what | record |
| --- | --- | --- |
| 01:39 | owner: 「A，我已停用和啟用了」 (fgp-nc stopped, litecore started) | -- |
| 01:40:12 | step 0: running set {litecore}; KWallet `b false` | `host-0.2.32/README.md` |
| 01:40:41-55 | `install-0.2.32.sh`: pre-checks held, `bffc7dc`, buildId `80349a1a24cecb17`, `litecore: 0.2.32`, both routes 401 | `install.txt` |
| 01:41-01:49 | `chain-phase-h.sh`: **VIEWER HOST HOLDS** (H1, H2 + control + red arm, H3, H6); Apache log: only `profiles/ods-viewer-v2/` served, no v1; **H4**: H-154c/o/H-155 PASS x2 browsers x3, HOST_ENTRY LANDS | spec §10.4, `phase-h/shakedown/2026-10-22T174116+0000.json` |
| -- | SPEC-M3-production-ui §17.27 residual 1 witnessed (login + cookie DAV under `--password-store=basic`) -- §17.29 | -- |

The scratch worktree is removed (branch `host-0.2.32` stays, merged into main).

**Next:** H7 is the owner's (runbook §7: `three-sheets-distinct.ods`; to see what changed, `upstream/functions.ods` and `upstream/fdo67682-2.ods`). Then the remaining open items of the first part's Next 4. §34.4 unchanged: **46 / 27**.

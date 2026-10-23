# Viewer v3 machine gates hold; next input is the owner's V3-SEE observation

## Entry point

The owner finished both manual builds. The v3 core built in 184 seconds; the SDK link exited 0. Codex then completed post-link verification, archiving, the targeted sweep, product-page E4b/E9 and its red case, E6, and three full-corpus sweeps. **The only pending Phase E item is the owner's control-visibility observation (V3-SEE).** It was requested asynchronously, but no answer has arrived. Do not count the agent's screenshot as the owner's answer.

Original task/constraints: `handoff/HANDOFF-2026-10-23b-to-codex-158b-dba-only.md`. Canonical gate: `specs/SPEC-M4-viewer-v3.md`, now through section 15, append-only. Machine evidence and replay commands: `findings/evidence/m4-ods/viewer-v3/phase-e/README.md`.

## State (the four shapes)

- **Installed:** unchanged host **0.2.32**, host main `bffc7dc`, engine package **80349a1a24cecb17**, editor e2-editor-v22 / f7a40bcc, viewer ods-viewer-v2 / aa576ce7. No ddev command was run in this work. The previous handoff left litecore stopped; do not infer today's running set from that old observation.
- **Built and archived, uncounted:** new **ods-viewer-v3 / ebb7e0cb…**, archive `wasm_sdk_probe/build/archive/ods-viewer-v3-ebb7e0cb-worker-9c85043a/`. Full identities in `findings/evidence/m4-ods/viewer-v3/post-link/identity.json`. Actual gzip **49,530,696 B**, headroom **2,898,104 B** below the 52,428,800 cap. Manifest has part-info + form-controls, bits **63539**. No host 0.2.33 package/worktree/branch was prepared yet: the pinned all-pass step waits for V3-SEE.
- **Bound/counted:** nothing new. Nominal shipped host remains **0.2.26**; full count chain K stays batched. Do not initiate or re-pin K.
- **Accumulated uncounted:** host 0.2.29-0.2.32 as in the original handoff, plus this separate v3 engine candidate (not installed).

Section 34.4: this work **+0 / +0** (because of execution / because of review); cumulative **46 / 27**. No existing judge was changed. New K3/V3-NR tools implement newly pinned criteria; the runner changes only add the v3 profile name. Do not grow a checker-review loop.

## What changed and what passed

The shared LibreOffice source has a tenth patch, `wasm-dbaccess-core-with-explicit-dbconnectivity`: stripped builds with explicit DB connectivity add only dba/dbahsql; database UI and reportdesign stay out. All ten patches reverse-check. Other source modifications/untracked research files were preserved. Core build remains `wasm-lite/build-ods-viewer-v2`; do not rebuild gate0 or headless-probe. K3 passes: 791 constructors, all 8 dba constructors including RowSet; no dbu/sdbt/rpt/rptui constructors; existing bridge/forms/scaddins/link inputs hold.

Correction to the original handoff: dbaxml's source component has **6**, not 0, constructors. They are absent from the built core. This stays record-only; the pinned K3-b source set was not changed.

The independent v3 Makefile rule/builder uses v2's exact engine ABI/defines/worker, on the new core. Engine src is unchanged from 2430916d, the revision recorded for aa576ce7. Base 21bec646… / metadata 43da6a24…, E8-prime controls pass; compared with a6390eef's old DB-connectivity base, only services.rdb changes, adding dba's component. The old 1,643-file frozen set is unchanged. The current editor/viewer and all manifest resource targets were also backed up and verified under `build/archive/before-ods-viewer-v3-20261023T160805Z/`.

`web/ods-viewer-app.js` now names v3 (source only, commit 99859cd4); dist's page and the installed package have not been staged/repacked. E4b/E9 on that product source pass, and no-refit reproduces E4b red. Static tests pass; viewer unit tests 57/57. New V3-NR reader: `wasm_sdk_probe/tools/check_ods_viewer_v3_nonregression.py`; it uses staged path/indexed case URLs because 306 corpus entries have only 304 distinct hashes, and calls the existing E2 judge.

Full sweeps (all UTC report starts on 2026-10-23, local date 10-24): **163018Z, 164128Z, 164203Z**. Each: **303 opens / 3 encrypted refusals**, all 298 old opens retained, all five form-control files pass E2/E3/E4a, tdf138507 opens. Each has 470 text reads / **0 unconfirmed**. E3 fails only the existing user-defined-function.ods / L-no-basic-udf; raw runner exits are 1 and preserved. All other machine criteria pass. V2-160-D passes all three, actual redispatches **1 / 0 / 0**, with the run-1 retry exercised and confirmed. N=3 is complete; do not run extra sweeps.

E6 B=0, boots/reopen shape pass. Reopen series remains record-only; finding 164 / L-E6-leak-sbrk were not withdrawn. Highest stage sbrk across all full sweeps: **553,844,736 B**, below 939,524,096.

## Required owner input: V3-SEE

On this host, open **http://127.0.0.1:8794/ods-viewer.html?diagnostics=1**. It automatically opens **tdf134161.ods** (101 controls). A green banner identifies **ods-viewer-v3 / ebb7e0cb**. Ask whether the controls are visible, for example the small box in the yellow cell. Record the exact answer, the page identity and time. The user previously did not see one async question, so repeat the actual question plainly in a final reply if necessary.

The server is alive and was checked again at the end. Its PID/root, source/served hashes and exact fixture are in `findings/evidence/m4-ods/viewer-v3/phase-e/human-preview/preview.json` and `wasm_sdk_probe/build/ods/viewer-v3-human/server.json`. This is a mirror of the product page, with only the HTML's identity banner and local load-only fixture host added; no dist mutation or ddev. `page-state.json` and preview.png show the agent's preflight, **not** a human confirmation. Keep the server available for the owner. If it has died, serve that existing mirror with `web/serve.py --port 8794 --root <recorded root>` after checking the port, without changing any bytes.

If the owner reports a rendering problem, stop shipment and read that observation before choosing another change. If they confirm visibility, append their words to the spec/evidence/finding 158; this satisfies the last pending v3 criterion and permits the next step.

## After V3-SEE: prepare host 0.2.33, then ask for a ddev slot

Follow the original handoff steps 7 and `findings/evidence/host-0.2.32/` as the template. Read applicable host repo instructions before editing it. The live app is `/home/jiajun/Projects/Nextcloud_Apps/litecore`; it was clean on main bffc7dc when read. Build the package in an isolated worktree, **always pass `package_m3_engine.py --app <worktree>`** (the default is the live directory). Stage viewer assets only after reading the Makefile's cp-only target; do not relink an engine. Create the version-only host commit with the agreed Codex trailer. Derive the actual new package identity and compare the editor closure against 0.2.32's archive.

Complete offline gates/red cases, archive, rollback recipe, install pre-check script, Phase H chain, runbook and release-text draft before asking to use ddev. Re-pin package bindings only to the measured new buildId. Do not mutate counted evidence or default runner outputs. Install and H1-H7 only in an owner-named slot; short install commands are the agent's job, core/link compilation remains the owner's. K remains batched even though the engine changed.

Reply in Taiwan Traditional Chinese; handoff/evidence/upstream/commit text stays English. Every new commit in this work uses `Co-Authored-By: Codex <noreply@openai.com>` at the owner's request. Never sudo/su/doas. Keep commits cohesive. Current worktree should be clean after this handoff commit.

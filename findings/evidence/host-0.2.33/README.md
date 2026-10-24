# Host 0.2.33: v3 viewer package and installation evidence

Spec: `specs/SPEC-M4-viewer-v3.md` section 16. V3-SEE was confirmed by the owner on 2026-10-24 (exact words in `m4-ods/viewer-v3/phase-e/human-preview/owner-confirmation.md`).

## Candidate prepared before installation

- Host branch `host-0.2.33`, commit **4f7f870** on **bffc7dc**: only `appinfo/info.xml` changes, 0.2.32 -> 0.2.33. The isolated worktree is recorded in `release.json`; the live main remains untouched at preparation time.
- `make ods-viewer-assets` copied only the viewer source module to dist (`stage-assets.txt`), compiling/relinking nothing. The packager was invoked with an explicit isolated `--app`; see `package.txt`.
- Schema `litecore-engine/3`, buildId **a67beefefebe57d6**: **35** decoded files, **345,292,248 B**, gzip **118,065,155 B**, zstd **85,087,410 B**. Page table: editor e2-editor-v22 / f7a40bcc, viewer ods-viewer-v3 / ebb7e0cb.
- Against package 80349a1a24cecb17: **28 identical**, only `ods-viewer-app.js` changed among common paths, six v2 profile paths removed and six v3 paths added (`manifest-diff.json`). The entire derived editor closure (**22 files**, including coding/hash metadata) is identical. No editor behavior change is claimed.
- Largest gzip: viewer wasm **49,530,696 B** (cap 52,428,800); largest zstd: **37,177,361 B** (cap 45,000,000). Existing frame-window checks pass.
- Archive: `wasm_sdk_probe/build/archive/host-0.2.33-engine-a67beefefebe57d6/`. **71 files** copied, compared to the isolated package, then checked with `archive.sha256`; output `archive-verification.txt`. Only ATTRIBUTION.md is extra in the archive.

## Offline checks

- Packager self-test **13/13**.
- `offline-package-check.py <isolated-worktree>`: K0/Z0/H5-1 **0 problems**, **22/22** package red cases red.
- Same script on live 0.2.32: exit **1**, **16** problems against the new closure/binding (`offline-package-check-control-live-0.2.32.txt`). The live package itself was not modified.
- `check_m3_assets.BUILD_ID` now binds the measured new package. This is a package binding, not a judge change. Section 34.4 +0 / +0, cumulative 46 / 27.

## Scripts and functional rollback

`install-0.2.33.sh` validates the recorded live/candidate commits and parent, clean main, old live engine against the 0.2.32 archive, new archive checksums, an open owner-named window, and only litecore running **before** changing anything. Then fast-forward merge, copy the archived package, occ upgrade and route smoke checks. `--preflight-only` stops before mutation.

`chain-phase-h.sh`: unchanged H1/H2/H3/H6 viewer criteria, H4's two-browser three-round H-154c/H-154o/H-155 and host-entry. Each step checks the time window, ddev running set and wallet. The new chain captures each return code before timestamping and stops on nonzero; it does not change any criterion. Raw H reports use the existing shakedown namespace with unique timestamps, H155 writes into this directory.

`script-guards.json`: synthetic ddev-list fixtures verify that stopped litecore and another running project refuse; a valid preflight performs no live mutation. The closed-window Phase H control exits 3. All three scripts pass `bash -n`. **These controls run no real ddev command or Phase H.** Actual ddev observations are recorded separately.

If a Phase H criterion is red, read its raw data before taking the specified rollback: `bash findings/evidence/host-0.2.33/rollback-package.sh`. This restores only the engine from **host-0.2.32-engine-80349a1a24cecb17**; leave the host version at 0.2.33, with no reset/downgrade/occ. Both archives remain available.

Installation/Phase H results will be appended after execution. H7 remains the owner's Files-path observation; the completed mirror V3-SEE does not replace it. Full count chain K remains batched and nominal shipped host remains 0.2.26.

## Installed and machine Phase H holds, 2026-10-24 (supersedes preparation status)

The owner requested autonomous execution while asleep, a handoff/stop at a work-unit boundary, and recording hard-to-judge results. `ddev-before-slot.json` showed no running project; the agent started only litecore and used the recorded 30-minute window, 01:13:48 to 01:43 Asia/Taipei (`slot.json`, spec section 18).

- Install **01:14:31-01:14:44**: all real pre-checks held, main fast-forwarded to 4f7f870, live engine became a67beefefebe57d6, occ upgraded litecore to 0.2.33, maintenance disabled, both unauthenticated routes returned 401 (`install.txt`).
- Phase H **01:15:14-01:23:42**, every step exit 0 (`chain.log`, `guard.log`, `phase-h-summary.json`):
  - **H1/H2/H3/H6:** VIEWER HOST HOLDS, no problems. Raw report `findings/evidence/m4-ods/phase-h/shakedown/2026-10-23T171515+0000.json`; includes the ODT lock positive control and lock-taking-viewer red arm.
  - The actual Apache window has **12 v3 profile requests, all 200**, no v2 profile request (`access-log-viewer-engine.txt`).
  - **H4 dialogs:** Chrome and Firefox, three rounds each, H-154c/H-154o/H-155 all pass with --require-h155 (`h155/`, `judge-h155.txt`).
  - **H4 host entry:** HOST_ENTRY LANDS, Chrome/Firefox open-save and conflict 3/3 each, both Chrome broken-host controls 1/1, no problems. Raw report `findings/evidence/m3-host-entry/shakedown/2026-10-23T171807Z.json`.
  - **H5:** the prepared package's offline gates above hold; installed package matches the archive (`post-install-identity.txt`).
- Result: **0.2.33 / a67beefefebe57d6 replaces 0.2.32 as the installed uncounted candidate**. No rollback was needed. No unresolved judgment question was encountered; no existing acceptance tool was changed.

**H7 is pending**, because the owner is asleep: later open Files -> `M4 phase-h/M4 檢視 測試 plain.ods` (fileId 24674), verify Alpha/Beta/Gamma and switch tabs. The fixture folder is preserved for that observation. It is a later manual entry point, not an immediate request. K remains batched; nominal shipped host stays 0.2.26.

## Stop/cleanup completed

At 01:25 the agent stopped its litecore project. `ddev-after-stop.json` exactly matches every starting project status: litecore stopped, nc-bridge paused, all others stopped. The agent's 8794 preview server was terminated only after matching its recorded PID/command/root; the port is closed, the mirror files remain. The isolated worktree was removed only after verifying it was clean and its package matched the archive; main and branch host-0.2.33 remain at 4f7f870. `cleanup.json` records all of this. Both engine archives remain intact.

Two routine orchestration corrections had no product impact: an initial root-repo git command was issued from the host cwd and failed without changes, then was rerun from the correct repo before installation; a post-run path reader was corrected to read the host-entry log's JSON record rather than a plain path. Neither changed a runner, criterion, report or verdict. Section 34.4 remains +0 / +0, cumulative 46 / 27.

## Owner H7 holds, 2026-10-25 (supersedes pending H7)

In a new slot explicitly requested after the owner freed the shared ddev environment, the agent started only litecore. The current installed version, manifest and retained ODS were read from the container and matched the candidate and prior machine H2/H3 fixture (`h7-2026-10-25/container-identity.json`).

The owner opened the identified Files-path test and replied **「三個工作表都能顯示」** ("All three worksheets can be displayed."). **H7 holds**; exact words, identity and the existing machine half are recorded in `h7-2026-10-25/owner-confirmation.md`. The browser was not specified. This is distinct from V3-SEE; machine Phase H was not repeated. `phase-h-summary.json` remains the historical 2026-10-24 machine-run record; `release.json` now points to the completed H7.

At **02:55:46 Asia/Taipei**, the agent had stopped its litecore project again, exit 0. All project states exactly match this slot's starting snapshot: litecore stopped, fgp-nc and nc-bridge paused, all others stopped. See `h7-2026-10-25/cleanup.json` and its raw snapshots. The fixture folder and installed candidate are preserved.

**All candidate Phase H clauses now hold; 0.2.33 / a67beefefebe57d6 remains installed and uncounted.** K remains batched, not run or re-pinned, and nominal shipped host remains 0.2.26. No criterion/judge/binding changed: section 34.4 **+0 / +0**, cumulative **46 / 27**.

## Later autonomous editor count preparation, 2026-10-25

After H7, the owner requested autonomous continuation, suggested Xvfb, and asked to stop at required human verification. `count-preparation-2026-10-25/README.md` records the resulting work: the already prescribed v22 modal census repair, with a committed old-runner witness, red-first focused tests (5/5 after repair), 158/158 existing red cases, and clean actual Vrw/Vro runs in both browsers. This judge repair adds section 34.4 **execution +1 / review +0**, cumulative **47 / 27**; product and package remain unchanged.

Native X11 typing on a headed Chrome under Xvfb succeeded in **3/3** actual Files-path rounds after Insert and Cancel, with server-saved text verified. The inherited **editor F3-hand owner report remains pending**, distinct from completed ODS H7/V3-SEE. A dedicated manual fixture and runbook are ready. No new K pins, BINDING or chain were applied; K remains unrun and the candidate uncounted.

The agent stopped its litecore project at **03:24:15 Asia/Taipei**. All ddev project states match the new slot's start; see `count-preparation-2026-10-25/cleanup.json`. The evidence separately records the existing runner's lock-table clearing and does not claim database row equality. Host source is clean at 4f7f870; both archives and the retained manual fixtures remain.

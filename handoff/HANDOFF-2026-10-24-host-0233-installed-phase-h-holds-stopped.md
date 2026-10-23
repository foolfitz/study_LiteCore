# Host 0.2.33 installed, machine Phase H holds, services restored to stopped

## Stop instruction and next entry point

The owner said they were going to sleep, authorized autonomous execution, asked for a handoff and stop at a work-unit boundary, and asked that hard-to-judge issues be recorded. That work unit is complete. **Stop here. Do not start another sweep, core build, count chain or ddev session without a new user instruction.**

The only remaining human acceptance item is **H7**, later: the owner opens an ODS from Nextcloud Files. This is distinct from V3-SEE, which the owner already confirmed. No unresolved judgment question was encountered. K remains batched and was not started/re-pinned.

Canonical spec: `specs/SPEC-M4-viewer-v3.md` through section 19 (append-only). Deployment evidence/status: `findings/evidence/host-0.2.33/README.md`, `phase-h-summary.json`, `release.json`, `cleanup.json`. Prior handoff `HANDOFF-2026-10-24-viewer-v3-machine-gates-hold-awaiting-visibility.md` is historical: its pending V3-SEE and not-installed statuses are superseded.

## State (four shapes)

- **Installed:** host **0.2.33**, main **4f7f870**, package **a67beefefebe57d6**, editor e2-editor-v22 / f7a40bcc, viewer **ods-viewer-v3 / ebb7e0cb**. This replaces 0.2.32 as the installed uncounted candidate. Only the host version changed; no route/controller/Files-action code changed.
- **Built and archived, uncounted:** `wasm_sdk_probe/build/archive/host-0.2.33-engine-a67beefefebe57d6/` (71 package files verified), and `build/archive/ods-viewer-v3-ebb7e0cb-worker-9c85043a/`. The 0.2.32 engine archive **80349a1a24cecb17** remains the rollback. All old profiles stay preserved. The isolated 0.2.33 worktree was removed only after verifying clean Git status and exact package/archive equality; its branch remains at 4f7f870, same as main.
- **Bound/counted:** nothing new. Nominal shipped host remains **0.2.26**; do not interpret machine H as the full count chain K.
- **Accumulated uncounted:** host 0.2.29-0.2.33 (previous viewer entry/page/host fixes, then the v3 form-control support). Keep K batched until the owner explicitly schedules it.

Section 34.4: this work **+0 / +0** (because of execution / because of review), cumulative **46 / 27**. New criterion readers and package binding changes did not alter existing acceptance judges. No extra review/measurement loop is pending.

## What the owner confirmed and what passed

V3-SEE: identified local mirror, tdf134161.ods, v3/ebb7e0cb. Owner's exact words: 「綠色橫幅 OK」「黃色格子裡的小方框 OK」. `findings/evidence/m4-ods/viewer-v3/phase-e/human-preview/owner-confirmation.md` records the words, translation and identity. Do not request that test again.

The v3 source/core work, K3, post-link checks, E8-prime, targeted sweep, E4b/E9/red case, E6 and full corpus x3 all hold with the existing Basic UDF limitation. Every sweep: **303 opens / 3 encrypted refusals**, five form-control cases pass E2/E3/E4a, **298/298** prior v2 opens preserved, **470/0** text reads/unconfirmed. V2-160-D actual redispatches **1/0/0**, all matched and confirmed. Do not run a fourth sweep. Finding 164 / L-E6-leak-sbrk and L-no-basic-udf remain registered.

Package a67beefefebe57d6: schema 3, 35 files, 345,292,248 B decoded, 118,065,155 B gzip, 85,087,410 B zstd. Largest viewer wasm: 49,530,696 B gzip / 37,177,361 B zstd, inside caps. Entire derived editor closure **22 files** is identical to 0.2.32; 28 package paths identical, common-path change only ods-viewer-app.js, six v2 paths replaced by six v3 paths. Offline K0/Z0/H5-1 clean, package red cases **22/22**, packager selftest **13/13**, old live-package negative control correctly red (16 problems).

## Actual autonomous slot and Phase H

Initial `ddev list`: no running project; litecore stopped, nc-bridge paused, all other projects stopped. The sleeping owner's autonomous instruction was applied to a bounded idle slot, **01:13:48-01:43 Asia/Taipei**, recorded before installation (`slot.json`, spec section 18). Only litecore was started; no other project was stopped.

- **Install 01:14:31-01:14:44:** real pre-checks hold, fast-forward to 4f7f870, archived package copied, occ upgrade to 0.2.33 successful, maintenance off, both unauthenticated routes 401.
- **Phase H 01:15:14-01:23:42:** every chain step exit 0, no guard refusal. `h-viewer.log`: **VIEWER HOST HOLDS**, no problems, H1/H2/H3/H6 including lock positive/red controls. Raw `findings/evidence/m4-ods/phase-h/shakedown/2026-10-23T171515+0000.json`.
- Actual Apache window: **12 v3 profile requests, all 200**, no v2 request (`access-log-viewer-engine.txt`).
- H4: Chrome and Firefox, three rounds each, H-154c/H-154o/H-155 pass with --require-h155. Host entry **LANDS**, Chrome/Firefox open-save and conflict 3/3 each; two Chrome broken-host controls 1/1 each, no problems. Raw `findings/evidence/m3-host-entry/shakedown/2026-10-23T171807Z.json`.
- H5: offline package checks above, live engine compared to archive after installation. No rollback needed.

Routine orchestration corrections (recorded in the evidence README) did not change any product/judge/report: a root Git command initially ran in the host cwd and failed, then was rerun from the correct repo before install; the post-run reader was corrected to parse the host-entry log's JSON path record. There is no remaining decision to make about either.

## Cleanup and service state at handoff

**litecore is stopped again**, retaining 0.2.33 and its data. Every project's status exactly matches the starting snapshot (`ddev-after-stop.json` vs `ddev-before-slot.json`): nc-bridge still paused, all others stopped. The agent's 8794 preview server was stopped after matching its recorded PID/command/root; its port is closed. The mirror files remain under `wasm_sdk_probe/build/ods/viewer-v3-human/root/` for reproducibility. Do not present the old 8794 URL as currently serving.

The two engine archives, v3 profile archive, source patches and evidence remain. The live app repo and study repo are clean. The temporary host worktree is gone; `release.json`'s worktree path is historical. For a read-only offline check later, use the live app directory with `findings/evidence/host-0.2.33/offline-package-check.py`, not the removed worktree.

## Later H7 (owner's step, in a new slot)

Once the owner wants to resume, start litecore only in their next authorized ddev slot (check the current running set; do not recycle the expired overnight window). In Files as the test admin, open **M4 phase-h/M4 檢視 測試 plain.ods** (fileId **24674**): Alpha/Beta/Gamma tabs, switching shows the sheets. That fixture folder is preserved specifically for H7. No immediate manual action was requested while the owner slept.

Record the owner's exact words and identity in the spec/evidence; H7 is not already satisfied by V3-SEE or by the automated host runner. After H7, the candidate still remains uncounted until K is explicitly scheduled. Do not proactively launch K or repeat Phase E/H just for reassurance. Clean up the retained test folder only within the owner's authorized scope.

Runbook: `handoff/RUNBOOK-install-host-0.2.33.md`; release draft: `handoff/RELEASE-TEXT-DRAFT-0.2.33.md`. Functional rollback, if later needed: `findings/evidence/host-0.2.33/rollback-package.sh` restores engine 80349a1a24cecb17, leaving code version 0.2.33 (no reset/downgrade/occ). Do not run it without a reason/new authorization.

Standing rules: Taiwan Traditional Chinese replies; handoff/evidence/upstream/commits English, exact owner quotations preserved as data. No sudo/su/doas. Compilation make goes to the owner unless explicitly asked otherwise. All new commits use the owner-approved `Co-Authored-By: Codex <noreply@openai.com>`. Keep cohesive commits. This session ends after committing this handoff.

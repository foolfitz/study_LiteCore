# Release draft: host 0.2.33, read-only ODS form controls (uncounted candidate)

This draft describes the final candidate, with evidence. Installation/Phase H status is recorded in `findings/evidence/host-0.2.33/README.md`; full count chain K remains batched, nominal shipped host 0.2.26.

Compared with 0.2.32, the read-only spreadsheet viewer moves from ods-viewer-v2 / aa576ce7 to **ods-viewer-v3 / ebb7e0cb**. Files containing form controls can now open instead of being refused with FORM_CONTROLS_UNSUPPORTED. The five corpus examples pass opening, visible-sheet tiles and text checks in three full sweeps. The owner confirmed the visible control in tdf134161.ods on the identified mirror. This establishes viewing, not editing or interacting with form controls. Evidence: `findings/evidence/m4-ods/viewer-v3/phase-e/README.md` and the owner's confirmation there.

Every one of v2's 298 actually opened corpus entries still passes opening conditions in all three v3 sweeps, including tdf138507.ods. Each sweep opens 303 files and rejects three encrypted files, with no newly introduced failure. The existing Basic UDF limitation remains (user-defined-function.ods); volatile-sheet comparison and the registered E6 leak limitation are unchanged.

The editor's entire derived page closure (22 files) is byte-identical to 0.2.32, including its engine and shared resources. Host code changes only the version number. The package is schema litecore-engine/3, **a67beefefebe57d6**, 35 files. The viewer wasm is 49,530,696 B gzip / 37,177,361 B zstd, below both existing caps. Evidence: `findings/evidence/host-0.2.33/manifest-diff.json`, `release.json`, offline checks and archive verification.

A new package buildId gives engine files new URLs, so a browser will fetch that version on its next use; the editor bytes themselves are unchanged. The viewer remains read-only and accepts .ods only; encrypted ODS files are refused. The existing 157/159/160 fixes carry over.

Mirror acceptance and offline package checks do not establish the new package's Nextcloud behavior. Phase H and the owner's later Files-path H7 must be reported separately. The rollback is the archived 0.2.32 engine package, while retaining the 0.2.33 host version.

## Installation status, appended 2026-10-24

0.2.33 was installed at 01:14 Asia/Taipei under the owner's sleeping/autonomous instruction. Machine H1-H6 pass, including the viewer host's read-only/headers/tab checks, Chrome/Firefox x3 dialog regressions, host-entry open/save/conflict, and the offline package gates. Apache records the v3 engine files, all 200. Evidence: `findings/evidence/host-0.2.33/README.md` and `phase-h-summary.json`.

The installed version is an **uncounted candidate**, with the owner's Files-path **H7 still pending**. Full K remains batched. The agent stopped litecore after testing, restoring the initial stopped state; it retains the installed package and data and is available on the next ddev start. No immediate manual task is requested while the owner sleeps.

## Owner Files-path acceptance, appended 2026-10-25

This supersedes the pending-H7 status above. On the identified installed 0.2.33 candidate, the owner opened `M4 phase-h/M4 檢視 測試 plain.ods` from Files and confirmed **「三個工作表都能顯示」** ("All three worksheets can be displayed."). H7 holds, with the same candidate/fixture's existing machine H2/H3; evidence: `findings/evidence/host-0.2.33/h7-2026-10-25/owner-confirmation.md`. All candidate Phase H clauses now hold.

The agent stopped litecore after this slot and verified that every project state matched the starting snapshot. Host 0.2.33 and its data remain installed. The candidate is still **uncounted**: K has not been run or re-pinned, and nominal shipped host remains 0.2.26.

## Inherited editor acceptance still pending, appended 2026-10-25

The completed ODS H7 does not close v22's separate F3-hand editor requirement. Autonomous follow-up verified native X11 keyboard typing after Markdown Insert and Cancel under Xvfb in 3/3 rounds, including server-saved content, but the owner's normal Chrome desktop report is still absent. Evidence and the prepared manual fixture are in `findings/evidence/host-0.2.33/count-preparation-2026-10-25/`; the one-minute procedure is `RUNBOOK-host-0.2.33-f3-hand.md`. This draft makes no completed F3-hand or shippable-release claim. K remains batched/unrun.

# Owner editor acceptance slot opened, 2026-10-25

The owner said **「好我們驗收吧」** ("All right, let's do the acceptance test."). This resumes `handoff/RUNBOOK-host-0.2.33-f3-hand.md`; the earlier autonomous preparation slot is closed and is not reused as authorization.

## Fresh slot and readiness

At **08:53:37 Asia/Taipei**, a fresh ddev snapshot showed no running project: litecore and the other projects were stopped, except fgp-nc and nc-bridge paused. `slot.json` records the new instruction and the manual-acceptance boundary before starting only litecore. `ddev start` completed with exit 0 and "Successfully started litecore"; `ddev-after-start.json` shows only litecore changed to running.

At **08:54:19**, read-only container access verified (`container-identity.json`):

- Host **0.2.33 / 4f7f870**, package **a67beefefebe57d6**, maintenance **false**; manifest hash and full editor entry match the prepared candidate.
- File **LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt**, fileId **24920**, **1,518 bytes**, sha256 **3d17d51266216f6e282a6785e902f19460cbd59ccfdbb4c09579624147291297**. The complete identity matches the retained preparation record.
- An unauthenticated HTML request to Files reaches the login page with **200** (`files-entry.txt`). No browser or test runner was used to replace the owner's test.

## Pending owner report

The owner has been given the actual Files entry and the dedicated fixture. Requested observations, in the owner's normal Chrome:

1. After Markdown **Insert**, type **A** on the real keyboard and confirm it appears in the document.
2. After **Cancel**, type **B** and confirm it appears in the document.
3. The carried Home/End hand check: Ctrl+Home then Backspace, Ctrl+End then Delete; neither should delete at the respective document boundary.
4. The carried appearance check: dialog centred when open, absent when closed.

The first two observations are existing **F3-hand**; the latter two are separately recorded owner follow-ups, not new F3 criteria. No owner outcome has been recorded yet. ODS H7 and V3-SEE already hold and were not requested again. The completed Xvfb diagnostic remains distinct from this owner observation.

litecore remains running for this manual slot. Stop the agent-started service after the observation or cancellation unless the owner asks to retain it, and record all project states. No lock-table clearing, fixture overwrite, product change, compiling make, new count binding, K chain or reassurance rerun was performed. Section 34.4 **+0 / +0**, cumulative **47 / 27**.

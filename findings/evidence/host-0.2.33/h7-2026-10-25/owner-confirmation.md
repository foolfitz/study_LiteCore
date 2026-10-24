# H7 owner confirmation, host 0.2.33, 2026-10-25

The owner replied directly to the request to open the identified ODS from Nextcloud Files and switch Alpha / Beta / Gamma:

> 三個工作表都能顯示

Translation: "All three worksheets can be displayed."

## Observation identity

- Entry provided to the owner: **https://litecore.ddev.site:8443/index.php/apps/files/**, using the existing test **admin**, then **M4 phase-h/M4 檢視 測試 plain.ods**.
- File: **24674**, **7,537 bytes**, sha256 **0402e52724cb5bbd3046461a5fb1c40b9431b33f20834136a835a68f3123e750**.
- Installed host **0.2.33**, source **4f7f870bb44e703e101148f143f174c7facee5c9**, package **a67beefefebe57d6**.
- Viewer **ods-viewer-v3**, wasm **ebb7e0cb9f886185c0b0e53eb68f137eb9c5df07af2e83cdb09255c07477d82a**.
- The current container configuration, manifest and retained file identity were read at **02:52:02 Asia/Taipei**, before the owner's report: `container-identity.json`. The fixture name/id/size/hash match the existing machine report.
- Browser was not specified by the owner and is not inferred.

## Existing criterion and result

**H7 holds.** The human half is the owner's exact report above. The machine half is the existing H2/H3 on the same candidate and fixture in `findings/evidence/m4-ods/phase-h/shakedown/2026-10-23T171515+0000.json`, including tab read-back. This follows `specs/SPEC-M4-viewer-v2.md` section 10.5 and the current v3 H7 runbook; no new browser run was needed to replace the human observation.

This is the installed host's Files-path acceptance, distinct from the already completed mirror V3-SEE and the previous 0.2.32 H7. It supersedes the pending-H7 status in this directory's readiness README and spec section 21. Machine H1-H6 plus this H7 now hold for host 0.2.33.

The candidate remains **uncounted**. K is still batched and requires a separate explicit owner schedule; nominal shipped host remains **0.2.26**. Section 34.4 **+0 / +0**, cumulative **46 / 27**. No acceptance criterion, judge or package binding changed.

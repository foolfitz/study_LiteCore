# Release draft: host 0.2.33, read-only ODS form controls (uncounted candidate)

This draft describes the final candidate, with evidence. Installation/Phase H status is recorded in `findings/evidence/host-0.2.33/README.md`; full count chain K remains batched, nominal shipped host 0.2.26.

Compared with 0.2.32, the read-only spreadsheet viewer moves from ods-viewer-v2 / aa576ce7 to **ods-viewer-v3 / ebb7e0cb**. Files containing form controls can now open instead of being refused with FORM_CONTROLS_UNSUPPORTED. The five corpus examples pass opening, visible-sheet tiles and text checks in three full sweeps. The owner confirmed the visible control in tdf134161.ods on the identified mirror. This establishes viewing, not editing or interacting with form controls. Evidence: `findings/evidence/m4-ods/viewer-v3/phase-e/README.md` and the owner's confirmation there.

Every one of v2's 298 actually opened corpus entries still passes opening conditions in all three v3 sweeps, including tdf138507.ods. Each sweep opens 303 files and rejects three encrypted files, with no newly introduced failure. The existing Basic UDF limitation remains (user-defined-function.ods); volatile-sheet comparison and the registered E6 leak limitation are unchanged.

The editor's entire derived page closure (22 files) is byte-identical to 0.2.32, including its engine and shared resources. Host code changes only the version number. The package is schema litecore-engine/3, **a67beefefebe57d6**, 35 files. The viewer wasm is 49,530,696 B gzip / 37,177,361 B zstd, below both existing caps. Evidence: `findings/evidence/host-0.2.33/manifest-diff.json`, `release.json`, offline checks and archive verification.

A new package buildId gives engine files new URLs, so a browser will fetch that version on its next use; the editor bytes themselves are unchanged. The viewer remains read-only and accepts .ods only; encrypted ODS files are refused. The existing 157/159/160 fixes carry over.

Mirror acceptance and offline package checks do not establish the new package's Nextcloud behavior. Phase H and the owner's later Files-path H7 must be reported separately. The rollback is the archived 0.2.32 engine package, while retaining the 0.2.33 host version.

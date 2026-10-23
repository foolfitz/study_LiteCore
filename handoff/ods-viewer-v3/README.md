# Viewer v3: owner-run core build

Spec: `specs/SPEC-M4-viewer-v3.md`. This is finding 158-B, option A: dba + dbahsql only, on the existing `wasm-lite/build-ods-viewer-v2` core. The shared source patch is already applied and captured in the patch inventory. All ten reverse-checks and K-1 passed. K3's pre-build red controls are committed under `findings/evidence/m4-ods/viewer-v3/core/`.

From `/home/jiajun/LibreOffice/study_LiteCore`, run this short command:

```bash
bash handoff/ods-viewer-v3/build-core.sh --make-only
```

Estimate: **15-40 minutes**, default `JOBS=12`. This compiles dba/dbahsql and relinks the core; it does not link the SDK viewer. It runs no autogen and does not touch ddev. Avoid overlapping another build or a timing measurement.

Each invocation creates a unique `findings/evidence/m4-ods/viewer-v3/core/runs/<id>/` directory. The full make log is `wasm-lite/build-ods-viewer-v2/build-v3-<id>.log`; `build-v3.log` points to the latest. A failed build also saves its last 200 lines. Timing is recorded per run and appended to the core evidence's `timing.txt`.

Report the final DONE/STOP line and run path. Codex can read K-1, K3, sizes, hashes and logs directly; there is no need to paste long output. A fresh session should read this file, the spec, and the initial handoff `handoff/HANDOFF-2026-10-23b-to-codex-158b-dba-only.md`.

Stop on a failure inside dba/dbahsql (F3-1), a red K3, or a projected viewer gzip above 52,428,800 B (F3-2). Do not start a patch chain. A green K3 permits the next agent to prepare the **separate** `ods-viewer-v3` link, read the E8-prime base-pack diff, verify/archive the current profiles and hand over another short link command. No v3 SDK profile exists yet, and no Phase E result is established for v3.

Installed state remains host 0.2.32, package `80349a1a24cecb17`, viewer `ods-viewer-v2` (`aa576ce7…`), editor `e2-editor-v22`. ddev was stopped at the handoff and has not been started for this preparation. The full count chain K stays batched; nominal shipped host remains 0.2.26. No ddev work without an owner-named slot.

Section 34.4: this preparation **+0 / +0** (because of execution / because of review), cumulative **46 / 27**. New checker construction and red controls are not modifications of existing counted machinery.

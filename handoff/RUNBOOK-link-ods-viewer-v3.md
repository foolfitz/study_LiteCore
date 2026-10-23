# First link of ods-viewer-v3 (the owner's step)

Spec: `specs/SPEC-M4-viewer-v3.md`, pinned before the source patch and core build. The owner built the core successfully in **184 seconds** (`core/runs/20261023T235528-ctpzQR/`); K-1 and K3 pass. Core gzip 49,951,424 B; projected viewer gzip **49,532,187 B**, cap 52,428,800 B. The actual viewer is measured at this link.

## What is linked

- Independent identity `ods-viewer-v3`, its own `build/ods/viewer-v3/` and `dist/profiles/ods-viewer-v3/`.
- Core `wasm-lite/build-ods-viewer-v2` with dba/dbahsql, including RowSet, without dbu/sdbt/reportdesign. Engine sources are unchanged from the aa576ce7 viewer's recorded source (`2430916d`); the define remains `OXSDK_ODS_VIEWER_V2`, with finding 160's retry of undispatched SelectAll.
- The v2 export list, worker pin `9c85043a…`, and link flags. A distinct v3 builder/profile/base stem. Manifest must declare `form-controls`, capability bits **63539**.
- Base `21bec646…` (39,934,615 B, 1,488 files), classified from this core, dropping exactly one `35-lang-normalize.conf`. Positive control reproduces 9901e9be. Against v1: 0 added, 0 removed, 9 changed; against a6390eef's diagnostic base: only services.rdb differs, adding the dba component. The full per-file reading is in the spec and pre-link evidence. CJK/fallback packs retain their v1 paths and bytes.

Pre-link evidence: `findings/evidence/m4-ods/viewer-v3/pre-link/README.md`. Existing profiles and manifest-referenced resources were copied and SHA256-verified into the archive recorded by `archive-before-link.json`. `frozen-set-before.sha256` records the old profiles and archives; every listed file must remain unchanged.

## Run (a few minutes)

From `/home/jiajun/LibreOffice/study_LiteCore`:

```bash
bash handoff/ods-viewer-v3/link.sh
```

The script compiles the SDK's three objects and links only this new profile. It does not rebuild the LibreOffice core. One fresh log per run, with `wasm_sdk_probe/build/link-ods-viewer-v3.log` pointing to the latest. The closing make line prints the actual viewer gzip size; above the cap it fails (F3-2). Report the final make/tee exit line and log path. Stop on an error; Codex reads the log before deciding what to do.

Only this target receives `ALLOW_FROZEN_RELINK=1`. The Makefile edit makes older targets stale, so do not use this flag with any other target.

## After the link (Codex, before any Phase E)

1. Verify all entries in `frozen-set-before.sha256`; only the new v3 profile is added. Inspect the new manifest: profile `ods-viewer-v3`, `part-info` and `form-controls`, bits 63539, expected base and shared resource hashes. Measure the real viewer gzip and read F3-2.
2. Verify the viewer markers (`search-result`, `partBefore`, `lateSelectAllResults`, SelectAll retry message), absence of the editor completion marker, presence of Calc/forms/RowSet in the bytes; run `check_pthread_stack_literal.py` and the read-only `check_e1_c_bundle_intact.py`.
3. Archive v3 immediately under `build/archive/ods-viewer-v3-<wasm-sha8>-worker-9c85043a/` with all local profile files, exports/base report, SHA256SUMS and ATTRIBUTION.md. Record witnesses under `findings/evidence/m4-ods/viewer-v3/post-link/`. A wasm rebuild cannot recover this identity.
4. Add v3 to the Phase E runners' profile options as specified; keep every run's `--out` explicit. Start with ladder, five form-control files and tdf138507; if V2-158B or V3-NR fails, stop and record the next blocker. If they pass, continue the pinned Phase E, including full corpus x3 for V2-160/160-D. The owner must still inspect tdf134161 on the identified mirror page for V3-SEE.
5. Only a passing v3 prepares host 0.2.33. Installed host remains 0.2.32, package 80349a1a24cecb17; no ddev work without an owner-named slot. Count chain K remains batched; nominal shipped host is 0.2.26.

Section 34.4: this preparation +0 / +0 (because of execution / because of review), cumulative 46 / 27.

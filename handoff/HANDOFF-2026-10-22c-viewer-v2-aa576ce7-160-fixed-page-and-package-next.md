# Handoff, 2026-10-22c: viewer v2 `aa576ce7` -- finding 160 fixed, Phase E clean on the mirror; next: point the viewer page at v2, E4b/E9, a new host package, Phase H

**First line, in SPEC-M3-link-batch-v22 §13.1's shapes:**
- **(a) installed:** unchanged -- ddev runs host **0.2.31** on package `1b4d6a1fc905fb8a` (viewer `ods-viewer-v1` `f6ab3cdb`).
- **(b) built and archived, uncounted:** **`ods-viewer-v2` `aa576ce7`** (the candidate; `wasm_sdk_probe/build/archive/ods-viewer-v2-aa576ce7-worker-9c85043a/`, also in `dist/profiles/ods-viewer-v2/`). Superseded, archived: `e96e01ec` (fallback core, 160 unfixed), `a6390eef` (158-B's diagnostic).
- **(c) bound / counted:** nothing. Nominal shipped version still 0.2.26; K batched.
- **(d) accumulated-uncounted list:** unchanged.

Spec: `specs/SPEC-M4-viewer-v2.md` §8 (160's fix, pinned before the link), §8.4 (link), **§8.5 (Phase E)**. Previous handoff: `HANDOFF-2026-10-22b-…` (everything before the 160-fix link).

## What happened since 10-22b

| when (CST) | what | record |
| --- | --- | --- |
| ~11:20 | owner relinked (`link-gate0.sh`): **`aa576ce7`**, gzip 47,971,896; runbook G2 holds (frozen set: only probe.js/probe.wasm changed; manifest `fa54c32c`, worker `9c85043a`, base `6f7424a1` identical to e96e01ec's); archived | §8.4, `d2869c6d`, `160-fix-post-link/` |
| ~11:25 | V2-160-D's judge (`tools/judge_v2_160_d.py`) before any run: selftest 9/9; red on exactly e96e01ec's three failed-dispatch files on real reports | `0b948bf4` |
| 11:27-11:58 | Phase E chain on aa576ce7: targeted run all PASS (tdf138507 opens; five control files refused per 158-A); E6 per SPEC-M4 addendum 12 PASS, B = 0; full corpus x3: E1/E2/E4a/E5/E6/V2-157 PASS, E3 red only on `L-no-basic-udf`, **V2-160 0/0/0**, **V2-160-D PASS x3** (6 failed dispatches, each recorded by engine and LOK alike, each confirmed after one 50 ms pause) | §8.5, `6e5fb375`, `160-fix-phase-e/` |

Finding 160: **fixed in the v2 engine**; the cause behind the failed dispatch (why the Desktop's active frame is missing for a moment) is inferred, not measured. Four of the six redispatched files had failed before, all at part 0: the failure prefers some files.

## Next, in order

1. **Point the product viewer page at v2.** `wasm_sdk_probe/web/ods-viewer-app.js:26` names `./profiles/ods-viewer-v1/sdk-worker.js` -- change it to v2 (a product change; write the reason in SPEC-M4-viewer-v2 first), re-stage with `make ods-viewer-assets` (cp only), re-run the shell's unit tests.
2. **E4b and E9 on v2** (never run on any v2 link; SPEC-M4 §4 says E1-E9 all re-run). `tools/run_ods_viewer_e4b_e9.py` hard-codes `PROFILE = "ods-viewer-v1"` and refuses unless the page names PROFILE exactly once: give it `--profile` as `run_ods_viewer_e6_leak.py` got (default v1), then run against the v2 page with `--phase-e-report` = a 160-fix-phase-e full-corpus report and `--out` under `findings/evidence/m4-ods/viewer-v2/160-fix-phase-e/e4b-e9/` (its default out is v1's counted directory). Its red case (`--red-case no-refit`) once on v2 too.
3. **A new host package** carrying `ods-viewer-v2` `aa576ce7` (and the unchanged editor `e2-editor-v22` `f7a40bcc`): branch `host-0.2.32` in `~/Projects/Nextcloud_Apps/litecore`, packager `tools/package_m3_engine.py` (schema `litecore-engine/3`), offline checks K0/Z0/H5-1 (`tools/check_m3_assets.py`) and the package red cases, as `RUNBOOK-install-host-0.2.29.md` and `HANDOFF-2026-10-20j-…` describe. Viewer gzip 47,971,896 is under the 52,428,800 cap. Write an install runbook for it.
4. **Phase H in a ddev slot the owner names** (ddev is shared: memory `ddev-is-shared-do-not-occupy`). The first host Chrome runner there is also the witness for SPEC-M3-production-ui §17.27's residual 1 (host runners under `--password-store=basic`).
5. Still open: H7 on 0.2.31 (owner clicks `three-sheets-distinct.ods` in Files); 158-B as its own work item (finding 158); finding 164's intra-open growth work item.

## Hazards

- Every ODS runner's default `--out` is v1's counted directory: always pass `--out`.
- The four Chrome launchers outside `ChromeSession` (`validate_e1/r7/r8_preflight`, `v21_network`) have no `--password-store=basic`.
- The product page still names v1: until step 1, anything driving `web/ods-viewer.html` measures v1, not the candidate.
- `build-ods-viewer-v2` (6.0 GB) is only 158-B's starting point; nothing defaults to it.

## §34.4

- This stretch: because of execution **+0**, because of review **+0** (`judge_v2_160_d.py` is a new judge with its own red cases; the engine change is product code with D1-D4 and four mutations). Running total since 10-14b: **46 / 27.**
- New, unreviewed: `tools/judge_v2_160_d.py`; `selectAllUntilDispatched` (product, tested); `tools/probe_160_native.cpp` (probe).

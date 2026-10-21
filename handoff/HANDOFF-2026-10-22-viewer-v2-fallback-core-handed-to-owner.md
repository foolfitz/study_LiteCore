# Handoff, 2026-10-22: viewer v2 — 157/159/160 proven on a6390eef, 158-B hit F-3, the owner chose the fallback; the gate0 core rebuild is the owner's next command

**First line, in SPEC-M3-link-batch-v22 §13.1's shapes:**
- **(a) installed:** unchanged — ddev runs host **0.2.31** on package `1b4d6a1fc905fb8a`.
- **(b) built and archived, uncounted:** core `wasm-lite/build-ods-viewer-v2` (DB connectivity, 6.0 GB, K-1/K-2 green) and its link **`ods-viewer-v2` `a6390eef`** (archived `wasm_sdk_probe/build/archive/ods-viewer-v2-a6390eef-worker-9c85043a/`). **It cannot ship** (F-3, below); kept as 158-B's diagnostic artifact.
- **(c) bound / counted:** nothing. Nominal shipped version still 0.2.26; K batched.
- **(d) accumulated-uncounted list:** unchanged.

Spec: `specs/SPEC-M4-viewer-v2.md` — §2.7 (first build: 003, then F-1 overridden by the owner with the reportdesign patch), §5 (core built, pre-link gates), §6 (link), §7 (Phase E on a6390eef, F-3), **§7.1 (the owner chose A: the fallback, with its steps and pre-written readings)**. Previous handoff: `HANDOFF-2026-10-21b-…`.

## What happened

| when (CST) | what | record |
| --- | --- | --- |
| 10-21 10:43 → 10-22 01:19 | v2 core: 003 race; 003 retry (log lost); `libdbulo.a not defined` (reportdesign needs dbaccess's dbu) → owner chose "A, patch" over F-1 → ninth patch; 4th run exit 0 after 45 min | spec §2.7, `findings/evidence/m4-ods/viewer-v2/core/` |
| 01:19–01:36 | K-2 green (80 signatures = the offline set; 783 constructors with OFormsCollection, no dbaccess); base diff read (9 files: DB connectivity's own + two zips with identical content); gzip estimated 49.1 MB; all pre-link gates; my builder's `--report` crashed (Path in JSON) and was fixed before packaging hit it | spec §5 |
| ~01:57 | **owner linked** `a6390eef`; make ended `Error 1` on my gzip-print line (quoting bug, after every check; fixed); frozen set intact, markers, Calc + forms in the wasm, gzip 49,153,029; archived | spec §6, `…/viewer-v2/post-link/` |
| 02:09–02:11 | Phase E on a6390eef: **V2-157, E3 for 159's files, V2-160 PASS**; **the five form-control files and tdf138507 (fine on v1) do not load**: `ODatabaseForm` aggregates dbaccess's `com.sun.star.sdb.RowSet` with `UNO_QUERY_THROW` (`forms/source/component/DatabaseForm.cxx:358`), dbaccess is stripped → F-3 | spec §7, finding 158 (158-B section), `…/viewer-v2/phase-e/` |
| 02:13 | **owner chose A: fallback** (v2 = 159 + 157 + 160 on gate0; 158-B its own work item) | spec §7.1, `32dcd7fd` |

## Next, in order (spec §7.1)

1. **Owner:** `bash /home/jiajun/LibreOffice/study_LiteCore/handoff/ods-viewer-v2/build-core-fallback-gate0.sh` (handed over 02:14, not run yet). Incremental in `build-a11y-gate0`; make re-runs autogen first (configure.ac changed). It prints `DONE`/`STOP`; evidence in `findings/evidence/m4-ods/viewer-v2/fallback-core/` (`config-after-autogen.txt` must say `same` for all 52 files — if not, read before going on; `k2-gate0.json`: K-2a/K-2b/K-2e true, **K-2c false by design**).
2. **Mine, before the relink:** compare `dist/profiles/ods-viewer-v2/` with the a6390eef archive, then delete it and `build/ods/viewer-v2/` (objects were compiled against the v2 core's headers, `HAVE_FEATURE_DBCONNECTIVITY 1`, and the object rule does not track `-I` headers — skipping this ships a form-controls bit the gate0 manifest will not declare, and the worker refuses at init); redo `RUNBOOK-link-ods-viewer-v2.md` §0 against gate0 (test-e2-c-static, builder `--check --core ../wasm-lite/build-a11y-gate0` → base 6f7424a1 with diff 0/0/0, `make -n` diff, syntax, a new frozen-set snapshot). Append the runbook with the fallback command.
3. **Owner:** `make ALLOW_FROZEN_RELINK=1 ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0 dist/profiles/ods-viewer-v2/sdk-manifest.json` (from `wasm_sdk_probe`, after `unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX`).
4. Post-link (runbook §3; expect no `form-controls`, bits 30771 = 14387 + 16384, no `OFormsCollection`), archive, then **Phase E from zero** on the new identity: targeted run (ladder + fdo67682-2 + 159's two + the five control files [refused, 158-A] + **tdf138507 must open**), E6's B on v2, then the full corpus ×3 for V2-160. Then a new package and Phase H in an owner-named ddev slot.
5. 158-B: register as its own work item (needs dbaccess's RowSet; dbaccess carries the whole database UI; gzip margin was 3.28 MB on a6390eef).
6. Still open: H7 (owner clicks `three-sheets-distinct.ods` in Files on 0.2.31).

## Hazards

- `build-a11y-gate0` is v1's core; the fallback rebuild changes it in place (v1 itself is archived; fine).
- The three configure/build patches in the shared tree: any `make` in `build-headless-probe` also re-runs autogen once first.
- `test-e2-c-static`'s carrier line now judges ODS_VIEWER_V2's objects against whatever `ODS_VIEWER_V2_CORE` defaults to (the v2 tree) — keep the v2 tree on disk, or change the default together with the fallback link.
- Evidence runners write by default (memory `evidence-runners-write-by-default`).

## §34.4

- This stretch: because of execution **+0**, because of review **+0** (the builder's report crash and the Makefile's gzip print were bugs in tools before any judgement, not check changes). Running total since 10-14b: **45 / 27.**
- Unreviewed tools as in 10-21b, plus `build-core-fallback-gate0.sh` (a build script, not a judge).

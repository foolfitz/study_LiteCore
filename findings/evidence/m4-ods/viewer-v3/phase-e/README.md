# Phase E on ods-viewer-v3 ebb7e0cb, 2026-10-24

Spec: `specs/SPEC-M4-viewer-v3.md` sections 4, 12-14. Mirror only, no ddev. The engine was not relinked between measurements and verdicts. **Machine criteria pass subject to the existing Basic UDF limitation; V3-SEE still awaits the owner's observation.** Host 0.2.33 has not been packaged.

| Measurement | Result |
| --- | --- |
| Targeted (ladder, five form-control files, tdf138507, 157/159 controls, ODT negative control) | All criteria pass, including V2-158B for all five control files and E2 for tdf138507 |
| E4b / E9 on the product source page naming v3 | 2/2 and 1/1 pass; the no-refit red case reproduces E4b failure while E9 remains green |
| E6, without --bound | B = 0; boots and five-cycle reopen shape pass for all three entries; reopen series recorded, not judged as a leak bound (finding 164 retained) |
| Full corpus x3 | Each run: 303 opens, 3 encrypted refusals; E1/E2/E4a/E5/E6/V2-157/V2-158B/V2-160 pass; E3 fails only user-defined-function.ods, the existing L-no-basic-udf |
| V3-NR | Every one of v2's 298 actually opened entries passes the existing E2 opening conditions in every v3 run, including tdf138507; no SHA-only collapse of distinct corpus paths |
| V2-160-D | PASS in all three; one actual failed dispatch in run 1, matched by the engine's retry record and followed by confirmed selection; runs 2/3 had no failed dispatch |

## Full-corpus results

Reports and summaries are under `full-corpus/`. The raw runner returns exit 1 because of the registered E3 limitation; those outputs are preserved without relabeling them all-green. Runs 2 and 3 used independent cold Chrome instances/servers/logs in parallel (source, bytes and criteria unchanged), on a 12-core host with no make running.

| UTC report start | Seconds | Open / refused | Text reads / unconfirmed | Largest wait (ms) | Highest stage sbrk (B) | Old opens retained |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-10-23T163018Z | 640.2 | 303 / 3 | 470 / 0 | 177 | 553,840,640 | 298 / 298 |
| 2026-10-23T164128Z | 672.3 | 303 / 3 | 470 / 0 | 182 | 553,844,736 | 298 / 298 |
| 2026-10-23T164203Z | 672.5 | 303 / 3 | 470 / 0 | 266 | 553,840,640 | 298 / 298 |

All high-water values are below E6's 939,524,096 B cap. The one redispatch was tdf167450_source.ods in run 1; LOK count = engine count = 1, every read confirmed, no never-dispatched line. V2-160/160-D hold with the retry exercised on this identity. N=3 is complete; no extra sweep is required for that criterion.

## Read the existing artifacts (no browser, no rewriting evidence)

From the repo root:

```bash
python3 wasm_sdk_probe/tools/check_ods_viewer_v3_nonregression.py findings/evidence/m4-ods/viewer-v3/phase-e/full-corpus/report-*.json
python3 -I wasm_sdk_probe/tools/judge_v2_160_d.py findings/evidence/m4-ods/viewer-v3/phase-e/full-corpus/report-*.json
```

The first command enumerates the required old opens from the fixed aa576ce7 report and applies the existing E2 judge per candidate entry. The second reads the actual recorded LOK/engine messages. Both exit 0 on these three reports. Their saved results are `nonregression-{1,2,3}.json` and `v2-160-d-all.jsonl`; `summary-all.json` also records the pending human step. The existing Phase E `judge(report)` function recomputes E1-E6/V2-* from each report's raw data; it was rerun when these summaries were made.

## Pending human observation and next step

`human-preview/` identifies the local product-page mirror: http://127.0.0.1:8794/ods-viewer.html?diagnostics=1 . Green banner: ods-viewer-v3 / ebb7e0cb, automatically loaded tdf134161.ods (101 controls). The page bytes, exact fixture, state and screenshot were verified before handing it to the owner. **That preflight is not the owner's confirmation.**

Record the owner's exact answer with this identity. Until then, do not claim V3-SEE or a completed 158-B fix, and do not proceed to the spec's all-pass host 0.2.33 packaging step. After confirmation: prepare the isolated host worktree/package/offline gates/archive/install and rollback scripts; only then request an owner-named ddev slot for Phase H. Full count chain K remains batched.

Section 34.4: +0 / +0 (because of execution / because of review), cumulative 46 / 27. No existing judge was changed.

## Owner confirmation, 2026-10-24 (supersedes pending statements above)

The owner confirmed both the green identity banner and the small box in the yellow cell. V3-SEE holds; the exact original answer and its translation are in `human-preview/owner-confirmation.md` (or `owner-confirmation.md` from the preview directory). All pinned Phase E requirements are now met with the existing Basic UDF limitation retained. Host 0.2.33 packaging is the next step; installation remains unperformed.

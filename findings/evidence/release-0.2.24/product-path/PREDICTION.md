# Product-path net for the 0.2.24 release — predictions (written 2026-10-15, before any run)

0.2.24 is 0.2.23 plus finding 145's page fix (`f7887ced`, page `ccb67a52…` → `901dd6a6…`, shell v73, host `1479e56`, engine package `d3cd39bbc71ec311`). Everything in `../../release-0.2.23/product-path/PREDICTION.md` is carried. That net ran in the 0.2.23 chain (`20261015T025837Z`) and read `SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 2)`. It was not made red offline before its verdict was read, because the count did not hold (merge, finding 145) and the verdict was never needed.

The reader is `judge.py` here (0.2.23's copy, with the two page constants moved; see its docstring). The runner is unchanged (`9d1f44c6…`).

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v20 reports: entrypoint `901dd6a6…`, no candidate keys; v8 reports: source before repointing `901dd6a6…`, rest of shell equals source, entrypoint `daa868d3…`, profile e2-editor-v8, `pinBefore 313b08d5cb085897` |
| P3 | 0 red cells under §23 + row 1′ |
| P4 | descriptive: the cells that differ between the arms are NE-only, as 0.2.23's two were (Firefox `clear-format-removes-every-inline-format`, Firefox `recovery-returns-what-the-product-promised`), or none |

## The one change since 0.2.23, and the cells that could see it

| Change | Where it lives | Cells that touch it | Prediction |
|---|---|---|---|
| **Finding 145**: `settleDelete` counts a delete's answer back even when its document is gone, and drops the presses held for that document | page (0.2.24, v73), `e2-editor-app.js` `settleDelete` | Only a cell where the engine **refuses a delete** and a later delete of the same key follows in the same page. On v20 no plain cell induces a refusal: boundaries are C no-ops, and `a-refused-action-is-reported-and-changes-nothing` induces one only in diagnostic mode. On the v8 arm a refusal at a boundary can happen, for example in `recovery-returns-what-the-product-promised` (finding 038's path). | No cell turns red. On v8 a cell whose later delete was held under 0.2.23 now sends it, so its outcome may move between PASS and NE inside row 1′'s window. Any move is listed under P4, not judged. |

**Watch item (carried)**: Chrome `clear-format-removes-every-inline-format` NE in ≥ 2 of the 6 Chrome runs (either arm) means the product-path verdict is not read until that is diagnosed.

Before the verdict is read, the reader is made red once on scratch copies, as in 0.2.12 (`../../release-0.2.12/product-path/judge-red-offline.txt`):
- a flipped v20 cell where v8 passes → P3 MISS;
- a wrong v20 entrypoint → P2 MISS.

The verdict is the `SUMMARY` line (§34.7).

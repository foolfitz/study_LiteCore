# M2: the 84 S5 type cells on v24, both browsers (preparation, not counted)

Spec `specs/SPEC-M3-link-batch-v24.md` §6.3 M2 (ruling 1 §5 M2). Runner `wasm_sdk_probe/tools/run_v24_feature_selection.py --population s5-type`; reader `tools/judge_v24_feature_selection.py` (J-red held first, `../j-red/`). Bindings: profile `e2-editor-v24` (archive pins), page `b15a6d8e…`, candidate shell digest `56ce44c7…` (generation 77 not frozen, spec §15).

## shakedown-01 (2026-10-28 11:22 +0800)

One cell, finding 168's stop: `shift-Right@cell-end/type`, both browsers, to see the instruments run end to end before the full population. **PASS in Chrome and Firefox**: T2 holds (every insertText `route`/`method` `uno-insert-text`, `completion` `uno-command-result`); T1 compares with native run-03 (`selection-before-x`) and is equal — A1 empty, B1 `x`, where v23 saved `A1 cell textx` / `B1 cell textx#`. The standalone reader on the report: `NOT_ESTABLISHED` only because 2 of 168 cells were observed; 0 proof-absent; reply methods `["uno-insert-text"]`. Raw cells as `.json.gz` (index `../m2-shakedown-01-storage-index.json`).

## run-01: owner-run (owner chose B, 2026-10-28)

`cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/run_v24_m2_owner.sh` — all 84 type cells, Chrome then Firefox, `--keep-going` (a preparation records every cell). Writes `run-01/`, `run-01.runner.txt` (one line per cell, then the exits) and `run-01.reader.json` (the standalone reader). Before it was handed over, the runner gained a one-line-per-cell progress print and was checked on one Chrome cell in the scratchpad (`shift-Right@caret-mid/type` PASS). M2 holds if the reader says `PASS`: 168/168 cells PASS (T1 and T2), 0 proof-absent `insertText` replies, reply methods exactly `["uno-insert-text"]`.

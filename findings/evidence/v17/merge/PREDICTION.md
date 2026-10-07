# Prediction, before the run: merge (option B) WASM shakedown on v17, Chrome and Firefox (spec 26.3 V6)

Written 2026-10-07, before any v17 merge run in this directory (V5's run in `../v5/` used `--owner-document` and no `--frame-cell`; it is not this run). Uncounted.

## Commands (from `wasm_sdk_probe/`, one at a time, after the product-path chain)

For B in chrome, then firefox:

```
python3 tools/run_merge_wasm_shakedown.py --browser B --candidate-profile e2-editor-v17 --frame-cell --rounds 2 --out ../findings/evidence/v17/merge/shakedown-B.json
python3 tools/run_merge_wasm_shakedown.py --browser B --candidate-profile e2-editor-v17 --frame-cell --rounds 2 --control --out ../findings/evidence/v17/merge/control-B.json
python3 tools/run_merge_wasm_shakedown.py --pair ../findings/evidence/v17/merge/shakedown-B.json ../findings/evidence/v17/merge/control-B.json
```

Tool-generated list (spec 22.1 as narrowed by 25: 26 cases) plus the frame cell (F01, F02); no `--cases`; no `--owner-document`. Runner sha256 prefix `c3f723b3be6eb4bf`; page `4c0088c7…` (the report's `candidate.pageSha256`). Two rounds so that a case that passes once and not twice is visible; this is still a shakedown, not M2's counted 3 x 2.

## Predictions

- **S1 (precondition).** Every report: profile `e2-editor-v17`, `pageSha256` `4c0088c7a518bc36…`, `restOfShellEqualsSource` true, boot ready, 56 case records (28 x 2), no `runner-error`. A miss here is not evidence about v17.
- **S2 (Chrome).** As V5's synthetic half and v16 run 3: 20 M2-1 cases pass every clause, G01 `verified-selection-delete`, the five M2-3 cases refused with R0c's stage and `keyPosted`, F01/F02 refused `anchor-mismatch` with `keyPosted:false`, in both rounds. M2-0 `reducedBytesEqual` for both synthetic fixtures. `--pair`: 0 differ.
- **S3 (Firefox; first run of this runner on Firefox).** The same outcomes and clauses as S2. Latency (`keyToResponseMs`) is listed and not judged: on Firefox it includes WebDriver key dispatch (10-07c "N2 (Firefox latency)": `t0` is read by a page evaluate before the key is pressed, `run_merge_wasm_shakedown.py:645-666`).
- **S4.** No toast other than the expected ones (spec 22.1's toast window), no 「重繪失敗」.

## What a miss means

- S2 miss on Chrome: v17 changed something B depends on (first suspect: layout, i.e. a synthetic fixture whose caret moved; V5 says the synthetic carets are unchanged); blocks the v56 freeze until diagnosed.
- S3 miss only on Firefox: first separate the harness (key dispatch, focus) from the product by checking the same case on v16 in Firefox before calling it a v17 effect (v16 was never run on Firefox with this runner either).
- If never run: V6's merge part is not met (26.3: v17 may not be cut over).

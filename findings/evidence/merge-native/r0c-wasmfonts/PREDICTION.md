# Prediction, before the run: native R0c on the owner's document with the WASM profile's fonts

Written 2026-10-07, before the run. Owner's choice B (spec 25): re-run the owner's-document R0c round natively with the fonts `e2-editor-v16` lays out with, so the merge runner's placement by native coordinates can work there.

## Why

Merge shakedown run 3 (`v16-shakedown/merge/README.md`): all 11 owner's-document cases ended `placement-mismatch`; native and WASM line heights differ (348/276, 521/414 twips ...). Font resolution on this machine (`fc-match`, system config vs the profile's): `Microsoft JhengHei` -> 微軟正黑體 and `PMingLiU` -> 新細明體 natively (the real fonts are installed here), `Noto Sans CJK TC` (the tier-E subset) on WASM; every other name in the document resolves the same way under both.

## Setup

`tools/extract_wasm_fontset.py --profile e2-editor-v16 --out build/wasm-fontset-v16`: the profile's 13 font files (Liberation Mono/Sans/Serif x4, `NotoSansCJK-Regular-subset-E.ttc`) and its fontconfig (`fonts.conf` with only that directory, its 22 `conf.d` files). `FONTCONFIG_FILE=<that>/fonts.conf fc-list` shows 17 faces (system: 838). The native install bundles no fonts besides `opens___.ttf` (WASM has the same).

```
FONTCONFIG_FILE=$PWD/build/wasm-fontset-v16/fonts.conf MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z \
  tools/run_merge_native.sh build/merge-native-pmpc/r0c-wasmfonts 3 build/scratch-m3-production-ui/PMPC指南.odt test-docs/merge/r0-pmpc.cases.tsv 1
```

Saved documents stay under `build/` (the owner's document never enters the repository); `arms.jsonl` and `inputs.sha256` are copied here, as for the earlier owner's-document rounds.

## Predictions

- **W1 (merge does not depend on fonts).** The native reader (`check_merge_eshape.py`) decides the same 11 cases as R0c did (`merge` each), 0 KILL; its only STOP is the vacuous "a decision class never occurred".
- **W2 (the 0.79 is the fonts).** The native placed carets now have WASM's heights: E01, E12, P27, E13, E15, P62, P63 height 276 (was 348); E02 414 (was 521); E05 276; E10 230. If the heights stay at the old values, the difference is the engine, not the fonts, and B falls back to A.
- **W3 (placement).** With the merge runner pointed at this round, every one of the 11 cases places exactly (engine caret = native caret) on Chrome.

## What a miss means

- W1 misses: a font change changed what a merge does natively; stop and look before anything uses this round.
- W2 misses: the layouts still differ; spec 25 falls back to A (narrow M2-1 to the synthetic fixtures).
- W3 misses with W2 hit: a placement problem other than line heights; diagnose before counting.

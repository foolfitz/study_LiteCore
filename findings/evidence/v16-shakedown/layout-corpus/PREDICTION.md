# Prediction, before the run: corpus layout dry run (noise) and red case

Written 2026-10-07, before any run of `wasm_sdk_probe/tools/compare_layout_corpus.py`. This run is NOT counted (spec section 21.2: it sets T; the counted comparison is a later, separate run, v16 against `e2-editor-v15-cjk-r5-ab`, after T is appended to the spec).

## Command (one invocation, Chrome, after the product-path chain has finished)

```
python3 tools/compare_layout_corpus.py --profiles e2-editor-v16 e2-editor-v16 e2-editor-v15 --out <this directory>
```

Pairs written to `comparison.json`: (v16 session 1, v16 session 2) = noise; (v16 s1, v15) and (v16 s2, v15) = red case. All three profiles have wasm `ad3f68bb85f94589`; v15 and v16 differ only in the CJK pack (v15: one family, the cause of finding 113; v16: five families). The page is `web/e2-editor-app.js` repointed (`pp.CUTOVER_PAGE_SOURCE`). The corpus split by the tool's own `cjkCharacters` (paragraph text of `content.xml`): 44 documents > 0, 27 documents = 0, 5 unreadable as ODT (`None`: three are not zip files, two have no `content.xml`).

## Predictions

- **L1 (noise).** v16 against v16: every comparable document identical (`maxTopDifference` 0, same band count). Basis: one wasm, one pack, the tool waits for two identical canvas reads. If not 0, T = that maximum + 2 px (spec 21.2).
- **L2 (red case, the instrument sees 113).** v16 against v15, both pairs: at least one document with `cjkCharacters > 0` differs by more than T or in band count. Expected magnitude: tens of pixels on a CJK-heavy document such as `test-docs/t1-plain-zh.odt`, because 113 changes the line height of every CJK line and the offset accumulates down the page.
- **L3 (one variable).** v16 against v15: every document with `cjkCharacters == 0` identical. A miss is a second variable (for example empty-paragraph height through the Asian font slot) to be registered and explained, not a failure of L2.
- **L4.** The not-comparable set is the same in all three measurements and includes the three non-zip documents.

## What a miss means

- L1 misses only by size: T grows. L1 with differences larger than a line height: the instrument is not stable enough to carry 21.2; stop.
- L2 misses: the instrument cannot see 113 at T; spec 21.2 says the criterion may not be used.
- If this run is never made: 20.3 stays a draft; the conclusion is 20.3's "never done" sentence.

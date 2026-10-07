# Prediction: is the narrower line on v15 the CJK pack? (written 2026-10-07, before any run)

Question: on v15 the line the product-path runner samples at canvas y 0.28 ends earlier than on v8 in both browsers
(`inkLeft` unchanged; `inkRight` Chrome 505 -> 471 on a 725 px canvas, Firefox 627 -> 584 on 900 px, i.e. 4.7% and 4.8% of
the canvas width), and on Firefox the caret placed "near the start" (left + 0.12 x span) is no longer detected
(`strokeLost 0`), so `the-caret-is-drawn-where-it-was-placed` FAILs and `the-caret-lands-where-the-click-was` is NE
(`findings/evidence/v15-shakedown/product-path/README.md`, section B). v15 changed four things at once (B, 096's engine half,
082's fix, the CJK pack). The fixture's text mixes Latin and CJK (`test-docs/e1/list-contexts.odt`: e.g.
"E1-LC-ISOLATED 前後都不是清單的段落", "E1-LC-BULLET-TWO 中文項目").

Instrument: the same runner, unchanged (`tools/run_e2_c_product_path.py`), with `--profile e2-editor-v15-cjk-r5-ab`.
That profile is v15's link (`probe.wasm` ad3f68bb..., `probe.js` 46b2f40a..., `sdk-worker.js` 00882139..., v15's
`exports.txt`) packed by `tools/build_e2_editor_v4_profile.py` from `sdk/r6-writer-review-manifest.json` instead of
`sdk/v15-writer-review-manifest.json`. Its manifest differs from v15's in exactly three places: `profile`, `sdkVersion`, and
the CJK pack entry (`cjk-r5`, the full `NotoSansCJK-Regular.ttc`, instead of `cjk-sub-e`). It lives in
`wasm_sdk_probe/dist/profiles/e2-editor-v15-cjk-r5-ab/` (not in git, never shipped; `--profile` stamps every report
diagnostic). One round per browser: the quantities below were identical in all three rounds of each profile.

Outcomes, decided now:

- **P1 (CJK pack is the cause)**: on the A/B profile `inkRight` is 505 (Chrome) and 627 (Firefox), as on v8, and on Firefox both
  caret checks PASS. Then the engine changes are cleared for this cell, and the next question is which glyphs moved
  (pixels of that line on v15 against the A/B profile) and whether that is the registered loss of spec section 19
  (Japanese/Korean/Simplified-tagged text rendered in Traditional forms) or something not registered.
- **P2 (the engine changes are the cause)**: `inkRight` stays 471 / 584 and the Firefox caret cells stay red. Then the CJK pack
  is cleared and the line width difference comes from B, 096 or 082 -- unexpected for all three, so it would be read from the
  engine source before anything else is run.
- **Anything else** (for example `inkRight` between the two values, or the two browsers disagreeing): neither hypothesis; no
  conclusion is drawn and the run is repeated before reading further.

Not decided by this run: whether a red caret cell is a product defect or this instrument's documented limit (the caret is
adjacent to glyph ink and on Firefox `strokeLost` can be 0). That is a separate question either way.

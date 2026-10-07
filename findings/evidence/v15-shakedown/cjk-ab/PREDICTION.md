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

## Addendum, same day, still before any run: the Asian-slot probe

Read while the A/B run was going (no browser involved):

- Vertical metrics of the subset font are identical to every face of the TTC (`hhea` 1160/-288/0, `OS/2` typo 880/-120/0,
  win 1160/288, `head` yMin/yMax -1048/1808), so "the subset font is selected" cannot change a line height.
- The TTC carries ten families (Noto Sans CJK JP/KR/SC/TC/HK and the Mono variants); the subset carries one, `Noto Sans CJK TC`.
- fontconfig 2.17.1 (`fc-scan`) says the tier-E subset covers `zh-cn`, `zh-tw`, `ja` but **not `ko`**; every TTC face covers `ko`.
- An ODT the WASM engine saved earlier (`findings/evidence/016/selection-barrier-wasm/browser/firefox/plain-positive-final.odt`,
  an r5-era profile with the full TTC) declares `style:font-name-asian` "Noto Sans CJK KR" (2) and "Noto Sans CJK SC" (1), and
  `style:font-name-complex` "Noto Sans CJK KR" (3): the engine's defaults named TTC families that the subset does not have.
- The base pack's only other fonts are Liberation Mono/Sans/Serif and OpenSymbol. The ratio of the caret heights on v15 to v8 in
  the recovery arm (Chrome 16/20, Firefox 19/24, both about 0.8) is close to a Liberation line (about 1.15 em) over a Noto Sans
  CJK line (1.448 em).
- Check 42 (finding A) is consistent with the same cause: on v15 Chrome the endnote fixture's first two body lines are 8 px or
  less apart and merge into one band under `BAND_MERGE_GAP = 8`; the page-bottom endnote band keeps the band count at 3, so the
  `len(bands) >= len(base_lines)` guard passes and `noteLineIndex [1]` aims at the third line (`drag` y 0.07197 is the centre of
  band [126, 139]). The 038 inducer then misses, the once-per-browser worker-failure inducer is spent on the recovery arm, and
  check 42 cannot fire its own.

Hypothesis H-slot: on v15 the Asian font slot that the defaults (and any non-TC CJK family name) ask for no longer resolves to a
CJK font, so it is filled by a Latin font with a smaller line height, and the CJK glyphs come from glyph fallback.

Probe: `wasm_sdk_probe/tools/probe_cjk_font_slots.py` (Chrome only; profiles v8, v15, v15-cjk-r5-ab; saves each document through
the product's save button and keeps the engine's font declarations; canvas PNG and unmerged ink runs). Its generated fixture has,
for each variant, two identical one-line paragraphs, so the pitch between the pair's ink tops is that variant's line height:
default, `font-name-asian` = Noto Sans CJK TC / SC / JP / KR, and Latin-only pairs (default, TC, KR).

Predictions under H-slot:
- v8 and the A/B profile: every CJK-variant pitch equal; v15: `SLOT-TC` equal to v8's, `SLOT-DEFAULT` smaller.
- Latin-only `LATIN-DEFAULT` follows the default slot (smaller on v15 than v8) -- that is what the `EN-PLAIN` line already showed.
- Not predicted: which names v15 writes for the defaults, nor whether `SLOT-SC`/`SLOT-JP`/`SLOT-KR` resolve to the subset on v15
  (fontconfig's answer depends on the language the pattern carries, which this probe does not control).

H-slot is refuted for this probe if v15 `SLOT-DEFAULT` pitch equals v8's, or if v15 `SLOT-TC` pitch differs from v8's.

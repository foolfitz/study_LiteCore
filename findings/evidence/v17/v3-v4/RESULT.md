# v17: spec 26.3 V3 (engine side) and V4 (layout, two locales)

Run 2026-10-07, Chrome, `wasm_sdk_probe/tools/probe_fc_debug.py` at `c5d360da` with `--profiles e2-editor-v16 e2-editor-v17 --locales zh-TW en-US` (output `run/`; shipped loaders unchanged, `shipped-loaders-before.txt`). Locale took effect: `navigator.languages` zh-TW run `[zh-TW, zh, en-US, en]`, en-US run `[en-US, en]`; fontconfig `familylang` carries `zh-TW` only in the zh-TW runs.

## V3 -- HIT

| Profile | conf.d loaded | 35 loaded | 思源黑體 primary lookups (no charset) | glyph-fallback lookups |
|---|---|---|---|---|
| v16 (red case) | 22 | yes | 2 x lang `tw` -> **Liberation Sans** | 4 x lang `tw` -> Noto Sans CJK KR |
| v17 | 21 | no | 2 x lang `zh-tw` -> **Noto Sans CJK KR** | none needed |

Same in both locales (en-US adds the weak default `en` after the strong value). The face is KR, not TC, as review N3 predicted; on v17's subset all five faces share metrics and cmap.

## V4 -- the locale clause HIT; the "becomes 20" clause MISSED on two rows

Pitch (canvas px, 113's reading, page frame rules removed), identical in zh-TW and en-US on each profile:

| Row | v16 | v17 |
|---|---|---|
| TW-SIYUAN (思源黑體) | 16 | **19** |
| TW-PMINGLIU | 16 | 20 |
| TW-XIMINGTI (新細明體) | 15 | 20 |
| TW-KAI (標楷體) | 16 | **19** |
| TW-JHENGHEI | 16 | 20 |
| TW-UMING | 16 | 20 |
| TW-TC, TW-DEFAULT, SLOT-TC, SLOT-DEFAULT | 20 | 20 |
| LATIN-DEFAULT, LATIN-TC, LATIN-KR | 16, 16, 15 | 16, 16, 15 |

- Locale pair: identical tables on both profiles, and no Latin row moved -> the N2 prediction (weak default `tw` -> `zh-tw` inert for Latin text) holds on this fixture.
- Spec 26.3 V4 says the four named rows go from 15-16 **to 20**. TW-PMINGLIU and TW-XIMINGTI did; **TW-SIYUAN and TW-KAI are 19**. That clause is a miss as written. The rows left the Latin height (15-16) for the CJK range, and 19 is also what SLOT-KR shows on v8, v15 and v16 in 113's table (`../../v15-shakedown/cjk-ab/font-slots-r3/pitches.txt`), but whether 19 vs 20 is sub-pixel phase down the page or a metric difference is **not measured**. The criterion was written in canvas pixels against TW-TC's 20 without allowing for that; it is not moved here. The fidelity claim is V5's: the engine's own caret heights in twips on the owner's document (348/521 expected).

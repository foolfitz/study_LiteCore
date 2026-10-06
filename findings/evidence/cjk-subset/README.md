# CJK glyph subset — results (2026-10-07)

Owner's choice D (keep bundled fonts, subset the CJK font, ship with v15; fontTools 4.61.1 from `python3-fonttools` as a build dependency). Predictions and both amendments: `PREDICTION.md` (`7142cbbd`, amendment 1 in the next commit, amendment 2 before the final run). Tool: `wasm_sdk_probe/tools/build_cjk_subset.py`; built fonts under `wasm_sdk_probe/build/cjk-subset/` (not in the repository; rebuilt by the tool).

## Runs

| File | What | Counted |
|---|---|---|
| `shakedown-all-features-C.json` | tier C with all layout features except `locl`: 37,118 glyphs, 7.78 MB zstd — the optional features' alternates (`aalt`, `fwid`/`hwid`/`pwid`, `ruby`) | no; it forced amendment 1 (features = fontTools' default set minus `locl`, because LibreOffice shapes with HarfBuzz's defaults only, `CommonSalLayout.cxx:446–462`) |
| `result-before-combining.json` | C/E/F with the corrected features; base set missing U+0300–U+036F | yes, superseded by amendment 2 |
| `result.json` | C/E/F, base set with combining marks, deterministic build (`recalcTimestamp=False`: the source's `head.modified` kept) | **yes, final** — the non-deterministic run before it differed only by ≤ 17 bytes of zstd per tier; raw sizes, glyphs, coverage, identity and misses identical |

Red cases (`--self-test`, before the counted runs): a dropped code point, a changed advance, a swapped outline — 3/3 caught.

Corpus: `wasm_sdk_probe/test-docs/` (385 documents; 3 deliberately broken zip fixtures skipped and listed in the JSON) and the owner's `PMPC指南.odt` (read only).

## Result (`result.json`)

**Coverage and identity: 0 failures on every tier** — every required code point maps to the original glyph, every kept glyph has the original's decomposed outline and horizontal/vertical metrics.

| tier | code points | glyphs | raw | gzip-9 | zstd-19 | saving vs `cjk-r5` (12,170,785 zstd) | corpus documents with misses |
|---|---:|---:|---:|---:|---:|---:|---|
| C | 20,095 | 20,098 | 5.68 MB | 4.90 MB | **4,426,757** | 7.74 MB | 5 (Hangul ×3, U+5F66/U+5FB3/U+8D30 Simplified/Japanese forms, U+38AD Ext-A) |
| E | 25,768 | 25,825 | 7.20 MB | 6.23 MB | **5,599,936** | 6.57 MB | 3 (Hangul, U+38AD Ext-A) |
| F | 43,329 | 45,282 | 10.84 MB | 9.13 MB | **8,103,587** | 4.07 MB | 0 |

**The owner's document misses nothing at any tier.** Every miss is in a test fixture (Korean and LibreOffice's own `tdf*` spreadsheets).

## Against the predictions

| What | Predicted | Measured |
|---|---|---|
| C glyphs / zstd | 19,000–21,000 / 3.8–4.7 MB | 20,098 / 4.43 MB — as predicted |
| E glyphs / zstd | 24,600–27,000 / 4.8–5.9 MB | 25,825 / 5.60 MB — as predicted |
| F glyphs / zstd | 42,000–45,000 / 6.9–8.4 MB | **45,282** (282 over) / 8.10 MB |
| coverage, identity | 0 failures | 0 |
| corpus, C | nothing in `test-docs/` | **wrong**: 5 fixtures miss characters outside Big5/HKSCS |
| corpus, E and F | nothing | **wrong at E** (Hangul, Ext-A in 3 fixtures); F nothing |
| corpus, owner's document | at most a handful at C | **none at any tier** |

The first prediction (all features but `locl`) was wrong by a factor of two and is the reason for amendment 1; the base-set gap (combining marks) was an instrument error, amendment 2.

## What is given up, at every tier

- Text tagged Japanese, Korean or Simplified Chinese renders in Traditional Chinese glyph forms (`locl` and the other faces dropped).
- A document that names an optional OpenType feature in its font name (`:fwid`, `:ruby`, …) gets the default forms.
- Characters outside the tier render as missing glyphs, and nothing reports it (LOK has no missing-glyph callback; finding 085).

## Owner's choice and the pack (2026-10-07)

**Tier E.** `wasm_sdk_probe/tools/build_cjk_subset_pack.py` builds it, re-verifies coverage and identity, and packs it with `build_r5_profiles.create_pack`: `dist/profiles/resources/cjk-sub-e.2d8240354ce1cf78.data` (7,200,632 bytes, one file `/instdir/share/fonts/truetype/NotoSansCJKtc-Regular-subset-E.otf`) and `cjk-sub-e.9bbc2a5e752f1364.metadata`. The build is deterministic: two builds from the same input give the same bytes (`2d8240354ce1cf78…`). `sdk/v15-writer-review-manifest.json` is `sdk/r6-writer-review-manifest.json` with only the `cjk-r5` entry replaced. `--check` (run by the v15 profile rule before packing) rebuilds in a scratch directory and fails on a tampered manifest or a missing pack file — both red cases run.

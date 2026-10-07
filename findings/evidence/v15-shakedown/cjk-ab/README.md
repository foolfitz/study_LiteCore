# v15 shakedown: the two red cells are the CJK pack, not the engine

Question (from `../product-path/README.md`, findings A and B): on v15, Chrome's `a-boundary-arrow-press-does-not-cost-the-work`
FAILs (B4 not measured) and Firefox's two caret cells are red, and the line sampled at y 0.28 is about 8% narrower in both
browsers. v15 changed four things at once: B (paragraph merge), 096's engine half, 082's fix, and the CJK pack
(`cjk-r5`, the full Noto Sans CJK TTC, replaced by `cjk-sub-e`, a tier-E subset of the TC face). Predictions were committed
before each run: `PREDICTION.md` (`8f54ea3a`; addendum 1 `7b8f1ec4`; addendum 2 `0a6222dd`).

Nothing here is counted. Every profile below except v8 and v15 is unshipped and diagnostic, lives in
`wasm_sdk_probe/dist/profiles/` (not in git), and was built from v15's link (`probe.wasm` `ad3f68bb...`, `probe.js` `46b2f40a...`,
`sdk-worker.js` `00882139...`, v15's `exports.txt`) with `tools/build_e2_editor_v4_profile.py`; each manifest differs from v15's
only in `profile`, `sdkVersion` and the CJK pack entry.

| profile | CJK pack | built from |
|---|---|---|
| `e2-editor-v15-cjk-r5-ab` | `cjk-r5` (the full TTC, as v8) | `sdk/r6-writer-review-manifest.json` |
| `e2-editor-v15-cjk-ttc5-ab` | `cjk-sub-e-ttc5-ab.ce59153d3861ef9c` (candidate, see below) | r6 manifest with the CJK entry replaced by `tools/build_cjk_subset_ttc_candidate.py` |

## 1. A/B with the same instrument: both red cells come back (P1)

`tools/run_e2_c_product_path.py --profile e2-editor-v15-cjk-r5-ab`, one round per browser (the quantities in question were
identical in all three rounds of each profile in `../product-path/`). Reports: `e2-editor-v15-cjk-r5-ab-{firefox,chrome}-r1.json`.

| | v8 | v15 | v15 link + full TTC |
|---|---|---|---|
| Firefox totals (PASS/FAIL/NE) | 29-30 / 1 / 11-12 | 28 / 2 / 12 | 30 / 1 / 11 |
| Firefox caret line `inkRight` (inkSpan) | 627 (526) | 584 (483) | **627 (526)** |
| Firefox `the-caret-is-drawn-where-it-was-placed` / `...-lands-where-the-click-was` | PASS / PASS | FAIL / NE | **PASS / PASS** |
| Firefox recovery arm `bandsAtInducer`, caret height | `[103,118] [132,150] [163,178] [1241,1267]`, 24 | `[103,118] [128,146] [158,173] ...`, 19 | **as v8**, 24 |
| Chrome totals | 40 / 0 / 2 | 39 / 1 / 2 | **40 / 0 / 2** |
| Chrome caret line `inkRight` (inkSpan) | 505 (423) | 471 (389) | **505 (423)** |
| Chrome recovery arm `bandsAtInducer` | `[83,95] [106,120] [130,143] [1000,1018]` | `[83,117] [126,139] [1000,1018]` | **as v8** |
| Chrome 038 inducer `drag`, `finding038Reproduced` | `[0.10621, 0.74069, 0.06138]`, true | `[0.10621, 0.4, 0.07197]`, false | **as v8**, true |
| Chrome `a-boundary-arrow-press-does-not-cost-the-work` | PASS (press not answered; B4 by the boundary press) | FAIL (B4 null) | **PASS** (press answered, state `ready`; B4 by the worker-failure inducer) |

Every check outcome on the A/B profile equals v8's in the same browser; against v15 the only differences are the three red cells.
So B and A are caused by the CJK pack, and on these cells v15's engine changes are clean. The last row also shows 096's engine
half working on Chrome: the boundary press is answered and the session stays `ready`, and B4 is still measured.

How A follows from the same cause (read from the reports and `run_e2_c_product_path.py`, not separately measured): v15's
shorter lines bring the endnote fixture's first two body lines within `BAND_MERGE_GAP = 8` of each other on Chrome, so they
merge into one band; the page-bottom endnote band keeps the count at 3, so `len(bands) >= len(base_lines)` passes;
`noteLineIndex [1]` then names the third line (y 0.07197 is the centre of `[126,139]`), the 038 drag misses the endnote mark,
the recovery arm falls back to `INDUCE_WORKER_FAILURE` (once per browser), and check 42 has no inducer left. Instrument note:
that guard counts bands that are not body lines; a body-line count would have refused the aim instead of missing.

## 2. Why the lines are shorter: the Asian font slot falls to Liberation Sans

Facts read without a browser (`PREDICTION.md` addendum 1): the subset's vertical metrics equal every TTC face's; the TTC has
ten families (five Sans, five Mono), the subset one (`Noto Sans CJK TC`); fontconfig 2.17.1 says tier E covers zh-cn, zh-tw and
ja but not ko. The base pack's only other fonts are Liberation and OpenSymbol.

Probe: `wasm_sdk_probe/tools/probe_cjk_font_slots.py` (Chrome; saves each document through the product's save button and reads
the engine's own font declarations; canvas PNGs). Its generated fixture (`cjk-font-slots.odt` in each directory) has two identical
one-line paragraphs per variant; the distance between the pair's ink tops is that variant's line height in canvas pixels.

- `font-slots-r1/`: **the generated fixture was not served** (`build_mirror` replaces existing files only; the engine opened the
  server's 404 page, visible in the `*-cjk-font-slots.png`). Its first two documents are valid. Kept as the reason for the
  fixture check that `r2` onwards records (`fixtureOpened`).
- `font-slots-r2/`: 8 variants, default Asian language. `pitches.txt`.
- `font-slots-r3/`: 16 variants, adding names a Taiwanese document carries, tagged zh-TW (taken from the owner's document's
  font declarations; none of its content is used). `pitches.txt`.

The default Asian font the engine wrote into `styles.xml` (default paragraph style), every document, every run:

| v8 | v15 | v15 link + full TTC |
|---|---|---|
| `Noto Sans CJK KR` | **`Liberation Sans`** | `Noto Sans CJK KR` |

Line pitch (`font-slots-r3/pitches.txt`):

| variant (`font-name-asian`) | v8 | v15 | full TTC |
|---|---:|---:|---:|
| CJK text, default | 20 | **16** | 20 |
| CJK text, Noto Sans CJK TC | 20 | 20 | 20 |
| CJK text, Noto Sans CJK SC / JP / KR | 20 / 20 / 19 | **16 / 15 / 16** | 20 / 20 / 19 |
| Latin-only text (default, TC, KR) | 16 / 16 / 15 | 15 / 16 / 16 | 16 / 16 / 15 |
| CJK text, zh-TW, default / Noto Sans CJK TC | 20 / 20 | **16** / 20 | 20 / 20 |
| CJK text, zh-TW, 思源黑體 / PMingLiU / 新細明體 / Microsoft JhengHei / AR PL UMing TW / 標楷體 | 16 / 16 / 15 / 16 / 16 / 16 | 15 / 16 / 15 / 16 / 16 / 15 | 16 / 16 / 15 / 16 / 16 / 16 |

Reading: on v15 a line with CJK text gets a Latin line height unless its Asian font is literally `Noto Sans CJK TC`; the CJK
glyphs still draw (glyph fallback finds the subset), so nothing looks missing, but every such line is about 0.8 of its v8
height and documents reflow. Saving on v15 writes `Liberation Sans` as the default Asian font of a document that did not name
one. Spec section 19 registered "Japanese/Korean/Simplified-tagged text renders in Traditional Chinese forms"; what happens
instead for those names and for the default is a Latin line height, which was not registered.

Not a v15 difference, and not diagnosed: the names a Taiwanese document uses (last row) get a Latin line height on v8 as well.
Whether that is a fidelity gap depends on what it is compared with (the real fonts' own metrics differ from Noto Sans CJK's
too); nothing here measures that.

## 3. A candidate that restores v8: the same subset as a five-family collection

`wasm_sdk_probe/tools/build_cjk_subset_ttc_candidate.py`: the shipped tier-E font five times, in the original TTC's face order
(JP KR SC TC HK), with only the `name` table differing (family, full and PostScript names, and each face's own language
records as in the original TTC; the TC face keeps the shipped subset's table), saved as one collection with shared tables.
7,210,328 bytes against 7,200,632 (+9,696); two builds byte-identical; every face's cmap, hmtx, vmtx, hhea, OS/2, CFF, GSUB and
GPOS equal to the shipped subset's (checked by the tool); fontconfig reports the five families. Glyph coverage, outlines and
metrics are therefore exactly tier E's, and spec section 19's registered loss becomes true as written: text naming SC/JP/KR/HK
draws Traditional Chinese forms at the line height it had on v8.

`font-slots-ttc5/` (v8 against the candidate): all 16 pitches equal, **all 32 line tops identical**, and the default Asian font
written is `Noto Sans CJK KR` in every document, as on v8.

## 4. Product-path on the candidate

`tools/run_e2_c_product_path.py --profile e2-editor-v15-cjk-ttc5-ab`, one round per browser (run by a subagent, sequentially,
nothing else running): `e2-editor-v15-cjk-ttc5-ab-{firefox,chrome}-r1.json`.

| | Firefox | Chrome |
|---|---|---|
| totals (PASS/FAIL/NE), `complete`, last state, page errors | 30 / 1 / 11, true, ready, none | 40 / 0 / 2, true, ready, none |
| check outcomes differing from the full-TTC A/B profile | **none** | **none** |
| caret line `inkLeft`/`inkRight`/`inkSpan`, `strokeLost` | 101 / 627 / 526, 19 | 82 / 505 / 423, 14 |
| recovery arm `bandsAtInducer`, caret height, 038 reproduced | as v8, 24, true | as v8, 20, true |
| `a-boundary-arrow-press-does-not-cost-the-work` | NE (no CDP, as on every profile) | PASS; press answered, state `ready`, B4 by `worker-failure` |

Addendum 2's predictions held: no CJK-variant pitch differs from v8's and neither report differs from the A/B profile's in any
check outcome. The Firefox FAIL is `an-inline-format-reaches-a-selection`, which fails on v8 and on every profile here.

## 5. What this does and does not settle

- Settled: findings A and B of `../product-path/README.md` are the CJK pack (finding 113), and on these cells v15's engine
  changes are clean; the candidate restores v8's layout on everything measured at +9,696 bytes.
- Not settled: whether to adopt the candidate (a new CJK pack is a new profile identity; no relink) -- the owner's decision.
  Spec section 19's tile criterion ("tiles identical wherever the page's characters are in tier E") cannot hold as written on
  documents tagged Japanese/Simplified/Korean even with the candidate (they draw Traditional forms by design), so it needs
  amending before it is run. One round per browser here; the counted product-path rounds on whatever profile ships are separate.

# Counted corpus layout comparison, v17 vs v17-cjk-r5-ab (spec 26.3 V6; 21.2 as amended by 27): result

Run 2026-10-08 01:00:59-01:46:08 (+08:00) by `../followon.sh`, after the product-path chain and the merge shakedown, one tool at a time; per `PREDICTION.md` (committed `127775ee` before the run). Tool `compare_layout_corpus.py` sha256 `21f90c31…` before and after (`tool-sha-*.txt`); exit 0, stderr empty; `ps-before.txt` / `ps-after.txt`. Reader `judge.py` (committed `d6db60ea` before the run, red cases in `selftest-output.txt`); output `judge-output.txt`.

## Verdict: **RED** (one document)

- **K1 MISSED.** `judge.py`: documents 76, not comparable 5, not measured 23, measured 48; 47 of 48 within T = 2 px; **`test-docs/e1/paragraph-content.odt` red**: 27 bands in both arms, maximum top difference 4 px.
- **K2 HIT.** Not comparable: the same 5 in both arms and the same 5 as the dry run (`l3-bad-central-directory`, `l3-high-ratio`, `l3-too-many-entries`, `l3-truncated`, `r7-corrupt-truncated`).
- **K3 HIT.** Not measured: 23 in both arms, the dry run's set exactly (judge's 27.3 note "same set: True"). Measured: 48 (21 with CJK characters).
- **K4 MISSED.** Besides the red document, 8 measured documents differ by 1 px (within T; listed in `judge-output.txt`, the CJK-heavy `t3-long` family and `r7-finding-012/t2-keep-*`).
- Cross-check against the tool's own `comparison.json`: AGREE (71 comparable, 60 identical).
- Observed beside the verdict: all 48 measured documents on v17 are band-for-band identical to the dry run's v16 session 1. Removing 35 moved nothing the corpus measures (the corpus has no measured document whose CJK text names a font that needs substitution).

## The red document

`paragraph-content.odt` is a project fixture (`wasm_sdk_probe/test-docs/e1/`, no private text). Bands 0-9 are equal; from band 10 every band of the control arm sits 3 px lower (one 4 px), until the page-bottom bands 24-26, which are equal: one line above band 10 is 3 px taller in the control. v17's bands equal the dry run's v16 here, so it is the full-TTC arm that differs.

Matching band heights to the fixture's paragraphs (24 pt Title = band 12, 14 pt Subtitle = band 13, and so on upward), band 10 is `PC-PRE preformatted paragraph`, style `Preformatted Text`, ASCII only. **The prediction's named risk (Korean punctuation advances) is not it: the first differing line has no CJK character.**

Read, not measured (the discriminator is the next step, not done here):

- The two CJK packs differ in family names: `cjk-sub-e5` holds 5 faces (Noto Sans CJK JP/KR/SC/TC/HK); `cjk-r5` holds 10, the same 5 plus **Noto Sans Mono CJK JP/KR/SC/TC/HK** (fontTools on the shipped pack bytes).
- `Preformatted Text` (`SwPoolFormatId::COLL_HTML_PRE`) takes its fonts from `DefaultFontType::FIXED` (`sw/source/core/doc/DocumentStylePoolManager.cxx:1419-1421`); for zh-TW that list is 「思源黑體 HW;Source Han Sans HW TC;Noto Sans Mono CJK TC;細明體;MingLiU;Liberation Mono;…」 (`officecfg/registry/data/org/openoffice/VCL.xcu`). With the full TTC the Asian slot can be Noto Sans Mono CJK TC; with the subset the first installed name is Liberation Mono.
- Hypothesis H-mono (NOT VERIFIED): the Asian slot of that paragraph is Noto Sans Mono CJK TC in the control and Liberation Mono in v17, and the Asian slot's metrics enter the height of a Latin-only line (V4's LATIN-TC 16 px against LATIN-KR 15 px is the same kind of effect).

## What this means for 26.3

V6's corpus part is **not met** (21.2: that document is red; the prediction: "26.3 V6 is not met until it is explained. Not adjusted."). This is a property of the CJK subset (v15 onward), not of v17's fix: v16 has the same `cjk-sub-e5`, and the dry run could not see it because all three of its arms were subsets.

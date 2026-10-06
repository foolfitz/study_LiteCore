# CJK glyph subset — instruments and predictions (written 2026-10-07, before any subset was built)

Why: the owner chose option D (keep bundled fonts, subset the CJK font; `research/RESEARCH-2026-10-06-wasm-size-status.md` §7), fontTools as a build dependency, and to ship the subset with v15. The CJK pack is 25% of the first open (12.17 MB zstd of 48.53 MB). This round measures what each coverage tier costs and whether the subset draws exactly what the full face draws; the owner chooses the tier from these numbers.

## Instrument (this commit)

`wasm_sdk_probe/tools/build_cjk_subset.py`: takes face 3 ("Noto Sans CJK TC") of the TTC inside the shipped `cjk-r5.b76b0433….data`, subsets it with fontTools (all layout features except `locl`, all names, `.notdef` kept), and checks:

- **coverage** — every code point of the tier that the original face maps, the subset maps to the same glyph (CID name);
- **identity** — every kept glyph has the original's decomposed outline and horizontal/vertical metrics;
- **corpus** — every code point used in the corpus documents (`content.xml` + `styles.xml` text) that the original face can draw, the subset can draw; misses listed per document. Corpus: `wasm_sdk_probe/test-docs/` (all `.odt/.fodt/.ods`) and the owner's `PMPC指南.odt` (not in the repository; read only). An empty corpus is a failure.

Red cases (`--self-test`, on a built tier): a required code point dropped from the cmap; an advance width changed; one glyph's charstring replaced by another's — each must be caught. Run before the counted build.

Tiers (intersected with what the TC face maps): **C** Latin/Greek/Cyrillic, punctuation, symbols, box drawing, Bopomofo, fullwidth, CJK radicals/compatibility blocks, Big5, HKSCS; **E** C + kana + all of U+4E00–U+9FFF; **F** E + GBK + Extension A + Hangul.

## Predictions

Basis: fable's derivation from the CFF charstrings (§7.2 of the research file), which assumed local subroutines kept whole (upper bound) and a narrower base set (Latin/punctuation/Bopomofo/fullwidth/Kangxi only). This tool's base set is wider (Greek, Cyrillic, math, box drawing, dingbats) and fontTools keeps the GSUB closure (vertical alternates), so glyph counts should come out somewhat above fable's and sizes near the top of its ranges.

| tier | fable's glyphs | fable's zstd | predicted here |
|---|---:|---:|---|
| C | 18,904 | 3.8–4.3 MB | glyphs 19,000–21,000; zstd 3.8–4.7 MB |
| E | 24,576 | 4.8–5.4 MB | glyphs 24,600–27,000; zstd 4.8–5.9 MB |
| F | 42,139 | 6.9–7.7 MB | glyphs 42,000–45,000; zstd 6.9–8.4 MB |
| full TC face (reference) | 65,535 | 12.0 MB | — |

- coverage and identity: 0 failures on every tier (fontTools keeps charstrings; outlines are compared decomposed).
- corpus: tier E and F miss nothing; tier C misses nothing in `test-docs/`, and at most a handful of code points in the owner's document (a Taiwanese government guide; anything outside Big5/HKSCS would be a rare personal-name or Extension character).
- red cases: all three caught.

## What would change the decision

- Any identity failure: the subset does not draw what the full face draws — stop; find out why before choosing a tier.
- Tier C missing characters in the owner's document: C is not safe for real documents; E becomes the floor.
- Sizes far above the ranges (say C over 6 MB zstd): the saving no longer justifies the coverage loss against E; re-derive.
- As predicted: present C/E/F with sizes and corpus misses to the owner; the chosen tier becomes the v15 profile's CJK pack (a re-pack, no relink).

## Amendment (2026-10-07, after an uncounted shakedown, before the counted run)

**Shakedown, not counted** (`wasm_sdk_probe/build/cjk-subset/try-C.json`, tier C only, corpus `test-docs/` — 385 documents, 3 deliberately broken fixtures skipped and listed): with "all layout features except `locl`", tier C kept **37,118 glyphs for 20,089 code points, 10.54 MB raw, 7.78 MB zstd** — far outside the prediction. The GSUB closure pulled in the alternates of optional features: the TC face's GSUB has `aalt` (access all alternates), `fwid`/`hwid`/`pwid`, `ruby`, `dlig`, `hist` besides the default ones.

**What forced the change, read from source:** LibreOffice shapes with HarfBuzz's default features only, adding just the features named in the font name (`vcl::font::FeatureParser`) and switching kerning/ligatures off (`vcl/source/gdi/CommonSalLayout.cxx:446–462`; vertical runs check `vert`, `:319–336`). None of the optional features above is applied unless a document names it in a font name.

**Instrument change:** layout features = fontTools' default set (it mirrors shapers' defaults plus the vertical features) minus `locl`. The instrument description above ("all layout features except `locl`") is superseded by this line. Registered consequence: a document that names an optional feature (e.g. `Noto Sans CJK TC:fwid`) gets default forms for glyphs not kept.

**Predictions for the corrected policy** (the shakedown measured the old policy only): the table above stands as written — C glyphs 19,000–21,000 / zstd 3.8–4.7 MB; E 24,600–27,000 / 4.8–5.9; F 42,000–45,000 / 6.9–8.4. Coverage and identity 0 failures. The shakedown's 7 corpus documents with misses at tier C are expected to remain at C (code points outside Big5/HKSCS in test fixtures, e.g. kana or Hangul) and to drop at E or F.

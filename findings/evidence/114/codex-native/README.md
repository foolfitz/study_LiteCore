# Finding 114: native LibreOffice reproduction with and without 35 (from the codex review)

Made by the independent review in `../../../114-review-2026-10-08-codex.md` (2026-10-08, files written under `/tmp/litecore-review114-*`), imported here unchanged so they survive a reboot. The main session re-read the raw outputs before importing and checked them against the review's table (they agree).

## What it is

One native LibreOffice build (`native-lok-26-8/build/instdir`), one fixture, two fontconfig rule sets that differ by exactly one file:

- `fixture.fodt` (`setup.py` writes it): four paragraph styles, each used twice, all tagged Asian language zh-TW, Western font Liberation Sans: (a) Asian font `思源黑體` 12 pt (not installed under that name), (b) `Noto Sans CJK TC` 12 pt (installed), (c) `思源黑體` 18 pt, (d) a Latin-only control 12 pt.
- Fonts: the 13 files extracted from the shipped `e2-editor-v16` packs (`fonts-MANIFEST.json`: base `ba15a988…`, CJK `cjk-sub-e5` `ce59153d…`).
- Rules: `with35/` = the v16 pack's 22 conf.d files (`with35/conf.d.sha256` equals `wasm_sdk_probe/build/wasm-fontset-v16/conf.d`, checked); `without35/` = the same minus `35-lang-normalize.conf` (checked). Each `fonts.conf` includes its conf.d by absolute path.
- `native.cpp`: a new `main` around the existing native merge probe (`wasm_sdk_probe/tools/merge_native_boundaries.cpp`, included, its `main` renamed): open the fixture, find each paragraph, read the caret rectangle.

## Result (`with35/stdout.txt`, `without35/stdout.txt`; caret `x, y, width, height` in twips)

| paragraph | with 35 | without 35 |
|---|---|---|
| 思源黑體 12 pt | height 276, second copy 276 below | height 348, 348 below |
| Noto Sans CJK TC 12 pt | 348 | 348 |
| 思源黑體 18 pt | 414 | 521 |
| Latin control 12 pt | 276 | 276 |

All 8 searches matched in each arm. With `FC_DEBUG=1024` both processes printed the rule files they loaded (top of each `stdout.txt`): their own `fonts.conf`, its conf.d (with or without 35), and LibreOffice's own `instdir/share/fonts/truetype/fc_local.conf`, in both arms; no `/etc/fonts` file.

## Limits

- Both processes die with a signal during process-exit cleanup (`stderr.txt`: libc exit handlers, SystemClipboard), after the measurements were printed. Neither run is labelled PASS.
- The fonts are the WASM profile's, so this shows the rule file's effect inside native LibreOffice, not what a stock desktop install does.
- `fc_local.conf` (and OpenSymbol) are loaded in both arms; the single variable is 35.

# Result: why WASM gives a Latin line height to "思源黑體" tagged zh-TW (finding 114)

Run 2026-10-07 21:05 +0800, Chrome, `wasm_sdk_probe/tools/probe_fc_debug.py` at `58c512cf` (prediction committed in the same commit, before the run). Output: `run1/` (`fc-debug.json`, raw logs `e2-editor-v8-fc-log.txt` / `e2-editor-v16-fc-log.txt`, canvas PNGs, the fixture). The shipped loaders' sha256 are the same before and after (`shipped-loaders-before.txt`); nothing in `dist/` was written. Native reproduction: `native-repro/`.

## Against the prediction

| Item | Outcome |
|---|---|
| C0 instrument alive | **HIT.** v8 9,257 / v16 7,486 forwarded lines. `/instdir/share/fontconfig/fonts.conf` and all 22 conf.d files load (`Loading config file ... done`), the profile's font files are scanned, 41 / 40 `Match` blocks. |
| C1 layout positive control | **HIT** after removing the page frame's two 1-row runs (y 15, y 914), the same rule `../../v15-shakedown/cjk-ab/font-slots-r3/pitches.txt` states; the probe's own `pitches()` does not remove them, so its `pitch` table is absent and the numbers were computed from `pitches.runs`. Both profiles: TW-TC 20, TW-DEFAULT 20, SLOT-TC 20, TW-SIYUAN 16, TW-PMINGLIU 16, TW-XIMINGTI 15, TW-KAI 16, LATIN-DEFAULT 16 (113's numbers). |
| C2 the question | **R-b's observation hit, its stated cause missed.** Every `思源黑體` request, on both profiles, reaches fontconfig (so not R-a) with `lang: "tw"(s)` and no `zh-tw` (so not R-c or R-d as written). But LibreOffice did not lose the language: fontconfig's own config rewrote it (below). R-b's text named `mapToFontConfigLangTag` / `meLanguage` as the place; that part is wrong. |
| C3 config | Recorded: the full config loads; `familylang`/`namelang` are `zh-TW`, i.e. the engine's environment locale is zh-TW. No `Fontconfig error` on stderr. |

Per profile, the six `思源黑體` blocks in the fixture phase alternate: two answer **Liberation Sans** (`LiberationSans-Regular.ttf`), four answer **Noto Sans CJK KR** (TTC index 1; v8's full TTC, v16's subset). Which lookup is which (primary font vs glyph fallback) is not recorded by this probe; the line height says the primary is the Latin one.

## The mechanism (reproduced natively, one variable)

1. `PrintFontManager::Substitute` adds the font's language with `FcPatternAddString(pPattern, FC_LANG, "zh-tw")` (`vcl/unx/generic/fontmanager/fontconfig.cxx`, around line 1139): a **string** value.
2. The profile's `conf.d/35-lang-normalize.conf` (fontconfig 2.18.2's, 258 rules) has, for every language code, `<test name="lang" compare="contains"><string>tw</string></test><edit name="lang" mode="assign" binding="same"><string>tw</string></edit>` ("tw* -> tw"). When both sides are strings, `FcConfigCompareValue` implements `contains` as `FcStrStrIgnoreCase` (`src/fccfg.c:1134`), a substring test. `zh-tw` contains `tw`, and `tw` (Twi) sorts before `zh`, so the value becomes `tw`.
3. With `lang=tw`, a Latin-script language, the best match is a Liberation face; the CJK glyphs still come from glyph fallback, so the text is drawn and only the line height shows it.

`native-repro/fc_string_lang.py` asks fontconfig exactly that way (string `FC_LANG`, then `FcConfigSubstitute`, `FcDefaultSubstitute`, `FcFontMatch`) with v16's 13 font files:

| Config | fontconfig | `zh-tw` | `zh-cn` | `zh-sg` | `pt-br` | `fr-ca` |
|---|---|---|---|---|---|---|
| `build/wasm-fontset-v16/fonts.conf` as extracted (relative `<include>conf.d</include>`) | LO's bundled 2.18.2 / system 2.17.1 | stays `zh-tw` -> Noto Sans CJK TC | stays | stays | stays | stays |
| same, `<include>` with the **absolute** path of the extracted conf.d (`fonts-abs-include.conf`) | LO's bundled 2.18.2 / system 2.17.1 | **`tw`** -> Liberation Mono | stays | **`sg`** | **`br`** | **`ca`** -> Liberation Mono |

(Full outputs: `relative-include.*.txt`, `absolute-include.*.txt`.) The family differs from WASM's (Mono vs Sans) because this pattern carries no weight/width/generic family; the rewrite is the same.

## What this corrects in finding 114

The native R0c rerun with `FONTCONFIG_FILE=build/wasm-fontset-v16/fonts.conf` did **not** use the profile's rules. A relative `<include>conf.d</include>` resolves against fontconfig's default config directory, not the including file's: the rule files loaded were `/etc/fonts/conf.d/*` (61 files, `relative-include.rule-files.txt`), against the profile's 22 with the absolute include (`absolute-include.rule-files.txt`). This machine's `/etc/fonts/conf.d` has no `35-lang-normalize.conf` (`system-etc-fonts-conf.d.txt`). The `strace` positive control was about font files (7 opened) and could not see this: it showed the font set was restricted, not that the rule set was. So "same font files and same fontconfig, different result, therefore the WASM engine" was wrong; with the same rules native does the same thing, and the cause is the profile's fontconfig rule file meeting LibreOffice's string `FC_LANG`.

The same also applies to the `fc-match` rows written in `PREDICTION.md` under "What is already measured": those used the relative include, i.e. the system rules (and `fc-match` parses `:lang=zh-tw` as a langset, which `contains` treats as language containment, not substring).

## Not done

- Which distributions enable `35-lang-normalize.conf` for desktop LibreOffice (where the same rewrite would happen natively) is not checked.
- No fix is made or measured here. The candidates are listed in finding 114.

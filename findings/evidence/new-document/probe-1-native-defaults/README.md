# Probe 1: what a style-less ODT becomes when LibreOfficeKit loads and saves it (native 26.8)

Companion to `../analysis-1.md` (brief 1, new-document line). Run 2026-10-14 by the analysis
session; no product bytes touched.

## What was run

`tool/lok_defaults_probe.cpp` is a 40-line LibreOfficeKit client: `lok_init_2(install, profile)`,
then `documentLoad(url)` or `documentLoadWithOptions(url, options)`, then `saveAs(out, "odt", nullptr)`
(the same `saveAs` shape as `wasm_sdk_probe/src/probe_engine.cpp:6069`). Compiled with the recipe
of the repo's native harnesses (`wasm_sdk_probe/Makefile:2710`):

```
g++ -std=c++17 -O2 -I libreoffice-26-8/include lok_defaults_probe.cpp -ldl -o lok_defaults_probe
```

Engine: `native-lok-26-8/build/instdir/program` (git HEAD `96dd0fce49d9bd094701d3dae55b81dba22ba8fb`,
`libsofficeapp.so` sha256 `9ad354649f183fd31982c24c4b5af9dbbfec07cc980dc789f1b57bb08ec1947c`).
Input: richdocuments 8.7.3 `emptyTemplates/template.odt` (1,268 bytes, sha256 in `SHA256SUMS`), whose
`styles.xml` carries one `style:default-style` with only `style:use-window-font-color="true"`: no
language, no font, no page layout.

Each arm ran in its own process with a fresh, empty user profile (`-env` via `lok_init_2`), with
`LC_ALL`, `LANGUAGE`, `LC_CTYPE`, `LC_PAPER`, `PAPERSIZE` unset and `SAL_USE_VCLPLUGIN=svp`.

| arm | `LANG` | load options | models |
| --- | --- | --- | --- |
| A | `zh_TW.UTF-8` | none | the owner today: a zh-TW browser, no `Language=` |
| B | `en_US.UTF-8` | none | a user whose browser is English |
| C | `C.UTF-8` | none | Emscripten's fallback when `navigator.language` is absent |
| D | `en_US.UTF-8` | `Language=zh-TW` | candidate (b): English browser, Nextcloud language zh-TW |
| E | `zh_TW.UTF-8` | `Language=en-US` | the inverse control |
| F | `zh_TW.UTF-8` | `Language=zh-TW` | candidate (b) on the owner's machine |
| G | `en_US.UTF-8` | `Language=zh-CN` | shows the tag selects the Asian language, not the fonts |

## Result (`extract-output.txt`, produced by `tool/extract.py` from `styles/*-styles.xml`)

| arm | Western / Asian / Complex language | default fonts (W / A / C) | page | registry after the run |
| --- | --- | --- | --- | --- |
| A | en-US / **zh-TW** / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | **8.5in x 11in (Letter)** | `ooSetupSystemLocale=en-US ooLocale=en-US` |
| B | en-US / **zh-CN** / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Letter | en-US / en-US |
| C | en-US / zh-CN / hi-IN | same as B | Letter | en-US / en-US |
| D | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | **21.001cm x 29.7cm (A4)** | **zh-TW / zh-TW** |
| E | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | Letter | en-US / en-US |
| F | en-US / zh-TW / hi-IN | same as A | A4 | zh-TW / zh-TW |
| G | en-US / zh-CN / hi-IN | same as B | A4 | zh-CN / zh-CN |

Hashes: B and C are byte-identical `styles.xml`; A and E are byte-identical. See `SHA256SUMS`.

## How to read it

- The registry column is the discriminating one. Without `Language=`, the profile ends the run with
  `ooSetupSystemLocale=en-US` although `LANG` said `zh_TW`: LibreOfficeKit writes it itself at init
  (`desktop/source/lib/init.cxx:8347`, `setLanguageAndLocale(u"en-US"_ustr)`). Paper is derived from
  that key (`i18nutil/source/utility/paper.cxx:231`), which is why arm A is Letter on a zh_TW host.
- The Asian language still followed `LANG` (A: zh-TW, B/C: zh-CN) because `desktop::langselect::prepareLocale`
  (`desktop/source/app/langselect.cxx:70-75`) reads the environment locale through the LocaleBackend and
  sets `MsLangId::setConfiguredAsianFallback`. `Language=` does not clear that fallback: arm E keeps zh-TW.
- The default fonts never moved with the language. They are pool defaults computed once per process
  with `LANGUAGE_ENGLISH_US` (`editeng/source/items/textitem.cxx:2927-2952`); the Asian slot resolves
  through VCL's `en` UI font list to whatever the font collection substitutes. On this host that is
  DejaVu Sans; on the WASM profile finding 113 measured `Noto Sans CJK KR` for the same slot.
- The Complex font (Noto Sans CJK TC vs Noto Sans Arabic UI) is fontconfig's locale-sensitive
  substitution on this desktop host and is not transferable to the WASM image (13 Latin faces plus one
  CJK TTC).
- Native paper is not a proxy for WASM paper when `ooSetupSystemLocale` is empty (glibc `LC_PAPER` and
  `paperconf` are consulted natively, neither exists on Emscripten), but here the key is never empty,
  so the Letter/A4 readings do transfer.

## Files

- `tool/lok_defaults_probe.cpp`, `tool/extract.py`, `tool/input-template.odt`
- `styles/<arm>-styles.xml`: the saved `styles.xml` of each arm
- `registry/<arm>-registrymodifications.xcu`: the profile each arm left behind
- `logs/<arm>.stdout`, `logs/<arm>.stderr`: the probe's output (stderr is nine `SAL_WARN` lines per arm,
  two of them `MsLangId::getConfiguredSystemLanguage() - not configured yet`, which is the pre-init read)
- `extract-output.txt`, `SHA256SUMS`

# Parser check for `tools/probe_fc_debug.py`

Two real fontconfig debug logs, produced natively (system fontconfig 2.17.1; same `FcPatternPrint` / `FcFontSetMatch` print code as the bundled 2.18.2), used as the reader's known answers by `wasm_sdk_probe/tests/test_probe_fc_debug.py`. Absolute font paths are replaced by `FONTS/`.

| File | Command (cwd `/tmp`, `LANG=C`, `FC_DEBUG=1`) | Known answer |
|---|---|---|
| `native-full-config-zh-tw.txt` | `FONTCONFIG_FILE=build/wasm-fontset-v16/fonts.conf fc-match '思源黑體:lang=zh-tw'` | asked `思源黑體`, lang `zh-tw` then `en`; best `Noto Sans CJK TC`, TTC index 3, langset has `zh-tw` |
| `native-bare-config-en.txt` | `FONTCONFIG_FILE=bare-fonts.conf fc-match '思源黑體:lang=en'` (only `<dir>` = v16's 13 font files, no conf.d) | asked `思源黑體`, lang `en`; best `Liberation Mono`, langset without `zh-tw` |

The reader's first version failed on the first file twice: it read the asked lang as `['en']` (langset values are printed unquoted: `lang: zh-tw(s) "en"(w)`) and lost the best match's `lang` (a charset dump ends with a bare `(s)` line, which stopped the tab-prefixed collection). Both were fixed before any WASM run.

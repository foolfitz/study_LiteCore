# Native round trip of the blank-document templates (SPEC-M3-new-document N11)

Run 2026-10-14 by `wasm_sdk_probe/tools/check_new_document_native.py` against native 26.8
(`native-lok-26-8/build/instdir`; `libsofficeapp.so` sha256 in `report.json`). No product bytes touched.

## What was run

The analysis session's LibreOfficeKit client (`../probe-1-native-defaults/tool/lok_defaults_probe.cpp`:
`lok_init_2`, `documentLoad`, `saveAs(out, "odt", nullptr)`), compiled with the repo's native-harness recipe,
loaded four of the host's generated templates (`~/Projects/Nextcloud_Apps/litecore/blank/`, MANIFEST sha256 in
`report.json`) and saved each as ODT, once under `LANG=en_US.UTF-8` and once under `LANG=zh_TW.UTF-8`.
Each arm: its own process, a fresh empty profile, `LC_ALL`/`LANGUAGE`/`LC_CTYPE`/`LC_PAPER`/`PAPERSIZE` unset,
`SAL_USE_VCLPLUGIN=svp`.

Control: richdocuments' style-less `template.odt` (`../probe-1-native-defaults/tool/input-template.odt`) under
the same two environments.

## Result

| template | `LANG` | saved W / A / C | saved fonts (W / A / C) | saved page | verdict |
| --- | --- | --- | --- | --- | --- |
| `en-US_zh-TW_A4` | en_US | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | 210.01 x 297 mm (A4) | PASS |
| `en-US_zh-TW_A4` | zh_TW | same | same | A4 | PASS |
| `en-US_zh-TW_Letter` | en_US | en-US / zh-TW / hi-IN | same | 215.9 x 279.4 mm (Letter) | PASS |
| `en-US_zh-TW_Letter` | zh_TW | same | same | Letter | PASS |
| `en-US_ja-JP_A4` | en_US | en-US / ja-JP / hi-IN | Liberation Serif / Noto Sans CJK JP / Liberation Sans | A4 | PASS |
| `en-US_ja-JP_A4` | zh_TW | same | same | A4 | PASS |
| `de-DE_zh-TW_Letter` | en_US | de-DE / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Letter | PASS |
| `de-DE_zh-TW_Letter` | zh_TW | same | same | Letter | PASS |
| control (richdocuments) | en_US | en-US / **zh-CN** / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Letter | the environment shows |
| control (richdocuments) | zh_TW | en-US / **zh-TW** / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | Letter | the environment shows |

8 of 8 arms keep every stated default; the control's Asian language follows `LANG`, so the instrument sees
the environment the templates are claimed to override. `N11 PASS`.

The registry each arm left behind still says `ooSetupSystemLocale=en-US` (LibreOfficeKit's forced en-US):
the template wins over the engine's own belief, which is the point.

## Files

- `report.json`: every arm's raw record (probe stdout, saved size, the `describe()` reading, departures, registry).
- `styles/<template>-<lang>-styles.xml`: the saved `styles.xml` of each arm; `styles/control-<lang>-styles.xml` for the control.

Reader: `make_new_document_templates.describe()` / `compare()` (the same code the WASM runner uses for N6).

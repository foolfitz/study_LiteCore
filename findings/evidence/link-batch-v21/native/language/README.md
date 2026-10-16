# `Language=` characterised natively (link batch v21, plan §2.6–2.7, step 1c)

Run 2026-10-16 for `handoff/PLAN-2026-10-16-link-batch-v21.md` §4 step 1c. This is **not** going into the next link. These are measurements for a later owner decision on `Language=` (with the pins) and D12. No product bytes, profile, `make`, Makefile, `wasm_sdk_probe/src`, `dist`, `build`, shell, page, SDK, core tree or Nextcloud app was touched; no browser was used.

**Labels.** **observed**: read from this run's stored output. **inferred**: reasoned from source or from other evidence, not measured here. **not run**: not attempted.

## Answers

### Q1. `LANG=de_DE.UTF-8` + `Language=zh-TW`: saved Western default is **en-US** (observed). analysis-1's de-DE claim does not hold; the fact sheet's reading of `langselect.cxx:139-141` does.

- `Q1-deDE-zhTW` saves `en-US / zh-TW / hi-IN`, A4, in both runs. Its `styles.xml` is byte-identical to the en_US environment with the same option (`Q2-zhTW`) and to probe-1 arm D (`b21957cd…`).
- **The environment really reached LibreOffice (observed).** The LocaleBackend value `System/L10N/Locale` read inside the process is `"de-DE"`. Even so, the effective Western fallback after init is en-US.
- **The instrument can show de-DE (observed).** Mutation control `M1` forces the Western fallback to de-DE after init (`MsLangId::setConfiguredWesternFallback`), then makes the same load and save. The saved Western slot reads `de-DE`. So `en-US` in Q1 is a reading, not the only value this path can print.
  - Side result: pinning a fallback after `lok_init_2` and before the load takes effect natively (Western only; Asian and Complex pins **not run**).
- **Control `LANG=de_DE.UTF-8`, no option (observed):** `en-US / zh-CN / hi-IN`, Letter. It is byte-identical to `LANG=en_US`, no option (`b4724ec0…`, probe-1 B). A Latin-script environment leaves no trace in a style-less save.
- **The fallback readout cannot tell "unset" from "set to the built-in default"** (en-US / zh-CN / hi-IN). Source says `:139-141` sets the Western fallback to the system language (en-US) [inferred]; the outcome is the same either way.

### Q2. D12: `Language=en` gives **A4**, `Language=en-US` gives **Letter** (observed). The fact sheet's `paper.cxx` reading holds.

| option (`LANG=en_US`) | saved W / A / C | page | lengths written in | registry after run | LOK tag after load |
| --- | --- | --- | --- | --- | --- |
| none | en-US / zh-CN / hi-IN | Letter | inch | en-US / en-US | `zxx` (none) |
| `Language=en` | en-US / zh-CN / hi-IN | **A4** | **inch** | `en` / `en` | `en` |
| `Language=en-US` | en-US / zh-CN / hi-IN | **Letter** | inch | en-US / en-US | `en-US` |
| `Language=en-GB` | en-GB / zh-CN / hi-IN | A4 | cm | en-GB / en-GB | `en-GB` |
| `Language=de` | **de-DE** / zh-CN / hi-IN | A4 | cm | `de` / `de` | `de` |
| `Language=zh-TW` | en-US / zh-TW / hi-IN | A4 | cm | zh-TW / zh-TW | `zh-TW` |
| `Language=xx_bad!` | en-US / zh-CN / hi-IN | Letter | inch | en-US / en-US | `zxx` |
| `Language=zh_TW` (underscore, extra arm) | en-US / zh-CN / hi-IN | Letter | inch | en-US / en-US | `zxx` |

- **`en` versus `en-US` (observed).**
  - The registry stores the raw tag. `paper.cxx:232`, `:362-366` split it at the first `-`, so `en` has an empty country and gets A4.
  - The Western language is en-US for both: `makeFallback` turns `en` into en-US.
- **`en` is a mixed state (observed).** The paper is A4, but the locale data is en-US: the currency is USD and lengths are written in inches (see "Lengths" below).
- **`en-US` is identical to no option (observed).** `styles.xml` and `content.xml` are byte-identical to no option; only the LOK tags differ.
- **Positive control (observed).**
  - The invalid tag `xx_bad!` is **ignored silently** (`init.cxx:2848`, `isValidBcp47`). Every saved byte, every readout and the registry equal the no-option run, and the LOK tag stays `zxx`. Paper is the visible tell: Letter, where a taken tag of a non-Letter country gives A4.
  - **`zh_TW` with an underscore is ignored the same way.** Nextcloud's `data-locale` uses underscores (fact sheet b7). A tag taken from it unconverted would be dropped with no error, so a host design must convert or reject it [inferred from the observation].
- **D12 in one line (observed natively):** whether `en` users get A4 or Letter from the engine path is purely the page or host's choice between sending `en` or `en-US`. LOK maps neither to the other.

### Q3. Template-made documents under `Language=`: **semantically unchanged** (observed). **Byte-identical under `en-US`; under `ja`, only the length unit changes** (observed).

Templates: `en-US_zh-TW_A4.odt` (`7e6221b6…`) and `en-US_zh-TW_Letter.odt` (`23f8b70d…`), copied from `~/Projects/Nextcloud_Apps/litecore/blank/`. Both hashes match its `MANIFEST.json` (`e5cdb8e2…`). Loaded with `LANG=en_US`, nothing typed, saved.

| template | option | saved W / A / C | saved fonts W / A / C | page (mm) | `styles.xml` = no-option save | `content.xml` = no-option save | overrides of the defaults |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A4 | none | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | 210 × 297 | — | — | none |
| A4 | `en-US` | same | same | 210 × 297 | **yes** (bytes) | yes | none |
| A4 | `ja` | same | same | 210 × 297 | **no**: units only | yes | none |
| Letter | none | en-US / zh-TW / hi-IN | same | 215.9 × 279.4 | — | — | none |
| Letter | `en-US` | same | same | 215.9 × 279.4 | **yes** (bytes) | yes | none |
| Letter | `ja` | same | same | 215.9 × 279.4 | **no**: units only | yes | none |

- **The templates' stated defaults survive (observed).** Languages, fonts and page match the template (`summary.txt`, section "Q3"). The page is resolved through `master-page[@style:name='Standard']`, not the first page-layout.
- **No overrides anywhere (observed).** No `style:text-properties` in `styles.xml` or `content.xml` sets a language, country or font name that differs from the default.
- **What `ja` changed (observed).** It changes three places, and only the unit: the graphic default-style's shadow and line-spacing offsets, the line-numbering offset, and the `Mpm1` page-layout properties. For example, `8.2681in` became `21.001cm`, and `8.5in` became `21.59cm`.
  - **Mechanism [source]:** the Writer export unit is `SwModule::GetMetric` (`sw/source/filter/xml/xmlexp.cxx:192-197`). That comes from `SwMasterUsrPref`, which picks cm for a metric locale and inch otherwise (`sw/source/uibase/config/usrpref.cxx:46-51`, `SvtSysLocale().GetLocaleData().getMeasurementSystemEnum()`).
  - `Language=` moves that locale (see Q5's readouts).
  - The A4 template's `21cm` already saves as `21.001cm` (`8.2681in`) with no option; that rounding is not caused by `Language=`.
- **Consequence for the next count (inferred, not run on WASM).**
  - Byte pins on WASM-saved `styles.xml` move as soon as v21 passes a metric-locale tag (zh-TW, ja, de, en-GB, …): 0.2.19's `5addf7dc…` / `09d2dd95…` (`specs/SPEC-M3-new-document.md:245-250`) and anything like them. The content does not change.
  - Tags `en-US` and `en` keep inches.

### Q4. Asian and Complex fallbacks (observed)

| arm | `LANG` | option | saved W / A / C | page | paragraph-default fonts W / A / C | graphic-default fonts W / A / C |
| --- | --- | --- | --- | --- | --- | --- |
| Q4-jaJP-none (control) | ja_JP | none | en-US / **ja-JP** / hi-IN | Letter | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans CJK JP |
| Q4-jaJP-enUS | ja_JP | `en-US` | en-US / **ja-JP** / hi-IN | Letter | same | Liberation Serif / DejaVu Sans / Noto Sans |
| Q4-enUS-ja | en_US | `ja` | en-US / **ja-JP** / hi-IN | A4 | same | **Noto Serif CJK JP / Noto Serif CJK JP / Noto Sans CJK JP** |

- **The browser's Asian language survives a Western tag (observed).** With `LANG=ja_JP`, the Asian fallback read after init is ja-JP, and `Language=en-US` does not clear it: the save is ja-JP. This is the ja version of probe-1 arm E (zh_TW).
- **Complex stays hi-IN everywhere (observed).** No arm had a complex-script environment.
- **Same languages, different saves (observed).** "ja browser + `en-US` tag" and "en browser + `ja` tag" save the same three languages but differ in paper (Letter / A4), in length unit, and in the graphic default fonts.
- **Paragraph-default fonts: `Language=` never moved them in any arm (observed).** They are pool defaults computed with a fixed `LANGUAGE_ENGLISH_US` (analysis-1 D2).
  - The Asian `DejaVu Sans` and Complex `Noto Sans Arabic UI` are this desktop's fontconfig substitutes and do not transfer to WASM (finding 113 measured `Noto Sans CJK KR` there).
  - `LANG` moved one slot: under `zh_TW` (`R-*zhTW-none`, and probe-1 A, E and F) the Complex font is `Noto Sans CJK TC` instead of `Noto Sans Arabic UI`. This host's fontconfig reads the environment. `ja_JP` and `de_DE` did not move it.
- **Graphic default-style fonts DO follow the tag (observed; mechanism from source).** These are the defaults for shapes and text boxes.
  - `SdrModel::SetTextDefaults` asks VCL for default fonts in `Application::GetSettings().GetLanguageTag()` (`svx/source/svdraw/svdmodel.cxx:656-690`). Under LOK that is the LOK language tag (`vcl/source/app/settings.cxx:2697-2698`), which `Language=` sets.
  - Without a tag it is `zxx`, and the Complex family falls to an environment-dependent fontconfig choice: `Noto Sans CJK JP` under ja_JP.
  - This corrects the fact sheet's "Fonts: not affected" (b3). That statement is true for the Writer paragraph default only.
  - The template-made saves (Q3) keep the template's fonts in the graphic default too.
  - What WASM would pick (VCL.xcu lists against the image's 14 fonts): **not run**.

### Q5. Number, date and currency (observed for a date field and for the engine's locale data; a currency in a document: not run)

- **The date field follows the tag.** `.uno:InsertDateField` into the style-less document was saved and read back as text:
  - none and `en-US`: `10/16/26`;
  - `de`: `16.10.26`;
  - `zh-TW`: `2026/10/16`.
- **Under `zh-TW` the Western text language stays en-US**, yet the field shows the zh-TW date format. Its saved data style `N30` carries `number:format-source="language"`; the other arms save `N37` with explicit parts and no `format-source`.
  - What another application then renders for `format-source="language"` is **not run** [inferred: it may use its own locale's default].
- **The engine's locale data after the load** (`SvtSysLocale().GetLocaleData()`, read in-process) follows the tag:

  | tag | currency | decimal sep | date |
  | --- | --- | --- | --- |
  | none, `en`, `en-US` | USD `$` | `.` | `10/16/2026` |
  | `en-GB` | GBP `£` | `.` | `16/10/2026` |
  | `de` | EUR `€` | `,` | `16.10.2026` |
  | `zh-TW` | TWD `NT$` | `.` | `2026/10/16` |
  | `ja` | JPY `￥` | `.` | `2026/10/16` |

  With no option, `SvtSysLocale::GetLanguageTag()` is `zxx`; under LOK it returns the LOK locale tag (`unotools/source/misc/syslocale.cxx:160-165`).
- **Not run:**
  - inserting a currency-formatted number into a document;
  - reading `SvNumberFormatter`'s currency table directly.

## Per-arm tables (generated from `summary.txt`; run 1 shown, run 2 identical in every arm)

"W / A / C" are the paragraph `default-style`'s `fo:` / `-asian` / `-complex` language-country. The page is resolved through the `Standard` master page. The registry column is what the fresh profile held after the process exited.

| arm | `LANG` | option | saved W / A / C | paragraph-default fonts W / A / C | graphic-default fonts W / A / C | page (Standard master) | registry `ooSetupSystemLocale` / `ooLocale` | styles.xml sha256[:16] | run 1 = run 2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-orig-enUS-none | en_US | none | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| R-orig-zhTW-none | zh_TW | none | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | Letter (8.5in x 11in) | en-US / en-US | `d2b08cda0de24b0e` | yes |
| R-zhTW-none | zh_TW | none | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | Liberation Serif / DejaVu Sans / Noto Sans CJK TC | Letter (8.5in x 11in) | en-US / en-US | `d2b08cda0de24b0e` | yes |
| Q1-deDE-none | de_DE | none | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q1-deDE-zhTW | de_DE | `Language=zh-TW` | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / Noto Serif CJK TC / Noto Sans CJK TC | A4 (21.001cm x 29.7cm) | zh-TW / zh-TW | `b21957cd574dd5c8` | yes |
| M1-deDE-zhTW-forceW-deDE | de_DE | `Language=zh-TW` | de-DE / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / Noto Serif CJK TC / Noto Sans CJK TC | A4 (21.001cm x 29.7cm) | zh-TW / zh-TW | `b03184bccdad195d` | yes |
| L-deDE-none | de_DE | none | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| L-deDE-zhTW | de_DE | `Language=zh-TW` | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / Noto Serif CJK TC / Noto Sans CJK TC | A4 (21.001cm x 29.7cm) | zh-TW / zh-TW | `b21957cd574dd5c8` | yes |
| Q2-none | en_US | none | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q2-en | en_US | `Language=en` | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | A4 (8.2681in x 11.6929in) | en / en | `2334c7de903afdd4` | yes |
| Q2-enUS | en_US | `Language=en-US` | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q2-enGB | en_US | `Language=en-GB` | en-GB / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | A4 (21.001cm x 29.7cm) | en-GB / en-GB | `37e6c47c4f29a047` | yes |
| Q2-de | en_US | `Language=de` | de-DE / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | A4 (21.001cm x 29.7cm) | de / de | `383b4d413523508b` | yes |
| Q2-zhTW | en_US | `Language=zh-TW` | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / Noto Serif CJK TC / Noto Sans CJK TC | A4 (21.001cm x 29.7cm) | zh-TW / zh-TW | `b21957cd574dd5c8` | yes |
| Q2-invalid | en_US | `Language=xx_bad!` | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q2-zh_TW-underscore | en_US | `Language=zh_TW` | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q3-A4-none | en_US | none | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Liberation Serif / Noto Sans CJK TC / Liberation Sans | A4 (8.2681in x 11.6929in) | en-US / en-US | `d2a661373fbb97fe` | yes |
| Q3-A4-enUS | en_US | `Language=en-US` | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Liberation Serif / Noto Sans CJK TC / Liberation Sans | A4 (8.2681in x 11.6929in) | en-US / en-US | `d2a661373fbb97fe` | yes |
| Q3-A4-ja | en_US | `Language=ja` | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Liberation Serif / Noto Sans CJK TC / Liberation Sans | A4 (21.001cm x 29.7cm) | ja / ja | `f2e37e7d8c0d1b4a` | yes |
| Q3-Letter-none | en_US | none | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Letter (8.5in x 11in) | en-US / en-US | `0ad2e588e80cd437` | yes |
| Q3-Letter-enUS | en_US | `Language=en-US` | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Letter (8.5in x 11in) | en-US / en-US | `0ad2e588e80cd437` | yes |
| Q3-Letter-ja | en_US | `Language=ja` | en-US / zh-TW / hi-IN | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Liberation Serif / Noto Sans CJK TC / Liberation Sans | Letter (21.59cm x 27.94cm) | ja / ja | `7a9c2a87283adfe5` | yes |
| Q4-jaJP-none | ja_JP | none | en-US / ja-JP / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans CJK JP | Letter (8.5in x 11in) | en-US / en-US | `6e5cf3ead4a69b70` | yes |
| Q4-jaJP-enUS | ja_JP | `Language=en-US` | en-US / ja-JP / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `d8bc211b801f62ea` | yes |
| L-jaJP-none | ja_JP | none | en-US / ja-JP / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans CJK JP | Letter (8.5in x 11in) | en-US / en-US | `6e5cf3ead4a69b70` | yes |
| L-jaJP-enUS | ja_JP | `Language=en-US` | en-US / ja-JP / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `d8bc211b801f62ea` | yes |
| Q4-enUS-ja | en_US | `Language=ja` | en-US / ja-JP / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Noto Serif CJK JP / Noto Serif CJK JP / Noto Sans CJK JP | A4 (21.001cm x 29.7cm) | ja / ja | `16e262b8a14548f5` | yes |
| Q5-none | en_US | none | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q5-enUS | en_US | `Language=en-US` | en-US / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | Letter (8.5in x 11in) | en-US / en-US | `b4724ec01b34ea51` | yes |
| Q5-de | en_US | `Language=de` | de-DE / zh-CN / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / DejaVu Sans / Noto Sans | A4 (21.001cm x 29.7cm) | de / de | `383b4d413523508b` | yes |
| Q5-zhTW | en_US | `Language=zh-TW` | en-US / zh-TW / hi-IN | Liberation Serif / DejaVu Sans / Noto Sans Arabic UI | Liberation Serif / Noto Serif CJK TC / Noto Sans CJK TC | A4 (21.001cm x 29.7cm) | zh-TW / zh-TW | `b21957cd574dd5c8` | yes |

Readouts taken inside the process (`tool/lok_language_probe.cpp`). M1's after-init fallbacks are from before its mutation; its `after-mutation` readout shows `western=de-DE` (`out/M1-…/probe.stdout`).

| arm | LocaleBackend `System/L10N/Locale` (after init) | fallbacks after init W / A / C | after load: `SvtSysLocale` (LOK locale tag, locale data, currency, decimal, date) | date field (text; data style, number:language, number:country, format-source) |
| --- | --- | --- | --- | --- |
| R-orig-enUS-none | (probe-1 tool, no readout) | - | - | - |
| R-orig-zhTW-none | (probe-1 tool, no readout) | - | - | - |
| R-zhTW-none | "zh-TW" | en-US / zh-TW / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q1-deDE-none | "de-DE" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q1-deDE-zhTW | "de-DE" | en-US / zh-CN / hi-IN | tag zh-TW, data zh-TW, TWD NT$, dec ".", date 2026/10/16 | - |
| M1-deDE-zhTW-forceW-deDE | "de-DE" | en-US / zh-CN / hi-IN | tag zh-TW, data zh-TW, TWD NT$, dec ".", date 2026/10/16 | - |
| L-deDE-none | "de-DE" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| L-deDE-zhTW | "de-DE" | en-US / zh-CN / hi-IN | tag zh-TW, data zh-TW, TWD NT$, dec ".", date 2026/10/16 | - |
| Q2-none | "en-US" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q2-en | "en-US" | en-US / zh-CN / hi-IN | tag en, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q2-enUS | "en-US" | en-US / zh-CN / hi-IN | tag en-US, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q2-enGB | "en-US" | en-US / zh-CN / hi-IN | tag en-GB, data en-GB, GBP £, dec ".", date 16/10/2026 | - |
| Q2-de | "en-US" | en-US / zh-CN / hi-IN | tag de, data de-DE, EUR €, dec ",", date 16.10.2026 | - |
| Q2-zhTW | "en-US" | en-US / zh-CN / hi-IN | tag zh-TW, data zh-TW, TWD NT$, dec ".", date 2026/10/16 | - |
| Q2-invalid | "en-US" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q2-zh_TW-underscore | "en-US" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q3-A4-none | "en-US" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q3-A4-enUS | "en-US" | en-US / zh-CN / hi-IN | tag en-US, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q3-A4-ja | "en-US" | en-US / zh-CN / hi-IN | tag ja, data ja-JP, JPY ￥, dec ".", date 2026/10/16 | - |
| Q3-Letter-none | "en-US" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q3-Letter-enUS | "en-US" | en-US / zh-CN / hi-IN | tag en-US, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q3-Letter-ja | "en-US" | en-US / zh-CN / hi-IN | tag ja, data ja-JP, JPY ￥, dec ".", date 2026/10/16 | - |
| Q4-jaJP-none | "ja-JP" | en-US / ja-JP / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q4-jaJP-enUS | "ja-JP" | en-US / ja-JP / hi-IN | tag en-US, data en-US, USD $, dec ".", date 10/16/2026 | - |
| L-jaJP-none | "ja-JP" | en-US / ja-JP / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | - |
| L-jaJP-enUS | "ja-JP" | en-US / ja-JP / hi-IN | tag en-US, data en-US, USD $, dec ".", date 10/16/2026 | - |
| Q4-enUS-ja | "en-US" | en-US / zh-CN / hi-IN | tag ja, data ja-JP, JPY ￥, dec ".", date 2026/10/16 | - |
| Q5-none | "en-US" | en-US / zh-CN / hi-IN | tag zxx, data en-US, USD $, dec ".", date 10/16/2026 | 10/16/26 (N37, -, -, -) |
| Q5-enUS | "en-US" | en-US / zh-CN / hi-IN | tag en-US, data en-US, USD $, dec ".", date 10/16/2026 | 10/16/26 (N37, -, -, -) |
| Q5-de | "en-US" | en-US / zh-CN / hi-IN | tag de, data de-DE, EUR €, dec ",", date 16.10.2026 | 16.10.26 (N37, -, -, -) |
| Q5-zhTW | "en-US" | en-US / zh-CN / hi-IN | tag zh-TW, data zh-TW, TWD NT$, dec ".", date 2026/10/16 | 2026/10/16 (N30, -, -, language) |

## Validity of the arms

**`locale -a`** (`host/locale-a.txt`): `C`, `C.utf8`, `POSIX`, 23 `en_*` entries (`en_US.utf8` among them), `zh_TW.utf8`. **`de_DE.UTF-8` and `ja_JP.UTF-8` are not installed.** All arms are valid, for these reasons:

1. **LibreOffice reads the locale with `getenv`, not with glibc (observed).**
   - The LocaleBackend reads `LC_ALL`, then `LC_CTYPE`, then `LANG` (`shell/source/backends/localebe/localebackend.cxx:165-169`, `:256`). In the de_DE and ja_JP arms, `System/L10N/Locale` reads `"de-DE"` and `"ja-JP"`, and the ja_JP arms' Asian fallback is ja-JP.
   - glibc's own locale is `C` in **every** run of this tool (58 runs; the probe-1-tool arms print no readout), installed locales (`en_US`, `zh_TW`) included: `setlocale(LC_ALL, NULL)` is printed in every readout. Nothing on this path calls `setlocale(LC_ALL, "")`.
2. **The one glibc-dependent effect (observed):** sal's thread text encoding.
   - `osl_getTextEncodingFromLocale` calls `newlocale(LC_CTYPE_MASK, "<LANG>")` (`sal/osl/unx/nlsupport.cxx:578-582`). That fails for an uninstalled locale, and sal falls back to ASCII (`sal/osl/unx/thread.cxx:1040`).
   - Exactly the 10 de_DE and ja_JP runs log `RTL_TEXTENCODING_DONTKNOW -> _ASCII_US`.
3. **Control for it (observed).** Arms `L-*` repeat the four de_DE and ja_JP arms with `LOCPATH` pointing at private copies.
   - The copies were built with `localedef -i de_DE -f UTF-8 <scratch>/locales/de_DE.UTF-8`, and likewise for ja_JP. They live in the scratchpad: no sudo, nothing installed system-wide.
   - The warning disappears. `styles.xml`, `content.xml`, every readout and the registry snippet are **byte-identical** to the uninstalled-locale runs, in both runs (`summary.txt`, "Pairs").
   - So no `sudo locale-gen` is needed for any arm. If the owner wants the system locales anyway: `sudo locale-gen de_DE.UTF-8 ja_JP.UTF-8` (optional; nothing here depends on it).

**Replication of probe-1 (observed).**

- probe-1's own tool, rebuilt unchanged and run here (`R-orig-*`), reproduces probe-1's arm A (`d2b08cda…`) and arm B (`b4724ec0…`) byte for byte.
- This tool reproduces the same hashes (`R-zhTW-none`, `Q2-none`), and arm D (`b21957cd…`, `Q2-zhTW`). So linking `libmergedlo.so` and reading state in-process do not perturb the save.
- The install has not changed since 10-14.

**Determinism (observed).** Every arm ran twice. Run 1 and run 2 are identical in all 31 arms: `styles.xml` bytes, `content.xml` bytes (with the date field's wall-clock `text:date-value` masked), the in-process readouts, and the registry snippet.

## How it was run

- **Install.** `native-lok-26-8/build/instdir/program`, the same native install as probe-1.
  - `program/versionrc` `buildid=671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`, which equals `native-lok-26-8/src` HEAD.
  - `libmergedlo.so` sha256 `2d49c9ff845d3e2cd3fb5d109ea95e9ce01bf45f2925e9a1ed2176eaedd3f924`; `libswlo.so` `885566e3…`; the rest are in `host/install.txt`.
- **Tools.** `tool/build.sh <outdir>` compiles two one-file probes with g++ 15.2. The binaries live in the session scratchpad, not here; their hashes are in `host/binaries.txt`.
  1. `tool/lok_language_probe.cpp`. These are the same LOK calls as probe-1 (`lok_init_2`, `documentLoad[WithOptions]`, `saveAs(out,"odt",nullptr)`), plus read-only in-process readouts after init and after load:
     - the LocaleBackend `System/L10N/*`, `Setup/L10N/ooSetupSystemLocale` and `ooLocale`, and `Linguistic/General/DefaultLocale*`;
     - the configured system language, the three fallbacks (through `MsLangId::resolveSystemLanguageByScriptType`), and `resolve(LANGUAGE_SYSTEM)` per script, which is SwDoc's computation;
     - the LOK language and locale tags, `PaperInfo::getSystemDefaultPaper`, `SvtSysLocale` locale data, and glibc's `setlocale(LC_ALL,NULL)`.

     Two switches exist: `PROBE_DATE_FIELD=1` (Q5) and `PROBE_FORCE_WESTERN_FALLBACK=<tag>` (M1 only). The probe links `libmergedlo.so` (the file `lok_init_2` dlopens, so one copy is shared) and `libi18nlangtag.so`, with `-DLIBO_INTERNAL_ONLY` and the build's generated UNO and officecfg headers.
  2. probe-1's `lok_defaults_probe.cpp`, unchanged, with probe-1's recipe.
- **`tool/run_arms.sh <probe> <probe-1-probe> <scratch> <evidence> [regex]`**
  - It runs each arm twice, strictly one process at a time, each under `nice -n 10` and `timeout 300`, with a fresh empty profile directory.
  - The environment is built with **`env -i`**: `HOME`, `PATH=/usr/bin:/bin`, `TMPDIR=<scratch>/tmp`, `LANG=<arm>`, `SAL_USE_VCLPLUGIN=svp`, plus the arm's one extra switch. There is no `LC_*`, `LANGUAGE` or `PAPERSIZE`; every probe prints the `LANG*`/`LC_*` it saw.
  - The input is copied into the run directory first, because LibreOffice writes a lock file next to the document.
- **Extra environment note.** The calling shell carries nine `LC_*=zh_TW.UTF-8` (`host/calling-shell-locale-env.txt`). Unsetting only the five variables probe-1 named would have left `LC_TIME`, `LC_NUMERIC`, `LC_MONETARY`, `LC_MEASUREMENT` and others in place, hence `env -i`.
- **Commands** (2026-10-16; about 95 s for the 27 arms of the full pass):

  ```
  tool/build.sh <scratch>
  tool/run_arms.sh <scratch>/lok_language_probe <scratch>/lok_defaults_probe <scratch> <this dir>
  python3 -I tool/summarize.py <this dir> > summary.txt
  ```

  The `L-*` arms were added after the first full pass and run with the regex `'^L-'`. They used the same binary; the runner changed only by gaining those rows and the `@SCR@` substitution.

## What this does NOT show

- **Nothing about WASM is observed.** Language, fallback and paper behaviour should carry over, because the core files are the same commit (fact sheet: the six cited files are byte-identical between `native-lok-26-8/src` and `libreoffice-26-8`, and the WASM trees' `SRC_ROOT` is `libreoffice-26-8`) [inferred]. Not observed in WASM:
  - Emscripten's `newlocale` and text-encoding behaviour;
  - the WASM image's font choices, for both the paragraph default and the graphic default (finding 113 measured `Noto Sans CJK KR` for the paragraph Asian slot there);
  - whether the WASM build's measurement-unit choice matches. The Q3 "byte pins move" consequence is inferred from that.
- **All font names here are this desktop's fontconfig substitutes:** DejaVu Sans, Noto Sans Arabic UI, Noto Serif/Sans CJK TC/JP. They do not transfer.
- **One load per process.**
  - `Language=` is process-wide; the "first load" capture (`SfxLokHelper::setLoadLanguage`) and the lazily built `SwMasterUsrPref` unit are per process.
  - A second load in the same process with another tag was **not run**. The product makes a new worker per open (fact sheet 1(b) b1), so one load per process matches it [inferred].
- **Only 2 of the 30 templates, only `LANG=en_US`, and nothing typed** for Q3.
  - J2's typed-text leak check was **not run**.
  - The other 28 templates were not loaded. They differ only in the stated languages, fonts and paper [inferred from the generator table].
- **Pins.** Only the Western fallback was overwritten, in M1, as a control. Asian and Complex pins, and pin values, were **not run**.
- **No complex-script environment** (`LANG=ar_*`, `hi_*`, …) was run, so the Complex fallback was never moved from hi-IN.
- **Finding 031** cannot be observed without `.mo` catalogs (none are packed or installed here); **not run**.
- **Q5.** A currency-formatted number in a document, and `SvNumberFormatter`'s currency table itself, are **not run**. How another application renders `number:format-source="language"` is **not run**.
- **The fallback readout's built-in defaults.** A fallback that reads en-US, zh-CN or hi-IN may be unset or explicitly set; the saved outcome is the same.

## Discrepancies found on the way (for whoever plans the batch)

- **analysis-1 (`analysis-1.md:116`, `:208`, `:272`):** "de-DE browser + `Language=zh-TW` gives Western de-DE" is **refuted** natively (Q1). The engine-side reason to pin the Western fallback falls away. The Asian pin is still needed (Q4; and `zh-CN` for any non-Asian environment).
- **Fact sheet b3, "Fonts: not affected".** It is right for the Writer paragraph default and wrong for the graphic default-style (Q4).
- **probe-1 README and analysis-1 D4 record `libsofficeapp.so` sha256 `9ad35464…`.** In this merged-lib build that file is a 21-byte text placeholder (`invalid - merged lib`), so the hash identifies nothing. The code is `libmergedlo.so` (`2d49c9ff…`).
- **analysis-1 D4's git HEAD `96dd0fce…`** is not the install's `buildid` (`671c848b…`, `program/versionrc`).
- **Fact sheet `paper.cxx:231`** is `:232` in both trees (the files are identical).
- **probe-1 unset only five locale variables.** The replication arms under `env -i` reproduce its A, B and D bytes, so the leftover `LC_*` did not affect those outputs (observed for those three).

## Files

- `tool/`: `lok_language_probe.cpp`, `build.sh`, `run_arms.sh`, `summarize.py`, and `inputs/`:
  - `styleless-template.odt`, richdocuments' `template.odt` as in probe-1, `a3354bae…`;
  - the two host templates.
- `out/<arm>-r<n>/`: `run.txt` (arm, env, rc, seconds, input/output/registry hashes), `probe.stdout` (readouts), `probe.stderr` (SAL warnings), `styles.xml`, `content.xml`, and `registry-snippet.xcu`. The snippet is the `Setup/L10N`, `Linguistic/General` and `I18N` items of the profile's `registrymodifications.xcu`; the full file's hash is in `run.txt`.
- `summary.txt`: `tool/summarize.py`'s output, derived only from `out/` and `tool/inputs/`.
- `host/`: `locale-a.txt`, `install.txt`, `binaries.txt`, `calling-shell-locale-env.txt`.
- `SHA256SUMS`: every file above except `README.md` and `SHA256SUMS` itself.

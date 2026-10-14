# Analysis 1: what language, fonts and page the WASM engine gives a style-less ODT, and how to make it right

This answers `brief-1-default-language-and-fonts.md` (commit `b014871b`). Written 2026-10-14 by fable as analyst. The analyst's harness refused its write, so the main session wrote the text verbatim from its report; only the SUMMARY's placeholder was expanded into its nine points.

The raw output of the measurement is in `probe-1-native-defaults/`. This is not an owner-delegated ruling; choices are given as options.

## SUMMARY

1. **Q1, the engine's locale.** LibreOfficeKit forces the process locale to **en-US at init**, native and WASM alike (`desktop/source/lib/init.cxx:8347`, `setLanguageAndLocale(u"en-US"_ustr)`). This happens before the main thread starts (`:8381`). Paper size is derived from that key (`i18nutil/source/utility/paper.cxx:231`), so a style-less document is **Letter** everywhere unless a load passes `Language=`. The Western default is en-US.
2. **The Asian default is the odd one: it follows the browser.**
   - `desktop::langselect::prepareLocale` (`desktop/source/app/langselect.cxx:70-75`) reads the environment locale through the LocaleBackend and sets the Asian fallback from it. The backend is linked and registered in the shipped image.
   - In the WASM worker that environment variable is synthesized by Emscripten from `navigator.language` (shipped `probe.js`, `getEnvStrings`).
   - So a zh-TW browser gives zh-TW, and an English or any Latin-script browser gives **zh-CN**. CTL is hi-IN.
   - Nextcloud's language setting plays no part today.
3. **Fonts do not follow any locale.**
   - Default fonts are pool defaults computed once with `LANGUAGE_ENGLISH_US` (`editeng/source/items/textitem.cxx:2938-2940`).
   - The Asian slot resolves through VCL's `en` UI font list to a substitute. On the WASM profile that substitute is **`Noto Sans CJK KR`**. Finding 113 measured it on v8 and on the five-family pack that v19 ships.
   - Neither `Language=` nor Collabora's route changes this.
4. **Measured natively (7 arms).** Fonts were identical in all seven arms.
   - `LANG=zh_TW`, no options: en-US / zh-TW / hi-IN, Letter.
   - `LANG=en_US`: zh-CN, Letter.
   - `Language=zh-TW` on an en_US host: zh-TW, **A4**, and the registry is rewritten to zh-TW.
   - `Language=en-US` on a zh_TW host: Letter, but the Asian language **stays zh-TW**; the browser leak survives the tag.
5. **What `Language=` does (R6).**
   - It rewrites `ooSetupSystemLocale` and `ooLocale` for the whole process at every load (`init.cxx:2843-2869`, `:2780-2786`).
   - It also sets the LOK UI and locale tags and the default view language.
   - So it changes the default languages (through the script-type fallback), the paper and the currency table. It does not change the default fonts.
6. **Q2, impact.**
   - Taiwanese buyers get Letter in every new blank document today.
   - Users on English browsers get zh-CN for Asian text. That means SC glyph forms in any viewer that honours the language, and PRC typography and spelling downstream.
   - Every saved blank document names `Noto Sans CJK KR` as its Asian font.
   - The owner sits in the lucky cell (a zh-TW browser), except for the paper.
   - There is no 114-shape line-height problem with e10.
   - The image has no spell-check or hyphenation, so the language tags matter for glyph forms, CJK rules, and what desktop software does with the file later.
7. **Q3, options.**
   - (a) Registry in the profile: per engine and repack-only, but the paper half needs an `oor:finalized` trick to survive the forced en-US. A hack.
   - (b) `Language=` per load: per user, with the right languages and paper. It **needs an engine change, so it waits for the link after v20**. Fonts stay wrong, and 031 stays latent because no `.mo` is packed.
   - (c) The blank template carries explicit defaults: host-only, and per user if the host picks the template by Nextcloud language. It fixes language, paper **and** font name, and the browser cannot affect it.
   - (d) UNO commands after load: no dispatch is reachable from JS, it cannot set fonts, and it dirties a new document. Dominated.
8. **Recommendation:** C first (the template carries the defaults; the host picks one per language), then (b) in the next link batch as the engine-level complement, together with 031's fix. The B lean is not viable alone: without (c), the saved blank document names a Korean font, and until the link it is Letter with a browser-dependent Asian language.
9. **Q4, `.ott`.** The first version offers blank and `.odt` only. Nextcloud core copies the `.ott` bytes into the new `.odt`, so R1's "leaves the file empty" is false. Offering `.ott` needs a first-open conversion design plus four measurements.

## DIAGNOSIS (Q1)

### D1. Where the engine's locale comes from, in order of application

The shipped image (`dist/profiles/resources/base-r5-no35.*`, 1,240 files) contains **no user profile and no `registrymodifications.xcu`**. The engine passes `file:///tmp/user` (`wasm_sdk_probe/src/probe_engine.cpp:6240`, `:6685`), an empty MEMFS directory.

- **Registry:** `Langpack-en-US.xcd`, `Langpack-qtz.xcd`, `Langpack-zh-TW.xcd`, `main.xcd`, `cjk.xcd`, `ctl.xcd` and the `res/registry_*.xcd` trio.
- **Missing:** `.mo` catalogs (finding 031) and dictionaries.
- **Fonts:** twelve Liberation faces, `opens___.ttf`, and `NotoSansCJK-Regular-subset-E10.ttc` (five Sans and five Mono families sharing one TC glyph set).

So every locale the engine believes in is computed at run time, from three inputs.

1. **The process environment.**
   - Emscripten synthesizes it in the shipped loader: `var lang=(typeof navigator=="object"&&navigator.language||"C").replace("-","_")+".UTF-8"` and `env={USER:"web_user",...,LANG:lang,...}` (`dist/profiles/e2-editor-v19/probe.js`, `getEnvStrings`).
   - The worker has a `WorkerNavigator`, so `LANG` is the **browser UI language**, for example `zh_TW.UTF-8` or `en_US.UTF-8`.
   - Nothing in the SDK worker or the engine overrides `ENV`. `sdk-worker.js` has no `preRun` or `ENV`. The only `setenv` in the engine is `SAL_LOK_OPTIONS` (`probe_engine.cpp:6679-6681`). The `static/emscripten/environment.js` pre-js sets only `ENV.MAX_CONCURRENCY`.
2. **LibreOfficeKit's own init.**
   - `lo_initialize` ends its first-init block with `setLanguageAndLocale(u"en-US"_ustr)` (`init.cxx:8347`). That function is `SvtSysLocaleOptions::SetLocaleConfigString` + `SetUILocaleConfigString` + `Commit` (`:2780-2786`).
   - The first of those also calls `LanguageTag::setConfiguredSystemLanguage(en-US)` (`unotools/source/config/syslocaleoptions.cxx:398-415`).
   - This happens **before** the main thread is created (`osl_createThread(lo_startmain, ...)`, `:8381`), and it is unconditional.
   - It is why every no-option run of the native probe ends with `ooSetupSystemLocale=en-US ooLocale=en-US` in its profile, although `LANG=zh_TW`.
3. **`Desktop::Main` → `langselect::prepareLocale()`** (`desktop/source/app/app.cxx:509`). This runs on the main thread, after step 2.
   - **It reads the environment locale.** It reads `officecfg::System::L10N::SystemLocale` and `::Locale` (`langselect.cxx:72-75`).
     - Those are external values served by the LocaleBackend, which on Unix and Emscripten reads `LC_ALL`/`LC_CTYPE`/`LANG` (`shell/source/backends/localebe/localebackend.cxx:163-169`, `:256`).
     - The backend is linked (`soffice.js.linkdeps` has `-llocalebe1lo`) and registered (the image's `program/services/services.rdb` names `com.sun.star.configuration.backend.LocaleBackend`).
     - For each value it calls `setMsLangIdFallback` (`:50-66`). An Asian-script locale sets `MsLangId::setConfiguredAsianFallback`, a complex-script one sets the complex fallback, and anything else sets the Western fallback.
     - **This is the only path by which the browser language reaches the document defaults.**
   - **It re-derives the system language.** It takes it from `ooSetupSystemLocale` (`:129-134`), which step 2 set to en-US, and sets the fallback for that script type too (`:140-141`). So Western is en-US.
   - **It picks `ooLocale`** from the installed langpacks for the environment's UI language (`:88-116`).
     - Natively only `Langpack-en-US.xcd` is installed, so it picks en-US.
     - The WASM image also installs `Langpack-zh-TW.xcd`, so for a zh-TW browser this write (after step 2) likely lands `ooLocale=zh-TW`. **Not measured.**
     - The consequences are confined to localized configuration strings (`registry_zh-TW.xcd`) and to `Application::GetSettings().GetUILanguageTag()`. UI strings stay English because no `.mo` is packed.

### D2. How a style-less document turns those inputs into defaults

- **Languages.**
  - `SwDoc::SwDoc` (`sw/source/core/doc/docnew.cxx:382-397`) reads `Linguistic/General/DefaultLocale{,_CJK,_CTL}`. All three are empty in the schema (`officecfg/registry/schema/org/openoffice/Office/Linguistic.xcs:155-181`), and an empty string means `LANGUAGE_SYSTEM` (`unotools/source/config/lingucfg.cxx:81-86`).
  - `MsLangId::resolveSystemLanguageByScriptType` (`i18nlangtag/source/isolang/mslangid.cxx:135-166`) takes the configured system language, en-US. Because its script is Latin, it returns en-US for Western and the **configured fallback** for Asian and Complex. With no fallback set, those default to zh-CN and hi-IN.
  - The ODF import leaves these untouched, because richdocuments' `styles.xml` names no language. The export writes them out explicitly.
- **Paper.**
  - The default page description takes `SvxPaperInfo::GetDefaultPaperSize()` (`sw/source/core/doc/docdesc.cxx:73-81`, `editeng/source/items/paperinf.cxx:102-109`), which calls `PaperInfo::getSystemDefaultPaper()` (`paper.cxx:227-367`).
  - That function reads `ooSetupSystemLocale` first (`:231`). Only when the key is empty does it consult the fallbacks, and none of them applies on WASM:
    - `paperconf`, compiled out on `__EMSCRIPTEN__` (`:244`);
    - glibc `LC_PAPER`; the Emscripten sysroot's `locale.h` defines no `LC_PAPER`, so `:310` is compiled out;
    - the LocaleBackend (`:352-353`).
  - Step 2 never leaves the key empty, so the WASM path is simply `getDefaultPaperForLocale(ooSetupSystemLocale)`.
  - That gives Letter for US, PR, CA, VE, CL, MX, CO, PH, BZ, CR, GT, NI, PA and SV (`:440-500`), and **A4 for everything else, including TW**. With the forced en-US, the result is **Letter**.
- **Fonts.**
  - The Writer attribute pool's static defaults come from `GetDefaultFonts()` (`sw/source/core/bastyp/init.cxx:480-489` → `editeng/source/items/textitem.cxx:2927-2952`). It asks `OutputDevice::GetDefaultFont` with **`LANGUAGE_ENGLISH_US` for both the Latin and the CJK slot**, and `LANGUAGE_ARABIC_SAUDI_ARABIA` for CTL, `OnlyOne`.
  - Per-language fonts are applied only by `SwDocShell::InitNew`, for a brand-new document (`sw/source/uibase/app/docshini.cxx:140-215`). `SwDocShell::Load` never applies them (`:461-500`).
  - VCL's `en` node has no `CJK_TEXT` list, so the lookup falls back to the `en` UI font list (`unotools/source/config/fontcfg.cxx:189-229`; VCL.xcu en `UI_SANS`: `Segoe UI;Tahoma;Arial Unicode MS;Lucida Sans Unicode;DejaVu Sans;...`). The image has none of those fonts, so `GetDefaultFont` hands the whole list to the font cache and records the substitute's family name (`vcl/source/outdev/font.cxx:518-590`).
  - Finding 113 measured that substitute on the WASM profile: `Noto Sans CJK KR` on v8 and on the five-family pack (`e2-editor-v15-cjk-ttc5-ab`), and `Liberation Sans` on the one-family v15 pack.
  - v19's `cjk-sub-e10` carries the same five Sans family names, so **`Noto Sans CJK KR`** is the expected name. That is an inference from 113's measurement; it was not re-measured on v19.
  - Western: `Liberation Serif`, which is installed and first in `en` `LATIN_TEXT`.
  - Complex: `Liberation Sans`. The 08-22 operator save shows `Liberation Sans1` in that slot.

### D3. What `Language=` changes, from source (R6)

If the tag is valid BCP-47, `lo_documentLoadWithOptions` (`init.cxx:2843-2869`) does five things:

1. It records the first load's language (`SfxLokHelper::setLoadLanguage`). That is used at save time to key field-master names (`sfx2/source/doc/objstor.cxx:3486-3510`).
2. It sets the default view language (`SfxLokHelper::setDefaultLanguage`), which new views read at `sfx2/source/view/viewsh.cxx:2770-2771`.
3. It sets the LOK UI tag and locale tag (`comphelper::LibreOfficeKit::setLanguageTag/setLocale`). Under LOK, `SvtSysLocale::GetUILanguageTag/GetLanguageTag` return exactly these (`unotools/source/misc/syslocale.cxx:160-172`). Both are `LANGUAGE_NONE` until set (`comphelper/source/misc/lok.cxx:81-83`).
4. It **rewrites `ooSetupSystemLocale` and `ooLocale` for the whole process** (`setLanguageAndLocale`, the same function as the forced en-US).
5. It resets the currency table.

`doc_createViewWithOptions` (`:6955-6975`) does only (3).

Arms D–G confirm the consequences:

- The system language becomes the tag. `resolveSystemLanguageByScriptType` then yields the tag for the tag's own script, and the fallbacks for the other two.
- The paper follows the tag's country.
- The fallbacks that `prepareLocale` set from the browser are **not** touched. That is why arm E (`Language=en-US` in a zh_TW environment) still gives Asian zh-TW.
- For the same reason, a de-DE browser with `Language=zh-TW` would give Western de-DE. This is an inference from `:50-66` and `mslangid.cxx:157-162`; it was not measured.
- The default fonts were unchanged in all arms.

### D4. The measurement

- **Build:** native 26.8 (`native-lok-26-8/build/instdir`, git HEAD `96dd0fce…`, `libsofficeapp.so` sha256 `9ad35464…`).
- **Input:** richdocuments' `template.odt` (sha256 `a3354bae…`), loaded through LOK (`lok_init_2`, `documentLoad[WithOptions]`), saved with `saveAs(out,"odt",nullptr)`, and its `styles.xml` read back.
- **Isolation:** a fresh empty profile per arm, with `LC_ALL`, `LANGUAGE`, `LC_CTYPE`, `LC_PAPER` and `PAPERSIZE` unset.
- **Raw output:** `probe-1-native-defaults/`.

| arm | env `LANG` | options | W / A / C | page | registry after run |
| --- | --- | --- | --- | --- | --- |
| A | zh_TW | none | en-US / zh-TW / hi-IN | Letter (8.5in x 11in) | en-US / en-US |
| B | en_US | none | en-US / zh-CN / hi-IN | Letter | en-US / en-US |
| C | C | none | en-US / zh-CN / hi-IN | Letter | en-US / en-US |
| D | en_US | `Language=zh-TW` | en-US / zh-TW / hi-IN | A4 (21.001cm x 29.7cm) | zh-TW / zh-TW |
| E | zh_TW | `Language=en-US` | en-US / zh-TW / hi-IN | Letter | en-US / en-US |
| F | zh_TW | `Language=zh-TW` | en-US / zh-TW / hi-IN | A4 | zh-TW / zh-TW |
| G | en_US | `Language=zh-CN` | en-US / zh-CN / hi-IN | A4 | zh-CN / zh-CN |

The fonts were `Liberation Serif / DejaVu Sans / <fontconfig substitute>` in every arm. B and C, and A and E, produced byte-identical `styles.xml`.

The registry column is the discriminator. It shows the forced en-US (A–C), and it shows that `Language=` is a process-wide config write (D–G).

What carries over to WASM:

- The language and registry columns carry over: the code is the same, and the only WASM-specific input is where `LANG` comes from.
- Paper carries over, because the key is never empty on either side.
- Font names do not carry over, because the installed set differs. Use finding 113's reading.
- The Complex font flips between A and B. That comes from this desktop's fontconfig and does not apply to the image.

### D5. The WASM measurement an executor should run

This was not run here: there were 34 `chrome` processes and the owner's desktop was in use.

1. Open `probe-1-native-defaults/tool/input-template.odt` in the shipped v19 page (`#open-file`/`#file`, `web/e2-editor.html:265-266`).
2. Save it through the SDK (`sdk-worker.js:1561`, `case "save"`) and unzip `styles.xml`.
3. Run two arms: Chrome with `--lang=zh-TW` and with `--lang=en-US` (for Firefox, set `intl.accept_languages`). Count `chrome` processes first.

Predictions for both arms:

- `fo:language="en" fo:country="US"`;
- `style:language-complex="hi"`;
- page `8.5in x 11in`;
- fonts `Liberation Serif / Noto Sans CJK KR / Liberation Sans`;
- Asian `zh-TW` in the first arm and **`zh-CN`** in the second.

What each surprise would mean:

- Asian zh-TW in the en-US arm: the browser is not the fallback's source. D1 step 3 is wrong; find the real source.
- A4: the forced en-US does not reach WASM. D1 step 2 is wrong.
- Another Asian font name: 113's reading does not hold for e10. Re-measure before quoting it.

## IMPACT (Q2)

1. **Paper: everyone, always.** Every user of every browser gets Letter, until a load passes `Language=` with a non-Letter country or the template says otherwise. This is the one defect the owner sees on their own machine.
2. **Asian language: users whose browser is not set to an Asian-script language get `zh-CN`.**
   - Inside LiteCore nothing looks wrong: e10 shares one TC glyph set, which is finding 113's fix working.
   - The damage is in the file. Desktop LibreOffice, Word and browsers pass the text language to the shaper, and Noto CJK fonts carry `locl`, so `zh-CN` text renders in Simplified forms elsewhere. This is inferred from the fonts' design, not measured.
   - It also brings PRC typography rules and, downstream, PRC spell-checking.
   - A Taiwanese institution whose staff keep Chrome in English is squarely in this cell.
3. **Asian font name: everyone.** Every saved blank document declares `Noto Sans CJK KR`.
   - Inside LiteCore it is harmless.
   - A machine with real Noto CJK renders the KR face (Korean default forms) unless the viewer honours `locl`. A machine without it substitutes by name.
   - `Language=` cannot fix this. Collabora's route has the same defect, because the server has the same pool default.
4. **Line height (the 114 shape): no new exposure.** The Asian slot resolves to a CJK face in e10, and `35-lang-normalize.conf` is gone from `base-r5-no35`.
5. **Spell-check and hyphenation: none in the image**, for any language. The language tags matter only for glyph forms, CJK line-breaking, and what desktop software does later.

Who is affected:

- **The owner:** paper only.
- **Taiwanese institutional buyers:** paper for everyone; zh-CN for every seat with an English browser; the KR font name in every outgoing file.
- **Users whose Nextcloud language is not Chinese:** zh-CN or their browser's Asian language, Letter, and the KR font. Western stays en-US regardless of their setting until `Language=` exists.

## OPTIONS (Q3, Q4)

Cost vocabulary:

- **relink**: an engine source change and a new link. v20's engine is final (since amended: `543a5566`), so any relink belongs to the batch after it.
- **repack**: a new profile from the archive without a link, as v16–v18 were.
- **page/host**: the shell or the Nextcloud app only.

### Q3

| | A: template carries explicit defaults (brief's c) | B: `Language=` per load (brief's b) | C: profile registry (brief's a) |
| --- | --- | --- | --- |
| Fixes | languages, paper, **font names**, Western language | languages (own script), paper | languages (if set explicitly), paper only via a hack |
| Leaves | the engine's own beliefs (irrelevant once the file states its defaults) | **fonts** (`Noto Sans CJK KR` stays); browser leak into the other scripts' fallback | fonts; per-user languages impossible |
| Cost | **host only**: one 2–3 KB `template.odt` per language in the app, picked server-side by `IL10NFactory::getUserLanguage()` | **relink** (open command gains a `language` field → `documentLoadWithOptions`) + worker/page passes `document.documentElement.lang` (`_`→`-`) | **repack**: worker writes `registrymodifications.xcu` into `/tmp/user/user` before `libreofficekit_hook_2` (worker already does `FS.mkdirTree`/`writeFile` for packs, `sdk-worker.js:653-654`) |
| Per user / engine | per user | per user | per engine |
| 031 | none (file stores ProgNames) | **latent, unchanged**: `setLanguageTag(zh-TW)` keys `SwStyleNameMapper`'s UI-name table by zh-TW, but no `.mo` is packed so names stay English and the barrier matches; the day translations are packed, 031 fires. Fix 031 (compare ProgName/id) in the same batch. | none |
| Paragraph-style UI | unaffected | unaffected today (same reason) | unaffected |
| Risks | template must name fonts the image has (`Noto Sans CJK TC`, `Liberation Serif`) and keep standard style names; owner leaned away from "a template with styles", but this is richdocuments' mechanism with different bytes | process-wide locale switch at every load; `ooSetupSystemLocale` written into MEMFS each open; de-DE browser + zh-TW Nextcloud gives Western de-DE unless the engine also pins the three fallbacks (`MsLangId::setConfigured*Fallback`, one more line) | paper needs `oor:finalized="true"` on `ooSetupSystemLocale=zh-TW` to survive `init.cxx:8347` (`SetLocaleString` returns early on read-only, `syslocaleoptions.cxx:403`); whether a user-layer finalized prop is honoured must be shown with a red case (remove `finalized` → Letter returns); conflicts with B later |

Option D (UNO commands after load) is dominated:

- No UNO dispatch is reachable from JS (there is no `postUnoCommand` in `sdk_api.cpp` or `editor_api.cpp`; actions are a closed list), so it would be a relink anyway.
- `.uno:LanguageStatus?Language:string=Default_<name>` takes a display name, not a tag (`sw/source/uibase/shells/langhelper.cxx:200`).
- `.uno:AttributePageSize` can set A4, but nothing sets default fonts.
- Every step dirties the new document and fills the undo stack.

**Recommendation: A first, then B as the complement in the next link batch.**

- **A.**
  - It is the only option that fixes the font name. It changes neither the engine nor the profile, and the browser cannot affect it.
  - In mechanism it is "the way richdocuments does it": a blank file that the app ships, written by the template listener. Only the bytes differ.
  - The owner's reason for the style-less lean (leave styles to the engine) does not hold. The engine's style-less defaults are not a neutral baseline: they are en-US, Letter and KR by construction.
  - One template per supported Nextcloud language keeps it per user.
  - Acceptance: open the saved blank document natively with `LANG=en_US`. It must read `fo:language="en" fo:country="US"`, `style:language-asian="zh" style:country-asian="TW"`, `style:font-name-asian="Noto Sans CJK TC"`, page `21cm x 29.7cm`. The same must hold from the WASM engine (the D5 harness) in both browser arms, with byte-identical `styles.xml` between the arms.
- **B** is still worth doing, for three reasons:
  - It fixes every other style-less document a user opens.
  - The Western default and the paper of new page styles come from the engine's belief, not from the template.
  - It waits for the link after v20. Pair it with 031's fix, and with pinning the three fallbacks.

  Fonts remain the template's job, or a later engine change that sets the document's `Defaults` after load.
- **C** only as a stop-gap, if A is refused and B is far off.

**Is the B lean viable without (c)?** No. Without a template that names its defaults, the blank document is Letter, with a browser-dependent Asian language, until the link. It also names a Korean font, permanently.

### Q4. `.ott` templates

**Recommendation: blank and `.odt` only for now.**

- Nextcloud core writes the chosen template's bytes into the new file (`lib/private/Files/Template/TemplateManager.php:165`, `newFile($filename, $template->fopen('rb'))`). So a chosen `.ott` becomes an `.ott` payload under an `.odt` name.
  - richdocuments records a `TemplateSource` (`FileCreatedFromTemplateListener.php:65-68`).
  - Collabora then loads the template URL and saves over it with `TakeOwnership,FromTemplate` (`kit/ChildSession.cpp:1006`).
  - We have no server-side engine. The equivalents are a first-open conversion in the WASM engine (plus a persisted "still a template payload" flag, like `richdocuments_template`), or a native LibreOffice on the server. Both are new work.
- In LOK, `FromTemplate` only stamps a new creation date (`init.cxx:3825-3836`), and loading already forces `AsTemplate=false` (`:2943-2950`). Our `saveAs(url,"odt",nullptr)` (`probe_engine.cpp:6069`) picks the filter by format. So a loaded `.ott` saves as a text document even without `FromTemplate`.
- The SDK renames every input to `.odt` before loading (`probe_engine.cpp:2930`), so content detection decides the format (cf. finding 013).

To offer `.ott` later, measure four things:

1. An `.ott` payload under an `.odt` name loads in the WASM engine, and the saved result has mimetype `application/vnd.oasis.opendocument.text` and no template marker in `meta.xml`.
2. The user's `.ott` styles, page layout and fonts survive the round trip byte-for-byte in `styles.xml`.
3. For a user who creates from `.ott` and never opens the file: what Files, WebDAV clients and desktop LibreOffice do with the payload.
4. The first-open conversion is idempotent, and it keeps the `watchUnsaved` and page-honesty invariants (the document is modified by the conversion before any typing).

## WHY (for the owner)

（內部備註，給擁有者看的白話版；不送上游。）

**今天的空白文件長什麼樣子。** 引擎一啟動，LibreOfficeKit 就把「系統語言」釘成 en-US（`desktop/source/lib/init.cxx:8347`），原生版、WASM 版都一樣。紙張大小是從這個設定算出來的，所以**不管誰開、用什麼瀏覽器，空白文件都是 Letter**。西文語言也固定是 en-US。

**亞洲語言反而跟著瀏覽器走。** 引擎啟動時會另外讀一次「作業系統的語言」，用來決定亞洲文字的預設語言。在 WASM 裡，這個「作業系統語言」是 Emscripten 從 `navigator.language` 拼出來的，也就是**瀏覽器的介面語言**：

- 瀏覽器是 zh-TW，就得到 zh-TW；
- 瀏覽器是英文（或任何拉丁字母的語言），就得到 **zh-CN**。

Nextcloud 的語言設定完全沒有參與。你自己剛好落在幸運的那一格（瀏覽器是 zh-TW），所以只會碰到 Letter 這一項。

**字型跟任何語言設定都無關。** 預設字型是用 en-US 查表，整個程序只算一次。亞洲字型那一格，因為字型包裡沒有表上任何一個名字，最後落到替代品；finding 113 量到的是 **`Noto Sans CJK KR`**。在 LiteCore 裡看不出差別，因為子集的五個家族共用同一套 TC 字形。但存出去的檔案寫的是韓文字型的名字，拿到別台電腦用 Word 或桌面版 LibreOffice 開，就可能畫成韓式字形。

**`Language=`（Collabora／richdocuments 的做法）能修什麼。** 它在每次載入時，把整個程序的系統語言和介面語言改寫成那個標籤。三種預設語言會對，紙張也會對（zh-TW 就是 A4，原生量到了）。但它有三個限制：

- **它修不了字型**：七組量測的字型完全一樣。
- 它要改引擎（開檔命令要能帶語言）。v20 的引擎已經凍結，**要等下一次連結**。
- 瀏覽器語言還是會漏進另外兩種文字的預設語言。例如德文瀏覽器加上 zh-TW 設定，西文預設會變成德文。要在引擎裡多加一行，把這些預設釘死。

**建議：先做 A（空白範本自己寫明預設），下一批連結再做 B（`Language=`）補上。**

- A 不動引擎、不動 profile，只改宿主 app 裡那個 2–3 KB 的空白檔，而且是**唯一能把字型名字修對**的路。
- 機制上它就是 richdocuments 的做法：app 裡放一個空白檔，由 template listener 寫進新檔，只是內容不同。
- 「不帶樣式、交給引擎」這個理由不成立：引擎給的不是中性的預設，而是 en-US、Letter 和韓文字型。
- 範本依使用者的 Nextcloud 語言挑選（zh-TW、en 各一份），就能做到每個人各自的預設。

**`.ott` 先不要。** Nextcloud core 會把 `.ott` 的內容直接寫進新的 `.odt` 檔。richdocuments 是靠 Collabora 在伺服器端重新載入範本再存回去；我們沒有伺服器端的引擎，要另外設計「第一次開檔時的轉換」。所以第一版只提供空白文件與 `.odt` 範本。

## FACT CHECK (R1–R6)

**R1, richdocuments 8.7.3.**

- `TemplateFileCreator('richdocuments','New document','.odt')` with the odt and ott mimetypes: **confirmed** (`lib/Listener/RegisterTemplateFileCreatorListener.php`).
- A null template leads to `putContent(getEmptyFileContent(ext))` with `emptyTemplates/template.odt`: **confirmed** (`FileCreatedFromTemplateListener.php:45-46`, `TemplateManager.php:473-485`). **Incomplete**, though: the same branch then records a `TemplateSource` pointing at the empty-template folder's `document.ott` (`:47-53`). So even the blank document goes through Collabora's template load, and `template.odt` is only a placeholder.
- 1,268 bytes, one `style:default-style` with only `use-window-font-color`, no language, font or page: **confirmed** (unpacked). `document.ott` has the same `styles.xml` and is 1,288 bytes.
- "For `.ott` it records a TemplateSource and leaves the file empty": **half false**. It does record the source (`:65-68`), or fills form fields (`:57-61`). But the file is not empty, because Nextcloud core has already written the template bytes (R3).

**R2, Collabora.** The `saveAs` with `"TakeOwnership,FromTemplate"` at `ChildSession.cpp:1002-1009`: **confirmed** (`:1006`). `Kit.cpp:1999` `",Language=" + lang`: **confirmed**.

**R3, Nextcloud core 34.0.2.** `createFromTemplate` at `:144-175` creates the file with the template bytes or empty, then dispatches `FileCreatedFromTemplateEvent`: **confirmed** (`version.php` 34.0.2; `:144`, `:165`, `:167`).

**R4, our engine.**

- Plain `documentLoad` at `:2992-2993`: **confirmed**.
- `documentLoadWithOptions` only under `#ifdef OXSDK_E2_UI_LANGUAGE`, `:2969-2991`, Makefile `:780`: **confirmed**.
- 031 is the cost seen: **confirmed, with a framing correction**. The comment at `:2975-2977` says `Language=` sets `setLanguageTag`/`setLocale`. It also rewrites `ooSetupSystemLocale`/`ooLocale` process-wide (D3), and that is what moves the paper and the languages.
- `saveAs(url, format, nullptr)` with no `FromTemplate` at `:6069`: **confirmed**.

**R5, font history.**

- 113: the one-family subset made the Asian slots fall to Liberation Sans, and 113 also measured the default Asian slot as `Noto Sans CJK KR` on v8 and on the five-family packs: **confirmed**.
- 114: `35-lang-normalize.conf` rewrote `zh-tw` to `tw` and was dropped in v17: **confirmed**. `base-r5-no35` ships no `35-*.conf`.
- 116: no Mono family: **confirmed**.
- `sdk/v18-writer-review-manifest.json` lists `cjk-sub-e10`, `base-r5-no35` and `fallback-fonts-r5`: **confirmed**. The v19 manifest has the same three.
- Core sources in `libreoffice-26-8/` and the native build in `native-lok-26-8/build/instdir`: **confirmed**.

**R6.**

- The frontend reads `@nextcloud/l10n` `getLanguage()`/`getLocale()`, maps the result to BCP-47 in `src/helpers/index.js:8-40`, and appends `&lang=` in `src/helpers/url.js` (`getWopiUrl`): **confirmed**. Those two calls return `document.documentElement.lang` and `data-locale`, which Nextcloud renders from the user's setting (`TemplateLayout.php:199-205`, `core/templates/layout.user.php:22`).
- Collabora turns it into `Language=`: **confirmed** (R2).
- "richdocuments' style-less skeleton gets its defaults from the language passed at load": **partly true**. Languages and paper, yes. The default fonts come from the server's en-US pool default, not from the tag (D2, D3).
- Our page can read the same attribute: **confirmed**. The host renders the editor as a `TemplateResponse` in Nextcloud's layout (`EditorController.php:173`). The value uses an underscore, for example `zh_TW`.

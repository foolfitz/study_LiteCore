# Facts for the next link batch: `Language=` (with 031's fix and the three fallbacks pinned) and new-document D12

Gathered 2026-10-16, read-only. Nothing was edited, built or run in the repo. No browser was used.

**Labels.** Every claim carries one of these:

- **[src]**: read in source by me, at the cited path:line.
- **[doc]**: stated in a repo document; I did not re-derive it.
- **[obs]**: observed by me read-only (grep, cmp, or reading a JSON or metadata file).
- **[inf]**: my inference, not measured.

**Trees.**

- Core source: `libreoffice-26-8/`, HEAD `671c848b…` [obs]. The WASM build trees `wasm-lite/build-headless-probe` and `build-a11y-gate0` both have `SRC_ROOT` pointing at it (`config_host.mk`) [obs].
- `native-lok-26-8/src` is also at `671c848b`. The six core files cited below are byte-identical between `native-lok-26-8/src` and `libreoffice-26-8` (`cmp`) [obs]: `init.cxx`, `langselect.cxx`, `paper.cxx`, `mslangid.cxx`, `syslocaleoptions.cxx` and `docnew.cxx`.
- analysis-1 records the native build as git HEAD `96dd0fce…` (`findings/evidence/new-document/analysis-1.md:121`) [doc]. That object does not exist in `libreoffice-26-8` [obs].
- Engine paths below are relative to `wasm_sdk_probe/`. Host paths are relative to `~/Projects/Nextcloud_Apps/litecore/`, whose HEAD is `1479e56` (0.2.24) [obs].

---

## 0. Summary

1. **The product does not pass `Language=` today.** The shipped engine (v20) calls plain `documentLoad` (`src/probe_engine.cpp:2992-2993`) [src].
   - `documentLoadWithOptions(…,"Language=" OXSDK_E2_UI_LANGUAGE)` exists only under `#ifdef OXSDK_E2_UI_LANGUAGE` (`:2969-2990`) [src].
   - Only the discovery profile `e2-locale-attribution` defines that macro, with `E2_LOCALE_LANGUAGE := zh-TW` (`Makefile:199-207`, `:776-780`, `:2624-2640`) [src].
2. **LOK forces en-US at init** (`init.cxx:8347`) [src]. With `Language=<tag>`, LOK rewrites `ooSetupSystemLocale` and `ooLocale` for the whole process (`init.cxx:2866`, `:2780-2786`). It also sets the LOK UI and locale tags (`:2860-2861`) and the view default (`:2858`). It captures the first load's tag for save time (`:2850-2856`). An invalid BCP-47 tag is **ignored silently** (`:2848`) [src].
3. **"The three fallbacks"** are `MsLangId::setConfiguredWesternFallback`, `setConfiguredAsianFallback` and `setConfiguredComplexFallback` (`include/i18nlangtag/mslangid.hxx:201-203`) [src]. They decide the default language of the two scripts that are not the system tag's script (`mslangid.cxx:135-166`) [src].
   - They are set once at startup by `langselect::prepareLocale` from the Emscripten-synthesized `LANG`, which comes from `navigator.language` [src/obs].
   - `Language=` does not touch them [src].
   - **"Pinned"** means the engine overwrites them explicitly (analysis-1 `:208`, `:228`, `:272`) [doc].
4. **Correction to analysis-1.** I read the browser leak as narrower than analysis-1 does: it reaches only the **Asian and Complex** slots. `prepareLocale` ends by overwriting the **Western** fallback with the system language (forced en-US) at `langselect.cxx:139-141` [src].
   - So analysis-1's example "de-DE browser + `Language=zh-TW` gives Western de-DE" (`analysis-1.md:116`, `:208`, `:272`) contradicts my reading [inf]. It is unmeasured on both sides.
   - Separately, the Asian default for **any** non-Asian browser is zh-CN (`mslangid.cxx:146-147`) [src]. So pinning is needed even with no "leak".
5. **"031's fix" is not defined anywhere.** Finding 031 lists four directions, none chosen (`findings/031-…md`, 「影響與修法方向（未決）」) [doc].
   - In today's engine, the format barrier **no longer decides on the localized string**: "The state broadcast no longer decides anything" (`probe_engine.cpp:1690-1705`). The paragraph-style verdict uses the HTML block tag (`:4889-4894`, `:4940-4942`) [src].
   - The localized string survives only in evidence counters (`crosstalkCount` and `earlyStateCount`, `:1696-1705`, `:1524-1525`) and in the state field `paragraphStyle` (`:1375-1378`). I found no product reader for either [src/obs].
6. **The 031 tripwire watches the wrong image.** `TestFinding031Tripwire` reads the build tree's `soffice.data.js.metadata` (1,358 files) (`tests/test_e2_profile.py:954-983`) [src]. The product has shipped the repacked `base-r5-no35` (1,240 files) since v17. Both have 0 `.mo` today [obs].
7. **D12 depends on a tag-mapping choice nobody has written down.** Paper comes from the **raw** `ooSetupSystemLocale` string, split at the first `-` (`paper.cxx:231`, `:362-368`) [src].
   - So `Language=en` gives **A4**, which agrees with the template, while `Language=en-US` gives **Letter** [inf from src; unmeasured].
   - Spec §3.5's premise, that `Language=` maps `en` to en-US and gives Letter, is an assumption about the page's mapping, not a property of LOK.
   - richdocuments passes bare `en` (`richdocuments/src/helpers/index.js:9`) [src].
8. **One tag cannot express every D2×D3 cell.** `Language=` carries a single tag that sets both the own-script language and the paper country. D2/D3 decouple those two.
   - With constant pins (Western en-US, Asian zh-TW, Complex hi-IN), the right tag reproduces the template's (W, A, paper) triple for the common cells [inf].
   - It cannot for a non-TW CJK user, or a Western user, whose explicit locale names a country of the other paper size. Example: `ja` with `en_US`. That needs per-user pins or a separate paper input [inf].
9. **Where the change lands.** It needs a relink and a new profile, because `oxsdk_document_open` has no option parameter (`src/sdk_api.cpp:67-82`) [src]. It also touches:
   - the worker, whose sha is pinned in the Makefile recipe and the manifest;
   - the SDK client;
   - the page, which hard-codes profile v20 (`web/e2-editor-app.js:3305`, `:50`);
   - and probably the host, as the place to compute the tag.
   - The open call itself sits in the **E1-C-bound** `editor-shell/editor-session.js:160-172` (`_openFresh`, which also runs on every recovery reopen) [src]. The language has to be injected without editing that file.
   - Pinning needs core-internal headers (`MsLangId`). The only precedent in this tree is a separate bridge object built with `-DLIBO_INTERNAL_ONLY` (`Makefile:115-121`, `:1101-1106`) [src].
10. **Test gap.** Nothing has measured `Language=` together with the 30 templates. N11 varied `LANG`, not the `Language=` option (`findings/evidence/new-document/native-roundtrip/README.md`) [doc].
    - N6 sees only the default style and the first page-layout (`tools/make_new_document_templates.py:267-299`) [src]. That is the "crafted-override blind spot" J2 deferred to this batch (`review/DISPOSITION.md:17`, `:87`) [doc].
    - The paper size is a cheap **positive control** that `Language=` reached LOK. Finding 031's 08-11 run had none [inf].

---

## ITEM 1: `Language=` with finding 031's fix and the three fallbacks pinned

### 1(a) Origin: decisions and rulings, quoted

- **The owner's choice, 2026-10-14** [doc]. From `handoff/HANDOFF-2026-10-14-v20-linked-v67-frozen-new-document-0.2.19.md:7`:
  > After reading analysis 1 the owner chose **A**: 「範本寫明預設＋下批連結補 Language=」.

  Same text in `specs/SPEC-M3-new-document.md:7` and `handoff/tasks/TASK-2026-10-14d-new-document.md:5`. The task adds: "The engine-side `Language=` waits for the link batch after v20 and is **not** part of this task."
- **The analysis recommendation, which is not a ruling** [doc]. `findings/evidence/new-document/analysis-1.md:5` says: "This is not an owner-delegated ruling; choices are given as options."
  - `:40`: "C first (the template carries the defaults; the host picks one per language), then (b) in the next link batch as the engine-level complement, together with 031's fix."
  - `:228`: "It waits for the link after v20. Pair it with 031's fix, and with pinning the three fallbacks."
  - `:208`, risk column for B: "de-DE browser + zh-TW Nextcloud gives Western de-DE unless the engine also pins the three fallbacks (`MsLangId::setConfigured*Fallback`, one more line)".
  - `:206`, the 031 column for B: "**latent, unchanged** … the day translations are packed, 031 fires. Fix 031 (compare ProgName/id) in the same batch."
  - `:230`: "Fonts remain the template's job, or a later engine change that sets the document's `Defaults` after load."
  - `:272` (zh-TW): 「瀏覽器語言還是會漏進另外兩種文字的預設語言。例如德文瀏覽器加上 zh-TW 設定，西文預設會變成德文。要在引擎裡多加一行，把這些預設釘死。」
- **The queue wording** [doc].
  - `HANDOFF-2026-10-14-…:49`: "`Language=` fixes the languages and the paper but not the fonts, and it needs a relink. It is queued for the next link batch, with finding 031's fix and the three fallbacks pinned."
  - The same handoff at `:109`: Markdown paste goes "together with `Language=` and 031's fix".
  - `HANDOFF-2026-10-14b-…:89`: "`Language=` with 031's fix and the three fallbacks pinned".
  - `HANDOFF-2026-10-14b-…:98`, under Later: "J2's work items, among them N6's crafted-override blind spot, which goes with `Language=`."
  - Later handoffs shorten it to "`Language=` with 031's fix": `HANDOFF-2026-10-14b:179`, `HANDOFF-2026-10-15:70`, `HANDOFF-2026-10-15b:100` and `HANDOFF-2026-10-16:98`. **The pinning half dropped out of the wording after 10-14b.**
- **The release text** [doc]. `handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md:137`: 「下一批連結補 `Language=`（擁有者選 A 時說的；交接 10-14b Next 3）。」 The owner has read this text and flagged nothing (header, `:9`).
- **What N6 is** [doc]. N6 is the new-document criterion that the saved `styles.xml` states its defaults (`SPEC-M3-new-document.md:168`).
  - J2 is the §34.3 review disposition of `check_m3_new_document.py` (`findings/evidence/new-document/review/DISPOSITION.md`), ruled by fable for the owner under task 10-14j.
  - Row `:17` ("opus N6, codex N6") reads: "`describe()` reads only `default-style[paragraph]` and the FIRST `page-layout`; four crafted saves … read `[]`". The disposition is **Registered**, with: "A typed-text language leak is what the `Language=` link batch should watch, where the environment language changes; work item there, not here."
  - Work item `:87`: "A typed-text language leak check at the `Language=` link batch."
  - The four crafted cases are listed in `review/opus-review.md:48-53`:
    1. an automatic style on the typed paragraph with zh-CN / KR / en-GB;
    2. `Standard` overriding the default;
    3. the master page pointing at a second, Letter layout;
    4. a font-face named TC whose family is KR.

    Opus's proposed fixes (`:58-60`) are to resolve the page through `master-page[@style:name='Standard']/@style:page-layout-name`, and to assert that no `style:text-properties` in `content.xml` or `styles.xml` sets a language, country or font-name that differs from the default.

### 1(b) Current behaviour

#### b1. The product engine passes no language [src]

- `wasm_sdk_probe/src/probe_engine.cpp:2969-2994` (`handleOpen`):
  ```cpp
  #ifdef OXSDK_E2_UI_LANGUAGE
    // Finding 031 measurement profile, discovery only.
    ...
    const std::string options = std::string("Language=") + OXSDK_E2_UI_LANGUAGE;
    emitStage("open.documentLoadWithOptions");
    gState.document = gState.kit->pClass->documentLoadWithOptions(gState.kit, fileUrl.c_str(), options.c_str());
  #else
    gState.document = gState.kit->pClass->documentLoad(gState.kit, fileUrl.c_str());
  #endif
  ```
  The comment at `:2981-2984` says "The tag is compiled in, so JS cannot choose it and this stays a build-level experiment rather than a surface."
- **Which builds define the macro.** Only `$(E2_LOCALE_BUILD)/%.o` does (`Makefile:776-780`: `-DOXSDK_E2_UI_LANGUAGE='"$(E2_LOCALE_LANGUAGE)"'`), with `E2_LOCALE_LANGUAGE := zh-TW` (`:206`). It feeds `dist/profiles/e2-locale-attribution`. The profile builder records `--ui-language` as `diagnostic.uiLanguage` (`Makefile:2635`; `tools/build_e2_discovery_profile.py:249-253`).
- **The product rule does not define it.** `$(E2_V20_BUILD)/%.o` (`Makefile:1548-1554`) defines `OXSDK_EDITOR_DISCOVERY`, `OXSDK_FINDING_016_SELECTION_BARRIER`, `OXSDK_E2_FORMAT_BARRIER`, `OXSDK_MERGE_KEY_UNDO` and `OXSDK_E2_V20_LINK_BATCH`. The v20 manifest has no `diagnostic` key [obs].
- **The open ABI has no place for options.** `oxsdk_document_open(requestId, bytes, byteLength, nameUtf8, nameLength)` (`src/sdk_api.cpp:67-82`; `src/sdk_api.h:51-53`). ABI 1.1 (`sdk_api.h:10-13`); editor ABI 4 (`editor_api.h:43`).
- **The worker's open** (`sdk/sdk-worker.js:1331-1344`) forwards only buffer and name. **The SDK client's open** (`sdk/document-sdk.js:408-421`) sends `{ buffer, name }`.
- **The product call site** is `editor-shell/editor-session.js:168-172`, inside `_openFresh` (`:146-…`):
  ```js
  this.document = await this.engine.open(sourceBytes.slice(0), { name: this._authorityName, transfer: true, timeoutMs: 180000 });
  ```
  - `this.engine = await this._engineFactory()` runs at `:160`, so every open, recovery reopens included, gets a new worker.
  - This file is in E1-C's bound set (`e1/editor-shell-bundle-v2.json` includes `editor-shell/editor-client.js`, `editor-session.js`, `state-machine.js` and `input/*.js`) [obs]. The guard is `tools/check_e1_c_bundle_intact.py`.
- **The page** hard-codes `workerUrl: "./profiles/e2-editor-v20/sdk-worker.js"` (`web/e2-editor-app.js:3303-3308`) and `PINNED_WASM_SHA256 = "313b08d5cb085897"` (`:50`).

#### b2. LOK without `Language=`: the init state [src]

- `lo_initialize`'s first-init block ends with `setLanguageAndLocale(u"en-US"_ustr)` (`libreoffice-26-8/desktop/source/lib/init.cxx:8347`).
  - That block runs before `osl_createThread(lo_startmain…)` (`:8381`) and `RequestHandler::WaitForReady()` (`:8383`).
  - The product engine uses that non-unipoll path. It calls `libreofficekit_hook_2("/instdir/program", "file:///tmp/user")` at `probe_engine.cpp:6240` under `#ifndef OXSDK_MAINLOOP_ENGINE`.
- `setLanguageAndLocale` (`init.cxx:2780-2786`) is `SetLocaleConfigString`, then `SetUILocaleConfigString`, then `Commit`.
  - `SetLocaleString` stores the **raw string** and calls `LanguageTag::setConfiguredSystemLanguage(m_aRealLocale.getLanguageType())`, where `m_aRealLocale` is `reset(string).makeFallback()` (`unotools/source/config/syslocaleoptions.cxx:398-415`, `:259-270`).
  - The raw string is what gets committed to `Setup/L10N/ooSetupSystemLocale` (`:112-115`, `:335-340`).
  - The early return when read-only is at `:403`.
- Without `Language=`, the LOK UI and locale tags stay `LANGUAGE_NONE` (`comphelper/source/misc/lok.cxx:75-86`). Under LOK, `SvtSysLocale::GetUILanguageTag()` / `GetLanguageTag()` return those tags (`unotools/source/misc/syslocale.cxx:160-172`).
- `lo_documentLoad` is `lo_documentLoadWithOptions(pThis, pURL, nullptr)` (`init.cxx:2799-2802`). So today's load and a `Language=` load share one code path and differ only in the `:2848-2869` block [src]. Also: `Language` is extracted from the options before `FilterOptions` is built (`:2845-2846`, `extractParameter` at `:1052-…`), so the filter never sees it.

#### b3. What `Language=<tag>` does in LOK [src]

The block is `init.cxx:2843-2869`, entered only when `!aLanguage.isEmpty() && LanguageTag::isValidBcp47(aLanguage, nullptr)` (`:2848`).

1. **Capture the first load's tag.** `static bool isLoading` makes `SfxLokHelper::setLoadLanguage` run once per process (`:2850-2856`). Save uses it to undo the UI-language dependency of field-master names. Upstream's comment in `sfx2/source/doc/objstor.cxx:3484-3510` cites `SwStyleNameMapper::GetTextUINameArray`, the same table as finding 031.
2. **Set the default for new views.** `SfxLokHelper::setDefaultLanguage(tag)` (`:2858`), read by new views at `sfx2/source/view/viewsh.cxx:2768-2771`.
3. **Set the LOK UI and locale tags.** `comphelper::LibreOfficeKit::setLanguageTag` and `setLocale` (`:2860-2861`). This re-keys `SwStyleNameMapper`'s UI-name tables (`sw/source/core/doc/DocumentStylePoolManager.cxx:2665-2676`) and changes `SvtSysLocale::GetLanguageTag()` from `LANGUAGE_NONE` to the tag (`syslocale.cxx:160-165`).
   - That last change plausibly moves number, date and currency defaults [inf]. The upstream comment at `:2864-2865` says "use with care - it sets it for the entire core, not just the document".
4. **Rewrite the process locale.** `setLanguageAndLocale(tag)` (`:2866`) rewrites `ooSetupSystemLocale` and `ooLocale` for the whole process, which changes the configured system language.
5. **Reset currencies.** `SvNumberFormatter::resetTheCurrencyTable()` (`:2868`).

**How the defaults follow.**

- **Languages.** `SwDoc::SwDoc` resolves `nDefaultLanguage{,_CJK,_CTL}` through `MsLangId::resolveSystemLanguageByScriptType` **at construction** (`sw/source/core/doc/docnew.cxx:382-397`).
  - That function returns the configured system language for its own script. For the other two scripts it returns the configured fallback, or zh-CN / hi-IN / en-US when unset (`i18nlangtag/source/isolang/mslangid.cxx:135-166`; zh-CN at `:146-147`; Western at `:156-161`).
- **Paper.** `PaperInfo::getSystemDefaultPaper()` reads `ooSetupSystemLocale` (`i18nutil/source/utility/paper.cxx:231`).
  - It splits at the first `-` into Language and Country (`:362-366`), then calls `getDefaultPaperForLocale` (`:368`, `:439-503`). Letter is used only for 14 countries (`:440-500`); everything else, **including an empty country**, is A4.
- **Fonts: not affected.** analysis-1's seven native arms found the fonts identical (`analysis-1.md:19`, `:117`) [doc].

**Measured natively by analysis-1** [doc] (`analysis-1.md:126-136`; raw output in `findings/evidence/new-document/probe-1-native-defaults/`):

| arm | `LANG` | option | Western / Asian / Complex | paper |
| --- | --- | --- | --- | --- |
| D | en_US | `Language=zh-TW` | en-US / zh-TW / hi-IN | A4 |
| E | zh_TW | `Language=en-US` | en-US / **zh-TW** / hi-IN | Letter |
| F | zh_TW | `Language=zh-TW` | en-US / zh-TW / hi-IN | A4 |
| G | en_US | `Language=zh-CN` | en-US / zh-CN / hi-IN | A4 |

Arm E shows the browser's Asian language surviving a Western tag. No arm used a bare tag such as `en`, or a non-en/zh environment such as `de_DE` [doc].

#### b4. How the browser reaches the defaults [src/obs]

- **Where `LANG` comes from.** The v20 loader synthesizes it: `var lang=(typeof navigator=="object"&&navigator.language||"C").replace("-","_")+".UTF-8";` and puts `LANG:lang` in the environment (`dist/profiles/e2-editor-v20/probe.js`, `getEnvStrings`) [obs].
  - `sdk/sdk-worker.js` has no `preRun` or `ENV` reference (0 matches) [obs].
  - I found no `"ENV"` export in the v20 loader [obs]. So the worker cannot override `LANG` without a link-time change, such as a pre-js or an exported `ENV` [inf].
- **How `prepareLocale` uses it** (`desktop/source/app/langselect.cxx:72-144`, called from `app.cxx:509`):
  - `:75` and `:77` call `setMsLangIdFallback` on `System::L10N::SystemLocale` and `::Locale`. Those are the LocaleBackend's view of `LANG`, per analysis-1 D1 [doc].
  - `setMsLangIdFallback` (`:50-66`) sets the Asian, Complex or Western fallback, according to the tag's script type.
  - `:129-134` reset the system language from `ooSetupSystemLocale`, which is already en-US because of `init.cxx:8347`.
  - `:139-141`: `LanguageTag docTag(LANGUAGE_SYSTEM); setMsLangIdFallback(docTag.getBcp47());` This sets the **Western** fallback to the system language, en-US.
- **Consequence** [inf from src].
  - After startup, the Western fallback is en-US whatever the browser is.
  - The Asian fallback is the browser's language only if the browser is Asian-script; otherwise it stays unset, which means zh-CN.
  - The Complex fallback is the browser's language only if the browser is complex-script; otherwise it stays unset, which means hi-IN.
- **This contradicts analysis-1** on the Western slot (`analysis-1.md:116`: "a de-DE browser with `Language=zh-TW` would give Western de-DE. This is an inference … not measured"). It is consistent with arms A, B, D and E. A native arm `LANG=de_DE.UTF-8` with `Language=zh-TW` discriminates: my reading predicts Western en-US, analysis-1's predicts de-DE.

#### b5. "The three fallbacks" and what "pinned" means

- **The API** [src]. `include/i18nlangtag/mslangid.hxx:197-203`:
  ```cpp
  /** @ATTENTION: these are _ONLY_ to be called by the application's configuration! */
  static void setConfiguredSystemUILanguage( LanguageType nLang );
  static void setConfiguredWesternFallback( LanguageType nLang );
  static void setConfiguredComplexFallback( LanguageType nLang );
  static void setConfiguredAsianFallback( LanguageType nLang );
  ```
  These are plain static stores (`mslangid.cxx:51-67`). `Language=` never calls them (`init.cxx:2843-2869`).
- **"Pinned"** [doc]. The engine itself sets all three explicitly, so the Asian and Complex defaults (and, per analysis-1, the Western one) no longer depend on `navigator.language` (`analysis-1.md:208`, `:228`, `:272`). No pinned **values** are specified anywhere I found [obs].
- **Constraints on where to pin** [inf from src].
  - Pinning must happen before `documentLoad*`, because `SwDoc`'s constructor resolves the defaults at `docnew.cxx:382-397`.
  - It must also happen after `prepareLocale`, which has finished by the time `lo_initialize` returns on this topology (`init.cxx:8383`, `WaitForReady`).
  - The product objects (`probe_engine`, `sdk_api`, `editor_api` and `unoembind_stub`; `Makefile:43-44`, `:56`, `:65`, `:1544`) include only LOK and UNO API headers (`probe_engine.cpp:58-66`).
  - The precedent for core-internal calls is the separate bridge object `a11y_tree_probe.o`, built with `-std=c++20 -DLIBO_INTERNAL_ONLY` (`Makefile:115-121`, `:1101-1106`). The Makefile notes its symbols were checked against linkdeps first.
  - `-li18nlangtag`, `-lutllo` and `-li18nutil` are on `wasm-lite/build-headless-probe/instdir/program/soffice.js.linkdeps` [obs].
  - The header warning above means this is outside upstream's intended use.
- **Pin values that would reproduce D2** [inf]. Pins of Western en-US, Asian zh-TW and Complex hi-IN, plus `Language=<the user's own-script tag>`, give D2's triple for every row of `BlankDocument::WESTERN` / `ASIAN` (host `lib/Template/BlankDocument.php:25-35`).
  - `de` with `Language=de-DE` gives de-DE / zh-TW (pinned) / hi-IN (pinned).
  - `zh_TW` with `Language=zh-TW` gives en-US (pinned) / zh-TW / hi-IN.
  - Constant pins break for a non-TW CJK user whose locale demands the other paper size; see 2(b).

#### b6. Finding 031: what it is, its status, and what is left to fix

- **What it says** [doc] (`findings/031-styleapply-postcondition-compares-a-localized-ui-name.md`, 2026-08-11). The E2-A barrier matched the `.uno:StyleApply` state payload against the whole strings `Heading 1` and `Body Text`. Those are **UI names**, from a table keyed by UI language (`SID_STYLE_APPLY` carries a `UIName` but no ProgName). Under a translated UI, the two paragraph-style actions would time out as `MUTATION_OUTCOME_UNKNOWN` although the document is right.
  - It is latent because the shipped image packs **no `.mo`**.
  - The measurement profile `e2-locale-attribution` (zh-TW) gave a **false negative with no positive control**.
  - Evidence: `findings/evidence/sdk-e2/discovery/state-readback/locale-attribution/chrome/result.json`.
  - Fix directions (`:…影響與修法方向（未決）`): (1) read the ODT style name; (2) fill `StyleNameIdentifier`, which changes core; (3) narrow the promise to the list actions; (4) compile the translations in, not recommended. **None chosen.**
- **Partly superseded already** [doc]. After finding 030, the owner chose on 2026-08-11 that the postcondition reads the document (the selection's `text/html`). SPEC E2-A records: 「分辨用的是 HTML 結構而非 UI 名稱，所以 2.5 節的 finding 031 曝險在段落樣式那兩個動作上一併解掉」 (`specs/SPEC-E2-A-paragraph-format-discovery.md:349-351`; also `findings/README.md:42`, row 030; `handoff/HANDOFF-2026-08-08-session-state.md:411`).
- **What the engine does today** [src].
  - `observeFormatBarrierPayload` (`probe_engine.cpp:1690-1705`) has the comment "The state broadcast no longer decides anything -- finding 030 showed it is silent exactly when the answer would matter most." It only increments `crosstalkCount` or `earlyStateCount`.
  - `formatBarrierPostconditionMet()` still compares `gEditorState.paragraphStyle` against `kHeadingReportedStyles = {"Heading 1"}` and `kBodyReportedStyles = {"Body Text"}` (`:1460-1480`, `:4570-4573`, `:4575-4583`, `:5348`).
  - The verdict for `ParagraphStyle` is `everyBlockHasTag(parsedBlocks, expectedBlockTag)` with `h1`/`p` (`:4889-4894`, `:4940-4942`, `:5354`).
  - The dispatch sends the ProgName `Text body` / `Heading 1` (`:4570-4571`, `:4585-4590`).
  - The readback parser does not look at `class=` (`format_readback_text.hpp` and `probe_engine.cpp` have no `western` / `class=` match) [obs].
- **What still carries the localized name** [src/obs].
  1. The two counters. Their only tool consumers are E2-A discovery: `tools/build_e2_discovery_profile.py` and `e2/discovery-matrix-v1.json`. No M3 judge reads them.
  2. `editorState.paragraphStyle` (`probe_engine.cpp:1375-1378`), read only by `web/e2-format-discovery-app.js`. No product reader in `editor-shell-v2/`, `sdk/` or `web/e2-editor-app.js`.
  3. The stale comment at `:2971-2984`, which says the postcondition "compares whole strings", and the `TestFinding031Tripwire` docstring (`tests/test_e2_profile.py:955-966`), which says the barrier "matches the paragraph style postcondition against the whole strings".
- **The tripwire's target** [src/obs]. It reads `wasm-lite/build-headless-probe/workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.metadata` (`tests/test_e2_profile.py:968-983`): 1,358 files, 0 `.mo`.
  - The product ships `dist/profiles/resources/base-r5-no35.1700ed39031eaf49.metadata`: 1,240 files, 0 `.mo`. Both carry `Langpack-zh-TW.xcd`.
  - A future pack that adds `.mo` would not trip the test [inf].
- **The other 031 test.** `TestLocaleAttributionProfile` (`tests/test_e2_profile.py:826-848`) asserts that only the locale profile compiles a language in, checking four discovery manifests. Its docstring says: "Finding 031: the UI language is a build-level experiment, not a surface." A product `Language=` makes that premise false for the product, but the test checks no product manifest, so it would stay green [inf].
- **Bottom line** [inf]. With no `.mo` packed, a `Language=zh-TW` product cannot trip 031: arms D–G kept English UI names, and finding 031's own run did too. "031's fix" in this batch is therefore precautionary. The candidate scope:
  - (i) remove or neutralize the localized compare in `formatBarrierPostconditionMet` / `styleCandidates`, or make it ProgName/id-based as analysis-1 suggests;
  - (ii) say what `paragraphStyle` is, a UI name;
  - (iii) re-point the tripwire at the shipped pack;
  - (iv) update finding 031's status to say the barrier's exposure was closed by the HTML readback.

  Which of these is "the fix" is undecided.

#### b7. Where the page would get a language [src]

- **The host renders the editor** inside Nextcloud's `user` layout (`lib/Controller/EditorController.php:173-177`). Its initial state `config` carries user, file, editor and `filesUrl`, **no language or locale** (`:159-171`).
- **Nextcloud's layout** sets `<html lang="…">` from `findLanguage()` with `_` replaced by `-` (`nextcloud/lib/private/TemplateLayout.php:199`, `:203`). It sets `data-locale` from `findLocale($lang)` (`:200`). Both are rendered at `core/templates/layout.user.php:22`.
  - analysis-1 `:316` says the value "uses an underscore, for example `zh_TW`". For `lang` that is **wrong**: it is `zh-TW`. `data-locale` does use underscores.
  - `findLocale` turns a zh_TW user with no locale into `en_US` (`SPEC-M3-new-document.md:40-42`) [doc]. D3 refuses that input ("不用 Nextcloud 的 `findLocale()`", `:217`) [doc].
- **The standalone page** hard-codes `<html lang="zh-TW">` (`web/e2-editor.html:2`). When hosted, the host re-wraps only the body and style, so Nextcloud's `<html>` is the one in effect (`EditorController.php:150-177`).
- **richdocuments** reads `getLanguage()`, replaces `_` with `-`, and special-cases `de-DE`→`de`, `es-419`→`es-MX`, `en-GB`+`en_AU`→`en-AU` and a de/fr/it Swiss whitelist. Otherwise it passes the language as is, so `en` stays `en` (`~/OSSII/NC_modules/richdocuments/src/helpers/index.js:8-45`, `url.js:45`).

### 1(c) Decided vs open

**Decided** [doc]:

- `Language=` goes into the next link batch (owner, 10-14, choice A).
- It is paired with 031's fix and with pinning the three fallbacks (analysis-1's recommendation; the queue text up to 10-14b).
- Fonts are out of scope; the template carries them (analysis-1 `:18`, `:230`).
- A typed-text language-leak check belongs to this batch (J2, `DISPOSITION.md:17`, `:87`).
- Compiling `make` is the owner's job, and the current profile is archived first (`HANDOFF-2026-10-16:106`; global rule).

**Open** (none of these is written anywhere I found):

1. **Which tag is passed per user**, and computed where:
   - the page from `document.documentElement.lang`;
   - the page from `data-locale` (D3 rejects it);
   - the host from `IL10NFactory::getUserLanguage` plus the explicitly set locale, the D3 input, through initial state.

   This includes whether `en` goes as `en` or as `en-US` (D12, below).
2. **The pin values**: constants (en-US, zh-TW, hi-IN, matching D2) or per user from the host. Also whether to pin Western at all, given b4.
3. **The engine API shape**:
   - a new export, or an extended open ABI (a new `open` with options, or a separate "set document language" call before open);
   - whether the engine validates the tag itself, since LOK ignores an invalid one silently (`init.cxx:2848`).
4. **Where the option goes through the shell** without editing E1-C-bound `editor-session.js`: the `engineFactory` wrapper, the SDK-client default, or a `NarrowEditorV2Session` override of `_openFresh`. Every recovery reopen must carry it too.
5. **What "031's fix" consists of** (b6 (i)–(iv)), and whether the tripwire is re-pointed.
6. **The manifest declaration**: a new `editorContract` field, as `pageRectangles` was declared through `--page-rectangles`, gated in the worker the way `DOCUMENT_EXPORT_OPERATIONS` gates exports (`sdk/sdk-worker.js:213-223`). Also whether the declaration names the pinned values.
7. **Whether the batch also wants the side effects** `Language=` brings: LOK locale for number and date formats, the currency table, `ooLocale`.
8. **Which of analysis-1's two Western-slot predictions holds** (b4). It decides whether the Western pin does anything.

### 1(d) What changes, and which bindings it touches [src for the existing bindings; inf for what moves]

| Layer | Change | Binding touched |
| --- | --- | --- |
| Engine C++ | `handleOpen` calls `documentLoadWithOptions` with a runtime tag (`probe_engine.cpp:2969-2994`); a new or changed SDK export in `sdk_api.cpp`/`.h`; the pin calls, probably in a bridge object with `-DLIBO_INTERNAL_ONLY` | **A relink and a new profile** (e2-editor-v21): new wasm, loader and manifest hashes. A new define like `OXSDK_E2_V20_LINK_BATCH`, so v8, v15, v19 and v20 and the E1-C `e1-editor-v1` TU stay preprocessor-identical (`probe_engine.cpp:1752-1754`; M1-1, `tools/check_merge_key_undo_scope.py --carrier …`, `Makefile:3629-3633`). The export list (`Makefile:1557-1569` pattern), X1 and `what_the_link_ships` |
| Worker | forward the tag (`sdk/sdk-worker.js:1331-1344`) | The v20 recipe pins the **tree's** worker: `E2_V20_WORKER_SHA256 := 478d0da1…` with `sha256sum -c` (`Makefile:1546`, `:1590`). Editing `sdk/sdk-worker.js` makes the v20 recipe refuse, by design; v19 builds from an archived worker (`:1506`) |
| SDK client | `open(input, {…, language})` (`sdk/document-sdk.js:408-421`) | A shell bundle generation, now v73 (`tools/build_e2_c_shell_bundle.py:757`). Not E1-C-bound; `document-sdk.js` is not in `e1/editor-shell-bundle-v2.json` [obs] |
| Shell | inject per open | Do **not** touch `editor-shell/editor-session.js` (E1-C bound). Use an override in `editor-shell-v2/` or the page's `engineFactory` |
| Page | read or receive the tag; switch `engineFactory` to v21; new `PINNED_WASM_SHA256` | Page sha: the host `engine/MANIFEST.json`, the nine runners' `PAGE_SHA256` pins, and `check_m3_new_document.py` `ENGINE_BUILD_ID` / `PAGE_SHA256` (`:107-108`) |
| Manifest | a new `editorContract` declaration | `tools/build_e2_editor_v4_profile.py` gains a flag, as `--page-rectangles` did (`Makefile:1598-1599`) |
| Host | optional: pass the D3-consistent tag in initial state (`EditorController.php:159-171`) | Host version bump; `check_m3_new_document.py` `HOST_COMMIT` / `HOST_VERSION` (`:99-100`) |
| Templates | none for `Language=` itself | `blank/MANIFEST.json` `e5cdb8e2…` (`check_m3_new_document.py:101`) unchanged unless D12 changes D3 |

### 1(e) Tests, criteria and evidence that bear on it, and a measurement that would show it works

**Existing:**

- `tests/test_e2_profile.py:826-848` (`TestLocaleAttributionProfile`) and `:954-983` (`TestFinding031Tripwire`).
- The 031 run: `findings/evidence/sdk-e2/discovery/state-readback/locale-attribution/chrome/`.
- analysis-1's native arms D–G, from the 40-line `findings/evidence/new-document/probe-1-native-defaults/tool/lok_defaults_probe.cpp`, which already takes an options argument (`argv[5]`, `:14`, `:22`) [src].
- N11's native round trip (`findings/evidence/new-document/native-roundtrip/README.md`): 8/8, but varied by **`LANG` only**, no `Language=` [doc].
- N6 and N12 (`SPEC-M3-new-document.md:168`, `:175`).
- `describe()` / `compare()` (`tools/make_new_document_templates.py:267-308`).

**A measurement that would show it works** [inf; built from analysis-1 D5, `analysis-1.md:147-167`, which was never run on WASM as far as I can find]:

1. **Native first.** This needs no relink, only the existing probe; compiling it is the owner's call under the global rule. Add arms to analysis-1's table:
   - `LANG=en_US` + `Language=en`. Prediction from source: Western en-US, paper **A4**.
   - `LANG=en_US` + `Language=en-US`: Letter.
   - `LANG=de_DE` + `Language=zh-TW`. Western is en-US by my reading, de-DE by analysis-1's; this is the discriminator.
   - `LANG=ja_JP` + `Language=en-US`: Asian ja-JP. This is the positive control for the leak that pinning must remove.
   - Each of the 30 templates under `Language=`: does `styles.xml` stay equal to the no-option save?
2. **WASM after the link.**
   - Open richdocuments' style-less `template.odt` in v21. Run Chrome with `--lang=zh-TW` and `--lang=en-US`, and Firefox with `intl.accept_languages`, each with the page passing the per-arm tag. Save and read `styles.xml`.
   - Pass: the Asian language is identical across the browser-language arms (pinning works). The paper and Western language follow the tag.
   - Control: v20 on the same arms shows zh-TW vs zh-CN, which is analysis-1's prediction.
   - The paper (A4 vs Letter) is the **positive control** that the option reached LOK. Finding 031's run had none; a silently ignored invalid tag (`init.cxx:2848`) would show up as Letter.
3. **New-document count on v21.** N1–N6 must still pass. The browsers' `styles.xml` stays byte-identical per arm (0.2.19: `5addf7dc…` / `09d2dd95…`, `SPEC-M3-new-document.md:245-250`).
   - Add the typed-text leak check: no `style:text-properties` in `content.xml` or `styles.xml` with a language, country or font-name differing from the default. Resolve the page through the master page (opus `:58-60`).
   - Source reading suggests the input-language path is inert on the headless frame: `SvpSalFrame::GetInputLanguage()` returns `LANGUAGE_DONTKNOW` (`vcl/headless/svpframe.cxx:461-464`; used at `sw/source/uibase/docvw/edtwin.cxx:1443`, `:6598-6605`) [src]. Whether the WASM build uses that frame was not checked [inf].
4. **031.** It cannot be observed until translations are packed (finding 031). The verifiable parts are the source changes in b6 and a tripwire that reads the shipped pack.

---

## ITEM 2: new-document D12 (Letter vs A4 for `en` once `Language=` exists)

### 2(a) Origin, quoted [doc]

All rulings below are by fable for the owner, 2026-10-14 (`specs/SPEC-M3-new-document.md` §6, `:209-228`): 「每一條都是本輪我替擁有者決定的…擁有者看了不同意可以推翻」.

- **D3** (`:216-218`): 「紙張跟「地區」不跟語言，而且只認使用者明確設的地區：設了 locale（或系統 `default_locale`／`force_locale`）就用它的國家；沒設就看語言代碼有沒有地區段（zh_TW→TW、en→沒有）；都沒有→A4。…**不用 Nextcloud 的 `findLocale()`**…代價：美國使用者語言 `en` 沒設 locale 會拿到 A4，要到 Nextcloud 個人設定把地區設成 en_US（或管理者設 `default_locale`）。」
- **D12** (`:228`): 「**D12 一併登錄的不一致**（3.5）：下一批 `Language=` 對 `en` 給 Letter、本輪範本對 `en` 沒設地區給 A4——到那一批再一起決定，本輪不處理。」
- **§3.5** (`:133-139`): 「已知的不一致，登錄不處理：下一批連結的 `Language=` 會把語言 `en` 對到 en-US→引擎自己對**其他**不帶樣式的檔案給 Letter；本輪的空白範本對 `en` 沒設地區給 A4（3.2）。兩者的對象不同（新建的檔 vs 使用者帶來的無樣式檔），到那一批再一起決定。」
- **§7.4** (`:287-288`): 「D12（§3.5）進下一批連結的 `Language=` 討論：`en` 的紙張。」 and 「`Language=`（分析 1 的 B）在 v20 之後的連結批次；本輪的範本不受它影響（檔案自己寫明）。」
- **Release text decision F**, 2026-10-15 by opus with the owner's delegation; the owner later read the text and flagged nothing (`RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md:310-314`): 「決定：寫，照 3.1 現在的寫法。」 The published sentence (`:133`) is 「**代價：美國使用者語言 `en` 沒設 locale 會拿到 A4**，要到個人設定把地區設成 en_US。」
- **Queue**: `HANDOFF-2026-10-14:85` "new-document's D12 (Letter versus A4 for `en` once `Language=` exists)", and every later "next link batch" list.

### 2(b) Current behaviour

- **The template path, shipped since 0.2.19** [src]. `BlankDocument::choose($language, $locale)` (host `lib/Template/BlankDocument.php:49-67`):
  - The country comes from the explicit locale; failing that, from the language code's region; failing that, none (`country()`, `:70-80`).
  - Letter applies only for `LETTER_COUNTRIES` (`:40`); otherwise A4.
  - `en` with no locale has country `null` (no region segment), so the user gets **A4** and the file `en-US_zh-TW_A4.odt`.
  - The EN counting arm uses `en` + `en_US`, which gives Letter (`SPEC-M3-new-document.md:153-154`).
- **The engine path, which exists only once `Language=` exists** [src + inf]. Paper comes from the raw `ooSetupSystemLocale` string (`paper.cxx:231`, `:362-368`). With `setLanguageAndLocale(tag)` storing the tag verbatim (`syslocaleoptions.cxx:398-415`, `:335-340`):
  - `Language=en` gives Country `""`, so **A4**. Western is still en-US, because `makeFallback` derives the system language (`:268`) [inf; unmeasured].
  - `Language=en-US` gives US, so Letter (arm E's Letter is consistent [doc]).
  - Therefore **D12's inconsistency exists only if the page or host maps `en` to `en-US`**. §3.5 assumes that mapping ("會把語言 `en` 對到 en-US"); LOK does not impose it.
- **Who sees the engine's paper** [doc/inf]: style-less files the user brings or that other apps create (richdocuments' own blank `template.odt` has no page layout, `analysis-1.md:289`), and new page styles. Files made from our templates state their own page (N6 / N11).
- **One tag cannot express every D2×D3 cell** [inf from src]. The tag's script gives one language; its region gives the paper. Pins give the other two languages.
  - With constant pins (en-US / zh-TW / hi-IN), these rows match the template's triple:

    | Nextcloud lang + locale | tag | Western / Asian / paper |
    | --- | --- | --- |
    | `en` + none | `en` | en-US / zh-TW / A4 |
    | `en` + `en_US` | `en-US` | en-US / zh-TW / Letter |
    | `zh_TW` + none | `zh-TW` | en-US / zh-TW / A4 |
    | `zh_TW` + `en_US` | `en-US` | en-US / zh-TW / Letter |
    | `de` + none | `de-DE` | de-DE / zh-TW / A4 |
    | `es_MX` + none | `es-MX` | es-MX / zh-TW / Letter |
    | `ja` + none | `ja-JP` | en-US / ja-JP / A4 |

  - **Not expressible** with constant pins:
    - `ja` + `en_US` (template: en-US / ja-JP / Letter). Letter needs a US region, but the Asian slot is the pin, zh-TW.
    - A Western user whose explicit locale names a country of the other paper size, for example `de` + `en_US` (template: de-DE / zh-TW / Letter). It would need a tag like `de-US`, whose `makeFallback` result is unknown.
  - Per-user pins from the host, or a paper input independent of `Language=`, would close these cells.

### 2(c) Decided vs open

**Decided** [doc]:

- D3 for templates. The A4 cost for a bare `en` is documented in the release text, decision F.
- D12 is to be decided "at that batch, together with `Language=`".

**Open:**

1. **The `en` tag mapping.** Bare `en` gives A4 and agrees with D3. `en-US` gives Letter and creates D12's inconsistency.
2. **Whether D3 itself changes**, treating bare `en` as US. That changes `BlankDocument::country()` / `choose()`, N12's table and the release text §3.1 sentence; the template set stays the same 30 files [inf].
3. **Whether the engine-path paper should follow D3 exactly.** That needs host-side computation, because `data-locale` is `findLocale` (b7), and per-user pins or a paper input for the cells above.
4. **Whether the two paths may disagree**, given their different objects (spec §3.5), and if so how the release text says it.

### 2(d) What changes, and which bindings it touches [inf]

- If only the tag mapping is chosen: page or host code (1(d)). No template change.
- If D3 changes: host PHP (`lib/Template/BlankDocument.php`), a host version bump, `check_new_document_choice.py` (N12, 174 inputs) and the EN/TW arm expectations if they move. The `blank/` bytes and `MANIFEST.json` `e5cdb8e2…` stay unchanged, because both `en-US_zh-TW_A4` and `_Letter` already exist. Also the release text §3.1 and decision F.

### 2(e) Tests and evidence

- N2, N6 and N12 (`SPEC-M3-new-document.md:164`, `:168`, `:175`).
- `check_m3_new_document.py` bindings (`:99-108`).
- The 0.2.19 count (`runs/2026-10-14T035226Z.json`): the TW arm `zh_TW` + none gave A4; the EN arm `en` + `en_US` gave Letter (`SPEC-M3-new-document.md:245-250`).
- **No arm has `en` with no locale**, which is the D12 cell. Proposed:
  - A native `Language=en` vs `Language=en-US` pair on the style-less template, settling the A4/Letter prediction in 2(b).
  - A third runner arm, `en` + none, that exercises the D12 cell on both paths: the template (expect A4) and a style-less file opened under v21 (expect whatever D12 decides).

---

## (f) Interactions

1. **Item 1 against Item 2.** D12 is not separate work. It is the choice of the `Language=` tag for `en`, plus whether the pins and the paper follow D3. Decide the tag-mapping rule once; it settles D12 [inf].
2. **`Language=` against the 30 templates** [inf from src]. The templates state default-style languages, fonts and an explicit `Mpm1` page layout (`SPEC-M3-new-document.md:106-114`). `Language=` changes engine beliefs, not imported attributes, so the saved defaults should not move.
   - Unmeasured: N11 varied `LANG`, never the `Language=` option. The new-document count on v21 is the check.
   - Per-browser byte identity of `styles.xml` (0.2.19) should hold. If pins work it holds a fortiori, since the browser feeds only fallbacks.
   - It could change if `Language=` alters anything else that `styles.xml` serializes, for example number styles. Not observed.
3. **The typed-text leak** (J2) [doc/inf]. A paragraph typed into a template-made file could gain an automatic style with another language only through an input-language path. That path reads `LANGUAGE_DONTKNOW` on the headless frame (1(e) 3).
   - The leak J2 wants watched is "where the environment language changes" (`DISPOSITION.md:17`). Pins remove the browser from that environment.
4. **031 against `Language=`** [doc/inf]. With no `.mo`, `Language=zh-TW` keeps English UI names: arms D–G and finding 031's run. The barrier verdict uses HTML tags anyway, so `Language=` cannot trip 031 in this batch. The packing of translations does: the tripwire's job, currently pointed at the build image.
   - Save-time field-master names depend on the UI tag. LOK compensates with the load language (`objstor.cxx:3484-3510`).
5. **Fonts.** `Language=` does not fix the Asian default font of style-less files (`Noto Sans CJK KR`, inferred for e10 from finding 113; `analysis-1.md:95`) [doc]. Templates remain the only fix (D5). A style-less file opened under v21 still saves KR.
6. **The rest of the batch.** Markdown paste (A) and the other queued link items share the same relink, worker, SDK client and page bindings (`HANDOFF-2026-10-16:97-105`) [doc]. One worker sha and one page sha move for all of them together.

## Discrepancies found while reading (for whoever plans the batch)

- `analysis-1.md:116`, `:208`, `:272`: the de-DE-browser Western leak contradicts `langselect.cxx:139-141` [inf]. Unmeasured both ways.
- `analysis-1.md:316`: "The value uses an underscore". Nextcloud's `<html lang>` uses a hyphen (`TemplateLayout.php:203`); `data-locale` uses underscores.
- `SPEC-M3-new-document.md:138` / D12 assume `Language=` maps `en` to en-US. That is a mapping choice; bare `en` gives A4 by source reading.
- `analysis-1.md:206` says the 031 "barrier matches". The barrier no longer decides on that string (`probe_engine.cpp:1690-1705`), but the comments at `:2971-2984` and in `tests/test_e2_profile.py:955-966` still describe the old design.
- `TestFinding031Tripwire` watches `wasm-lite/…/soffice.data.js.metadata`, not the shipped `base-r5-no35` pack.
- The "three fallbacks pinned" clause dropped out of the queue wording after `HANDOFF-2026-10-14b:89`.

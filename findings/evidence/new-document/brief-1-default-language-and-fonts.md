# Analysis brief 1: what language, fonts and page does the WASM engine give a document that carries no styles?

**Context.** In yesterday's hand test, the owner could not create a new document in Nextcloud. The host app (`~/Projects/Nextcloud_Apps/litecore`, 0.2.18 `96a87d8`) registers only a Files action, "Open in LiteCore" (`src/files.js`). It has no entry in the "+ New" menu.

The owner wants new documents created the way richdocuments and Collabora do it. For the blank document's content the owner leans toward **B: richdocuments' minimal skeleton**, which leaves styles to the engine. The owner then asked (2026-10-14): 「"WASM 引擎的預設語言和字型" 是需要解決的問題，幫我發給fable分析」.

You are asked to analyse, diagnose and recommend. This is not an owner-delegated ruling. Where a choice belongs to the owner, give it as options A/B/C with your recommendation.

## What the main session read (claims to check, not conclusions)

- **R1, richdocuments (local fork at `~/OSSII/NC_modules/richdocuments`, version 8.7.3; upstream-shaped for this part).**
  - `lib/Listener/RegisterTemplateFileCreatorListener.php` registers `TemplateFileCreator('richdocuments', 'New document', '.odt')` with mimetypes odt and ott.
  - `lib/Listener/FileCreatedFromTemplateListener.php`: when the template is `null`, it calls `putContent(getEmptyFileContent(ext))` with `emptyTemplates/template.odt`.
  - That file is 1,268 bytes. Its `styles.xml` holds only `<style:default-style style:family="paragraph"><style:text-properties style:use-window-font-color="true"/></style:default-style>`. It sets no language, no font and no page layout.
  - For `.ott` templates it records a `TemplateSource` and leaves the file empty.
- **R2, Collabora (`~/LibreOffice/collabora_online`).**
  - For a TemplateSource, the kit loads the template and immediately calls `saveAs(url, nullptr, "TakeOwnership,FromTemplate")` (`kit/ChildSession.cpp:1002–1009`).
  - Every load passes the user's language as a LOK load option, `",Language=" + lang` (`kit/Kit.cpp:1999`).
- **R3, Nextcloud core 34.0.2 (`~/Projects/Nextcloud_Apps/litecore/nextcloud`).** `TemplateManager::createFromTemplate` (`lib/private/Files/Template/TemplateManager.php:144–175`) creates the file with the template's bytes, or empty when there is no template. It then dispatches `FileCreatedFromTemplateEvent`.
- **R4, our engine (`wasm_sdk_probe/src/probe_engine.cpp`).**
  - The product loads with plain `documentLoad` (`:2992–2993`) and passes no `Language=`.
  - `documentLoadWithOptions(…, "Language=" OXSDK_E2_UI_LANGUAGE)` exists only under `#ifdef OXSDK_E2_UI_LANGUAGE`, "Finding 031 measurement profile, discovery only" (`:2969–2991`; Makefile `:780`).
  - Finding 031 is the cost already seen: with a UI language set, style names come back localized and a postcondition compared one of them.
  - Save uses `saveAs(url, format, nullptr)`, with no `FromTemplate` (`:6069`).
- **R5, font history that bears on this.**
  - Finding 113: the CJK subset kept only the TC family name, so the defaults and the SC/JP/KR Asian fonts fell back to Liberation.
  - Finding 114: fontconfig's `35-lang-normalize.conf` rewrote `zh-tw` to `tw`, which gave Latin line height. It was fixed in v17 by dropping that file.
  - Finding 116: there was no Mono family.
  - The shipped resource packs are listed in `wasm_sdk_probe/sdk/v18-writer-review-manifest.json` (`cjk-sub-e10`, `base-r5-no35`, `fallback-fonts-r5`). Core sources are in `libreoffice-26-8/`; the native 26.8 build is in `native-lok-26-8/build/instdir`.

## Questions

1. **What does a style-less ODT become in the shipped WASM engine (profile `e2-editor-v19`, the engine behind 0.2.18)?**
   - The Western, Asian and CTL default languages, and the default font per script.
   - The paper size. LibreOffice derives it from the locale, so an en-US engine would give Letter. Taiwanese users expect A4.
   - Whether the engine's answer differs from native 26.8 started with a zh-TW locale.

   Diagnose from source and from the profile's configuration (what locale the WASM engine believes it runs in, and where that comes from). Then design a discriminating measurement and say what each outcome would mean. One example: save the blank document through the engine and read `styles.xml`, because a save writes the effective defaults out explicitly. If a measurement is cheap and safe, run it; otherwise specify it for an executor.
2. **Is that a product problem, and for whom?**
   - Chinese glyph forms (SC versus TC for the same code point), line height (the 114 shape), page size, and spell-check or hyphenation language.
   - Which users are affected: the owner, institutional buyers in Taiwan, users whose Nextcloud language is not Chinese.
3. **Fix options under the owner's B lean.** For each, give the cost:
   - whether it needs a relink, or only a repack, page or host change;
   - its interaction with finding 031 (localized style names) and with the paragraph-style UI;
   - whether it is per user or per engine.

   Candidates I can see, and you may add others:
   - (a) the engine's default locale set in the profile's configuration (for example an `.xcu` in a resource pack: `L10N`, `Linguistic DefaultLocale` / `DefaultLocale_CJK`, VCL default fonts);
   - (b) Collabora's way: `Language=` per load from the user's Nextcloud language, which the page would pass. This needs an engine change. v20's engine source is final at `82af92ca` per ruling 6, so say whether this waits for the next link;
   - (c) the blank template itself carries explicit defaults (the owner's option A, which they leaned away from; say whether B is viable without it);
   - (d) setting the defaults after load through UNO commands from the page.
4. **`.ott` templates.** Should the first version offer the text-template mimetype, so that Nextcloud's template picker lists users' `.ott` files? Our save passes no `FromTemplate`. Say what has to be measured before it can be offered, or recommend blank and `.odt` templates only for now.

## Limits

- Read anything. Native probes and scratch scripts go in your scratchpad.
- Two executors are committing in this tree right now: one in `wasm_sdk_probe/editor-shell-v2/`, one in `wasm_sdk_probe/tools/` plus `tests/`. Do not edit tracked files except your output below.
- No build, no link, no `make` that builds anything, no host install, no push.
- If you drive a browser against a WASM profile, use the existing runners or probes read-only, and count `chrome` processes first. The owner's desktop may be in use.

## Output

Write `findings/evidence/new-document/analysis-1.md` with these sections:
- `## SUMMARY` (at most 30 lines);
- `## DIAGNOSIS` (Q1, with file:line and any measurement, its raw output kept next to it under `findings/evidence/new-document/`);
- `## IMPACT` (Q2);
- `## OPTIONS` (Q3–Q4, with A/B/C for the owner and your recommendation);
- `## WHY (for the owner)`, in 台灣正體中文, plain words;
- `## FACT CHECK` (R1–R5, each confirmed or false, with where).

Do not commit. Return the SUMMARY.

# Task 2026-10-14d: "New document" in Nextcloud's Files "+ New" menu (host 0.2.19, an uncounted candidate)

**The owner's request (2026-10-14).**
- 「我昨天人工測試的時候，發現沒辦法建立新文件，我希望可以在nextcloud中建立新文件」, and 「可以參考richdocuments跟collabora的做法」.
- After reading analysis 1, the owner chose **A**: 「範本寫明預設＋下批連結補 Language=」. In plain terms, the blank document the host ships **states its own defaults** (languages, paper, fonts), picked per user from their Nextcloud settings. The engine-side `Language=` waits for the link batch after v20 and is **not** part of this task.

**Read first.**
- `findings/evidence/new-document/analysis-1.md`: the diagnosis, the recommendation, and the acceptance sketch under "Recommendation: A first". Its D5 is the WASM harness.
- `findings/evidence/new-document/brief-1-default-language-and-fonts.md`, R1–R6.
- The host app, `~/Projects/Nextcloud_Apps/litecore` (0.2.18, `96a87d8`; `lib/AppInfo/Application.php`, `lib/Listener/`, `src/files.js`).
- richdocuments' two listeners in `~/OSSII/NC_modules/richdocuments/lib/Listener/`: `RegisterTemplateFileCreatorListener.php` and `FileCreatedFromTemplateListener.php`. They are a reference; do not copy its `emptyTemplates` bytes.
- Nextcloud core 34.0.2: `~/Projects/Nextcloud_Apps/litecore/nextcloud/lib/private/Files/Template/TemplateManager.php`.
- The repo's CLAUDE.md, for the form of acceptance criteria. The memory notes on the ddev scaffold are summarised under "Known traps" below.

You are designer and executor. B′ gives criteria and semantic design to fable. The owner has authorised fable to decide in their place this session; record every such decision in plain zh-TW in the spec's 裁決 section.

## Deliverables, in order

### 1. Spec: `specs/SPEC-M3-new-document.md` (zh-TW, the shape of the other `SPEC-M3-*.md`)

Write it before any code. It must state:

- **Scope.**
  - "New document" (`.odt`) only, because Calc is not ready.
  - Blank documents and the user's own `.odt` templates. `.ott` is **not** offered (analysis 1 Q4): list only `application/vnd.oasis.opendocument.text`, not `…-template`. Say what the template picker then shows.
- **Which defaults per user.** Decide how language and paper are chosen from the user's Nextcloud **language** and **locale**.
  - Analysis 1 suggests one template per supported language, picked by `IL10NFactory::getUserLanguage()`.
  - Consider whether paper should follow the locale's country (Letter for the US list in `paper.cxx:440-500`, A4 otherwise) rather than the language.
  - Consider whether one base template with values substituted server-side beats N static files.
  - Decide what an unsupported language falls back to.
- **The template bytes.**
  - The fonts must exist in the shipped image: `Liberation Serif` / `Liberation Sans` and `Noto Sans CJK TC`; the e10 pack carries five Sans family names, so check which names are real.
  - Standard style names must be kept.
  - The template must be generated **deterministically** by a script committed in study_LiteCore, not hand-edited bytes, and its sha256 must be recorded.
  - It must pass the ODF validator if one is available locally (`~/OSSII/odfvalidator-desktop` exists; check whether it runs headless).
- **Acceptance criteria.** Each must be form one or form two (CLAUDE.md §1), with a default for "if this is never done" and a red case for each.
  - At minimum:
    - from Files "+ New → New document", a file appears with the user's chosen name;
    - it opens in LiteCore through the default action;
    - typing and saving work;
    - reopening shows the text;
    - the saved `styles.xml` states the expected `fo:language`/`fo:country`, `style:language-asian`/`style:country-asian`, `style:font-name-asian` and page size for at least two user settings (zh_TW, and an English one), **from the WASM engine in both browsers** (analysis 1 D5);
    - a 0-byte or corrupt result can never be produced silently;
    - a user without write permission on the folder gets Nextcloud's normal refusal.
  - Also say what happens on 0.2.18 (the red case: there is no menu entry).
- **What it does not change.** The engine, the profile, the page bytes and the shell generation: none of them change. Only the host app changes, and its version becomes 0.2.19.

### 2. Template generator and templates

The generator goes in study_LiteCore. The output templates go into the host app.

Check them natively first: native 26.8 LOK loads the template and saves it, and the saved `styles.xml` keeps the stated defaults. Reuse `probe-1-native-defaults/tool/`. Test both with `LANG=en_US` and with `LANG=zh_TW`; the template must win in both.

### 3. Host code (`~/Projects/Nextcloud_Apps/litecore`)

- A `RegisterTemplateCreatorEvent` listener.
- A `FileCreatedFromTemplateEvent` listener that writes the right template when the template is `null`, and leaves user templates alone.
- Registration in `Application.php`.
- Version 0.2.19 in `appinfo/info.xml`.
- If the app's JS changes, rebuild it with `npm run build`; a JS change needs the version bump.
- Commit in the host repo with the normal `Co-Authored-By` trailer for your model; that repo is not under `~/OSSII`.

### 4. Measurement on the ddev instance (`https://litecore.ddev.site:8443`)

- **Install.** Follow how earlier host versions were installed; see `handoff/HANDOFF-2026-10-13d-*.md` and the precedent for 0.2.18.
- **Browsers.**
  - **Do not start any browser run until the main session tells you the pre-v67 witness (task 10-14c) is finished.** Until then, do steps 1–3 and the native checks.
  - Before any browser run:
    - run `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`; `b true` means stop and report;
    - count `chrome` processes;
    - make sure nothing of ours is running.
- **Runner.** Write it in the style of the existing `check_m3_*.py`. It drives Files' "+ New" menu, the editor, typing and saving, then reads the saved file over WebDAV and checks `styles.xml`. It must cover:
  - both browsers;
  - the two user settings;
  - the red case on a 0.2.18-shaped control, or the reason none is possible.

## Known traps (from memory; verify, do not trust)

- `nc-link` links only the repo's top-level entries present at the time it runs, so a new top-level directory needs `ddev nc-link` again.
- An app JS change needs a version bump, because of the `?v=` cache-busting.
- Login POSTs need an `Origin` header.
- AppConfig is cached in APCu for about 3 s.
- The owner uses this ddev instance daily; another ddev project's `ddev start` makes the shared router return 404 briefly.

## Limits

- Do not touch `wasm_sdk_probe/` product bytes (`web/`, `editor-shell*/`, `sdk/`, `src/`, `Makefile`, `dist/`), other than adding new tools or tests, or study_LiteCore's v20 work.
- No push, no deleting user files, no `sudo`. If something needs root, stop and report the command.
- Commit only your own paths in study_LiteCore (`git commit -- <paths>`). Another session commits there.
- Report a `## SUMMARY` of at most 30 lines. Include anything you decided on the owner's behalf, in one zh-TW line each, so the main session can relay it.

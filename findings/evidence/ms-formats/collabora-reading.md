# How Collabora Online and richdocuments handle Microsoft formats (code reading, 2026-11-03)

Sources, read-only:

- COOL co-26.04: `study_LiteCore/cool-26-04` (wsd/, kit/, browser/, discovery.xml; `engine/` only where named).
- richdocuments 31.1.1, an OSSII fork of upstream: `/home/jiajun/OSSII/ncdev_env/apps/richdocuments`. Fork-specific behaviour is flagged.

Gathered by a read-only subagent and spot-checked by the main session against the source (marked **checked**). Everything else is the subagent's reading with its citation, not re-read.

## 1. Which formats are editable

- wsd serves discovery.xml almost as is; every `edit` action's `ext` goes into `EditFileExtensions` (wsd/ClientRequestDispatcher.cpp:2684, 1513-1527). An extension outside that set is forced read-only, comments allowed (wsd/COOLWSD.hpp:166-178, wsd/DocumentBroker.cpp:1113, 1503-1510).
- `edit` + `view`: doc (discovery.xml:20-21), docx (24-26, plus `editnew`; **checked**), docm (27-28), dotx (29-31, `editnew` → newext docx), rtf (42-44), xls (88-89), xltx (93-94), xlsx (97-99, plus `editnew`; **checked**), xlsb (100-101), xlsm (102-103), csv (109-111), ppt (143-144), pptx (147-149). `view` only: dot (22), pot (145). No `convert` action.
- richdocuments looks discovery up by **mimetype** and takes the first action (lib/WOPI/Parser.php:69-74; Parser.php is fork-modified, +134/-8).

## 2. Format written back on save: the original format

- `DocumentBroker::sendUnoSave` sends `save background=… {DontTerminateEdit, DontSaveIfUnmodified}` with no FilterName (wsd/DocumentBroker.cpp:4319-4375). Kit rewrites it to `uno .uno:Save …` (kit/ChildSession.cpp:793-821; **checked**, line 797). LOK's `.uno:Save` only adds an interaction handler; its one special case is PDF (engine/desktop/source/lib/init.cxx:5734-5790). The upload is a WOPI PUT to the same file (wsd/wopi/WopiStorage.cpp:777-784). Only an explicit Save As (PUT_RELATIVE, WopiStorage.cpp:816-821) changes the format.
- Templates: loaded under the template's extension, then `saveAs(url, nullptr, "TakeOwnership,FromTemplate")` right after load (kit/Kit.cpp:2135-2148, kit/ChildSession.cpp:1114-1146).
- Client warning: only `readonlyStartingFormats` = txt, csv (canEdit) and xlsb (canEdit: false) (browser/src/control/Permission.js:16-20; **checked**): those start read-only with "This document may contain formatting or content that cannot be saved in the current file format" and an offer to save as ODF (Permission.js:158-219). **docx, xlsx, doc, xls are not on it.**
- Core's alien-format dialog exists (sfx2/source/doc/guisaveas.cxx:809-814, 851-863, 2104-2147; `WarnAlienFormat` defaults true, officecfg Common.xcs:1685-1692) and no COOL override was found; whether it fires under LOK on save or autosave was **not established** (needs a runtime test).
- No COOL setting forces ODF or OOXML on save. `view_mode/file_extensions` (coolwsd.xml.in:287-290) opens listed extensions in view mode by default; it ships empty.

## 3. Legacy binaries

- doc, xls, ppt are edited in place and saved in the same format via `.uno:Save`; no conversion on open. Core forces Save As only when the loaded filter has no EXPORT flag (guisaveas.cxx:800-805). Formats without an export filter are view-only in discovery; template extensions set `_disableExport` (wsd/wopi/WopiStorage.cpp:56-68, 340-341).
- richdocuments' ConversionProvider (identical to upstream) is a user-triggered Files conversion (docx→odt, xlsx→ods, odt→doc/docx…), not on open (lib/Conversion/ConversionProvider.php:24-118).

## 4. richdocuments: mimes and the format of new files

- `Capabilities::MIMETYPES` (ODF…), `MIMETYPES_MSOFFICE` (doc/docx/dotx/docm/xls/xlsx/xltx/xlsm/xlsb/ppt/pptx/…/text/csv), `MIMETYPES_OPTIONAL` (lib/Capabilities.php:17-68). The MS list opens by default unless officeonline or onlyoffice is enabled (Capabilities.php:111-118, lib/Service/CapabilitiesService.php:195-205).
- New files: admin setting `doc_format` (empty = ODF, `ooxml` = OOXML), the checkbox "Use Office Open XML (OOXML) instead of … ODF by default for new files" (src/components/AdminSettings.vue:148-152, 665-668); it switches the New-menu creators to .docx/.xlsx/.pptx (lib/Listener/RegisterTemplateFileCreatorListener.php:48-90) and the template extension (lib/TemplateManager.php:65-69, 416-424, 445-451). Unchanged from upstream stable31.

## 5. Restrictions specific to MS formats

- **Fork-specific `saveToOdf`**: default `'yes'` (lib/AppConfig.php:53); for doc/docx/docm, xls/xlsx/xlsm, ppt/pptx/pptm CheckFileInfo sends `UserExtraInfo.SaveToOdf = odt|ods|odp` (lib/Controller/WopiController.php:272-276, 1054-1094; **checked**). Admin label "Automatically convert Microsoft Office files to ODF files" (AdminSettings.vue:136-144). **Stock COOL never reads `SaveToOdf`** (no match in browser/src, wsd, kit; **checked**): it needs OSSII's own client.
- Passwords: generic, kit returns `passwordrequired:to-view|to-modify` and the client prompts (kit/Kit.cpp:2125-2127, 2192; browser/src/app/Socket.ts:2329-2339).
- Macros: `enable_macros_execution` false, `macro_security_level` 1 by default (coolwsd.xml.in:259-260).
- No persistent "not ODF" banner; `isFileODF` only hides Fontwork and changes one Calc tooltip (browser/src/app/LOUtil.ts:894-905).

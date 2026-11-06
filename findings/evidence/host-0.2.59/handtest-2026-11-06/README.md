# Owner's hand test of host 0.2.59 (2026-11-06 / 07)

The script is `HANDTEST-2026-11-06-host-0.2.59.md` (repo root, 10 items), run on `https://litecore.localhost:18443` with 0.2.59 installed (host `480ba6b`, engine `a2e67f21`). The fixtures are in admin's `手測-0.2.59/` (`../handtest-fixtures/put.json`).

The result, in the owner's words: "測完了，writer 沒問題". Calc has one finding.

## The finding: a column copied into desktop Calc splits cells at spaces

The owner's words: copying column A of 「編輯測試」 (A1 `原始中文 Alpha`) "以欄的形式" and pasting into desktop Calc turns a cell with a space into two cells (`原始中文` | `Alpha`). Copying one cell, or a row, does not. Screenshots: `owner-copy-range.png` (A1:A5 selected on the page) and `owner-paste-desktop-calc.png` (desktop Calc after the paste: A1 `原始中文`, B1 `Alpha`, A2 `鄰格`, B2 `必須保留`).

Measured afterwards, the copy is correct, and the split is desktop Calc's text import:

- `1-calc-after-handtest.ods` is the file as it was on the host after the test (sha256 `b5cfb18e…`; it differs from the upload because of the test's own edits and autosave). On the native core, A2 is now `'鄰格 必須保留'`, with a U+0020 space from an edit during the test. So both cells that split contain a space. Op 15 on A1:A5 gives `'原始中文 Alpha\n鄰格 必須保留\n合併格\n隱藏列\n隱藏列之後\n'`, plain TSV with no stray tab.〔observed〕
- `sc/source/ui/view/viewfun5.cxx:760`: pasting `STRING` with a newline anywhere but the last character opens the Text Import dialog (`SC_PASTETEXT`), and it uses the separator options last used (`SaveParameters`, config `Office.Calc/Dialogs/ClipboardTextImport`). One cell has no newline, and one row has its only newline at the end, so neither opens the dialog: hence no split.〔observed, source〕
- `sc/source/ui/view/viewfun3.cxx` `PasteFromSystem`: when the clipboard also has HTML, Calc pastes that before `STRING`, so the text import dialog never runs. Collabora puts `text/html` and `text/plain` on the clipboard (`cool-26-04/browser/src/map/Clipboard.js`); this page puts only `text/plain` (SPEC-P-calc-copy 2.2, a named limit).〔observed, source〕

So the named limit "no `text/html`" has a practical consequence: a multi-row copy into desktop LibreOffice goes through Text Import, where whichever separators the user last used apply. The fix is the owner's choice (the handoff for this session).

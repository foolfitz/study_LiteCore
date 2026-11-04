# Owner's hand test of host 0.2.56 (2026-11-04, 10:05-10:28 +0800)

Script: `HANDTEST-2026-11-04-host-0.2.56.md` (repo root). Owner's desktop Firefox, real profile, on `https://litecore.localhost:18443`
after the morning reboot (stack brought up with `docker compose --env-file litecore.env up -d`; app 0.2.56, host repo `main` = `6def1da`).

Fixtures were put by the session into admin's `手測-0.2.56/` over WebDAV, with a temporary user `handtest_ro` holding read-only shares of the
two `10-*` files (user deleted after the test, shares gone with it):

| Name | Source | For |
|---|---|---|
| `1-writer.odt` | `wasm_sdk_probe/test-docs/r7-compat/l1-layout-table-image.odt` | 1-3 |
| `4-calc.ods`, `8-excel.ods` | `findings/evidence/host-0.2.50/files-workflow-01/fixture/cell-editing.ods` | 4-5; 8-excel.ods makes Save As's default name taken |
| `7-word.docx`, `10-唯讀.docx` | `wasm_sdk_probe/test-docs/r7-compat/l1-plain.docx` | 7, 9, 10 |
| `7-word.odt` | `wasm_sdk_probe/test-docs/r7-compat/l1-plain.odt` | makes Save As's default name taken |
| `8-excel.xlsx`, `10-唯讀.xlsx` | `libreoffice-26-8/sc/qa/unit/data/xlsx/formats.xlsx` | 8, 9, 10 |
| `~/Downloads/6-上傳用.ods` (local) | the same `cell-editing.ods` | 6, uploaded by the owner |

## Result: 9 of 10 items pass; item 1 fails on zoom

| Item | Owner's verdict |
|---|---|
| 1 Writer zoom, Shift+Up/Down/Home/End, four alignments | **Zoom fails**; the rest passes |
| 2 Heading menu, list toggles | pass |
| 3 Enter over a two-paragraph selection; copy with only the image selected | pass |
| 4 Calc text colour, fill, alignment; sheet switch keeps scroll and active cell | pass |
| 5 Calc type, Enter, undo/redo by button and keys; bold then undo | pass |
| 6 Files New spreadsheet; upload an .ods and open it | pass |
| 7 Word: type, Save, close, reopen | pass |
| 8 Excel: type, autosave, reopen | pass |
| 9 Save As from .docx and .xlsx: ODF preselected, taken name refused in the dialog, new name opens the copy | pass |
| 10 Read-only shares of .docx / .xlsx: view only, no Save As | pass |

**Item 1, zoom (owner's words, translated):** Firefox. The document opens at 75 percent (fit); the first zoom-in step, to 100 percent, turns the
whole editor area white -- no grey desk, no paper edge, no text -- and every larger level too. The header still shows 就緒, the status bar
"第 1 頁，共 3 頁", a horizontal scrollbar spanning most of the width and a vertical scrollbar are visible. Owner's screenshot (not copied
into git): `~/Pictures/螢幕截圖/螢幕截圖_20261104_101842.png`. Zoom passed the owner's hand test on 0.2.47 (`168204628`); Z (mirror,
`t3-long.odt`, 22 pages) held on generation 89 (`ms-formats/gen-89/rerun-01/writer-zoom/`), so the mirror net did not see the owner's path.
Diagnosis: next section.

## Item 1 diagnosed: a resize loop under a zoom level, on documents whose reported width moves with the paint scale

Measured by a session subagent on 2026-11-04 10:35-10:50 with its own headless browsers (scripts, screenshots and paint logs in the session
scratchpad, not in git), on copies in a folder of its own (deleted after; no lock rows left):

| Run (`l1-layout-table-image.odt` unless stated) | Fit | 100 | 125 | 150 | 200 | Back out |
|---|---|---|---|---|---|---|
| Host, Firefox, 1000x1000 (the owner's case) | 79: painted | blank, still blank 5 s later | - | - | - | 75, 50, reset: painted |
| Host, Chrome, 1400x900 | 79: painted | blank | blank | blank | painted | reset: painted |
| Host, Chrome, 800x600 | 64: blank | blank | blank | blank | painted | - |
| Mirror of the current `dist/` (page byte-identical to the host's), Chrome 1400x900 | painted | blank | blank | blank | painted | - |
| Mirror of the 0.2.47 archive (generation 84 page, Writer v29), Chrome | painted | blank | blank | blank | painted | - |
| Positive control: `t3-long.odt` on the host, Chrome | 87: painted | painted | painted | painted | painted | reset: painted |

- **Not a regression**: 0.2.47, the version whose zoom passed the owner's hand test, blanks the same way on this document. The owner tested
  zoom on a different document then. Page and engine, not the host: the mirror reproduces it.
- **Mechanism** (observer on the Worker, Chrome): for this document the width the engine reports after a paint (`documentWidthTwips`)
  depends on the canvas width it painted at -- at 100 percent 16960, 17003, 17002, 16961, ... -- so `documentSizeChanged` is true on every
  reply (159 of 159 at 100, 116/116 at 125, 90/90 at 150). `renderDocument` breaks out on it and calls `layoutCanvas()`
  (`wasm_sdk_probe/web/e2-editor-app.js:1761`, `:1783`), which clears `lastTiles`; under a zoom level `cssWidth` is computed from
  `session.document.widthTwips` (`:1437-1439`), so the canvas moves by 1-3 px and the next paint reports another width. No band is ever
  kept; the canvas repaints about 50 times a second while the level stays. Read in the source by the main session: the comment at `:1784`
  ("It terminates because the engine reports a CHANGE, so the next reply for an unchanged document says false") is the assumption this
  document breaks. At fit `cssWidth = min(available, 900)` does not follow the reported width and the loop settled after 3 changes in the
  1400 px window; 200 percent happened to settle after 2.
- Engine side, read: `src/probe_engine.cpp:3970-3976` reads `getDocumentSize` right after `paintTile` and compares with the last report.
  Why Writer's width for this document moves with the paint scale is **not established**.
- Not explained: fit blank in the 800x600 window.
- **Why Z did not see it**: `check_writer_zoom.py:44` opens `t3-long.odt` only, whose reported width does not move. Its `settled()` needs
  the visible rows covered by painted bands, so it should turn red on this document (inferred from the code, not run).

## Read back after the test (session, 10:29)

Over the filecache and the data directory, not the owner's eyes:

- `7-word.docx` still OOXML (`word/document.xml`), mtime 10:26:10, its text gained the owner's typed `今天喜歡聽美秀集團` (typed with the
  Chinese IME); `7-word.odt` (the taken name) unchanged since the fixture put; the Save As copy is `7-word-2.odt` (ODF).
- `8-excel.xlsx` still OOXML (`xl/workbook.xml`), mtime 10:27:37; `8-excel.ods` unchanged; the Save As copy is `8-excel-2.ods` (ODF).
- `10-唯讀.docx` / `.xlsx` unchanged since the put (10:05:15-16).
- `add_new.ods` (item 6's new spreadsheet) and `6-上傳用.ods` (the upload) present.
- No row in `oc_files_lock` created in the three hours before the read: nothing left locked by the test.

The folder `手測-0.2.56/` stays in admin's Files until item 1 is re-tested.

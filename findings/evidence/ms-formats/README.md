# Microsoft formats: measurements before the link (2026-11-03)

For `specs/SPEC-P-ms-formats.md` sections 3 and 6. Nothing here was linked: M0 runs the native 26.8 core, M1 runs the shipped
pages and frozen profiles.

| Directory | What |
|---|---|
| `native-m0/` | M0: `tools/run_msformat_native.py` driving `tools/msformat_native.cpp` (build `build/msformat-native-2`, sha256 `6a55e9ab…c2c9`, built by `tools/build_msformat_native.py`, 3.4 s, receipt in that build dir) on `build-native-26-8`, core `671c848b`. |
| `wasm-m1/` | M1: `tools/run_msformat_wasm.py` on `dist/` (Writer `e2-editor-v32`, Calc `ods-editor-v4`), Chrome 156.0.8078.47, comparing against `native-m0/`. |
| `f184-ods-reload/` | Finding 184: the ODS that never finishes loading, its backtrace, three timings. |
| `collabora-reading.md` | How COOL co-26.04 and richdocuments 31.1.1 handle MS formats (code reading). |
| `native-m0.stdout.txt`, `wasm-m1.stdout.txt` | The one-line-per-file summaries the two runs printed. |

Evidence is lean on purpose: the LibreOffice user profiles and input copies are deleted after each run, every saved document is kept
as sha256 and size in `report.json` (`outputs`), and the content dumps are gzipped. The inputs are named by path and sha256 in the
reports; they are files of the pinned `libreoffice-26-8` QA tree and `wasm_sdk_probe/test-docs/r7-compat`.

## Corpus (33 files, the list is in `run_msformat_native.py`)

- 7 DOCX and 10 XLSX from the LibreOffice QA tree whose `docProps/app.xml` names a Microsoft application, under 400 KB, most
  features first;
- 3 DOC and 3 XLS from the QA tree (the first three of 20-200 KB by name);
- the 10 DOCX of R7 (`test-docs/r7-compat`), one of them truncated (the negative control).

## What a "dump" is

`msformat_native.cpp` walks the loaded model: text documents give each body paragraph's string and each table's cells by name, in
order; spreadsheets give, per sheet, every non-empty cell of the used area as `A1<TAB>getFormula()`. Two dumps are compared line for
line (`compare()` in the driver; `onlyInFirst` / `onlyInSecond` count distinct lines). Equal dumps mean equal text and cell formulas,
not equal formatting or layout; layout is approximated by the part count (pages for Writer) and the document height in twips,
which the harness also reports.

## M0 results (native 26.8, LOK)

- Load: 32 of 33. The truncated DOCX fails, as it should. 28-241 ms.
- Filters chosen: DOCX 15 `Office Open XML Text`, 1 `MS Word 2007 XML`; XLSX 8 `Calc Office Open XML`, 1 `Calc MS Excel 2007 XML`
  (the tenth never printed its report, see below); DOC `MS Word 97`; XLS `MS Excel 97`.
- Same bytes under an ODF name: the same filter for DOCX, XLSX and DOC; XLS gets the template variant `MS Excel 97 Vorlage/Template`
  (same content).
- Own format, saved twice (LOK `saveAs`, and `storeToURL` with the load filter as `.uno:Save` would): the two arms agree on every
  file. Content equal after reload for all but two: `n830205.docx` gains 2 empty paragraphs; `XlStartupExternal.xls` turns 54
  external add-in formulas into `=NA()`. Writer page counts unchanged on all 16 comparable DOCX.
- ODF: content equal for all but formula reference case (`a3:m25` -> `A3:M25`) in one file and the 16th digit of 100 date-time
  values in another. Layout: `n830205.docx` goes from 7 to 11 pages; four XLSX change total row height.
- `forum-mso-en4-134670.xlsx`: import, XLSX save and ODS save finish in seconds; reloading the ODS does not finish (both arms hit the
  driver's 180 s timeout, so the harness never printed its JSON; the dumps written before that point are compared). Finding 184.

## M1 results (shipped WASM engines, no link, Chrome)

- Every file is handed to the page under its ODF name (finding 013's boundary), through the page's own host contract
  (`globalThis.liteCoreHost`, installed by `Page.addScriptToEvaluateOnNewDocument`), saved with the page's toolbar button.
- Opened: 32 of the 32 loadable files, 1.4-5.3 s from navigation to ready (Writer: the state pill; Calc: a selected cell). The
  truncated DOCX ends `stopped` with `LOK_ERROR：loadComponentFromURL returned an empty reference`.
- The saved ODF, dumped by the native harness, equals M0's native ODF round trip for all 31 comparable files.
  `forum-mso-en4-134670.xlsx` opens and saves in the WASM page but is not comparable: reading its ODS hits finding 184.
- Firefox not run: its WebDriver classic has no init script to install the host before the page's modules run.
- A first run of the tool (scratch, not kept) died retrieving a 12.5 MB save over CDP (the websocket client's 1 MiB frame cap); the
  tool now retrieves in 500 kB slices, and this run compares that file too.

## Not measured here

- DOCX / XLSX saved by the WASM engine: the shipped save boundary accepts `odt` / `ods` only. After the link (spec 6.2 W1).
- Firefox.
- Opening the finding-184 ODS in WASM.

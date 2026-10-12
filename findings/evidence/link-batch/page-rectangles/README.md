# Link batch item 2 — `getPartPageRectangles` on native LibreOffice 26.8

Brief: `handoff/tasks/TASK-2026-10-12c-native-page-rectangles-and-129-shapes.md`, Part N1. Plan: `handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md` item 2 ("the page number, Collabora's way"). Native only (`native-lok-26-8/build/instdir`, `SAL_USE_VCLPLUGIN=svp`); no browser, no WASM, no product bytes.

## Prediction (main session, before any run; copied verbatim from the brief)

- P-N1a: the string is `x, y, w, h; x, y, w, h; ...` in twips (from `SwWrtShell::getPageRectangles`).
- P-N1b: the 60-page document gives 60 rectangles natively (it may differ on WASM because of fonts; not asserted here).
- P-N1c: first call < 50 ms, later calls < 5 ms on 60 pages.
- P-N1d: Edit A adds exactly one rectangle and is followed by `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`; Edit B leaves the rectangles unchanged.

(Written into this file before the first native run of this part; the results below were added afterwards and the block above was not edited.)

## What was run

| item | value |
|---|---|
| tool | `wasm_sdk_probe/tools/native_page_rectangles.cpp` (sha256 in `round-20261012T030439Z/inputs.sha256`) |
| runner | `wasm_sdk_probe/tools/run_native_page_rectangles.sh` (`SCRATCH_DIR=<outside the repo>`), analysis `wasm_sdk_probe/tools/analyze_native_page_rectangles.py` |
| build | `g++ -std=c++17 -O2 -I<libreoffice-26-8>/include tools/native_page_rectangles.cpp -ldl -lpthread -o native-page-rectangles` (also in `round-*/build-command.txt`) |
| run | `SAL_USE_VCLPLUGIN=svp native-page-rectangles <native-lok-26-8/build/instdir/program> file://<fresh profile> file://<copy of the document> <label> <round> [--redact]`; one process = one fresh load; 3 rounds per document, each its own process and profile |
| native build | `native-lok-26-8/build/instdir` (read-only), LibreOffice 26.8 |
| owner's document | `wasm_sdk_probe/build/scratch-m3-production-ui/PMPC指南.odt`, sha256 `7b336879547df057ae6d38e907f221b40c90c37cd65d2df5afceceb91941657e`; copied to a scratch directory outside the tree for each round (byte-compared with `cmp`), never into the repository; run with `--redact` (see "Instrument notes") |
| 60-page document | `python3 tools/create_long_document.py --pages 60 --out <scratch>/long60.odt`, 5149 bytes, sha256 `d741a83aedc324fe507b491be6d9e81778e919b819626769c5ffa421746b09b0` (not committed) |
| sequence per load | `documentLoad`, `initializeForRendering`, one `paintTile`, `registerCallback`; read `getParts` / `getDocumentSize` right after the load; wait until no callback for 1.5 s; read them again; 10 consecutive timed `getPartPageRectangles()` calls (`steady_clock` around the call only); 1 more call after 2 s idle; Edit A = `.uno:GoToEndOfDoc`, 0.8 s, `.uno:InsertPagebreak`, wait quiet, two reads; Edit B = `.uno:GoToStartOfDoc`, 0.8 s, type `Q`, wait quiet, two reads |
| raw output | `round-20261012T030439Z/{owner,long60}-r{1,2,3}.jsonl` (every rectangle string verbatim, every call's ms, every callback with type, payload and ms since process start), `*.stderr` (LibreOffice warnings), `*.exit` (all 0), `ended-utc.txt` |
| parsed output | `round-20261012T030439Z/analysis.json` and `analysis.txt` (arithmetic on the raw strings only) |
| last native run of this part | additional polling arm, ended 2026-10-12T03:53:03Z (`poll-round-20261012T035214Z/ended-utc.txt`); the main rounds ended 2026-10-12T03:05:49Z |

## Results

### The string (P-N1a)

`getPartPageRectangles()` returns one string, rectangles separated by `"; "`, the four numbers of a rectangle by `", "`, no trailing separator. First two and the last rectangle of the 60-page document, verbatim from `long60-r1.jsonl`:

```
284, 284, 11906, 16838; 284, 17406, 11906, 16838; ... ; 284, 1010482, 11906, 16838
```

and of the owner's document (18 pages): `284, 284, 11906, 16838; 284, 17406, 11906, 16838; ... ; 284, 291358, 11906, 16838`. All six raw strings match `-?\d+(, -?\d+){3}(; -?\d+(, -?\d+){3})*` (`raw_separator_ok: true` in `analysis.json`).

Order is x, y, width, height (the source, `SwCursorShell::getPageRectangles`, appends `Left, Top, Width, Height` of each page frame; the LOK header says "using the same format as LOK_CALLBACK_TEXT_SELECTION", whose payload in this tool's logs is also `x, y, w, h`).

Units are twips. What makes me conclude it: (1) every rectangle is 11906 x 16838, which is A4 portrait in twips (210 mm = 11905.5, 297 mm = 16838.6 at 1440 twips per inch); the generated document declares `fo:page-width="21cm" fo:page-height="29.7cm"` (`tools/create_long_document.py:65`); (2) `getDocumentSize()` is documented as TWIPs (`LibreOfficeKit.hxx:211`) and returns `[12474, 1027604]` for the 60-page document, which is exactly page width + 2 x 284 wide and last rectangle's bottom (1010482 + 16838) + 284 high; 284 is `DOCUMENTBORDER` (`sw/inc/swtypes.hxx:80`, "~5mm") and is also the first rectangle's x and y. The same arithmetic holds for the owner's document (`docH - last bottom: 284` in all rounds).

Contiguity: every rectangle has x = 284, w = 11906, h = 16838 (in both documents, all rounds); y is strictly increasing and the vertical gap between consecutive rectangles is the single value 284 (`vertical_gaps: [284]`). So the rectangles are contiguous in the sense of a constant 284-twip gap, not touching. Neither document has a page of another size or orientation, so the strings here cannot tell "equal page heights" from "per-page rectangles" (the plan wants the latter and this does not test it).

### Page-count sources (brief: compare the count)

| source | long60 | owner |
|---|---|---|
| rectangles in the string, after settling | 60 (3 of 3 rounds) | 18 (3 of 3) |
| `getParts()` (Writer: `SwXTextDocument::getParts` returns `GetPageCnt()`, `unotxdoc.cxx:3421`) | 60, already 60 right after the load, before any callback went quiet | 18, likewise |
| `.uno:StatePageNumber=Page N of M` (a `LOK_CALLBACK_STATE_CHANGED` the core pushes, first seen 1.29-1.43 s after the load) | `Page 1 of 60` | `Page 1 of 18` |
| `getDocumentSize()` | `[12474, 1027604]` | `[12474, 308480]` |

All three page counts agree in every round (`count_equals_getParts_equals_statusM: true`). No document-statistics command was read (the LOK C API used here has none for the page count that is not one of the three above; I did not invent one).

Two observations the plan may care about (not asked for): `getParts()` is a cheaper source of M than the rectangles; and the core already pushes `Page N of M` as a state change, where N is the page of the CURSOR (it changed to `Page 60 of 60` on `GoToEndOfDoc`, to `Page 61 of 61` after the break, back to `Page 1 of 61` on `GoToStartOfDoc`), not of the view. Whether the engine/page see that state payload is not measured here; from reading `src/probe_engine.cpp` (`updateEditorFormatState`, ~1671-1710) only the format commands it watches are parsed (inferred).

### Cost (P-N1c)

Ten consecutive calls on the settled document, `steady_clock` around `getPartPageRectangles()` only, milliseconds (table from `analysis.json`):

| document | round | first call | other nine: min / median / max | one more call after 2 s idle |
|---|---|---|---|---|
| long60 | 1 | 0.0186 | 0.0077 / 0.0099 / 0.0225 | 0.0467 |
| long60 | 2 | 0.0208 | 0.0085 / 0.0086 / 0.0123 | 0.0426 |
| long60 | 3 | 0.0162 | 0.0071 / 0.0072 / 0.0208 | 0.0404 |
| owner | 1 | 0.0163 | 0.0028 / 0.0029 / 0.0056 | 0.0585 |
| owner | 2 | 0.0275 | 0.0043 / 0.0043 / 0.0125 | 0.0393 |
| owner | 3 | 0.0151 | 0.0042 / 0.0044 / 0.0078 | 0.0388 |

Tens of microseconds on native. The layout was already complete at load (`getParts` was final right after `documentLoad`), so these are the cost of walking finished page frames, not of laying out. They say nothing about WASM speed.

### Edit A (adds a page) and Edit B (does not) (P-N1d)

| document | round | A: rectangles before -> after (two reads) | A: `getParts`, `getDocumentSize` after | A: `DOCUMENT_SIZE_CHANGED` (ms after the `InsertPagebreak` dispatch, payload) | A: `StatePageNumber` after (ms) | B: rectangles before -> after (two reads) | B: rectangle strings identical | B: `DOCUMENT_SIZE_CHANGED` / `INVALIDATE_TILES` |
|---|---|---|---|---|---|---|---|---|
| long60 | 1 | 60 -> 61, 61 | 61, [12474, 1044726] | 1.32 (`12474, 1044726`) | 322.9 (`Page 61 of 61`) | 61 -> 61, 61 | yes | 0 / 0 |
| long60 | 2 | 60 -> 61, 61 | 61, [12474, 1044726] | 1.35 (same) | 321.59 (same) | 61 -> 61, 61 | yes | 0 / 0 |
| long60 | 3 | 60 -> 61, 61 | 61, [12474, 1044726] | 1.35 (same) | 322.12 (same) | 61 -> 61, 61 | yes | 0 / 0 |
| owner | 1 | 18 -> 19, 19 | 19, [12474, 325602] | 1.84 (`12474, 325602`) | 323.09 (`Page 19 of 19`) | 19 -> 19, 19 | yes | 0 / 0 |
| owner | 2 | 18 -> 19, 19 | 19, [12474, 325602] | 1.74 (same) | 323.42 (same) | 19 -> 19, 19 | yes | 0 / 0 |
| owner | 3 | 18 -> 19, 19 | 19, [12474, 325602] | 1.66 (same) | 322.11 (same) | 19 -> 19, 19 | yes | 0 / 0 |

- Edit A: the first N rectangles are byte-identical before and after (`first_n_rects_unchanged: true`, 6 of 6); one rectangle is appended: `284, 1027604, 11906, 16838` (long60) / `284, 308480, 11906, 16838` (owner), 284 below the previous one. `getDocumentSize` height grows by exactly 17122 (= 16838 + 284).
- Every callback type between the edit and quiet, per `analysis.txt` (union over the six runs): from `GoToEndOfDoc` to the dispatch: `INVALIDATE_VISIBLE_CURSOR`, `SET_PART`, `STATE_CHANGED`, `VERTICAL_RULER_UPDATE` (owner's document also `CONTEXT_CHANGED`, `MOUSE_POINTER`, `RULER_UPDATE`); from the `InsertPagebreak` dispatch to quiet: `DOCUMENT_SIZE_CHANGED`, `INVALIDATE_TILES` (payload `0, 0, 3839, 3839, 0, 0`, the same instant as `DOCUMENT_SIZE_CHANGED`), `INVALIDATE_VISIBLE_CURSOR`, `SET_PART`, `STATE_CHANGED`, `VERTICAL_RULER_UPDATE`.
- Edit B: the typed `Q` did arrive (visible-cursor x moved `1418 -> 1649` in long60; the word-count state went from 117,257 to 117,258 characters, A's page break adding none; the owner's document's cursor moved too). No `DOCUMENT_SIZE_CHANGED` and, as observed here, no `INVALIDATE_TILES` for typing either (0 in all six runs, with no client visible area set; observed, not explained).

### Additional arm (not in the brief): is the new page visible by the time `DOCUMENT_SIZE_CHANGED` fires?

`poll-round-20261012T035214Z/` (tool `native_page_rectangles_poll.cpp`, runner `run_native_page_rectangles_poll.sh`, 3 rounds x 2 documents): after `.uno:InsertPagebreak` the main thread called `getPartPageRectangles()` and `getParts()` in a loop with a 1 ms sleep for 1.5 s (1380-1400 samples), recording only changes. In all six runs the sequence was exactly one change, old count -> old + 1 (60 -> 61 and 18 -> 19, `getParts` in step with the rectangles), first seen by the sample that started 1.21-1.25 ms after the dispatch; the `DOCUMENT_SIZE_CHANGED` callback was logged 1.20-1.54 ms after the dispatch. A LOK call takes the same mutex the callback is delivered under, so a sample cannot return in the middle of the edit. No sample returned the old count after the new one, and none returned the new count before the callback was delivered (inferred from the mutex; the log orders sample START times, not return times, so the two can differ by the length of a blocked call). Reading: a re-read made from the `DOCUMENT_SIZE_CHANGED` handler or after it sees the new page; in these six runs there was no window with the callback fired and the old rectangles still returned. (The 60-page document was regenerated for this round; its sha256 is `e9c24cef373cd17c3769f508e00ddfc5054717c0eb567900edfa16ff53eea7f4` against `d741a83a...` in the main rounds: the same command gives different bytes, zip metadata is the likely cause - inferred, not checked. Both documents have 60 pages.)

### Predictions

| prediction | verdict | what the raw output shows |
|---|---|---|
| P-N1a: `x, y, w, h; ...` in twips | **held** | string format as quoted above, 6 of 6 runs; twips by the A4 and `DOCUMENTBORDER` arithmetic |
| P-N1b: 60 pages -> 60 rectangles | **held** | 60 in 3 of 3 rounds (and `getParts` and `Page 1 of 60` agree) |
| P-N1c: first < 50 ms, later < 5 ms | **held, by a wide margin** | first call 0.015-0.028 ms (limit 50 ms), later calls at most 0.0225 ms on the 60-page document (limit 5 ms) |
| P-N1d: A adds exactly one rectangle and is followed by `DOCUMENT_SIZE_CHANGED`; B leaves rectangles unchanged | **held** | 6 of 6; A +1 and `DOCUMENT_SIZE_CHANGED` 1.3-1.8 ms after the dispatch; B identical strings, no `DOCUMENT_SIZE_CHANGED` |

## Instrument notes and what is not covered

- Settling: "quiet" = no callback for 1.5 s (the waits were 2.6-2.9 s after the load, 2.0 s after Edit A and 1.9 s after Edit B). Nothing else defines "layout settled"; `getParts` was already final right after `documentLoad`, so these documents did not lay out lazily in the observed runs.
- The "first call" is the first `getPartPageRectangles` call of the process, but it was made after `getParts`/`getDocumentSize` had already been called, and after the layout was complete at load. A WASM engine that lays out lazily could differ.
- Neither document has a page of another size, orientation, a section with other margins, or a multi-column layout; the owner's document has 18 identical A4 pages. The design sketch's "never infer from equal page heights" is therefore not exercised.
- Redaction (owner's document): the probe was run with `--redact`, which replaces the payload of every callback type that can carry document text by its length, keeping geometry types and `.uno:PageStatus` / `.uno:StatePageNumber`. One imperfection: `STATE_CHANGED` payloads that are JSON (no `=`) were kept verbatim by that code path. I inspected all 10 distinct ones in the owner's files: zoom, view layout, ruler/margin numbers and accessibility-check state; no document text. A grep for non-ASCII bytes in the owner's raw and stderr files finds none.
- This tool had no earlier runs (a compile check only); `round-20261012T030439Z` is its first run. The polling arm likewise ran once (3 rounds x 2 documents).
- The runner scripts and the 60-page generator need `SCRATCH_DIR` outside the repository; the owner's document and the generated 60-page document are not in the tree.
- No product bytes, no browser, no WASM; nothing was committed.

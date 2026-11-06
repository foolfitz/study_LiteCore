# ods-editor-v8: Calc copy with text/html, and Calc zoom

One link carries both items: `specs/SPEC-P-calc-copy.md` section 9 (op 15 also returns the core's `text/html`, define `OXSDK_ODS_COPY_HTML`, capability bit 27 `cell-copy-html`) and `specs/SPEC-P-calc-zoom.md` (op 16 sets the view's zoom, define `OXSDK_ODS_ZOOM`, capability bit 28 `cell-zoom`). The criteria were committed before any counted run (`e03122f98`), and the corrections found by uncounted tool shakedowns were committed before the counted runs too (`04390df77`: copy append 3, zoom append 1).

## Before the link (2026-11-07)

| Folder | What | Result |
|---|---|---|
| `native-build-01/` | `tools/build_calc_undo_native.py`: the bridge to be linked plus `tools/calc_undo_native.cpp` (now with `paste` and `paint` actions), against build-native-26-8. Variant `v8` = v7's defines + `OXSDK_ODS_COPY_HTML` + `OXSDK_ODS_ZOOM`; variant `v7` = v7's defines (the control). | exit 0 |
| `n-copy-01/` | `tools/check_calc_copy_native.py --html`: N-C1..C6 again on the changed source, plus N-H1..H6, N-H7's costs, the `<pre>` fallback red case and the v7 control. | **N_HOLDS** |
| `n-zoom-01/` | `tools/check_calc_zoom_native.py`: N-Z1..Z6, N-Z7's costs, the "client zoom stuck at 3840" red case and the v7 control. | **N_HOLDS** |
| `syntax-tool-reproduces-v7/` | `tools/check_v7_syntax.py` with no new arguments after it was parametrised: it must reproduce `calc-copy/pre-link-syntax-02` (cadence item 2). | green, controls red |
| `pre-link-syntax-01/` | `check_v7_syntax.py --target ods-editor-v8-dev --define OXSDK_ODS_COPY_HTML --define OXSDK_ODS_ZOOM`: em++ `-fsyntax-only` with `make -n`'s own command lines; a positive control per define and file. | green, 4 controls red |

### Reading the results

- **Copy.** B1:C2's `htmlText` is one `<table>` with `[[42, 84], [格式測試, 待清除]]`. A1:C2's HTML pasted at L20 through LOK `paste("text/html")` (the same `.uno:Paste` desktop Calc runs) gives L20 = `原始中文 Alpha` in one cell, and L20:N21 equals A1:C2 cell by cell. Cost: B1:C2 1.9 ms, column A 181 ms (124 KB of HTML), the sheet 230 ms (2.5 MB). The core's HTML export skips hidden rows and columns (`htmlexp.cxx`), so column A's HTML has 999 rows where the plain text has 1000. The spec records this as a named limit (copy append 3).
- **Zoom.** At every level (50, 75, 100, 125, 150, 200, read from the bridge's `kTileTwips`), for F100 and AA1000 on sheet 1 and C30 on sheet 2, the red fill on a tile painted at that ratio sits where op 0 says the cell is. Its top and left edges are 1 px further out (the fill covers the grid line), and every edge is within 0.5 px. Op 13's header edges and op 5's hit test agree. The red case (op 0's rectangle read at 3840 and scaled, which is what v7 would give the page) misses at 50, 75, 125 and 150. The fixed engine is needed because the core floors each row to whole pixels at the zoom it paints at.
- The wasm core's `libscfiltlo` contains `sc/source/filter/html/htmlexp.o` (`../wasm-lite/build-ods-viewer-v2/workdir/LinkTarget/Library/libscfiltlo.a.objectlist`), so the HTML export should reach the link. Only P on the linked profile can show it; if it does not, LOK quietly returns its `<pre>` fallback, which is exactly the copy red case.

### Files

- `n-zoom-01/tile-*.bgra.gz`: the canvases the judge read (512 x 512, the core's BGRA), gzipped after the run. Their sha256 before gzip is in `tiles.sha256`. Re-judge with `gunzip -k`.
- `n-copy-01/observations-n.jsonl.gz`: the main session's requests and replies (2.9 MB before gzip; most of it is the sheet's HTML).
- `session-*/profile/` (LibreOffice user profiles) are not committed.

## Executed fixes (not review)

- The zoom tool sent op 16 to sheet 1 whatever sheet was active, which moved the active sheet under N-Z5's cursor read. It now sends op 16 to the current sheet (a tool bug; the criterion did not change).
- Two criteria were wrong, not the engine: N-Z1's "1 px" did not allow for the grid-line overpaint plus the half-twip rounding at 200%, and N-Z4's document size grows with where the cursor has been. Also N-H4/P-H2 assumed the HTML has the hidden row. All three were corrected in the specs before the counted runs (see the spec appends).

## The link (2026-11-07 03:41)

The owner asked the agent to run it ("幫我跑連結"). `link/link.sh` exited 0 after 2 m 40 s:

- wasm `61e2a069`, worker `91d514f1` (the derived one);
- capability bits = v7's | 1<<27 | 1<<28;
- archived read-only as `build/archive/ods-editor-v8-dev-61e2a069`.

## After the link (2026-11-07, the owner away, autonomous round authorised)

Chrome 156.0.8078.47 and Firefox 157.0.1 on a mirror of the live page with `build/ods/editor-v8/profile`.

| Folder | What | Result |
|---|---|---|
| `p-copy-01` | `check_calc_copy.py --html`. | P_RED: P-H4 (the spec compared P-H1's B1:C2 with A1:C2; copy append 4) and Firefox P-H3 (a tool bug) |
| `p-copy-02` | After append 4. | P_RED: Firefox P-H3 only (WebDriver's script sandbox; copy append 5) |
| `p-copy-03` | After append 5. | **P_HOLDS** 10/10 in each browser |
| `p-copy-red-plain-only` | Page mutation: no ClipboardItem write. | MUTATION_RED in P-H1 |
| `review-codex-01/` | Codex review of the engine and page commits. 7 findings: 6 adopted, 1 named limit; P-Z9 added (zoom append 3). | see its README |
| `p-zoom-01` | `check_calc_zoom.py`, first run, page from before the review. | Chrome: P-Z1..Z4 and Z7 hold at all six levels. P-Z5 red only in the column at the document's left edge (zoom append 4). Then hung in P-Z6 on review finding 3; interrupted. |
| `p-zoom-02` | Page with the review fixes; tool with bounded waits. | **P_HOLDS** 41/41 in each browser |
| `p-zoom-red-{point-15,no-op16,no-centre,drag-no-zoom}` | Page mutations, Chrome. | all MUTATION_RED where the spec says (P-Z3; P-Z3/P-Z4; P-Z5; P-Z9) |
| `p-copy-04`, `p-copy-red-plain-only-2` | Copy again on the final page (the review touched the copy path). | **P_HOLDS** 10/10 in each browser; plain-only red in P-H1 |
| `regression/` | The Calc nets of the 0.2.59 release regression on v8 (`regression/chain-v8.sh`). | all pass, see below |
| `units/` | Node suite on a quiet machine, plus the three Calc mutation tools. | 1070/1070; mutation tools pass |

### Regression results

Every step holds in both browsers:

- sheet view 11/14;
- CU;
- cell 31;
- range 40;
- autosave;
- style 33;
- headers 145/121 (the same as v7's);
- structure 18/18;
- sheets 9/9.

Headers, structure and sheets first failed in the same second: their mirrors are named after `--out` and collided with `calc-copy/v7-regression`'s names. They were rerun as `*-v8`. The failed outputs are in `regression/failed-name-collision/`.

### What P could not see

- Whether a real Ctrl+C's user activation survives the engine round trip (P relaxes it to read the clipboard).
- A paste into **desktop** Calc. P-H4 pastes the browser's HTML into the native core with the same `.uno:Paste` instead.

Both are in the 0.2.60 hand-test draft (`HANDTEST-2026-11-07-host-0.2.60.md`).

## Section 34.4

Checks changed because of review: 1 (P-Z9, from Codex's finding 3).

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

## The link (owner)

```
bash ~/LibreOffice/study_LiteCore/findings/evidence/calc-v8/link/link.sh
```

Expected: about 3 minutes, like v7's (2 m 52 s). It writes `link/link-01.*` and `link/profile-SHA256SUMS`.

## Section 34.4

Checks changed because of review: 0.

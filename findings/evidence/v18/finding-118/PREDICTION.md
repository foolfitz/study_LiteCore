# Finding 118 (a document that loses a page): red cases, page fix, verification; predictions before any run

Source: finding 117's diagnosis D3 (`../diag-117/RESULT.md`). On M2-4, press 55 takes the document from two pages to one. The page asks for the stale two-page height, and the strip comes back 0.47 painted. The page throws TILE_NOT_PAINTED before it reads `documentSizeChanged`, so the canvas also stays at two pages' rows for every later paint (100 of 100). Fable's ruling section 3: fix on the page, red case on v8 without a link, verify on v18 with the M2-4 mode before v56. Labels P1-P5 are this file's.

## Instruments

- **`wasm_sdk_probe/tools/run_shrink_repaint.py`**, committed with this file. Fixture: `undo-limit-105.odt` cut to its first 52 paragraphs, built in memory, sha256 `1fe79470094ecf3d…`; every other zip part is byte-identical.
  - Why 52 paragraphs and not "Enter, then delete one line back" as the ruling said: on v18, M2-4 measured 53 such paragraphs at two pages and 52 at one. v8 refuses a boundary delete, so the shrink is the toolbar's Undo after the toolbar's paragraph break.
  - Verdict line `VERDICT RED (118 present)` exits 1, `GREEN` exits 0, and `NOT MEASURED` exits 3. NOT MEASURED means the run did not see both the growth to 34,528 twips and the shrink to 17,406.
- **The merge runner's M2-4 mode** (`run_merge_wasm_shakedown.py`, unchanged since `0e00aa4c…`), on the plain `e2-editor-v18` profile.

## The fix (written after P1 and P2 have run)

In `renderDocument` (`web/e2-editor-app.js`), the existing line `if (tile.documentSizeChanged) documentResized = true;` moves above the painted test, unchanged. It is followed by `if (documentResized) break;`. A strip asked against a size the document no longer has is not judged. The page re-lays out the canvas and asks again; the next reply says `documentSizeChanged` false, so finding 062's genuinely unpainted strip is still caught, one request later. The product-path mutation `ignore-a-document-that-grew` finds that line verbatim, so the line itself is kept byte for byte.

## Expected

- **P1, red on the shipped page.** `--profile e2-editor-v8 --page dist`, Chrome and Firefox.
  - The document grows to 34,528 twips and shrinks back to 17,406.
  - The first paint after the Undo asks for `h` 34,528 and comes back `docH` 17,406, `documentSizeChanged` true, painted below 0.5.
  - A TILE_NOT_PAINTED toast appears, and the last paint's rows are the two-page rows.
  - **VERDICT RED, exit 1.**
  - If P1 is GREEN, "v8 ships 118" stays a reading of the code (`dist/e2-editor-app.js:824` against `:834`), not a measurement, and that is what gets written.
- **P2, red on the cutover page before the fix.** `--profile e2-editor-v18 --page cutover`, Chrome and Firefox: as P1, **VERDICT RED.**
- **P3, green on the cutover page after the fix.** Same command as P2.
  - No toast.
  - After the Undo, one paint has `documentSizeChanged` true and is not judged. Then a paint asks for `h` 17,406 into the one-page rows, about half of the two-page rows, painted at least 0.9.
  - The growth step still re-lays out: two-page rows are found.
  - **VERDICT GREEN, exit 0**, Chrome and Firefox.
- **P4, M2-4 with the fixed page.** Plain `e2-editor-v18`, Chrome and Firefox, instrumented.
  - Every §30.2 clause is true, `noToast` included, so `pass: true`.
  - Latency is unchanged: 102 presses at 2000 ms engine-side, because the engine is not changed by a page fix.
  - After press 55, every paint's rows are the one-page rows (about 1,012); none is 2,007.
  - **Not counted.** The per-press latency clause (spec §31) is not written yet, and the engine fix is not linked.
- **P5, static.** The fixed page contains the mutation's line `      if (tile.documentSizeChanged) documentResized = true;` exactly once, and `node --check` passes on the page.

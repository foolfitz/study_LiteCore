Adversarial correctness review (read-only). Do not build, link, run browsers, or modify any file. Small greps and reading files are fine.

Repository: /home/jiajun/LibreOffice/study_LiteCore. Review exactly these two commits and nothing else:
- `git show baa1176ed` -- engine side of "ods-editor-v8": wasm_sdk_probe/src/calc_cell_bridge.cpp (OXSDK_ODS_COPY_HTML: op 15 also returns the core's text/html; OXSDK_ODS_ZOOM: op 16 stores gTileTwips, every op calls applyClientZoom, op 5 hit test divides twips by 256/T), sdk_api.*, the Makefile block ods-editor-v8, the worker delta tests/ods-v8-worker-delta.json.
- `git show 381869ee8` -- page side: wasm_sdk_probe/spreadsheet-shell/calc-document-sdk.js (normalizeCopy htmlText, setZoom, normalizeZoom), spreadsheet-shell/calc-editor-session.js (setZoom re-reads the selection's ends at the new zoom and returns the centre cell's rectangle before/after; _extent), viewer-shell/ods-viewer-session.js (setScale), web/ods-editor-app.js (every twips/px conversion now uses tw() = 15/scale; zoomTo keeps the centre cell; writeClipboard writes a ClipboardItem with text/plain + text/html, falling back to writeText), web/ods-editor.html.

Specs (the intended behaviour): specs/SPEC-P-calc-zoom.md and specs/SPEC-P-calc-copy.md sections 9-12. Native measurements already show the engine side is right on the native core (findings/evidence/calc-v8/README.md); the core lays rows out in whole pixels at the zoom it paints at, which is why every op must use the same client zoom as the tiles.

What I want: concrete defects with a failure scenario (inputs/state -> wrong output), each with file:line. Especially:
1. Any place in the page or session that still converts between twips and CSS px with a fixed 15, or mixes rectangles read at one zoom with another zoom (drag selection, header clicks, pointed references, the structure menu, autoscroll, sheet switching, undo/redo reads, the formula reference box, whole-row/column selection extents).
2. Races: a zoom click while a paint, a header refresh, a sheet switch, a drag or an undo is in flight; the `zooming` flag and pendingView handling in zoomTo; refit() comparing the handle's size from an old paint reply against the size op 16 returned.
3. Whether the engine's gTileTwips can disagree with the page's zoom (e.g. an op failing after op 16, a refused op 16, a new document in the same engine).
4. The clipboard path: anything that would make a Ctrl+C write nothing, write stale data, or lose the plain-text fallback.

Not defects (named limits, do not report): header labels not scaling; no zoom while editing; zoom not persisted; HTML lacking hidden rows/columns; Ctrl+wheel stays the browser's; tile canvases are 1 CSS px per canvas px (no devicePixelRatio).

Report in English, most severe first, at most 12 findings, each: file:line, defect, failure scenario, confidence (high/medium/low). If you find nothing real, say so. Separate what you verified by reading code from what you infer.

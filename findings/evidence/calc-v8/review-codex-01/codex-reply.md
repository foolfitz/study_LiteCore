Found seven defects. Code observations are verified by reading the two commit snapshots; failure scenarios are inferred, not runtime reproduced. No files were modified or builds, tests, or browsers run.

1. **[P1] Pointer input during zoom can select the wrong cell.** [ods-editor-app.js:1118](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:1118)  
   **Verified:** Grid pointer handlers do not check `zooming`. They convert coordinates immediately, while `selectAt()` executes later in the session queue.  
   **Failure scenario:** Start 100% → 75%, then click and release over a cell before op 16 returns. Both pointer coordinates use the old geometry; the queued hit tests execute at 75%. Because row positions differ between layouts, another row can become selected, directing subsequent typing there.  
   **Confidence: high.**

2. **[P1] A failed read after successful op 16 leaves incompatible zoom states.** [calc-editor-session.js:385](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/spreadsheet-shell/calc-editor-session.js:385)  
   **Verified:** `_zoom` changes immediately after op 16, but `viewer.setScale()` runs only after all subsequent cell reads succeed. There is no recovery around those reads.  
   **Failure scenario:** Op 16 accepts 75%; the centre, anchor, or focus read then rejects with `CELL_GEOMETRY_UNAVAILABLE`. The engine and page conversion helper now use 75%, while the scheduler still paints at 100% and selection rectangles retain old geometry. This error does not mark the session uncertain, so interaction continues with mismatched coordinates.  
   **Confidence: high.**

3. **[P2] Ordinary grid selection leaves zoom buttons disabled.** [ods-editor-app.js:484](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:484), [ods-editor-app.js:891](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:891)  
   **Verified:** Zoom controls disable while `dragWork` exists. Selection completion emits its final state before `extendDrag()` clears `dragWork`; clearing it refreshes only format controls.  
   **Failure scenario:** With painting settled, click or drag-select cells and release without scrolling. All three zoom controls remain disabled until another operation causes a full render.  
   **Confidence: high.**

4. **[P2] Zoom leaks into the next document opened in the same engine.** [calc_cell_bridge.cpp:97](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/calc_cell_bridge.cpp:97)  
   **Verified:** `gTileTwips` is engine-global. Its only runtime assignment is op 16; document close/open never resets it.  
   **Failure scenario:** Open A, set 75%, close A, then open B using the same engine. B’s cell reads and headers use 75%, although a new session starts with `_zoom = 100` and viewer scale 1. Its overlays and hit tests disagree with its tiles. The page’s fresh-engine `openBytes()` path avoids this; SDK engine reuse does not.  
   **Confidence: high.**

5. **[P2] Zoom before header refresh loses the centre cell.** [ods-editor-app.js:498](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:498), [ods-editor-app.js:511](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:511)  
   **Verified:** Zoom remains available during paint/header refresh. If cached headers do not cover the current centre, `centreCell()` returns null and zoom uses proportional pixel scaling. Cached headers also lack a checked zoom identity.  
   **Failure scenario:** Scroll to a distant region and immediately zoom before its headers arrive. The ratio fallback preserves a scaled pixel position rather than the same row. The supplied native measurements establish that accumulated row rounding makes these positions differ substantially. A rapid second zoom can similarly consume headers from the preceding zoom.  
   **Confidence: high.**

6. **[P2] `refit()` can overwrite op 16’s dimensions with an old paint’s dimensions.** [calc-document-sdk.js:314](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/spreadsheet-shell/calc-document-sdk.js:314), [ods-viewer-session.js:330](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/viewer-shell/ods-viewer-session.js:330)  
   **Verified:** `setZoom()` returns the new dimensions without updating the handle’s dimensions. `setScale()` updates `_fitted`, but `refit()` subsequently trusts the handle without checking which zoom produced its size.  
   **Failure scenario:** An old paint is awaiting `drain()` when zoom completes. Cancelling its outstanding tiles releases that drain before a new-scale paint updates the handle. Its unconditional `refit()` replaces the new dimensions with the last old-scale dimensions, temporarily resizing the surface and scroll bounds incorrectly. Later painting may repair them.  
   **Confidence: medium.**

7. **[P2] An older clipboard fallback can overwrite a newer copy.** [ods-editor-app.js:1254](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/ods-editor-app.js:1254)  
   **Verified:** Engine copy requests are serialized, but clipboard writes are outside that queue. There is no copy generation check before the fallback `writeText()`.  
   **Failure scenario:** Copy A starts an asynchronous HTML write; copy B starts before it settles. A’s write then rejects and its fallback writes A after B’s write, leaving stale plain text and potentially removing B’s HTML. The missing ordering guard is verified; this browser completion ordering was not reproduced.  
   **Confidence: medium.**

I found no remaining uncompensated fixed-15 conversion in the specified page/session paths. Invalid op 16 arguments are rejected before changing `gTileTwips`. For an isolated copy, HTML-write rejection correctly reaches the plain-text fallback.
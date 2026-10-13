# Prior art for D and for L-134-restore-flash: Collabora Online's Writer reconnect

Read-only reference: `study_LiteCore/cool-26-04` (online.mirror `distro/collabora/co-26.04` @ `c64a7343a5c6`, 2026-07-30). No code taken; this records what it does. It was read on 2026-10-13 at the owner's suggestion to look at Collabora for ideas.

A COOL reconnect reloads the document in core. That is the closest analogue to our automatic reopen after a boundary refusal: a fresh engine, with the caret at the start.

1. **Before teardown, save the scroll offset.** `browser/src/app/Socket.ts:571-576`: `_docLayer._savedScrollPos = activeLayout.viewedRectangle.clone()`, and `_restoringViewScroll = false`.
2. **While reconnecting, ignore the start-of-document caret.** `browser/src/layer/tile/WriterTileLayer.js:128-137`. The comment there says: "In writer, core always sends the cursor coordinates of the first paragraph of the document so we want to ignore that to eliminate document jumping while reconnecting". It sets `persistCursorPositionInWriter = true` and keeps `_savedCursorPos = lastCursorPos.clone()`.
3. **Once the full layout is back, click the saved caret and restore the offset.** `WriterTileLayer.js:227-238`:
   - If the saved caret centre is inside the document size, post `buttondown` / `buttonup` at `_savedCursorPos.center`.
   - Then set `_restoringViewScroll = true` and `scrollTo(_savedScrollPos)`.
4. **The caret update from that click re-affirms the saved offset instead of following the caret.** `browser/src/layer/tile/CanvasTileLayer.js:3089-3101` (`_onUpdateCursor`): while `_restoringViewScroll && _savedScrollPos`, it calls `scrollTo` the saved offset, then clears both and returns.

## Against ours (`wasm_sdk_probe/web/e2-editor-app.js`, page `6470dec0…`)

- **Step 3 is our D**: `placeCaret(x, y + height / 2)` at the engine's last caret, after `restart()`. Same idea: a click at the caret's centre. COOL also checks that the point is inside the document size before clicking. Ours only checks that the numbers are finite. The reopened document is the same content, so the point is inside unless the checkpoint differs.
- **Steps 1, 2 and 4 are what we lack.** Our `followCaret()` follows the fresh engine's start-of-document caret: the view goes to 0. Then it follows the restored caret back. That jump-and-return is **L-134-restore-flash**: 0.71–0.78 s at the start, measured in `acceptance-0.2.16/` and `restore-window/`.
- **COOL's shape would remove it.** Do not follow the caret from the moment the reopen starts until D has put the caret back (or failed). If D succeeds, the restored caret is where the view already is, so there is nothing to scroll. If D fails, follow the start-of-document caret as today, which is honest: the caret really is there.

**Not done.** It is a page change: new shell generation, host bump, and the condition-4 chain again. Whether and when to do it is a ruling, not something to do while the owner is away without one.

# fable's ruling on finding 122 (2026-10-10; the owner asked for it explicitly)

Brief: `brief.md` in this directory. The owner's later question (consider Collabora Online) was sent as an addendum while fable was working; the ruling below does not mention it, so it was asked again separately. Returned verbatim:

---

RULING

122: B′ — not A, not the brief's B as written, not C. Page only, in `renderDocument`: split the whole-canvas repaint into bands (≈ 2048 device px; the strip loop and the pixel-edge-derived twips already exist from 062), render the band(s) under the viewport first, blit each band as it arrives, and between bands check `renderAgain`: a new `document-invalidated` aborts the pass and restarts it visible-first. The remaining bands fill in afterwards. Because the page posts band k+1 only after band k replies, an insert posted meanwhile goes ahead of it in the engine's FIFO — the repaint becomes preemptible by typing without any throttle constant, and the canvas stays whole, so every whole-canvas reader in the nets (`INK_ROWS`, `LINE_INK`, `CARET_COLUMNS` in run_e2_c_product_path.py) still holds once the page is quiet. Not A: a throttle only helps bursts; the owner's complaint is the per-keystroke latency on their document (text appears only after a full ≈ 85 ms render — see FACT CHECK), which A leaves untouched. Not the viewport-only B: it blanks or stales the regions the product-path net reads at document fractions, forcing check changes with no §34.4 witness. Not C: no profile change is needed once the visible band is ≈ 8 ms; register it as "only if B′ measures above target".

Ships together, shell v59 / host 0.2.10: 122 (B′), 121 (`beforeinput`: selection not collapsed and `session.offers("delete-selection")` → `delete-selection`, both inputTypes, the cut path's judgement), 120 (one line after `attachInput`). Three commits.

WHY（給擁有者）

1. 探針的「上螢幕」量錯了：它抓的是修訂號更新後的第一次 blit，而那一下是游標覆蓋層用舊圖重畫（每次只差 0.1–4 ms），字其實還沒出現；唯一一次真的量到畫好的是第 20 字，晚了 87 ms。
2. 所以你在正常打字時感覺到的慢，是每一鍵都要等整份 22 頁重畫完（約 85 ms）才看得到字，不只是快打時的堆積。
3. 節流（A）只管快打堆積，正常速度一樣慢；只畫可視範圍（B）會讓回歸網讀整張畫布的檢查全部失準。
4. 改法：把整張畫布切成一條條，先畫你看得到的那一條、畫一條貼一條，打字進來就中斷重排——其餘的在你停下時補完。
5. 不動 worker、不換 profile；121、120 一起走這一次頁面發佈（v59、宿主 0.2.10、一次重新計數）。
6. 驗收前探針要先修：「上螢幕」必須是帶著新修訂號的那張圖貼上去的時間，而且先在現在的頁面上讀出約 120 ms（不是 40 ms）才算儀器可信。

FACT CHECK

- F1 — correct (`layoutCanvas` :773–785, `renderDocument` :803–905, `MAX_TILE_HEIGHT` 32767 :152, `MAX_BACKING_WIDTH` 2400 :130). The engine `calloc`s the full buffer per paint (probe_engine.cpp :3103), the worker copies it (`copyOwnedBuffer` sdk-worker.js :755) and transfers it, the page wraps it in `ImageData` — three ≈ 80 MB passes per repaint on the owner's document.
- F2 — correct (`openDocument` `onEvent` :2050–2052; `run()` :1226; coalescing :807/:902). Addition: the worker posts `document-invalidated` for LOK ids 0 AND 1 (sdk-worker.js :1109–1114), so a caret move alone also triggers a whole-document repaint.
- F3 — holds structurally: paint and insert are engine commands on one FIFO (`submit` :2423, `handleInsertText` :3186, the paint handler :3112). Not instrumented, as the brief says.
- F4 — correct (:1111–1114 forward only handle and revision).
- NOT in the brief, and load-bearing: the README's "key → on screen" column does not measure the character appearing. `probe_typing_latency.py` takes the first `putImageData` at or after the `#s-revision` change (:118–122); `updateState` writes that element and then calls `paint()` (web/e2-editor-app.js :613, :665), which blits the cached `lastTiles` plus the caret. The data shows it: gap 200 Chrome paint − rev = 3.8–4.1 ms on every row, Firefox 0.7–0.9, boundaries 2.6; gap 80 rows 2–18 = 0.1–0.3 ms; only row 19 (no further state update before the render) = 87.5 ms — the one direct observation of text on screen. So "≈ 40 ms on screen at 200 ms gaps" is withdrawn; the true figure on the owner's document is unmeasured and, from row 19, ≈ rev + 85–90 ms ≈ 120–135 ms (Chrome). That is what the owner feels at normal speed. The "key → committed" column and the backlog finding stand.
- 121: v19 manifest `delete-backward`/`delete-forward` gestures `["collapsed"]`, `delete-selection` id 20 `["range-single","range-cross"]` with the table limit; `DELETE_INPUT_TYPES` :1683 maps unconditionally; cut :1913 already uses `offers("delete-selection")`. Correct.
- 120: `attachInput` (editor-session.js :206) only calls `input.attach`; the adapter exposes `state.blocked` publicly (input-adapter.js :80–92). The one-line fix is sound.

CONDITIONS

Write first, appended to `specs/SPEC-M3-production-ui.md` (new section), with predictions; correct `findings/evidence/typing-latency/README.md` by appending (the "on screen" column renamed "next overlay blit, stale tiles"; row 19 named as the only text-on-screen observation).

Instrument, before any acceptance run (probe only, no product byte): "on screen" for character i = the first `putImageData` of a NEW `ImageData` (constructor wrapped, WeakSet) whose band covers the caret line and whose render reply carried `revision ≥ start + i + 1` (pair `Worker.prototype.postMessage` render requests with their replies by `requestId`; the reply's `value.revision` is forwarded by the worker, :760). Red case on the CURRENT page: the fixed instrument must report ≈ rev + 80–100 ms (not 4 ms) at gap 200 on the owner's document; if it still says ≈ 40 ms it is wrong. Positive control once: `LINE_INK`-style ink growth on the caret line agrees within one band.

Unit (page functions compiled as the B1 tests do): B1 bands cover the canvas exactly (edges from pixel edges, no gap, no overlap; a 22,256-px canvas → 11 bands); B2 order: the band under the viewport first; B3 a `document-invalidated` arriving between bands aborts the pass and the next pass starts visible-first; B4 each band is blitted on arrival and `lastTiles` stays a consistent set for `paint()`; B5 `documentSizeChanged` on any band → relayout + full pass (118 unchanged); B6 `TILE_NOT_PAINTED` per band still throws (062 unchanged); 121-U: non-collapsed selection + offer → `delete-selection`, collapsed → `delete-backward`/`-forward`, no offer → today's action; 120-U: after `attachInput` the sink's `disabled` equals the new adapter's `state.blocked`. Red cases, each red once: render in document order (B2), ignore `renderAgain` between bands (B3), blit only at pass end (B4), drop the offer check (121-U), drop the line (120-U).

Browser (candidate `dist/`, both browsers, the fixed probe), owner's document: gap 80 × 20 chars — key → committed max < 80 ms (today 775), no growth (commit intervals ≈ gap), key → on screen median < 70 ms Chrome / < 90 ms Firefox, max < 150 ms; gap 200 × 10 — on screen median < 70 / < 90 ms; after the last key the full canvas is current within 200 ms (last band's new-ImageData blit); boundaries.odt gap 200 not worse than today's key → committed. 121-B: `select_delete_probe.py` on both browsers, Backspace and Delete on `range-single` → the word removed, state `ready`, generation 1 (today's reports are the red case). 120-B: `sink_probe.py` residue arm → `Q` lands (today's `sink-*.json` are the red case).

Release, in order: three commits → `make test-e2-c-static` (§14.5 reading before the freeze) and E1-C intact → `make e2-c-assets` (cutover pins unchanged) → the three browser criteria above on `dist/` (anything they force goes back before the freeze) → freeze v59 last (never touch v58) → host 0.2.10 (`package_m3_engine.py`, info.xml, `occ upgrade`) → re-pin the seven runners, pin lines only → red cases, the count chain, the product-path net per M2-5 on the new page, static exit 0. Handoff numbers expected 0 / 0.

Must not: change the worker or any profile file; make the canvas viewport-only or leave any band stale once the page is quiet; add a throttle or debounce constant; touch the product-path runner's pixel readers or any check beyond pin lines; run or cite acceptance with the current "on screen" metric; mark 122 fixed without the gap-80 backlog cell and the gap-200 on-screen cell both green in both browsers; bundle anything beyond 122/121/120 into v59.

---

## Main session's check (2026-10-10)

The load-bearing correction holds: `updateState` writes `#s-revision` and then calls `paint()` (`web/e2-editor-app.js` :613, :665), and `paint()` blits the cached `lastTiles` (:960–963). The reports' paint − revision gaps are 3.8–4.1 ms (Chrome, gap 200), 0.7–0.9 (Firefox), 2.6–5.8 (boundaries), 0.1–4.2 (gap 80, rows 0–18), and 87.5 ms for row 19 — the stale overlay blit every time but the last.

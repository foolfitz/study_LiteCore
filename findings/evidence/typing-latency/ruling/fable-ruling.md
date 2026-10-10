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

---

# Second answer (2026-10-10): does Collabora Online change B′? (the owner's question)

Returned verbatim:

RULING

COOL does not change B′ — keep it, with one small amendment and a sharper C registration. COOL solves the same problem with the same shape B′ already has: forward the invalidation, keep the old pixels on screen, refetch only what the user can see, visible first, coalesce bursts. What COOL adds on top (fixed 256-px tiles, a wire-id tile cache, zstd deltas, PNG, a 5-s request cooldown, prefetch borders) exists to save bandwidth and server CPU across a socket shared by many views; we have one consumer, one engine, zero-copy transferable buffers, no zoom levels — none of that pays here.

- Borrow now, inside B′ (page only): (1) order the background bands by distance from the viewport, not top-to-bottom (COOL's `distanceFromView`); (2) COOL's rule "an invalidated tile keeps its old bitmap until the new one arrives" — B′ already does this by replacing bands on arrival; make it explicit in the criteria (never clear a band). (3) COOL's wsd re-renders the visible invalidated tiles proactively on invalidation, without waiting for the client — that is exactly B′'s "visible band first on `document-invalidated`"; nothing to add.
- Borrow later (worker change → new profile identity, no relink): C in COOL's shape — forward `x, y, width, height` plus a monotonic wire id (`gEditorState.documentChangeSequence` already is one) in `document-invalidated`; the page unions rectangles and re-renders only the bands they intersect, and uses the band reply's `revision` against the invalidation's id as the race guard (`invalidFrom >= wireId`). Trigger: only if B′'s visible band measures > 40 ms on the owner's document or a document class makes full-width bands too slow. COWASM proves the forwarding is trivial inside one WASM process: it runs kit and wsd in pthreads and passes the identical `invalidatetiles:` text frame to the browser over a fake socket.
- Do not borrow: deltas/keyframes (`Delta.hpp`), PNG/zstd, the tile cache keyed by wire id across zooms, tilecombine dedup, the 5-s cooldown, prefetch, `EMPTY` invalidation, split panes, the decompression TaskWorker. Also: borrow mechanisms, not code — COOL is MPL-2.0 (header of every file cited); cite as prior art with file:line, do not paste.

WHY（給擁有者）

1. 該參考，而且它印證了 B′：COOL 同一顆核心、同一個問題，做法就是「核心報哪裡髒、瀏覽器把舊圖留在畫面上、只重抓看得到的、看得到的先抓、一串髒訊息合併」——B′ 全有。
2. COOL 多出來的那些（256 像素小磚、磚快取、差分壓縮、PNG、五秒冷卻、預抓邊緣）是為了省網路頻寬和伺服器 CPU、給很多人同時看；我們一個人、一個引擎、零拷貝傳圖，用不到。
3. 現在只借一件小事：背景補畫的順序改成「離視窗近的先」。
4. 之後若 B′ 量出可視那一條還是太慢，再做 C：讓 worker 把髒區矩形和一個遞增序號傳給頁面，只重畫被碰到的那幾條——COWASM 證明這在單一 WASM 行程裡就是一行訊息的事，但動 worker 就是新 profile、要 cutover。
5. 程式碼不要抄（MPL-2.0），只引用它的做法並註明檔案行號。

FACT CHECK（/home/jiajun/LibreOffice/study_LiteCore/cool-26-04）

- Kit forwards `LOK_CALLBACK_INVALIDATE_TILES` with its rectangle and a wire id: `kit/ChildSession.cpp:3827–3889` (`invalidatetiles: part= mode= x= y= width= height= wid=`; `EMPTY` = everything; Writer forces part 0). The kit coalesces a burst before sending: `kit/KitQueue.cpp:160–262` — a queued invalidation fully covered by a new one is dropped (:218–230), intersecting ones are joined if the union stays under 4×3840 × 2×3840 twips (:234–262); `kit/Kit.cpp:1299–1305` routes INVALIDATE_TILES through that merge for all views.
- Browser tile size 256 px: `browser/js/global.js:297`. Tile state with `wireId`/`invalidFrom`, `needsFetch = invalidFrom >= wireId || !hasContent`: `browser/src/app/Tile.ts:25–26, 41–43`; `forceKeyframe` :60–64; the 5-s per-tile cooldown :66–71.
- Invalidation → tiles: `browser/src/layer/tile/CanvasTileLayer.js:1327–1342` parses the message; `browser/src/app/BitmapTileManager.ts:1424–1452` intersects the rectangle with every cached tile and calls `invalidateTile`, which keeps the old bitmap and only marks the keyframe forced (:2288–2309: a tile without content is removed, one with content gets `forceKeyframe(wireId)`).
- Which tiles get requested, in what order: `updateTileDistance` sets `distanceFromView = 0` for visible tiles and the distance to the view centre otherwise (`BitmapTileManager.ts:1147–1178`); the request loop queues only `!tile || tile.needsFetch()` within the current/expanded tile range (:1236–1281); `sendTileCombineRequest` dedups keys and skips tiles asked < 5 s ago, sending `oldwid` per tile (:1056–1110); `tilecombine` protocol with `oldwid=0` forcing a keyframe: `wsd/protocol.txt:272–280`; `invalidatetiles:` wire format :663–671.
- wsd side (also inside COWASM): `TileCache::invalidateTiles` marks intersecting cached tiles invalid (`wsd/TileCache.cpp:411–449`); `ClientSession::handleTileInvalidation` then builds a `TileCombined` of the invalidated tiles inside the client's visible area and renders them proactively (`wsd/ClientSession.cpp:4087–4199`, visible-area iteration :4147–4192).
- Kit rendering: one `paintPartTile` over the bounding area of the combined request, then split into tiles (`common/RenderTiles.hpp:77–133`, warning above 4096 px :117–120); per tile a delta against the previous keyframe or a keyframe, with "identical → zero-length delta, skip" (`kit/Delta.hpp:620–630`).
- COWASM keeps the protocol unchanged in the browser: `wasm/wasmapp.cpp:38–58` (`send2JS` → `MAIN_THREAD_EM_ASM` → `TheFakeWebSocket.onmessage`), `handle_cool_message` :62–73; wsd and kit sources compiled in: `wasm/Makefile.am:60–80` (`ClientSession.cpp`, `DocumentBroker.cpp`, `TileCache.cpp`, `KitQueue.cpp`, `FakeSocket.cpp`). The earlier study's runtime model (`research/RESEARCH-2026-08-01-cowasm-co-26-04-reference.md` §3) still describes it correctly: main-thread module, computation in pthreads, no JSPI.
- Our side, for the mapping: the engine already stamps `documentChangeSequence` on every INVALIDATE_TILES (`wasm_sdk_probe/src/probe_engine.cpp:2632–2633`) and the tile reply already carries `revision` (:3153–3156; the worker forwards it, `sdk/sdk-worker.js:760`); the worker drops the rectangle (:1111–1114). So C needs only the worker to forward the payload rectangle and the sequence; no engine change.

CONDITIONS（only what changes）

1. B′ amendment: background bands ordered by distance from the viewport (unit test B2 extended: visible first, then nearest first); add to the criteria "a band is never cleared; old pixels stay until the new band arrives".
2. C registration (relink-queue item, no relink): forward `{x, y, width, height, documentChangeSequence}` in `document-invalidated`; page: union of rectangles since the last pass → re-render only intersecting bands, visible first; race guard = band reply `revision` vs the invalidation's sequence. Trigger written now: B′'s visible-band render on the owner's document > 40 ms (either browser) or a measured document where the full pass exceeds 1 s. Cost: new profile identity (repackage, cutover, re-validation round) — not this release.
3. Spec/finding text: cite COOL as prior art with the file:line above; no code copied (MPL-2.0).
4. Not borrowed, and say so in the finding: deltas, PNG/zstd, tile cache across zooms, cooldown, prefetch, `EMPTY`, split panes.

## Main session's spot check (2026-10-10)

`cool-26-04/browser/src/app/BitmapTileManager.ts:1147` is `updateTileDistance` (visible tiles get distance 0); `wasm_sdk_probe/src/probe_engine.cpp:2632–2633` sets `documentChangeSequence` on `LOK_CALLBACK_INVALIDATE_TILES`. Both as cited.

---

# Third ruling (2026-10-10, on `brief-2-firefox-misses.md`; fable, on the owner's behalf — the owner asked "發給fable裁決" for 122). Verbatim.

RULING

A + B, and the whole-canvas cell → (ii).

- A (sink `beforeinput` of any input type that will reach the engine — composition updates excluded — sets `renderAgain` ONLY while `rendering` is true; no `preventDefault`, no adapter contact). It removes the structural waste F2(2): the band the page posts after the in-flight one returns, before it has been told of the change. Verified in `raw.blits`: Firefox gap 200 key c (8225.7) +22.5 old band, +61.0 new-revision band 18423 off-screen, +78.9 revision, +87.4 band 0; gap 80 key b the same shape (+22.5 / +53.3 / +72.0 / +79.5). Chrome never shows it because its pass (9 bands × 11–15 ms) ends before the next key at gap 200.
- B (`RENDER_BAND_HEIGHT = Math.floor(MAX_TILE_HEIGHT / 32)`, ≈ 1023 rows). Halves the in-flight wait and the render of the visible band — the two terms that remain in Firefox's commit after A: insert alone 43 ms median / 50.5 max (`v58-firefox-owner-gap200-fixed-instrument.json`), so A alone leaves commit ≈ 43 + ≤ 20 + ≤ 20, which straddles the 80 line; with B ≈ 43 + ≤ 11 + ≤ 11. Band cost is near-proportional to rows (a ≈ 1100-row band ≈ 10 ms in both browsers on `boundaries`, a 2047-row band 12–16 Chrome / 18–20 Firefox), so the full pass grows only by the per-request overhead (predicted ≤ +30%).
- Whole-canvas cell → (ii), restated per instance: after the last key, the next pass runs to completion without an abort and every band's blit carries the last character's revision (`allCurrentAfterLastKeyMs` not `None`, within the probe's quiet window); the time is RECORDED, per browser, as a named number with a prediction, not gated. Reason, written now: the 200 ms was derived from Chrome's single-strip render; a quiet Firefox pass is ≥ 11 × 18–20 ms at this window and cannot meet it under B′ whatever the ordering (F4 holds). The property the cell protects ("no band stale once quiet", first ruling's must-not) is per-instance and is what (ii) asserts. Not (i): C is not justified by a bound that was never derived for Firefox.
- The two latency numbers stay (Firefox gap-80 commit max < 80, gap-200 on-screen median < 90). Predicted with A+B: Firefox commit max 65–78, on-screen median 55–68; Chrome commit max 45–55, on-screen median 45–55. If Firefox's commit max still lands ≥ 80 with no growth, stop and bring a third brief with the insert-alone floor measured on the candidate — do not restate that cell yourselves.
- Fact check: F1–F4 hold against `raw.blits` and the v58 baselines. One confound to record: the two browsers do not paint the same canvas — Firefox 22,257 rows vs Chrome 17,929 (≈ 24% more pixels per band in Firefox at the same band height), so part of "Firefox is slower per band" is window size. Equalise the window in the probe if it is one line; otherwise record both canvases' width × height beside every number.

CONDITIONS（before v59 freezes）

1. Append §15.6 to the spec before any run: A, B, the restated whole-canvas cell with the reason above, the window confound, and predictions (the numbers above; full pass recorded: Firefox 230–300 ms, Chrome 160–230 ms).
2. Unit: B1 re-stated for the new band count (22,256 px → 22 bands, edges exact); B8 a `beforeinput` during a pass ends it after the in-flight band and the next pass starts with the visible band; B8-control a `beforeinput` while idle sets nothing and starts no pass; B2–B7 unchanged. Red cases, each red once: band constant back to /16 (B1), drop the `rendering` guard (B8-control), drop the listener (B8).
3. 122-B re-run in full — both browsers, all six reports — on the new candidate `dist/` (the page bytes change, so every cell re-binds to the new sha; Chrome's cells must hold, not be assumed). Same probe (`dbad93c0…` or the window-equalised one, whose red case must still read the v58 baselines as FAIL).
4. Freeze v59 only when: Chrome all cells; Firefox gap-80 no growth and commit max < 80, gap-200 on-screen median < 90, max < 150 both gaps; whole-canvas (ii) satisfied in both; `boundaries` unchanged. Then the R‴ order of §15.2 as written.
5. Must not: add any constant beyond B's derived one; make A call `preventDefault` or touch the adapter; set `renderAgain` outside a running pass; restate the latency numbers; freeze on Firefox's three cells partially green; run 122-B concurrently with other headless-browser work.

WHY（給擁有者）

1. Firefox 慢的原因讀出來了：每按一鍵，頁面在得知文件變了之前，會先多畫一條看不見的條（約 30 ms 白費），而且每條在 Firefox 要 18–20 ms。
2. A 是讓「使用者開始輸入」就結束這一輪補畫，下一輪直接從你看得到的那條開始——白費的那條就沒了。
3. B 是把每條切一半（約 1000 列）：等待中的那條和要畫給你看的那條都只剩一半時間；整張補完只慢一點點。
4. 「最後一鍵後 200 ms 內整張換新」那個數字是從 Chrome 一條到底的時代推出來的，Firefox 光是安靜地畫完一輪就要 220 ms，再怎麼排序都過不了；它真正守的是「安靜之後沒有舊的條」，改成逐條驗這件事，時間照實記、不當門檻。
5. 兩個延遲數字不動；A+B 之後預測 Firefox 都過。若 80 那格還是沒過，不要自己改數字，帶著量到的底線再來裁一次。
6. 一件要記下的事：兩個瀏覽器畫的畫布大小不一樣（Firefox 多 24% 像素），所以「Firefox 比較慢」有一部分是視窗比較大。
7. 頁面變了，六份報告兩個瀏覽器全部重跑，Chrome 不能靠上一輪。

# Fourth ruling (2026-10-10, on `brief-3-firefox-commit-floor.md`; fable, on the owner's behalf — the owner sent 122 to fable, and chose "B 交 fable 裁決" for Part 2 in this session). Verbatim.

PART 1

FACT CHECK
- G1 holds. `control-v58page-…gap600-floor` 42.7/59.7, `control-bprime-b10f6017-…` 54.1/57.5, `v59-candidate2-firefox-owner-gap600-floor` 57.6/74.4, Chrome A+B 35.9/41.4; each report's `page` sha is the page it claims. My third ruling's "43 + ≤11 + ≤11" used `v58-firefox-owner-gap200-fixed-instrument.json` (43.0) — the v58 floor. (The swap/restore procedure rests on the README's word; the shas are the evidence.)
- G2 holds, with a caveat. `lazy_shim_probe.py` does only what it says (two per-call `dataset` writes → one `setTimeout(0)` flush; probe `dbad93c0` untouched). Idle v58 44.7 vs 42.7, A+B 52.7 vs 57.6 (≈5 ms); gap 80 max 84.9 (3/20 ≥ 80). Caveat: the lazy gap-80 MEDIAN is 71.1 vs 65.3 — run-to-run spread exceeds the effect measured, so "≈5 ms" is a one-run estimate. The unlocated ≈8 ms: `updateState()` ends in `paint()` (e2-editor-app.js:665, :1025–1029), which re-blits all 22 bands (~80 MB) on every state write; at idle that is 130 stale `putImageData` per key on A+B (clusters 65/44/21) against 6 whole-canvas calls on v58 — same bytes, 22× the calls, and A+B's first burst starts 5 ms later. Not located, but that is the candidate (registration R2).
- G3 holds. `raw.blits` Firefox gap 80, keys 6–11: band 0 blitted twice per key, same revision; `#s-revision` changes 0.5 ms before the SECOND blit every time (key 8: +51.5 / +75.1 / +75.6). Chrome varies: key 7 the pass ran on to band 1 before the restart and the revision landed 0.2 ms before band 1's FIRST blit (+54.1/+54.3), then bands 0 and 1 were both re-rendered. That Chrome row is load-bearing against A′'s hoped-for gain: the drain's write is paced by when the engine answers, not by the duplicate band.
- G4 partly holds. Fields: yes — the paint reply carries `gState.revision` (probe_engine.cpp:3157), forwarded (`sdk-worker.js:760`), returned whole by `render()` (`document-sdk.js:397–421`), so `tile.revision` is visible in `renderDocument`; `document-invalidated` carries `gCallbackRevision` (:2540–2548; worker :1111–1114) and reaches the page's `onEvent` whole (`editor-session.js:598`). Same counter: `gCallbackRevision` is a copy of `gState.revision` (:2478–2481, :3210–3211). Missed: (i) `handleInsertText` increments AFTER `paste`/`postKeyEvent` (:3189–3211) and the callback stamps the revision at delivery — "covered" is correct only if LOK delivers INVALIDATE_TILES after the handler returns; nothing measures it (the probe records no event revisions). A callback delivered inside the LOK call carries the PRE-change revision and A′ keeps a stale band — the first ruling's must-not. (ii) The comparison must run at the loop check after the in-flight band returns; in the event handler the blitted set is empty and "covered" is vacuous. (iii) A's `beforeinput` must stay a boolean that always ends the pass. (iv) Effect on commit unestablished, and the Chrome key-7 row says probably nil; the saving is Worker time (≈10–13 ms/key Firefox, 8–10 Chrome) and one band of fill-in.

RULING: R. Not A′ in v59 (registered below). The restated cell replaces §15.6's "gap-80 commit max < 80", for both browsers; every other number stays.
  Cell: "At gap 80 × 20, per browser, from `rows[].revisionMs` of the bound report: (a) every key's revisionMs < 2 × gap (= 160 ms) — no key is ever two behind; (b) the run's median revisionMs < gap (= 80 ms) — the drain keeps up with the keys."
  Form: (a) per-instance; (b) a tool-closed aggregate over the report's rows, computed by a reader — no hand reading. The only constant is the run's own gap.
  "No growth" becomes (a)+(b). The per-key backlog b_i = max(0, revisionMs[i−1] − (key_i − key_{i−1})) and the first-five/last-five medians are RECORDED per browser with a prediction, not gated (today's reading of them is by hand — a §2 defect in my own earlier cell).
  Reason, written now: 80 was floor + two half-bands using the v58 floor; the candidate's own idle floor is 57.6/74.4 (G1), so the derivation's premise is gone and I withdraw the number rather than build A′ to rescue it. The user-facing cell is met with margin in both browsers; a 2.6 ms one-key excess at utilisation ≈0.8 is absorbed by the next key. Not A′-then-R: A′'s commit effect is unestablished, its safety premise is unmeasured, and the brief's own on-screen prediction for it is ±5.
  Default if never measured: 122 not fixed; v59 does not freeze.
  Predictions on the existing reports: Firefox (a) 82.6 < 160, (b) 65.3 < 80; Chrome 54.8 / 45.2 — PASS both. The bite lives in the reader's red cases, not in these numbers.

CONDITIONS (before v59 freezes)
1. Append §15.8 before the reader runs: the cell, form, reason with G1's numbers, default, predictions, registrations R1/R2.
2. Reader (reads existing JSON, no browser), per browser: binds `page` = `18c8afbe…` and `runner` = `dbad93c0…` (the lazy diagnostics cannot count); checks (a), (b) on the two gap-80 reports and re-checks every other §15.6 cell from `summary` (on-screen medians/max both gaps, (ii) not None, boundaries); prints b_i and first/last-five medians; exit 0 only when both browsers pass. Red cases, each red once: `v58-chrome-owner-gap80-fixed-instrument.json` (median 508.2, max 814.6; there is no Firefox v58 gap-80 report) → FAIL (a) and (b); the Firefox candidate report with 80 added to every revisionMs → FAIL (b) only; with one row set to 160 → FAIL (a) only; a report whose `runner` is the lazy shim → refused.
3. No page byte changes for 122: 122-B is NOT re-run; the six `v59-candidate2-*.json` are the evidence. If any page byte changes before the freeze, the third ruling's condition 3 (full 122-B, both browsers) stands.
4. 121-B and 120-B on the final page bytes (deferred in §15.7), then R‴ of §15.2 as written; the Part 2 re-anchor goes in before `make test-e2-c-static`.
5. Must not: implement A′ or any `paint()` change in v59; touch probe `dbad93c0`'s recording; restate any other number; freeze with either browser failing (a) or (b).
6. Registrations (next page change, not v59). R1 A′: admissibility measurement first — the probe's Worker wrapper records `document-invalidated` revisions; admissible only if every invalidation following an insert carries that insert's post-increment revision; one pre-change value and A′ is dropped, not patched. Unit: covered → continue; not covered → restart; empty blitted set → restart; `beforeinput` → always restart. Red cases: drop the comparison (today's behaviour), never restart. Predictions: on-screen ±5, commit ±5, Worker −10–13 ms/key Firefox. R2: `updateState()→paint()` re-blits the whole canvas on every state write, ≈6 writes/key — finding candidate; measure bytes blitted per key v58 vs A+B before any design.

WHY（給擁有者）
1. 80 這個數字是我拿舊頁面（v58）的 43 ms 底線加兩個半條推出來的；新頁面在什麼都沒在畫的時候，底線本身就是 58 ms（最慢 74）。前提沒了，數字就該撤，不該再加一層機制去保它。
2. 你真正會感覺到的是「字出現」：Firefox 中位數 49 ms、最慢 72（之前 187），Chrome 37，兩邊都過、有餘裕。
3. 差的那 2.6 ms 是「第 9 鍵的計數更新比第 10 鍵晚了 2.6 ms 才到」，下一鍵就吸收掉，20 鍵沒有累積——使用者看不到。
4. 改成兩條：每一鍵 < 160（絕不落後兩鍵）、全輪中位數 < 80（引擎跟得上）；由讀報告的工具算，不再用人眼讀頭五尾五。
5. 既有六份報告就能判，頁面不動、不重跑；121／120 的瀏覽器驗收要在最終頁面上補跑。
6. 「可視條畫兩次」是真的浪費，但只省 Worker 時間、螢幕上看不出來，而且它的安全前提（失效訊息帶的是改完之後的版本號）還沒量過——登錄到下一次改頁面時做。
7. 另登錄：頁面每次狀態更新都把整張 80 MB 畫布重貼一次、每鍵約六次，兩個頁面都這樣，很可能就是那 8 ms 的藏身處。

PART 2
RULING: re-anchor as proposed.
Verified: old find string 0 hits in web and dist (both `18c8afbe…`); proposed find string exactly 1 hit in both (e2-editor-app.js:918); the replacement keeps the same defect (`documentResized` never set → no relayout when the document grew; the dead `break` changes nothing); the witness shows exactly this failure, the generation guard the only other red.
CONDITIONS
1. Change only `find`/`replace` of `ignore-a-document-that-grew` (run_e2_c_product_path.py:1799–1807); `tests.test_product_path_mutations` green; `make test-e2-c-static` red only on the generation guard until v59 freezes.
2. Before any counted product-path run: that one mutation, one browser, `the-canvas-follows-a-document-that-grew` must be red (precedent 521ed923); file the run beside the witness.
3. Handoff counts 因執行而修 1／因審核而修 0; the commit message names the witness path.
WHY（給擁有者）
1. 突變要找的那一行被 B′ 改寫了（多了大括號和 break），找不到就報 0——是錨點過時，不是檢查錯。
2. 新錨點意思一樣：文件長了，畫布還是開檔時的高度。
3. 照 119 那次先例：換字串、跑一次證明它真的會咬人，計入「因執行而修 1」。

# Fifth ruling (2026-10-10, on `brief-4-whole-document-canvas.md`; fable, the owner asked "發給fable裁決"). Verbatim.

## Part 1 — the option

RULING: **A now, as its own release; then C′ amended (a windowed canvas, not a sticky one, with B folded in) as its own spec and release.** Not B alone (same harness port as C′, keeps the 321 MB canvas and H6's 22 ms blit — dominated). Not C (page-drawn scrolling buys nothing we measured; native scrolling is what the sink, IME and a11y nodes already ride). Not D: the measured failing configuration (ratio 2, window ≥ 940 CSS px) is a 14-inch laptop at Windows' default 150% with a maximized browser, i.e. the buyer's machine, not the owner's.

Per configuration (commit median / on-screen median, ms; H# in brackets, all checked against the JSON unless marked):
- **Ratio 1, 900 px (the owner; the counted configuration).** Shipped: Chrome 42/34, Firefox 60/45. A: Chrome ≈ 26/25, Firefox ≈ 39/32 [H2, checked: whatif-skip rows]. Already passing; A buys margin. C′ buys only memory here (160 MB → tens).
- **Ratio 2, narrow (1450/1238 wide).** Shipped fails §15.8(b) in both (106.7/105.6) and (a) in Firefox (171.2). A: Chrome 35/33 [H4, checked]; Firefox 60/33 **only if** a small-source blit into a 152 MB canvas is cheap — unmeasured, see Part 5 item 1. C′: Firefox on-screen and the memory.
- **Ratio 2, wide (1800 × 44,514, 321 MB).** Shipped: Chrome 426/369 (122's symptom), Firefox 208/91. A: Chrome 47/47 [H4, checked]; Firefox ≥ 159/82 — the what-if is an UPPER BOUND on A's gain (the README says so; the brief's option A text does not), and if H6's "the cost is the destination's" holds for small sources, a real A pays ≈ 22 ms per paint task twice per key and lands ≈ 200. **Named limit on the A page; closed by C′.** C′: predicted Chrome 35–50/35–50, Firefox 55–85/40–60 (H5+H6 removed; the insert floor at ratio 2 is unmeasured).
- **Any ratio, long documents.** The brief lists "the canvas-height ceiling" without numbers. From 062 (65,535 usable rows in BOTH browsers; 65,536 → Chrome draws nothing below, Firefox NS_ERROR_FAILURE) and the measured canvases: ≈ 2,023 rows/page at ratio 2 wide → a **33-page** document is 062-blank on a HiDPI maximized window today; ≈ 1,012 rows/page at ratio 1 → **65 pages**. `layoutCanvas` (:773–785) caps width at 2400 and height not at all. Institutions have 33-page documents. This is C′'s strongest "划算" argument and the brief undersold it; verify it as a red case before C′ (Part 4).

What C′ costs, corrected: the band model, visible-first order, `renderAgain`, `paintBand`, the 062/118 tests and the 1023-row band constant all stay; what changes is the destination mapping (a y-offset and which element supplies geometry) in `layoutCanvas`, `visibleCanvasRows`, `paint`/`paintBand`, `drawOverlay`, `moveSinkToCaret`, `pointToTwips`, `positionProjection`, and the four pointer listeners moving from `#canvas` to `#paper` (:1712, :2060, :2067–2068). `#sink` and `#a11y-doc` are already absolute inside `.paper` (`position: relative`, html :86/:104/:164), so their coordinates hold — the brief is right there. The real cost is the harness port (Part 2) and one more release cycle.

Amendments to C′ (binding): (1) **not `position: sticky`** — a sticky canvas repainted from the `scroll` event lags the compositor's async scroll by a frame on every scroll frame (Firefox warns about exactly this); instead an absolutely positioned canvas ≈ 3 viewports tall inside the `.paper` spacer, re-placed and redrawn in one task when the view nears its edge, so native scrolling moves it with the content and the only visible cost is old pixels/blank during a fast fling while bands render on demand — a **new named limit**, measured not gated. (2) B folded in: after a revision change every band outside the window is stale-by-revision (H9 means there is no rectangle to narrow this; assume none ever comes); a band keeps its old pixels until its replacement arrives (COOL's rule, second answer). (3) `lastTiles` bounded to window ± N bands, evicting the rest — otherwise the 321 MB JS copy stays and the brief's "removes 2 × 321 MB" is half true. (4) A's dirty-rect `paint()` carries over with the y-offset; nothing from A is thrown away.

A, specified: `paint()` blits nothing unless the overlay's inputs (caret rect, selection rects, collapsed flag) differ from what is on the canvas; when they do, restore the union of the old and new overlay rects from the band cache and redraw the overlay clipped to them. The pending/busy/pending/ready writes then cost zero blits [H1, checked]. No throttle, no debounce, no coalescing constant. R1 (A′): **out** in both releases — under C′+B the running pass is one or two bands and the stale-by-revision bookkeeping is the same comparison; A′ has nothing left to skip.

## Part 2 — harness under §34

The port is neither a new tool nor a fix of a misjudging check; it is a **check fix forced by a product change, with a witness constructed on purpose**: the run of the UNPORTED net on the C′ candidate (honest, committed, red only on geometry-addressed checks, for the reason the port exists). That satisfies 34.4's letter. Count it as 因執行而修 **1 per runner** by porting one shared addressing helper, not per check: scroll the point's document fraction into view, `elementFromPoint`, dispatch (bubbles reach `#paper` on the new page and `#canvas` on the old); ink reads scroll the rows into the window and read the window canvas — the pixels on screen, not the band cache (CLAUDE.md §7). Not a 34.3 review unless more than half the runner is rewritten (it will not be). Trust while ported: a reader (form 2, new, no browser) compares two product-path reports cell for cell; the ported net on the unchanged whole-canvas page must show **0 differences** against that page's counted verdict (RESULT-0.2.10, or the A release's — the A release is the better reference because the port then also proves A under the old addressing); then on the C′ page every mutation must be red (the runner's own self-proof) before any counted run. Counted runners touched: product path (POINT_AT/DRAG/CARET_COLUMNS/INK_ROWS/LINE_INK, the `grew` check reads `#paper`'s height), page honesty (pointer + TEXT_LINES), locks/assets/host-entry (2 each). `check_m3_production_ui.py` has 0 canvas references, not 3.

## Part 3 — criteria (form; default if never done)

Release A (page v60, host 0.2.11):
- A1 per key, bytes passed to `putImageData` outside fresh band blits ≤ 2% of canvas bytes, both browsers, ratio 1 — per-instance over rows, read by the existing blit probe (no product-path change). Default: A not accepted, 0.2.10 stays.
- A2 §15.8 (a)(b) and the §15.6 on-screen cells re-bound on the new page, ratio 1, both browsers — tool-closed (the existing §15.8 reader). Predictions: Chrome commit 24–30/max < 40, on-screen 24–30; Firefox 36–45/max < 75, on-screen 30–40.
- A3 RECORDED, not gated, with predictions: ratio 2 narrow (Chrome 33–40; Firefox 58–70 if the small-blit bench says ≤ 1 ms, else 80–110) and ratio 2 wide (Chrome 45–55; Firefox 155–210, named limit). Default: the finding names ratio-2-wide Firefox as a limit of the A page.
- A4 the product-path net per M2-5, no reader touched; 121-B/120-B unchanged. Default: no freeze.

Release C′ (own spec section; criteria added under CLAUDE.md §9 — forced by the wide measurement, named, form 1/2, closed when C′'s count lands):
- C1 `#canvas.height ≤ 3 × desk.clientHeight × dpr` at every state read, and `#paper`'s CSS height = document height — per-instance; unit + one runtime read. Default: C′ not accepted.
- C2 ratio 2 wide becomes a criterion: §15.8 (a)(b), on-screen median < 70 Chrome / < 90 Firefox, max < 150, both browsers. Ratio 1 cells of A2 must still hold. Default: C′ not accepted.
- C3 replaces §15.6 (ii), per-instance: after the last key, every band intersecting the window is blitted with revision ≥ last within the probe's quiet window; every band outside carries revision < last or is absent (read from the page's band bookkeeping exposed on a dataset attribute, cross-checked by the probe's fresh-blit coverage of the window). Default: the first ruling's must-not ("no band stale once quiet") stands unrestated and C′ fails it by construction.
- C4 per-instance over fractions {0.5, 1.0}: after 20 keys at the top, scrolling to the fraction yields window bands with revision ≥ last within 500 ms. Default: C′ not accepted. (This is the only criterion that bites B's logic.)
- C5 the comparator reader: 0 cell differences on the whole-canvas reference; all mutations red on the C′ page. Default: the net is not trusted on the new page; no count.
- C6 062 ceiling: a 40-page document at ratio 2 wide opens drawn in both browsers (ink in the last strip). Default: named limit at 32/64 pages stays in the finding.
- Recorded with predictions, not gated: full window current after last key (< 300 ms both), old-pixel/blank frames during a 10,000-px fling, live `lastTiles` bytes (≤ 60 MB at ratio 2 wide), H9 census.

## Part 4 — red cases, computed now

- A1: the shipped page `18c8afbe` under the blit probe = 6.0 canvases/key = 600% ≫ 2% (r2-current-* rows) → FAIL. Mutation "paint() blits every strip" (revert) → FAIL.
- A2 reader: `v58-chrome-owner-gap80` (508.2/814.6) → FAIL (a)(b), as in the fourth ruling.
- A unit (page functions compiled as the B1 tests do): caret moves y1→y2; rows at y1 equal the band's pixels; drop the restore → red.
- C2 reader on existing reports: wide-base-chrome gap80 (425.7, max 516.9) → FAIL (a)(b); wide-skip-firefox gap80 (158.8, max 214.5) → FAIL (a)(b); dpr2-base-firefox gap80 (105.6, 171.2) → FAIL both; dpr2-skip-chrome gap80 (34.5) → PASS. Four reports, two verdicts, before the page exists.
- C4: mutation "never mark off-window bands stale" → scrolled window shows pre-typing pixels → red. C3: mutation "blit the window band at pass end only" → red.
- C5: feed the comparator the same report twice → 0; one cell flipped → 1; the unported net's run on the C′ page → red on geometry-addressed checks only (this run IS the §34.4 witness; file it).
- C6: a 40-page document at ratio 2 wide on the A page, both browsers → blank/throws (062 reproduced; if it does NOT, the ceiling claim is withdrawn and C6 with it).

## Part 5 — sequencing

1. Before A's Firefox predictions are written (no product byte): one bench row — a 64 × 64 `ImageData` into 1800 × 44,514, 1238 × 30,616, 900 × 22,257, Firefox, 12 single-blit tasks. Prediction: ≤ 1 ms (then A reaches ratio-2 narrow Firefox) or ≈ 22 ms (then Firefox HiDPI is C′'s alone and A3's Firefox rows move up). Either way A ships.
2. A: §15.16 appended (specification, A1–A4, predictions, A3 numbers) → implement → unit red cases → blit probe both browsers ratio 1 → A3 recorded → `make test-e2-c-static`, E1-C intact, `make e2-c-assets` → freeze v60 (never touch v59) → host 0.2.11 → re-pin, count chain, product-path net per M2-5. Handoff 0 / 0.
3. One positive control if any ratio ≥ 1.5 machine is reachable: the blit probe on the A page, maximized window, both browsers. Not a blocker; if it PASSES both browsers' cells, C′'s trigger is weakened and goes back to registration with that report named.
4. C′: own spec section first (amended design, C1–C6, predictions, the named limits, the H9 question registered — explained AFTER, with 040's never-idle build as the candidate explanation; the design assumes no rectangle ever) → the comparator reader and its red cases → the port, validated on the A page (0 differences) → the page → mutations red → C2–C6 → freeze v61 → host 0.2.12 → count. One §34.3 review only if the runner is more than half rewritten.
- Must not: ship A and C′ in one page release; make the canvas sticky; leave `lastTiles` unbounded; restate the ratio-1 numbers; port the readers to read the band cache instead of the window's pixels; count 因執行而修 per check instead of per runner.

## Wrong or missing in the brief

1. **Unmentioned cell**: `dpr2-{base,skip}-chrome-owner-gap{600,80}` all carry `allCurrentAfterLastKeyMs: None` while every Firefox ratio-2 report has a number and Chrome wide has 1133.8/739.2. Either the probe's coverage computation against `canvasHeight` (probe :185–202) or a band left stale at ratio 2 narrow in Chrome — the first ruling's must-not. Explain before ratio 2 becomes a criterion (C2 presupposes the instrument is right there).
2. Option A's Firefox-wide figure (≈ 159) assumes dirty-rect blits are free; the bench never measured a small source. Upper bound, say so.
3. C′ as written (sticky + redraw on scroll) has the one-frame async-scroll lag; the amendment in Part 1 removes it.
4. The ceiling has numbers (65,535 both browsers from 062, not "32,767"; 33 pages HiDPI wide, 65 at ratio 1) and is the product's strongest reason for C′.
5. `check_m3_production_ui.py`: 0 canvas references, not 3.
6. "Rewrites the eleven page functions": the band pipeline survives; the rewrite is the geometry mapping plus four listeners.
7. Memory gain is half unless the band cache is bounded.
8. R1 under C′ is moot; the brief asks "in or out" as if it were independent.

WHY（給擁有者）
1. 先做 A（只改 `paint()`：狀態更新不再整張重貼，只補游標和反白動過的那幾格）。Chrome 在每一種螢幕上都因此夠用；你的 1 倍螢幕兩個瀏覽器都已經過、再多餘裕。這是一次小改、量過上界的發佈。
2. 再做 C′ 當獨立案子：畫布只有視窗三倍高、放在一個跟文件一樣高的墊子裡，捲動照用瀏覽器原生的；看不到的條只標記過期、捲到才畫。它買到的是 Firefox 高解析度寬視窗（A 救不到）、記憶體（兩份 321 MB 變幾十 MB）、以及一個 brief 沒算出來的牆：高解析度最大化視窗下 33 頁以上的文件今天是空白（062 的 65,535 列上限）。機構的文件常超過 33 頁，這才是「划算」。
3. 不用 sticky：它每一格捲動都慢一幀。改成絕對定位、快到邊緣才搬一次。
4. 回歸網要跟著搬，但方法是：先在沒動的頁面上證明搬過的網判得一模一樣（0 格不同），再去判新頁面；算「因執行而修」每支 runner 1。
5. 兩件要先查的：Chrome 2 倍窄視窗三份報告「最後一鍵後整張換新」都是空值，README 沒提；Firefox 貼一小塊進大畫布到底是 0 ms 還是 22 ms，台架沒量過。

## Main session's check (2026-10-10)

Checked against the sources before adopting:

- **Holds**: 062's browser ceiling is 65,535 in both browsers (`findings/062-…md` :75–80: Chrome "65536 起底部像素畫不進去", Firefox "65536 起 NS_ERROR_FAILURE"); the four pointer listeners are on `el.canvas` at :1712, :2060, :2067, :2068; `.paper` is `position: relative` (html :86) and `#sink`/`#a11y-doc` are absolute inside it (:104–105, :164); the three Chrome ratio-2-narrow reports carry `allCurrentAfterLastKeyMs: None` (every other ratio-2 and wide report has a number) — I did not report it.
- **Wrong, 1**: "a 14-inch laptop at Windows' default 150% … ratio 2". Windows 150 % is devicePixelRatio **1.5**: backing 1350 px wide at the 900-px cap, between the measured narrow (1450 / 1238) and wide (1800) rows, nearer narrow; ≈ 1,517 rows per page, so the 65,535 ceiling is reached at ≈ 43 pages, not 33. Ratio 2 with a wide window is 200 % scaling (4K at 200 %, Retina-class panels).
- **Wrong, 2**: "`check_m3_production_ui.py` has 0 canvas references". It imports `POINT_AT` (:64) and uses it (:272); `POINT_AT` addresses the canvas by fraction of its bounding box. One use, not three — my grep's 3 counted a comment and the import.
- Both corrections were sent back to fable before anything is acted on.

## Fifth ruling, addendum (2026-10-10; fable's reply to the main session's two corrections). Verbatim.

Both corrections are right; neither changes the option, the sequencing, the §34 classification, or the criteria forms. What moves:

(1) Ratio 1.5 is the buyer's default, and it is unmeasured.
- "Not D": the reason stands but its sentence changes — the buyer's maximized 150% laptop is a 1350 × ≈ 33,400 canvas (≈ 180 MB), which sits between the two measured rows where the shipped page already fails §15.8(b) in both browsers (narrow: 152/208 MB → 106.7/105.6; wide: 321 MB → 425.7/208.1). That is interpolation, not a measurement, so it does not carry a criterion on its own; it carries the decision to measure it (below). Ratio 2 wide is 200%/Retina — real, less common; it remains the worst measured case.
- A3 gains a row, recorded not gated, both pages, both browsers: `--dpr 1.5 --window` wide enough for the 900-px cap. Predictions on the shipped page: Chrome commit median 150–250 → (b) FAIL; Firefox 120–160 → (b) FAIL, (a) borderline. On the A page: Chrome 35–45 PASS; Firefox 55–100, the split decided by Part 5 item 1's small-blit result (≤ 1 ms → 55–70 PASS; ≈ 22 ms → 80–100 FAIL). If the shipped page PASSES both browsers at ratio 1.5 wide, D's case strengthens for Firefox only; A still ships for Chrome's ratio-2 rows and the owner's margin.
- Part 5 item 3 (the positive control) is now this ratio-1.5 run, emulated first (same wrapper, `--dpr 1.5`), a real 150% machine if one is reachable. Do it with item 1, before A's predictions are written.
- C2 stays at ratio 2 wide as the criterion: the windowed canvas makes the destination size ratio-independent, and blit cost is monotone in destination size (H6), so the harder measured case covers 1.5. Ratio 1.5 wide is recorded under C′ with predictions (Chrome 35–50, Firefox 50–80).
- C6's page counts: 43 pages at ratio 1.5 wide (1,517 rows/page), 33 at ratio 2 wide, 65 at ratio 1. The red case stays at ratio 2 wide / 40 pages (already instrumented; 80,920 rows > 65,535); add the ratio-1.5 reading: a 50-page document (75,850 rows) blank on the A page, drawn on C′. The "划算" argument weakens from 33 to 43 pages on the default laptop and holds: regulations, reports and theses exceed 43 pages.

(2) `check_m3_production_ui.py` is touched through `run_e2_c_page_smoke.POINT_AT` (:64, :272). Good — that is where the shared addressing helper should live, so one port serves page smoke, production ui and (if its :175–180 copy is replaced by the import) page honesty. Counting: 因執行而修 1 for the helper's file, 0 bytes for importers; but note §34.5 — the importers' pins do not see the helper change, so each importing runner must appear in C5's 0-difference reproduction on the whole-canvas page, not only the product-path runner. Add production ui and page honesty to C5's list explicitly.

The Chrome ratio-2-narrow `None` cells: measurement first is the right order; whichever way it reads (probe coverage vs a stale band), C2's instrument must be shown to print a number on a passing Chrome ratio-2 run before C2 is a criterion — that condition in my ruling is unchanged.

## Main session's note on the `None` cells (2026-10-10)

Explained: not the probe. The shipped page never paints its 53-row last band in that configuration and toasts 「重繪失敗：TILE_NOT_PAINTED」 after every pass — registered as **finding 123** (`findings/123-…md`, evidence `findings/evidence/123/`).

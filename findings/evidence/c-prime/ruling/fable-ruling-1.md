# fable's ruling on brief-1 (2026-10-11, the owner asleep and having authorized fable to decide on their behalf: "授權 fable 代為裁決"). Verbatim.

RULING

Q1 — A, with the floor derived from the product, not from the fixtures. W = min(docRows, max(3·floor(desk.clientHeight·scale), 4·RENDER_BAND_HEIGHT)), scale = canvas.width / canvas CSS width. Derivation: 4 is the smallest band multiple that holds one whole A4 page at the width cap (MAX_BACKING_WIDTH 2400 × 1.374 rows/px = 3,297 rows; 3 bands = 3,069 < 3,297 ≤ 4,092). "Short fixtures still fit" is a consequence to record once (CLAUDE.md §1 form 3), never the reason. C1 is amended to equality with that formula (append-only, §10; no run has counted against C1, so §9 permits it). Not B: it builds stitching machinery to preserve a bound that was itself a derivation (§4); the bound's three purposes (< 65,535 rows, memory, blit-destination size) all survive the floor. Not C: 060. Note the floor is the common case, not a corner: it binds in every harness window and at 1400×1000 in both ratios (3×540×2 = 3,240 < 4,092); "3×view" binds only on desks > 1,364 CSS px at dpr 1 / > 682 at dpr 2. N4 predictions must therefore use W = 4,092 for the 1400×1000 configurations (canvas 29.5 MB at 1800 wide, lastTiles ≤ 5 bands ≈ 37 MB; C2's destination shrinks 10.9×, not 8×).

Q2 — A. B's "latest = max(three sources)" is a hand enumeration of where the engine advances the revision — I count eight sites (probe_engine.cpp :1603, :2718, :2774, :2816, :3210, :3448, :3688, :4087), every one AFTER the LOK callbacks of the same command — and B's actual safety comes from its "always re-request the window" clause, which A has intrinsically. A is per-instance: any `document-invalidated` or completed `run()` invalidates. Known cost: `document-invalidated` is LOK id 0 or 1 (sdk-worker.js:1109–1113), so caret-only moves also advance the counter and make off-window bands stale; bounded by today's behaviour (every arrow key already re-renders every band, e2-editor-app.js:916–918) and measured by C4. Conditions: dataset exposes counter + per-band labels; C3/C4 "last" = counter value at quiet; C4 gains Backspace and set-bold arms; red cases "never mark off-window stale" and "label at reply instead of at request".

Q3 — A; it keeps faith. The owner's condition was "runners and HTML unchanged"; the spec's literal (hide + sibling) broke it, the child does not: READ_STATE (page_smoke :32–47) and production_ui :118 read `dataset.state`; `real_click` (check_m3_locks.py:101–108) clicks the CENTER of `#state-pill`'s box, which is the child's box, and the parent has no handler; INVENTORY admits via `closest('#state-pill')` (:167). One honest change: `#state-pill.textContent` becomes the shown (delayed) label, so READ_STATE's `label` field changes meaning — no logic reads it (grep), but §17.2's "文字…立即更新" sentence must be amended (optionally stamp the immediate label as `data-label`). "Never blank" resolves S4; the direct writes at :2262 and :2423 go through the same function and cancel the timer. 125-B reworded as the brief states.

Q4 — adopt the lean. Collabora's exclusion is `_selectionType === 'complex'` (CanvasTileLayer.js:3022–3024): table-cell/graphic selections this editor has no analogue for; the active pointer drag (`drag.active`, :1720) is the right analogue, and `endDrag` clears it before the final `pumpDrag`, so the release update follows normally (the caret is under the pointer, inside the view, so no scroll). Register a named limit: no drag-autoscroll (a drag cannot extend a selection past the desk edge). Record, not gate.

Q5 — adopt. Under Q1-A and Q3-A, 124 and 125 no longer disturb the unported net on short fixtures (POINT_AT dispatches directly on `#canvas`; INK_ROWS/TEXT_LINES `getImageData` the whole canvas = whole document), so S6's premise mostly dissolves; the order still stands because a witness must be attributable to one cause, and it costs nothing. Re-derive and write the witness's predicted red set (long-document cells, production UI's owner-document positions) before the run.

"Also adopted" list — no objection. N3 made explicit: on the C′ page a blank 40/50-page document = C′ not accepted; my fifth ruling's default "named limit at 32/64 pages stays" is superseded by 126 (a whole-document blank is not a limit; it is the failure of C′'s strongest reason). S5's surviving mutation is registered under §3 as "有行為而沒有東西守著".

WHY（給擁有者）
1. 畫布最少四條（約 4,092 列）：這個數在每個測試視窗、連 1400×1000 都在作用，不是角落案例；它守得住 C′ 要買的三件事（65,535 上限、記憶體、Firefox 貼圖成本），短文件照舊整份在一張畫布上，回歸網幾乎不用搬。
2. 「哪一條過期」改用頁面自己數的變更號，不用引擎的修訂號：引擎在八個地方才把號碼往前走，而且都在畫面失效通知之後；靠它會讓 Backspace／粗體之後的舊畫面留在螢幕上，而所有檢查都綠。
3. 「處理中」延後顯示的膠囊放在原本膠囊裡面當子元素：runner 一個位元組不改、HTML 不改，你選 A 的原意保住。
4. 游標跟隨：鍵盤（含 Shift 選取）都跟，滑鼠按住拖曳時不跟。
5. 先只用 C′ 那個 commit 跑見證，再把 124、125 放進來。

FACT CHECK
- F-a holds: JSON 1800×98,869 / 1350×92,682, dark 0/0 both browsers; Chrome `state: ready`, no toast; Firefox 「重繪失敗…Canvas exceeds max size」; controls 59,338/61,181 drawn.
- F-b: Chrome holds (run_browser_probe.py:214–223, `--headless=new`, no size; desk 325.4–464 = 138.6 px). One page 725×1012 / 900×1256 holds (release-0.2.11/product-path r1 `geometry`). "Firefox 1366×768" is Firefox's built-in default — the launcher passes only `-headless` (:117); not in any file I read; immaterial, since the floor must cover the smaller Chrome desk anyway.
- F-c holds; `real_click` lives in check_m3_locks.py:101, not run_browser_probe.
- F-d holds: verdict124B false from press 14/11 ("not wholly inside"), verdict125B false ("no #state-shown"), machinePillBusy 85.
- Brief inaccuracies: "advance it only in the UNO result handler" — eight sites, all post-callback (the point stands); "≤ 29 MB" is 29.5 MB; Q1-A's "short fixtures keep canvas = document" is a form-3 consequence, not a derivation; the 3,727-row figure is scaled, not measured.
- Also verified: today's page uses no revision for staleness at all; the tile reply carries `gState.revision` (:3157), stored at document-sdk.js:408.

CONDITIONS
1. §17 amended append-only before any implementation: C1′ formula and derivation; the Q2 counter with C3/C4 wording and the two new C4 arms; the 125 child design and the textContent sentence; 124's drag exclusion and named limit; the Q5 order; N1–N5; predictions recomputed with W = 4,092 at 1400×1000.
2. C1 unit enumerates (desk, scale) pairs including the 139-px desk and a 4K/200% desk; red cases: drop the floor → 139 px yields 417; drop the 3× term → the large desk yields 4,092.
3. Q2 red cases run before any count: "never mark off-window stale" (C4) and "label at reply, not at request" (a band in flight across a change stays fresh) → red.
4. Q3: 125-U as written plus "parent keeps class pill" → red; runners' zero-byte claim proven by C5(i) with production UI and page honesty in the 0-difference set.
5. The witness report names the C′-only page commit and the pre-port runner commit; its predicted red set is committed before it runs.
6. Nothing executes tonight: no product byte, no run, no freeze; the owner reads this first.

## Main session's check (2026-10-11)

- Recomputed: 2400 × 1.374 = 3,297.6; 3 × 1023 = 3,069; 4 × 1023 = 4,092; 4,092 / 3 = 1,364; 3 × 540 × 2 = 3,240; 4,092 × 1,800 × 4 = 29.46 MB; 5 × 1,023 × 1,800 × 4 = 36.8 MB; 44,514 / 4,092 = 10.88. All as stated.
- Revision sites: `grep -n "advanceRevision()" src/probe_engine.cpp` gives calls at :1603, :2173, :2718, :2774, :2816, :3448, :3688, :4087, plus the inline `++gState.revision` at :3210 (`handleInsertText`) — nine sites, not eight; the ruling's list has :3210 in place of :2173. The point (every advance follows the command's LOK callbacks) is unaffected; Q2-A does not depend on the count.
- `real_click` at `tools/check_m3_locks.py:101–108` clicks the centre of the selector's box (`CENTER`), as stated. `drag` is declared at `web/e2-editor-app.js:1720`.
- Condition 6 is followed: after this ruling, no product byte, no run, no freeze until the owner has read it. The C2 reader, the C5 comparator and the 124/125 probe extension were written and their red cases run BEFORE the ruling arrived (commits `17b4ab2a`, `cb680d6a`, `f0291565`); none is a product byte or a counted run.

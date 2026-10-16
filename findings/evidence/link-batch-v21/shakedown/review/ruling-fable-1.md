# Ruling 1 (v21 shakedown), fable, 2026-10-17 ~05:20

Request: `brief-fable-1.md` (commit `da4666ee`). The owner authorised fable to decide on their behalf (2026-10-17 ~03:00, 「我要去睡了，請你自主執行／有疑義的地方可以發給fable，我授權它代我決策」). Fable worked read-only. Verbatim below, as returned to the main session.

---

**Ruling 1 (v21 shakedown), fable, 2026-10-17 ~05:20, read-only.** Everything below was checked against the files; nothing in the brief was taken on trust.

## Q1 — finding 150 (move key during an in-flight delete takes the range path)

**RULING: A.** Apply fix 2 (`deletesInFlight === 0 &&`) to both decisions — the arrows' path and `sendDocumentMove` — before the v74 freeze. Not a timing rule; it is finding 131's rule A applied where it was missing.

**WHY（給擁有者）**：頁面在判斷「游標是不是在範圍上」時，把刪除 barrier 自己推出來的一字選取當成使用者選的，於是先點一下再移動，中間按的 Delete 就刪在點擊處。這條「刪除在途時，引擎的範圍不是使用者的」規則，頁面已經在三個地方用了，只有這兩個移動的判斷漏掉。方向鍵那一半是 0.2.24 就有的，兩個瀏覽器各 3/3 量到會刪錯字；Ctrl+End 只是重用同一條路。補上之後 V6e 與 D8 (e) 都回到按鍵順序，真的範圍（拖選後按方向鍵）仍照舊先點再移。

**FACT CHECK**: F1–F4 confirmed in `web/e2-editor-app.js` (:105 `deletesInFlight`, :1766, :2787-2789, :3192-3197, :3330-3333) and `dist/e2-editor-app.js:2975-2977` (0.2.24, same condition); V6e/D8E/range-control numbers match the reports. Stronger than F3: on 0.2.24 the *second Backspace* also ran after the click. F5 agreed: D8's default remedies the hold rewrite (§10.3), not this cause, so taking it would not turn (e) green.

**CONDITIONS**
1. One shared pure predicate for both paths (shape, gestures, `pointMovesInFlight`, `deletesInFlight`), so they cannot drift again; red-first node test over the fake engine (`page-held-after-move.test.mjs` style): barrier range + delete out → no place-caret; real range, no delete → place-caret then move; collapsed → direct. Keep the red output as the witness.
2. Evidence run (N=3, both browsers): D8 (a)–(e) on the final shell; re-run `page-held-deletes`, `page-held-depth`, `page-delete-and-sink`, `page-held-after-move` on the final bytes (D8's own clause).
3. V6e (arrows) is run once more on the final shell with the diag tool, N=3 both browsers, as a **record** arm — no new gate criterion (it is outside item 1's scope).
4. Spec §12.3 (append-only): D8 (e)'s cause and the fix, stating no threshold moved and that D8's default does not address it.
5. Finding 150: ruling = A; 影響版本 must list 0.2.24 (arrows, 3/3 both browsers); release note for 0.2.24.

## Q2 — finding 151 (typing after a dirty Ctrl+Home/End lands at the old caret)

**RULING: A.** Fix 1 (22/23 take no checkpoint). D11's dirty-checkpoint clause is withdrawn for 22/23 under CLAUDE.md §4. A′ (the six arrows) is deferred to the ordered-commands batch with the §34 process; the arrows' instance is registered now under 151 as affecting 0.2.24.

**WHY（給擁有者）**：檢查點是為 finding 096「按下的鍵在邊界上永遠等不到回呼」設的，但這顆引擎的 Ctrl+Home／End 最多 251 ms 就以讀回完成（D7），不會卡死，前提已經不成立。代價卻是實測每次都中：改了內容再按 Ctrl+End 接著打字，18/18 落在舊游標。拿掉 22／23 的檢查點後 18/18 正確，而且不是「等一下再送」那種時間補丁，是刪掉一個前提已假的機制。方向鍵那一半（第一下方向鍵接著打字，0.2.24 就有，6/6）同樣成立，但它被一支計數中的檢查釘著，改它要走 §34，今晚不動，先登錄。根治仍是「有序指令」那一批。

**FACT CHECK**: F6, F7 (V1/V2/V4 18/18; V7 X≈0 stale 6/6, ≥300 ms fine 10/10), F9 (18/18; D11b dirty 0 saves) confirmed. F8: the number the brief lacked is now in the README third round — **0.2.24's `Q` lands at the pre-arrow caret 6/6** (`report-*-third-*`). Two things the brief does not say: (a) the wedge premise is equally false for the six arrows on this engine (the product-path check's own comment: "on e2-editor-v14 the press is answered"), so the 22/23-vs-arrows line is drawn by *what pins them*, not by the engine; (b) fix 1 as measured changes the `if` line that the counted mutation `boundary-move-takes-no-checkpoint` targets by exact text, and `apply_mutation` (`run_e2_c_product_path.py:2717-2722`) exits when hits ≠ 1 — so fix 1 touches that check's table either way. F10 (fix 1′ 18/18, boundary control no wedge) and F11 confirmed; the 10–300 ms window after a save is unmeasured.

**CONDITIONS**
1. `BOUNDARY_CAPABLE_MOVES` stays eight (D13). The checkpoint predicate becomes a second named set of the six arrows, with a comment giving the reason (D7's ≤251 ms readback; V1/V2/V4 18/18; the arrows kept only because a counted check pins them).
2. Red-first: the session test "finding 096: all eight key-path moves bank it" (`narrow-editor-v2-session.test.mjs:616`) goes red first; rewrite to six bank / 22-23 do not / the other nine do not; add "dirty + Ctrl+End → no save, `dirty` true, no checkpoint".
3. Produce the `apply_mutation` "tree moved under the mutation" exit as the witness, then update that mutation's `find`/`replace` to the new lines; the check's expectation is unchanged and must still go red. Tally in the handoff: modified because of execution 1, because of review 0.
4. Spec §12.3 (§4 withdrawal, append-only, names what it replaces): D11 dirty for 22/23 = no `save` before the move, `dirty` stays true, `#s-checkpoint` 「無」; arrows unchanged; default stays 「第 1 項不出貨」; "if never done" = item 1 does not ship.
5. New criterion **D14** under §9's four conditions (forced by finding 151; form 1; before any evidence run; closes with the item-1 evidence run): dirty plain3 and long60, Ctrl+End, a typed character ≤30 ms later lands at the document end; N=3 both browsers; default 「第 1 項不出貨」. The count is not reset (no evidence run exists yet).
6. §9.1's L-142-readback-overtaken wording is corrected by append: not a rare stall — after any save it happens every time (V7, V1); the class stays.
7. Finding 151: ruling = A; residual registered: (a) a save <300 ms before Ctrl+Home/End (autosave, Ctrl+S); (b) the arrows' instance, 0.2.24 and v21, release note; root fix = ordered commands (relink).

## Q3 — finding 152 (Chrome loses typing after the Markdown dialog)

**RULING: C** (register; no page change in v21). Because Q4 removes the entry, the dialog is unreachable in v21; fix 3 ships with item 2 in the next batch, its criterion written now.

**WHY（給擁有者）**：fix 3 的數字很好（headless 6/6、headed 1/1、Firefox 1/1），但第 2 項這批不出貨，對話框在 v21 根本開不到，改了也量不到好處。而 `sink.blur()` 對頁面其他 blur 相關路徑的副作用沒有量過，不該帶一個沒人能量的改動進要凍結的殼層。它跟著第 2 項一起出，到時候由你親手在真的 Chrome 打一次字當最後一關。

**FACT CHECK**: F12 confirmed (V5 9/9, V11c/d 3/3, headed 3/3; `closeMarkdownDialog` :2337-2344). F13's missing numbers are now in the README third round: fix3 headless V5 3/3 + V11c 3/3, headed Chrome 1/1, Firefox 1/1, fix3b not needed. F14 confirmed (CDP keys; locked screen). Not audited: sink `blur` listeners.

**CONDITIONS**
1. Finding 152 written with fix 3 as the candidate and these numbers; 影響版本: v21 candidate only (0.2.24 has no `<dialog>`, V11f).
2. Criteria for the batch that ships item 2, written now: V5 (0 / 300 ms) and V11c/V11d N=3 both browsers; plus the owner's hand test in a real Chrome (type after 插入 and after 取消). "If never done" = no entry.

## Q4 — finding 153 (one long paragraph overflows the 64 KiB engine-thread stack)

**RULING: A.** Item 2 does not ship in v21: no page entry, L-md-sdk-callable, SDK still callable. M3 is red on the linked engine and its pinned default applies; the fix is a relink and belongs to the next batch with its own criteria. v21 ships item 1 only.

**WHY（給擁有者）**：一段 43,520 位元組以上的中文（約十頁）一貼就讓引擎的執行緒把 64 KiB 的堆疊撐爆，三種死法都量到了，兩個瀏覽器一樣；只把 loader 的預設堆疊改成 1 MiB 就 6/6 正常，所以原因確定。這要重新連結，是你的步驟，也是新的引擎身分，今晚不可能做。M3 釘死的「引擎直接送 65,536 要完成」這一臂是紅的，預設就是第 2 項不出貨；把 SDK 上限降到 16 KiB 救不了這一臂，那是事後搬門檻。0.2.24 的引擎其實也會死，只是 Ctrl+V 的 16 KiB 上限擋住了使用者；第 1 項不改變這件事。

**FACT CHECK**: F15 confirmed (`Makefile:847` 65536, `:849` ASSERTIONS=0, `probe_engine.cpp:6956` `std::thread`); the sw recursion I did not open — the counterfactual (F17, 6/6) makes the cause sufficient regardless. F16 nit: 43,520 is hang / ok-then-crash; the `memory access out of bounds` crash starts at 49,152. F18 confirmed (`input-adapter.js:338-345`; 0.2.24 raw `insertText` hangs). F19 confirmed verbatim in §11.2 M3 and §11.0. Two gaps the brief does not mention: (a) the diag tool's `open` route (a document that already holds such a paragraph) was added but **never run** — if it crashes on load, 0.2.24 reaches it by opening a file; (b) the page entry is manifest-driven (`updatePasteMarkdownAffordance`, `offersPasteMarkdown` ← `contract.pasteMarkdown`), and the v21 manifest declares it, so "no entry" is a shell edit with a test, not a profile fact.

**CONDITIONS**
1. Entry removed on the shell (toolbar button and any route to `openMarkdownDialog`), with a red-first test in `page-markdown-dialog.test.mjs`: profile offers it, shell shows no entry; SDK callable. Spec §12.3: M8's page cell on the final shell reads "hidden by the shell", v20 pairing rule unchanged; I1's declaration diff lists `pasteMarkdown` under L-md-sdk-callable.
2. M7 (Ctrl+V 照舊; default 「v21 不出貨」) runs in the evidence, N=3 both browsers, on the final shell. M1–M6, M9–M11 are not run; their defaults are already taken.
3. Finding 153 written (cause, threshold 43,008/43,520, counterfactual, 0.2.24 reachability bounded by 16 KiB, native 6/6) with the **next batch's criteria pinned now**: the four failing inputs paste OK N=3 both browsers; the stack size chosen with a reason and its memory cost measured (pool 7 × stack); a decision on an overflow check; the `open` route.
4. Tonight, record only: run the `open` cell (Chrome, fresh browser, N=3) if the lock is free; it decides 153's 0.2.24 severity and the release note.
5. Release note and finding 153: a host calling `pasteMarkdown`/`insertText` directly with such a paragraph crashes the engine on both versions.

## Overall

**v21 ships item 1 only** (fix 1 + fix 2 in the tree, item 2's entry off, engine `e2-editor-v21` unchanged). Tonight, in this order: (1) spec §12.3 appends (D11 rewrite, D14, D8 (e) note, §9.1 frequency correction, M8 reading) — before any tree edit or run; (2) findings 150/151 rulings, 152/153 new; (3) tree edits with red-first tests (fix 2 shared predicate, fix 1 six-move set, entry off), full node suite; (4) the mutation `find` witness and update (§34.4, tally 1/0); (5) build the candidate page, record its identity; (6) item-1 evidence runs N=3 Chrome then Firefox under the lock with D14 and M7, plus the V6e and `open` record cells; (7) handoff for the owner: freeze v74 if all green, host 0.2.25, count chain K, and the v22 relink plan (stack size) carrying item 2 and fix 3.

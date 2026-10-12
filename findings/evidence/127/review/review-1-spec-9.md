# Review 1 — SPEC-M3-autosave §9 (the freeze draft), adversarial, read-only

Reviewer: fable (Claude Fable 5.1), 2026-10-12. Brief: `brief-1-spec-9.md`. Nothing was run; every claim below is read from the files cited (line numbers are of the tree as of this session) or from the evidence READMEs. Tags: BLOCKING = the spec must change before freezing; SHOULD = fix in the same freeze; NOTE = register.

## SUMMARY

1. BLOCKING — Premise "no counted runner saves again after a copy" is false. `check_m3_host_entry.py` arm `conflict` saves twice after the intruder and expects every attempt `[(412, True)]`, statuses `[412, 412]` and two copies (`h3`, lines 440–460; driven at 304–335; counted 3/3 per browser in `build/m3-count-2026-10-11b/chain.txt`; consumed by install_elsewhere I3-13). Under O1 = B the second save lands in the copy (204, no `If`, one copy). Change: §9.4 計數 pre-registers (append, reason "O1 = B replaces the 0.2.12 expectation") the arm's new expectation — save 1 `[(412,True)]` → copy; save 2 one PUT to the copy, 204, no `If`; 1 copy = save 2's bytes; original = intruder — and names the first 0.2.13 run as its §34.4 witness. Also state that the page's `documentName` / `#s-doc` is NOT renamed by B-3: `h3` line 452 and locks K6 line 944 read it and expect the original name.
2. BLOCKING — Counted arms whose edit is followed by a long wait will record an autosave. Locks K8 `frozen` (edit → freeze 320 s → thaw → save, lines 606–622): the overdue 30 s one-shot fires at thaw (and the hidden trigger at freeze if the CDP freeze hides the page first) → `len(saves) != 1` (line 963) red by construction. K7 `expired` (edit → phase wait ≤ 25 s → save, 595–605): worst-case gap ≈ 29.5 s against 30 s, a tail race. Change: §9.4 計數 pre-registers K8's new expectation (the manual save is the last record; earlier `trigger:"auto"` records allowed; the refresh-window clause unchanged) with the first run as witness, and names K7's margin as a known race, not "unchanged".
3. BLOCKING — 128 fix A as written ("`run()` 在途時…只標記", §3.6) also defers typing's `document-invalidated` during `run("存回")` (the host GET/PUT, `e2-editor-app.js:1913`; the engine is free and typing proceeds) → typed text stays invisible until the server answers (78–105 ms on ddev, longer on a real server) on every manual and auto save — 128's class, exactly where users type (M1). Change: §9.1 — defer only while the session reports an engine operation in flight (`state.snapshot.pending > 0`), never on `run()` alone.
4. BLOCKING — No AS-4 cell has a live lock token: (a)/(b) use K6/M3 (token dead, `loseLock`), AS-3(b) uses K5 (no token). A PUT to the copy that still carries `If: (<token>)` is a 412 (Sabre `Locks/Plugin.php:454–497` leaves an unknown token invalid; the host's own K7 path documents the 412, `litecore-editor.js:502–505`) → one more copy per save: the M3 defect again, in the commonest real conflict (a version restored in Files, K12/versions shape). Change: add AS-4(c): K12 (`unlock-refused`) shape, then a second save: 1 copy holding the second edit; the original's lock held, token unchanged (this also pins the B-2 withdrawal); Chrome wire: the PUT to the copy carries `If-Match` = the copy's version and no `If`.
5. SHOULD — AS-1's conditions "開檔時鎖被拒而且沒有副本目標" and "沒有擱淺" are host facts the page cannot see through `{load, save, watchUnsaved}` (`litecore-editor.js:378–435`). Change: `load()` returns `lockRefused`; every thrown save error carries `outcome` (`copy`|`stranded`) and `savedAs`; success returns `{ name, target }`; the page keeps `copyTarget`/`stranded` from these, and a manual save whose outcome is `copy` ends a pause.
6. SHOULD — AS-1 broken-but-green: `conditions` read from the page's DOM mirrors (`el.sink.dataset.composing`, :2190–2194) rather than the sources the decision must use (`session.input.state.composing` / `queueDepth`, adapter :85/:90). Change: one sentence — conditions are read from session/adapter state, the same values the decision uses.
7. SHOULD — B-5 (no autosave before the first manual save when the lock was refused at open) re-opens the 127 window for the user most exposed (own second window, or someone else's lock) and is the main session's addition, not O1. Change: withdraw B-5 (AS-3(b): idle → auto writes exactly 1 copy and switches target; idle again → still 1), or add L-locked-open to §9.7 and have the owner read it.
8. SHOULD — The pause after *stranded* keeps the rescue bytes stale: `strand()` (:321–325) holds the first failure's bytes; later edits exist only in the tab; 「下載這份內容」 hands over old content with nothing saying so. The §8.1 reason for pausing (copies multiplying) is gone under B-1. Change: either do not pause on stranded (each idle re-strands fresher bytes) or state the new reason and make the stranded notice carry the time of the bytes it holds.
9. SHOULD — "活動" never includes a mutation that arrives without a sink keydown or a paper pointer (toolbar formats, `paste`/`cut`, the `#text` insert every runner uses): such edits never arm the 30 s clock; the user waits for the 5-min cap. Change: a completed mutation (`dirty` false → true) also arms the clock.
10. SHOULD — AS-5 does not say when the server is read; the 20 characters typed during the save are not in that save's bytes (taken before). Change: read after the next auto (idle 30 s again) or one manual save; same for the held-key arm's 收到數.
11. SHOULD — AS-7 has no resumption cell (a pause that never ends is green); AS-2c has no reset cell (a cap that stays at 3 s is green). Change: AS-7 tail — re-grant the share (`set_share(…, 3)` exists), manual save → saved, edit, idle → one auto record; AS-2c tail — after the [3, 6] s save, one key, 10 s quiet → no auto record.
12. SHOULD — 129: after the collapse click, `lastSelectionShape` (set only in the paper pointerdown, :2109) stays `range-*` and the toolbar's gesture affordance is stale (:818–827). Change: 129-B adds "`#toolbar[data-selection-shape]` is `collapsed` after the key".
13. SHOULD — §9.5 row 1 "拿掉唯讀檢查 → AS-3(a) 紅" is not red: a view-only session is never dirty (`_enqueue` refuses mutations, `narrow-editor-v2-session.js:636–641`) and `saveDocument` refuses anyway (:1871–1874). Change: say AS-3(a) has no single-mutation red case (it is a regression cell for the existing guard); keep the judge's red case.
14. SHOULD — 128 fix A must also repaint on `run()`'s failure path (:1715–1735 never calls `renderDocument`): an invalidation deferred during an action that then throws (the "dispatched, unverified" format path) is never painted. Change: one sentence in §9.1.
15. SHOULD — B-1: `saveCopy`'s PUT must set `lastAnswered` (only `put()` does, :486), or the first write into the copy can land within 1.1 s of its creation (103/104 on the copy).
16. NOTE — B-2's withdrawal is no regression, but under B the lock on a file the session will never write again blocks others until leaving: list it in §9.8 as a work item rather than drop it silently.
17. NOTE — AS-2h cannot help on close/navigate (the engine segment outlasts unload; no fetch goes out): say so in the release note; L-discard's wording is right.
18. NOTE — O2: the label must be absent before the first write and live in its own element (production_ui P reads the inventory at open, :523, and asserts `#litecore-host-title` == file name, :691; text outside `TEXT_PLACES` is badText); name the host field for 完成時間 (`attempts[-1].respondedAt`; there is no `settledAt`).
19. NOTE — An auto-copy surfaces as toast `存回：CONFLICT：…` and latency `存回 失敗` with no user action — 129's class of developer text, pre-existing for manual saves; register, do not fix here.
20. NOTE — L-129 wording: the trigger is "the point displayed at a line's end", not CJK as such; the stated objection to the endpoint rule ("needs the drag direction") is wrong (a backward selection's cursor equals START exactly, measured); the real reasons to defer are evidence coverage (3 wrap shapes, forward only) and CLAUDE.md §4. The decision stands.
21. NOTE — The `#notice` sentence 「自動儲存已暫停」 is reachable only on engine failure (no inducer; the session's recovery notice already speaks there): candidate for withdrawal. The 3 s re-check loop should stop once the session can no longer become ready.

No defect found: AS-2 (foreground idle; "開始時間" = host record `at`, after the engine segment, consistent with §9.6), AS-6(a)/(b), 128-B's measurement, 129-B's < 400 ms bound (if the inferred empty-`TEXT_SELECTION` acknowledgement is wrong the cell is red on the product, which is the right outcome), 130-U, O2-1 (a)–(e) beyond note 18.
Premises: §9.1 true; §9.2 true; K5/K6/K10′ true as described; §9.3 B-3 first half true (the thrown error must keep the code and 「name」 in its message: `run()` :1722/:1729, `describeError` :195–199), second half FALSE (item 1).

---

## A. Premises, one by one

| Premise (as stated in the brief) | Verdict | Where |
|---|---|---|
| §9.1: K12, same_second, versions require the lock held with the same token after a conflict copy | **true** | `check_m3_locks.py:911–913` (`unlock-refused`: host `lock.state == "held"` and server token == the one at open, after `one_copy` + `page_failed_with`); `check_m3_same_second.py:263–267` (`score_foreign`, after S2 → `changed` → copy); `check_m3_versions.py:265–267` (after the third save → 412 → copy) |
| §9.1: 0.2.12 holds the lock until leaving after a copy | **true, with one caveat** | `saveOnce` (`litecore-editor.js:494–555`) never releases; the only lock loss on the save path is the dead-token retry (`loseLock('save', 412)`, :512–516), which is K6's case — there the lock is already lost before the copy, so "照舊持有" is moot for AS-4(a) |
| §9.1: B-2 was the main session's addition, not the owner's B | **true** | §8.2 lists B-1…B-6 as 「主 session 依此擬的設計草稿」; the owner's words are 「01: B」 |
| §9.3 B-3: keeping the first copy's outcome as a thrown `CONFLICT`/`HOST_SAVE_FAILED` leaves `page_failed_with(..., "CONFLICT", copy_name)` unchanged | **true, conditional** | `page_failed_with` (`check_m3_locks.py:799–803`) needs latency `存回 失敗` and the toast to contain every needle. `run()` sets the latency on any throw (:1722) and the toast is `${label}：${code}：${message}` (:1729 via `describeError` :195–199). The condition: the host's message must still contain 「{copy name}」 after B-3's rewording, and the code must stay `CONFLICT` for 412/423/changed and `HOST_SAVE_FAILED` for the rest (K9′ `readonly` matches only the copy name, :980; K10′ matches 「下載這份內容」, :993) |
| §9.3 B-3: no counted runner performs a second save after a conflict copy | **FALSE** | `check_m3_host_entry.py` arm `conflict`: intruder PUT with the page's own token (:304–313), save 1, `time.sleep(5)`, `afterWait`, save 2 (:327–335). Scorer `h3`: every save `[(412, True)]` with `tokenOnServer is True` (:440–444), both pages `存回 失敗` + `CONFLICT` (:447–450), `afterWait.doc == NAME` (:452), `[412, 412]` (:454), two copies whose hashes are the two saves' (:458–460). Counted: `chain.txt` 2026-10-11 18:06–18:12Z `HOST_ENTRY LANDS chrome:conflict=3/3 … firefox:conflict=3/3`. install_elsewhere's I3-13 (`check_m3_install_elsewhere.py:2001–2006`) consumes this arm |
| §9.2: the host's GET/PUT does not hold the session queue | **true** | `saveOnce` (page :1899–1915): `take()` = `run("儲存", () => session.save())` is the only session-queued part; `HOST.save` is `fetch` (host :453–492). M2 measured the host segment at 78–105 ms with no spacing wait (`findings/evidence/127/m2/README.md`). Note the 128 consequence in item 3: `run("存回")` is nonetheless a `run()` |
| K5 / K6 / K10′ as described | **true** | K5 `foreign-lock`: other user's LOCK first (:502–504), host 423 → `refused` (:917–930). K6 `broken-then-written`: owner unlock + intruder PUT, save → `[(412,True),(412,False)]` → 衝突副本 (:581–594, :931–945). K10′ `nowhere`: writable at open (`SHARE_OF`, :505–510), share cut to 1 (`revoke`, :632), save → `[(403,True)]`, copy status 403 `failed`, STRANDED bar, download, two guarded leaves (:630–659, :984–1016) |

Additional premise checked because §9.4's 計數 line depends on it — "every counted arm's edit → next expected save/leave gap is under 30 s": **false for K8, marginal for K7**, see §C.1 below for the census.

## B. The criteria of §9.4, one by one

### AS-1 (per-record conditions)
- Broken but green (6): the page records `conditions` from its own DOM mirrors. `el.sink.dataset.composing` is written by the page's own `compositionstart/end` listeners (:2190–2194); the adapter's `_composing` (adapter :57, :150, :170) is what gates commits. The two are set by different listeners on the same events and can disagree for a tick (finding 050's neighbourhood, where ordering already bit once). A record saying `composing: false` while the adapter is composing is green. Fix: read from `session.input.state` (adapter :82–93 publishes `composing`, `queueDepth`, `blocked`).
- Broken but green (5): two conditions are not knowable by the page at all. "開檔時鎖被拒" lives in the host's `out.lock.state` (:208–231); "有副本目標" and "擱淺" live in the host's `stranded`/record (:102, :321–336). The page's view of the host is `load()`'s `{bytes, name, readOnly}` (:398), `save()`'s resolve/throw, and the thrown error's `code`+`message`. An implementation that hard-codes `lockRefused: false, copyTarget: null, stranded: false` because it has no source is green on every AS run except AS-3(b)/AS-7, where the *other* clauses carry the verdict. The spec must give the page a source (item 5) or move those two conditions into the host (`save(bytes, {trigger:'auto'})` refusing with a distinct, unrecorded outcome — more machinery; the data route is smaller).
- Check-then-act gap: conditions hold "開始那一刻"; `saveDocument` then queues behind `hostSaves` and `take()` queues behind `_holdBehindTyped` (:653–656), so the engine segment can start after the user has resumed typing or composing. AS-1 is green; the user meets a busy engine with a composition in progress. Not data loss at typing speed (M1b), and inherent to any check-then-act; register, no change.
- Form check: the `0 records → NOT_ESTABLISHED` clause is right.

### AS-2 (foreground idle)
- No defect found in the cell. Note the timestamp: "第一筆 auto 紀錄的開始時間" is the host record's `at` (`save()` entry, :412), i.e. after the engine segment; §9.6's 30.6–31.5 s agrees. The runner should also keep the page's decision time (`decidedAt` in the record) so a slow engine segment on a big document is not misread as a late trigger.
- Not covered by AS-2: that composition events and paper pointer events reset the clock (§9.2's definition). A keydown-only implementation is green. Low harm (the conditions still refuse during composition/drag, then retry at 3 s), so not raised beyond this line.
- Item 9 is the real gap in the definition: an edit without a sink keydown or paper pointer never arms the clock. `POINT_AT` dispatches real `PointerEvent`s on `#canvas` that bubble to `#paper` (`run_e2_c_product_path.py:1140–1148`; handler :2098), so runner edits do arm it today — which is why §C.1's census matters.

### AS-2h (hidden)
- Broken but green: an implementation that saves on `hidden` without the conditions. AS-1 would catch a record with a false clause only if the run happened to be in that state; AS-2h itself never is. Covered adequately by AS-1's form, provided item 6 is applied (the conditions are read from real sources).
- Unload sequence (brief item 3): on close/navigate, `visibilitychange(hidden)` fires after `beforeunload` and around `pagehide`. With nothing unsaved the trigger does nothing. With unsaved edits the host's dialog already asked; if the user leaves, the autosave's `session.save()` (≥ 150 ms) never returns before teardown and no fetch goes out. So AS-2h helps for tab switch / minimise / discard, never for close — item 17. Firefox U1 (page_honesty, prompt accepted) stays green for the same reason: no PUT can leave.
- Throttling: the one-shot 30 s timer is right; the 3 s re-check chain is a chained timer and will be throttled to 1/min after 5 min hidden in Chrome — harmless, the transition save already ran.

### AS-2c (the cap)
- Broken but green (11): the cap never returns to 30 s after a successful write. Every later 3 s pause then costs an engine segment (0.15–0.7 s input block) — the exact cost §3.2 was written to avoid. AS-2c ends at the first save. Tail proposed in item 11.
- Also green: the 5-min clock starting at page open instead of at the first unsaved edit. Lower harm (an earlier first save for late typers); register only.

### AS-3 (not saving when it must not)
- (a) has no single-mutation red case (item 13). View-only sessions cannot become dirty (`_enqueue` :636–641 rejects every `mutation: true` with `EDITOR_VIEW_ONLY`; arrow keys only make `pending` flicker), so `hasUnsavedEdits()` is false at the 30 s mark, and even if the autosave decision ignored `viewOnly`, `saveDocument` returns early (:1871–1874). Removing the autosave's `viewOnly` clause does not turn AS-3(a) red. The §9.5 row should say so; the cell is still worth keeping as a regression cell for the existing guard.
- (b) depends on B-5. If B-5 stays: the broken-but-green is an implementation keyed on `lock.state === 'refused'` only, which also blocks autosave when the state is `not-stored` or `failed` (LOCK answered 200 without storing, or 5xx, :214–231) — those are not 423 and a save there is an ordinary If-Match + read-back write. Harm: no autosave for a user whose lock did not take; not caught by (b). If B-5 is withdrawn (item 7) the question disappears.
- (b)'s second half (auto writes into the copy) is sound: the copy sits in the user's own folder (`saveCopy`, :359–375), independent of the other user's lock.

### AS-4 (after a conflict, O1 = B)
- Item 4 is the serious hole: no cell exercises a live token. `put()` adds `If: (${token})` whenever `token` is non-null (:483); B-1 says not to carry it to the copy; the cells that would catch a mistake all have `token === null` (K6 after `loseLock`, K5 never had one). A PUT to the copy with the original's token is refused by Sabre's lock plugin (`validateTokens`, `Locks/Plugin.php:454–497`: a token that is not a lock of the request URI stays invalid → the `If` condition fails → 412), and the host then writes 「衝突副本（衝突副本 …）」 — B-6's "罕見" case made the common case. K12's shape (`unlock-refused`, :560–574) is a refused unlock that moves the ETag with the token alive; the versions runner's restore is the same shape in daily life.
- Broken but green on (a)/(b) even with the token right: the PUT to the copy without `If-Match`, or without the read-back GET. `on_wire` (:813–837) checks only PUTs whose URL ends with the original's name. Fold into AS-4(c) as in item 4 (Chrome wire: GET of the copy before the PUT, `If-Match` = the copy's version, no `If`).
- Item 15: `saveCopy`'s PUT does not touch `lastAnswered` (:486 is inside `put()`), so a second press right after a conflict (Ktwo's shape) writes into the copy within a second of creating it.
- The bar: B-3's priority (stranded > copy > lock) must survive a later `loseLock` from a refresh, which today overwrites `lockNotice` (:234–240); `render()` has one slot (:118–126). Implementation detail; the spec's wording suffices.
- Honesty of the state after an auto-copy (AS-6(b)): the user never pressed anything, the toast was 4 s, the bar says where the content went only while the tab is open, the next open of the original shows the intruder's bytes. L-reload covers reload; this is the owner's O1 = B. Register as the user-facing cost of B, nothing to change.

### AS-5 (typing during the autosave)
- Item 10: the first arm's 20 characters land in the adapter queue *after* `take()` produced the bytes, so they reach the server only through the next save. A runner reading the file after the autosave settles sees 0 of 20 on a correct product. Say when to read.
- Detecting "the engine segment of the auto save": the first `busy` after ~29 s of silence is the save; fine. The arm must not warm up (the prediction of 8–14 lost in the held-key arm is for the cold first save, M1b).
- The held-key arm's toast is the only channel (`toast()` :187–193 replaces text and restarts 4 s); a 30/s burst produces one visible toast; "至少跳一次" is the right quantifier.

### AS-6 (leaving)
- (a): no page_honesty arm idles 30 s after an edit (U1 Chrome: two guarded leaves ≈ 10–16 s; Uwin: the trap navigates as soon as 「儲存 N ms」 appears; see §C.1). No defect found.
- (b): after a thrown `CONFLICT` the page's `turn.then(settle, settle)` (:1895) and the host's `finally` (:428–433) both settle; `dirty` is false; `stranded` null → not asked. No defect found.
- A side effect worth one sentence in the release note: an autosave in flight makes `inFlight > 0`, so a user who closes the tab 30.3 s after their last key is asked 「確定離開？」 for a save they did not press. Honest, not a defect.

### AS-7 (pause)
- Item 11: no resumption cell. §9.2 says the pause ends at the next manual write; nothing measures it.
- Item 8: the design question. With `strand()` overwriting only on a new attempt (:321–325) and the pause stopping attempts, the download button hands over the first failure's bytes for the rest of the session unless the user presses save by hand. On 0.2.12 that was also true of a manual strand, but the user had pressed save and seen the bar; under autosave they may not have. Either side is defensible; the spec should state the reason it chose, now that the §8.1 reason no longer applies.
- "L-engine-pause" (no inducer): correct to register. The `session.save()` path's 180 s timeout (`editor-session.js:562`) is the one engine failure a user can meet; a pause after it is right.

### O2-1
- Broken but green: showing the attempt time instead of the completion time (the ±1 min tolerance cannot tell them apart; harmless). The host record has no `settledAt`; `attempts[-1].respondedAt` is the closest field (:487) — name it (item 18).
- Item 18's P-arm point: `check_m3_production_ui.py` reads the inventory at open (:523) and requires `inventory.title == NAME` (:691) and no text outside `TEXT_PLACES` (:112, :166–170). An O2 element that is present-but-empty or `hidden` at open passes; one that reads 「上次儲存：—」 or sits inside `#litecore-host-title` does not.
- (d) "寫進副本之後時間更新" relies on the host counting the first (thrown) copy as a write; §9.3 says so. Consistent.

### 128-B
- Item 3 (BLOCKING) and item 14 are design defects of fix A, invisible to 128-B's own cell (Backspace, succeeds, no host save in flight). A measurement that would see item 3 exists in the tree (the typing-latency instrument of §15.x), but the fix is a one-line design change and does not need one.
- 128-B's own measurement: no defect found. The prediction (10–20 ms) is consistent with the 128 trace (the action returns at ~45 ms, one band ~10 ms).

### 129-B
- Item 12: `editorAction` and the toolbar derive gesture affordance from `lastSelectionShape` (:818–827, :2231 falls back to it); a programmatic collapse via `placeCaret` does not reset it (only the pointerdown handler does, :2109). After an arrow key on a selection the buttons' disabled state and the 「manifest 沒有為「range-single」宣告」 tooltips describe a selection that no longer exists until the next click. Observable through `#toolbar[data-selection-shape]`, which the 129 evidence already reads.
- The < 400 ms bound is the right criterion for the inferred early acknowledgement (the empty `TEXT_SELECTION` advancing `sourceSequence`, `findings/evidence/129/README.md`, "Callbacks after the click"). If the inference is wrong, every arrow key on a selection pays `placeCaret`'s grace (`editor-session.js:399`) and the cell is red on the product — correct.
- On WASM the wrap offsets differ (other fonts); the 42 cells must re-discover W as the native tool did. The five extra shapes (s1e, m1r, m1e, s1d, m1d) should be recorded on WASM too; §9.4 says 「只記錄、不判」 for the wrap-end cells — good.
- Shift+Arrow becoming a no-op: Shift+Home/End used to move (as plain moves); the spec's rule 「不能照做的鍵就不要接」 is applied consistently. No change.

### 130-U
- No defect found. The replay (`findings/evidence/130/replay-input-trace.mjs`) extracts the page's predicate at run time; the red case (0.2.12's condition) is real (0 toasts). The toast text 「輸入未送出：queue-full」 shows an adapter reason code to the user; §3.8's 「說出有字沒有輸入」 is the better sentence — wording, not a criterion.

### 計數 (the unchanged counted runners)
- False as stated for host_entry `conflict` (item 1) and locks K8 (item 2); marginal for K7. Per CLAUDE.md 「驗收條件是為某個處方寫的；換了處方就要改條件，並寫下理由」 and §34's append-only rule, the right move is to re-base those cells now, with the reason, and let the first 0.2.13 run be the witness — not to discover them red and then argue §34.1(b), which is for a judge's error, which this is not.

## C. Interactions the design may have missed

### C.1 Census: counted arms, edit → next expected save/leave (read from the drivers; a one-off measurement, not a criterion)

| Runner / arm | Edit, then | Gap to the next save or leave | Under autosave |
|---|---|---|---|
| locks `hold` | save, marker, Ctrl+S | seconds | unchanged |
| locks `closetab`, `crash`, `heartbeat` | no edit | — | unchanged (`heartbeat` idles 330 s clean) |
| locks `unlock-refused` (K12), `foreign-lock` (K5) | save at once | seconds | unchanged; K12 now switches target (lock held — the scorer's :911–913 still true) |
| locks `broken-then-written` (K6) | save, sleep 5, `product_state` | 5 s | unchanged **iff** `#s-doc` keeps the original name (:943–945) |
| locks `expired` (K7) | `QUIET_PHASE` wait ≤ 25 s, clear lock, save | 5–29.5 s (edit() ≈ 1–4 s + wait ≤ 25 s) | **tail race** against the 30 s clock armed by `POINT_AT`'s pointerdown; a run that crosses records an auto save `[(204,True)]` before the manual one → `len(saves) != 1` (:950) |
| locks `frozen` (K8) | freeze 320 s + 10 s, thaw, save | the 30 s one-shot is overdue at thaw | **red by construction**: two saves (:963). Whether `Page.setWebLifecycleState frozen` also dispatches `visibilitychange` first is not verifiable here; the overdue timer alone suffices |
| locks `readonly` (K9′), `nowhere` (K10′), `offline` (K11) | manual save → copy / stranded; then dialogs, download, ≤ 75 s offline wait | long | unchanged: after the manual save `dirty` is false (`save()` finalize :576–582) and `savesUnsettled` 0, so there is nothing to autosave during the waits; K11's second save follows its marker at once |
| same_second (all) | each press edits then saves within the same script | < 2 s | unchanged |
| versions | edit→save, sleep 3, marker→Ctrl+S, restore, marker→save | seconds | unchanged |
| page_honesty U1 Chrome | two guarded leaves (dialog ≤ 5 s + 1.5 s each, reads), then save | ≈ 10–16 s | unchanged (margin ≈ 15 s) |
| page_honesty Uwin, U2, U3, U4, U7, Kheld, Ksep, Ktwo | save/leave within seconds | seconds | unchanged |
| production_ui Kdel/Kbs/Rbs/Rdel, P, B3x | 1 s waits; B3x's three refusals keep the session out of `ready` between keys | seconds | unchanged (B3x: the 30 s clock is re-armed by each typed marker; at the ceiling the session is `restart-required`) |
| assets | `open_and_smoke` → `save_before_leaving` at once | seconds | unchanged |
| host_entry `conflict` | save, sleep 5, save | 5 s | **red by design** (item 1) |

### C.2 The brief's list
- **1.1 s spacing and read-back (103/104/108)**: unchanged for the original; for the copy see items 4 and 15. A manual save < 1.1 s before the 30 s mark makes the autosave skip (`savesUnsettled > 0`) and find nothing dirty afterwards; fine.
- **`savesUnsettled` / `hostSaves`**: autosave through `saveDocument` serialises with manual saves (:1893–1896); a manual Ctrl+S during the auto engine segment becomes a second save with identical bytes (a second version, as Ksep already allows). 「尚未儲存」 shows during an autosave (`hasUnsavedWork` counts `savesUnsettled`, :87–89) — honest.
- **Leaving guard (107)**: `inFlight` guards during the host segment (:289); see AS-6 above.
- **B1 rescue**: `rescueAtGenerationLimit` goes through `saveDocument` (:1693); at the ceiling the session is not `ready`, so the autosave conditions refuse; the 3 s re-check then runs for the rest of the page's life (item 21).
- **109 reopen**: `_openFresh` restores `dirty: useCheckpoint` (`editor-session.js:193`), so content reopened from a checkpoint newer than the last save is `dirty` and the autosave will save it — the 109 user is covered. Good; worth a sentence in §9.2.
- **Browser-side checkpoint**: an autosave clears `dirty`, so `_checkpointBeforeSelection` (:472–476) and `_checkpointBeforeBoundaryMove` (:379) skip afterwards — autosave *reduces* checkpoint saves. A checkpoint in progress is inside an operation (`pending > 0`) and defers the autosave. No conflict.
- **View-only**: item 13; the existing guards make the autosave clause redundant but harmless.
- **Lock refresh after the target switch**: continues against the original (`refreshLock` :242–253), as B-2's withdrawal intends; a later LOST refresh must not overwrite the copy notice (B-3 priority; one-slot `render()` today).
- **Manual save racing an autosave**: serialised; the reverse order (auto timer during a manual save) skips and re-checks. No problem.
- **`visibilitychange` at unload / bfcache**: item 17; bfcache is already blocked by the Worker and open connections (the pagehide release path, :319, unchanged).
- **Firefox vs Chrome hidden timers**: the one-shot is right; the 3 s chain is throttled when hidden — harmless.
- **Composition at `hidden`**: switching tabs ends the composition; the conditions refuse during it and retry at 3 s.

## D. The 129 decision (§9.1, L-129)

- The conclusion (ship "click at the visible cursor", name Down-at-wrap-end as L-129, exact remedy in the link batch) is defensible: Down only; content unchanged; 42/42 on the brief's cells; the exact remedy is scheduled.
- The reasoning overstates in one place. 「它要靠拖曳方向猜哪一端是游標所在端」 is not a necessity. Measured: for a backward selection the visible cursor equals `TEXT_SELECTION_START` exactly (p2-backward), for a forward one it equals `END` (main round); the ambiguity exists only when the cursor matches neither — the wrap-end shapes (m1e, s1d, m1d: cursor at the end of line 1, END at the start of line 2) and the cell selection (S5: cursor in B1, START/END in A1 on the same row). A rule "cursor matches an endpoint → click the cursor; matches neither → click the endpoint that sits on another line, else the cursor" needs no direction and fits all 7 + 5 measured shapes. The honest reasons not to ship it are: three forward-only wrap shapes of evidence, a backward drag ending at a wrap end unmeasured, and CLAUDE.md §4 (a new rule while the exact remedy is a link away). Say those.
- L-129's wording 「或中文任意處換行」 names a cause, not the condition. The condition is: the selection's point is *displayed* at the end of a wrapped line (a drag ending to the right of the line's end, or Shift+End); CJK makes a wrap at the drag's end more likely, it does not make every CJK selection affected (S1 made with Shift+Right across a wrap was 6/6 same). Suggested: 「選取的游標端顯示在某一行的行尾時（拖曳結束於該行行尾右側、或 Shift+End）；中文可在任意字元換行，所以拖到行尾的情況更常見」.
- One unmeasured risk on WASM: the native click arms waited 500 ms of quiet before reading the cursor rectangle; a user presses the key sooner. If the page reads `caret` from a state snapshot that predates the drag's last `TEXT_SELECTION` update, it clicks the wrong rectangle. 129-B (42 cells, real keys, both browsers) is the measurement that decides; no change to the criterion, but the runner should press the key promptly after the drag's `selectionShape` settles, as a user would, not after a long quiet.

## E. New machinery (CLAUDE.md §4, §34) — keep, state, or withdraw

| Item | Verdict |
|---|---|
| Per-record `conditions`, `trigger`, `target` | data, not mechanism; keep (fix its sources, items 5–6) |
| 30 s one-shot + 5-min cap + 3 s re-check | needed; the cap has a stated precedent (COOL); keep; make the re-check stop in a dead session (item 21) |
| B-5 gate | the main session's addition; cost = a 127 window for the locked-at-open user; **withdraw or name as L-locked-open** (item 7) |
| Pause after stranded | its stated reason (copies multiplying) no longer exists under B-1; **state a new reason or withdraw** (item 8); pause after engine failure stays (180 s timeout) |
| Page `#notice` 「自動儲存已暫停」 | reachable only on engine failure, where the session's own recovery notice already speaks; candidate for withdrawal (item 21) |
| O2 label, 「（自動）」 suffix | the owner's decision; keep (item 18 for placement) |
| B-1 target switch | the owner's O1 = B; keep (items 4, 15) |
| B-2 withdrawal | right under §34 for this release; list the lock-on-abandoned-file cost as a work item (item 16) |

## F. What I could not verify here

- Whether Chrome's `Page.setWebLifecycleState({state:"frozen"})` dispatches `visibilitychange` before freezing (Chromium's handler hides the page first, from memory). K8 goes red regardless (the overdue timer at thaw), so no measurement is needed for item 2.
- That the empty `TEXT_SELECTION` after the collapse click advances `sourceSequence` on WASM (inferred in the 129 README). 129-B's < 400 ms bound measures it; nothing to add.
- The real server's host-segment length (§9.8 already lists it). It sets the size of item 3's regression on the owner's deployment, not whether it exists.

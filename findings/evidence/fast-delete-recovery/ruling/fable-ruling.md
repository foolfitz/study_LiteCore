# fable's ruling on findings 119 and 111 (2026-10-09; the owner authorised fable to decide this round)

Brief: `brief.md` in this directory. Returned verbatim below; the main session's own check of the facts the ruling corrects follows at the end.

---

RULING

119: **D** — A now (shell only), C registered as the root-cause item. Two corrections to A as written:
(1) Do NOT premise it on "the document is unchanged by the key". Bank the engine's current content at the refusal regardless (109's keyPosted branch is the precedent: "every typed change survives; only the key's own effect is uncertain"), and word it accordingly — never 「文件沒有被改動」 for this code.
(2) Scope = actions `delete-backward` / `delete-forward` × code `EDITOR_STATE_UNAVAILABLE` with no `formatBarrier` detail. In the subclass's `action()` catch, before `_blockQueueIfDispatched`: checkpoint (`_checkpointBeforeSelection`, swallowed into `checkpointError` as 109 does), then `this._blockQueue(error, "restart-required", …)` yourself (the base class's RECOVERY_ERRORS does not contain this code, so nobody else will), set `error.recovery = "restart"`, rethrow. Page: route it into the existing `reopenAfterBoundaryRefusal` (it already does restartAvailable / restartKeepsContent / B1 ceiling / focus) with its own lead sentence; and add `el.sink.focus({ preventScroll: true })` inside `onNoticeAction`'s `run()` after `rollback()` resolves (the `Q` that did not land).
Not B: a checkpoint-before-every-rollback would reopen documents holding an unverified mutation, which is exactly what "rollback" exists to discard; it changes the meaning of every rollback to fix one code. Not C now: engine + relink + re-validation for a 1-in-40–90 tail event that the shell can make lossless.

111: **ship**, in the same release, as its own commit, with: the five prototype tests; a generation guard (a held operation records the session generation it was held under and is rejected, not run, if the session restarted before release — the base `_enqueue` stamps generation only at enqueue time, so a released item would otherwise run on the fresh Worker); and a `save` ordering test. Optional: read the adapter's public `state` getter (`requestCount`, `queueDepth`, input-adapter.js:80–92) instead of `_queue`/`_requestCount`; `queueDepth > 0` holds one char longer but never reorders.

Together: **yes** — one shell generation (v58), one host (0.2.9), one recount. Two commits so a red cell bisects by checkout, no relink.

WHY（給擁有者）

1. 119 是資料遺失：引擎拒絕刪除時明說「沒有動到文件」，但殼層把它當成「可能改壞了」擋住佇列，唯一出口是上次存檔，打的字就沒了。
2. 修法跟 109 同一個模子：拒絕那一刻先把引擎裡的內容存成檢查點，再自動重開——使用者打的字全留，代價是重開約兩秒、游標回開頭。
3. 不選 B：「每次要回滾都先存檢查點」會把「可能已經改壞」的內容重開回來，等於把所有回滾都改掉，為了一個代碼動全身。
4. 不現在做 C：要改引擎、要擁有者連結、要整套重驗，而且成因（callback 為什麼晚到）還沒量，先量再修；登錄成待辦。
5. 一處要改掉：不能宣稱「文件沒有被改動」——引擎四個出口有一個理論上在送出之後（實際幾乎到不了），措辭寫「這一下刪除沒完成，內容已先保住」就永遠不會說錯。
6. 111 一起出：同一個檔案、同一次凍結、同一次重新計數（約 3.5 小時）；分兩個 commit，紅了可以用 checkout 分辨。
7. 111 多加一道守衛：被暫緩的操作若在等待期間工作階段重開了，要丟掉、不能在新引擎上執行。
8. 驗收：單元測試先紅一次再綠；瀏覽器用同頁探針跑到自然出現至少 2 次（目前頻率約 180 次 2 次，預算 400 次），每次都要看到字留著、不點擊就能打字。
9. 自然出現不到 2 次，就只能寫「沒量到實例」，由「注入同一個錯誤」的臂扛瀏覽器那一半，不能宣告自然路徑已修。
10. 順序：改完、單元綠、探針綠，**最後才凍 v58**；絕不覆寫 v57。
11. 第二輪同頁探針（79 次 0 失敗）還在跑，不要殺；它的次數算進 119 的頻率。

FACT CHECK

- F1 — correct. `rejectSelectionBarrierAtDeadline` :3888–3894; `finishSelectionBarrierError` :3324–3334 appends the suffix when `viewRecoveryRequired` (= selection visible or caret not typed-collapsed).
- F2 — partly wrong. :3496 (`queueSelectionBarrierStep`) is also reached from `maybeQueueSelectionBarrierFinalVerification` (:3502–3513), i.e. AFTER `postUnoCommand` at :3839, with `viewRecoveryRequired=false` (no "no mutation" suffix). So "at the three selection-barrier sites the delete has not been dispatched" is false for one reachability. Practically unreachable: `submit()` (:2423) fails only before the engine starts (non-sdk commands skip the duplicate check). Consequence: the fix must not word itself on "unchanged". The :4009 precondition and the v19 merge-path claim (`finishMergeKeyError` always `EDITOR_BOUNDARY_UNSUPPORTED` with `mergeKey`) are correct.
- F3 — correct, chain verified: `recoveryFor` (paragraph-editor-session.js:44–78) → `formatFailureDisposition` (paragraph-editor-client.js:234, falls to "unknown-rollback": no barrier, not LOK_COMMAND_FAILED, not in PRE_DISPATCH_CODES) → "rollback" → `_blockQueueIfDispatched` (:716–722) → `recoverable-error`. Base `RECOVERY_ERRORS` (editor-shell/editor-session.js:15–22) does not list the code — only the subclass blocks it. 109 keyed at narrow-editor-v2-session.js:510–511 and page :1236; `reopenAfterBoundaryRefusal` requires `restart-required` (:1097) — hence block as `restart-required`.
- F4 — correct. `e1/editor-shell-bundle-v2.json` includes editor-client, editor-session, state-machine, clipboard-adapter, input-adapter only. The v2 session and page are M3 pins (page sha, session sha), which is the recount cost you already priced.
- F5 — inference, and imprecise as stated. `handleInsertText` (:3186–3225) replies AFTER `paste()` returns, so the paste is applied when the insert resolves; what is late is `LOK_CALLBACK_TEXT_SELECTION` for the barrier's OWN unit selection (the selection is already readable at the 250 ms deadline, its callback not flushed). Normal attempts finish the whole delete in 83–100 ms, so this is a tail of the callback-flush latency, not "still applying the paste". Unmeasured; C must start by measuring that interval.
- F6 — holds by reasoning (FIFO: the delete still starts right after the last insert's reply, now after Y instead of X); not measured. The 119 run on the fixed page will produce a rate; record it, do not read F6 off it.
- Also checked: the prototype's release points are real — the adapter's `_pump` passes `requestNumber` in metadata (input-adapter.js:388–393) and the base session wires `commit: (text, metadata) => this.commitText(text, { metadata })` (editor-session.js:31–32). Run 2 (`chrome-same-page-2.json`) is at 79 attempts, 0 failures, still running; with run 1 and the 111 round that is ~2 in ~180 same-page attempts — lower than the brief's "1 in ~40". The ruling does not depend on run 2.

CONDITIONS

Write first (before any run): a new appended section in `specs/SPEC-M3-production-ui.md` (append-only) with the criteria below and predictions; the `因審核而修` / `因執行而修` numbers in the handoff are expected 0 / 0.

Unit, 119 (narrow-editor-v2-session.test.mjs + page functions compiled as the B1 tests do):
- U1 dirty doc, fake `editor.action("delete-backward")` rejects with the recorded error (code `EDITOR_STATE_UNAVAILABLE`, no details): checkpoint taken from the engine's current content, state `restart-required` (not `recoverable-error`), `restartKeepsContent()` true, `error.recovery === "restart"`, input blocked; `restart()` reopens the checkpoint bytes.
- U2 clean doc: no save, `restart-required`, `restartKeepsContent()` true.
- U3 checkpoint save fails: `checkpointError` set, `restartKeepsContent()` false, the caller still gets the engine's error.
- U4 control: same code on a non-delete action without barrier detail keeps today's behaviour (rollback / `recoverable-error`). U5 `delete-forward` covered.
- U6 page: `run()` with this error reaches the auto-reopen path; the lead sentence contains no 「沒有被改動」; `onNoticeAction` focuses the sink after `rollback()` resolves.
- Red cases, each shown red once: remove the checkpoint call (U1), block as `recoverable-error` (U1), drop the action scope (U4), drop the focus (U6). Existing 155 (+5) pass.

Unit, 111: the five prototype tests; U7 a held operation across a block + restart is rejected, not run on the new generation (red before the guard); U8 `insert X, insert Y, save` order with X in flight and Y in the adapter. Existing 155 pass.

Browser, 119 (candidate `dist/`, Chrome where it reproduces; Firefox optional and named unmeasured):
- Instrument: `probe_fast_delete_recovery.py --same-page`, adapted to read the auto-reopen (no notice pressed): after a failed delete, within 10 s state `ready`, generation +1, toolbar enabled, `#notice` hidden; save → heading holds X (and Y: with 111 the refused delete followed Y); real `Q` without a click → revision advances. Red case for the reading rule = existing `chrome-same-page-1.json` attempt 41 (holdsX false, typingQ 0→0) must read FAIL.
- Budget up to 400 attempts, stop at 3 natural failures. Prediction: ≥ 2 failures, each keeping X and landing Q.
- Verdict rule, fixed now: ≥ 2 natural occurrences all green → browser half established. 0–1 → the natural half is registered 「沒有實例可量」 (not 「沒有東西守著」) with the attempt count, and the browser half is carried by an injection arm: the probe's shim makes `editor.action` reject with the exact recorded error on the real engine and the owner's document, 3/3 per browser, same observables (product bytes unchanged). Run the injection arm in both outcomes — it is the deterministic positive control.
- Run it serially with everything else that drives headless Chrome (the 250 ms deadline is engine-side; load moves the rate).

Browser, 111: `probe_111_overtake.py` on the candidate `dist/`, `--document boundaries` and `--document owner`, gaps 0 and 10, Backspace and Enter, 10 each, both browsers: prediction 0 overtaken, 0 `other`, 0 `no-save`, `ok` 10/10. Red case under the same rule = existing `browser/firefox.json` and `owner-firefox.json` (9–10/10 overtaken at 0 ms).

Release, in this order (freeze last):
1. Commit 119 fix + tests; commit 111 fix + tests; `make test-e2-c-static` exit 0 and E1-C intact after each.
2. `make e2-c-assets` → new page sha; confirm the cutover pins did not move (`PINNED_WASM_SHA256` 1aafd4f9…, `workerUrl` v19).
3. Both browser probes on `dist/`. Anything they force goes back to step 1, before any freeze.
4. Freeze shell generation **v58** (`build_e2_c_shell_bundle.py --frozen-date …`, question mode exit 0 afterwards), point MANIFEST at it. Never touch v57.
5. Host **0.2.9**: `package_m3_engine.py` from `dist/` (new buildId; packs unchanged), info.xml bump, `ddev occ upgrade`.
6. Re-pin per §13.5's pattern: page sha, session sha, host 0.2.9 + commit, buildId, shell v58 digest, `check_m3_production_ui.py`'s own sha. Pin lines only — a binding move, not a check change.
7. Count: each of the seven runners once + its `--red-cases`, then the chain (~3.5 h), product-path net per M2-5 on the new page, `make test-e2-c-static`.
8. Register C as a named queue item: measure (engine-side timestamps) the interval between the barrier's unit-selection post and `LOK_CALLBACK_TEXT_SELECTION` across same-page attempts, rule between callback-flush latency (040's family) and accumulated per-document work in a long-lived Worker, before choosing "arm after the insert's callbacks" vs "re-arm on a readable-but-unannounced selection". Also register as named limits: each auto-reopen spends a Worker generation (B1 ceiling → rescue path after the third); a held operation is outside `pending` for the milliseconds the adapter queue is non-empty.
9. 119 → 已修 only after step 3's rule AND step 7 green; 111 likewise.

Must not:
- Edit `editor-shell/editor-session.js`, `input/input-adapter.js` (E1-C) or the engine; no relink this round.
- Key the disposition or the scope on `error.message` text; widen to B; claim 「文件沒有被改動」 for this code.
- Freeze v58 before both probes are green; overwrite v57; put anything else into v58.
- Change any §34.1 tool or any runner beyond the pin lines; add a third review seat; write a new judge tool for 119 (the probe JSON plus the written rule is the reader).
- Declare 119 fixed on the natural path with fewer than 2 natural occurrences; declare 111 fixed without the owner-document arm.
- Kill `chrome-same-page-2`; its count goes into 119's rate.

---

## Main session's check of the corrected facts (2026-10-09)

- F2's correction holds: `maybeQueueSelectionBarrierFinalVerification` (`src/probe_engine.cpp` :3502) runs only in `AwaitingDeleteCompletion`, which the barrier enters right before `postUnoCommand` (:3836–3840), and it calls `queueSelectionBarrierStep`, whose submit failure emits `EDITOR_STATE_UNAVAILABLE` (:3494–3498) without the "no mutation" suffix.
- The adapter's public `state` getter has `requestCount` and `queueDepth` (`input/input-adapter.js` :82–92; `queueDepth` counts the in-flight item too).

---

# Second ruling (2026-10-09, after the v58 freeze): the `rollback` mutation's anchor

Asked: after freezing v58, `make test-e2-c-static` failed `test_every_mutation_matches_its_target_exactly_once` (mutation `rollback`, `tools/run_e2_c_product_path.py` ~:2383): its anchor `  void run("回到檢查點", () => session.rollback())` no longer exists because U6 moved the focus into that operation; the first ruling forbade runner edits beyond pins. Options A (re-anchor the one mutation), B (restore the line, focus after run()), C (drop the focus). Returned verbatim:

RULING

A. Re-anchor the one mutation in `run_e2_c_product_path.py`: find `    await session.rollback();` → replace `    await session.undo();`, same check id, same `reintroduces` text. Keep the page as frozen; v58 stands (the runner is not in the shell bundle, so no refreeze). Not B (focus after `run()` was measured too late for the first key on 2026-10-06, and it moves the page → v59). Not C (it trades a measured defect fix — `typingQ 0→0` in `chrome-same-page-1.json` attempt 41 — for a test anchor; the check serves the product, not the reverse).

WHY（給擁有者）

1. 那條測試自己的錯誤訊息就寫著「樹在突變底下移動了；修樣式，不要修次數」——這正是它被寫來抓的情況，不是產品錯。
2. 突變的意思（把回復接成 undo）一個字都沒變，只是釘的那一行因為加了「重開後把焦點還給輸入槽」而換了形狀。
3. 不選 B：焦點晚一拍給，第一個鍵會掉——2026-10-06 量過；而且要改頁面、重凍 v59。
4. 不選 C：為了保住一個測試錨點而拿掉一個量到的缺陷修法，本末倒置。
5. 這算「因執行而修」的檢查 1 筆，證人就是那次 `make test-e2-c-static` 的失敗輸出；「因審核而修」仍是 0。
6. 還沒有任何 0.2.9 的產品路徑執行，所以沒有東西作廢；預測檔那句「runner 不變」要用追加的方式更正。

FACT CHECK

- Mutation `rollback` at `wasm_sdk_probe/tools/run_e2_c_product_path.py:2383–2399`: find `  void run("回到檢查點", () => session.rollback())`, check `notice-action-recovers-the-session`, declared live (no `expectedToBeDetected`). Confirmed.
- `wasm_sdk_probe/tests/test_product_path_mutations.py:146–158` (`test_every_mutation_matches_its_target_exactly_once`) reads `dist/`, demands exactly one hit, and its own message prescribes "fix the pattern, not the count". Confirmed — an honest static failure with a committed product cause (73da170e), which is the witness §34.4 asks for.
- `web/e2-editor-app.js:1516–1518` and `dist/e2-editor-app.js:1516` now read `void run("回到檢查點", async () => { await session.rollback(); el.sink.focus({ preventScroll: true }); …`. Confirmed; `await session.rollback();` is the natural single-occurrence anchor (the boundary reopen calls `session.restart()`, not `rollback()`). The census test itself proves the count after the edit.
- §34.1's freeze window ended when X7's verdict was read (handoff 10-08f); §34.4 still applies and is satisfied by the witness. `findings/evidence/release-0.2.9/product-path/PREDICTION.md` line 5 says "`tools/run_e2_c_product_path.py` unchanged" — now false; correct by appending, not editing.
- v58 (`a6f9331a…`) differs from v57 only in session and page; the runner is outside the bundle — A does not touch the frozen bytes. Uncommitted right now: `e2/editor-shell-v2-bundle-v58.json` and the pointer change in `build_e2_c_shell_bundle.py`.

CONDITIONS

1. Commit the v58 freeze as it is (manifest + MANIFEST pointer) BEFORE the runner edit.
2. Runner commit: only the two strings of the `rollback` mutation (find/replace); `make test-e2-c-static` exit 0 after; the pre-edit failing output saved as the witness (e.g. `findings/evidence/release-0.2.9/product-path/test-e2-c-static-before-reanchor.txt`) and cited in the commit message.
3. Let the mutation go red once before any counted product-path run: if the net's plan already includes the self-proof mutation run, nothing extra; otherwise run that single mutation, one browser, and record `notice-action-recovers-the-session` red under it. A green there means the re-anchor missed — fix before counting.
4. Append to `release-0.2.9/product-path/PREDICTION.md`: the runner is no longer "unchanged"; its new sha256, the reason (this ruling), and that no run preceded the change so nothing is voided. If `judge.py` pins the runner's sha, move that pin in the same commit (pin line, allowed) and say so in the appended paragraph.
5. Handoff numbers: 因執行而修 = 1 (this, with the witness), 因審核而修 = 0.
6. Must not: edit the page or session again for this (no v59); widen the runner edit beyond the two strings; change the check id, the mutation's semantics, or any other mutation; count the product-path net before step 3 has gone red once.

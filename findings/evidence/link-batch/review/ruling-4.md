# Ruling 4 — the model test's six holes in §10–§12; what this link ships instead

Ruled by fable on the owner's behalf (same authorisation: owner, 2026-10-13, 「有疑義的發給fable，我授權它代我下決定」). Brief: `brief-4-model-holes.md` (`3881dbc7`) and the coordinator's correction (reachability on 0.2.12 and 0.2.18 separately). Evidence: `findings/evidence/link-batch/extend-model/` (`fce084d6`): `README.md`, `test-output.txt`, `wasm_sdk_probe/src/extend_completion.hpp`, `wasm_sdk_probe/tests/extend_completion_model_test.cpp`, task `handoff/tasks/TASK-2026-10-13j-extend-rule-header-and-model-test.md`. Condition numbers continue from 29.

**What I ran.** Rebuilt the test with the README's command into the scratchpad and ran it: exit 0, `ok`, the six `REPORTED` lines with the same counts as `test-output.txt` (514; 44,124; 103,776; 160 with 128 wedged; 110,784 with 27,744 wrong; 222,240 with 2,448 wrong). Traced the first sequence of each with `EXTEND_MODEL_TRACE`; each trace is read below. Nothing was built for the engine; no file other than this one was written.

## RULING

### The two claims of my own rulings, head-on

1. **Ruling 3 Q2 / §12.2: "every stacked-extend sequence refuses." False.** Trace 1 (`E=readback-move(Shift+Right,deadline=0) U=Shift+Right … Backspace`): two forward extends still queued, the barrier posts K1 behind them, core runs Shift+Right, Shift+Right, Shift+Left, one flush with selection `[0,1]` = "a", one code point, flagged, admitted; `verified-selection-delete` of one unit, Writer deletes "ab". Trace 4 (`E=readback-move(Right,deadline=0) U=Shift+Left … Backspace(lagReg2=1)`): the pending extend's own flush lands between K1's post and K1's run; the verifier reads that selection as K1's, admits it, K1 then runs on the deleted text; in 128 sequences the collapse never arrives and `AwaitingDeleteCompletion` waits forever (confirmed: only `AwaitingUnitSelection` and the merge stages carry deadlines, `probe_engine.cpp:3342`, `:4023-4031`; none at `:3504`, `:3837`, `:3910`, `:3931`). The one-code-point rule was a proof about the selection's size; it never identified which key produced it. I withdraw the claim and the flag as a closure.
2. **Ruling 3 Q2 / §12.2: the forged-completion residual "needs three coincidences".** Wrong as structure and unsupported as frequency. Trace 3: the earlier readback extend sets the flag, the user's extend completes on a forged transition (the earlier key's flush), which *clears* the flag, and `delete-selection`'s `.uno:Delete` runs ahead of the queued key; 103,776 generated sequences across every earlier-operation class. And the same mechanism needs no extend at all: items 5 and 6 reach `delete-selection` through today's completions on the product as shipped. The "three coincidences" sentence is struck.

### Why there is no further patch (the owner's instruction, and the structure)

All six items have one cause. Two delete dispatches bypass the posted-key FIFO: `.uno:Delete` runs synchronously under the SolarMutex (`probe_engine.cpp:5352`) and the barrier's K1 is a key posted behind whatever keys are still queued (`:4041-4049`). And the engine has completions that answer before the key ran (the 250 ms readback, `:2300-2330`) or on another operation's flush (today's first-callback rule for caret-start moves, `:2155-2175`; a forged rule-(a) transition; `uno-command-result` before its own flush, `:2742-2797`; a select-range before END's selection, `:5555-5625`). Any rule that admits a delete behind an unconfirmed key is a bet on timing, and a key that changes nothing can never be confirmed without a FIFO marker. Each guard the model or the executor suggests closes some items and not others: the anchor fence for Barrier-class units closes 1 and 4 (the executor is right: in both traces K1's anchor side is not at P) but not 2, 3, 5, 6; a flag on readback-completed plain range moves closes item 2's readback half; a flag that transitions cannot clear closes item 3 where a readback preceded, not where none did (undo, then a forged extend, then `delete-selection`); the one-code-point rule applied unflagged closes item 3's barrier half and regresses every multi-code-point grapheme; a flag on any deadline completion reopens after any stalled typing. Per the brief, I do not stack another patch for the model to break.

### Ruling per item

- **Item 1 (514):** hole confirmed by trace; §12.2's flag withdrawn as a closure.
- **Item 2 (44,124):** hole confirmed by trace 2 (`E=uno:undo U=Left lagReg=3 … Backspace`: the plain move on the restored selection answered by readback, `delete-selection` deletes the selection Writer would have collapsed). v20-only (range-start plain moves are not offered by v19's manifest; 0.2.12 and 0.2.18 route them to a gate refusal or, on 0.2.18, to the 129 click-then-move).
- **Item 3 (103,776):** the residual's size claim withdrawn; the clearing rule is defeated by the very population it was named for.
- **Item 4 (160, 128 wedged):** hole and wedge confirmed. The wedge is a property of today's barrier (no deadline on `AwaitingDeleteCompletion`) reachable only through an extend's flush landing between K1's post and run, so v20-only; no deadline is added in this link (no reachable path without extends; one variable).
- **Item 5 (110,784; 27,744 wrong):** trace 5 (`E=uno:undo U=Left lagReg=0 … Backspace`): the plain move registered while undo's flush is half delivered completes on undo's late `TEXT_SELECTION` before its own key is posted (today's first-callback rule); the page's snapshot is undo's range; `delete-selection` passes the cache-read gate (`:5285-5300`) and `.uno:Delete` deletes the restored text ahead of the queued Left. Writer collapses and deletes nothing. **Reachable today; a finding, registered below.**
- **Item 6 (222,240; 2,448 wrong):** trace 6 (`E=select3(gapRS=1,gapSE=0,deadline=1) U=Left … Backspace(lagReg2=3)`): the product's select-range arms the 250 ms readback (`editor_api.cpp:210-224` → `probe_engine.cpp:6790` → `:5559`); it completes collapsed before START/END's flush; an arrow is sent bare; the late selection arrives; `delete-selection` deletes the whole range where Writer collapses first. **Reachable today; the same finding.**

### (a) Reachability, the two releases separately

Both run engine `e2-editor-v19`; the differences are the page and the shell.

- **0.2.12 (counted; page `8909564e…`, read from the count tree `7fb0ed08`, sha256 verified; shell v61; host `b245ae7`).**
  - Items 1, 3, 4: **not reachable** — no extend reaches the engine (the page sends a plain move when Shift is held, finding 129's original defect; the ABI accepts extend only for the two character moves and the manifest offers them `collapsed`-only).
  - Item 2: **not reachable** — a plain move on a range is refused by the gate when the cache holds the range; when the cache is stale-collapsed the move is a caret-start move, which is item 5's class.
  - Items 5 and 6: **reachable.** The page chooses `delete-selection` at `beforeinput` from the session's snapshot (`8909564e…` lines 2224-2231, no `deletesInFlight`, no `moveFromPoint`); `selectionShapeOf` reads `state.selection` from the engine's cache (`editor-shell-v2/narrow-editor-v2-session.js:121-133`); the engine's rules are v19's.
- **0.2.18 (today's uncounted candidate; page `b24d754a…`, shell v66, host `96a87d8`).**
  - Items 1, 3, 4: **not reachable** — the page drops Shift (`e2-editor-app.js:2596`); same ABI and manifest.
  - Item 2: **not reachable** — on a range the page clicks at the point and then moves (`:2609-2615`, 129's prescription); the move is dispatched on a caret.
  - Items 5 and 6: **reachable**, same mechanism (`:2403-2421`; rule A changes nothing here, no delete precedes the move).
- **Precondition on both:** the core thread must stay silent longer than the engine's 250 ms readback (item 6) or than one page round trip (item 5: worker → page drain → `getState` → next item → worker), and the arrow and the Backspace must be typed inside that silence. Finding 135 measured 196.6–210 ms silences on 4 of 21 runs of one cell; nothing longer has been measured and no runner can induce one. Severity: data-changing (a selection the user had just collapsed is deleted; or, in item 5's forward variant, one character ahead of the caret). Not a wedge.

### (b) What the counts mean

Coverage of the generated interleaving space (two texts, eight shapes, eight earlier operations, six keys, lags), not real-world frequency. What they establish is that the class is structural: it spans every earlier-operation class, every shape and several lags, so it is not one unlucky lag. Any statement about frequency needs a measurement of core-thread silences on the product, which does not exist beyond 135's one cell.

### (c) Validation in the model before wiring

Yes, and widened: the model is the gate for **any** delete-path design before native rounds, and the executor re-runs it with every red case and liveness check reported again. Two shapes it does not yet hold and must gain for the next spec (reported, not ruled): typing (`paste`, synchronous) dispatched behind a pending key, and an inline format dispatched behind a pending key; both jump the FIFO exactly as `.uno:Delete` does.

### What ships instead

- **Items 1 and 2 are withdrawn from this link.** Ruling 2's (d) is overturned on the model's evidence: the residual is not "one stale reply"; it is four data-changing shapes and a wedge, and no rule inside the current delete design closes them. The owner asked for Shift+Arrow by name; the honest answer is that it is safe only once deletes are ordered as Writer orders them, and that belongs to the next engine batch.
- **This link (v20) ships:** the page number (item 3, §10.8/§12.3), C (item 4, §10.5's window without the flag clauses), §4.5(2) as data (`caretBefore`, E2, E3), and the count K with 127–136. Editor ABI stays 4 (no action-contract change; `page-rectangles` is a document export). The manifest's six moves stay `collapsed`-only. The page's delete routing is unchanged (today's `beforeinput` choice and rule A); §10.4/§12.4, S1–S5, R1, S-12 and §12.5's pin widening are deferred with items 1/2.
- **C without extends is safe on the model's own evidence:** "pending plain move then Backspace Writer-equal 80/80" is the liveness cell for the keys v20 offers, and the cancelled-pair no-op and item 4's wedge both need an extend. L-C-late-K1 and C1's per-completion criterion stand.
- **The header stays as committed:** rule (a) is still the right completion for extends when they come; the flag's functions are not wired by anything and are superseded by the next spec. The test's pinned `REPORTED` counts are re-ruled here (condition 32).
- **Finding registered (two numbers are the index's to assign; one finding, two items):** "a delete-selection dispatched from a snapshot that an earlier operation's late flush forged: undo/redo/format/delete-selection then arrow then Backspace (item 5); a drag whose selection flush is later than 250 ms then arrow then Backspace (item 6)". Reachable on 0.2.12 and 0.2.18; evidence = the model's traces; precondition and severity as above; closure = the ordered-deletes spec. No interim page patch: every candidate is a timing bet of the kind this ruling refuses.
- **The next engine batch: ordered deletes.** A spec whose single property is "every document change the page asks for happens in the order Writer would apply it". Candidates, each measured natively first and model-gated before wiring: **(A)** `delete-selection`, and every delete behind a move or extend, as the user's own key posted FIFO and proved by the `.uno:Undo` payload — the merge path's own method (v15–v19; 324 native cases byte-equal; 117's poll); the barrier stays only where no key can precede it; to measure: the Delete/Backspace key on ranges (single-line, cross-paragraph, tables, inline objects, fields) against `.uno:Delete`'s result; the boundary case (a key that does nothing proves nothing: `key-deadline` → reopen, so C's gain is lost behind a move — decide); the `selectedText` report (the undo comment). **(B)** a FIFO marker after each posted key (§16.1 forgery analysis first). **(C)** the single-thread engine topology (`OXSDK_MAINLOOP_ENGINE`, unipoll: keys synchronous, so no key is ever pending — constrained by finding 040 and the `#error` at `probe_engine.cpp:15`; a measurement question). Typing and inline formats behind a pending key belong to the same spec. Shift+Arrow and range-start moves ship with that batch.
- **Order:** relink v20 now with the reduced scope and run the count, then the ordered-deletes spec. 127–136 have been uncounted since 0.2.12 and the owner works on an uncounted candidate daily; the reduced v20 is not worse than the counted release on items 5/6 (same class, same engine), and it removes nothing the counted release has.

## WHY (for the owner)

模型測試證明我前兩次裁決的那個旗標關不住洞：它只證明選到的東西有多大，從來沒證明那是哪一鍵選的，所以兩個往前延伸會被縮成一個字而放行、延伸自己的回呼會被當成 K1 的，還有一條會卡死。更根本的是，這六個洞同一個成因：刪整段選取的指令和刪一個字時引擎自己送的 Shift＋左，都會插到還沒執行的按鍵前面，而引擎又有幾種「鍵還沒跑就回報完成」的情況；只要刪除可以排在一個沒被確認的按鍵後面，任何規則都是在賭時間，而一個「什麼都沒改」的按鍵根本沒辦法被確認。再補一層規則，模型會再找到下一個洞，你也說了寧可不要。所以 Shift＋方向鍵和範圍上的方向鍵從這一批拿掉，等「刪除照 Writer 的順序執行」那一批一起出；這一批只出頁碼、兩端 Backspace 不重開、拒絕帶游標，然後做完整計數。第 5、6 兩個洞不需要新功能，今天的 0.2.12 和 0.2.18 都到得了：復原或選取之後緊接著方向鍵和 Backspace，若核心剛好停頓超過兩百多毫秒，整段選取會被刪掉而不是先收起來；登錄成 finding，不打臨時補丁，因為補丁也是賭時間。模型的序列數說的是「這一類不是某個巧合」，不是「多常發生」；多常發生沒有人量過，也沒有工具能逼出來。下一批先在原生量「把刪除改成送使用者自己的鍵、用復原紀錄證明」這條路，模型先過，才接線。

## FACT CHECK

| claim relied on | status | where |
|---|---|---|
| the test rebuilds and reproduces the six items with the same counts | confirmed (ran it) | README's command; my run: exit 0, `ok`, `REPORTED 1–6` identical to `test-output.txt:2799-2804` |
| each item's first sequence behaves as described | confirmed (traced) | `EXTEND_MODEL_TRACE` on the six `first:` sequences; outcomes: 1 deleted=1 text=bcd writer=cd; 2 deleted=1 text=abcd writer=zabcd; 3 deleted=1 text=bcd writer=abcd; 4 completed Writer-equal in the first sequence (wedge in 128 others per the census); 5 deleted=1 text=abcd writer=zabcd; 6 deleted=2 text=ad writer=acd |
| the header implements §10.1/§12.2 as written (flag set on readback extends, cleared on any transition, one-code-point rule, window refusal) | confirmed | `src/extend_completion.hpp:157-247` |
| the model's LOK, page and barrier assumptions trace to source | confirmed where cited | `tests/extend_completion_model_test.cpp:12-80`; `init.cxx:1592-1594`, `:2530-2537`, `:2485-2486`, `:2577-2581`; `lokhelper.cxx:1291`; `probe_engine.cpp:3186-3221`, `:2742-2797`, `:5555-5625`, `:3785-3895`, `:4004-4049`; `editor-session.js:287-311` |
| `AwaitingDeleteCompletion` has no deadline | confirmed | `probe_engine.cpp:3342` (merge stages), `:4023-4031` (`AwaitingUnitSelection`); none at `:3504`, `:3837`, `:3910`, `:3931` |
| `.uno:Delete` for delete-selection is synchronous and not a posted key | confirmed | `probe_engine.cpp:5333-5352`; `unoctitm.cxx:655-657` |
| the product's select-range arms the readback | confirmed | `src/editor_api.cpp:210-224` (`boundedReadback=true`), `probe_engine.cpp:6776-6790`, `:5559` |
| caret-start plain moves complete on the first callback | confirmed | `probe_engine.cpp:2155-2175`, `:5470-5472` |
| the page's shape comes from the engine's cached `state.selection` | confirmed | `editor-shell-v2/narrow-editor-v2-session.js:121-133` |
| 0.2.12's page chooses delete-selection at `beforeinput` from the snapshot; no rule A, no click-then-move, no Shift drop | confirmed | `git show 7fb0ed08:wasm_sdk_probe/web/e2-editor-app.js` (sha256 `8909564eb2316afa…`), lines 2224-2231 |
| 0.2.12's identity (page, shell, host, engine v19, counted) | confirmed | `handoff/HANDOFF-2026-10-12-0.2.12-counted-hand-test-next.md:9`, `:19`; `specs/SPEC-M3-autosave.md:633-641` |
| 0.2.18's page drops Shift, routes range moves through click-then-move, chooses the delete form at `beforeinput` | confirmed | `web/e2-editor-app.js:2596`, `:2609-2615`, `:2403-2421` |
| finding 135's silences: 196.6–210 ms, 4 of 21 runs | confirmed | `findings/135-…md:9`, `:16`, `:20` |
| the merge path's key-plus-undo-payload method and its native record | confirmed (prior rulings) | `specs/SPEC-M3-paragraph-merge.md:48-77`, §17, §24; `probe_engine.cpp:6058-6080` |
| the main-loop engine profile makes keys synchronous (unipoll) and is excluded from the merge build | confirmed | `probe_engine.cpp:15-16`, `:6171`, `:6426-6441`; `lokhelper.cxx:1282-1288` |
| the executor's "fence distinguishes items 1 and 4" | confirmed by the traces (K1's anchor side is not at P in both) | `merge_key_undo.hpp:140-150`; traces 1 and 4 |
| frequency of core-thread silences on the product | not measured anywhere beyond 135's one cell; stated as such |
| the Delete key on a range equals `.uno:Delete` in Writer, and one undo action results | not checked; a native-round item of the next spec, never a premise here |

## CONDITIONS

29. §12.2's flag is withdrawn as a closure; §10.4/§12.4 (resolver), S1–S5, R1, S-12 and §12.5's widening are deferred with items 1 and 2; the two struck claims (12.2's "every stacked sequence refuses", the "three coincidences" residual) are struck in an appended section that cites the traces.
30. This link's scope is items 3, 4, 5(2) and K; editor ABI 4; manifest moves `collapsed`-only; the page's delete routing unchanged; the relink and the count proceed on that scope.
31. One finding is registered for items 5 and 6, reachable on 0.2.12 and 0.2.18, with the model's two traces as evidence, the precondition and severity as written above, "not inducible by any runner" stated, and closure assigned to the ordered-deletes spec; no interim page or engine patch.
32. The executor re-runs the model with v20's offered keys only (plain caret-start moves; no extend; no range-start move) and attaches the printed Writer-divergent population to the finding; the pinned `REPORTED` counts are replaced by that run's; any Writer-divergent kind outside items 5/6's class stops the relink.
33. Before the next spec, the model gains "typing behind a pending key" and "inline format behind a pending key"; reported, not ruled.
34. The ordered-deletes spec names candidates A, B and C, measures the chosen one natively first, passes the model before any wiring, and carries Shift+Arrow and range-start moves; its first review's fixed questions are: a sequence in which a FIFO key's undo-payload proof is satisfied by a different change; a key that does nothing and how the page is told; a table or inline-object case where the key differs from today's refusal.
35. C ships as §10.5 minus the flag clauses; C1 per-completion criterion and L-C-late-K1 stand; no deadline is added to `AwaitingDeleteCompletion` in this link.
36. Defaults: if 32 is never run, the relink waits; if 31 is never registered, the count's release text must still name items 5/6 as a known data-changing class on both releases; if 34 is never written, Shift+Arrow does not ship on any profile.

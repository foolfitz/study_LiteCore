# Review 1 — SPEC-M3-link-batch at `b5f2e812` (adversarial, before any engine code)

Reviewer: opus, brief `findings/evidence/link-batch/review/brief-1-spec.md`. Every claim below was checked against the tree at `ca48673a`; line numbers are from that tree. Nothing was built or run. Scope rule (§34): only criteria that would let a broken product pass an honest run get remedies that add checking; everything else aims at the design.

## SUMMARY

Counts: **BLOCKING 3, SHOULD 12, NOTE 11.**

- **B1 (§9, S2).** The new completion rule ("complete an extend, and a move from a range, on the first `INVALIDATE_VISIBLE_CURSOR`") does not tie the callback to the dispatched key. The native facts §9 rests on ("exactly one CUR, always last") are properties of one LOK flush by construction (`init.cxx:736-758`, `2395-2420`, `2485-2486`), not of one key. The engine already has completions that end before their own flush: insert-text is synchronous, the merge key completes by polling, and every 250 ms readback. `postKeyEvent` is asynchronous, so an earlier flush can land after `gEditorPending` is set and before the key runs. This repo has already rejected this exact rule twice: SPEC-M3-paragraph-merge §3.2/M1-2 (the red case "first cursor callback after posting") and the §16.1 ruling ("any rectangle change can forge a cursor"; idle spell-check repaint on this core hits "type then immediately Delete"). S2 measures isolated cells after an 800 ms quiet period, so it passes while the product is wrong.
- **B2 (S1–S4, §4.1 page).** No criterion covers what a user does with a keyboard selection. The page decides between `delete-backward` and `delete-selection` from its snapshot when `beforeinput` fires, and an extend that is still in flight is not in that snapshot. "Shift+End, Backspace" at typing speed therefore reaches the gate with the wrong action and is refused (121's symptom; 131 is the same class). All of S1–S4 pass.
- **B3 (§4.4, C1).** C's safety readback is taken after the deadline has already read NONE. It cannot see a K1 that has not run yet: K1 is a posted async event, and nothing in the engine learns when it runs. "Collapse back to the pre-barrier caret" names no LOK mechanism. The only synchronous option (`setTextSelection` RESET) runs before a queued K1 and is then undone by it. C1's busy arm waits for a `late-selection` flag that, by construction, is almost never raised. Today a late K1 dies with the reopened worker; under C it lands in a live session.
- SHOULD, in short:
  - The worker also refuses extend on line moves, and v19's worker is a frozen copy (S-1).
  - Widening the manifest switches the page's 129 branch by itself, so Q-C's "conservative" option and R1's default both need new page code (S-2).
  - S2 does not cover the 24 range-start plain moves whose completion §9 changes (S-3).
  - S2's "active readback" of the caret is not implementable (no LOK cursor getter). §9's "state still right, only slow" is false when the CUR is late rather than absent (S-4).
  - The prediction lists 16 cells, not 18 (S-5).
  - S1 has no verdict for a cell that differs from native, and its Up/Down/Home/End cells depend on fonts (S-6).
  - E1's population (`kStages`) leaves out the `finishSelectionBarrierError` exits that §4.5(1) names, including a known reachable one (Backspace after a tab) (S-7).
  - `caretBefore` read from the cache is stale after a poll-completed merge, and E2's oracle shares that staleness (S-8).
  - C also turns "Delete at the document end" into a no-op, which turns existing 134/136 guard arms red by design (S-9).
  - The page-number criteria: M is tautological, the page-centre oracle depends on the viewport, and P2's trigger is a paint that may never come (S-10).
  - The page-rectangle call needs a manifest gate for the v8/v14 control runs (S-11).
  - A held Shift+arrow keeps extending after key-up (S-12).
- Verified true: the coupling claim (the gate reads only the action: `probe_engine.cpp:5285-5300`), the §3 citations, the v19 "first TEXT_SELECTION" behaviour, and that the red-on-v19 prediction can be derived from the LOK flush order (for 16 cells). Writer's page rule (`viewsh.cxx:2964-2995`) is read correctly. The Collabora read-only claim is overstated (N-1).
- No `.md` or source file other than this one was edited.

## BLOCKING

### B1 — §9's completion rule accepts a cursor callback that the dispatched key did not cause; S2 cannot see it

**Claim attacked.** §9 "定案": an extend, and any move whose start is a range, completes on `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`. The basis is "every cell has exactly one SEL and one CUR, and CUR is always last" (10-13h). S2 is the guard.

**Evidence.**
- What the native facts are. In 26.8, `TEXT_SELECTION_START/END/TEXT_SELECTION` are "updated types" and `INVALIDATE_VISIBLE_CURSOR` is a per-view updated type (`desktop/source/lib/init.cxx:736-758`). They are kept as flags, and their payloads are fetched only at flush time ("Append messages for updated types, fetch them only now", `init.cxx:2485-2486`). They are appended in a fixed order, SS, SE, SEL, then the per-view CUR (`init.cxx:2395-2420`). The engine's own merge code says the same (`merge_key_undo.hpp:186-190`). So "one SEL, one CUR, CUR last" holds **per flush, by construction**. The native run measured one key per freshly loaded document after 800 ms of quiet, which is one flush per arm. Its README says the interleaving with the engine's pending logic "is not measured here".
- Nothing correlates the completing callback with the key. `completePendingEditorOperation` (`probe_engine.cpp:2155-2175`) checks only the callback type against `requiredCallback`. It is called for every parsed callback (`:2655`). `beforeSequence` is only reported, never compared.
- The key runs later than the dispatch. `SwXTextDocument::postKeyEvent` → `SfxLokHelper::postKeyEventAsync` (`sw/source/uibase/uno/unotxdoc.cxx:4009-4013`, `sfx2/source/view/lokhelper.cxx:1294-1311`). Callbacks are delivered on LOK's own thread while the engine thread dispatches. The merge spec's §16.1 established this (`svpinst.cxx:130-149`, `init.cxx:4813`).
- Some completions end before their own flush:
  - `handleInsertText` answers `inserted` synchronously after `paste()` and waits for no callback (`probe_engine.cpp:3186-3221`). This is the typing path.
  - The merge key completes by polling `.uno:Undo`; the source says "the completion may now be sent between the key's KEYINPUT and KEYUP" (`:6061-6071`).
  - All three 250 ms readbacks (`:2300-2330`). The 096 comment: "The late callback then arrives with gEditorPending cleared".
- The repo has rejected this rule before:
  - SPEC-M3-paragraph-merge §3.2 (`specs/SPEC-M3-paragraph-merge.md:80-90`): a key's evidence may only be a cursor that **differs** from the cursor known at dispatch.
  - M1-2 (`:119`) uses "送出之後的第一個游標回呼" as its red case.
  - §15.1 (`:499`): the first counterexample found is "事件已處理、它的 flush 跨到交易開始之後＝打字後立刻 Delete".
  - The §16.1 ruling (`:526-533`): "任何矩形的變動都能偽造一個游標"; idle spell-check repaint is alive on this core (`config_wasm_strip.h` has `ENABLE_WASM_STRIP_HUNSPELL 0`; `layact.cxx:2169-2175` calls `InvalidateWindows`). I did not trace whether `InvalidateWindows` itself flags a CUR. The ruling treats it as possible, and §9 does not.

**Failure scenario.**
1. The user types "abc" and presses Shift+Home within one flush interval.
2. The insert has already completed. Its flush (CUR = the caret after "abc", no selection change) is delivered after the extend's `gEditorPending` is set and before the Shift+Home key runs.
3. The extend completes with a collapsed selection and the old caret. Its own SEL+CUR arrive afterwards, with the slot already cleared.
4. The page's snapshot says "collapsed" until the push arrives. An immediate Backspace is routed wrong (B2).

The same happens with "Backspace that merges, then Shift+Right" (the poll completion) and with any idle repaint during a held Shift+arrow. A range-start plain move (also switched to CUR) has the same exposure. In the opposite direction, a stale "range" cache makes §9 wait for a CUR, which the pending flush supplies.

**Why S2 passes.** Its population is the native Shift cells, each run alone on a settled document. The interleavings above never occur in it.

**Remedy (narrow).**
- (i) Accept the CUR only after a `TEXT_SELECTION` whose payload differs from the selection cached at dispatch. This is the merge spec's transition rule, and it holds in all 98 changing native cells: P-a says no cell changed the selection without one, and for the 24 plain-on-range cells SEL0 differs from the range. Cells with no change keep the 250 ms readback.
- (ii) Add to S2's population: insert text then Shift+key with no wait; a merging Backspace then Shift+key; Shift+Right held for 1 s. Run them through the existing product-page runner. Alternatively, exercise the rule in the existing `tests/merge_key_undo_model_test.cpp` sequence generator, which already models FIFO, flush coalescing and events that straddle a transaction start. That reuses existing machinery and adds none.

### B2 — No criterion covers the follow-up to a keyboard selection; the page routes Backspace and Delete from a snapshot taken mid-flight

**Claim attacked.** S1–S4 as the complete gate for item 1. §4.1 says "工具列與 `lastSelectionShape` 讀引擎回報的狀態".

**Evidence.**
- `beforeinput` computes `shape = selectionShapeOf(session.state.snapshot.editorState)` and picks the action at that moment (`web/e2-editor-app.js:2408-2414` → `deleteActionFor` `:2403-2406`).
- Moves are fire-and-forget (`void editorAction(action)`, `:2615`). The only in-flight guard is `deletesInFlight`, for deletes.
- In v19 the gate refuses `delete-backward` on a range and `delete-selection` on a caret (`probe_engine.cpp:5285-5300`). In the manifest, `delete-backward` gets `["collapsed"]` and `delete-selection` gets `["range-single","range-cross"]`.
- Finding 131 is this race class for deletes (the comment at `:2394-2402`).

**Failure scenarios.**
- Shift+End, then Backspace about 50 ms later, while the extend is still out. The shape is `collapsed`, so `delete-backward` is queued and runs after the extend. The engine now has a range, so the gate refuses: a toast and nothing deleted. This is 121's symptom through keyboard timing.
- Shift+Left on a one-character range collapses it (native P-c, `SEL0 CUR`). A quick Backspace then goes out as `delete-selection` on a caret and is refused.
- With B1, the window is longer than the engine's own latency.

Every S criterion passes, because none of them presses a second key.

**Remedy.**
- Page: choose the delete form when the queued item runs, after earlier moves and extends have completed, or count moves and extends in flight like `deletesInFlight`.
- Criterion S5 (form 2 over S1's cells): from each Shift cell's start shape, press Shift+key immediately followed (no wait) by Backspace, by Delete, and by one typed character. Compare the saved document with Writer's for the same sequence. Default if never done: the page does not send `extendSelection`.

### B3 — C's late-Shift guard is read at the wrong moment and its "collapse back" has no mechanism; C1 cannot see the failure

**Claim attacked.** §4.4: "完成之前引擎讀回選取：若不是 NONE（晚到的 Shift），先收回成 barrier 之前的游標再完成；收不回就照今天拒絕". C1's busy arm: "若在 12 次裡出現 `late-selection`，照實記，不判失敗".

**Evidence.**
- `nothing-selected` is raised in `rejectSelectionBarrierAtDeadline` right after `readSelection()` returned NONE (`probe_engine.cpp:3843-3861`). The source comment says that 250 ms of NONE "can also be a Shift press not run yet" (`:3859-3860`).
- A second read at completion happens microseconds later and sees the same NONE. A K1 that has not run is still in VCL's posted-event queue (`unotxdoc.cxx:4011-4012`), and the engine has no signal for when it runs.
- No LOK operation is named for "收回":
  - `setTextSelection(LOK_SETTEXTSELECTION_RESET, x, y)` is synchronous (`unotxdoc.cxx:4066-4067` → `SwEditWin::SetCursorTwipPosition`, a coordinate hit-test, so L-129's wrapped-line-end ambiguity applies). It executes **before** the queued K1, which then re-selects.
  - The E-shape (`.uno:Escape`, reverse Shift+key, `.uno:Escape`) is asynchronous and has its own failure stage (`return-mismatch`; L-136-rule-iii-residual).
- `late-selection` would only be set when K1 runs inside that microsecond window, so C1's busy arm will read 0 whether or not C is broken.

**Failure scenario.** Mid-document Backspace while the worker stalls longer than 250 ms (finding 135's ~200 ms stalls, 096's 37–39 ms per key).
- Today: `nothing-selected` → reopen. The late K1 dies with the disposed worker.
- Under C: success, `changed:false`. K1 runs later and selects the previous unit in the live session. The next typed character replaces it, or Delete removes the wrong unit, or Ctrl+B formats it.

At the true document start or end a late K1 selects nothing (native P-b), so the start-press case C targets is safe. The risk lies entirely in the other `nothing-selected` cases.

**Remedy.**
- After the first NONE, keep the transaction open for a bounded window (`MergeStepDeadlineMs`, which already exists).
  - If a non-empty `TEXT_SELECTION` arrives in the window, refuse as today (`unit-late`, reopen). The live session then never holds a late selection.
  - Complete as a no-op only if nothing arrives. The residual (K1 slower than the window) becomes a named limit.
- Drop "收回成 barrier 之前的游標" from C.
- C1's busy arm becomes a criterion: after every no-op completion, `editor-get-state` at ≥ 500 ms reads `selectionType` NONE (form 1, per completion). If it does not, C fails.

## SHOULD

### S-1 — Item 1's scope omits the worker, the profile builder and three pins; v19's worker is a frozen copy

**Claim attacked.** §2 row 1 ("ABI、引擎、manifest、client、頁面") and §4.1.

**Evidence.**
- `sdk/sdk-worker.js:132-135`: `EDITOR_V1_MOVE_ACTIONS` holds the two character moves. `:1404-1410`: `editorActionV2` rejects `extendSelection: true` for any other action with `INVALID_ARGUMENT`.
- v19's worker is `$(E2_V15_ARCHIVE)/sdk-worker.js` (`wasm_sdk_probe/Makefile:1489`, `:1507`).
- The profile builder has `ABI_VERSION = 4` and `limits: ["no-extend-selection"]` (`tools/build_e2_editor_v4_profile.py:81`, `:100-103`).
- Pins:
  - `tests/test_e2_editor_v4_profile.py:38-42` ("was widened without a measurement", covering the two character moves) and `:109-111`.
  - `tests/editor_abi_header_test.cpp:20` (`== 4u`).
  - `src/editor_api.cpp:78-81` (`isMove`).
  - `narrow-editor-v2-client.d.ts:72`.

**Failure scenario.** Shift+Up/Down/Home/End are refused in the worker. S1 goes red honestly, so this is not blocking. But the link plan (§6, the "Makefile changes shown to the owner" step) and the new worker hash are not planned.

**Remedy.** List the worker (a new build, not the v15 copy; item 3 needs a new one anyway), the builder and the three pins in §2. Give the move widening an evidence field like v19's `inlineRangeEvidence`.

### S-2 — The coupling is true, but the page's 129 branch is manifest-driven, so Q-C's "conservative" option and R1's default need new page code

**Claim attacked.**
- §3: "第 1 項與第 2 項在引擎端是同一件事，分開的只有頁面送不送".
- Q-C: "頁面可以先維持 0.2.13 的處方".
- R1's default: "頁面保留 0.2.13 的處方".

**Evidence.**
- The gate uses `action` only. `command.values[1]` (extend) is never read there (`probe_engine.cpp:5285-5300`). So the claim is true.
- The page takes `moveFromPoint` only when `!gestures.includes(shape)` (`web/e2-editor-app.js:2609-2615`). Once v20's manifest grants the range gestures, that branch is dead and plain moves on a range go straight to Writer **with no page change**.
- Also:
  - The toolbar ◀ ▶ (`web/e2-editor.html:266-267`) become enabled on ranges (`updateGestureAffordance`, `:877-881`).
  - The guard chain's 129-B (`tools/probe_129_m4_wasm.py`, part of the count list in §7) would measure Writer's own move on v20, not the page fix it was written for.
- The coupling is a property of today's gate, not a law. This link edits the engine anyway, and an (action, extend) check would decouple the two items.

**Remedy.** Rewrite Q-C and R1's default to name the page change they need, or decouple in the gate. In §7, say that 129-B is retired on v20 and replaced by R1.

### S-3 — S2's population leaves out the 24 cells whose completion §9 changes

**Claim attacked.** S2 "同一組格" (= S1's "每一個「Shift＋鍵」格"), and §9 "起點是範圍的移動…完成條件改成 CUR".

**Evidence.** §9 changes the completion for the 24 plain-key-on-range cells (native Table 2, all `SEL0 CUR`). R1 checks only where the caret lands.

**Failure scenario.** A range-start move completes stale (B1, or a CUR from another flush). R1 passes because the landing is right, and S2 never looks.

**Remedy.** S2's population = Table 1 ∪ Table 2, both taken from the native `arms-r*.jsonl` (tool-closed).

### S-4 — S2's "engine actively reads back the caret" is not implementable; §9's "still right, only slow" is false when the CUR is late

**Claim attacked.**
- S2: "等於完成後 500 ms 由引擎主動讀回的游標與選取".
- §9: "若 WASM 上出現「有選取回呼、沒有游標回呼」的格，它也會在 250 ms 讀回完成，狀態仍是對的、只是慢".

**Evidence.**
- `LibreOfficeKit.h` has no cursor getter. Writer's `getCommandValues` list (`sw/source/uibase/uno/loktxdoc.cxx:1189-1227`) has none either.
- `editor-get-state` (`probe_engine.cpp:5701-5721`) actively reads only `selectionType`/`selectionText` (`readSelection`). The caret and the rectangles come from the callback cache (`appendEditorState`, `:1220ff`).
- `verified-move-readback` serialises the same cache (`:2300-2330`); it is not a LOK read.
- Because SEL and CUR come out of the same flush, a SEL without a CUR at 250 ms means either "Writer did not flag the cursor" (correct) or "the CUR is late" (the completion then carries the new selection and the **old** caret).

**Failure scenario.** A CUR arrives after 250 ms (a stall). The completion is stale, yet §9 calls it correct.

**Remedy.**
- Reword S2 as "the cache at completion = the cache at completion + 500 ms (`editor-get-state`)". Add the one available active cross-check: the completion's `selection.collapsed` agrees with `getTextSelection` type and text at +500 ms.
- Strike §9's "狀態仍是對的". S3's judge records whether a CUR arrived after the readback.

### S-5 — The v19 prediction has 16 cells, not 18

**Claim attacked.** §9: "原生清單裡「起點是游標、Shift＋左／右、選取有變」的 18 格（…）… 若有任何一格是綠的…不往下做".

**Evidence.**
- The cells listed sum to 2+1+1+2+2+2+2+2+2 = **16**.
- The nine caret shapes × Left/Right make 18. The two not listed, `shift-Left@doc-start` and `shift-Right@doc-end`, have no callback (Table 5). On v19 they complete by `verified-move-readback` and are **green** under S2.
- The prediction itself follows from the source for the 16:
  - v19 completes an extend on SEL (`probe_engine.cpp:5470-5472`).
  - Completion runs inside the SEL callback (`:2655`) before the CUR of the same flush has updated the cache (`init.cxx:2395-2420`).
  - On v19 the gate admits caret starts, and the client and worker accept extend for the character moves.

**Failure scenario.** A judge built from the count "18", or from the description, includes the two boundary cells. Two greens follow, and the stop rule halts work for nothing.

**Remedy.** Write 16. Name the source as "Table 5's last-CUR-after-last-SEL list ∩ caret shapes ∩ {Left, Right}". Also say that on v19 the cells are driven through the SDK client, because the v19 page drops Shift (`e2-editor-app.js:2596`). S1/S2 on v20 use the product page, so the pre-red exercises the judge, not the v20 path.

### S-6 — S1 has no verdict for a differing cell; native text is font-dependent for most of its cells; the WASM shapes are unspecified

**Claim attacked.** S1: "引擎讀回的選取文字與原生的 `getTextSelection` 逐字相同；不同的格要列名，不得以比率帶過".

**Evidence.**
- Up/Down move to the point's column, and Home/End on the wrapped and CJK paragraphs depend on line breaking. WASM fonts (`cjk-sub-e10`, `base-r5-no35`) are not the native host's.
- The native shapes come from a key-walk discovery and a click at the discovered rectangles (README, "How this was measured"). S1 does not say how the WASM shapes are built or checked.

**Failure scenario.**
- Either many cells differ for font reasons, and the run is red or "listed" with no rule.
- Or a real defect (Shift+Down extending one line too far) is listed next to the font cells and ships.

**Remedy.**
- Add a verdict and a font-independent oracle for each cell on WASM: after Shift+key from shape S, the anchor is unchanged and the moving end equals the caret the plain key reaches from S's point (separate fresh arm).
- Keep exact native text only for layout-independent cells (Left/Right; Home/End on one-line paragraphs).
- Require shapes rediscovered by the same key walk, with the pre-key text checked as native did.

### S-7 — E1's population is a hand list relative to §4.5(1); the measured property is mostly invisible after a reopen

**Claim attacked.** §4.5(1) "每一個拒絕出口（`finishMergeKeyError`、`finishSelectionBarrierError`）", and E1 "（工具封閉）merge 的 stage 表… 每一個 stage".

**Evidence.**
- `kStages` (`merge_key_undo.hpp:220-226`) covers only `finishMergeKeyError` (`probe_engine.cpp:3378-3408`).
- `finishSelectionBarrierError` (`:3324-3334`) is called at `:3419`, `:3425`, `:3439`, `:3495`, `:3827-3830` and `:3888-3895`. At `:3827` and `:3888` it passes `viewRecoveryRequired = selected.type != NONE`, which means "the barrier's own selection is left".
- One of these is a known, reachable refusal: Backspace right after a tab or an inline object. `classifyUnit` returns `Refused` (`merge_key_undo.hpp:61-70`), so the unit is not merged, `textSafe` is false, and the exit is `:3827`. SPEC-M3-paragraph-merge `:53-54` records it as "照舊拒絕".
- `nothing-selected` is in `kStages`, but C turns it into a success.
- Every `EDITOR_BOUNDARY_UNSUPPORTED` reopens the worker (`e2-editor-app.js:1653-1655`, `:1674ff`). "引擎讀回選取為 NONE" after the refusal therefore has to be read from a worker the page is disposing. If E1 does not say how, it reduces to trusting the refusal JSON's own `selectionLeft`.
- For key-posted stages, "收回成 barrier 之前的游標" is ill-defined: the key may have changed the layout.

**Failure scenario.** Backspace after a tab leaves the tab selected and refuses. E1 passes because that exit is not a stage.

**Remedy (narrowest).** Limit §4.5(1) to C's no-reopen path, the only path where a left selection survives. D already reads `caretBefore` (E2) on the reopen paths, so collapsing there buys nothing. This also takes one engine behaviour change out of the riskiest barrier (N-9). If it is kept, take E1's population from the source's call sites, not from `kStages`.

### S-8 — `caretBefore` from the cache at barrier start is stale after a poll-completed merge; E2's oracle shares the staleness

**Claim attacked.** §4.5(2): `caretBefore` = "barrier 開始那一刻引擎快取的游標矩形與 `sourceSequence`". E2: "等於送出那一下之前引擎回報的游標".

**Evidence.**
- A merge completes by poll before its key's flush (`probe_engine.cpp:6061-6071`).
- With H2 (`e2-editor-app.js:2620-2638`) the next held press is already waiting, so `startSelectionBarrierDelete` (`:3996-4049`) captures the pre-merge cache.
- "Reported before the press was sent" is page time. Held-key §17 records that 0.2.17's FIFO failed on exactly this, off by one unit.
- The merge attribution already holds a fenced P: "the caret where K1 ran" (`merge_key_undo.hpp:140-150`, `fenceHolds`).

**Failure scenario.** A held Backspace merges, then the next press is refused (for example `anchor-mismatch` at a cell start). `caretBefore` is the pre-merge caret, and E2 compares it with an equally stale "reported before send" value and passes. D then puts the caret a paragraph off.

**Remedy.**
- Make `caretBefore` = the attribution's P when it is established, otherwise the cache, with a `source` field saying which.
- E2's oracle = K1's anchor rectangle from the same transaction.
- Add a held-press arm across a merge to E2.

### S-9 — C also covers Delete at the document end; existing 134/136 arms are red on v20 by design and §7/K does not say so

**Claim attacked.** §2 row 4 / §4.4, which speak only of "段首 Backspace". K: "計數鏈在最終位元組上全過".

**Evidence.**
- Delete's K1 is Shift+Right. At the document end it produces no callback (native: `shift-Right@doc-end`), so it ends in `nothing-selected` by the same path.
- Arms whose expectations encode that refusal:
  - `end-hold` ("拒絕 1 次、世代 ['1','2']");
  - `end-press-type`;
  - `restore-window` ("每輪拒絕 1 次、世代 1→2");
  - `start-hold` (SPEC-M3-held-key §14, §15, §17).
- `boundaryText`'s `nothing-selected` sentence and B's `deleteRefusedThisHold` become unreachable at the start and end.

**Failure scenario.** K goes red on correct v20 bytes. The only ways to green are editing judges after seeing the run (forbidden by §34 without a witness report) or leaving 127–136 uncounted.

**Remedy.** In §7, before the run, name each arm whose expectation changes under C and its new expectation (0 refusals, generation `['1']`, document unchanged, caret unchanged), with a witness report.

### S-10 — Page number: M is tautological, the page-centre oracle depends on the viewport, and P2's trigger may never fire

**Claim attacked.** §4.3 "之後只在 paint 回覆帶 `documentSizeChanged: true` 時重讀"; P1 "M 是矩形數 … 另記原生的頁數，不比對（字型可能不同）"; P2 "下一次 paint 之內 M 加 1".

**Evidence and scenarios.**
- (a) The status bar's M and P1's expected M both come from `getPartPageRectangles`, so an incomplete list passes. The 60-page fixture's count does not depend on fonts: `tools/create_long_document.py` header, "Page count is made exact … `fo:break-before="page"`". Native rounds also agree with `getParts()` (page-rectangles README).
- (b) The spec's own rule counts every page whose whole rectangle overlaps the view. When the viewport is taller than a page plus its gaps (a landscape A4 at fit-width in a tall window), the centre of page k shows k−1..k+1. "第 k 頁" is then wrong, and the run goes red, or someone tunes the viewport afterwards.
- (c) `documentSizeChanged` exists only on a paint reply (`probe_engine.cpp:3125-3149`).
  - Writer's page count changes after the edit's synchronous part: native `DOCUMENT_SIZE_CHANGED` comes 1.3–1.8 ms later, and later still on WASM.
  - Under C′, off-screen invalidations are not painted.
  - So if the in-view paint wins the race, no later paint reports the change, and M stays stale until some unrelated paint. P2 is then vacuously "within the next paint".
  - A shrink has the mirror form: the canvas is resized on the reply while the rectangles are old.
- (d) Recomputing "only on scroll" misses window resize, devicePixelRatio and zoom changes (the page has a resize handler, `e2-editor-app.js:2845`), and a worker restart (reopen, B1).

**Remedy.**
- Assert M = 60 for the 60-page fixture, and build the mixed fixture with hard breaks so its count is declared too.
- Fix the viewport below the minimum page height minus two gaps, or compute the expected N–L from the rule independently in the runner.
- Re-read the rectangles when `documentChangeSequence` advances (`INVALIDATE_TILES` already bumps it, `probe_engine.cpp:2632-2633`; the call costs < 0.03 ms natively), or forward `DOCUMENT_SIZE_CHANGED`.
- P2 = M is correct 2 s after the edit with no further input, plus a page-removal case.
- Recompute on resize and restart.

### S-11 — The new SDK call needs a capability gate; the page runs on other profiles

**Claim attacked.** §4.3 SDK and page: "開檔後讀一次".

**Evidence.**
- The product-path net runs the same page against v8 and v14 through `--profile` (`tools/run_e2_c_product_path.py:4554ff`).
- Redo is the precedent: it is a compiled export, gated by a manifest field and `offersRedo()` (`narrow-editor-v2-client.js:233-238`, `e2-editor-app.js:939-953`).

**Failure scenario.** An unconditional `pageRectangles()` reaches a missing export on the v8 and v14 controls, and the control arms die.

**Remedy.** Declare a manifest field and an `offers` gate in §4.3. Also say which ABI the export belongs to (N-7).

### S-12 — A held Shift+arrow keeps extending after key-up

**Claim attacked.** §4.1 page: the six keys with `shiftKey` send `extendSelection: true`. No criterion covers holding the key.

**Evidence.** `dropsHeldRepeat` limits only Backspace and Delete (`e2-editor-app.js:2632-2638`). 132's baseline: a held delete went on for 1.8 s after key-up. An extend costs about one WASM key round trip (37–39 ms for a plain move, 096) against a 30 ms repeat.

**Failure scenario.** The user holds Shift+Right, releases at the word they want, and presses Delete. The queued extends have widened the selection past the release point, and more text is deleted than was highlighted at key-up.

**Remedy.**
- Apply 132's depth rule to moves and extends.
- Criterion (form 1, per hold): Shift+Right held 2 s; after key-up the selection grows by at most the extends that were in flight at key-up. Default if never done: holding Shift+arrow is a named limit in the release text.

## NOTE

- **N-1 (§4.3, Collabora).**
  - `Parts.js:307-322` (`_resolveCurrentPage`) only picks the source page for prev/next navigation in non-edit mode. The read-only status string is set only in `goToPage` (`Parts.js:344-354`). Collabora has no scroll-driven client-side page number. In edit mode the status bar shows core's string (`Control.StatusBar.js:681-683`, `:161-164`).
  - The client rule in §4.3 is Writer's (`viewsh.cxx:2964-2995`), adapted. Besides L-page-margin:
    - Writer writes "Pages 3 and 4 of 18" for exactly two pages (`view2.cxx:1904-1905`, `STR_PAGES_TWO_CONJUNCTION`).
    - Writer's `Overlaps` includes x.
    - Writer trims a later page's bottom margin only `if Top() > 0` (`:2975`).
- **N-2 (a11y).** v20's core is a11y-stripped (`wasm-lite/build-headless-probe/config_host/config_wasm_strip.h:5`), so no A11Y callback can interfere here. The next step (the writer+calc a11y core) relinks the same source, so S2 must be rerun there. Extend completions do not call `refreshCaretParagraph` (only the caret and readback paths do, `probe_engine.cpp:2180`, `:2241`, `:2311`). On an a11y core, an extend completion's `a11y` block can therefore describe the previous paragraph.
- **N-3 (existing race, not introduced).** `gEditorPending` is written on the engine thread without a lock (`probe_engine.cpp:5466-5502`) and consumed on the LOK thread (`:2155-2175`). The deadline path checks and then clears it on the engine thread (`:5940-5946` → `:2300-2306`). A CUR landing at the 250 ms deadline can produce two completions for one request. §9 makes extends depend on the same handoff. S2's judge should flag duplicate completions.
- **N-4 (out of scope, register).** Backspace after a tab or inline object is refused via `finishSelectionBarrierError` with no `mergeKey`. The page then says "目前還不能在段落交界刪除（把兩段合併成一段）" (`e2-editor-app.js:1625`, `:1664-1667`), which is the wrong sentence, and spends a Worker generation.
- **N-5 (S3).** S3 pins the completion name `verified-move-readback`. If WASM emits a CUR for a key that changes nothing, S3 goes red while the product is fine. That is an honest red, not a pass.
- **N-6 (P3).** A paint during the scroll that legitimately reports `documentSizeChanged` triggers a re-read. Exclude re-reads triggered that way from the count of zero.
- **N-7 (ABI 4→5).**
  - The worker's exact match (`sdk-worker.js:1153-1161`) means every later relink of this source (the core switch) must declare 5.
  - The e1 profiles are frozen and unaffected.
  - The Document SDK ABI (packed major/minor, `:1137-1144`) stays untouched only if `page-rectangles` is an editor export. Say which.
  - If it ever becomes an *action*, `kMaxExternalAction` (`editor_api.cpp:65`) and `kMaxInternalEditorAction` (`probe_engine.cpp:6817`) must move together (AGENTS.md, "界限要跟著清單走").
- **N-8 (owner's scope).** Nothing from handoff 10-13d addendum 2 is missing. Not in scope and silently not taken: Ctrl+Shift+arrows (`if (accel) return;`, `e2-editor-app.js:2586`), Shift+click, Shift+PageUp/PageDown. Say so in the release text.
- **N-9 (one variable per link).** §9, the manifest widening, C and 5(1) are four behaviour changes. Two of them sit in the barrier that produced 109/119/133/134, which makes attributing a red in the count chain expensive. Dropping 5(1) (S-7) costs no user-visible behaviour; 5(2) is pure data.
- **N-10.** E3's "誘發不了→登錄" with its default is acceptable. S4's (b) and (c) test one mechanism on the product: the page's drag is `setTextSelection` START/END, the same as (c).
- **N-11.** Shift+Right at a cell end leaves the cell (native `SEL CUR`, a table selection). That shape was reachable by dragging and is now one key away. `delete-selection`'s v19 limit `not-characterised-in-tables-or-note-apparatus` then applies after a single keystroke. Mention it in the release text.

## Criteria: form, default, honest pass while broken

| criterion | form (AGENTS.md §1) | default written | honest run passes while broken? |
|---|---|---|---|
| S1 | 2 (native arms) | yes | yes: no verdict for listed cells (S-6) |
| S2 | 2 | yes | yes: isolated cells only (B1), misses Table 2 (S-3); "active readback" unimplementable (S-4) |
| S3 | 2 (native no-callback list) | yes | no (over-constrained, N-5) |
| S4 | 2 (native interaction arms) | yes | yes for keyboard follow-ups (B2), which it does not cover |
| R1 | 2 (129 cells) | yes, but not executable without new page code (S-2) | no |
| P1 | 2 for positions; M is self-referential | yes | yes: M from the same call (S-10a) |
| P2 | 1 (single instance) | yes | yes: vacuous if no paint follows (S-10c) |
| P3 | 1 | yes (not blocking) | no |
| C1 | 2 (start-press only; busy arm is not a criterion) | yes | yes (B3) |
| E1 | claimed 2, actually 3 relative to §4.5(1) | yes | yes (S-7) |
| E2 | inherits E1 | yes | yes (S-8) |
| E3 | 1 | yes | no |
| K | 2 (the chain's own lists) | yes | n/a; red by design without S-9 |

# Review 3 — SPEC-M3-link-batch §10 only (focused, bounded; opus, adversarial)

Brief: `findings/evidence/link-batch/review/brief-3-focused.md`. Subject: `specs/SPEC-M3-link-batch.md` §10 as committed in `66e39525`; §10 is byte-identical at `edf3d643` (the only later change to the spec is the appended §11, which is out of scope). No file under `wasm_sdk_probe/`, `libreoffice-26-8/` or `tools/` changed between the ruling's tree (`93b8df21`) and `edf3d643` (`git diff --stat 93b8df21 HEAD -- wasm_sdk_probe libreoffice-26-8 tools` is empty), so every line number below is valid for the ruling's tree too. Nothing was built or run. No file other than this one was written. Limits: SPEC-M3-paragraph-merge §34; remedies add checking only where a criterion would pass a broken product in an honest run.

## SUMMARY

Verdicts: **Q1 COUNTEREXAMPLE, Q2 COUNTEREXAMPLE, Q3 SHOULD, Q4 COUNTEREXAMPLE (+SHOULD), Q5 COUNTEREXAMPLE.**

- **Q1.** Two completion paths emit before their own `TEXT_SELECTION` reaches the cache, and neither is in L-extend-prior-flush's written population. (A) Every `uno-command-result` completion (delete-selection, the four inline formats): LOK queues `UNO_COMMAND_RESULT` at dispatch and appends SEL/CUR only when the flush runs (`init.cxx:5106` vs `:2485`). (B) The product's select-range: three synchronous `setTextSelection` calls; RESET's `SEL0` can complete it before START/END run. Both windows are narrow and the effect is the named one. The fix is to let the model test's printout define the population, with these two event shapes added to its LOK model. That printout is a tool-closed list; the prose population is a hand list.
- **Q2.** The anchor fence only runs for a MergeKey unit. A Barrier-class unit (no separator) is deleted with no proof of attribution (`probe_engine.cpp:3809-3840`). The failure: Shift+Left is answered by the 250 ms readback before its key ran, and Backspace follows at once. The core then runs the extend and K1 in one batch, and the barrier deletes **two** characters (`verified-selection-delete`); Writer deletes one. §10.5 raises the core pause this tolerates from about 250 ms to about 2,250 ms. This falsifies 10.1's "文件不會被改錯" and 10.5's "a late K1 is the same K1 with the same proof". In the opposite direction the two keys cancel and the result is a silent mid-paragraph `verified-boundary-noop`, which C1 cannot tell from a real boundary.
- **Q3.** For the trigger pair, I found no counterexample that the product can reach. SHOULD: the counter must count every callback, not every change in payload. Its arrival must also push editor-state by itself, because the callback switch pushes only seven types (none of them `DOCUMENT_SIZE_CHANGED`). P2's edits move the caret, so P2 would pass a counter that never pushes on its own.
- **Q4.** S5's single follow-up key cannot see either of two refused sequences. With rule A "照舊" (pinned at beforeinput), "Backspace, Shift+Left, Backspace" is refused when the first delete is still out. With rule A folded into the run-time resolver, "range, Backspace, Backspace" is refused, because delete-selection's reply is serialised before its own `SEL0`. SHOULD: S5's oracle needs §24's `reduce_content`, without which it is red on every cell. It also needs §10.3's layout split, because otherwise the Up/Down/Home/End cells are red on a correct product. And it needs a positive control showing that "no wait" really overlapped.
- **Q5.** S-1's list is incomplete. `e2/expected-gesture-offers.json` pins all six moves to `collapsed` and fails on any widening; it still points at `e2-editor-v8`, so if left alone it never sees v20. Rows `p1-4-abi-3` and `p1-7-header-test` in `e2/relink-queue-v3.json` pin `4u` with `blocksRelink`. Both are run by `test-e2-c-static` at every freeze. Also missing: `editor_api.h:43` and its extend contract text, and the d.ts `moveLine` overload.

## Q1 — a completion before its own flush, outside L-extend-prior-flush's population — COUNTEREXAMPLE

**Claim attacked.** §10.1: "母數（依 F1）：一是對非空選取做的 `insert-text`…；二是以讀回完成、自己的 `TEXT_SELECTION` 卻晚於 250 ms 才到的操作。不在母數裡：合併鍵…以及從游標出發的一般移動" (ruling-2 B1: "By F1 the population is: …").

**Census of every completion site in `probe_engine.cpp`:**

| site | lines | completes before its own `TEXT_SELECTION` is in the cache? |
|---|---|---|
| `completePendingEditorOperation` (moves, extends, select, place-caret) | 2155-2228 | completes on the first matching callback, mid-flush. Caret move: CUR only (F1). Place-caret: `SEL0` precedes CUR in the flush (init.cxx:2398-2420), so it is cached first. Select: see (B) |
| `completePendingEditorSelectByReadback`, `…ActionByReadback` | 2205-2235, 2300-2330 | yes: population member 2 |
| UNO result, `gUnoOperation == "editor-action-completed"` | 2742-2797 | **yes, not in the population: (A)** |
| `maybeFinishSelectionBarrier` (`verified-selection-delete`) | 3411-3486 | no: waits for the collapse `SEL0` (3502-3512, 3911-3918) and re-reads NONE |
| `finishMergeKeyUndo` (`verified-key-undo`) | 3681-3722 | completes by poll before the key's flush, but that flush is empty→empty: Escape #2's empty `TEXT_SELECTION` is the proof that lets the key be posted (`merge_key_undo.hpp:166-168`, 3659-3679). F1 holds; not a member |
| `completeFormatBarrier` | 1600-1631 | no: it finishes on the restore's `SEL0` (5055-5058). The no-restore exits (4960-4972, 4994-5013) finish over a selection already in the cache: the caller's range on the cross route, or `.uno:SelectText`'s, which must be observed before `ReadQueued` (5034-5041) |
| `handleInsertText` | 3186-3221 | yes: member 1. The `postKeyEvent` fallback (3195-3207) completes before its keys run, but `paste` of `text/plain` does not fail in practice |
| `handleReplaceSelection` | 4076-4094 | synchronous paste; not reachable from the product (page paste goes adapter → `commitText` → `insertText`). Equivalent to member 1 if it ever is |
| §10.5's new `verified-boundary-noop` | (to be written) | a K1 later than ~2,250 ms lands afterwards. It is inside member 2 by the spec's wording ("以讀回完成…晚於 250 ms"). Ruling-2 names only the three `Editor*Readback` kinds, so keep the spec's wording and do not tie the model's readback kind to the 250 ms constant |
| `handleClick` (replies `clicked` at once) | 3163-3184 | not reachable (the product uses place-caret) |

**(A) `uno-command-result` completions.**
- `startEditorUnoAction` (4284-4316) serves delete-selection (5333), insert-paragraph/line-break, editor undo/redo, and set-bold, italic, underline and strikethrough (5344-5375). All of them complete on `LOK_CALLBACK_UNO_COMMAND_RESULT` and serialise `appendEditorState` there (2742-2797).
- With a listener the dispatch is synchronous (`unoctitm.cxx:655-657`). The selection repaint flags `TEXT_SELECTION` while the command runs (`viscrs.cxx:505-527`), and `dispatchFinished` then **queues** the result (`init.cxx:5106`).
- The flush runs later as a user event (2577-2581). It appends the updated types SEL/CUR only at that point, after everything already queued (`init.cxx:2485-2486`, `enqueueUpdatedTypes` 2380-2449).
- So the completion is emitted before its own `SEL0` (delete-selection on a range) or its own changed rectangles (bold or italic widens a selected run).

Scenario:
1. A range is selected and Ctrl+B is pressed.
2. Bold's reply is emitted at `UNO_COMMAND_RESULT`.
3. The core thread is preempted before it delivers the rest of that flush, for longer than one page round trip.
4. The session dispatches Shift+Right. Its dispatch cache is the old rectangles.
5. Bold's late `TEXT_SELECTION` differs from that cache, and the CUR follows it. Rule (a) completes the extend with bold's state, before the extend's own key.

**(B) The product select-range.**
- `editorSelectRangeV2` → `oxsdk_editor_select_range` → `InternalSelectionTextHandles` (`editor_api.cpp:72-74`, `:210-226`).
- That issues `setTextSelection` RESET, START and END as three separate LOK calls (5577-5622). Each takes and releases the SolarMutex.
- `requiredCallback` is `TEXT_SELECTION` (5555), and an empty payload counts (`parseEditorSelectionRectangles` returns true on empty, 1188-1189).

Scenario:
1. A range is selected and the user drags a new selection.
2. RESET flags `SEL0` and posts the flush.
3. The core thread takes the SolarMutex between RESET and START and delivers `SEL0`. The select completes, collapsed.
4. START and END produce a non-empty `TEXT_SELECTION` in a later flush.
5. If that flush is late relative to the next Shift+key's dispatch, rule (a) completes the extend on it. This is the 039 interaction sequence (drag, then Shift+arrow). It is completed by callback, not by readback, and it is not insert-text.

**Weight.**
- Both windows are narrow. (A) needs the core thread preempted in the middle of one `invoke()` loop. (B) needs the core thread to win the SolarMutex between two consecutive engine calls. Member 1 has the same kind of window.
- The effect is the named one: one stale reply, which the next push corrects.
- The defect is in the population: it is written as a hand enumeration (AGENTS.md §1, form 3) and presented as exhaustive. §10.1 already says the model test prints the population. If that test's LOK model has only the two example operations, it will print exactly the hand list.
- (A) also matters more to §10.4 than to rule (a): see Q4, sequence B.

**Remedy (no new mechanism).**
1. Define the residual as "any completion emitted before its own flush's updated types reached the cache", and take the printed set as the list.
2. Give `tests/merge_key_undo_model_test.cpp`'s LOK model the two event shapes it lacks: a command result queued ahead of the same flush's SEL/CUR, and a multi-call synchronous selection with a flush between the calls.

## Q2 — K1 late inside §10.5's window, ordinary unit path, a P the fence does not catch — COUNTEREXAMPLE

**Claims attacked.**
- §10.5: "窗內到了 K1 的 `TEXT_SELECTION`：照今天的路走（…→ 單位驗證 → 併段／刪除…）…歸屬的 P 與錨點柵欄在 K1 之前就已設好". Ruling-2 B3: "a late K1 is the same K1 with the same proof".
- §10.1's effect: "文件不會被改錯".

**Evidence.**
- The fence is consulted only for `UnitClass::MergeKey`. `verifyAndDispatchSelectionBarrierDelete` → `classifyUnit` → `startMergeKeyUndo` → `fenceHolds()` (3792-3807, 3602-3611).
- A unit with no separator is `UnitClass::Barrier` (`merge_key_undo.hpp:61-70`). It goes to `geometrySafe` (one rectangle) and `textSafe` (≤128 bytes, no separator) (3811-3818). Then `.uno:SwBackspace`/`.uno:Delete` runs on **whatever is selected** (3836-3840). A two-character selection on one line passes both checks.
- The barrier's start precondition is a synchronous read: `readSelection()` NONE plus a collapsed cache (4004-4011).
  - `doc_getSelectionTypeAndText` takes the SolarMutex and runs no events (`init.cxx:5988ff`).
  - Posted keys run only on the core thread's loop (`unotxdoc.cxx:4008-4012` → `postKeyEventAsync`).
  - So the precondition cannot see a posted key that has not run yet.
- An extend always arms the 250 ms readback (5495-5502), and §10.1 keeps that fallback. `completePendingEditorActionByReadback` serialises the cache (2300-2330), which is still "collapsed" if the key has not run.
- §10.4's resolver reads the session's snapshot. The queue writes `result.state` before running the next item (`editor-session.js:299-311`), so the resolver sees "collapsed" and chooses delete-backward, which the gate admits (5285-5300).
- K1 is posted behind the extend key (FIFO). The flush is posted when the first of the two keys runs (`init.cxx:2577-2581`), which is after K1 was posted. So both keys run before one flush: SS, SE, one non-empty `TEXT_SELECTION`, then CUR. The attribution's P is the last caret before that (X, with no CUR between), and the anchor (END for backward) is X.

**Scenario (Backspace; Delete is the mirror with Shift+Right):**
1. The caret is at X in the middle of a line, with nothing selected. The user presses Shift+Left. The core thread then runs no posted events for ≥ 250 ms without holding the SolarMutex (for example, its worker is descheduled). Finding 135 measured about 200 ms worker silences on 4 of 21 runs of one cell.
2. At 250 ms the extend completes as `verified-move-readback` with a collapsed state.
3. The already-queued Backspace runs. The resolver chooses delete-backward, the barrier start reads NONE, and K1 (Shift+Left) is posted.
4. Today: at 250 ms after K1 the result is `nothing-selected`, then a reopen, and the stale extend dies with the worker. Under §10.5 the barrier waits 2,000 ms more.
5. The core resumes inside the window. It runs Shift+Left (the extend), then Shift+Left (K1), then one flush: `SEL [X-2, X]`, CUR.
6. `handleSelectionBarrierStateCallback` → `UnitVerificationQueued` (3897-3906). The text is "ab", Barrier class, one rectangle. `.uno:SwBackspace` deletes "ab", and the reply is `verified-selection-delete`, `changed: true`, `selectedText: "ab"` (3445-3486).
7. Writer, for Shift+Left then Backspace, deletes "b". One extra character is deleted, silently.

**The other cases.**
- MergeKey variant: the fence **holds** (P = X, anchor END = X). The K2 text check is what catches it. After Escape #1 the caret is at X-2, and K2 selects one unit, which is not K1's two. That gives `return-mismatch` and a reopen (3643-3657). So the guard there is K2, not the fence.
- Opposite direction (Shift+Right, then Backspace): the two keys cancel. By F1 neither SEL nor CUR is sent, both reads are NONE, and the result is `verified-boundary-noop` in the middle of a paragraph. Writer would delete the selected character. C1 ("selectionType none at +500 ms") passes, because C1 cannot tell a false boundary from a true one.
- Plain moves in the same position are Writer-equivalent: K1 starts from the moved caret, and for MergeKey the fence catches the stale P. The hazard is specific to a pending **extend**, because K1 then extends an existing selection.
- The precondition is new in v20: the v19 page drops Shift (`e2-editor-app.js:2596`). §10.5 raises the tolerated pause from about 250 ms to about 2,250 ms after K1. No criterion sees it: S5 runs isolated cells with no stall.

**Remedy options (for the disposition).**
- (a) Narrowest: a K1 `TEXT_SELECTION` that arrives after the first 250 ms deadline takes the ordinary path only for a MergeKey unit. A Barrier-class unit is refused as today (`unit-late`, then a reopen).
  - This restores today's band for the one class that has no proof.
  - It keeps the window for the targets C was written for (true boundaries, where K1 produces no callback, P-b) and for MergeKey units (fence plus K2 check).
  - Cost: one flag. Ruling-2 rejected that flag for every unit; this limits it to the class that has no proof.
- (b) In any case, name the residual and correct the two claims above. The residual: an extend answered by the readback before its key ran, followed at once by Backspace/Delete in the same direction, deletes one unit more than Writer (single line, no separator). In the opposite direction it becomes a silent mid-paragraph no-op.

## Q3 — a page-count change with neither `DOCUMENT_SIZE_CHANGED` nor a paint `documentSizeChanged` — SHOULD

I found no product-reachable counterexample to the trigger pair. What I checked:

1. **Writer has one emitter.** `SwViewShell::SizeChgNotify` (`viewsh.cxx:1294-1322`) → `SfxLokHelper::notifyDocumentSizeChanged` (`lokhelper.cxx:713-728`). It notifies only when `ActionPend() || mbPaintInProgress`, and never while `IsCalcLayoutProgress()` (1298-1304). The other branch (`::SizeNotify` → `SwView::DocSzChgd`, `viewport.cxx:154-194`) has no LOK path.
2. **When pages change.** Page frames are created and removed only by layout: `SwPageFrame::Paste`/`Cut` → `CheckViewLayout` (`pagechg.cxx:995`, `:1039`). `CheckViewLayout` notifies on `bPageChanged || aNewSize != aOldSize` (2632-2634), so a page change that leaves the size the same still emits the callback, with an unchanged payload.
3. **Contexts.**
   - Layout at EndAction runs with `mnStartAction` still 1 (`viewsh.cxx:342-351`), and idle layout increments `mnStartAction` (`layact.cxx:2424`, `SwLayIdle` ctor). Both emit.
   - Layout during a paint goes through `CheckInvalidForPaint` with `++mnStartAction` (`viewsh.cxx:1912-1919`), so it emits too. But `doc_paintTile` disables callbacks (`init.cxx:4454-4534`), and `queue()` drops every Writer notification while they are disabled (`init.cxx:1846`).
   - The paint reply's size comparison after `paintTile` (`probe_engine.cpp:3125-3133`) catches that case unless the change leaves the size the same.
4. **CalcLayout** emits nothing (point 1). Its callers: TOC update, repaginate, print/PDF `getRendererCount` (`unotxdoc.cxx:2782`), view creation with updatable fields, OLE size at load, `GetLineCount`, `crsrsh.cxx:2322` (cursor content without a frame), and the ww8/docx/rtf export. None is reachable from the product's actions or its ODT save.
5. **Size-invariant count changes.** An automatically inserted blank page uses the 0×0 empty page format and gets zero height in non-book view (`pagechg.cxx:2425-2434`). It appears or disappears when a page break with a number offset flips parity (`InsertPage`, `pagechg.cxx:1610-1614`). In product edits that flip always comes with a real page added or removed, so the size changes.

So only "a size-invariant page change during a paint or during CalcLayout" emits neither, and I found no product trigger for it.

**SHOULD: delivery (P2 cannot see it).**
- §10.8 should say the counter increments once per callback, not per change of payload (point 2 emits with an unchanged payload).
- The counter's arrival must itself push editor-state.
  - The callback switch sets `editorStateChanged` only for seven types (2556-2629: tiles, cursor, selection, start, end, cursor-visible, a11y), and `emitEditorStateEvent` runs only then (2630-2655).
  - A page added by idle layout away from the caret can arrive with no CUR/SEL (both deduplicated). It may also arrive with no `INVALIDATE_TILES`, because `PaintTile` sets the core's visible area to the last painted tile (`viewsh.cxx:2209`). Native Edit A saw `INVALIDATE_TILES 0, 0, 3839, 3839` beside the size change.
  - The counter would then reach the page only with the next unrelated push.
- P2's cases (add a page, remove a page) move the caret in the same flush. So the caret's push carries the counter, and P2 passes a counter that never pushes by itself.
- Remedy: write the push into §10.8, and make P2's "add" case a page added by reflow away from the caret. For example, type on page 1 of a fixture with no hard breaks whose last page is full. §34 allows this: P2 would pass that broken product in an honest run.

## Q4 — can S5's population or oracle be passed by a broken product — COUNTEREXAMPLE (+SHOULD)

**Population (COUNTEREXAMPLE).** S5 is "Shift cell, then one key". Wherever rule A is placed, one of two sequences is refused and S5 contains neither.

Evidence:
- Rule A is evaluated at beforeinput (`e2-editor-app.js:2403-2421`): `deletesInFlight > 0` pins the key's own collapsed form.
- delete-backward stays `["collapsed"]` (`tests/test_e2_editor_v4_profile.py:92-100`; §10 widens only the six moves).
- The gate refuses delete-backward on a range and delete-selection on a caret (`probe_engine.cpp:5262-5300`).
- The base `_drain` (`editor-session.js:287-311`; `NarrowEditorV2Session extends EditorSession`, `narrow-editor-v2-session.js:150`) writes `result.state`, then runs the next item in the same task, before the next worker message (the push) is processed.

- **Sequence A: rule A kept literally ("照舊").**
  1. Caret. The user presses Backspace (#1); it is out for 46–67 ms (finding 131).
  2. Shift+Left, then Backspace (#2) while #1 is still out (a fast burst, or any backlog such as a 135-type pause).
  3. #2 is pinned to delete-backward before it is queued.
  4. Queue order: #1, extend, #2. When #2 runs, the cache holds the extend's range, and the gate refuses it.
  5. Writer deletes the selected character.

  This is new in v20. In v19 the only thing that could sit between two deletes and make a range was a mouse drag.
- **Sequence B: rule A folded into the run-time resolver**, as ruling-2's "late binding gives rule A's answer" suggests.
  1. A range is selected, then Backspace (#1 → delete-selection), then Backspace (#2) queued while #1 is out.
  2. #1's reply is `uno-command-result`, serialised before its own `SEL0` (Q1 (A)), so the session's snapshot still says "range".
  3. #2's resolver runs before the `SEL0` push is processed, chooses delete-selection, and the gate refuses it on a caret.

  This is finding 131 §9.16's NOT_ESTABLISHED case.

Remedy:
- Move rule A into the resolver, keyed on the queue: if the item that ran immediately before this one was a delete, use this key's own collapsed form; otherwise use the snapshot. Every delete ends collapsed even when its reply is stale, and a move or extend in between completes fresh under rule (a).
- Population: for S5's Backspace and Delete arms, add (i) the same delete key a second time and (ii) one delete key before the Shift+key, with no waits. Writer's reference comes from the native tool, as now.

**Oracle (SHOULD).**
- **Raw bytes.** SPEC-M3-paragraph-merge §24 measured native and WASM `content.xml` byte-different on every input with no edit at all (namespace order, `soft-page-break`, empty `office:forms`). S5's "逐位元組" must name §24's `reduce_content`; without it, S5 is red on all 168 delete cells of a correct product.
- **Layout-dependent cells.** §10.3 limits exact comparison with native to Left/Right and single-line Home/End, because WASM fonts differ. S5 compares all 84 cells with native, so the Up/Down/Home/End cells on wrapped or CJK paragraphs are red on a correct product. That forces a judge edit after the run (§34.4).
  - Apply §10.3's split: native reference for the layout-independent cells.
  - For the rest, the reference is the same cell on WASM with a settled wait before the follow-up key (the "fresh arm" pattern).
- **"No wait" has no positive control.** Nothing records that the follow-up key was queued while the extend was still out. If the runner's two keys never overlap, S5 passes a product without late binding.
  - Record, per cell, the page's count of moves and extends in flight at the follow-up's beforeinput. S-12 needs that count anyway.
  - Count only cells where it is > 0, and fail on an empty set.
- **Not reachable by S5 in an honest run:** Q2's stall path. Name it rather than test it.

## Q5 — is S-1's pin list complete — COUNTEREXAMPLE (incomplete)

Confirmed as cited:
- `sdk/sdk-worker.js:132-135` and `:1401-1410` (`EDITOR_V1_MOVE_ACTIONS` gates `editorActionV2` too).
- v19's worker is `$(E2_V15_ARCHIVE)/sdk-worker.js` (`Makefile:1493-1494`).
- `tools/build_e2_editor_v4_profile.py:81`, `:98-103`.
- `tests/test_e2_editor_v4_profile.py:38-42`, `:109-111`.
- `src/editor_api.cpp:78-81`.
- `narrow-editor-v2-client.d.ts:71-74`.
- `tests/editor_abi_header_test.cpp:20`.

**Missing.**
1. **`wasm_sdk_probe/e2/expected-gesture-offers.json`**
   - It pins all six moves to `["collapsed"]` (lines 59-76) and is pointed at `"profile": "e2-editor-v8"` (line 7).
   - `tools/check_gesture_offers.py` fails on any WIDER gesture (57-63) and forbids editing `expected` without the evidence named in `rationale`.
   - It runs in `make test-e2-c-static` (`Makefile:3594-3596`), which every freeze runs (`findings/evidence/136/unit/test-e2-c-static-after-freeze-v66.txt`).
   - Two failure modes:
     - Move it to v20: it is red on six widenings until `expected` and `rationale` move with R1/S1 evidence.
     - Leave it on v8: the 078 guard never reads v20, silently.
2. **`wasm_sdk_probe/e2/relink-queue-v3.json`**
   - Rows `p1-4-abi-3` (101-115: `#define OXSDK_EDITOR_ABI_VERSION 4u`) and `p1-7-header-test` (163-178: `static_assert(OXSDK_EDITOR_ABI_VERSION == 4u);`), both `blocksRelink: true`.
   - Checked by `tools/check_relink_queue.py` in the same target (`Makefile:3586-3587`).
   - The 3→4 `supersedes` notes in those rows are the precedent.
3. **`src/editor_api.h`**
   - The define at `:43`.
   - The contract text that states the narrowing ABI 5 removes: `:84-96` ("`extend_selection` is accepted ONLY by the two character movements, NOT by these four … can be added later by a version that measures it first") and `:134-135`.
4. **The client.**
   - `narrow-editor-v2-client.d.ts:82-83`: `moveLine(direction, options?: RevisionOptions)` has no `extendSelection`. This is in addition to `:71-74`.
   - `narrow-editor-v2-client.js:322-327`: the runtime check and its message "restricted to character movement". §4.1 names the client as design, but S-1's pin list does not.
5. **`tools/build_e2_editor_v4_profile.py:81`.**
   - `ABI_VERSION` is a module constant shared by every profile minted through `--profile`; v19 is built with it (`Makefile:1503-1510`).
   - Bumping it would mint 5 into any frozen profile rebuilt from this builder, and it fails `test_abi_version_is_four`.
   - S-1 should say "a per-profile ABI", the way `--inline-range-gestures` is per profile.

**NOTE.**
- `web/e2-editor-app.js:156` declares `MOVE_ACTIONS` with the two character moves, and nothing reads it (it is the only occurrence in the file). Remove or widen it, so that nobody wires S-12's in-flight count to it.
- Not pins of the three kinds asked about, but the same change will hit them:
  - `editor-shell-v2/tests/narrow-editor-v2-client.test.mjs` `DECLARED_DIVERGENCE` (194ff) must declare `verified-boundary-noop` on the two deletes (§10.5).
  - `tools/probe_129_m4_wasm.py`'s `m4-shift-*` arms pin "Shift+arrow does nothing". They are retired together with 129-B (S-2).
- Checked and not pins:
  - `tools/make_negative_profiles.py` derives the mismatched ABI (declared + 1).
  - `declaration-drift.test.mjs` pins wire ids, not extend.
  - The session's `BOUNDARY_CAPABLE_MOVES` (`narrow-editor-v2-session.js:74-77`) already lists all six moves.
  - The host repo (`~/Projects/Nextcloud_Apps/litecore`) pins no editor ABI.

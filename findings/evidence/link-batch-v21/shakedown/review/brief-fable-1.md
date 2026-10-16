# Ruling request 1 (v21 shakedown): four product defects found by the smokes

**You decide on the owner's behalf.** The owner is asleep and wrote (2026-10-17 ~03:00): 「我要去睡了，請你自主執行／有疑義的地方可以發給fable，我授權它代我決策」. Some things stay outside what you can authorise tonight:

- a relink (a compiling `make`) is the owner's own step;
- push, deletes, the count chain and installing a host (ddev) do not happen tonight.

A ruling may still **plan** any of them for the owner.

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. Read `CLAUDE.md` 「驗收判準的形式」 §1–§11 first; it governs how criteria may change.

## Where we are

- **v21** = item 1, Ctrl/Cmd+Home/End (finding 142, engine actions 22/23), plus item 2, paste as Markdown (a dialog plus an SDK call).
  - The criteria are pinned: spec `specs/SPEC-M3-link-batch-v21.md` §11.
  - Appended readings: §12.1 and §12.2.
- **What is linked:** the engine `e2-editor-v21` (wasm `db3408f5…`).
- **What is not done yet:**
  - shell v74 (page and session) is not frozen;
  - nothing is bound;
  - host 0.2.25 is not built.
- **Nominal shipped version:** 0.2.24 (page `901dd6a6…`, engine `e2-editor-v20`).
- **The shakedown so far:**
  - the arms are committed (`findings/evidence/link-batch-v21/shakedown/ARMS*.md`, `8f1dbf0a`);
  - one Chrome smoke per item has run (`smoke/`);
  - two diagnostics followed (`diag-dirty-move/`, `diag-long-paragraph/`);
  - **no evidence run has started.**
- **Every page or session change you allow** changes the v74 bytes. The smokes are then void as evidence, as they already are; the evidence runs (N=3, two browsers) happen after the changes.

## The four defects (F-claims: check them against the files)

### Q1: finding 150, a move key during an in-flight delete takes the range path

- **F1.** The page decides "the caret is on a range" from the engine's pushed state (`selectionShapeOf(...)`) in two places: the arrows' range path (`wasm_sdk_probe/web/e2-editor-app.js` about `:3192-3197`, finding 129) and v21's `sendDocumentMove` (about `:3330-3333`). Neither checks `deletesInFlight`.
- **F2.** Finding 131's rule A ("while a delete this page sent is out, a range in the engine's state is the barrier's, not the user's") is applied in three other places: `deleteActionFor` (about `:2787`), `overlayEditorState` (about `:1766`, 132) and the reopen caret (136, about `:1038-1046`).
- **F3.** The measurement, `diag-dirty-move/` V6e: from «Bravo|», Backspace @0, Backspace @20, ArrowRight @40, Delete @60. Key order gives «Bra econd».
  - v21 gives «Bra scond» 3/3 per browser, request order `delete-backward ×2 → editorPlaceCaretV2 → delete-forward → …`.
  - **0.2.24 gives «Brasecond» 3/3 per browser.** The defect predates v21.
  - Item-1 smoke D8 (e) is the Ctrl+End twin. It is a pinned criterion and it is red.
- **F4.** Candidate fix 2: `deletesInFlight === 0 &&` at the head of both decisions. Served in the mirror only (page `17a28c1c…`).
  - V6e and D8 (e) then give the key-order text 3/3 per browser.
  - A range control (drag `second`, then ArrowRight) still takes click→move 3/3.
  - It is the existing rule applied where it was missing, not a timing rule. Finding 137's ruling 4 forbids timing patches.
- **F5.** D8's pinned default, if red, is 「頁面保留今天的扣住規則，具名 L-142-held-after-move」. That default is about the hold rewrite. It does not remove this mechanism [inferred].

Options:
- **A.** Apply fix 2 to both paths before the v74 freeze.
- **B.** Apply it to `sendDocumentMove` only, the v21 scope. The arrows keep the 0.2.24 defect, registered as finding 150's remainder for a later batch.
- **C.** No fix. Take D8's default and register.

**My lean: A.** The arrows' half is the same one-condition change, measured, and it removes a data-changing defect the shipped version has.

### Q2: finding 151, after unsaved edits, typing right after Ctrl+Home/End (and after the first arrow) lands at the pre-move caret

- **F6.** In a dirty document the session saves a checkpoint before every move in `BOUNDARY_CAPABLE_MOVES` (`editor-shell-v2/narrow-editor-v2-session.js` `action()`, about `:1004-1006`; the reason is finding 096, a posted key at a boundary that waits forever; comment at about `:62-90`). v21 added 22/23 to that set.
- **F7.** After **any** save (the checkpoint or the toolbar save), core does not run the next posted key for more than 250 ms. The engine then completes the move `verified-move-readback` from its cache with the **old** caret, and the next typed character (`insertText` → synchronous `paste`) runs before the move. Measurements, `diag-dirty-move/`, each 3/3 in Chrome and 3/3 in Firefox:
  - V1: `Z` (dirty), Ctrl+End, `Q` 30 ms later → `Q` at the pre-move caret;
  - V2: the same with `Q` 50 ms after the move's reply → pre-move caret;
  - V4: long60 → pre-move caret;
  - V3: the clean control → document end, the move answered by callback in 34–45 ms;
  - V7: toolbar save, then Ctrl+End 2–9 ms after the save's reply → pre-move; 300, 1000 or 3000 ms after → document end. The window between 10 and 300 ms is not measured.
- **F8.** **The arrows too, on the shipped 0.2.24** (V8d, the first arrow after a change): `save` → `move-line-down` `verified-move-readback` 251 ms with the old caret → `insertText`. On 0.2.24, 3/3 per browser answer by readback; the v21 page's `Q` lands at the pre-arrow caret 3/3 per browser. (0.2.24's `Q` landing: see the agent's latest README section if present.) This is L-142-readback-overtaken / finding 137's class, which was registered as "core stalls, no runner can induce it". A save induces it every time.
- **F9.** Candidate fix 1: 22/23 take no checkpoint, in the mirror only (session `8828a390…`).
  - V1, V2 and V4 → document end, 9/9 per browser, the move answered by callback in 33–51 ms.
  - D11b-like: no `save`, `dirty` stays true.
  - **Conflict:** the pinned D11 says 「乾淨與髒文件依 096／098 斷言」. `ARMS-item1.md` D11b reads that as "exactly one checkpoint `save` before the first move in a dirty document". With fix 1 that clause is red by construction, and D11's default is 「第 1 項不出貨」.
  - D11's premise, as `narrow-editor-v2-session.js:84-89` states it, is that 22/23 "are SILENT at the boundary, exactly the shape this set exists for". But 22/23 are answered by the 250 ms readback (D7 silent presses 250.6–251.2 ms, item-1 smoke), so they cannot wait forever. The checkpoint protects only the generic case where the session dies right after the press.
- **F10.** Candidate fix 1′: no checkpoint before any of the eight moves.
  - V8d and V1 → correct, 3/3 per browser.
  - A boundary ArrowUp answers by readback, with no wedge.
  - **Conflict:** the counted product-path check `a-boundary-arrow-press-does-not-cost-the-work` (`wasm_sdk_probe/tools/run_e2_c_product_path.py` about `:2195-2215`, the mutation `boundary-move-takes-no-checkpoint`) guards exactly that checkpoint for arrows: if the session dies after a boundary arrow, the work must come back. Fix 1′ is that mutation. §34 governs changing checks.
- **F11.** The residual after fix 1: a save within less than 300 ms before Ctrl+Home/End (autosave, Ctrl+S), and the arrows (F8) unless fix 1′. The root fix is the ordered-commands batch (spec §9.1, finding 137 ruling 4), which needs an engine change and a relink.

Options:
- **A.** Fix 1 (22/23 only). Append a spec §12 correction withdrawing D11's dirty-checkpoint clause for 22/23 (CLAUDE.md §4: its premise, that they can wait forever, is false). Register the residual (F11), including the arrows on 0.2.24, under finding 151. The root fix stays with the ordered-commands batch.
- **A′.** Fix 1′ (all eight moves), with the §34 process for the arrow check.
- **B.** Keep the checkpoint, ship item 1 and register finding 151 as a named limit. Ctrl+End followed by typing is then wrong in the commonest workflow.
- **C.** Item 1 does not ship in v21. The page does not bind the keys (spec §11.0 「第 1 項沒出貨時」), L-142-sdk-callable applies, and item 1 waits for the ordered-commands batch.

**My lean: A.** Also register the arrows' 0.2.24 instance as a finding with a release-text note, and leave A′ to the ordered-commands batch, where it belongs with its guard.

### Q3: finding 152, in Chrome, keyboard typing is lost after the Markdown dialog closes

- **F12.** After the dialog closes (Insert, or Cancel with nothing sent), real keys reach the focused, enabled, non-inert sink, `document.hasFocus()` true, nothing prevented. But no `beforeinput` and no `insertText` follow, in 3/3 for each of V5, V11c and V11d in headless Chrome, and 3/3 for V5 and V11c in **headed** Chrome (`diag-dirty-move/` V11, V11g).
  - A paste (Ctrl+V) and CDP `Input.insertText` do land.
  - Firefox types fine.
  - `closeMarkdownDialog` does `dialog.close()` then `sink.focus()` in the same task (`web/e2-editor-app.js:2337-2344`).
- **F13.** Candidate fix 3: `el.sink.blur(); el.sink.focus(...)` there, in the mirror only. Headless Chrome V5 and V11c then type, 3/3 each. Headed Chrome and the Firefox control: see the agent's latest section if present.
- **F14.** Still unproven: the inputs were CDP key events, not an OS keyboard, and the headed window sat behind a locked screen. A hand test in a real Chrome would close both [inferred].

Options:
- **A.** Apply fix 3, and ask the owner for a hand test in the morning.
- **B.** No fix. Register it.
- **C.** It only matters if item 2 ships (see Q4).

**My lean: A, if item 2 ships at all.** It is a one-line page change, measured.

### Q4: finding 153, one long paragraph overflows the engine thread's 64 KiB stack

- **F15.** All link rules use `-sDEFAULT_PTHREAD_STACK_SIZE=65536` (`wasm_sdk_probe/Makefile:847`, `link_r5_product`; v20 and v21 both). The engine thread is a `std::thread` with the default stack (`src/probe_engine.cpp:6956`). Writer lays out a new paragraph's follow frames recursively, one nesting per page that one layout pass creates (`sw/source/core/text/frmform.cxx` FormatAdjust → AdjustFollow_ → CalcFollow → Calc), so one long paragraph overflows the 64 KiB stack. Nothing checks for that: `-sASSERTIONS=0`, so `STACK_OVERFLOW_CHECK` is 0. Evidence: `diag-long-paragraph/README.md`, crash stack mapped 20/20.
- **F16.** One CJK paragraph is fine up to 43,008 bytes (10 pages) and fails from 43,520 bytes, as a crash, a hang or OK-then-crash, in both browsers.
  - 65,536 bytes split into 2, 4 or 16 paragraphs: fine.
  - 65,536 ASCII bytes with no breaks: crash.
  - Native LibreOffice: fine, 6/6, 12 pages, about 50 ms.
- **F17.** **Counterfactual:** the same page with only the mirror's `probe.js` changed (the default pthread stack handed to `_emscripten_thread_init`, 65,536 → 1,048,576; `probe.wasm` untouched) pastes every failing input fine, 6/6.
- **F18.** **It predates v21.** 0.2.24's engine hangs on a raw `insertText` of the same paragraph. But 0.2.24's Ctrl+V cannot deliver it, because the input adapter refuses more than 16,384 bytes (`input/input-adapter.js:338-345`). v21's Markdown dialog accepts up to the SDK limit L = 65,536, so v21 makes it **user-reachable**.
- **F19.** Pinned M3 says 「SDK 在生效上限 L 與 L+1 各一臂；引擎直接在 65,536／65,537 各一臂」. SDK-L and ENG-65,536 both use this paragraph, so **M3 is red on the linked v21 engine.** Its default is 「第 2 項不出貨」, and by §11.0 that means 「頁面沒有入口；L-md-sdk-callable」.
  - M6's fallback (SDK limit 16 KiB) does not rescue M3: the engine arm is fixed at 65,536, and the engine's own limit is compiled in.
  - The fix (a bigger default pthread stack, or a stack attribute on the engine thread) needs a relink: a Makefile change (finding 042 applies) or an engine change. That is the owner's step.

Options:
- **A.** Item 2 does not ship in v21: no dialog entry, L-md-sdk-callable, the SDK still callable. Finding 153 goes into the next link batch with its own criterion (the paragraph that crashes today must paste on WASM, plus a memory cost check). v21 ships item 1 only, if Q2 allows.
- **B.** Hold v21 for a relink by the owner (`DEFAULT_PTHREAD_STACK_SIZE` raised, or the thread attribute). That is a new engine identity: the post-link checks and the shakedown restart on it, and the release waits.
- **C.** Something I have not seen.

**My lean: A** (ship what is sound; the relink belongs to the next batch, with its own criteria). **But note** that 0.2.24's engine already hangs on such a paragraph through a raw message, and Ctrl+V's 16 KiB cap is what keeps users away from it. Item 1 does not change that.

## What I need back (for each of Q1–Q4)

- `RULING`: the option, and any conditions.
- `WHY (for the owner)`: 台灣正體中文白話，三到六句，給擁有者明早讀.
- `FACT CHECK`: which F-claims you checked against the files, and any that are wrong.
- `CONDITIONS`: numbered and checkable, which the main session will follow and tick off. Include what must be re-measured, and what is appended to the spec under CLAUDE.md §9/§10.

Then one overall line: **what v21 ships** (item 1 / item 2 / neither) and **the order of the next steps tonight**. Tonight's work can be: page or session edits in the tree with red-first unit tests, the evidence runs under the browser lock, spec appends, and findings. The freeze, host and count need the owner, and the relink is the owner's.

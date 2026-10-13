## SUMMARY

- Q1 (C's window): COUNTEREXAMPLE for clause (c), not BLOCKING. On three positions K1 does nothing visible to the barrier, but Writer's own key would change the document. Measured natively, 3/3 each. (i) Delete with the caret in front of a numbering label: K1 only clears the in-front-of-label flag, giving one caret callback, no TEXT_SELECTION and NONE at +250 and +2250 ms. Writer's key does `Number On/Off`. (ii) Backspace at the document start when the first paragraph is bulleted: K1 sends no callback at all, Writer does `Number On/Off`. (iii) The same with a first-line indent: no callback, Writer does `Apply attributes`. v19 refused `nothing-selected` and reopened. v20 completes `verified-boundary-noop` after about 2.25 s, with no toast. `changed:false` is true, and no selection is left (a paste after K1 inserts at the caret), so C1 cannot see it. Clauses (a) and (b): NONE apart from L-C-late-K1. The README §2.1 re-entry claim "later, never different" is slightly wrong, in a harmless direction (see §1.4).
- Q2 (locks): NONE. Neither new `gMergeMutex` scope calls anything that locks, emits or calls LOK. Neither scope can be reached while either mutex is already held. Neither creates a gState.mutex/gMergeMutex order. `check_engine_lock_scopes.py` would see an emit or a LOK call under these locks. It would not see a re-entrant `gMergeMutex` or a `gMergeMutex`→`gState.mutex` nesting: two mutants of the HEAD source both exit 0, and a control mutant exits 1. Nothing of that kind exists today.
- Q3 (`page-rectangles` staleness): NONE in the engine. Every stale reply I could build is followed by a DOCUMENT_SIZE_CHANGED that arrives after the request was sent: a torn reply across the three separate SolarMutex reads, idle layout, a reply built between a change and its callback. The only way to get no trigger is core's CalcLayout path, which emits nothing (viewsh.cxx:1294–1321). That path needs layout that was incomplete at load. Natively, layout was complete at load; on WASM this was never measured (this is §12.3's P2 arm). Part 2 has to re-read on any push that arrives after it sent a request, and after BUSY. The reply carries no counter, so the page has no other way to order the two.
- Q4 (`sourceSequence` bump): COUNTEREXAMPLE, severity SHOULD (the fix is in the page, no relink). The consumer is the base `EditorSession.placeCaret`, which the v2 product inherits (editor-shell/editor-session.js:401–437; called from web/e2-editor-app.js:2280, 2694 and 1728). It counts `sourceSequence !== before` as the engine acknowledging the click. A DOCUMENT_SIZE_CHANGED with no other callback, arriving in the 22–28 ms before a click on the caret's own line takes effect, now satisfies the `onTarget && acknowledged` branch. placeCaret then returns with the old caret x. Demonstrated by running the real placeCaret against a scripted timeline, 3/3 runs: v19 returns at 26–28 ms with x=5000; v20 returns at 5–6 ms with x=1000. The next paste or format is synchronous and lands at the old x. This becomes BLOCKING-grade only if a flush containing nothing but DOCUMENT_SIZE_CHANGED occurs on WASM, which is exactly what §12.3's P2 arm tries to produce. The push cannot overwrite newer page state with older data.
- BLOCKING: none.

Every answer below is read against the v19 define set plus `OXSDK_E2_V20_LINK_BATCH` (no `OXSDK_MAINLOOP_ENGINE`, so `engineLoop` is the loop in use). Line numbers are for `wasm_sdk_probe/src/probe_engine.cpp` at `42bc8c1d` unless another file is named. Core sources are `libreoffice-26-8/`.

## 1. C's window: COUNTEREXAMPLE for (c), not BLOCKING

### 1.1 The path

`startSelectionBarrierDelete` (4179–4245) posts K1 as Shift+arrow. The engine loop then waits on `boundaryDeadline` (6278–6296). At 250 ms, `rejectSelectionBarrierAtDeadline` reads NONE with the typed selection collapsed and opens the window (4033–4039). Two seconds later it reads NONE again and calls `finishSelectionBarrierBoundaryNoop` (4041 → 3541–3569). Nothing in that path asks whether K1 *did* anything. It only asks whether a selection exists. That is the right question at a true document boundary. But there are positions where K1 changes nothing that the barrier can see, while the key the user pressed would change the document.

### 1.2 Native measurement

Tool: a probe built in scratch (appendix B). It runs one fresh `soffice` profile per arm against `native-lok-26-8/build/instdir` 26.8 with `SAL_USE_VCLPLUGIN=svp`. K1 is posted exactly as at 4234–4244: `postKeyEvent(KEYINPUT/KEYUP, 0, 1026|0x1000 or 1027|0x1000)`. The probe reads `getSelectionTypeAndText` at +250 ms and +2250 ms. It also compares the `.uno:Undo` payload before and after, and pastes "Z" afterwards. The "key" arm instead posts the user's own Backspace (1283) or Delete (1286). The fixtures are flat ODT files written by appendix B's generator.

| case | placement | K1 callbacks | readSelection +250 / +2250 | Writer's key (undo top) | rounds |
|---|---|---|---|---|---|
| (i) Delete in front of a bullet label | GoToStartOfDoc, then unshifted Left. The caret moves `2138 → 1778`: in front of the label | one `INVALIDATE_VISIBLE_CURSOR` `2138, 1418, 0, 276`, no TEXT_SELECTION | 0 / 0 (NONE) | `Number On/Off` | 3/3 K1, 3/3 key |
| (ii) Backspace at the document start, first paragraph bulleted | GoToStartOfDoc | none | 0 / 0 | `Number On/Off` | 3/3, 3/3 |
| (iii) Backspace at the document start, first paragraph with `fo:text-indent="1cm"` | GoToStartOfDoc | none | 0 / 0 | `Apply attributes` | 3/3, 3/3 |
| control: Backspace at the document start, plain first paragraph (hidden text before it) | GoToStartOfDoc | none | 0 / 0 | unchanged | 1/1 |
| control: Delete before hidden text at the document end | Home, Right ×3 | START/END/TEXT_SELECTION `1804, 1694, 1, 275`. readSelection TEXT `HIDDEN`, so the barrier takes its normal delete path | 1 / 1 | `Delete “HIDDEN”` (agrees with the barrier) | 1/1 |

The source explains it:
- (i) `SwCursorShell::LeftRight` case 1 (`sw/source/core/crsr/crsrsh.cxx:341–347`). A rightward move from in front of the label only resets the flag, and unlike case 2 (348–360) it does not check `HasMark()`. So the shifted K1 clears the flag and selects nothing. Writer's Delete in front of a label is `NumOrNoNum` (`sw/source/uibase/docvw/edtwin.cxx:1972–1976`).
- (ii)/(iii) Writer's Backspace at the start of a paragraph is `TryRemoveIndent` (`sw/source/uibase/wrtsh/delete.cxx:63–99`) or `NumOrNoNum` (`edtwin.cxx:2048–2125`). That is true at the document start as well. K1 has no position to move to, so it sends nothing. This matches spec §9's "完全沒有回呼的 10 格".

The product can reach (i). An unshifted Left at a numbered paragraph's text start takes case 2. The 096 G arm put the product caret in front of the label with a second Home, and the v16 shakedown observed the same (x 1778 against native 2138).

### 1.3 What each version answers

- v19: at 250 ms, `finishMergeKeyError("nothing-selected")` (4045). That is `EDITOR_BOUNDARY_UNSUPPORTED`; the page checkpoints, reopens and shows a toast.
- v20: `verified-boundary-noop` with `changed:false` and an unchanged revision after about 2.25 s. No toast, no reopen. In (i) the caret visibly jumps past the label: the K1 caret callback lands in `gEditorState.caret`, and the noop's `state` carries it.
- Writer: the document changes (label removed, or indent removed).

This is clause (c): "a delete the user asked for had something deletable and v19 would have answered a refusal that reopens". It is not BLOCKING. Nothing is written to the document. `changed:false` is literally true. No selection is left: after K1, the paste of "Z" went in at the caret in every K1 arm, and nothing was replaced. C1 (§10.5) cannot see it, because `selectionType` is `none`. The spec's named cost assumes that Backspace at the document start does nothing in Writer, and that holds only for an unnumbered, unindented first paragraph.

Two ways to dispose of it. The owner should pick one before the link, because one of them is an engine change:
- A: register it as a named residual beside L-C-late-K1. Cases (ii) and (iii) cannot be told apart from a true boundary by K1 alone, because neither produces any callback.
- B: for (i) only, keep v19's refusal when the window expires with a caret that moved since `caretBefore` (`gEditorState.caret` against `transaction.caretBefore`, captured at 4211). At a true document end K1 produces no callback (§9, P-b). A caret that moved therefore means K1 ran and selected nothing, which is not a boundary. If a relayout moves the cached caret, B misfires toward refusing, which is v19's behaviour. This is a three-line change under the define. It is not required, and it is offered only because it has to be decided before the link if it is wanted at all.

### 1.4 The named lead (README §2.1, the `textSafe && !geometrySafe` re-entry)

- Re-entry at 3984–3987 sets the stage back to `AwaitingUnitSelection` and leaves `boundaryDeadline` and `boundaryNoopWindow` alone.
- **Window still false.** The deadline is the original 250 ms one. If it has already passed, the loop synthesises the step at once. If not, the loop waits for it. If the next read is NONE with the typed selection collapsed, the window opens; v19 would have refused `nothing-selected`. If the read is still TEXT (the normal case: the selection that made `textSafe` true is still there), 4071–4077 returns `EDITOR_STATE_UNAVAILABLE` with view recovery, exactly as v19 does.
- **Window already true.** The loop waits until the window's deadline. NONE with the selection collapsed then gives the noop; TEXT gives `EDITOR_STATE_UNAVAILABLE`.
- **When can that next read be NONE?** Only if the selection seen as TEXT at verification disappears without any TEXT_SELECTION being delivered, because any TEXT_SELECTION in `AwaitingUnitSelection` re-queues verification (4084–4089) instead of reaching this function. Nothing in the transaction can do that:
  - every command is BUSY (`dispatch`, 6101–6106);
  - K1's KEYUP selects nothing;
  - core does not send an empty TEXT_SELECTION after a non-empty one on a relayout (merge_key_undo.hpp header);
  - an identical empty payload is dropped by the flush handler (`desktop/source/lib/init.cxx:2529–2535`).

  Even if it happened, (a) and (b) would not hold: nothing is selected and nothing changed.
- **The correction.** "Later, never different" is not exact. With the window open, the re-entry waits up to the window's deadline, and a single-rectangle TEXT_SELECTION arriving in that time completes the delete normally. v19 would have answered at once (`EDITOR_STATE_UNAVAILABLE`, or `nothing-selected` earlier). The difference is toward the ordinary path, so it is harmless. It is a correction to the README, not a defect.

### 1.5 Other things checked, NONE

- **What can move `boundaryDeadline` or `boundaryNoopWindow`?** Only engine-thread writes: 4206, 4220, 4213 at the start, 4034–4037 when the window opens, and the struct copy/reset at the finishes. The LOK thread writes neither. Re-entry keeps both. No command can open a second transaction (BUSY).
- **What does `finishSelectionBarrierBoundaryNoop` leave behind?**
  - It resets the ticket (3544–3547) and the transaction (3543).
  - It does not reset `gMergeAttribution`, so the phase stays `AwaitUnit`. The ticket is inactive, so `feedMergeAttribution` queues nothing (3719–3727). The next delete's `beginTransaction` clears everything except `lastCaret_` (merge_key_undo.hpp `beginTransaction`). A stale queued step is dropped by the serial check (4138–4144).
  - The noop leaves Writer's shell with an empty mark and in select mode, because `SttSelect` ran before the failed move. The native paste-after-K1 arms show no consequence.
- **(a) besides L-C-late-K1:** NONE. One extension of L-C-late-K1 that the spec's wording does not cover: K1 runs in time, its flush arrives after about 2,250 ms, and its unit's plain text is empty. `getSelectionTypeAndText` returns NONE for empty text (init.cxx:6026–6027), so the read at expiry cannot see it. The late TEXT_SELECTION still reaches the page by push. I did not find such a unit: an as-character image reads COMPLEX, and hidden text reads TEXT.
- **(b):** NONE. K1 cannot change the document, and every command is BUSY. A key already pending in core's queue before K1 is finding 137 (§14). Its own reply already advanced the revision, so the noop's `changed:false` is about this delete only.

## 2. Locks: NONE

- `appendCaretBefore` (3389–3415) holds `gMergeMutex` at 3395 and calls only `hasP()`/`p()`. Its callers are `finishSelectionBarrierError` (3439) and `finishMergeKeyError` (3520). Both call it after their own merge scope has closed, and the checker marks both callers as tainted (they emit), so it would flag either one if it were called under a lock.
- `finishSelectionBarrierBoundaryNoop` holds `gMergeMutex` at 3545 only to reset the ticket. It emits at 3567, outside the scope, and calls `finishAsynchronous` (`gState.mutex`) after the scope has closed.
- All 13 `gMergeMutex` scopes call only `Attribution` methods and `mergeRect` (enumerated: 2554, 3395, 3498, 3545, 3703, 3741, 3768, 3790, 3809, 3834, 3847, 3908, 4224). None calls LOK, emits, calls `submit`, or takes either mutex.
- No `gState.mutex` scope (2464, 2503, 2510, 6230, 6247, 6496, 6614, 6640, 6650, 6746, 6761, 7129) takes `gMergeMutex`. So no lock order exists to invert.
- **The LOK thread's tracker.** `feedMergeAttribution` releases `gMergeMutex` before `submit` (3729–3732), and a failed `submit` there calls no finish function. The one new LOK-thread path into a new scope is `handleSelectionBarrierStateCallback` → `queueSelectionBarrierStep` → failed `submit` → `finishSelectionBarrierError` → `appendCaretBefore`. It starts after `feedMergeAttribution` has returned (2588), so the acquisition is not nested. This repeats the existing shape, where the LOK thread takes `gMergeMutex` while holding the SolarMutex. That shape stays safe only because the engine thread never calls LOK while holding `gMergeMutex`, and the checker enforces that.
- **What the checker would see** (`tools/check_engine_lock_scopes.py`, run on copies in scratch):

| source | exit |
|---|---|
| HEAD copy | 0 (`gState.mutex 12, gMergeMutex 13`, 99 tainted) |
| M1: `appendCaretBefore` called inside `finishMergeKeyError`'s merge scope (re-entrant `std::mutex`, a self-deadlock) | **0** |
| M2: `finishAsynchronous` (`gState.mutex`) inside the noop's merge scope (a new lock order) | **0** |
| control M3: `emitJson("{}")` inside the noop's merge scope | 1 (`emitJson( while gMergeMutex is held`) |

  The checker would have seen an emit or a LOK call under these scopes. It is blind to re-entrant acquisition and to nesting of the two mutexes, because a function that only locks is not tainted. Nothing of that kind exists today. This is a description of the checker, not a request to extend it (§34).

## 3. `page-rectangles` staleness: NONE (engine)

Checked:
- **When the callback is emitted.** Writer sends DOCUMENT_SIZE_CHANGED from `SwViewShell::SizeChgNotify` only on the branch where an action is pending or a paint is in progress, and not during CalcLayout (`sw/source/core/view/viewsh.cxx:1294–1321`). Idle layout raises `mnStartAction` (`sw/source/core/layout/layact.cxx:2424`), so idle formatting does emit it. Edits run inside actions; the native A arm emitted it 1.3–1.8 ms after the edit, and the poll arm in `findings/evidence/link-batch/page-rectangles/` found no window with the callback delivered and the old rectangles still returned.
- **A reply built between a change and its callback** reflects the change: the change completes under the SolarMutex before any of the three reads can enter. The callback that follows causes one redundant re-read.
- **A torn reply.** `handlePageRectangles` takes the SolarMutex three times (4267, 4274, 4275), so a layout pass on the LOK thread can land between the reads. That pass emits its own DOCUMENT_SIZE_CHANGED afterwards, and it arrives after the page sent the request. If the count disagrees, the SDK refuses with `PAGE_RECTANGLES_INVALID`. Part 2 must re-read on the next trigger rather than give up.
- **BUSY.** Every command is BUSY while a barrier is in flight (6101–6106). A push that arrives during a merge therefore gets BUSY on its re-read. The repaint after the action catches the change only because `handlePageRectangles` leaves the paint baseline alone (4259–4263, README §9.4). That choice is load-bearing and should stay.
- **The case with no trigger** (conditional, not demonstrated). A size change made under CalcLayout emits no callback. In the product, the only CalcLayout an engine command can reach is `UpdateCursor` on content that has no frame yet (`crsrsh.cxx:2310–2324`). That needs layout that is incomplete after load. Natively, `getParts` was final right after `documentLoad`; on WASM this was never measured. It is the flush that §12.3's P2 arm tries to produce. If P2 ever shows lazy layout on WASM, this case becomes reachable.
- **What part 2 must do** (a requirement on the page, not a defect). The reply carries neither `documentSizeChangedCount` nor `sourceSequence`. A push emitted on the LOK thread while a reply is being built can therefore arrive before that older reply, and the page cannot order the two. "Re-read after any push that arrived after the request was sent" is enough. "Ignore pushes while a read is in flight" is not. A remaining gap that is out of scope here: the v2 session's announcement handler (`editor-shell-v2/narrow-editor-v2-session.js:294–310`) does not yet copy `documentSizeChangedCount`. README §9 already lists this for part 2.

## 4. The `sourceSequence` bump: COUNTEREXAMPLE, severity SHOULD (the fix is in the page)

### 4.1 The consumer

`EditorSession.placeCaret` is in `editor-shell/editor-session.js:394–445`. `NarrowEditorV2Session` (`narrow-editor-v2-session.js:150`) extends `EditorSession` and does not override it. The product calls it on pointer-down (`web/e2-editor-app.js:2280`), before a move from a point (2694), and when it restores the caret after a reopen (1728).

It posts the click with `document.click` → `handleClick`, which uses `postMouseEvent` and so runs later on the LOK thread (3211–3232). It then polls `getState`:
- `acknowledged = state.sourceSequence !== beforeSequence` (408);
- it returns on `(onTarget && (acknowledged || grace)) || (acknowledged && caretMoved)` (426–427).

The comment at 374–381 says an advance alone is not enough. But on a click on the caret's own line, `onTarget` is already true before the click runs. Any advance then ends the wait.

### 4.2 The counterexample

1. The caret is collapsed at x=1000 on line L. The user clicks L at x=5000.
2. `placeCaret` reads `before` (seq S). `handleClick` posts the mouse events.
3. A DOCUMENT_SIZE_CHANGED with no caret, selection or tiles callback beside it arrives before the click's caret callback. That callback normally comes 22–28 ms after the click (finding 048). In v20, 2663–2674 and 2678–2679 raise seq to S+1 and push it. In v19 the same callback changes nothing in `gEditorState`.
4. The next poll sees S+1 ≠ S with the caret still on L, so `onTarget && acknowledged` holds. The method returns `caretConfirmedBy: "engine-acknowledged"` with x=1000 while the click is still queued in core.
5. The next queued operation is a paste (`handleInsertText`, 3234ff, synchronous) or an inline format (`.uno:Bold`, synchronous). It runs ahead of the posted click, the same way §14 says these overtake a pending arrow. The text or the format lands at x=1000 instead of x=5000.

The harness (appendix A) runs the product's own `placeCaret` against a scripted `getState`/`click`. Three runs, identical:

```
{"arm":"v19 (no size bump)","returnedAtMs":26..28,"clickTookEffectAtMs":25,"caretConfirmedBy":"engine-acknowledged","caretInResult":5000,"caretWhenNextCommandIsSent":5000,"nextCommandLandsAtClickedPoint":true}
{"arm":"v20 (lone DOCUMENT_SIZE_CHANGED bump at 3 ms)","returnedAtMs":5..6,"clickTookEffectAtMs":25,"caretConfirmedBy":"engine-acknowledged","caretInResult":1000,"caretWhenNextCommandIsSent":1000,"nextCommandLandsAtClickedPoint":false}
```

### 4.3 Why SHOULD and not BLOCKING

- **The precondition is unmeasured on WASM.** It needs a flush whose only editor-state change is the size, inside the click's 22–28 ms. A typing or merge edit puts its own caret callback in the same flush. Idle layout after an open or reopen would qualify. That is the flush §12.3's P2 arm is trying to produce. If P2 establishes such a flush on WASM, treat this as BLOCKING before the count.
- **v19 already has the same class through another trigger.** The insert reply leaves before its caret callback (worker comment for 068). So a click queued right behind typing already gets `acknowledged && caretMoved` from the paste's own late caret. v20 adds a second trigger that needs no caret change at all.
- **The fix needs no relink.** One option is a `placeCaret` override in `NarrowEditorV2Session` (`editor-session.js` is E1-C-bound). It would not count an advance whose only difference is `documentSizeChangedCount` as an acknowledgement. The v2 state reply carries that field, since the worker names it in `editor-state-result`. Another option is to require `caretMoved` before the grace period ends.

### 4.4 Consumers checked, NONE

- **Selection barrier.** `dispatchSequence` (4094) is read only inside the TEXT_SELECTION type gate (4081), and that TEXT_SELECTION's own increment already satisfies `>`. A size callback cannot fall between a callback's increment and its handler on the LOK thread. `preselectionSequence`, `collapseSequence` and `acknowledgementBeforeCollapse` are recorded only.
- **Format barrier.** Gated on TEXT_SELECTION (5277–5293). `dispatchSequence` is evidence only (1518). `formatStateStale` is set only for the four caret/selection types (2690–2694).
- **Merge tracker.** `feedMergeAttribution` already saw type 13 in v19 (it runs before the switch, 2588). After the key, any callback asks for a re-read (3720), and that is unchanged.
- **Pending editor operations (096's readback included).** `completePendingEditorOperation` matches on callback type (2192–2203). `requiredCallback` is only TEXT_SELECTION, VISIBLE_CURSOR or −2, never 13. `verified-move-readback` is reached from the deadline, not from a sequence.
- **Worker.** Its projections copy sequences and judge nothing (`sdk-worker.js` 225–260, 355–385, 1054–1121).
- **Nothing else.** No JS outside tests reads `callbackSequenceAfter` or `callbackSequenceBefore` (grep over sdk/, editor-shell*/, web/e2-editor-app.js). Runners record sequences and do not judge on them.

### 4.5 Can the push overwrite newer page state with older data? No

The push is built on the LOK thread immediately after `++sourceSequence` (2679, then 2696), so it carries the newest sequence at that moment. Every field it reads was written before that increment, by the same callback or an earlier one.

A drain reply built earlier and emitted later carries a lower sequence. `machine.update` drops its `editorState` (`narrow-editor-v2-session.js:242–251`, strict `<`). A reply with an equal sequence was read after the increment, so it is at least as new.

The announcement path applies only `next > current` (291–292). The push's `revision` is a racy read of `gState.revision` (pre-existing for every push), and nothing on the page reads `editorState.revision`.

## Notes outside the four questions

- NOTE: the LOK thread can resurrect a stage on a barrier the engine just reset. It checks `stage == AwaitingUnitSelection` (4084–4085) and writes `UnitVerificationQueued` (4087) with no lock, so a reset by the engine thread between the check and the write leaves an Idle-zeroed transaction marked active. Its step then fails the handle check (4142), and every later command answers BUSY. This is pre-existing (review S1's shape). v20 reduces the exposure. v19 reset the struct at 250 ms, inside the tail of K1's arrivals (135: 196.6–210 ms stalls). v20 resets at about 2,250 ms instead, and the 250 ms point now only opens the window, without a reset. I found no other defect that changes document data or leaves a selection the user cannot see.

## Appendix A — Q4 harness (`node`, scratch, imports the repo read-only)

`node q4-placecaret.mjs file:///home/jiajun/LibreOffice/study_LiteCore` (sha256 `c5fe3bed…`). It builds `Object.create(EditorSession.prototype)` with `_enqueue = (label, op) => op({document, editor})`.

- `editor.getState()` returns `{sourceSequence, caret}` from closure variables.
- `document.click()` schedules two things: in the v20 arm, `seq += 1` at 3 ms (the lone size bump); in both arms, `seq += 1; caret = {x: 5000, …}` at 25 ms (the click).

It then calls the product's `placeCaret(5000, 2150)` with the caret starting at `{x: 1000, y: 2000, height: 300}`. It reports when the call returned and where the caret was at that moment.

## Appendix B — Q1 native probe (scratch)

- `k1probe.cpp` (sha256 `8e9845df…`), built with `g++ -std=c++17 -O2 -I libreoffice-26-8/include k1probe.cpp -ldl -lpthread`.
- The fixtures come from `make_fixtures.py` (sha256 `a60b5818…`). They are flat ODT files: `bullet` (bulleted "Alpha one", body "Beta two", bulleted "Gamma three"), `indent` (`fo:text-indent="1cm"` first paragraph), `hidden-end` and `hidden-start` (`text:display="none"` spans).
- Per arm the probe:
  - loads the document, calls `initializeForRendering`, registers the callback, paints one tile and waits until quiet;
  - runs the placement steps (`uno:<cmd>` or `key:<code>`, quiet for 600 ms after each);
  - reads the selection and `.uno:Undo`;
  - in a K1 arm, posts K1, reads the selection at +250 ms and +2250 ms, waits until quiet, reads undo, then pastes "Z";
  - in a key arm, posts the user's key, waits until quiet and reads undo;
  - saves the document as fodt.
- `STATE_CHANGED` is not printed. Exit status was 0 for every arm.
- Raw outputs stayed in the session scratch directory; the table in §1.2 quotes them. In the `hidden-end` K1 arm, K1 selected "HIDDEN" as one rectangle with readSelection TEXT, so the barrier takes its normal verified-selection-delete path. Writer's own Delete also deletes "HIDDEN" (undo `Delete “HIDDEN”`), so the two agree there. The saved `End<span T1>Z</span>` is the probe's paste replacing that selection; it is not a barrier outcome.

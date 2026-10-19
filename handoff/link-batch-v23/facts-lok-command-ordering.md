# Facts sheet: LOK command ordering for the "ordered commands" batch (v23)

Facts only; no candidate is recommended. Written 2026-10-20 from a read-only pass; nothing was built, run or edited except this file.

- `lo/` = `libreoffice-26-8/` (core worktree, HEAD `671c848b1bb8`; its local modifications are configure/build `.mk` files and `vcl/qt5/QtFrame.cxx`, none of the files cited here). `src/` = `wasm_sdk_probe/src/`. `wsp/` = `wasm_sdk_probe/`. `ev/` = `findings/evidence/`.
- Labels: **[SRC]** read at the cited line. **[INF]** my inference. **[EVID]** a measurement recorded in this repo, read here but not re-run.
- Product topology assumed throughout: engine without `OXSDK_MAINLOOP_ENGINE` (v22 rule `wsp/Makefile:1769-1780` defines none), i.e. threaded LOK, not unipoll.

## SUMMARY

1. **Q1 inventory.** Every engine command runs on the engine thread (`std::thread(engineLoop)`, `src/probe_engine.cpp:6956`). Some run **synchronously under the SolarMutex on that thread**: `paste` (typing, replace-selection, Markdown paste), `setTextSelection` (three calls for text-handles), and every `postUnoCommand(..., true)`: `.uno:Delete`/`.uno:SwBackspace`, InsertPara/InsertLinebreak, Bold/Italic/Underline/Strikeout, Undo/Redo, paragraph styles, the merge's `.uno:Escape`. Others are **posted** to the VCL user-event queue: every `postKeyEvent` (moves, extends, select-all, document start/end, barrier K1/K2, the merge's user key, the typing fallback), every `postMouseEvent` (click, place-caret, drag), and the two `postUnoCommand(..., false)` calls (`.uno:ExecuteSearch`, the comment-commit `.uno:Escape`). [SRC]
2. **Q1, hops.** In threaded LOK an accelerator-routed key takes **two posted hops**. Hop 1 is the KeyInput event. Hop 2 is an `AsyncAccelExec` event, posted at the back of the queue *when hop 1 runs*, and the move or delete happens in hop 2. Accelerator-routed keys: arrows, Home/End, Shift+arrows, Ctrl+Home/End, Ctrl+A, Backspace, Delete. Printable characters, and keys Writer handles inside `SwEditWin::KeyInput`, take one hop. [SRC + INF]
3. **Q2 queue.** The VCL main loop runs on LOK's own `lo_startmain` thread: `Application::Execute` → `emscripten_set_main_loop_arg(fps=100)`. Each tick dispatches **at most one** user event, and ticks start ≥10 ms apart. `PostUserEvent` feeds **one FIFO list** shared by all posters: posted keys, mouse and ext-text, async dispatches, `AsyncAccelExec`, the LOK callback flush, focus and resize. Timers and idles run only in a yield that dispatched no user event. [SRC + INF]
4. **Q3 re-entrancy.** Not found on WASM for paste, `.uno:Delete`, `.uno:Bold` or `.uno:Undo`. `Application::Reschedule` is a no-op there and `Application::Yield` aborts (`IsUseSystemEventLoop` measured true). The only SolarMutex releases found near these paths are `IdlesLockGuard` (finding 040: never returns, a wedge, not a reorder) and editeng's clipboard paste/copy (only with the cursor in an EditEngine). A synchronous command can still run **between** a posted key's hops. Native threaded LOK differs: Reschedule yields there. [SRC + EVID + INF]
5. **Q4 `doc_postUnoCommand`.** In threaded LOK it appends `SynchronMode=false`, which gives `ASYNCHRON` and posts via `SfxHintPoster` → `PostUserEvent`. `bNotifyWhenFinished=true` with a registered callback installs a listener, which **forces `SYNCHRON`**. So the flag changes ordering. `true`: runs now on the caller's thread and jumps the queue. `false`: posted at the back, FIFO for the first hop, no `UNO_COMMAND_RESULT`. `comphelper::dispatchCommand` never posts by itself. Of the slots used, Delete, SwBackspace, Bold, Undo and Paste are not `Asynchron`; Escape is. [SRC]
6. **Q5 public marker.** None found that is FIFO-positioned, observable and state-neutral at once. A KEYUP-only key is posted and neutral but emits nothing. An empty ext-text input deletes a selection. A posted `.uno:ExecuteSearch` that misses emits `SEARCH_NOT_FOUND`, but its effect on the selection is not established. `.uno:ReportWhenIdle` is neutral and observable, but it is a **quiescence** signal (lowest-priority idle), not a queue position. Unused in this repo. [SRC + INF]
7. **Q5/Q6, first-hop limit.** One marker (or a posted command) placed right after a key's KEYINPUT/KEYUP runs **before** that key's `AsyncAccelExec` hop. FIFO by construction covers only the first hop. [INF from SRC]
8. **Q6 internal API.** `PostUserEvent` is already reached from the engine thread on every posted key, and its list is guarded by a `std::mutex`. Calling it directly needs:
   - `vcl/svapp.hxx` and `tools/link.hxx` in a `-std=c++20 -DLIBO_INTERNAL_ONLY` translation unit. The precedent is `a11y_tree_probe.cpp`, but it is not linked in the v15–v22 product rules.
   - `DBG_UTIL` off, to match the core's `Link` layout.
   - `libvcllo.a`, which is already on linkdeps.

   Hazard: waiting for the marker while holding the SolarMutex deadlocks. The handler runs on `lo_startmain` inside a `noexcept` dispatch. [SRC + INF]
9. **Q7 unipoll.** The `#error` is our own wiring gap: the merge's deadlines and 15 ms poll live only in the blocking `engineLoop`. Finding 040 is an off-main-thread wedge. By source, the engine thread would be the main thread under unipoll; why the ruling counts 040 against C is not stated. [SRC + INF]
10. **Q8 completion.** The whole `.uno:Undo` payload is read before the user's key and re-read every 15 ms (and on every callback). A changed payload means `verified-key-undo`; a payload unchanged at 2000 ms means `key-deadline` refusal. Recorded engine `keyToUndoMs` is [30, 32, 33] ms on v20 (105 presses, both browsers); end to end it is 129–155 ms. [SRC + EVID]

## Q1. Engine inventory

All handlers run on the engine thread: `startEngine` → `std::thread(engineLoop, …)` (`src/probe_engine.cpp:6953-6956`, loop at `:6435`, `dispatch` at `:6285`) [SRC]. Each LOK `doc_*` entry takes `SolarMutexGuard` on the **calling** thread: `postKeyEvent` `lo/desktop/source/lib/init.cxx:4813`, `postUnoCommand` `:5301`, `postMouseEvent` `:5533`, `setTextSelection` `:5629`, `paste` `:6169`, `getCommandValues` `:6689` [SRC]. "Posted" means `SfxLokHelper::postEventAsync` → `Application::PostUserEvent(LOKPostAsyncEvent)` (`lo/sfx2/source/view/lokhelper.cxx:1273-1291`, threaded branch `:1289-1290`). The event later runs on `lo_startmain` (Q2) [SRC].

| wire action | engine (src) | LOK call(s) | sync / posted, and hops |
|---|---|---|---|
| move-character-left/right, move-line-up/down/home/end | `handleEditorAction` `:5694-5711`, posts `:5796-5799` | `postKeyEvent` KEYINPUT + KEYUP | **posted**. Path: `SwXTextDocument::postKeyEvent` → `postKeyEventAsync` (`lo/sw/source/uibase/uno/unotxdoc.cxx:4009-4013`, `lokhelper.cxx:1294-1312`). **2 hops**: KeyInput (`lokhelper.cxx:1214-1231`) → `SwEditWin` `KeyToView` (`lo/sw/source/uibase/docvw/edtwin.cxx:1906-1969`, `:2420-2444`) → accelerator `.uno:GoLeft`/`GoRight`/`GoUp`/`GoDown`/`GoToStartOfLine`/`GoToEndOfLine` (`officecfg/registry/data/org/openoffice/Office/Accelerators.xcu:6765`, `:6915`, `:6995`, `:6353`, `:6680`, `:6416`) → `AsyncAccelExec` posted (`lo/svtools/source/misc/acceleratorexecute.cxx:223-226`, `:496-501`; `lo/vcl/source/helper/evntpost.cxx:42-46`) [SRC] |
| extend (same keys with Shift) | `:5755` | same | **posted, 2 hops**: `edtwin.cxx:1878-1881` → `m_rView.KeyInput` `:1854` → `.uno:CharLeftSel`/`CharRightSel` (xcu `:6777`, `:6927`) [SRC] |
| move-document-start/end | `:5742-5747` | `postKeyEvent` Ctrl+Home/End | **posted, 2 hops** → `.uno:GoToStartOfDoc`/`GoToEndOfDoc` (xcu `:6686`, `:6422`). Natively observed reordering against a one-hop Backspace (`ev/link-batch-v21/native/142-ctrl-home-end/README.md:38-47`, `:379-384`) [SRC + EVID] |
| select-all (withheld) | `:5712-5737` | `postKeyEvent` Ctrl+A | **posted, 2 hops** → `.uno:SelectAll` (xcu Global `:29-32`) [SRC] |
| delete-backward / delete-forward at a caret | `startSelectionBarrierDelete` `:4205-4275` | K1 = `postKeyEvent` Shift+Left/Right (`:4260-4274`); selection read (sync); then `postUnoCommand(.uno:SwBackspace` or `.uno:Delete, null, true)` (`:4027-4028`) | K1 **posted, 2 hops**; the delete runs **sync** [SRC] |
| same, merge unit (option B) | `startMergeKeyUndo` `:3790-3810`, `postMergeReturn` `:3812-3829`, `postMergeKey` `:3847-3867` | `.uno:Escape` with `true` (sync, `:3774-3775`); K2 posted; Escape again; the user's own Backspace/Delete **posted** (`:3781-3787`); `getCommandValues(".uno:Undo")` polls (`:3499-3508`) | key: 2 hops via `.uno:SwBackspace` (xcu `:6257`) or `.uno:Delete` (xcu Global `:99-102`). 1 hop where Writer acts inside KeyInput (Backspace at a numbered start, `edtwin.cxx:2048-2110`, as cited by the 142 native README `:45`) [SRC + INF] |
| delete-selection | `:5607-5625` → `startUnoMutation` `:4356-4369` | `postUnoCommand(.uno:Delete, null, true)` | **sync** [SRC] |
| insert-text (typing) | `handleInsertText` `:3258-3294` | `paste("text/plain;charset=utf-8")` | **sync**: `doc_paste` → `doc_setClipboard` + `dispatchCommand(".uno:Paste")` with no listener and no SynchronMode (`init.cxx:6165-6192`); `SID_PASTE` not Asynchron (`lo/sfx2/sdi/sfx.sdi:3206-3221`); handler `lo/sw/source/uibase/shells/basesh.cxx:379-410`. Fallback when `paste()` is false: posted KEYINPUT/KEYUP per code point (`:3264-3280`), 1 hop each (printable chars flush at once because `AnyInput` is false on svp: `edtwin.cxx:2681-2690`, `lo/vcl/headless/svpinst.cxx:549-554`) [SRC + INF] |
| replace-selection (paste) | `handleReplaceSelection` `:4336-4354` | `paste` | **sync** [SRC] |
| Markdown paste | `handlePasteMarkdown` `:5830-5927` | `getCommandValues(.uno:Undo)` `:5886`; `paste(md MIME)` `:5898-5899`; `getCommandValues` `:5901` | **sync**, all three [SRC] |
| insert-paragraph-break / insert-line-break | `:5627-5632` | `postUnoCommand(.uno:InsertPara` or `.uno:InsertLinebreak, true)` | **sync** [SRC] |
| set-bold/italic/underline/strikethrough | `:5639-5672`, explicit arg `:4553-4556` | `postUnoCommand(.uno:Bold` etc. with `{"Bold":bool}`, `true)` | **sync** [SRC] |
| undo / redo (editor action and document op) | `:5633-5638`; `handleUndo`/`handleRedo` `:4371-4383` | `postUnoCommand(.uno:Undo` or `.uno:Redo, true)` | **sync** [SRC] |
| paragraph style / list (not asked) | format barrier `:5341-5470`, `:4711-4714` | `postUnoCommand(…, true)` incl. `.uno:SelectText` | **sync** [SRC] |
| place-caret | `handleEditorPlaceCaret` `:6073-6118` | `postMouseEvent` DOWN + UP | **posted** (`init.cxx:5529-5551` → `unotxdoc.cxx:4015-4046` → `lokhelper.cxx:1345-1375`). Hops after `MouseButtonUp`: not read [SRC] |
| click (legacy) | `handleClick` `:3235-3256` | same | **posted** [SRC] |
| set-text-selection (text-handles / reset) | `handleEditorSelect` `:5995-6044` | `setTextSelection` RESET, START, END (or RESET only) | **sync**: `SetCursorTwipPosition` (`unotxdoc.cxx:4048-4072`). Each call takes its own guard, so a posted event can run between the three [SRC + INF] |
| select by mouse-drag | `:5985-5994` | `postMouseEvent` DOWN, MOVE, UP | **posted** [SRC] |
| raw key / search (not asked) | `handleKey` `:6212-6217`; `handleSearch` `:3296-3327` | `postKeyEvent`; `postUnoCommand(.uno:ExecuteSearch, …, false)` (`:3325-3326`) | both **posted** (search via `SfxHintPoster`, Q4) [SRC] |

## Q2. The queue

**Which thread.**
- The product never enables unipoll:
  - `isUnipoll()` is `mpPollCallback != nullptr` (`lo/vcl/source/app/lok.cxx:50-54`), which only `lo_runLoop` registers (`init.cxx:7734`).
  - The engine calls `runLoop` and `setenv("SAL_LOK_OPTIONS","unipoll")` only under `OXSDK_MAINLOOP_ENGINE` (`src/probe_engine.cpp:6864-6880`, `:6902`).
  - [SRC]
- `lo_initialize` therefore creates `lo_startmain` (`init.cxx:8378-8384`). That thread runs this chain [SRC]:
  - `UpdateMainThread` (`:7714`), then `soffice_main` (`:7716`);
  - `ImplSVMain` → `InitVCL` (`lo/vcl/source/app/svmain.cxx:218`). `SvpSalInstance` records the constructing thread as main (`svpinst.cxx:96`) and sets `m_bUseSystemLoop` on Emscripten (`:102-104`);
  - `Desktop::Main` → `Execute()` (`lo/desktop/source/app/app.cxx:1679`) → `Application::Execute` (`lo/vcl/source/app/svapp.cxx:348-372`);
  - `DoExecute` → `emscripten_set_main_loop_arg(loop, this, 100, 1)` (`svpinst.cxx:308-316`).
- The hook itself waits for that loop [SRC + INF]:
  - `Desktop::Main` posts `OpenClients_Impl` (`app.cxx:1658`), which calls `RequestHandler::SetReady(true)` (`:1963`, `:1978`);
  - `lo_initialize` blocks in `WaitForReady` (`init.cxx:8382-8383`).
- A stack `SvpSalInstance::ImplYield ← loop ← … ← MainLoop_runner` was captured on WASM (`findings/040-…md:108-109`) [EVID].
- The engine thread is not the VCL main thread (`IsMainThread`, `svpinst.cxx:422-425`) [SRC].

**One tick.**
- `loop()` takes `SolarMutexGuard` and calls `ImplYield(bWait=true, all=false)` (`svpinst.cxx:303-306`) [SRC].
- `ImplYield` dispatches one user event and returns (`:442-444`). Only when none was pending does it run the sal timer, and with it the scheduler (`:447`). Otherwise it sleeps on `m_WakeUpMainCond` with the SolarMutex released (`:471`, `:484-503`). A post wakes it (`PostEvent` → `TriggerUserEventProcessing` → `Wakeup`, `lo/vcl/inc/salusereventlist.hxx:113-119`, `svpinst.cxx:130-148`) [SRC].
- The emsdk the probe links with (`wsp/Makefile:4-5`, emscripten 4.0.10) schedules the next tick 1000/fps = 10 ms after the previous tick's start (`wasm-lite/tools/emsdk/upstream/emscripten/src/lib/libeventloop.js:342-345`, `:474-475`, `:494-495`) [SRC].
- Hence, as an inference, back-to-back user events are paced about 10 ms apart. That is consistent with Q8's ~30 ms for KEYINPUT + KEYUP + `AsyncAccelExec` + flush + a 15 ms poll [INF].

**FIFO across posters: yes, one list.**
- The list is one per `SalInstance` (`SvpSalInstance : SalUserEventList`, `lo/vcl/inc/headless/svpinst.hxx:90`).
  - `PostEvent` does `push_back` under `m_aUserEventsMutex` (`salusereventlist.hxx:113-119`).
  - `DispatchUserEvents` pops from the front, on the main thread only (`lo/vcl/source/app/salusereventlist.cxx:59-136`).
  - `Application::PostUserEvent` → default window's frame → `SvpSalFrame::PostEvent` (`svapp.cxx:1064-1086`, `lo/vcl/headless/svpframe.cxx:168-172`).
- Posters into this same list [SRC]:
  - posted keys, mouse and ext-text (`lokhelper.cxx:1290`);
  - async dispatches (`lo/sfx2/source/notify/hintpost.cxx:35-51`);
  - `AsyncAccelExec` (`vcl::EventPoster::Post`, `lo/vcl/source/helper/evntpost.cxx:42-46`);
  - the LOK callback flush: `CallbackFlushHandler::scheduleFlush` posts `FlushQueue` (`init.cxx:2578-2588`), called from every `queue()` (`:2084`);
  - `IdlesLockGuard`'s empty event (`lo/vcl/source/app/scheduler.cxx:294`);
  - focus and resize events (`svpframe.cxx:125`, `:133`, `:215`, `:279`).
- Departures from plain FIFO [SRC]:
  1. Events for dead frames are dropped (`salusereventlist.cxx:98-104`).
  2. `RemoveUserEvent` cancels in place (`svapp.cxx:1088-1101`).
  3. At most one flush event is pending (`init.cxx:2580-2581`), so a callback queued later can ride an earlier-positioned flush.
  4. A posted dispatch that meets a locked dispatcher is re-posted to the back (`lo/sfx2/source/control/dispatch.cxx:996-1003`).
  5. Multi-hop handlers post their real work at the back (`AsyncAccelExec`, Q1).
  6. Timers and idles are not in the list; they run only in a yield that dispatched nothing (`svpinst.cxx:442-447`).

## Q3. Re-entrancy inside a synchronous command

- On Emscripten `m_bUseSystemLoop` is true (`svpinst.cxx:102-104`). It was measured `true` in a WASM profile, where `Reschedule(true)` returned `false` with zero events (`findings/021-…md:192-199`) [EVID].
  - `Application::Reschedule` returns false without yielding (`svapp.cxx:400-406`).
  - `Application::Yield` calls `std::abort()` (`:494-501`).
  - A modal `Dialog::Execute` loops on `Application::Yield` (`lo/vcl/source/window/dialog.cxx:1067-1068`), so it would abort, not re-enter [SRC + INF].
- Reschedule call sites exist: 13 in sw/sfx2/desktop/framework/svx/editeng outside `/qa/`, including the HTML import `lo/sw/source/filter/html/swhtml.cxx:2609` and `:2647`. All are no-ops on WASM [SRC].
- `Scheduler::ProcessEventsToIdle` bypasses that gate (`svapp.cxx:441-449` → `InnerYield`). From a non-main thread it makes the main thread dispatch user events on its behalf while the caller holds the mutex (`svpinst.cxx:338-367`, `:518-545`) [SRC].
  - Non-test callers: mail merge (`lo/sw/source/uibase/dbui/dbmgr.cxx:1375`, `lo/sw/source/ui/dbui/mmresultdialogs.cxx:712`), `Desktop` terminate (`lo/framework/source/services/desktop.cxx:288`), VCL/scheduler de-init (`svmain.cxx:438`, `scheduler.cxx:132`), uitest.
  - None is on the paste, Delete, Bold or Undo paths [INF; searched `sw sfx2 vcl svx editeng framework desktop comphelper svtools` sources].
- `SolarMutexReleaser` on or near these paths [SRC]:
  - `IdlesLockGuard` off the main thread (`scheduler.cxx:285-298`). Reached from `DelLayoutFormat` (`lo/sw/source/core/doc/DocumentLayoutManager.cxx:197`) and `unoframe.cxx:2611`. On WASM it never returns (finding 040): the engine wedges, it does not reorder.
  - `ImpEditView::Paste`/`CutCopy` release around `getContents`/`setContents` (`lo/editeng/source/editeng/impedit.cxx:1957`, `:1991`). These apply only when the cursor is in an EditEngine, e.g. a comment or draw text [INF].
  - Writer's body paste: `basesh.cxx:379-410` → `TransferableDataHelper::CreateFromClipboard` (`lo/vcl/source/treelist/transfer.cxx:2167-2188`, no releaser). The releasers in `transfer.cxx:1440-1470` are `_WIN32` only. `lokclipboard.cxx` uses only its own `osl::Mutex`. `swdtflvr.cxx` has no Reschedule, releaser or `PostUserEvent`.
  - The comphelper/sfx dispatch path holds the SolarMutex throughout (`unoctitm.cxx:578`).
- Layout idle and other idles run only from the main thread's scheduler (`svpinst.cxx:447`). They do not run inside a command executing on the engine thread [INF].
- **Not found**: a mid-command dispatch of posted keys on WASM for paste, `.uno:Delete`, `.uno:Bold` or `.uno:Undo`. **But** the engine thread can take the SolarMutex between any two user events, because each tick releases it (`svpinst.cxx:303-306`, `:471`). A synchronous command can therefore land between hop 1 and hop 2 of a posted key [INF].
- **Native differs**: `m_bUseSystemLoop` is set only under `__EMSCRIPTEN__`. On native threaded LOK, `Reschedule` (e.g. the HTML import) does yield, and the main thread then services one event for the caller (`svpinst.cxx:518-545`). Native re-entrancy results do not transfer to WASM for such paths [SRC + INF].

## Q4. `doc_postUnoCommand`

- The call itself runs synchronously on the caller under `SolarMutexGuard` (`init.cxx:5297-5302`). In threaded LOK it appends `SynchronMode=false` (`:5316-5322`) [SRC].
- With `bNotifyWhenFinished && mpCallbackFlushHandlers.count(nView)` it passes a `DispatchResultListener` (`:5513-5519`); otherwise it passes none (`:5520-5521`). The listener queues `UNO_COMMAND_RESULT` (`:5086-5107`) [SRC].
- `comphelper::dispatchCommand` calls `dispatchWithNotification` or `dispatch` directly, without posting (`lo/comphelper/source/misc/dispatchcommand.cxx:34-66`). That reaches `SfxOfficeDispatch` (`lo/sfx2/source/control/unoctitm.cxx:233-273`) and then `SfxDispatchController_Impl::dispatch` (`:568-787`) [SRC].
  - `SynchronMode` is parsed into `SYNCHRON` or `ASYNCHRON` (`:626-633`).
  - **`if (rListener.is()) nCall = SfxCallMode::SYNCHRON`** (`:655-657`).
  - Both execution paths (`:717` with args; `:734-738` via bindings → `bindings.cxx:1047`, `:1050`) end in `SfxDispatcher::Execute_` (`dispatch.cxx:730-756`).
  - There, `ASYNCHRON`, or `SLOT` mode on an `Asynchron` slot, means `xPoster->Post` → `Application::PostUserEvent` (`hintpost.cxx:35-51`). Otherwise `Call_Impl` runs synchronously.
- The posted request runs later in `PostMsgHandler`, which re-finds the slot server at run time (`dispatch.cxx:971-1004`). [SRC]
- **So `bNotifyWhenFinished` does change ordering** [SRC]:
  - `true`: the command runs now, on the engine thread, ahead of pending posted events.
  - `false`: the command is posted behind them, for the first hop, with no result callback.
  - The engine passes `true` for every document mutation (Q1 table) and `false` only for `.uno:ExecuteSearch` (`src:3325-3326`) and the comment-commit `.uno:Escape` (`src:2878-2879`).
- Slot flags [SRC]:
  - Not `Asynchron`: `Delete` (`sfx.sdi:961-976`), `Paste` (`:3206-3221`), `Undo` (`:4719-4734`), `Redo` (`:3590-3605`), `SwBackspace` (`lo/sw/sdi/swriter.sdi:402-417`), `InsertPara` (`:3624`), `InsertLinebreak` (`:3225`), `Bold`/`Italic`/`Underline`/`Strikeout` (`lo/svx/sdi/svx.sdi:832`, `:5197`, `:9066`, `:8491`), and the accelerator targets (`GoLeft` `swriter.sdi:1467`, `CharLeftSel` `:577`, `GoToStartOfDoc` `:2127`).
  - `Asynchron`: `Escape` (`swriter.sdi:1181-1197`). The merge's `.uno:Escape` is nonetheless synchronous, because the listener forces it.
- Edge cases [SRC]:
  - Posting happens only if the shell is on the dispatcher stack (`dispatch.cxx:744-752`); otherwise nothing happens.
  - A locked dispatcher drops a sync call silently (`:737-738`).
  - For toggle slots without arguments, the toggled value is computed at post time (`bindings.cxx:968-1045`). The engine always passes an explicit value (`src:4553-4556`).
- `doc_paste` passes no `SynchronMode` and no listener, so the mode is `RECORD` and execution is synchronous (`init.cxx:6183-6187`; `dispatch.cxx:740-742`) [SRC].

## Q5. A marker through public LOK only

Criteria: (a) posted into the user-event list, (b) produces an observable callback when it runs, (c) changes neither document nor selection.

| candidate | (a) | (b) | (c) | why |
|---|---|---|---|---|
| `postKeyEvent(KEYUP, 0, 0)` alone | yes (`lokhelper.cxx:1302-1311`) | **no** | yes | runs `KeyUp` (`:1232-1235`); `SwEditWin` has no `KeyUp` override (grep of `sw/source/uibase/docvw`, `edtwin.hxx`), so `vcl::Window::KeyUp` sets a flag only (`lo/vcl/source/window/window.cxx:1810-1815`) [SRC + INF] |
| KEYINPUT with a key that does nothing | yes | no guarantee | likely | no callback when nothing changes (finding 096's premise); also goes through accelerator lookup [INF] |
| `postMouseEvent(MOUSEMOVE)` | yes (`unotxdoc.cxx:4042-4045`) | only on change | not established | `MouseMove` + `RequestHelp` (`lokhelper.cxx:1256-1262`); `MOUSE_POINTER` is de-duplicated (`init.cxx:1596`); Writer's hover/drag state not read [SRC + INF] |
| `postWindowExtTextInputEvent(0, EXT_TEXTINPUT, "")` | yes (`init.cxx:4840-4868`) | — | **no** | the first ext input sends `StartExtTextInput` (`lo/vcl/source/window/winproc.cxx:1395-1401`); Writer then does `if (rSh.HasSelection()) rSh.DelRight()` (`edtwin.cxx:5931-5948`) [SRC] |
| `postWindowExtTextInputEvent(0, EXT_TEXTINPUT_END, "")` | yes | **no** | yes | with no active input `ImplHandleEndExtTextInput` does nothing (`winproc.cxx:1454-1470`) [SRC] |
| `postWindowKey/Mouse/GestureEvent` | yes (`svapp.cxx:812-831`) | — | — | needs a LOK window id; `FindLOKWindow` fails otherwise (`init.cxx:4929-4939`); nothing observable identified [SRC] |
| `postUnoCommand(cmd, …, false)` | yes, first hop (Q4) | only via the command's own effects | depends | no `UNO_COMMAND_RESULT` without the listener (`init.cxx:5520-5521`) [SRC] |
| … with `.uno:ExecuteSearch` for a string not in the document | yes | yes: `SEARCH_NOT_FOUND` (`lo/sw/source/uibase/uiview/viewsrch.cxx:551-556`, `:606-612`); `HAVE_FEATURE_DESKTOP` is 1 in the WASM config (`wasm-lite/build-headless-probe/config_host/config_feature_desktop.h:27`) | **not established** | `SearchAndWrap` does `Push`, `KillSelection` (unless search-in-selection), `Pop`, and on the wrap path `ClearMark` + `SttEndDoc` (`viewsrch.cxx:481-507`, `:566-578`); it also replaces the global search item [SRC + INF] |
| `postUnoCommand(".uno:ReportWhenIdle", {"idleID":…}, …)` | **no** (handled synchronously, not dispatched: `init.cxx:5481-5497`) | yes: `UNO_COMMAND_RESULT` with `commandName` and `idleID` (`:1414-1430`) | yes | starts an `Idle` at `TOOLKIT_DEBUG` (`include/vcl/task.hxx:39`). It fires only in a yield with no user event pending (`svpinst.cxx:442-447`) and no more urgent ready task, so it waits for Writer's `LOWEST` `SwDocIdle` (`lo/sw/source/core/doc/DocumentTimerManager.cxx:49`). Delay rule: no delay on svp (`scheduler.cxx:574-577`; `AnyInput` timer-only, `svpinst.cxx:549-554`). One outstanding per document (`assert` `init.cxx:5483`; with `NDEBUG` a second call overwrites `msIdleId`). A quiescence marker, not a queue position. Never used in this repo (grep) [SRC + INF] |

**First-hop limit (applies to every FIFO marker and to "post the command itself").**
- Example sequence:
  - The engine posts K_in and K_up, then marker M: queue `[K_in, K_up, M]`.
  - K_in runs and posts A, the `AsyncAccelExec` hop (`acceleratorexecute.cxx:223-226`): queue `[K_up, M, A]`.
  - M runs before the move.
- A marker that re-posts itself once from its handler would land behind A. The depth needed in general is not bounded by source (dispatcher re-post, other posters). [INF from SRC]

## Q6. A marker through internal API

- **Callable from the engine thread: yes, already done today** [SRC + INF]:
  - Every posted key reaches `Application::PostUserEvent` from the engine thread, inside `doc_postKeyEvent`'s guard (`init.cxx:4813`, `:4825` → `unotxdoc.cxx:4012` → `lokhelper.cxx:1290`).
  - `PostUserEvent` takes the SolarMutex only to create the default window lazily (`lo/vcl/source/app/svdata.cxx:268-283`) or for `bReferenceLink` (`svapp.cxx:1075-1079`).
  - The list and the wakeup use their own `std::mutex` (`salusereventlist.hxx:113-119`, `svpinst.cxx:135-148`).
  - Calling it under a `SolarMutexGuard`, as LOK does, is the same shape.
- **What the translation unit needs** [SRC]:
  - `include/vcl/svapp.hxx` (declares `PostUserEvent`/`RemoveUserEvent`, `:800-807`) and `include/tools/link.hxx` (`LINK_NONMEMBER`/`makeLink`, `:74-79`, `:184-187`).
  - The engine comment says `vcl/svapp.hxx` cannot be included from the public-header TU (`src/probe_engine.cpp:131-136`). So: a TU compiled `-std=c++20 -DLIBO_INTERNAL_ONLY` with `E1_CPPFLAGS`.
  - Precedent: `src/a11y_tree_probe.cpp` (header `:1-31`; rules `wsp/Makefile:1118-1132` for v4 and `:1856-1861`/`:1877-1881` for v5; also v10, v13, v14). The **v15–v22 product rules do not link it**: v22 objects are `E2_C_SOURCES` = `sdk_api, probe_engine, unoembind_stub, editor_api` (`Makefile:43-44`, `:65`, `:1763-1764`, `:1799-1802`).
  - `Link`'s layout changes with `DBG_UTIL` (`link.hxx:127-165`). The core build has `ENABLE_DBGUTIL=` empty (`wasm-lite/build-headless-probe/config_host.mk:176`), so the TU must not define it.
- **Library**: `Application::PostUserEvent` is in vcl (`svapp.cxx:1064`). The link line pulls the core's full `soffice.js.linkdeps` with `-sERROR_ON_UNDEFINED_SYMBOLS=1` (`Makefile:867-883`). Per `REACHABILITY.md` cited at `Makefile:1127-1129`, `libvcllo.a` is on it [SRC + EVID].
- **Alternative**: the out-of-tree mangled-name declaration trick already in the engine (`class Application { static bool Reschedule(bool); … }`, `src/probe_engine.cpp:121-160`). For `PostUserEvent` it would also need a layout-identical `Link<void*,void>` and `ImplSVEvent*` [INF].
- **Hazards** [SRC + INF]:
  - The handler runs on `lo_startmain`, with the tick's SolarMutex held (`svpinst.cxx:303-306`), inside a `noexcept` lambda: a throw aborts (`salusereventlist.cxx:116-120`).
  - If the engine thread waits for the marker **while holding the SolarMutex**, the next tick's `SolarMutexGuard` blocks in the main-thread `doAcquire` (`svpinst.cxx:333-372`). That is a deadlock.
  - Waiting on the engine's own condvar without the SolarMutex follows the existing pattern (`engineLoop` waits at `:6447-6582`; `dispatch` runs outside `gState.mutex`, `:6589-6590`). It requires today's lock order: LOK thread = SolarMutex, then engine mutex. The engine must never call LOK while holding `gState.mutex` or `gMergeMutex` (the rule stated at `src:588-589`).
  - Running the document command itself inside the posted event would execute it on `lo_startmain`. Any `IdlesLockGuard` would then be built on the main thread, and the wait branch requires `!IsMainThread()` (`scheduler.cxx:285`). The first-hop limit (Q5) still applies.

## Q7. Candidate C (unipoll)

1. Unipoll = `SAL_LOK_OPTIONS=unipoll` before the hook, plus `runLoop` registering poll callbacks (`init.cxx:8083-8089`, `:7722-7743`; `lok.cxx:50-54`). Under it, posted events run inline (`lokhelper.cxx:1283-1288`), accelerators dispatch synchronously (`acceleratorexecute.cxx:213-221`), and `postUnoCommand` adds no `SynchronMode=false` (`init.cxx:5316`). Only the `OXSDK_MAINLOOP_ENGINE` profile does this (`src:6853-6931`), calling `Application::Execute` itself because `runLoop` returns at once (`src:6904-6917`; `findings/021-…md:226-236`). [SRC + EVID]
2. The `#error` (`src:15-17`) is our wiring gap, not a core limit. Option B's stage deadlines and its 15 ms undo poll exist only in the blocking `engineLoop` (`src:6497-6533`). `mainLoopDrainCommands` (`src:6688-6752`) synthesizes only the selection-barrier boundary and format-barrier deadlines. It has no `gEditorPending` 250 ms readback either, which is finding 096's fix. [SRC]
3. Finding 040: `IdlesLockGuard` built off the VCL main thread waits on `m_inExecuteCondtion` (`scheduler.cxx:280-299`). The only `set()` is in `Application::Execute`'s fallback loop (`svapp.cxx:361-367`), which is unreachable on Emscripten because `DoExecute` never returns (`svpinst.cxx:308-316`). Measured entries: `doc_destroy`, `doc_getTextSelection`, `doc_getSelectionTypeAndText`, all destroying a frame-bearing `SwDoc` (`findings/040-…md:14-27`, `:205-215`). [SRC + EVID]
4. In unipoll the engine thread is the VCL main thread (`InitVCL` in the hook, `init.cxx:8385-8387`), so by source 040's wait branch would not be taken [INF]. Ruling 4 lists 040 and the `#error` as constraints and calls C "a measurement question" without saying why 040 applies (`ev/link-batch/review/ruling-4.md:56`).
5. `emscripten_set_main_loop_arg(..., 1)` throws `'unwind'` (`libeventloop.js:504-505`), so engine state must live outside that frame (`src:6853-6860`). Commands then run from the poll callback inside `ImplYield` with the SolarMutex released (`svpinst.cxx:471-481`). Asynchron slots and the LOK callback flush still go through `PostUserEvent`. The mainloop profile ran end to end once, before v20's machinery (`findings/021-…md:628-631`). [SRC + EVID]

## Q8. Completion evidence (the merge path, option B)

- **Before the key** [SRC]:
  - `P_start` = `getCommandValues(".uno:Undo")` before K1 (`src:4243-4244`; reader `:3499-3508`).
  - After K1, Escape, K2, Escape: `P0` is read and must equal `P_start`, otherwise `restore-mutated` (`src:3847-3856`; `merge_key_undo.hpp:370-377`).
- **The key** [SRC]: the user's own Backspace or Delete is posted (`src:3857-3867`).
- **The proof** [SRC]:
  - The **whole payload** is re-read until it differs from `P0`: every `MergeKeyPollMs = 15` ms (`src:604-605`; engine-loop wake `:6497-6533`, step `values[0]=3`, `:4178-4186`) and after any callback (`MergeTicket.afterKey`, `:599`).
  - A change parsed with ≥1 action is `verified-key-undo` (`merge_key_undo.hpp:391-414`; parser `:330-365`). An unchanged payload at `MergeStepDeadlineMs = 2000` (`src:603`) is a `key-deadline` refusal (`merge_key_undo.hpp:398-403`).
  - The whole payload is compared, not the count, because the count saturates at the undo limit: `actionsAfter` stuck at 100 (`findings/117-…md:17`) [EVID].
  - Reads hold the SolarMutex, so a read cannot fall inside a hop. It can fall between hops, which only yields `Pending` (`src:6505-6507`) [SRC + INF].
- **What it proves**: some undoable action was recorded after `P0`, not which one. A key that changes nothing proves nothing; its fate is the 2000 ms refusal and a reopen (spec §13.4 review question 1; `ruling-4.md:56`) [SRC + INF].
- **Recorded cost** [EVID]:
  - v20 WASM shakedown: engine `keyToUndoMs` [min, median, max] = **[30, 32, 33] ms** (Chrome and Firefox, M2-4, 105/105 presses). M2-1b engine 30–31 ms; runner end to end **129–155 ms** for the whole barrier plus key (`ev/link-batch/v20-shakedown/merge/README.md:10`, `:46-47`).
  - v19: [30, 32, 36] ms (`ev/v19/RESULT.md:26-27`).
  - Before finding 117's poll, on v18: median **2001 ms** over blank paragraphs (no callback after the key), 28–49 ms for ordinary merges, 628–633 ms for typing-then-merge (`findings/117-…md:19`, `:22`).
- The cost of each `getCommandValues(".uno:Undo")` read is not recorded.

## Open / not determined

- The ~10 ms one-event-per-tick pacing on WASM is inferred from source (Q2). It is not measured directly; browser `setTimeout` clamping for nested timers was not read.
- Whether Writer's mouse handling (place-caret, drag) posts further hops after `MouseButtonDown/Up` was not read.
- Return and Shift+Return: the accelerators map to `.uno:InsertPara`/`InsertLinebreak` (xcu `:6891`, `:6903`). Writer's `KEY_RETURN` case handles special states inside KeyInput (OLE, fly, glossary, `NumOff`, autoformat; `edtwin.cxx:1985-2034`), and otherwise falls to `KeyToView` [INF]. The hop count for a posted Return was not measured. The engine dispatches both as `.uno:` (sync) today.
- `.uno:ReportWhenIdle` on WASM: its latency after edits (Writer `LOWEST` idles), starvation under continuous input, and the `NDEBUG` behaviour with two outstanding are not measured.
- Posted `.uno:ExecuteSearch` miss: whether the selection and caret come back unchanged is not measured.
- How often a posted dispatch meets a locked dispatcher and is re-posted (`dispatch.cxx:996-1003`) is not determined.
- Whether `LOKPostAsyncEvent`'s `setView`/`GrabFocus` (`lokhelper.cxx:1191-1203`) emits callbacks for an otherwise neutral posted event is not determined.
- Why ruling 4 counts finding 040 against C (Q7 item 4) is open.
- No hop analysis was done for Calc/Impress; everything here is Writer.

# Brief for fable, ruling 1 (v23): the ordered-commands batch's scope, which candidate is measured first, and whether now is 0.2.28's ddev window

**Authority.** The owner, 2026-10-20 ~06:40, away from the desk: 「我不在座位，請自主執行任務，另外我授權給fable 代我做決策」. Earlier the same morning the owner chose "A+B":
- A: start the ordered-commands batch's preliminary work (native measurements, then the spec with its criteria pinned first, then review; no link, no ddev).
- B: prepare host 0.2.28, finding 155. The option text the owner chose said 「安裝等你給時段」.

You decide in the owner's place. **§1 of your ruling must be plain-language zh-TW for the owner** (台灣正體中文白話); the rest is English. The main session commits your text verbatim and re-checks every number before acting.

**Read by path (the tree is at the commit that adds this brief):**
- `handoff/PLAN-2026-10-20-ordered-commands-v23.md`: the census (18 items, four tiers), the order of work, the scope options (§4).
- `handoff/link-batch-v23/facts-lok-command-ordering.md`: written by an opus subagent, every claim cited; its SUMMARY is the first 30 lines.
- `specs/SPEC-M3-link-batch.md` §13.2–§15.1 (the candidates A/A′/B/C, the three fixed review questions, L-C-number-or-indent).
- `findings/137-…md`, `findings/evidence/link-batch/review/ruling-4.md` (`:50-62`), `ruling-5.md`.
- `findings/evidence/link-batch-v21/native/142-ctrl-home-end/README.md` §11-12.
- `CLAUDE.md` 「驗收判準的形式」 §1–§11 applies to any criterion you write.

**Constraints:** read-only. No ddev command, no browser, no make, no build, nothing written. Targeted reads only (no repo-wide search).

## Facts (F1–F12). ✔ = re-read in source by the main session today; the rest are the facts sheet's, unchecked

- **F1 ✔ The two-hop key.** In threaded LOK, an accelerator-routed key is posted (`SfxLokHelper::postEventAsync` → `Application::PostUserEvent`, `libreoffice-26-8/sfx2/source/view/lokhelper.cxx:1273-1290`). When it runs, `AcceleratorExecute` posts the actual command as a second user event, `AsyncAccelExec` (`svtools/source/misc/acceleratorexecute.cxx:213-226`, `:496-501`; `vcl/source/helper/evntpost.cxx:42-46`). Under unipoll the same branch dispatches synchronously (`:213-214`, 「tdf#130382 - all synchronous really」).
  - Two-hop keys: arrows, Home/End, Shift+arrows, Ctrl+Home/End, Ctrl+A, and Backspace/Delete through `.uno:SwBackspace`/`.uno:Delete`.
- **F2 ✔ Printable characters take one hop.** `SwEditWin::KeyInput` flushes the character at once when `AnyInput(KEYBOARD)` is false (`sw/source/uibase/docvw/edtwin.cxx:2678-2690`). That `AnyInput` is false on svp is the sheet's (`vcl/headless/svpinst.cxx:549-554`).
- **F3 ✔ Already observed natively.** In threaded native LOK, "Ctrl+Home then a Backspace that Writer handles inside KeyInput" ran the Backspace first, 3/3 back-to-back and 3/3 queued from a callback (`142-ctrl-home-end/README.md` §12). **So a FIFO of posted keys is not order-preserving across one-hop and two-hop keys.**
- **F4 ✔ The listener forces SYNCHRON.** `doc_postUnoCommand` adds `SynchronMode=false` in threaded LOK (`desktop/source/lib/init.cxx:5316-5321`). But `SfxDispatchController_Impl::dispatch` sets `nCall = SfxCallMode::SYNCHRON` whenever a result listener is passed (`sfx2/source/control/unoctitm.cxx`, `if ( rListener.is() )`). The engine's `postUnoCommand(…, true)` is therefore synchronous and jumps the queue. With `false` the command is posted, but behind a key's first hop only (sheet item 7: it runs before that key's `AsyncAccelExec`).
- **F5. Every synchronous call the engine makes jumps the queue:** `paste` (typing, replace, Markdown), `setTextSelection` (three separate calls), and every `postUnoCommand(…, true)` (Delete, SwBackspace, InsertPara, InsertLinebreak, Bold/Italic/Underline/Strikeout, Undo/Redo). Posted are every `postKeyEvent` and `postMouseEvent` (sheet Q1 table).
- **F6. One FIFO; on WASM, one user event per main-loop tick, ticks ≥ 10 ms apart.** The pacing is inferred from source, not measured (sheet Q2, Open).
- **F7. No re-entrancy found on WASM.** `Reschedule` is a no-op, so no synchronous command runs pending keys mid-command. A synchronous command can still run **between** a key's two hops. Native threaded results on re-entrancy do not transfer (sheet Q3).
- **F8. No public-LOK marker** that is FIFO-positioned, observable and state-neutral at once. `.uno:ReportWhenIdle` is neutral and observable, but it signals quiescence (the lowest-priority idle), not a queue position; it is unused here and its latency is unmeasured. With internal API, `PostUserEvent` is callable from the engine thread. That needs a `LIBO_INTERNAL_ONLY` translation unit (precedent `a11y_tree_probe.cpp`, not in the product link) and has a deadlock hazard if the engine waits while holding the SolarMutex (sheet Q5, Q6).
- **F9. Unipoll (C).**
  - Under unipoll, posted events run inline, accelerators are synchronous, and `postUnoCommand` adds no `SynchronMode=false`. So **no key is ever pending** (sheet Q7.1).
  - The `#error` at `src/probe_engine.cpp:15-17` is our own wiring gap. The merge's deadlines, its 15 ms undo poll and the 250 ms readback (finding 096's fix) exist only in the blocking `engineLoop` (Q7.2).
  - Finding 040's wait is taken only off the VCL main thread. Under unipoll the engine thread *is* the main thread, so by source it would not be taken [INF]; ruling 4 does not say why 040 counts against C (Q7.3-4).
  - The `OXSDK_MAINLOOP_ENGINE` profile ran end to end once, before v20's machinery (Q7.5).
- **F10 ✔ Collabora's own WASM build runs unipoll.** `cool-26-04/kit/SetupKitEnvironment.hpp:66` sets `"unipoll"`, and `setupKitEnvironment` is called on the WASM path (`kit/Kit.cpp:4353-4357`, `MOBILEAPP && !IOS && !QTAPP && !MACOS && !_WIN32`). How their loop is driven on Emscripten was not read.
- **F11. A's proof.**
  - The merge path posts the user's own key and re-reads the whole `.uno:Undo` payload every 15 ms. Engine `keyToUndoMs` is [30, 32, 33] ms on v20 (105/105 presses); the barrier plus key end to end is 129–155 ms (sheet Q8).
  - The proof is by effect, so it is hop-agnostic. But it covers deletes only, and a key that changes nothing proves nothing (a 2000 ms `key-deadline`).
- **F12 ✔ Native arms need no WASM link.** They are standalone C++ LOK clients (`lok_init_2`) against the native LO install (e.g. `142-ctrl-home-end/tool/f142_native_ctrl_home_end.cpp:329`). A native unipoll variant would set `SAL_LOK_OPTIONS=unipoll` and drive `runLoop` from the client [INF; not built]. A WASM unipoll or marker profile needs a link, the owner's `make`; **this round has no build authorization**.

## Main session's reading (a lean, not a premise; tell me where it is wrong)

- **A′ as stated is broken by F1–F3.** Typing as posted key events is one-hop, so "arrow then type" would run the character before the arrow's move. The same holds for any format sent as a posted accelerator behind a one-hop key.
- **B as stated is broken by F1 and F4.** A single marker posted after a key's KEYUP runs before the key's `AsyncAccelExec`.
  - A hop-aware marker (re-post once when it runs) assumes exactly two hops. A quiescence point (`ReportWhenIdle`, or an internal "user-event list empty" check) does not assume a hop count, but it waits for idles too, and its latency is unmeasured.
  - B also needs a new internal-API translation unit.
- **A works for deletes whatever the hops** (the proof is by effect). It closes L-C-number-or-indent. It does nothing for typing or formats, and it has the "key that does nothing" hole.
- **C makes the property hold by construction** (F9), and Collabora ships it on WASM (F10). Its cost is real engine work: our loop wiring (the merge's deadlines and poll, the 250 ms readback). Plus unknowns: rendering/callback timing, idle layout driven from our poll, finding 122's latency, and whether 040 applies at all.
- **Lean:** measure **C first, natively**, with a unipoll variant of the native harness, no link. Measure it on the shapes that matter:
  - 137's three effects;
  - 142's reorder pair (F3);
  - an arrow then a typed character;
  - an arrow then Bold;
  - Shift+Arrow then Delete;
  - the L-C-number-or-indent positions (i)–(iii) with their `.uno:Undo` tops.
  
  A is the fallback for deletes if C is blocked. B is reformulated (hop-aware or quiescence) only if both fail.
- **Scope lean: PLAN §4 A** (tiers 1+2). Shift+Arrow is the owner's named request, and the ordering exists to make it safe.

## Questions

- **Q1. Scope:** PLAN §4 A, B or C, or another cut. What is the default if the chosen candidate turns out not to be buildable?
- **Q2. Candidate and first measurements:** which candidate (or candidates) are measured first, and on what? Say native or WASM; WASM needs the owner's link. Name the arms, their positive controls and red cases, and what reading moves the decision. Is A′ withdrawn on F1–F3? Is B as stated withdrawn? Must the model (`extend_completion_model_test.cpp`) be re-run before or after the native arms? Any spec-level consequences to record now (for example, the three fixed questions under C)?
- **Q3. 0.2.28's window:** is now (owner away, daytime; at 06:43 `ddev list` showed only `litecore` OK) a window for 0.2.28's install and H-155 chain (v22 spec §14.4)? Or does the owner's chosen option text 「安裝等你給時段」 bind, so that the delegation does not reach it? The main session's lean: it binds; do not install.
- **Q4. What does this brief get wrong or leave out?**

**Shape:** `## 1. 裁決（白話，給擁有者）`, then `## 2. Answers (English)` (numbered items, each with its form per CLAUDE.md §1 and its default per §2), then `## 3. Facts checked`, then `## 4. What the main session does next, in order`.

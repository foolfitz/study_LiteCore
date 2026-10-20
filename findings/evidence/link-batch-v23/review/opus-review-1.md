# Two-seat review 1, opus seat: v23 under C, before any engine code (SPEC-M3-ordered-commands §10 step 3)

Brief: `R/findings/evidence/link-batch-v23/review/REVIEW-BRIEF-two-seat-1.md` (tree `152949f5`, brief written at `76fe206f`). Read-only on the repository; every experiment ran on a `git archive HEAD` extraction under this directory (`tree/`). No make, no ddev, no browser, no LibreOffice process. `g++` of the model and running it, and `python3 -I` over committed outputs, are the only things that ran.

Abbreviations as in the brief (`R`, `lo/`, `src/`, `ev/`), plus: `oc/` = `ev/native/ordered-commands/`, `pe` = `src/probe_engine.cpp`, `client` = `R/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js`, `model` = `R/wasm_sdk_probe/tests/extend_completion_model_test.cpp` (sha256 `6201a62d…`, identical to the scratch copy), `spec` = `R/specs/SPEC-M3-ordered-commands.md`. **read** = I read the cited line; **inferred** = my conclusion from read lines; **measured** = produced by an experiment in this directory from committed data.

## Verdict table

| # | question | verdict | one line |
|---|---|---|---|
| 1 | broken C → C-HOLDS, broken anyInput → N1-HOLDS | **COUNTEREXAMPLE** (in-model) | N1a's `INVALIDATE_TILES` clause is empty: 0 tile callbacks in all 235 counted and 47 smoke processes, every mode; d1's Backspace and d4's Bold can be dropped by a broken core and still land as seq; N1a's window ends 1500 ms after the first poll and skips join200. No misorder passes the landing. |
| 2 | correct C → FAIL / NE | **NONE** (committed arms) | No in-model false FAIL/NE found for the committed fixtures; two NOTEs for future arms (init-dependent landing fields; idle-job tile invalidations once tiles become visible). |
| 3 | non-vacuity | **COUNTEREXAMPLE** | "the X step fired" is constant `true` outside q (`oc_native.cpp:371`), so a d4 cell with no ops reads PASS (out-of-model input); 15/100 N1 ops have no reply-type callback at all before their first poll, incl. d7ii whose key changes the document (in-model). |
| 4 | exit and completeness | **COUNTEREXAMPLE** (in-model) | D7 cells never gate the verdict (a missing d7iii round → `C-HOLDS`, exit 0); D8 and N1a run on unclean cells and print `C-FAILS`/`N1-FAILS` with exit 0; D7's "5/5" is printed from round 1 only (the data is 5/5). |
| 5 | red-case coverage | (table) | read_results: 5 of 25 rules have a case, and the ruling's red case (b) "rounds disagree" is not what the one-round self-test exercises. read_n1: 7 of 18; five of the six N1a type names are never exercised. |
| 6 | the three fixed questions under C | **COUNTEREXAMPLE** | (1) NONE found. (2) Writer's undo grouping makes the `.uno:Undo` payload byte-identical after a Backspace that deleted a character (22nd+ press through a run of equal characters), so "undo unchanged" does not mean "nothing happened". (3) A click that selects an object defers `SwView::SelectShell` to a 120 ms timer: an effect pending past return and past the next poll. |
| 7 | addendum §2.2's vocabulary | **COUNTEREXAMPLE** | The grouping case yields either a `verified-boundary-noop` that the client accepts with the wrong meaning, or a reply §5.4/§5.5 do not name. A literal §5.2 would refuse a collapsed-caret Bold that Writer applied (its state arrives in the command's own flush, measured). `verified-key-undo` with `actionsAfter` 0: NONE. |
| 8 | addendum §2.3's anyInput rule | **COUNTEREXAMPLE** (bullet 1) | The rule bounds the wait to one scheduler task per tick, not to a short wait. The non-layout idle jobs (spelling, smart tags, autocomplete, word count, fields) never consult the LOK anyInput. Bullets 2 and 3: NONE by source; NOTE on PaintTile sharing the command queue. |
| 9 | the model's mode C | **SHOULD** (with a COUNTEREXAMPLE in (b)) | The zero follows from the loop shape and from completions chosen by an oracle (`keyChanged`). A mutation that labels 174,672 real deletions `verified-boundary-noop` leaves the committed test `ok` (exit 0). The forged definition compares rectangles only. Printed run counts are 22–135× the distinct C scenarios. |

Correction to the brief: it names `oc/smoke-n1/NOTES.md`; that file does not exist at HEAD (`oc/smoke-n1/` holds `arms.json`, `build.txt`, the cells, `reader-output.txt`, `run-log.jsonl`, `self-test.txt`) — **read** (directory listing).

---

## Part A — the two native readers

Reproduction first (measured, `native/a1-*.txt`): `read_results.py oc/out` and `read_n1.py oc/out-n1` print exactly the committed `reader-output.txt` (minus the `# exit` line), exit 0; both self-tests pass (5/5, 6/6). The run logs agree with the README: 165 and 70 lines, one per cell, no duplicates, all exit 0, load1 ≤ 0.39/0.44 — but neither reader reads `run-log.jsonl`; those README sentences are hand readings (**read**, `oc/README.md:7`, `:97`; `read_results.py:128-176`, `read_n1.py:45-79` never open it).

### Q1. A broken C that reads C-HOLDS, or a broken anyInput that reads N1-HOLDS — COUNTEREXAMPLE

**1a. Landing comparison (misorder): NONE.** Every decision arm has two ops, so there are only two orders, and the reader's NE gate requires q (the other order) to land differently from seq (`read_results.py:212-213`, **read**). The recorded landings differ in text for d2/d2p/d3/d5/d6, in list kind for d1, in run weight for d4 (`oc/out/reader-output.txt`, **read**). A misordered pair cannot pass.

**1b. Landing comparison (a dropped op): COUNTEREXAMPLE, in-model.** A broken core that silently drops the *second* op of d1 or d4 lands exactly as seq:
- d1: in Writer's order the Backspace runs at the document start of a plain P1 and is a no-op, so "Backspace dropped" saves the same document with the same caret (**inferred** from the seq landing in `oc/out/reader-output.txt` and `run_arms.py:42-43`).
- d4: in Writer's order `.uno:Bold` at a collapsed caret leaves no bold run in the saved file, so "Bold dropped" saves the same shape. The landing's caret is also unchanged (**inferred**; the trigger-only selection gives the same locator pair `["", "abcd"]`, `oc_native.cpp:531-540`). The D8 second rule is vacuous for both arms because neither op changes the undo payload or the selected text (`read_results.py:250-253`, **read**).
- What the raw output shows and the reader does not read (measured, `native/a9_bold_state.out`, `native/part_a_experiments.out` A8): in both seq and unipoll, d4's Bold returns `UNO_COMMAND_RESULT success:false, wasModified:false`, and the evidence that it ran is `STATE_CHANGED .uno:Bold=true` plus `.uno:ModifiedStatus=true` in the op's own flush. So "D4 measured explicit Bold args in Writer order under C" (facts sheet A7) is established for order, not for the Bold having run.
- Out-of-model companion (NOTE): removing the ops from all five d4 unipoll records and copying seq's save in reads `d4 PASS 5/5`, `C-HOLDS`, exit 0 (measured, A2).

**1c. D8 passing when the effect is not there at return: NONE, with vacuity.** The key check for d5 (`selText != ''`) and d7i/ii/iii (`undo != before`) is sound for these fixtures: the trigger is a plain move with no selection and no undo action (`read_results.py:241-249`, `run_arms.py:52-63`, **read**). But:
- D8 never sees a plain move's effect. `runOp` reads only selection and undo at return (`oc_native.cpp:303-310`, **read**), so the README's "every measured step's last op already reads at return what the settled window reads" (`oc/README.md:47`) holds for undo and selected text, not for the caret.
- The second rule is vacuous for d1, d4 and d7plain (above).

**1d. N1a missing a late reply-type callback: COUNTEREXAMPLE, in-model.** Four independent gaps:
1. **`INVALIDATE_TILES` is never recorded.** The count is 0 in `out/` (165 cells, seq/q/unipoll), `out-n1/` (70), `smoke/` and `smoke-n1/` — even for threaded typing (measured, `native/a11_tiles_anywhere.out`; A5).
   - The harness paints one 256-px tile over (0,0)–(3840,3840) twips at load (`oc_native.cpp:562-563`, **read**). LOK drops every invalidation outside the painted area, and all of them when it thinks nothing was painted (`lo/desktop/source/lib/init.cxx:1699-1717`, **read**).
   - Why even the in-box edits produce nothing was not read further.
   - Consequence: the README's "No … `INVALIDATE_TILES` arrived after an op's first poll" (`oc/README.md:105`) is true and empty. A C whose tile invalidations come late reads `N1-HOLDS`. This is the "X did not happen" arm without a positive control.
2. **The window ends 1500 ms after the first poll.** `lateCallbacks` is collected by the third micro-step, after a fixed 1500 ms idle (`oc_native.cpp:483-503`, **read**).
   - A reply-type callback that arrives later is attributed to the *next* op's pre-poll region for a non-last op. For the last op it falls into the 2000 ms settle, which only the `measured.callbacks` array holds (`:503`, `:507-521`). `read_n1.py` never reads that array (`read_n1.py:91-95`).
   - Not observed: the latest timer-class callback was 762 ms (`oc/README.md:108-112`).
3. **join200's uni1ai cell is excluded from N1a** (`read_n1.py:86`, **read**), although it is the only long-document arm.
   - tleave (also not a §3 arm) is included.
   - In the committed data join200 has only late `STATE_CHANGED` (measured, `inspect_n1.out`), so nothing is hidden today.
4. **Presence is not checked.** N1a fails only on a *late* reply type and never asks that the callbacks a reply depends on arrived at all (`read_n1.py:91-95`, **read**); see Q3.

**1e. A broken anyInput that reads N1-HOLDS: NOTE (out of the readers' reach).**
- N1 measures the *harness's* anyInput, which answers `gReplyPending` and clears it at the first poll (`oc_native.cpp:130-131`, `:480`, `:487`, **read**). It cannot say anything about the engine's implementation of §5.7 rule 4.
- An anyInput stuck at `true` would pass N1c ("uni1 slower than uni1ai") and N1a. It would also starve Writer's idle layout, which interrupts itself whenever the LOK anyInput is true (`lo/sw/source/core/layout/layact.cxx:95-99`, **read**). The committed harness cannot produce that input (out-of-model).
- Spec §9.2 has no cell that checks rule 4 on the engine (`spec:184-198`, **read**).

### Q2. A correct C that reads FAIL or NE — NONE for the committed arms

- **seq rounds varying for an unrelated reason: NONE in the data.** All five rounds agree in every arm and mode, including the D7 undo tops (measured, A3). The landing fields are values, not style names, except `listStyle` (`read_results.py:107-119`, **read**).
- NOTE (inferred): `listStyle` is an automatic style *name*, and the locator's line prefix and suffix depend on line breaking. The unipoll harness runs without `Desktop::Main` (`oc_native.cpp:19-44`, `smoke/NOTES.md:29-33`), so extension-registered dictionaries (hyphenation) are a plausible difference from seq (`lo/desktop/source/lib/init.cxx:8296-8300`, cited in addendum §2.5.6).
  - A future fixture with hyphenated long paragraphs, or list-style renaming on export, could make a correct C read FAIL for a reason unrelated to order.
  - To settle it: one fixture with `fo:hyphenate="true"` and a paragraph longer than one line, seq vs unipoll.
- NOTE (conditional, inferred): once tiles become visible to the harness (Q1d.1), N1a's type-level rule would go red on tile invalidations from idle jobs no reply depends on.
  - Online spelling and smart tags call `InvalidateWindows` from the idle (`layact.cxx:2174-2175`, `:2201-2202`, **read**).
  - N1a cannot tell "this command's tiles late" from "an idle job's tiles".
- D8's second rule under unipoll would go red if a timer changed undo or the selection after return. No such timer was found for the committed fixtures. `SwView::TimeoutHdl` runs `SelectShell` with undo off (`lo/sw/source/uibase/uiview/view.cxx:617-620`, **read**).

### Q3. Non-vacuity — COUNTEREXAMPLE

- **"the X step fired" is vacuous outside q.** `Measured::fired` defaults to `true` and is assigned only in q mode (`oc_native.cpp:371`, `:452`, **read**). The reader lists it as a clean-cell condition for every mode (`read_results.py:20-22`, `:157-158`).
  - Out-of-model demonstration: d4 unipoll with `ops: []` reads PASS (A2).
  - The rule to withdraw is the README's claim that every cell is checked for "the X step fired" (`oc/README.md:55`). It is a q-only check.
- **Topology: established for unipoll by D8 on d5 alone** (a decision arm, so it must be clean). The D7 part of D8 skips missing cells silently (`read_results.py:239-240`, **read**).
  - With all D7 arms removed from `arms.json` the verdict is still `C-HOLDS` (A13, out-of-model input).
  - With env missing on a threaded run labelled unipoll, d5 goes NE but D8 prints `C-FAILS`, exit 0 (A4, out-of-model input; the committed runner always sets the variable, `run_arms.py:110-112`).
- **N1a per-op presence, in-model.** In 15 of 100 uni1ai ops no reply-type callback arrived between the op's return and its first poll (measured, A6): d1's, d7ii's and d7plain's Backspace, 5/5 each.
  - d1 and d7plain are no-ops, as expected.
  - d7ii's Backspace changes the document (`Number On/Off`, `oc/README.md:41`) and still emits none of the six reply types. Only the undo payload shows it, and the bullet's repaint would be an `INVALIDATE_TILES` the harness cannot see.
  - For that op N1a is satisfied by absence.
- **N1c's meaning is wider than its reading.** PASS shows that *some* scheduler task ran between the flush and the first poll in uni1 (≈1.1 ms natively, `oc/README.md:115-119`). It does not show that idle layout ran, which the pinned reading assumes ("延遲相同＝沒有版面整理的閒置工作跑起來", `spec:180`).
  - The criterion as pinned is satisfied; its label is inferred.
  - To settle it: rerun one join200 uni1 round with `SAL_LOG=+INFO.vcl.schedule` and name the task.

### Q4. Exit and completeness — COUNTEREXAMPLE (in-model)

- **D7 completeness is not counted.**
  - D7 arms are `decides: False`, so their unclean cells are only appended to the printed line (`read_results.py:227-234`, **read**), and D8 skips cells without a `measured` record (`:239-240`).
  - Deleting d7iii's unipoll round 4 (an honest crash leaves exactly that) prints `C-HOLDS`, exit 0 (measured, A12).
  - The D7 tops are printed from round 1 only (`read_results.py:229-233`, **read**), so spec §3's "(5/5)" and the README's "5/5 each" (`oc/README.md:36`) are not tool-established. They are true in the data: all five rounds are identical in every D7 arm and mode (measured, A3).
- **Verdicts from unclean cells with exit 0.**
  - D8 is computed on every cell that has a `measured` record, clean or not (`read_results.py:236-253`), and `any('unipoll' in x for x in d8)` forces `C-FAILS` (`:256`). That contradicts the reader's own rule "An unclean cell makes its arm NE" (`:20-22`).
  - Measured, A7: d5 unipoll r1 with `saved:false` and an empty selection at return prints `d5 NE … not saved`, then `VERDICT C-FAILS`, exit 0. The trigger is in-model in principle: a failed save or a capped settle together with a D8 miss.
  - `read_n1.py` does the same: N1a violations are collected from every cell regardless of its problems, and any violation is `N1-FAILS`, exit 0 (`read_n1.py:91-95`, `:135-136`, **read**).
  - N1c FAIL is likewise reached without consulting `problems` (`:118-127`, `:135`).
- **Missing round/arm/mode:**
  - Decision arms: counted (`no output` → unclean → NE, `read_results.py:131-133`, `:208-209`).
  - Modes: hard-coded, so counted.
  - Arms: read from the run's own `arms.json` (`:194`). It is runner-generated from the committed table (`run_arms.py:98-99`), so the arm list is tool-closed only as long as nobody edits the out dir (A13, out-of-model).
  - `--rounds N` is free and the verdict line does not print N.
- **Duplicates: NONE in-model** (one file per cell, opened `'w'`, `run_arms.py:126`). Out-of-model: a concatenated jsonl is read by its first `measured` record (`read_results.py:153`).

### Q5. Red-case coverage

`read_results.py` (self-test at `:266-321`; every case runs on a **one-round** smoke, `:275`):

| rule | where | self-test case |
|---|---|---|
| seq rounds agree, else NE | `:210-211` | none (impossible with one round) |
| q rounds agree, else NE | `:212-213` | none (impossible with one round) |
| q lands differently from seq, else NE | `:212-213` | none |
| unipoll rounds agree, else FAIL | `:214-215` | none (impossible with one round). Ruling 1 §2.6 red case (b) asked for "rounds disagree" (`ruling-fable-1.md:86`); the implemented (b) exercises the next rule instead |
| unipoll lands as seq, else FAIL | `:216-217` | (a) `:286-298`, (b) `:300-302` |
| no output / fatal / no done | `:131-142` | none |
| unipoll env `SAL_LOK_OPTIONS` | `:144-145` | (c) `:304-306` |
| unipoll init record | `:146-148` | none ((a) copies it in to stay clean) |
| seq/q env without `SAL_LOK_OPTIONS` | `:149-150` | none |
| env mode mismatch | `:151-152` | none |
| no measured / not fired / capped | `:153-160` | none |
| not saved / no or unreadable save / no locate | `:162-175` | none |
| unclean ⇒ NE (decision arms) | `:208-209` | (c) |
| D8: unipoll key effect at return, d5 | `:241-249` | (d) `:308-313` |
| D8: unipoll key effect at return, d7 undo | `:241-249` | none |
| D8: q key effect absent at return | `:246-249` | none |
| D8: last op at return equals settled | `:250-253` | none |
| verdict mapping | `:255-261` | control / (a) (b) (d) / (c) |
| exit code | `:334` | none |

`read_n1.py` (self-test at `:145-208`):

| rule | where | self-test case |
|---|---|---|
| N1a: any late reply type ⇒ FAIL | `:91-95`, `:135` | `late_cursor` (`:164-170`) for `INVALIDATE_VISIBLE_CURSOR` only. The other five names are never exercised, and `INVALIDATE_TILES` never occurs in any recorded run (A5), so a misspelt name would not be noticed |
| N1a NE on problems | `:130` | `no_anyinput` (verdict NE) |
| N1b control: late STATE_CHANGED every tleave round | `:101-108` | `no_control` (`:172-178`) |
| N1c PASS / FAIL / overlap NE | `:122-127` | control / `reversed_` / `equal` |
| N1c missing rounds ⇒ NE | `:119-121` | none |
| clean: no output, fatal, done, env mode, `SAL_LOK_OPTIONS`, init record | `:48-67` | none |
| clean: `anyInputRegistered` per mode | `:68-69` | `no_anyinput` (`:197-199`) |
| clean: measured, capped, op without `lateCallbacks` | `:70-78` | none |
| verdict mapping | `:135-140` | covered |

---

## Part B — the spec under C

### Q6. The three fixed questions (spec §7) — COUNTEREXAMPLE

First, the candidates the brief lists, one by one.

- **`SfxDispatcher` re-post (`lo/sfx2/source/control/dispatch.cxx:996-1003`): NONE.**
  - `PostMsgHandler` handles only requests that were already posted.
  - Its `xPoster->Post` at `:1002` is unreachable: it sits in the `else` of `if (!IsLocked())` under `if (xImp->bLocked)`, and `IsLocked()` returns `xImp->bLocked` (`:200-203`) (**read**).
  - A synchronous call on a locked dispatcher is dropped, not reordered (`:737-738`, **read**).
- **`Application::Reschedule`: NONE on WASM.** It returns at once when the system loop is set (`lo/vcl/source/app/svapp.cxx:400-406`), which Emscripten always sets (`lo/vcl/headless/svpinst.cxx:102-104`) (**read**).
  - Natively it yields. So any future *native* arm whose command reaches `swhtml.cxx:2609`/`:2647` (HTML/Markdown import) would nest the harness's poll callback, which has no re-entrancy guard (`oc_native.cpp:576-613`, **read**). That is a NOTE for the harness, not a product path.
- **`Scheduler::ProcessEventsToIdle`: NONE in the product.**
  - The only engine caller is the diagnostic `EditorDrainScheduler` (`pe:6166-6184`), compiled only under `OXSDK_FINDING_016_SCHEDULER_PROBE` (`pe:6397-6401`) (**read**).
  - Under C it would re-enter `ImplYield` with all events (`svapp.cxx:441-449`). The guard returns 0 (`pe:6827-6835`).
  - If a diagnostic profile ever defines that macro, §5.7 rule 1 is violated by construction.
- **Dialog: NONE as a reorder.** `Dialog::Execute` loops on `Application::Yield` (`lo/vcl/source/window/dialog.cxx:1067-1068`), which aborts on Emscripten in both topologies (`svapp.cxx:494-501`) (**read**).
  - The key paths open their read-only notices asynchronously (`edtwin.cxx:1980`, `:2134`, `:2441`, `:2695`, `:6044` → `wrtsh1.cxx:2862-2872`, **read**).
  - The reply would then say "nothing happened" while a LOK dialog window is open. That is not C-specific.
- **A posted `.uno:` with no listener: an effect pending past return; ordering safe.**
  - Under unipoll `doc_postUnoCommand` adds no `SynchronMode` (`init.cxx:5316-5322`).
  - Without a listener the call mode stays `RECORD` (`unoctitm.cxx:619`, `:655-657`), and an `Asynchron` slot is then posted (`dispatch.cxx:740-752`).
  - `.uno:Escape` is `Asynchron` (`lo/sw/sdi/swriter.sdi:1181-1191`), so the engine's comment-commit `postUnoCommand(".uno:Escape", nullptr, false)` (`pe:2878-2879`) runs on a later tick under C (**read**).
  - It is a user event, and the poll never runs on a tick that began with one (`svpinst.cxx:442-444`; `salusereventlist.cxx:59-136`, **read**), so it completes before the next poll (**inferred**).
  - None of the engine's key targets is `Asynchron`: `GoLeft` … `EndOfDocumentSel`, `SwBackspace`, `Delete`, `SelectAll`, `Undo`, `Redo`, `Paste` were all checked in the sdi files (**read**, scripted grep over `swriter.sdi` and `sfx.sdi`).
- **`postMouseEvent`: COUNTEREXAMPLE for objects, NONE for text.**
  - Mouse events run inline (`lokhelper.cxx:1283-1288`).
  - A plain text click goes through `SwEditWin::MoveCursor`, which clears `g_bNoInterrupt` around `CallSetCursor` (`edtwin.cxx:2966-2995`). So `SwView::AttrChangedNotify` runs `SelectShell()` synchronously (`view.cxx:567-587`) (**read**). D6 is consistent with that.
  - A click that selects a drawing object or frame sets `g_bNoInterrupt = true` (`edtwin.cxx:3289`), calls `SelectObj`/`EnterSelFrameMode` and returns with it still set (`:3874-3880`) (**read**). The change link then takes the deferred branch: `m_bAttrChgNotified = true; m_aTimer.Start()` (`view.cxx:569-574`, timeout 120 ms at `:844`).
  - So the dispatcher's shell stack (`SelectShell`), `NotifySelChanged` and `LEAVEREGISTRATIONS` happen in `TimeoutHdl` 120 ms later (`:600-622`) (**read**).
  - The flag also suppresses every further notify until then (`:567`). Under C the page's next command arrives about two ticks later, so it runs against the pre-click shell stack. Slots resolve per shell: `FN_BACKSPACE` has separate handlers in `SwBaseShell` and `SwDrawBaseShell` (`basesh.cxx:258-299`, `drwbassh.cxx:389-402`, **read**).
  - seq (600 ms settles) always sees the timer fired; the measured `unipoll` mode (all ops in one poll) never does. Under C it depends on ticks. Whether a landing differs is not measured.
  - NOTE, experiment: a native arm "click an as-char image, then `.uno:Bold`; same with Delete, Backspace, Left", in seq, unipoll and uni1 (one op per poll, no idle between).
- **The fields idle: COUNTEREXAMPLE (content after the reply).**
  - `SwDocIdle` (LOWEST, `DocumentTimerManager.cxx:49`) updates expression, table-formula and reference fields when fields are dirty (`:142-151`, `:184-214`) (**read**).
  - That is a document-content change after the command returned, possibly after its reply and after the next command. Nothing in §5 names it. Unmeasured; it needs a fixture with fields.

**(1) Can the FIFO key's undo proof be satisfied by another change? NONE found.**
- Between the before-read and the at-return read only the key's own call runs, provided both reads are in the same poll (`spec:124`).
- No nested dispatch exists on the WASM paths above.
- Idle jobs that run between polls do not add undo actions: `SelectShell` runs with undo off (`view.cxx:617-620`), and the field update creates no list action (**inferred**; not exhaustive).
- Caveat (**inferred**): editeng's `SolarMutexReleaser` around clipboard calls (`impedit.cxx:1957`, `:1991`, cited by the facts sheet) releases the mutex on the main thread. Only paste into an EditEngine (comment or draw text) reaches it.

**(2) How does the page know a key did nothing? COUNTEREXAMPLE.**
- **Undo grouping hides a real deletion.**
  - Writer merges a single-character delete into the last `SwUndoDelete` (`DocumentContentOperationsManager.cxx:4648-4666`). Backspace prepends the character (`undel.cxx:621-632`), provided it has the same letter/numeric class (`:567-573`) and stays in the same paragraph (`:542-545`) (**read**).
  - The Backspace path reaches that merge with no undo bracket: `FN_BACKSPACE` → `DelLeft` → `SwEditShell::Delete` → `DeleteSel` → `DeleteAndJoin` (`basesh.cxx:296-298`, `delete.cxx:280`, `eddel.cxx:136-175`, `:122-123`, **read**).
  - The top comment is `"Delete $1"` with `$1 = ShortenString(text, 20, "...")` (`strings.hrc:435`, `undel.cxx:842`, `undobj.cxx:1626-1643`, `UndoCore.hxx:247`). It is recomputed on every read (`undel.cxx:200`; `undobj.cxx:718-745`).
  - The payload is `index`, `comment`, `viewId` and the action's construction `dateTime` (`svl/source/undo/undo.cxx:1310-1318`, `:76-78`), none of which grouping changes (**read**).
  - So once the merged deletion exceeds 20 characters and its newest 10 are equal, the payload is byte-identical before and after a Backspace that deleted a character. Example: the 22nd Backspace through `______________________________` or a run of zeros (measured on a re-implementation of the two functions, `q7_undo_grouping_comment.out`; not LibreOffice).
  - `judgeAfterKey` then reads "unchanged" (`merge_key_undo.hpp:399-405`, **read**).
  - This is new in v23: today mid-text caret deletes complete by the barrier, not by the undo proof. §5.4 moves every caret delete to the undo proof (`spec:124-126`).
  - NOTE, experiment: a native uni1 arm on a paragraph `Name: ` + 30 `_`, caret at end, 25 Backspaces one per poll, the `.uno:Undo` payload recorded at each return. The prediction is a byte-identical payload from press 22 on.
- **"游標…都沒變" at return has no named source.**
  - The caret cache is refreshed only by the flush, after return (facts sheet A1, `facts-async-key-machinery.md:36`).
  - The only synchronous read the engine has is the a11y focused paragraph (`pe:1958-1965`, `pe:1968-1980`, **read**). §5.5 names neither (`spec:131`).
- **N1a as the confirmation:** it is a one-time native measurement over the D arms, and its tile clause is empty (Q1d). §7.2's "確認沒有晚到的…回呼（N1a）" (`spec:162`) holds for cursor, selection and result callbacks on those fixtures only.

**(3) Tables and in-line objects, "default is Writer's behaviour": COUNTEREXAMPLE / NOTE.**
- At cell boundaries Writer's own keys are true no-ops that restore the caret (`delete.cxx:198-237` for `DelLeft`, `:335-403` for `DelRight`; tdf#115132, **read**). `verified-boundary-noop` is then the right answer.
- For in-line objects "Writer's behaviour" is timing-dependent under C: the 120 ms deferred `SelectShell` after an object click (above). The default "照 Writer" (`spec:163`) needs to say which Writer it means: settled (seq) or within two ticks (C).

### Q7. Addendum §2.2's vocabulary table — COUNTEREXAMPLE

What the frozen client accepts (**read**):
- `move`: revision unchanged, `changed:false`, `documented-callback-*` or `verified-move-readback` (`client:146-148`, `:355-361`).
- `delete`: either `verified-boundary-noop` with `changed:false` and revision unchanged, or `verified-selection-delete`/`verified-key-undo` (`actionsAfter ≥ 1`) with `changed:true` and revision +1 (`client:161-166`, `:362-382`).
- `mutation`: `uno-command-result`, `changed:true`, revision +1 (`:383-391`).

1. **The grouping case (Q6.2): COUNTEREXAMPLE (inferred from read lines; unmeasured).**
   - §5.4/§5.5 name two outcomes for a caret delete: undo changed → `verified-key-undo`; undo, caret and selection unchanged → `verified-boundary-noop` (`spec:124`, `:131`). §5.3 A5 withdraws `key-deadline` (`spec:110`).
   - For "undo unchanged, text changed" the engine either:
     - (i) reads the caret from the pre-flush cache and answers `verified-boundary-noop`, `changed:false`, revision unchanged. The client accepts that (`client:372-374`) with the wrong meaning: the page does not mark the document dirty and keeps the old revision while Writer deleted a character; or
     - (ii) sees the caret change and has no specified reply. The nearest existing code path, `judgeAfterKey` at a deadline, is the withdrawn `key-deadline` refusal (`merge_key_undo.hpp:400-403`) → `EDITOR_BOUNDARY_UNSUPPORTED` → checkpoint and restart. That is the "fix becomes the same failure" shape the client's comment warns about (`client:132-140`).
   - The §5.8 form-1 table test ("every reply's completion is an accepted string for its class", `spec:150`) passes in both cases, because it checks strings, not meaning.
2. **`verified-key-undo` with `actionsAfter` 0: NONE.** `judgeAfterKey` refuses `key-unparsed` when the changed payload parses to fewer than one action (`merge_key_undo.hpp:406-412`; `actionsAfter` is the after-payload's action count, `:334-366`) (**read**). Only a forged report could carry it.
3. **`verified-boundary-noop` when the caret moved but the text did not: NONE for meaning.**
   - The client's no-op claims are about the document (`changed:false`, revision unchanged, `client:363-374`, **read**).
   - `DelLeft`/`DelRight` at a table boundary restore the caret anyway (`delete.cxx:232-237`, `:373-375`).
   - Condition (**inferred**): the reply's `state` must be the post-flush cache, which §5.2's "reply at the next poll" gives.
4. **A range delete where Writer deletes nothing: COUNTEREXAMPLE, pre-existing, not introduced by C.**
   - The engine answers every successful `UNO_COMMAND_RESULT` with `changed:true` and `advanceRevision()` (`pe:2843-2856`, **read**), which the mutation class requires (`client:383-391`).
   - A `.uno:Delete` on a range of empty table cells is then accepted as a change that did not happen (**inferred**: the cell branch of `DeleteSel`, `eddel.cxx:53-95`).
   - This is fixed question 3's arm; the experiment is a native seq/unipoll pair on a two-empty-cell selection, reading the undo payload and `wasModified`.
5. **The inline format at a collapsed caret, under a literal §5.2: COUNTEREXAMPLE (measured input, inferred reply).**
   - In d4, Writer's own order answers `.uno:Bold` with `success:false`, in seq and unipoll alike (A8). The engine rescues that only through 059's check of the `STATE_CHANGED`-fed cache (`pe:2827-2834`, **read**).
   - §5.2 and §5.3 A7 forbid reply fields from that cache as "timer class" (`spec:98`, `:112`).
   - N1's own record shows `STATE_CHANGED` is not one class:
     - `.uno:Bold=true` and `.uno:ModifiedStatus=true` arrive in the Bold op's own flush, before its first poll, 5/5 (measured, `native/a9_bold_state.out`).
     - The table and clipboard states arrive late (measured, `native/a10_state_split.out`).
     - `.uno:Undo`, `.uno:StateWordCount` and `.uno:DocumentRepair` occur in both classes.
   - Read literally, the engine refuses with `LOK_COMMAND_FAILED` (`pe:2836-2841`) a Bold that Writer applied. That code is not in the session's `RECOVERY_ERRORS` (`R/wasm_sdk_probe/editor-shell/editor-session.js:15-22`, **read**), so the page reports a failure but the session survives.
   - The type-level claim "`STATE_CHANGED` is timer class" (`spec:98`, `:223`, L-timer-class-callbacks) is contradicted by N1's own data; per CLAUDE.md §4 it should be withdrawn in favour of the measured split. §5.3 A7's replacement ("read the format state directly, or the html readback") names no read for a collapsed caret: the html readbacks are selection reads, `pe:4851`, `:4885`, `:4948` (**read**).
6. **"Only this key's" callback (A2, `spec:107`): NONE for meaning.**
   - A layout slice in the poll's own tick can join command N's flush (`init.cxx:2578-2582`: one pending flush).
   - The cursor payload is computed at flush time (`init.cxx:2450-2465`, `:2486`), so it is the current rectangle whoever caused it.
   - The client accepts both move completions with `changed:false` (**inferred**).

### Q8. Addendum §2.3's `anyInput` rule — COUNTEREXAMPLE (bullet 1)

The tick, as read (`svpinst.cxx:303-306`, `:436-507`; `salusereventlist.cxx:59-136`):
1. Dispatch at most one user event; if one was dispatched, return before the poll.
2. Otherwise `CheckTimeout()` runs at most one scheduler task.
3. If that ran and `anyInput()` is false, return.
4. Otherwise poll, with timeout 0 if a task ran, else the remaining timer or −1.

The flush is a user event (`init.cxx:2578-2588`), and it is the only way doc callbacks reach the engine (`invoke()` is called only from `FlushQueue`, `init.cxx:2584-2588`, **read**).

- **Bullet 1: a reply waits behind a scheduler task although `anyInput` is true. COUNTEREXAMPLE (inferred from read lines; unmeasured on WASM).**
  - The rule guarantees at most one task per tick before the poll, not a short one.
  - Writer's layout pass consults the LOK `anyInput` (`layact.cxx:90-100`). Even so it is interruptible only at its `CheckIdleEnd` points (`:708`, `:939`, `:1887`, `:1986`, `:2082`).
  - The other idle jobs in the same `SwLayIdle` consult only `Application::AnyInput` (`layact.cxx:2176`, `:2184`, `:2192`, `:2207`), which on svp is timer-only (`svpinst.cxx:549-554`; `svapp.cxx:563-566`). Those jobs are online spelling, autocomplete, word count and smart tags.
  - The fields job (`DocumentTimerManager.cxx:184-214`) consults nothing.
  - So the first reply after opening a long document can wait behind a whole-document spelling pass, if a spell checker is loaded (which L-no-desktop-main may prevent), and any reply can wait behind a field update.
  - N1c measured the layout case natively at 0.1 vs 1.2 ms (`oc/README.md:115-119`). On WASM it is one 10 ms tick per task, inferred and unmeasured.
  - NOTE, experiment: the §9.2 diagnostic link records the reply delay on the largest fixture's first command after open, with and without dirty fields.
- **Bullet 2: a command drained before the previous command's flush: NONE (by source).**
  - With one command per poll, the poll that drains N+1 runs on a tick that began with an empty user-event list (`svpinst.cxx:442-444`). N's flush was posted during N (`init.cxx:2084`, `:1641-1649`), so it has already been dispatched.
  - Callbacks queued later by a task in the poll's own tick join a flush posted before the poll, which is the N1b late class.
  - Today's run-until-empty drain (`pe:6688-6751`) violates it, and §5.2 changes it.
- **Bullet 3: the non-blocking poll starves something: NONE (by source), two NOTEs.**
  - With the poll returning at once, each tick returns to the pthread's event loop. That is what `svpinst.cxx:308-316` needs: `emscripten_set_main_loop_arg(…, 100, 1)`.
  - Today's poll waits on a condition variable for up to 1 s (`pe:6798-6818`), which blocks it; §5.2 removes that.
  - NOTE 1 (**inferred**): `anyInput = command queued ∨ reply pending` counts *every* queued command. `PaintTile` and `EditorGetState` share `gState.commands` (`pe:6304-6311`, `pe:6389`; the page renders through `document-sdk.js:498`, and the session reads state after an op, `editor-session.js:301-302`).
    - While the page keeps rendering, `anyInput` stays true and Writer's layout idle interrupts itself at every check (`layact.cxx:95-99`).
    - A long document's background layout makes no progress until input stops.
    - The spec's "頁面的佇列本來就一次送一個" (`spec:93`) is true of the editor queue (`editor-session.js:287-311`) only; render and state requests are not serialised against it.
    - Rule 2 does not say whether a pending reply or a queued command goes first.
  - NOTE 2: §5.7 rule 4 has no engine-side cell in §9.2 (`spec:184-198`). The native N1c measured the harness's `anyInput`, not the engine's (Q1e).

### Q9. The model's mode C — SHOULD, with a COUNTEREXAMPLE in (b)

Reproduction: the scratch build of the committed test prints output with sha256 `c811b5f0…`, identical to `ev/model/test-output.txt`, in 24 s, ending `ok` (measured, `model/base.out`). Scripts: `model/make_variants.py`, `model/make_e6.py`; outputs beside them.

**(a) Earned or by construction?** Mostly by construction, and the construction is the right one, with one exception.
- C's "forged" check compares the cache with core at reply time (`model:661-668`, **read**). The cache equals core exactly when a full flush ran after the last change.
- The loop guarantees that for everything run inside an engine phase:
  - `enginePhase(); ++tick; lokStep();` gives exactly one LOK step between two engine phases (`model:960-968`);
  - the C gate waits for `lokIdle()` (`model:609-619`);
  - every change schedules a flush (`model:423-433`, `:651-652`).
- E2 (the poll executes every ready action) forges 2,898,074 and diverges 568,092. E3 (the poll may run while a flush is queued but not started) forges 2,562,384; its first forged sequence is the earlier operation that `go()` runs before the first engine phase (`model:961`), and no U completion is stale (`staleU=0`), so the forging comes from that tick-0 operation (inferred) (measured, `model/E2_drain_all.out`, `model/E3_queued_flush.out`). Both reduce to committed red case 1's mechanism: no LOK step between a command and its reply.
- Red case 2 removes "not mid-flush" (`model:611`). Real LOK cannot violate that, because `invoke()` delivers a whole flush inside one user event (`init.cxx:2489-2571`). What red case 2 stands for is "decide inside the callback handler", the withdrawn first-callback rule. That is a legitimate red case, but its README label ("a poll may land between two callbacks of one flush", `ev/model/README.md:47`) describes something LOK never does.
- **The rule with no red case, and none possible in this model: the completion's meaning.**
  - C's reply decides `verified-key-undo` vs `verified-boundary-noop` and transition vs readback from the model's own `keyChanged` (`model:651`, `:672`, `:677`, `:693`, **read**). That is an oracle; the engine decides from the undo payload and callbacks.
  - E6 changes only the Backspace label: a deletion that leaves the caret at 0 is called `verified-boundary-noop` with `outcome Noop`.
  - Result: 174,672 real deletions mislabelled, and the full committed test still exits 0 with `ok` and no FAIL line. Only the `completions:` lines differ (measured, `model/E6_lying_noop.out`).
  - Q6.2 shows this is not hypothetical in Writer.
- "One command per poll is not discriminated" (README) is confirmed. The README/§14 say it "must be checked in the engine (§9.2)" (`ev/model/README.md:57`, `spec:254`), but §9.2 has no such cell (`spec:184-198`, **read**). That is a dangling reference.

**(b) Does the forged-reply definition catch every way a reply misleads the page? COUNTEREXAMPLE.**
- It compares the selection rectangles and the caret rectangle only (`model:665`).
- It does not compare:
  - the completion string's truth (E6);
  - `changed` or the revision;
  - format state: the model has no `STATE_CHANGED` at all (`model:315`, `CbType {RESULT, SS, SE, SEL, CUR}`), so L-timer-class-callbacks and 059 are outside it;
  - text;
  - timer-class semantic effects (none modelled; Q6).
- The page snapshot it feeds is the selection only (`model:669`, `:826`).
- Withdraw the reading "C's forged-completion class is empty" (`spec:170`, `:246`) as a statement about replies. It holds for "no reply's selection or caret differs from core's".

**(c) Is "Writer-divergent = the whole end state" the right comparison?** Right for *order*, and stronger than text alone. In C mode, however, it can only fail through the page's delete-form choice (`model:825-830`) or a refusal.
- `writerCore` and `syncKeyBackspace` encode the same Backspace semantics (`model:280-282`, `:687-693`).
- Keys apply inside their call (`model:649-654`).
- Every other forged reply leaves the end state alone. The committed red-case output has moves, typing and format forged at up to 100% with `writerDiffers=0` (`ev/model/test-output.txt:4626-4661`, **read**).
- So the two zeros together do not establish "no reply misleads the page". SHOULD: say so where §14 reports them.

Also (SHOULD): the printed `runs` overstate the distinct C state space. C never reads `lagDeadline`, `lagB1`, `lagV`, `eDeadline`, `gapRS` or `gapSE` (`registerMove`, `startEarlier` and `resolveBackspace` return before using them: `model:643`, `:798-805`, `:830`). Dropping them leaves:

| shape | distinct scenarios | printed runs | factor |
|---|---|---|---|
| moves | 4,064 | 91,728 | 22.6× |
| Backspace | 16,256 | 2,201,472 | 135× |
| typing | 16,256 | 366,912 | 22.6× |
| format | 16,256 | 366,912 | 22.6× |

(measured, `model/E5_distinct.out`). The populations in README §D and spec §14 are runs, not scenarios.

---

## Experiments (all under this directory)

| file | what | result file |
|---|---|---|
| `native/a1-*.txt` | both readers and both self-tests on the scratch extraction | identical verdicts; 5/5, 6/6 |
| `native/part_a_experiments.py` | A2 d4 without ops; A3 D7 tops per round; A4 threaded-as-unipoll on d5; A5 reply types seen; A6 on-time reply callbacks per op; A7 D8 on an unclean cell; A8 Bold's result | `native/part_a_experiments.out` |
| `native/a9_bold_state.py` | Bold's state vs first poll, uni1ai | `native/a9_bold_state.out` |
| `native/a10_state_split.py` | `STATE_CHANGED` keys on time vs late | `native/a10_state_split.out` |
| `native/a11_tiles_anywhere.py` | `INVALIDATE_TILES` in every native output | `native/a11_tiles_anywhere.out` |
| `native/a12_d7_missing.py` | A12 a missing D7 round; A13 D7 arms dropped | `native/a12_d7_missing.out` |
| `inspect_n1.py` | per-op late callbacks, all N1 cells | `inspect_n1.out` |
| `q7_undo_grouping_comment.py` | re-implementation of `ShortenString` and the grouping rule (not LibreOffice) | `q7_undo_grouping_comment.out` |
| `model/make_variants.py` | baseline, E2, E3, E5 (driver runs SECTION D only) | `model/*.out` |
| `model/make_e6.py` | E6 mislabelled no-op, full committed `main()` | `model/E6_lying_noop.out` |

Nothing above needs a build to settle except the NOTEs, each of which names its native arm or diagnostic-link record.

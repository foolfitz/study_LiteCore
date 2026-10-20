# Review brief, two seats (opus, codex): v23 under C, before any engine code (SPEC-M3-ordered-commands §10 step 3)

Written 2026-10-20 at tree `76fe206f`. Both seats get this same text. Read-only: write nothing in the repository. The opus seat may run experiments, but only on scratch copies in its own scratch directory: `git -C /home/jiajun/LibreOffice/study_LiteCore archive HEAD <paths> | tar -x -C <scratch>`. Use absolute paths, and never `cd` into the repository or into `libreoffice-26-8/`.

**Rules:**
- No make, no ddev, no browser.
- Do not run the native harness `oc_native` or anything that loads LibreOffice: a native run must never overlap another.
- `g++` of the model test (2 s) and running it (24 s) on a scratch copy is fine.
- Read the files named here. Do not search the whole repository.

Abbreviations:
- `R` = `/home/jiajun/LibreOffice/study_LiteCore`;
- `lo/` = `R/libreoffice-26-8/` (LibreOffice core source, HEAD `671c848b1bb8`);
- `src/` = `R/wasm_sdk_probe/src/`;
- `ev/` = `R/findings/evidence/link-batch-v23/`.

## The decision under review

- `R/specs/SPEC-M3-ordered-commands.md`, pinned at `b9080313`, append-only since. It specifies candidate C for v23: LOK in unipoll, one thread, keys run inside the call. §14 (the model's result) was appended at `76fe206f`.
- The rulings behind it: `ev/review/ruling-fable-1.md` and `ev/review/ruling-fable-1-addendum-1.md`.
- The facts sheets: `R/handoff/link-batch-v23/facts-lok-command-ordering.md` and `R/handoff/link-batch-v23/facts-async-key-machinery.md`.

## Part A: the two native readers, their one review (§34.3)

Files:
- `ev/native/ordered-commands/tool/read_results.py` (verdict C-HOLDS, `ev/native/ordered-commands/out/`);
- `ev/native/ordered-commands/tool/read_n1.py` (verdict N1-HOLDS, `ev/native/ordered-commands/out-n1/`);
- the fields they read come from `tool/oc_native.cpp` and `tool/run_arms.py`;
- the arms and the reading rules are in `ev/native/ordered-commands/README.md`, `smoke/NOTES.md` and `smoke-n1/NOTES.md`, and in spec §3 and §9.1.

Both readers have already produced the committed verdicts. This review asks whether either verdict, or a future use, can be wrong.

Answer each question with COUNTEREXAMPLE, NONE or SHOULD. For each COUNTEREXAMPLE, say whether an honest run of the committed harness can produce its input (**in-model**), or only a forged or hand-edited report can (**out-of-model**: a NOTE at most).

1. **A broken C that reads C-HOLDS, or a broken anyInput that reads N1-HOLDS.** For example:
   - a landing comparison that two different documents pass, such as the run weights, list style or caret line prefix not discriminating a misordered delete;
   - D8 passing when the effect is not there at return;
   - N1a missing a late reply-type callback because of how `lateCallbacks` is windowed.
2. **A correct C that reads FAIL or NE.** For example: a seq reference that varies between rounds for a reason unrelated to order.
3. **Non-vacuity.** A run in which a mode never actually ran in its topology, or an arm's X step never fired, but which reads PASS.
4. **Exit and completeness.** A missing round, arm or mode that is not counted as missing. Duplicate cells. A verdict printed with exit 0 when a cell is unclean.
5. **Red-case coverage.** For each rule in each reader, name the self-test case that exercises it, or say that none does.

## Part B: the spec under C (§10 step 3)

6. **The three fixed questions, as spec §7 answers them under C.** Attack each answer against the source:
   - (1) Can a "FIFO key's undo proof" be satisfied by another change? Under C the claim is that nothing interleaves inside a command (§5.7 rule 1).
   - (2) How does the page know a key did nothing? Under C, the reply at the next poll, plus N1a.
   - (3) Do keys in tables and in-line objects behave differently from today's refusal? The default is Writer's behaviour.

   Find a path in `lo/` or `src/probe_engine.cpp` where a command, under unipoll, yields, re-enters, or leaves an effect pending past its return. Candidates: `Application::Reschedule`, `Scheduler::ProcessEventsToIdle`, a dialog, `SfxDispatcher` re-posting (`lo/sfx2/source/control/dispatch.cxx:996-1003`), a posted `.uno:` with `SynchronMode=false`, `postMouseEvent`. Any of these breaks the spec's claim.
7. **Addendum §2.2's vocabulary table** (spec §5.8, §5.4). Every reply must carry a completion string that the frozen client accepts for its postcondition class. The client is `R/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js`: `MOVE_COMPLETIONS`, `DELETE_COMPLETION`, `:146-148`, `:161-166`, `:372-374`. Find a reply that C would produce whose string the frozen client rejects, or one it accepts with the wrong meaning. For example:
   - `verified-key-undo` with `keyUndo.actionsAfter` 0;
   - `verified-boundary-noop` when the caret moved but the text did not;
   - a range delete at a document boundary.
8. **Addendum §2.3's `anyInput` rule** (spec §5.2): `anyInput` = a command is queued ∨ a reply is pending, and the poll never blocks on WASM. Read `lo/vcl/headless/svpinst.cxx:440-481` and `src/probe_engine.cpp:6688-6851`. Find a tick sequence in which:
   - a reply waits behind a scheduler task although `anyInput` is true;
   - a command is drained before the previous command's flush has run;
   - the non-blocking poll starves something. One candidate is the Emscripten main loop's pacing: `svpinst.cxx:308-316` installs its own main loop when `m_bUseSystemLoop` is set.
9. **The model's new mode C** (`R/wasm_sdk_probe/tests/extend_completion_model_test.cpp`: the header paragraph on SECTION D, `Knobs::sync*`, `Run::syncKey`/`syncReply`/`syncAnswer`/`syncKeyBackspace`, `sweepC`; the result is in `ev/model/README.md`).
   - Is C's zero earned by the rules of §5.2, or is it by construction? The two red cases remove a rule each and print forged replies. Is there a rule C's zero depends on that has no red case? The README already names one: one command per poll is not discriminated.
   - Does the forged-reply definition (the cache differs from core when the reply is sent) catch every way a reply can mislead the page?
   - Is "Writer-divergent = the whole end state" the right comparison?

## What the seats do not need to decide

- Whether C is the right candidate (ruling 1).
- Whether the arms are the right arms (the native README).
- The diagnostic profile's cells (§9.2), which are written later.

## Output

Start with a table: question, verdict, one line. Then one section per question, with `file:line` for every claim.
- Mark each claim **read** (you read the line) or **inferred**.
- A finding that needs a build or a browser to settle is a NOTE with the experiment that would settle it.
- Do not propose new machinery. When the right answer is to withdraw a claim, say so (CLAUDE.md, the section on acceptance criteria, §4).

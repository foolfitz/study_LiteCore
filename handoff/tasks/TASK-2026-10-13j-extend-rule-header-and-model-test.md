# TASK 2026-10-13j — link batch step 1: the completion rule and the flag as pure functions, and their model test

Spec: `specs/SPEC-M3-link-batch.md`, which is FINAL after §12 (no further spec round). The relevant parts are
§10.1 (rule (a) and L-extend-prior-flush), §12.1 (the population is defined by the model's printout), §12.2
(the flagged delete), and §10.5 together with §12.2 (C's window and the flag's effect on it). The rulings
behind them are `findings/evidence/link-batch/review/ruling-2.md` and `ruling-3.md`, both authoritative for
intent.

**This step writes no engine wiring.** Per ruling 2 condition 2 and ruling 3 condition 18, the header and the
model test are committed and made red **before** anything in `probe_engine.cpp` uses them.

## Deliverables

1. **`wasm_sdk_probe/src/extend_completion.hpp`**: pure functions only. No LOK, no globals, no I/O. Follow the
   style of `src/merge_key_undo.hpp`: state structs, small functions, comments that say WHY.
   - **Rule (a).** A pending move or extend is created with `{kind, dispatchSelection rectangles}`. `kind` is
     either extend-or-range-start or caret-start plain. For extend-or-range-start, completion requires a
     `TEXT_SELECTION` whose parsed rectangle list differs from `dispatchSelection` (empty against non-empty
     counts as different), followed by the next `INVALIDATE_VISIBLE_CURSOR`. Caret-start plain moves keep
     today's rule: the first cursor or selection callback. The 250 ms readback stays the fallback, and the
     header returns which completion happened.
   - **The flag `extendUnconfirmed`.**
     - Set when an extend completes by readback.
     - Cleared by a rule-(a) completion, by a flagged delete completing with proof, and on close or a new
       worker. NOT cleared by a caret-start plain move.
     - While set: `delete-selection` is refused before dispatch; a Barrier-class K1 is accepted only if it
       is exactly one code point; MergeKey keeps its fence plus K2 (that logic is unchanged and lives in
       `merge_key_undo.hpp`); at the end of C's window the result is a refusal, not `verified-boundary-noop`.
     - Stage name `prior-key-unconfirmed`, `keyPosted:false`.
   - The header must express all of this as decisions taken from inputs, so the engine can call it later.
2. **A model test**, `wasm_sdk_probe/tests/extend_completion_model_test.cpp`. Generate the sequences; do not
   list them by hand. Model LOK the way `tests/merge_key_undo_model_test.cpp` does (read its header comment
   and reuse its approach; you may factor shared pieces into a small header if that is cleaner than
   duplicating them):
   - one FIFO of posted keys and flushes;
   - a flush computes its payloads at flush time, in the order START, END, TEXT_SELECTION, then the cursor;
   - `TEXT_SELECTION` and the cursor are dropped when they equal the last value SENT
     (`init.cxx:1592–1594`, `2530–2537`).
   - Model a one-line text with a caret and a mark, so Shift+Left/Right, plain Left/Right and Backspace have
     real effects.
   - Earlier operations, all of which must be generated:
     - a synchronous `insert-text`, whose flush is still queued (typing, and typing over a range);
     - an operation completed by the 250 ms readback whose own `TEXT_SELECTION` arrives late;
     - a `uno-command-result` completion whose SEL/CUR flush comes after the result
       (`startEditorUnoAction` family: delete-selection, the inline formats, undo/redo);
     - a range select made of three synchronous `setTextSelection` calls (RESET, START, END), each able to
       produce its own flush.
   - Interleaving lags are generated, and the engine's decisions (dispatch, readback deadline) happen at
     event boundaries.
   - **Property for rule (a):** when the engine completes an extend or range-start move, the reported state
     equals core's state after that operation's own key has been processed. Every generated sequence where
     this fails is PRINTED; that printout IS L-extend-prior-flush's population (§12.1). The test asserts the
     rule is exact on every sequence that is not in the printout's declared classes, and it fails if the
     printout contains a sequence outside those classes.
   - **Property for the flag:** after an extend that completed by readback before its key ran, a following
     Backspace (late-bound to delete-backward on the stale collapsed snapshot), whose barrier posts its own
     Shift+Left, must REFUSE with `prior-key-unconfirmed` and must never delete two units.
   - **Liveness:**
     - with no disturbance, an extend completes by rule (a);
     - a flagged Backspace whose K1 is exactly one code point deletes exactly one;
     - "Shift+End at line end (silent), Backspace" deletes one character, as Writer does;
     - a range then Backspace uses delete-selection when the flag is clear.
   - **Red cases**, built into the test as alternative rules run through the same generator, each of which
     must produce counterexamples:
     - §9's rule (complete on the first cursor) fails "insert then Shift+key" and "type over a range then
       Shift+key";
     - v19's rule (complete on the first `TEXT_SELECTION`) fails the same two;
     - removing the flag yields a two-unit delete and a silent mid-paragraph no-op;
     - the one-code-point rule applied WITHOUT the flag gives a false refusal on a multi-code-point grapheme
       in an undisturbed sequence. This is L-flagged-delete-grapheme's reason.
3. **Build and run.** Add a target next to the existing `merge_key_undo_model_test` rule in
   `wasm_sdk_probe/Makefile` (around line 3535), in the same style, host compiler only. **Editing the Makefile
   is allowed only for this host-test rule.** Before and after the edit, run `make -n` on a profile target
   (for example `make -n dist/profiles/e2-editor-v19/sdk-manifest.json`) and confirm that the edit does not
   make any profile or link target out of date (finding 042). If it would, do NOT edit the Makefile; build the
   test with a documented one-line command instead.
4. **Evidence.** Write `findings/evidence/link-batch/extend-model/README.md` (English), beginning with
   `## SUMMARY` (≤ 30 lines). It records:
   - the generator's size (sequence count per class);
   - the printed population of L-extend-prior-flush by class;
   - each red case and the count of counterexamples it produced;
   - each liveness check;
   - the exact build and run commands.

   Also save the full test output there.

## Rules

- Do not touch `probe_engine.cpp`, `sdk/`, `editor-shell*/`, `web/`, `dist/`, any profile, or any spec.
- If the spec or a ruling is self-contradictory or not implementable as written, stop and report it. Do not
  improvise a rule.
- Commit only your paths (`git add … && git commit -m "…" -- <paths>`; retry if `.git/index.lock` exists).
  Use an English message ending `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, with no
  `Claude-Session:` line.

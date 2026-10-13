# Ruling brief 4: the model test found six holes in §10–§12

**Authority:** the owner, 2026-10-13: 「有疑義的發給fable，我授權它代我下決定」.

**Source:** `findings/evidence/link-batch/extend-model/` (commit `fce084d6`, written by a fresh fable executor
under `handoff/tasks/TASK-2026-10-13j-extend-rule-header-and-model-test.md`). The main session rebuilt and
re-ran the test: exit 0, 12 s, six `REPORTED` items reproduced. The test implements §10.1 and §12.2 verbatim.
Where the spec contradicts itself, the executor stopped and reported instead of improvising. Those are the
items below.

1. The one-code-point proof of §12.2 fails when the queued forward extension is 2 or more units. K1 shrinks
   it, one code point remains, the flag admits it, and the barrier deletes 1 unit where Writer would delete
   the whole selection. **514 sequences.** This contradicts §12.2's "every stacked sequence refuses".
2. §12.2 sets no flag for plain moves. A range-start plain move answered by readback, with its key still
   queued, followed by `delete-selection`, makes `.uno:Delete` remove a range that Writer would collapse, or
   delete forward. **44,124 sequences.**
3. The forged-completion residual, now counted: **103,776** wrong one-unit deletes.
4. The proof does not identify K1. A pending extend's own flush lands between K1's post and K1's run and is
   admitted as K1's; K1 then runs and the collapse never comes. **160 sequences, 128 of them wedged**
   (`AwaitingDeleteCompletion` has no deadline).
5. Today's caret-start plain rule (first callback) completes on an earlier operation's late `TEXT_SELECTION`
   before its own key is posted. The snapshot then shows a stale range, and `delete-selection` runs ahead of
   the queued move. **110,784 sequences, 27,744 wrong deletes.**
6. An early select-range completion (ruling 3's Q1 B) feeds `delete-selection` a partial range. **2,448
   wrong deletes.**

**The executor's observation:** the merge attribution's anchor fence, which is computed for every K1,
distinguishes (1) and (4). Ruling 3 consults it for MergeKey only.

**Rule on each item.** Also say:
- (a) which of these are reachable in the **current product** (0.2.18: page `b24d754a…`, v19 manifest moves
  `collapsed`-only, rule A at `beforeinput`, the 129 page prescription). Item 5 especially: if any is
  reachable today, it is a finding against the uncounted candidate, not only against this link;
- (b) whether the model's sequence counts mean anything about real-world frequency, or only about coverage of
  the interleaving space;
- (c) whether the remedy must be validated in the model before any wiring. The main session's lean is yes:
  the same executor re-runs the test with your revised rule, and every red case and liveness check is
  reported again.

**Reply as in rulings 2–3:** RULING, WHY (for the owner, zh-TW, plain), FACT CHECK, CONDITIONS, with
condition numbers continuing from 29. Write it to `findings/evidence/link-batch/review/ruling-4.md`. If the
honest answer is that the stacking problem cannot be closed within this link at an acceptable cost, say so,
together with what would ship instead.

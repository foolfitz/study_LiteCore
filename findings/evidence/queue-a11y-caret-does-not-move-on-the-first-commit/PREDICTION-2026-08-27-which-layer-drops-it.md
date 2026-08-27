# Prediction, written before the run: which layer drops the caret update

Finding **084**. Written 2026-08-27, before `--caret-source-diagnostic` existed
and before any of it was run. Kept whatever the run says, because a prediction
that is only kept when it holds is not a prediction.

## What is already measured

`caret-follows-the-text-you-type` fails on the accessibility lineage at 3 of 27
commits and at 0 of 42 on the shipped profile. With the fixed sleep replaced by
a poll on the check's own predicate, the wait is **bimodal**: 0-1 ms when the
caret follows, **8013 ms -- the deadline -- when it does not, and nothing in
between**. The end state is always correct: the next commit's caret is where
both commits' text put it.

Nothing is typed while the poll waits, so the poll cannot mask the defect.

## The three layers, and why one measurement can separate them

The caret reaches `#sink` through:

1. **the engine's own record** -- `gEditorState.caret`, written only by
   `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` (`probe_engine.cpp`), and readable
   on demand through `editor-get-state`;
2. **what the page believes** -- `snapshot.editorState.caret`, which has **two
   writers**: `EditorSession._drain()` with one `editor.getState()` per
   completed queued operation, and the engine's pushed `editor-state`
   announcement handled by `NarrowEditorV2Session._handleEngineEvent`
   (`editor-shell-v2/narrow-editor-v2-session.js`), which finding 068 added and
   whose own comment says it "is the writer that wins in practice";
3. **what the page applies** -- `moveSinkToCaret(caret)`, called from `paint()`
   only when `caret && editorState.selection?.collapsed !== false`.

**Corrected before the run, not after it.** The first draft of this file said
the drain was the only writer of layer 2. It is not, and has not been since
finding 068 -- the pushed announcement is the other one. The prediction below is
the one made with both writers in view; the sentence it replaced would have been
wrong about the mechanism whichever way the measurement came out.

`--caret-source-diagnostic` records all three in the same round.

## The prediction

**The engine will have the new caret while the page's snapshot does not**, and
the reason will be visible in `sourceSequence`.

Specifically, on a dropped commit:

* `engineBefore` and `engineAfter` differ, and `engineAfter` carries the caret
  the sink never reached;
* the first engine probe inside the settle poll that differs from `engineBefore`
  lands **early** -- tens to a few hundred milliseconds, not at the deadline;
* `window.__pp.caretApplied` gains no row with the new position, because
* `window.__pp.caretBelieved` ends the round holding the OLD caret.

**Why, and this is the part the instrument can actually decide.** Layer 2 has
two writers and only one of them is guarded. The pushed announcement refuses to
write unless `sourceSequence` **advances** -- its own comment says why: "a slow
event could land after a fresher read and move the caret backwards". The drain's
read has no such guard. It writes whatever its `getState()` returned, whenever
that write happens to run.

So the order that loses a caret is: the drain's read is answered at sequence N
with the old caret; the cursor callback lands and the announcement writes
sequence N+1 with the new one; the drain's `state.update()` then runs and puts
sequence N and the old caret back. The page believes the old caret, no further
announcement is due until the next commit, and the sink stays where it was for
exactly one commit -- with the end state correct, which is what nineteen runs
already say.

**The signature to look for**: `caretBelieved` containing a row whose
`sourceSequence` is LOWER than the row before it, with the caret going backwards
in the same step.

**What would refute it.** `engineAfter` reporting the OLD caret for the whole
8 s. That would put the loss at or below the engine -- the cursor callback not
arriving until the next command drives the loop -- and the JavaScript above it
would be innocent.

**What would refute the mechanism while leaving the layer**: the engine holding
the new caret, `caretBelieved` never receiving it at all, and `sourceSequence`
rising monotonically throughout. That would mean the announcement was never
sent or never accepted -- a different defect in the same layer, and the phase
guard (`ready`/`busy` only) is the first thing to read if so.

**A third outcome, and it is not a tie.** The page believing the new caret while
the sink stays put would mean `paint()` skipped `moveSinkToCaret`, and the
`collapsed` field recorded beside each belief says whether a stale range
selection is why.

## What this run may NOT conclude

**Not which build difference causes it.** Two cores differ by more than the
accessibility flag, and this measures one thing on one of them -- findings 040
and 048 are the record of what naming a layer from a single measurement costs.
Naming the layer that *drops* the update is inside this run's reach; naming
*why that core and not the other* is not.

**Observation effect, stated in advance.** Each engine probe is a real
`editor-get-state` command. It cannot move the sink -- the page never sees the
answer -- so the check's verdict is unperturbed. It could in principle let the
engine's loop deliver a callback that was waiting, which would make the engine
look like it caught up sooner than it would have. That is why the FIRST probe's
timestamp is recorded rather than only the final answer: a callback the probe
itself flushed would show up as "the engine was stale until the exact moment we
asked", the same reading at every deadline, rather than as an early catch-up.

## Instrument control

The engine probe must be able to print two different values or it is not a
probe: on a passing commit `engineBefore` and `engineAfter` must differ. A run
where they never differ measures nothing, whatever the sink did.

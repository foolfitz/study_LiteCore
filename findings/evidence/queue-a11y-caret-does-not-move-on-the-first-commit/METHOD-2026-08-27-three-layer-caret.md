# Method: reading the caret at three layers in one round

Finding **084**. Written 2026-08-27 alongside the runs, so that what was run is
recorded independently of what it found.

## What was run

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --profile e2-editor-v11 --caret-source-diagnostic --caret-rounds 12 \
    --caret-engine-probe {every-round|stalled} --out <report>.json
```

Chrome, twelve typing rounds per run, on the accessibility lineage
(`e2-editor-v11`): **two runs under `every-round`** (the flag did not exist yet
for those two -- the mode is what the runner did before it was added, and it is
what `every-round` reproduces) and **four under `stalled`**. Then the same
`stalled` configuration on the shipped profile, with no `--profile` at all.

Nothing else about the runner changed: the same 40 checks, the same fixture, the
same shell generation (`e2/editor-shell-v2-bundle-v42.json`).

`--caret-rounds` may raise the round count and never lower it -- the checklist
row this check answers says three times out of three, so twelve is the same
check asked more times, and the number is written into the check's own oracle so
no reader has to guess which one produced a verdict.

## The three layers

`#sink` is a DOM observable and it is three layers downstream of the engine, so
"the sink did not move" cannot say WHERE an update was lost. The diagnostic
mirrors the page -- `probe.wasm` byte-identical, `dist/` never written -- and
adds:

| layer | how it is read | what its absence means |
|---|---|---|
| the engine | `window.__ppCaretEngine(tag)` issues one `editor-get-state`, the same call `EditorSession` itself makes after every queued operation | the cursor callback has not reached `gEditorState.caret` |
| what the page believes | one row per `updateState`, carrying `caret`, `sourceSequence`, `revision`, `collapsed` | the page was never told |
| what the page applies | one row per `moveSinkToCaret` call | `paint()` skipped it -- no caret, or a selection it believes is a range |

The engine's answer is **stored, not returned**: a promise crosses `evaluate` in
Chrome and not in Firefox, and a 20 s engine timeout inside an evaluate would
block the harness for it. The page posts the answer into `window.__pp` and the
harness polls.

## Per round, what is recorded

Under **`stalled`** (the default): a commit the sink followed sends the engine
NOTHING. Once the sink has been seen not to move, the engine is asked on each
poll iteration until its caret differs from **what the page believes in that
same moment**, and the first such answer is kept with the milliseconds it took
(`engineFirstDifferent.afterMs`) and with the belief it was compared against
(`pageBelievedThen`). `engineProbes` counts how many were needed.

Under **`every-round`**: `engineBefore` and `engineAfter` additionally bracket
every commit, and the in-poll comparison is against `engineBefore`.

## Controls, and why each is there

**The instrument must be able to print two different values** -- and under
`stalled` that cannot be shown from the rounds, because a clean run issues no
probe at all. So it is shown OFF the commit path: `engineAtLineStart` and
`engineAtLineEnd` bracket the two caret placements the arm already performs
before any typing, where an extra engine command cannot perturb what is being
measured. `engineProbeTracked` is that pair having reported two different
carets. Under `every-round`, `engineMoved` asks the same question per round.

**The sink must track the caret at all** -- `sinkTracksTheCaret`, which predates
this work: a sink pinned at one place reports "never moved" for every round and
the check fails for a reason that has nothing to do with typing.

## Stated limits

**Observation effect -- and it was real.** `engineBefore` is a real engine
command issued immediately before every commit. Written here as a risk before
the runs, it turned out to be the finding's first result: 0 of 24 commits
dropped under `every-round` against 10 of 48 under `stalled`, same
configuration, one variable. **The first version of this instrument suppressed
the defect it was built to measure.** That is why `stalled` is the default.

The in-poll probes cannot suppress anything -- they fire only after the sink has
already failed, and their answer never reaches the page -- but they also cannot
prove, on their own, that the engine held the caret before being asked. The
`caretBelieved` log can, and does: the announcement it records is unprompted.

**This cannot name the build difference.** Two cores differ by more than the
accessibility flag. Naming the layer that drops the update is inside reach;
naming why that core and not the other is not -- findings 040 and 048 are the
record of what that costs.

**Not a product-path verdict.** Every run here carries `caretSourceDiagnostic`
and `profileDiagnostic`, and `tools/check_usable_editor.py` refuses both: a
mirrored page cannot reconcile the checklist for the product.

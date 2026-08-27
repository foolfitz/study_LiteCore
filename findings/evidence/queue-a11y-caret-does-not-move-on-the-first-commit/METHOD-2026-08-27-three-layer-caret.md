# Method: reading the caret at three layers in one round

Finding **084**. Written 2026-08-27 alongside the runs, so that what was run is
recorded independently of what it found.

## What was run

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --profile e2-editor-v11 --caret-source-diagnostic --caret-rounds 12 \
    --out <report>.json
```

Five runs on the accessibility lineage (`e2-editor-v11`), chrome, twelve typing
rounds each. Nothing else about the runner changed: the same 40 checks, the same
fixture, the same shell generation (`e2/editor-shell-v2-bundle-v42.json`).

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

`engineBefore` and `engineAfter` bracket the commit. Inside the settle poll --
and only while the sink has NOT moved -- the engine is asked again every 100 ms
until its answer differs, and the first differing one is kept with the
milliseconds it took (`engineFirstDifferent.afterMs`). `engineProbes` counts how
many were needed.

## Controls, and why each is there

**The instrument must be able to print two different values.** `engineMoved` is
recorded per round: the engine's reading before and after a commit the sink DID
follow must differ. `engineProbeTracked` is the same question for the whole run.
A run where they never differ measures nothing, whatever the sink did.

**The sink must track the caret at all** -- `sinkTracksTheCaret`, which predates
this work: a sink pinned at one place reports "never moved" for every round and
the check fails for a reason that has nothing to do with typing.

## Stated limits

**Observation effect.** `engineBefore` is a real engine command issued
immediately before every commit, and `engineAfter` one immediately after. Either
could in principle change the order in which the engine's loop delivers a
callback. The in-poll probes cannot: they fire only when the sink has already
failed to move, and their answer never reaches the page. The consequence to
watch for is a **suppressed** defect -- a probed run dropping fewer carets than
an unprobed one -- and the historical rate (3 of 27, unprobed) is the comparison
that would show it.

**This cannot name the build difference.** Two cores differ by more than the
accessibility flag. Naming the layer that drops the update is inside reach;
naming why that core and not the other is not -- findings 040 and 048 are the
record of what that costs.

**Not a product-path verdict.** Every run here carries `caretSourceDiagnostic`
and `profileDiagnostic`, and `tools/check_usable_editor.py` refuses both: a
mirrored page cannot reconcile the checklist for the product.

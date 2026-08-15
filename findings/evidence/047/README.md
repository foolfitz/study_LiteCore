# Finding 047 — a save immediately before a click-placed caret

**Artifact**: `e2-editor-v2`, wasm `572035ac…`. **Fixture**: `list-contexts.odt`,
cell L1 (`E1-LC-ISOLATED`, `set-list-unordered`). **Date**: 2026-08-15.
**Browsers**: Chrome and Firefox — every row below is identical in both.

## The four arms

Same cell, same document, same artifact. Only what happens *before* the action
changes.

| directory | before the caret | wait after the caret is confirmed | result |
|---|---|---|---|
| `d3ab-save-0`, `ff-save-0` | `session.save()` (215–244 ms) | none | **`MUTATION_OUTCOME_UNKNOWN` / `stage-deadline:awaiting-selection`** |
| `d3ab-delay-0`, `ff-delay-0` | wait 1500 ms, no save | none | `verified-format-readback` |
| `d3ab-save-2000`, `ff-save-2000` | `session.save()` | 2000 ms | `verified-format-readback` |
| `d3ab-skip-0` | nothing | none | `verified-format-readback` |

The delay arm is the one that matters: **spending time before the gesture is not
the trigger — saving is.** And the settle arm shows it is transient.

## What the arms rule out

* "anything slow before the action breaks it" — the 1500 ms delay arm passes;
* "this cell never worked" — the do-nothing arm passes;
* "a browser difference" — both browsers agree on all four;
* "the anchor or the fixture" — one cell, one document, one artifact throughout.

## What is NOT established

The mechanism. The shape belongs to the finding 043 / 049 family — a shell left
in selection mode, the next selection silently dropped — but nothing here shows
it is the same `m_bInSelect`, so the finding does not say it is.

Two facts constrain any explanation:

* the dispatch **happens** (`dispatched: true`); what never arrives is the
  selection callback the barrier waits for afterwards;
* waiting 2 s **before** the dispatch fixes it, while the barrier's own 5 s stage
  deadline **after** the dispatch does not — so the callback is not late, it is
  never coming.

## Reproducing

```
make e2-c-assets
python3 tools/run_e2_c_d0.py --browser chrome --page e2-c-d3.html \
    --namespace __e2c_d3 --param only=L1 --param before=save --param settle=0 \
    --output <dir>
```

`before` takes `save` (default), `skip` or `delay`; `settle` is milliseconds to
wait after the engine confirms the caret. Both switches exist for this
comparison and are recorded in each result as `beforeMode` / `settleMs`.

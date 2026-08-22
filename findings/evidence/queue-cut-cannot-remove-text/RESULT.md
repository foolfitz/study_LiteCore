# Result (2026-08-21) — the manifest was not the only thing withholding range delete

Measured against [`PREDICTION.md`](PREDICTION.md), written before the run.
Artifact `29ec627b`, shell v25, Chrome, clipboard granted. Two runs, identical.

**Verdict: do NOT widen the manifest.** The gesture mask is real, and it is not
the last gate.

## Command

```
python3 tools/run_e2_c_product_path.py --browser chrome --range-delete-diagnostic
```

`--range-delete-diagnostic` grants `delete-backward` **both** range bits in a
**mirrored** manifest — `dist/` is never written and `probe.wasm` stays
byte-identical. The report carries `rangeDeleteDiagnostic.evidenceClass:
"diagnostic"` so it can never be read as a product measurement.

Both bits together, never one: `probe_engine.cpp:4364-4374` requires **both** for
a selection the build has not classified, so one bit alone refuses every range.

## Against the predictions

| | Prediction | Outcome |
|---|---|---|
| **P-CUT-1** | the gesture refusal disappears | **HOLDS.** `refusalReported: false` — `EDITOR_FORMAT_GESTURE_UNSUPPORTED` is gone |
| **P-CUT-2** | a single-paragraph range is removed from the saved ODT | **NOT ESTABLISHED** — see below |
| **P-CUT-3** | the session survives | **FAILS.** `stateAfterCut: "recoverable-error"` |
| **P-CUT-4** | cross-paragraph recorded, not predicted | not reached |

## What actually happens

```
剪下：EDITOR_STATE_UNAVAILABLE：selection barrier requires a
      callback-confirmed collapsed caret（可能已經改到文件：請回到檢查點）
儲存：EDITOR_NOT_READY：editor operation save is unavailable in recoverable-error
```

The mask lets the dispatch through and the **selection barrier** refuses it
instead, because the barrier is built for a *callback-confirmed collapsed
caret*. The session goes to `recoverable-error`, and the save that would have
answered "was the text removed" is refused.

So P-CUT-1's diagnosis in the queue item is **confirmed** — the caret-only
declaration is what produced the old refusal — and the item's own warning is
**vindicated**: *"The fix is not simply to widen the manifest."* Now measured
rather than argued.

## What is NOT claimed

**Whether the engine can remove a range is still unknown.** The barrier refused
before any deletion was attempted, and the save afterwards was refused too.

The first version of this record got that wrong and it is worth keeping: it
reported `targetStillPresent: false`, `neighboursSurvive: false`, `linesAfter: 0`
— from a save that never happened. `after_texts` was `[]`, so every "is it still
there" question answered "no", and the record read as *the cut deleted the whole
document*. It meant *nothing was measured*.

That is the same shape as the caret oracle's tie-break found the same morning: a
question asked of missing data must return **null**, not a value. The recording
now guards on `documentReadableAfter` and returns `null` with a named reason.

## Consequences

* `cut` stays **`partial`**, now with a **measured** reason instead of an
  undeclared one.
* The queue item stays open, and its remedy narrows: not a manifest edit, but
  either an engine-side barrier that can confirm a **range**, or a distinct
  action that deletes a selection. **Both are engine work, so both need a link**
  — which moves this item next to `redo` / `move-by-line` / `select-all` in the
  ABI proposal rather than beside the no-link work.
* The `--range-delete-diagnostic` flag stays. It is the cheapest way to re-ask
  this question after any engine change, and it writes its own evidence class.

## Reproduction

Two runs, same numbers. The diagnostic wedges the session by design, so every
check after the cut in that run fails as collateral — that is expected for this
arm and is not evidence about those paths.

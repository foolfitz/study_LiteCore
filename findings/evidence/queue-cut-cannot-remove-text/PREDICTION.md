# Prediction, written before the measurement (2026-08-21)

Queue item: `queue-cut-cannot-remove-text`. Checklist row: `cut`, the only
`partial` besides `turn-formatting-off`.

## What is already established, and is not under test

* The product's cut is copy-then-delete, in that order, deliberately.
* The copy half succeeds.
* The delete half is refused **every time**, with
  `EDITOR_FORMAT_GESTURE_UNSUPPORTED`, because `delete-backward` is declared
  `["collapsed"]` for the ten v1 actions (`tools/build_e2_b_profile.py:81-86`)
  and a cut runs on a range by definition.
* The refusal's **disposition** was finding 063 and is fixed: the session stays
  `ready`, the document is untouched, and the user is told why.

So today cut is effectively copy. That is not in question.

## What IS under test

**Does the shipped engine `29ec627b` actually remove a range when
`delete-backward` is dispatched on one?**

The manifest's declaration is not wrong — it is honest about a measurement
nobody made:

> range dispatch was characterised for the paragraph actions, not for delete or
> insert, and **declaring a gesture nobody measured** would be the manifest
> claiming coverage the evidence does not have.

This supplies the measurement. **The manifest is not widened first.**

## Why both range bits are granted together

`src/probe_engine.cpp:4364-4374` requires **both** `RANGE_SINGLE` **and**
`RANGE_CROSS` for any selection the build has not classified:

```cpp
collapsed ? editorGesturePermitted(action, kGestureCollapsed)
          : (editorGesturePermitted(action, kGestureRangeSingle) &&
             editorGesturePermitted(action, kGestureRangeCross));
```

Granting one alone refuses **every** range, so two arms split by bit would both
measure the same refusal and read as "range delete does not work". The axis that
can actually vary is the **selection shape**, so that is the axis swept.

## No link, and no write to the bound artifact

The gesture mask **intersects** (`probe_engine.cpp:5736-5748`): a manifest can
withhold a class the binary implements and can never grant one it does not. The
binary already routes all three classes. `dist/` is never written — the widened
manifest is served from a symlink mirror, the same mechanism `apply_mutation`
uses, and `probe.wasm` stays byte-identical to `29ec627b`.

## The predictions

Thresholds fixed here, before the run.

### P-CUT-1 — the refusal is the manifest's, not the engine's

With both range bits granted to `delete-backward`, the cut **no longer reports**
`EDITOR_FORMAT_GESTURE_UNSUPPORTED`.

*If it still does*, the refusal comes from somewhere other than the gesture mask
and everything below is void — the diagnosis in the queue item is then wrong and
must be corrected before anything else is claimed.

### P-CUT-2 — a single-paragraph range is removed

Cut on a range **inside one paragraph**: the selected text is **absent from the
saved ODT**, the surrounding text of that paragraph survives, and both
neighbouring paragraphs survive.

The oracle is the **saved document**, not the revision counter: a revision that
advanced proves a dispatch, not a deletion.

### P-CUT-3 — the session survives it

State stays `ready`, and the product can save afterwards. A delete that removes
the text and wedges the session is not a fix.

### P-CUT-4 — the cross-paragraph shape is recorded, not assumed

A range **spanning two paragraphs** is measured and its outcome **recorded**. No
prediction is made about it: the five paragraph actions were characterised for
cross-paragraph ranges and the ten v1 actions were not, so predicting here would
be the same unmeasured confidence this item exists to remove.

**If P-CUT-4 removes text unevenly** (some blocks emptied, others not), that is a
finding in its own right and the manifest is **not** widened for `RANGE_CROSS`
semantics on the strength of P-CUT-2.

## What happens on each outcome

| | |
|---|---|
| P-CUT-1 and P-CUT-2 and P-CUT-3 hold | Declare it: `RANGE_DELETE_CHARACTERISED` in the v3 builder naming this evidence, gesture widened **in `build_e2_c_profile.py`'s v3 map only** (never the shared v2 one — `tests/test_e2_b_profile.py:78` pins v1 actions caret-only under both dispositions, and "one path, two identities" is what that builder's docstring was written against), queue item flipped, the cut check extended to require the text is **gone**, row `cut` → `done` |
| any of them fails | Record the measurement. The row stays `partial` with a **measured** reason instead of an undeclared one, and "an action that deletes a selection" joins the ABI proposal. **Do not widen the manifest to close the row.** |

## Traps this run must not repeat

* **One arm per fresh engine session.** The 2026-08-19 trap: a probe that swept
  a parameter ascending in one session carried state between arms and exonerated
  the engine wrongly.
* **The oracle is the saved ODT**, anchored to a named paragraph, with the
  neighbours required to survive.
* **`dist/` is never written**, and nothing is rebuilt between the sweep and the
  verdict (`wasm-build-not-reproducible`).
* The clipboard grant is **Chrome-only** (it needs CDP). On Firefox the copy half
  is denied by the driver and the delete never runs, so that arm measures the
  refusal path and must report `NOT_ESTABLISHED`, not a product failure.

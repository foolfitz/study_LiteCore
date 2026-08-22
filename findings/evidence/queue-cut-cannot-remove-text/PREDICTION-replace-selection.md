# Prediction, written before the measurement (2026-08-21, second arm)

Follow-up to [`PREDICTION.md`](PREDICTION.md) / [`RESULT.md`](RESULT.md), which
measured that widening the gesture mask does **not** make cut work — the
selection barrier refuses instead.

This arm asks a different question, and fable found it: **does cut need engine
work at all?**

## Why this arm exists

Two source facts, both verified before writing this:

1. **The empty-text refusal is a JavaScript guard, not an engine one.**
   `sdk/document-sdk.js:468-472` throws `INVALID_ARGUMENT` for
   `text.length === 0`. The engine's `handleReplaceSelection`
   (`src/probe_engine.cpp:3199-3216`) is a plain LOK
   `paste("text/plain;charset=utf-8", data, size)` with **no empty-text gate** —
   the caller's bytes and length go straight through.
2. **The selection barrier's collapsed-caret requirement is by design**, because
   it manufactures its own one-unit selection: `startSelectionBarrierDelete`
   (`:3143-3151`) refuses any pre-existing selection, then posts shift+Left/Right
   itself (`:3167-3173`).

So `delete-backward` can never accept a range — but `replaceSelection` does not
go near the barrier. **If LOK's `paste` with zero-length text deletes the
selection, cut closes with no engine change and no link.**

That would remove an item from the link payload, which is why this runs before
the link and not after.

## What is mirrored (dist/ is never written)

Two shipped files, in a symlink mirror, `probe.wasm` byte-identical to
`29ec627b`:

* `sdk/document-sdk.js` — the empty-text guard removed.
* `web/e2-editor-app.js` — the cut handler's delete half calls
  `session.document.replaceSelection("")` instead of
  `session.action("delete-backward")`.

**Declared bypass:** calling `session.document.*` goes around the shell's
`_enqueue`, so the state machine does not see this mutation. That is acceptable
for a diagnostic and is why the report is stamped diagnostic; it is **not** how
a shipped fix would be written (that would add a wrapped `replaceSelection` to
`EditorSession`, which is a shell change and mints a generation, but is still
not a link).

## The predictions

### P-RS-1 — the call is accepted

With the JS guard removed, `replaceSelection("")` reaches the engine and the
engine does not answer `LOK_ERROR`.

*If it answers `LOK_ERROR`*, LOK's `paste` rejects empty text and this route is
closed — record it and cut stays in the link payload.

### P-RS-2 — the selected text is gone from the saved ODT

The target paragraph's text is **absent**, its neighbours **survive**, and the
document is a valid ODT.

**The oracle is the saved document**, anchored to a named paragraph. Not the
revision counter: a revision that advanced proves a dispatch, not a deletion.

**Guarded**: if the save after the cut does not produce a readable ODT, every
"is it still there" question returns **null**, not false. That mistake was made
in this very item's first arm today and is not repeated.

### P-RS-3 — the session survives

State stays usable and the product can save afterwards. A delete that removes
the text and wedges the session is not a fix.

## What each outcome does to the link payload

| | |
|---|---|
| all three hold | **cut leaves the link payload.** The remedy is a shell change (wrap `replaceSelection` in `EditorSession`, use it for cut's delete half) plus characterisation — no engine work, no link item. The payload drops to five |
| P-RS-1 fails | LOK refuses empty paste. Cut **stays** in the payload as a distinct `delete-selection` action, id 20, range-only |
| P-RS-2 or P-RS-3 fails | the route is worse than the refusal it replaces. Cut **stays** in the payload, and whatever went wrong is recorded — a delete that half-works or wedges is a finding |

## Traps

* **Do not widen the manifest.** This arm does not touch gestures at all.
* **One arm per fresh engine session.**
* **Chrome only** for the removal half — the clipboard grant needs CDP, so on
  Firefox the copy is denied by the driver and the delete never runs. That arm
  reports `NOT_ESTABLISHED`, not a failure.

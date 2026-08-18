# Finding 059 — replacement predicate: prediction, written before the probe

Written 2026-08-18. **No arm of the probe described here has been run.** The
probe, its runner and its analyzer do not exist yet; this file is committed
first so the predictions below can be wrong in public.

Subject: native LibreOffice core 26.8 (`build-native-26-8`, `SAL_USE_VCLPLUGIN=svp`),
the same commit the shipped WASM artifact was built from. **Nothing here
describes the WASM build** — findings 040 and 048 are what that rule is for, and
059's own first mechanism was got wrong in exactly that gap. The WASM half is a
separate measurement.

## What is already settled, and by what

Recorded so the probe does not re-measure it and so a reader can see which
claims are load-bearing without evidence of their own.

### Settled by core's source

1. **`wasModified` cannot be a predicate for "did this command change the
   document".** It is `pDocSh && pDocSh->IsModified()` evaluated as an argument
   to the `DispatchResultListener` constructor, i.e. **before**
   `comphelper::dispatchCommand()` runs (`desktop/source/lib/init.cxx:5517-5518`);
   the member's own comment says "modified **before** saving" (`:5073`) and
   `dispatchFinished()` copies it out unchanged (`:5098`). It reports whether the
   document was already dirty.

2. **An unknown slot emits no command result at all.**
   `comphelper::dispatchCommand()` returns false as soon as `queryDispatch()`
   yields null (`comphelper/source/misc/dispatchcommand.cxx:48-50`), so the
   listener is never called. A refusal arm must therefore use a command core
   **knows but cannot currently run**.

3. **All four inline slots are in core's kit command list — and our engine says
   they are not.** `Bold`, `Italic`, `Underline` and `Strikeout` all appear in
   `GetKitUnoCommandList()` with `PayloadType::IsActivePayload`
   (`sfx2/source/control/unoctitm.cxx:1165ff`, entries at +4, +12, +22, +23),
   the same entry kind as `DefaultBullet`, whose broadcast the barrier already
   relies on. The list is unconditional — no build flag gates it.

   **This contradicts a comment in our own engine.** `src/probe_engine.cpp:4308-4310`,
   above the underline and strikethrough cases, states:

   > Neither command appears in core's `GetKitUnoCommandList()`, so no
   > format-state cache is kept for them

   That sentence is false for the tree we build from, and it is load-bearing: it
   is the stated reason those two slots have no state fields at all, which is in
   turn the reason the readback looks unavailable for them.

   **What is still open** is whether list membership means a broadcast actually
   arrives at runtime — the list has consumers (`unoctitm.cxx:1471`,
   `lokhelper.cxx:1157`) and membership is necessary, not obviously sufficient.
   P4 and P5 below are exactly that question, and they are written so that "the
   engine's comment was right for the wrong reason" is a possible outcome.

### Settled by this tree's own prior measurement

4. **Neither `success` nor `wasModified` tracks the document, and
   `LOK_CALLBACK_STATE_CHANGED` did.** Finding 020 (native 26.8, 2026-08-05)
   measured `.uno:RemoveBullets` reporting `success:false` and
   `.uno:DefaultBullet` reporting `wasModified:false` while both demonstrably
   changed the document — and recorded that all three commands' `STATE_CHANGED`
   broadcasts agreed with the saved file. The engine carries that conclusion in
   a comment at `src/probe_engine.cpp:1722-1726` and gates the barrier on the
   readback rather than on either field.

So the replacement predicate is not a new design. It is the barrier's existing,
already-validated basis, applied to four commands that never got it.

### Settled about our own engine

5. **The engine watches only two of the four slots.**
   `parseFormatStatePayload()` recognises `.uno:Bold`, `.uno:Italic`,
   `.uno:DefaultBullet`, `.uno:DefaultNumbering` and `.uno:StyleApply`
   (`src/probe_engine.cpp:1169`), and `EditorState` has `boldKnown`/`italicKnown`
   and no underline or strikeout fields at all (`:273-275`). Whatever core sends
   for the other two is discarded today.

## What is NOT settled, and is what this probe measures

Finding 020's shape is a **paragraph-level** command with the caret inside
existing text. The four inline formats on a **collapsed caret** are a different
shape: they set the attributes of the insertion point, and change nothing until
something is typed — which is why 059's first probe, which saved immediately
after dispatching, made every arm look identical.

Nothing has measured whether the state broadcast is truthful for *that* shape.

## Predictions

Each is written so that failing is meaningful, and each names what its failure
would cost.

| | prediction | if it fails |
|---|---|---|
| **P1** | After a parameterised `.uno:Bold` with `value:true` on a collapsed caret in a plain paragraph, core emits `LOK_CALLBACK_STATE_CHANGED` with payload `.uno:Bold=true`, and the marker typed next comes back `fo:font-weight="bold"` in the saved ODT. | The readback does not track the insertion point's attributes; the only surviving candidate for the simplest slot is gone and the predicate must be redesigned. |
| **P2** | The same dispatch with `value:false` emits `.uno:Bold=false`, and the marker comes back not bold. | The broadcast is not directional — it announces that something happened, not what. A predicate built on it would accept a command that did the opposite. |
| **P3** | `.uno:Italic` behaves as P1/P2 do. | Bold is special; per-slot measurement was necessary and the remaining slots are each their own question. |
| **P4** | **`.uno:Underline` behaves as P1/P2 do**, emitting `.uno:Underline=true` / `=false`. | Being in `GetKitUnoCommandList()` is not sufficient for a broadcast to arrive; item 3 above is not load-bearing and this slot needs a different answer. |
| **P5** | **`.uno:Strikeout` behaves as P1/P2 do**, emitting `.uno:Strikeout=true` / `=false`. | As P4. |
| **P6** | A **refusal arm** — a command core knows but cannot run in the current context — produces a command result and **no** state change for the slot under test. | The readback cannot separate an applied command from a refused one, which is the whole job. `success`, `wasModified` and the readback would then all be unsound and the predicate has to come from somewhere else entirely. |
| **P7** | The state change for a collapsed-caret inline dispatch arrives **without any selection command being issued** — the barrier's `.uno:SelectText` step is not needed for this shape. | The predicate costs a selection on every inline format, which on an empty paragraph is the shape that produced finding 046. That is a materially more expensive and riskier fix, and it must be judged rather than assumed. |

## Controls the probe must carry, or it measures nothing

* **A no-dispatch control arm.** A marker typed with no command dispatched must
  come back unstyled. Without it, "the marker is bold" can be the fixture's own
  style — the shape codex flagged, since the E1 corpus already declares an unused
  `E1Bold` and a bold heading style.
* **The verdict is read from the style actually attached to that arm's marker
  run**, resolved through `content.xml`'s style tree. A grep for
  `fo:font-weight` passes on a document where the marker is normal.
* **Every arm must show it received a fresh callback** — recorded by
  `startUnixTimeMics` or a sequence number. An arm that produced no callback must
  be reported as such and must not be scored. This is what makes P6 falsifiable
  rather than vacuous.
* **The analyzer must reject a constant.** If the state-change payload for the
  slot under test is identical across every arm, that is P1–P6 failing, not
  "consistent" — a field that never varies is not a predicate.
* **One document per arm, or a save per arm.** The existing four-arm probe shares
  one document and types before every dispatch, which is why its `wasModified`
  column carried no information.

## What this probe will not answer

* Why core reports `success:false` for a command it applied. Not measured, not
  named (040/048 precedent).
* Anything about the WASM build.
* Whether the engine *should* adopt the readback — that is a design decision
  taken after these numbers exist, and if the slots disagree it goes to
  adjudication rather than to my own judgement.

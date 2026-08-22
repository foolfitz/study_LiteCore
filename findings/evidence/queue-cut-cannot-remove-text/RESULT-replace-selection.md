# Result (2026-08-21) — the empty-text route is closed too, and it is closed in compiled code

Measured against
[`PREDICTION-replace-selection.md`](PREDICTION-replace-selection.md), written
first. Artifact `29ec627b`, Chrome, clipboard granted.

**Verdict: P-RS-1 FAILS. `cut` stays in the link payload.**

## The question

fable proposed that cut might need no engine work at all, on two source
readings:

* the empty-text refusal is a JavaScript guard (`sdk/document-sdk.js:468-472`) —
  **true**;
* the engine's `handleReplaceSelection` (`src/probe_engine.cpp:3199-3216`) is a
  plain LOK `paste` with no empty-text gate — **also true**.

Both correct. The conclusion did not follow, because there is a gate **between**
them.

## What the arm found: four layers, and the last one is compiled

Each gate was removed in a mirror (`dist/` never written, `probe.wasm`
byte-identical) and the next one appeared behind it.

| | where | what it says | JS or compiled |
|---|---|---|---|
| 1 | `sdk/document-sdk.js:468` | `replaceSelection requires non-empty text` | JS |
| 2 | `profiles/e2-editor-v3/sdk-worker.js:352` | `unable to allocate 0 bytes in WASM` | JS — and **incidental**: `withWasmBytes` asks for `length` bytes and throws when the pointer is falsy, so a generic allocation-failure check also refuses every empty payload |
| 3 | **`src/sdk_api.cpp:172-174`** | `OXSDK_STATUS_INVALID_ARGUMENT` | **compiled** |
| 4 | `src/probe_engine.cpp:3199-3216` | *(no gate)* | never reached |

Gate 3 is the answer:

```c
if (!validRequest(requestId) || documentHandle == 0 || !utf8 ||
    utf8Length == 0)
  return OXSDK_STATUS_INVALID_ARGUMENT;
```

Surfaced as `剪下：INVALID_ARGUMENT：replaceSelection was rejected before
queueing` — the worker's `accept()` (`sdk-worker.js:372-378`) reporting a
**non-zero status returned by the engine**, not a fourth JS check. The call did
reach the engine; the engine refused it at its ABI boundary, one layer above the
handler fable read.

**So `handleReplaceSelection` having no empty-text gate is true and
unreachable.** Reading the handler without reading its export wrapper is what
made the route look open.

## Against the predictions

| | Prediction | Outcome |
|---|---|---|
| **P-RS-1** | the call is accepted | **FAILS** — refused in compiled code |
| **P-RS-2** | the selected text is gone | not reached |
| **P-RS-3** | the session survives | **holds, incidentally** — `ready`, document unchanged, neighbours intact, save works |

The recording is honest this time: `documentReadableAfter: true`,
`targetStillPresent: true`, `linesBefore: 9`, `linesAfter: 9`. Nothing was
damaged, and nothing is claimed from an empty capture — the mistake this item's
first arm made this morning.

## Consequence for the link payload

Per the prediction's own table, P-RS-1 failing means **cut stays**, as a
**distinct `delete-selection` action, id 20, gestures range-single +
range-cross only** — not a widened `delete-backward`, which keeps
`delete-backward`'s measured caret-only characterisation untouched.

**The payload is therefore six items, not five.** The contingency fable attached
to it is resolved, and resolved the way that keeps the item in.

Relaxing gate 3 instead is *also* an engine change, so it buys nothing: either
way the artifact is rebuilt. A dedicated action is the better of the two —
it declares its gestures natively and refuses at a collapsed caret rather than
silently doing nothing.

## What is still not established

**Whether LOK's `paste` with zero-length text actually deletes a selection.**
No arm has reached it: gate 3 stops every route that exists today. It stays
open, and it is worth one probe *inside* the link work, because if LOK does
delete on empty paste then `delete-selection` can be implemented by relaxing
gate 3 and reusing `handleReplaceSelection` rather than writing a new barrier
entry.

Do not assume it either way. The barrier-entry route
(`startSelectionBarrierDelete` at `:3143-3151` refuses a pre-existing selection
by design, then posts shift+Left/Right to make its own) is the fallback and is
independently sound.

## Method note

Three mirrored files, each added only after the previous run named the next
gate. That is the right shape — but the reason it took three arms is that the
first two were designed from a **source reading that stopped one layer short**.
Reading a handler is not reading the path to it.

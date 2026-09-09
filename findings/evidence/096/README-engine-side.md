# 096 — the engine side: does the engine thread still answer, and did core broadcast anything?

**Protocol**: `handoff/tasks/TASK-2026-09-09-096-does-the-engine-thread-still-answer.md`,
registered and committed before the probe existed. Its `## Execution record`
carries the three changes shakedown 1 forced, all made before the first counted
attempt.

**This directory names no cause beyond what the registered table licenses.** It
answers one question — after a boundary arrow press has killed the session, is
the engine thread still executing commands, and did core invoke its LOK callback
between the press and the verdict? — and banks the raw payloads while it does.

It is the measurement
`handoff/DECISION-2026-09-09-which-layer-can-carry-096s-fix-and-what-each-costs.md`
§2.3 named as the cheapest next step: **no build, no relink, no product byte
moved.**

## Files

| file | what it is |
| --- | --- |
| `probe_096_engine_side.py` | the instrument. It imports `probe_096_boundary_arrow.py` for the gesture, the predicate, the arms and the document, and adds three things inside the **live worker's own realm**. |
| `engine-side-e2-editor-v8.json` | arm C — **the shipping bytes** |
| `engine-side-e2-editor-v13.json` | arm A — the candidate |
| `engine-side-shakedown-1-e2-editor-v8.json` | the uncounted shakedown, banked because the protocol says every attempt is reported. Its stored `cell` was computed by the pre-change classifier and is the instrument defect the execution record describes, not a result. |
| `summarise_engine_side.py` | reads whatever `engine-side-*.json` are present and prints every attempt |
| `RESULT-engine-side.md` | the verdict, read back against the table registered before the run |

## What the instrument adds, and why it is in the worker's realm

The page, the shell and the SDK are the layers the earlier evidence already
shows are blocked — the shell's queue fills 1→6, the SDK's 30 s deadline fires
to the millisecond, and the engine refuses the cancel. Asking any of them is
asking the wrong side. So all three additions run **inside the document
worker's own JavaScript realm**, reached through the CDP session
`Target.setAutoAttach` gives, re-enabled after the open because opening a
document replaces the worker.

1. **A wrapper on `globalThis.__probe_on_event`.** That global is the engine's
   only route into JavaScript: `emitJson` (`src/probe_engine.cpp:1032-1045`)
   does `MAIN_THREAD_EM_ASM(... globalThis.__probe_on_event(eventJson) ...)`,
   and the lookup happens at call time, so a wrapper installed after the module
   booted is called. The raw JSON **string** is banked verbatim, and the buffer
   index is marked before every press so emissions are attributable to a press.

2. **A pass-through wrapper on `self.postMessage`**, so the worker's own
   replies are visible from inside the worker.

3. **Three requests injected** by dispatching a `MessageEvent` on the worker's
   global — the worker listens with `self.addEventListener("message", …)`
   (`sdk/sdk-worker.js:1571`), so this reaches `handleRequest` exactly as a real
   post would. Ids `4000000000`–`4000000002`, which `document-sdk.js:_nextId`
   cannot issue.

   | tag | request | what it is for |
   | --- | --- | --- |
   | **C** | `f096ControlNoSuchOperation` | the **injection-route control**: answered `UNKNOWN_OPERATION` by the worker's own switch default, **without touching the engine**. Without it, "the engine did not answer" and "my injection never arrived" are the same silence. |
   | **G** | `editorGetStateV2` | goes through the engine's command queue (`probe::editorGetState` → `submit()`) and is run by `handleEditorGetState`, which answers synchronously and **does not touch `gEditorPending`**. Its reply carries `sourceSequence`. |
   | **P** | `editorActionV2`, same action as the arrow | the **positive control**: `handleEditorAction`'s first test after `requireDocument` is `gEditorPending.requestId != 0` → `BUSY` (`src/probe_engine.cpp:4624-4628`). It must answer `BUSY`; anything else voids the attempt rather than being reinterpreted. |

   `documentHandle` and `expectedRevision` are read out of the **worker's own
   `pending` map** — the wedged `editorActionV2`'s payload — not from the page.

## The `lok` line, and why the (a)/(b) separation needs no engine change

`onLokCallback` (`src/probe_engine.cpp:2372-2381`) is the function
`registerCallback` hands to LOK (`:2801`). Its first act — **unconditional,
before the type switch, outside every `#ifdef`** — is

```
emitJson("{\"type\":\"lok\",\"id\":<type>,\"payload\":\"<verbatim>\",…}");
```

So **every LOK callback of every type already produces one line**, and the
wrapper reads it. The protocol's §2.3 originally said this would need a counter
added to the trampoline, i.e. an engine edit, a relink and the decision doc's
row A cost. That was wrong, and the execution record corrects it: the
separation is complete at the LOK boundary on the **shipped** engine.

## What is held constant, and what varies

The page source is the current `web/e2-editor-app.js` with only the worker URL
and the pinned wasm hash rewritten (`repointed_page`), so the two arms isolate
the **engine**. Arm C's page is byte-identical to the shipped
`dist/e2-editor-app.js` (`1ec7baf9fb53c808…`).

| arm | page sha256 | probe.wasm | worker sha256 |
| --- | --- | --- | --- |
| C — `e2-editor-v8` (**shipping**) | `1ec7baf9fb53c808…` | `4a2710bba1ef07d9` | `070229cd10bda4a0…` |
| A — `e2-editor-v13` (candidate) | `31787584290e42bd…` | `0fe25650bec1bac5` | `6e75829a2911c1df…` |

Both manifests offer `move-line-up` / `move-line-down` with
`gestures: ["collapsed"]` and `limits: ["no-extend-selection"]`, checked before
the run rather than assumed.

The gesture, the document (`~/Documents/SLAT/e20-專訪瓦特老師.odt`, sha256
`63bf89cb…`, the owner's own file), the predicate (`data-state` ∈ DEAD_STATES
**and** `#notice` shown **and** `data-rescue == "none"`) and the viewport
(1920x1080) are all unchanged from `probe_096_boundary_arrow.py`.

## What this does not measure

- **Why core did not broadcast**, in the cases where it did not. A `lok` count
  of zero says core did not invoke the registered callback in the window; it
  does not say what inside core decided that.
- **A callback delivered after the window closes.** The window ends at the
  verdict.
- **A physical keyboard.** Keys are injected at the renderer by
  `Input.dispatchKeyEvent`, as in the earlier probe.
- **The other things finding 096 registers as possibly-separate** — the
  viewport not following the caret, and finding 095. Not measured here, not
  merged.

# Finding 059 — does a PASTE carry the caret's pending inline attribute? (native)

Round `round-20260818T072437Z`, native core 26.8 (`build-native-26-8`,
`SAL_USE_VCLPLUGIN=svp`), fixture `test-docs/f059-predicate-paragraphs.odt`.
Reproduce: `tools/run_f059_native_paste_pending.sh`.

**Nothing here describes the WASM build.**

## Why this round exists

The WASM half of 059 has to read the document effect of a command the product
reports as failed. On a collapsed caret an inline format is a *pending*
attribute — it changes nothing until something is inserted — and the product's
only text-entry path is `handleInsertText`, which calls LOK `paste` first and
falls back to `postKeyEvent` only when paste returns false
(`src/probe_engine.cpp`). The page discards the response, so a browser run
cannot see which mechanism ran.

So an unstyled marker on WASM would have had two explanations. This round
removes one of them from the list of *mechanisms* — it does not, and cannot,
describe WASM.

## What came back

| arm | dispatched | inserted by | paste returned | marker | style in the saved document |
|---|---|---|---|---|---|
| `paste-after-bold` | `.uno:Bold` true | **paste** | true | `PPP` | **bold** (`T1`) |
| `type-after-bold` | `.uno:Bold` true | postKeyEvent | — | `TTT` | **bold** (`T2`) |
| `paste-no-command` | — | paste | true | `QQQ` | no span at all, not bold |

**A paste carries the caret's pending bold.** The positive control (typing)
agrees with the predicate round, and the negative control shows the fixture
supplies no styling of its own.

## A third, unplanned confirmation about `wasModified`

`paste-after-bold` ran first, on a freshly loaded document that nothing had yet
modified, and its command result is:

```json
{ "commandName": ".uno:Bold", "success": false, "wasModified": false }
```

`false` — on the arm that demonstrably applied bold. The next arm, on a document
by then dirty, reports `true` for the same command doing the same thing. That is
the pre-dispatch dirty flag behaving exactly as `init.cxx:5517-5518` says it
does, observed rather than only read.

## Not established

* Anything about WASM, including whether its paste behaves the same way.
* Why core reports `success: false` for commands it applied.

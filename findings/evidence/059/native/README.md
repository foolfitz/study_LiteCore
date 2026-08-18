# Finding 059, native control — core APPLIES the command and reports failure

Measured 2026-08-17 on native core 26.8 (`build-native-26-8`, `SAL_USE_VCLPLUGIN=svp`),
same commit as the WASM artifact. Probe source and the resulting document are in
this directory; it is reproducible with:

```
c++ -std=c++17 -I../libreoffice-26-8/include \
    -o build/f059-native/f059-native-inline-format \
    tools/f059_native_inline_format_argument.cpp -ldl
./build/f059-native/f059-native-inline-format \
    <install>/instdir/program file://<profile> file://<doc.odt> file://<outdir>
```

## The question, and why the first answer was wrong

Finding 059 was filed as "core rejects the parameterised `.uno:Bold`", because
the shipped product answers `LOK_COMMAND_FAILED`. That was inferred from the
command result. It is wrong.

Each arm places a caret, dispatches, **types a marker**, and the verdict is read
out of the saved ODT. The typing matters: bold on a collapsed caret changes
nothing until something is typed, and the first version of this probe saved
straight after dispatching and made every arm look identical.

| arm | marker | style in the saved document | bold? |
|---|---|---|---|
| control, no command dispatched | `AAA` | `T2` | no |
| **`.uno:Bold` + `{"Bold":{...,"value":true}}`** | `BBB` | **`T1`** — `fo:font-weight="bold"` | **YES** |
| `.uno:Bold` bare | `CCC` | `T4` — `fo:font-weight="normal"` | no |
| `.uno:Bold` + `{"Bold":{...,"value":false}}` | `DDD` | `T4` — `fo:font-weight="normal"` | no |

**The parameterised command does exactly what finding 045 intended.** `true`
produces bold, `false` produces normal.

## And it reports failure while doing it

Core's `LOK_CALLBACK_UNO_COMMAND_RESULT` for that same arm:

```json
{ "commandName": ".uno:Bold", "success": false, "wasModified": true }
```

The bare form reports `success: true`. So `success` here does not mean "the
command worked" — the arm that worked reports `false` and the arm that reported
`true` left the text not bold.

The control settles that this is not specific to bold:
`.uno:DefaultBullet` with `{"On":{"type":"boolean","value":true}}` — the exact
shape the product's own format barrier uses and which demonstrably works — also
reports `success: false` with `wasModified: true`.

## So the defect is ours

`probe_engine.cpp:1696`, `commandResultSucceeded()`, requires `success: true`,
and `:2286` turns anything else into `LOK_COMMAND_FAILED`. The barrier path does
not gate this way, which is why the list actions kept working while the four
inline formats stopped.

Finding 045's fix was correct. What broke is that it moved these four commands
onto an argument form whose result payload the engine's own predicate reads as
failure.

## Not established

* **That the WASM build also applies the command.** The product errors out and
  blocks the session, so the document effect there has not been read. The
  `success: false` it reports is consistent with this measurement, but
  "consistent with" is not "measured" — and this tree has been wrong in exactly
  that gap before (findings 040, 048, and 059's own first mechanism).
* **Why core reports `false` for an applied command.** Not measured, not named.
* **Whether the barrier's readback is a sound replacement predicate**, and
  whether it is sound for all four slots rather than for Bold alone. Not
  measured.

## Correction, 2026-08-18 — `wasModified` is not a candidate

This file previously listed `wasModified` as "the obvious candidate" for a
replacement predicate. That was wrong, and core's source settles it without a
measurement:

```
desktop/source/lib/init.cxx:5517-5518
    new DispatchResultListener(pCommand, pDocument->mpCallbackFlushHandlers[nView],
                               pDocSh && pDocSh->IsModified()));
```

The boolean is captured when the listener is **constructed**, which is an
argument evaluated before `comphelper::dispatchCommand()` runs. The member's own
comment says so — `//< Whether or not the document was modified before saving`
(`:5073`) — and `dispatchFinished()` copies that same value into the payload
unchanged (`:5098`).

So `wasModified` reports **whether the document was already dirty before this
command**, not whether this command changed anything. A previously edited
document makes a no-op command report `true`; a freshly saved one makes a
successful command report `false`.

The `wasModified: true` in the table above is therefore not evidence about that
arm: this probe shares one document and types a marker in every arm before the
next dispatch, so the document was already dirty by then.

**The mechanism this file establishes is unaffected** — "core applies the command
and reports failure" is read out of `fo:font-weight` in the saved document, not
out of `wasModified`. Only the proposed remedy changes.

### Consequence for the refusal arms

A refusal arm must use a command core **knows but cannot currently run**, never
an unknown slot: `comphelper::dispatchCommand()` returns false as soon as
`queryDispatch()` yields null (`comphelper/source/misc/dispatchcommand.cxx:48-50`),
so the listener is never called and **no `LOK_CALLBACK_UNO_COMMAND_RESULT` is
emitted at all**. An unknown-slot arm measures nothing, and an analyzer that
defaults a missing field would score it as a pass. Every arm must show it
received a fresh callback.

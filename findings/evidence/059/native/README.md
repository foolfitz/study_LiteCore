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
* **Whether `wasModified` is a sound replacement predicate.** It is the obvious
  candidate and it is untested; the barrier's readback is the other.

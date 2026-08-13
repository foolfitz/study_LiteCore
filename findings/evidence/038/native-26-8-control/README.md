# Native same-commit control for findings 037 / 038 / 012

2026-08-13. The control the upstream report rests on: **the same calls, the
same fixtures, the same anchors, on a native build of the very commit the WASM
engine was built from.** All of them return in milliseconds.

| build | |
|---|---|
| install | `build-native-26-8/instdir/program` |
| buildid | `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb` |
| source | `libreoffice-26-8` at the same commit |
| probe | `findings/repro/037-as-char-frame-hang/lok_frame_hang.cpp` |
| VCL | `SAL_USE_VCLPLUGIN=svp`, fresh user profile per run |

The probe prints an `enter` line before every LOK call and an `exit` line
after it, so **a call that hangs is the one whose `enter` has no `exit`**.
Every run here has a matching pair for every step.

| log | fixture / anchor / span | call under test | result |
|---|---|---|---|
| `fx-note-8000.log` | `frame-contexts` `FX-NOTE` 8000 tw | `getSelectionTypeAndText(text/plain)` | **2 ms, 47 B** |
| `fx-note-2400.log` | `frame-contexts` `FX-NOTE` 2400 tw | same | 2 ms, 20 B |
| `fx-plain-8000.log` | `frame-contexts` `FX-PLAIN` 8000 tw | same | 2 ms, 41 B |
| `frame-no-image.log` | `frame-no-image` `FNI-TEXTBOX` | `getTextSelection(text/html)` | 3 ms, 629 B |
| `frame-paragraph-anchored.log` | `frame-paragraph-anchored` `FPA-FRAME` | same | 1 ms, 533 B |

Every number in this table is read out of the log file beside it. An earlier
ad-hoc pass of the same runs gave 8 ms and 4 ms for two of these rows; those
were a different run and are not what is recorded here.

`destroy(document)` returned in 2–3 ms in all five runs — including on
`frame-contexts.odt` and `frame-no-image.odt`, both of which carry as-char
frames and both of which need a worker restart under WASM (finding 012).

## The span pair is what proves the selection reached the trigger

A native control is only a control if it reproduced the same input state. The
two spans on the same anchor settle that without needing to trust the geometry:

```
2400 twips -> "FX-NOTE paragraph wh"                             (20 bytes)
8000 twips -> "FX-NOTE paragraph whose footnote holds a frame1"  (47 bytes)
```

The trailing `1` is the **footnote citation mark**, sitting inside the
extracted plain text — so the 8000-twip selection demonstrably covered the
citation, and the extraction demonstrably walked into the note apparatus. The
20-byte read matches, character for character, what the WASM harness read back
on the span measured *not* to hang.

That matters because the alternative reading of a passing control — "the drag
fell short, so of course nothing happened" — is exactly the mistake this
finding already made once, when a 513-twip span selected nothing at all and
looked like a safe partial selection.

## What this does and does not establish

**Does**: the three hangs are specific to the WASM build, not to the commit,
not to the fixtures, and not to the calls themselves.

**Does not**: say anything about where in core the WASM build stops. There is
still no stack for any of the three symptoms.

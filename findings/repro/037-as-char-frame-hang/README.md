# An as-char `draw:frame` makes two LibreOfficeKit calls never return under WASM

Self-contained reproduction for [finding 037](../../037-a-paragraph-with-an-inline-image-wedges-the-handle.md)
and [finding 012](../../012-r6-styled-document-close-timeout.md).

Two different LibreOfficeKit calls fail to return in an Emscripten/WASM build,
on a document whose only unusual content is a `draw:frame` anchored
`text:anchor-type="as-char"` inside a `text:p`:

1. **`getTextSelection(doc, "text/html", nullptr)`** over a selection covering
   that paragraph.
2. **`destroy(doc)`** on the same document.

Both return in single-digit milliseconds in a native build of the same commit.

**No image is involved.** The frame in these fixtures holds only a
`draw:text-box`; there is no `Pictures/` member, `draw:image` appears zero
times, and the manifest lists only the two XML parts. Images were how this was
first noticed, not what triggers it.

## The one-attribute boundary

The two fixtures differ by exactly one attribute and nothing else — same three
paragraphs, same text box, same styles, no images in either:

| fixture | `text:anchor-type` | `getSelectionType` | WASM `getTextSelection(html)` | WASM `destroy` |
|---|---|---|---|---|
| `frame-no-image.odt` | **`as-char`** | 3 (`COMPLEX`) | **never returns** | **never returns** |
| `frame-paragraph-anchored.odt` | `paragraph` | 1 (`TEXT`) | returns, 524 bytes | returns, 11 ms |

The selection type differs natively too, so that part is ordinary core
behaviour. Only the hang is specific to the WASM build.

## Files

| file | what it is |
|---|---|
| `frame-no-image.odt` | the failing case: one as-char frame, no images anywhere |
| `frame-paragraph-anchored.odt` | the control: identical but paragraph-anchored |
| `lok_frame_hang.cpp` | minimal LOK probe; prints an enter/exit line per step |

The probe prints before and after every call, so **the step that hangs is the
one whose `enter` line has no matching `exit` line**. A call that does not
return cannot report its own timing, which is why nothing here measures
durations of the failing step.

## Building and running (native)

```sh
g++ -std=c++17 -O2 -I<core>/include lok_frame_hang.cpp -ldl -o lok_frame_hang

SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
    <instdir>/program file:///tmp/lok-profile \
    "file://$PWD/frame-no-image.odt" FNI-TEXTBOX

SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
    <instdir>/program file:///tmp/lok-profile \
    "file://$PWD/frame-paragraph-anchored.odt" FPA-FRAME
```

Measured with LibreOffice 26.2.4.2 (system build), both fixtures, every step
returning:

```
frame-no-image.odt (as-char)              frame-paragraph-anchored.odt (control)
  documentLoad          118 ms              documentLoad          111 ms
  SelectText             12 ms              SelectText             11 ms
  selectionType           3                 selectionType           1
  getTextSelection        4 ms, 624 B       getTextSelection        1 ms, 528 B
  destroy(document)       2 ms              destroy(document)       2 ms
```

## Reproducing the hang

Build LibreOffice for WASM per `static/README.wasm.md` and drive the same
sequence through LibreOfficeKit from the engine thread. Under Emscripten,
`getTextSelection(…, "text/html", …)` does not return for the as-char fixture,
and the thread stops there: no further LOK callback of any kind arrives, and
the command queue is never drained again.

Our own harness observed it as:

- The dispatching thread stops inside the call. It is not waiting for a
  callback — the callback stream simply ends, mid-sequence, for the remaining
  86 seconds of the run.
- The worker's JS thread stays alive, the wasm module is still callable from
  that thread, and the engine's global mutex is free. Only the thread that
  entered the call is stuck.
- `destroy(doc)` behaves the same way on the same document. On **these**
  fixtures that was observed after a selection sequence — nobody has run a bare
  open→destroy on them. Bare open→close was measured on a different document
  (an as-char image frame), Chrome and Firefox, both timing out at the full
  180 s, so "no selection needed" is carried over rather than established here.

Measured on Chrome 150.0.7871.128 and Firefox 153.0.1 with identical
signatures, core commit `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`, across two
independently built engine artifacts.

## What is not known

**Neither symptom has a stack.** We know the calls do not return and where
they are entered from; we do not know where inside core they stop. That is the
next thing worth having and it needs a diagnostic WASM build.

The evidence that the two symptoms share a cause is that they turn on the same
one attribute, reached independently from the read side and the teardown side.
That is an inference, not an attribution — nobody has shown they run through
the same code.

Also not measured: `text:anchor-type="char"` for the destroy hang (its
selection type is `COMPLEX`, like as-char), frames in table cells or
footnotes, OLE objects, charts, and `draw:g` groups. No counterexample is not
the same as no counterexample existing.

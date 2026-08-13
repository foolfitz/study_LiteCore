# An as-char `draw:frame` makes three LibreOfficeKit calls never return under WASM

Self-contained reproduction for [finding 037](../../037-a-paragraph-with-an-inline-image-wedges-the-handle.md),
[finding 012](../../012-r6-styled-document-close-timeout.md) and
[finding 038](../../038-a-frame-inside-a-footnote-wedges-the-engine-on-selection.md).

Three LibreOfficeKit calls fail to return in an Emscripten/WASM build, when a
`draw:frame` anchored `text:anchor-type="as-char"` is reachable from the
current selection:

1. **`getTextSelection(doc, "text/html", nullptr)`** over a selection covering
   the paragraph that holds the frame.
2. **`destroy(doc)`** on the same document.
3. **`getSelectionTypeAndText(doc, "text/plain;charset=utf-8", …)`** over a
   selection covering the **citation mark of a footnote whose body holds the
   frame** — where the frame is nowhere near the selected text.

All three return in single-digit milliseconds in a native build of the same
commit.

**1 and 3 are the same extraction path reached two ways, and the difference
matters to anyone writing a client.** When the frame sits directly inside the
selection the type comes back `COMPLEX`, the text is never extracted
implicitly, and only an explicit `text/html` request hangs. When the frame is
reachable only through a footnote citation the type is `TEXT`, and the
extraction walks into the note body by itself. So a guard that refuses to read
unless the selection type is `TEXT` stops 1 and **does not stop 3** — we
shipped that guard and it does not help here.

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

## The two-condition boundary for symptom 3

Symptom 3 needs **both** conditions, and all four cells were measured under
WASM on the shipped editor artifact:

| | note body **has** a frame | note body has **no** frame |
|---|---|---|
| selection **covers** the citation | **never returns** | returns, 8 ms |
| selection **stops short** of it | returns, 6 ms | — |

The short-span row is what rules out "any selection in that paragraph": same
paragraph, same kind of drag, 2400 twips instead of 8000. Natively the two
spans extract

```
2400 twips -> "FX-NOTE paragraph wh"                             (20 bytes)
8000 twips -> "FX-NOTE paragraph whose footnote holds a frame1"  (47 bytes)
```

and that trailing `1` is the citation mark, sitting in the extracted plain
text. So the extraction demonstrably walks the note apparatus — presumably
where it meets the frame.

## The engine is healthy right up to the call

Measured, not inferred, and it is the sharpest thing in this pack. Drive the
trigger selection, then issue exactly **one** further call, fresh engine per
probe, with the same drag over an ordinary frameless paragraph as the control:

| call after the trigger selection | control paragraph | trigger selection |
|---|---|---|
| `getSelectionTypeAndText(text/plain)` | 2 ms | **never returns** |
| editor state read (same extraction path) | 13 ms | **never returns** |
| `ExecuteSearch` | 18 ms | 19 ms |
| `paintTile` | 88 ms | 45 ms |
| paste (text insertion) | 9 ms | 4 ms |
| `saveAs` (ODT) | 215 ms | **141 ms** |

The selection breaks nothing. Search, render, edit and **save** all still
work after it. The extraction call is the only thing that hangs — and once it
has, those same six calls all stop returning, because the thread that owns the
document is inside it.

**We had this backwards until we controlled for it.** Our own liveness probe
was an editor-state read, which is the same extraction path, so "the engine is
already dead after the selection" was the probe killing what it was measuring.

## Files

| file | what it is |
|---|---|
| `frame-no-image.odt` | symptoms 1+2: one as-char frame, no images anywhere |
| `frame-paragraph-anchored.odt` | the control: identical but paragraph-anchored |
| `frame-contexts.odt` | symptom 3: `FX-NOTE` is the failing case, `FX-PLAIN` the control |
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

# symptom 3: the failing case, its control, and the short span that misses
SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
    <instdir>/program file:///tmp/lok-profile \
    "file://$PWD/frame-contexts.odt" FX-NOTE range
SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
    <instdir>/program file:///tmp/lok-profile \
    "file://$PWD/frame-contexts.odt" FX-PLAIN range
SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
    <instdir>/program file:///tmp/lok-profile \
    "file://$PWD/frame-contexts.odt" FX-NOTE range 2400
```

Use a **fresh user profile directory per run**. A reused profile can carry
state from the previous run into the next one, and these runs are supposed to
be independent.

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

**Same-commit native control** (2026-08-13, `build-native-26-8`, buildid
`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb` — the tree the WASM engine was built
from, so this is the control that matters most). Every step returns:

| fixture / anchor | call | native | WASM |
|---|---|---|---|
| `frame-no-image.odt` | `getTextSelection(html)` | 3 ms, 629 B | never returns |
| `frame-paragraph-anchored.odt` | `getTextSelection(html)` | 1 ms, 533 B | returns |
| `frame-contexts.odt` `FX-NOTE` | `getSelectionTypeAndText` | **2 ms, 47 B** | **never returns** |
| `frame-contexts.odt` `FX-PLAIN` | `getSelectionTypeAndText` | 2 ms, 41 B | returns |

`destroy(document)` returned in 2–3 ms in all five native runs, including on
`frame-contexts.odt` and `frame-no-image.odt`, both of which carry as-char
frames.

Logs: [`findings/evidence/038/native-26-8-control/`](../../evidence/038/native-26-8-control/).

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

**No symptom has a stack.** We know the calls do not return, where they are
entered from, and that everything else works until the call is made; we do not
know where inside core they stop. That is the next thing worth having and it
needs a diagnostic WASM build.

Symptoms 1 and 3 share an extraction path *in the API surface*, which is a
stronger link than we have for 2 — 2 is tied to the others only by the same
content feature, reached from the teardown side. Neither link is an
attribution: nobody has shown they run through the same code.

Also not measured: `text:anchor-type="char"` for the destroy hang (its
selection type is `COMPLEX`, like as-char); **why a frame in a table cell goes
down path 1 and a frame in a footnote goes down path 3** (the table-cell case
reports `COMPLEX`, so the type guard catches it — we do not know what makes the
footnote case report `TEXT` instead); how deeply a frame can be nested and
still trigger symptom 3 (only one level of footnote body was tried); OLE
objects, charts, and `draw:g` groups. No counterexample is not the same as no
counterexample existing.

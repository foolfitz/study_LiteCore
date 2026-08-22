# Where the 32,767 tile limit actually lives (2026-08-21)

`queue-engine-reports-success-for-an-unpainted-tile` said:

> WHERE in the engine is not established: that a 2^15 boundary is a signed
> 16-bit quantity is **an inference from the number** and **no source at that
> point has been read**. Worth an upstream look before it is called ours.

The source has now been read. **The number is right and the inference was
wrong**, which is exactly why the queue item forbade asserting it.

## Verdict: ESTABLISHED — Cairo's image-surface size check

`wasm-lite/build/workdir/UnpackedTarball/cairo/src/cairo-image-surface.c:59`,
and Cairo's own comment gives the reason:

```c
/* Limit on the width / height of an image surface in pixels.  This is
 * mainly determined by coordinates of things sent to pixman at the
 * moment being in 16.16 format. */
#define MAX_IMAGE_SIZE 32767

static cairo_bool_t
_cairo_image_surface_is_size_valid (int width, int height)
{
    return 0 <= width  &&  width <= MAX_IMAGE_SIZE &&
	   0 <= height && height <= MAX_IMAGE_SIZE;
}
```

**Not a signed 16-bit height, and not an overflow.** It is an explicit range
check Cairo performs because pixman's coordinates are **signed 16.16
fixed-point** — `pixman_fixed_t` is `int32_t`, not `int16_t`. Nothing in the
LibreOffice height lineage is ever narrowed to 16 bits.

It also applies to **width equally**. Our widths were always under the limit, so
what we measured was a height boundary; it is a *dimension* boundary.

## The chain, each hop read

| | |
|---|---|
| our engine | `probe_engine.cpp` mallocs `width*height*4` itself and builds the reply unconditionally |
| LOK ABI | `paintTile` is **`void`** — `include/LibreOfficeKit/LibreOfficeKit.h:228` |
| `doc_paintTile` | `desktop/source/lib/init.cxx:4288` calls `SetOutputSizePixelScaleOffsetAndLOKBuffer(...)` **and discards its `bool`**, then paints anyway at `:4292` |
| `VirtualDevice` | `vcl/source/gdi/virdev.cxx:384` — `bool bRet = mpVirDev->SetSizeUsingBuffer(...)`, correctly returned |
| SVP virtual device | `vcl/headless/svpvd.cxx:107-111` — wraps our buffer with `cairo_image_surface_create_for_data`, `SAL_WARN_IF` on failure, `return cairo_surface_status(...) == CAIRO_STATUS_SUCCESS` |
| Cairo | rejects the size, returns a **nil/error surface** with `CAIRO_STATUS_INVALID_SIZE` |

Our build reaches this path: `config_vclplug.h:22,32` are `ENABLE_HEADLESS 1`
and `USE_HEADLESS_CODE 1`, and LOK forces `SAL_USE_VCLPLUGIN=svp` before
`InitVCL()` (`init.cxx:8273`).

## Why nothing throws and everything reports success

Cairo's error model returns a **valid pointer to a nil surface** rather than
null, and drawing on an error context is a documented **no-op**. So:

* Cairo does not throw — it flags;
* SVP **does** capture the flag and returns `false`;
* `doc_paintTile` **drops that `false`** and paints on the error surface;
* the LOK ABI is `void`, so there is nowhere to report it anyway;
* `doc_paintTile` clears the last-error string on entry and never sets it again.

The buffer therefore comes back **exactly `width*height*4` bytes and completely
untouched** — the zeros are our own `malloc`, not a successfully painted
transparent image. Every layer's report is locally true and the composite is a
silent lie.

**No clamp.** 32,768 is not reduced to 32,767; it is refused.

## Is it ours or upstream?

Two separate things:

1. **A single image surface cannot exceed 32,767 in either dimension** on this
   backend. That is a real limit a caller must respect — and our product already
   does, by splitting into strips.
2. **LOK completes silently on a size it cannot honour.** That is an **upstream
   error-propagation defect**: `LibreOfficeKit.hxx:136-142` documents the buffer
   as being sized by `nCanvasWidth`/`nCanvasHeight` and **does not document any
   limit**.

Minimal upstream-reportable statement (submission stays on hold since
2026-08-15; this is the text for when it reopens):

> In headless LibreOfficeKit using the SVP/Cairo backend, `paintTile()` with
> either canvas dimension greater than 32767 leaves the caller-provided ARGB32
> buffer unchanged and returns through the void LOK API without setting an
> error. Cairo returns `CAIRO_STATUS_INVALID_SIZE` because `MAX_IMAGE_SIZE` is
> 32767; `SvpSalVirtualDevice::CreateSurface()` converts that to `false`, but
> `desktop/source/lib/init.cxx::doc_paintTile()` ignores the return value of
> `SetOutputSizePixelScaleOffsetAndLOKBuffer()` and continues painting on the
> error surface. A dimension of 32767 succeeds. Expected: report the
> surface-creation failure through LOK, and document the backend limit, instead
> of silently returning an unpainted buffer.

## Ruled out, and how

* **Memory / total byte count** — Cairo tests each dimension, before any pixman
  allocation. This is consistent with our own measurement: 45 MB paints at
  32,767 and 45 MB is blank at 32,768.
* **`sal_Int16` / `short` overflow** — the lineage is LOK `int` → `Size` /
  `tools::Long` → SVP `tools::Long` → Cairo `int`. No 16-bit conversion exists.
* **`tools::Rectangle::RECT_EMPTY == -32767`** — a sentinel
  (`include/tools/gen.hxx:578`), unrelated; `Size` holds `tools::Long`.
* **`SalBitmap` copy-back** — that branch is non-headless Windows only
  (`init.cxx:4307`).
* **Qt or a browser canvas limit** — LOK forces `svp`, and the refusal happens
  before anything returns to JavaScript.
* **A clamp, or a caught exception** — neither exists on this path.

## Method

Delegated to codex (source archaeology, objective answer, no build, no browser)
and then **the crux was re-read directly** before being accepted: the Cairo
constant and comment, the discarded `bool` at `init.cxx:4288`, the SVP status
return, and this build's headless config. The rule this was run under was *do
not name a layer without showing the line* — 040, 048 and 062 itself are the
precedents for what happens otherwise.

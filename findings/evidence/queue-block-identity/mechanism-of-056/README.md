# Finding 056, mechanism — the accessibility half was never built into core

Measured 2026-08-17, the same day the second v3 link shipped. Artifact under
test: `probe.wasm` `d538ce0b91478426985f22207fff416c70ee6e0a5341bb349d09bca09646b6c7`
(hash re-verified before these readings), core build
`wasm-lite/build-headless-probe`, control build `build-native-26-8` — the same
core source commit for both.

The measurement that raised this is in [`../after-link-2-d538ce0b/`](../after-link-2-d538ce0b/):
the engine reported `enabled: true, unavailable: "", paragraphFresh: true` and
`changeCount: 0` — accessibility on, no callback ever, every paragraph the hash
of an empty string. That finding deliberately declined to name a mechanism.
This directory names it, from compiled objects and shipped symbols rather than
from reasoning about where a listener attaches.

## The chain

| # | where | what happens |
|---|---|---|
| 1 | `autogen.input` | `--with-wasm-module=writer` |
| 2 | `configure.ac:4371-4388` | Emscripten sets the strip TRUE; only `calc` and `impress` clear it — `writer` does not |
| 3 | `config_host/config_wasm_strip.h:5` | `ENABLE_WASM_STRIP_ACCESSIBILITY 1` (native: `0`) |
| 4 | `sw/Library_sw.mk:108-137` | 27 objects excluded, 26 of them in `sw/source/core/access/` |
| 5 | `sw/source/uibase/docvw/edtwin.cxx:6532-6542` | `SwEditWin::CreateAccessible()` returns `{}` |
| 6 | `vcl/source/window/accessibility.cxx:78-81` | `Window::GetAccessible()` is therefore empty |
| 7 | `sfx2/source/view/viewsh.cxx:3489-3493` | `SetLOKAccessibilityState()` returns at `if (!xAccessible.is())` — `attachRecursive()` is never called |

## The readings

Full raw output in [`measurements.txt`](measurements.txt).

**Objects compiled**, same source commit:

| `sw/source/core/access/` | count |
|---|---|
| wasm | **2** |
| native | **28** |

The two survivors are `AccessibilityCheck.o` and `AccessibilityIssue.o` — the
document accessibility *checker*, a different feature that shares the directory.
The difference of 26 is exactly the set excluded at `sw/Library_sw.mk:108`.

**Symbols in the shipped artifact** — not the build tree, the binary that
produced the measurement:

| symbol | hits |
|---|---|
| `SwAccessibleMap`, `SwAccessibleDocument`, `SwAccessibleParagraph` | **0** |
| `accmap.cxx`, `accpara.cxx` | **0** |
| `LOKDocumentFocusListener` | **45** |
| `LOK_CALLBACK_A11Y_FOCUS_CHANGED` | present |

The half that would *report* a paragraph is in the binary. The half that would
*produce* one is not. The listener is alive with nothing to attach to — a
sharper statement than "accessibility is off", and it is why the request
succeeded and the data never came.

## Why it failed silently

LOK's `setAccessibilityState()` returns **`void`**, and the `!xAccessible.is()`
path records nothing. So the engine's `enabled: true` / `unavailable: ""` only
ever meant *this call did not throw*. It never had a way to mean *core accepted
it*. The observability added by the second link asked the right question of the
wrong side of the boundary.

## Two hypotheses this killed

* **`DISABLE_GUI`.** It differs between the two builds (wasm TRUE, native
  empty), and the native control ran `SAL_USE_VCLPLUGIN=svp`, so it looked like
  the difference. There is no `DISABLE_GUI` gate anywhere on this path in
  `sfx2` or `sw`. It is a real difference that is not this one.
* **Listener attachment timing.** Named as the suspect in
  [`../after-link-2-d538ce0b/`](../after-link-2-d538ce0b/) and already refuted
  there by a native control. The listener code is present and correct; it is
  never reached.

Both were shape-matching. What settled it was counting compiled objects and
counting symbols in the shipped binary.

## Not established here

* **That fixing the build makes block identity work.** It buys a test, not a
  feature. Adversarial review (codex, 2026-08-17) enumerated further
  independent runtime conditions past `attachRecursive`: a 100-child recursion
  limit, a `MANAGES_DESCENDANTS` workaround that only runs for 1–9 children,
  focus callbacks that fire only when paragraph *text* changes, an
  `A11Y_FOCUS_CHANGED` filter during tiled painting, and
  `doc_getA11yFocusedParagraph` reading `SfxViewShell::Current()` rather than
  the view id passed to `setAccessibilityState`. None of these has been
  exercised, because nothing gets that far in this build.
* **That adding `calc` back to `--with-wasm-module` is the fix.** It is not —
  see finding 057. That was this investigation's own wrong answer, caught in
  adversarial review.
* **Anything about a build with the strip disabled.** No such build exists here.

## The guard left behind

`wasm_sdk_probe/tools/check_core_build_provides.py` asks whether the **core**
build provides the capability the product claims — the layer below
`check_product_build_reaches.py`, which passed while the mechanism was dead.

It requires *both* switches (see finding 057: they answer to different configure
inputs, so consulting one alone nods at a build that cannot work). Its positive
control is `build-native-26-8` — a real build that really passes, not a mutation
we invented. Self-test 5/5 ([`check-self-test.txt`](check-self-test.txt));
reports in [`core-build-capability-wasm.json`](core-build-capability-wasm.json)
(exit 1, red) and
[`core-build-capability-native.json`](core-build-capability-native.json)
(exit 0, green).

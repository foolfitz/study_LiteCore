# Prediction for a11y gate 0 — written 2026-08-21, before the rebuild

Roadmap §3.3's gate asks **one** question:

> **Does LOK emit a focused paragraph on WASM?**

Everything below is fixed **before** the patch is applied and before the core is
rebuilt. This matters more here than usual: the reason a11y was pulled forward
to before M2a is that this question has **never been measured**. Finding 056
proved it does not work *today*; it did not prove it cannot work *after the
configuration is fixed*. A threshold written after seeing the output would turn
the highest-uncertainty question in the roadmap into a formality.

## What is already known, and is not under test

* `SwEditWin::CreateAccessible()` returns `{}` whenever the C++ macro is set
  (`sw/source/uibase/docvw/edtwin.cxx:6532-6542`) — read, not inferred.
* On 26.8's Emscripten no flag combination clears that macro (finding 057).
* `setAccessibilityState()` returns `void` and does nothing when there is no
  accessible object, so the engine's `enabled: true` only ever meant *"this call
  did not throw"* (`queue-engine-must-report-core-lacks-accessibility`).

So a build without the patch **cannot** pass this gate, and running the probe
against one measures nothing. **The probe refuses to run on a build whose
`config_wasm_strip.h` still sets the macro** — that refusal is a feature.

## G0-1 — the build actually changed (precondition, not the gate)

After the patch and rebuild, `config_wasm_strip.h` has
`ENABLE_WASM_STRIP_ACCESSIBILITY` **0 or undefined**.

*If it is still 1*, the patch did not take and **nothing below is evidence**.
Check this before waiting for the full build.

## G0-2 — the gate itself

With accessibility enabled on the LOK view, moving the caret into a paragraph
produces a callback that **names the focused paragraph**, and the name it
carries **changes when the caret moves to a different paragraph**.

Both halves are required, and the second is the one that does the work:

* a callback that fires but reports the same thing for every paragraph is
  **not** a focused paragraph, it is an event;
* a single reading cannot tell those apart. **Three paragraphs, three distinct
  readings.** That is the positive control, and it is here because three checks
  on 2026-08-21 passed or abstained for want of exactly this.

**PASS** = ≥ 2 distinct paragraph identities across 3 caret placements, each
matching the paragraph actually targeted.

**FAIL** = no callback, or a callback carrying nothing paragraph-shaped, or the
same reading for all three.

## G0-3 — what a FAIL means, decided now

Roadmap §3.3: **stop.** Do not start on the shell half (§3.4's ARIA projection,
currently zero lines). Report the result to M3's product positioning, because
"a11y cannot work on this platform" is a product-level fact, not a task status.

**This is written down now so that a FAIL cannot be re-read later as "needs more
investigation".** If it fails, the next move is a decision, not another probe.

## G0-4 — what a PASS does NOT license

A PASS answers **only** the core half. It says nothing about:

* the ARIA projection (§3.4) — screen readers cannot read a canvas, and that
  path is currently zero lines;
* `queue-engine-must-report-core-lacks-accessibility` — the engine's honesty
  fix is owed either way, and a PASS makes it *more* urgent, not less, because
  then `enabled: true` starts being load-bearing;
* **block identity.** Roadmap §9 is explicit: a11y coming forward does **not**
  pull block identity with it. They share a data source; this gate asks only
  about the focused paragraph.

## G0-5 — the size number, recorded but not judged

Record the artifact size before and after. `sw/source/core/access/` is 53 files.
**No threshold is set** and none should be invented after the fact: roadmap §3.2
rates size as the *weak* reason for this ordering, and M2a is where size gets
judged, against R10's six lines of evidence.

Recording it here is so M2a starts from a measurement instead of a memory.

## Traps this run must avoid

* **Do not rebuild between the measurement and the verdict**
  (`wasm-build-not-reproducible`). Archive the current profile first.
* **Do not name a layer without measuring it** (040, 048, 062). If the callback
  is absent, "core does not support it" is one hypothesis; "our engine never
  enabled it", "the worker does not forward it", and "the callback id is not in
  the allowlist" are others. The worker allowlist has bitten this tree twice in
  one afternoon — **check that the callback is forwarded before concluding
  anything about core.**
* **An engine field nobody forwards does not exist.** Same rule, stated the way
  it was learned.

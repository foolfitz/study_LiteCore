# Finding 045 native probe — predictions, written before the probe ran

Written 2026-08-15, **before** `tools/f045_native_inline_format_arguments.cpp`
existed. Nothing below was edited after the first run; corrections go in a dated
section at the bottom, struck through rather than rewritten.

## What this probe is for

Two questions, and the second one is owed by finding 045 itself.

1. **Does sending the parameter make these four commands setters?** The engine
   dispatches `.uno:Bold` with empty arguments today, and core's slot is declared
   `Toggle = TRUE`. The proposed fix — the same shape finding 030 used for the two
   list commands — is to send the value. That has to be measured natively before it
   is written into a relink, because a relink in this repo costs an E2-B re-run plus
   a full E2-C round.
2. **Does a bare dispatch actually toggle?** Finding 045's own exclusion table says
   this is *not yet measured*: the WASM round put its two markers next to each
   other, and text inserted beside a bold run inherits it, so that observation could
   not separate "the toggle did not turn it off" from "the new text inherited the
   formatting". This probe uses **two anchors in different paragraphs**.

Native rather than WASM because a negative result on the WASM build alone cannot
tell "core does not accept this argument form" apart from "our build does not send
it properly". Nothing here describes the WASM artifact.

## The derivation being tested

Read out of the core tree at `671c848b`, not guessed:

* `sfx2/source/appl/appuno.cxx:206-219` (`TransformParameters`): for a property
  slot, a **single argument whose name equals the slot's UNO name** is handed to
  `pItem->PutValue(value, 0)`.
* MemberId 0 is the boolean accessor for all four items — `MID_BOLD`, `MID_ITALIC`,
  `MID_TEXTLINED`, `MID_CROSSED_OUT` are all `0`
  (`include/editeng/memberids.h:108-124`) — and each `PutValue` case 0 is
  `SetBoolValue(Any2Bool(rVal))` (`editeng/source/items/textitem.cxx`).
* `sfx2/source/control/unoctitm.cxx:713-717`: with a **non-empty** argument set the
  slot is executed directly with the item. The **empty** set takes the other branch
  at `:733-737`, whose comment reads "execute using bindings, **enables support for
  toggle**/enum etc." — that is the branch we are on today.

So the predicted argument strings are:

```
.uno:Bold        {"Bold":{"type":"boolean","value":<bool>}}
.uno:Italic      {"Italic":{"type":"boolean","value":<bool>}}
.uno:Underline   {"Underline":{"type":"boolean","value":<bool>}}
.uno:Strikeout   {"Strikeout":{"type":"boolean","value":<bool>}}
```

## Predictions

Each arm loads a **fresh document**. Markers are committed at a collapsed caret via
`.uno:InsertText`; where an arm uses two positions they are in **different
paragraphs**, so neither marker can inherit the other's formatting. Every arm saves
an ODT and the judging is done offline on the saved bytes.

| # | arm | prediction | confidence |
|---|---|---|---|
| P1 | `param-off` on plain text | marker is **NOT** formatted | **high** — this is the whole derivation |
| P2 | `param-on` on plain text | marker **IS** formatted | high |
| P3 | `bare` on plain text | marker **IS** formatted (toggle from off) | high — already measured in WASM |
| P4 | `bare-twice`, two non-adjacent anchors | first marker formatted, **second NOT** | **medium** — this is the toggle claim 045 could not make; it fails if the attribute is per-position rather than a shell-wide toggle |
| P5 | `param-off-then-on`, two non-adjacent anchors | first NOT formatted, second formatted | medium-high |
| P6 | `param-on` **on a range** (not a caret) | the selected text itself becomes formatted, and `<office:body>` changes | high |
| P7 | `param-off` on a range whose text is already formatted | the selected text loses the property | **medium** — the direction that matters for the product, and the one nobody has measured |

Predicted overall: **P1 holds** and the fix is the one-line-per-case change
finding 045 describes.

### What would refute the design

* **P1 fails** (parameter sent, marker still formatted): `TransformParameters` is not
  taking the branch derived above, or the item's `PutValue` is not reached. The fix
  as designed is wrong and the relink queue changes shape. This is the outcome worth
  an afternoon to rule out.
* **P6 or P7 fails** while P1 holds: the parameter works at a caret but not on a
  selection, which would be a narrower fix and a narrower contract than intended.
* **P4 fails**: the "bare dispatch toggles" claim is wrong as stated, and finding
  045's mechanism section needs its wording corrected even though its headline
  (`enabled: false` produces formatted text) is already measured twice.

### What this probe deliberately does not answer

* Whether the WASM build behaves the same. That is a separate run on a relinked
  artifact, and it is the reason the relink has to happen before E2-C round 2.
* Whether the typing attribute survives a caret move. Not needed for the fix
  decision.
* Anything about `d1-body-collapsed`. Different question, different probe.

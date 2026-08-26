# Result: finding 063's four properties hold, and the check can be made to fail

Measured 2026-08-26 on the shipped `e2-editor-v8`, chrome, answering
[`PREDICTION.md`](PREDICTION.md), which was written 2026-08-22 **before the arm
had ever been run** and left the queue item open for exactly that reason.

The route was built the day it was predicted; nobody had driven it. Two runs,
one each way, both against `dist/` with `probe.wasm` byte-identical — the only
change is one manifest field in a symlink mirror.

## The refusal arm: all four properties, on the same run

`--refusal-diagnostic` narrows `delete-selection` to `gestures: []` (present and
empty, never removed — deleting it would ship it wide open), so `offers()` reads
it as withheld and the page's cut handler falls back to `delete-backward`,
exactly as it did on v3. The engine then refuses it on the range a cut
necessarily has.

```json
{ "induced": true, "withheldAction": "delete-selection",
  "refusalReported": true,
  "toasts": ["剪下：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged",
             "已存出 11.9 KB"],
  "documentUnchanged": true, "stateAfterCut": "ready",
  "saveStillWorks": true, "handled": true }
```

| the prediction's criterion | measured |
|---|---|
| 1. a toast names the reason (`EDITOR_FORMAT_GESTURE_UNSUPPORTED`) | **held** |
| 2. the saved ODT's lines are what they were | **held** |
| 3. `stateAfterCut == "ready"` | **held** |
| 4. the save after the refusal produced a readable ODT | **held** |

`a-refused-action-is-reported-and-changes-nothing`: **PASS**. The run as a whole
was 38 PASS / 2 NOT_ESTABLISHED, `ok: true`, and the second abstention is
`cut-removes-the-selected-text` — correct, and predicted: this arm withholds the
delete, so there is nothing for that check to score either way.

## And it goes red for its own reason

`--refusal-diagnostic --mutate cut-swallows-the-refusal` puts finding 063's
discard back where it was — inside the operation, where `run()` cannot see the
rejection, so no toast is emitted:

```json
{ "induced": true, "refusalReported": false,
  "toasts": ["已剪下 U+0045,U+0031,U+002D,U+004C,U+0043,U+002D,U+0042 字",
             "已存出 11.9 KB"],
  "documentUnchanged": true, "stateAfterCut": "ready", "saveStillWorks": true }
```

`a-refused-action-is-reported-and-changes-nothing`: **FAIL**, and it fails on
the term the mutation moves — `refusalReported` — while the other three stay
true. The product **said it had cut** (`已剪下 …`) over an action that removed
nothing. That is finding 063's user-facing shape, reproduced on demand.

`cut-removes-the-selected-text` stayed `NOT_ESTABLISHED` under the mutation,
as predicted, and no other check moved.

## What this does not establish

* Anything about cut on the **shipped** manifest. Both runs are diagnostics and
  both stamp `refusalDiagnostic.evidenceClass: "diagnostic"`; the shipped
  manifest grants `delete-selection` both range bits and the cut succeeds
  (`cut-removes-the-selected-text`, measured separately).
* The clipboard half on Firefox. `clipboardGranted` is a Chrome-only CDP grant;
  without it the copy is denied by the driver, the delete never runs, and the
  check abstains rather than judging the product.

## The positive control needed no extra driving

The term at risk was `documentUnchanged`: "nothing changed" and "nothing
happened" are the same observation. The control is the same drive on the same
named line (`E1-LC-BETWEEN`) with the shipped manifest —
`cut-removes-the-selected-text`, which requires that line to be **gone** and
passes on every ordinary run. One run of each says the document survived because
the action was refused, not because the drag missed.

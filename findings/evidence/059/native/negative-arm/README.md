# Finding 059 — the negative arm, and whether the cache is primed

Round of 2026-08-19, native LibreOffice core 26.8 (`build-native-26-8`,
`SAL_USE_VCLPLUGIN=svp`), the same commit the shipped WASM artifact was built
from. **Nothing here describes the WASM build.**

Produced by `tools/run_f059_native_negative_arm.sh`, scored by
`tools/analyze_f059_negative_arm.py` (self-test 10/10). Nothing was rebuilt: the
probe is a standalone program compiled against the LOK headers that loads the
existing native install at runtime.

## What was owed, and why

The 2026-08-18 round settled which predicate replaces `success == true`: the
format barrier's own postcondition, **observed state against requested state**
(`formatBarrierPostconditionMet`, `probe_engine.cpp:1189`). Ten arms showed it
agreeing nine times.

Two things were left open, and both had to be closed before the engine could
change:

1. **The predicate had never been seen to disagree.** The intended refusal arm
   (`setViewReadOnly`) did not refuse — core applied the command anyway — so
   every arm in that round was a successful action. A predicate that has only
   ever agreed is not yet a predicate.
2. **`formatBarrierPostconditionMet()` returns false for two different
   reasons**: the state is unknown, or the state is known and wrong. If nothing
   ever broadcasts the slot, every "failed" it reports is really "I don't know"
   wearing the word failed. That is finding 021's shape and it was unmeasured.

## Answer 1 — the cache is primed, at document load, for all four slots

```
"priming": {
  "slotsKnownBeforeAnyDispatch": ["bold", "italic", "strikeout", "underline"],
  "values": {"bold": false, "italic": false, "strikeout": false, "underline": false}
}
```

Core emits a **complete** state set when the document loads — the first arm's
`fromCaretMove` carries about 120 entries including all four slots — and
afterwards broadcasts only **changes**. So the slot is known from load onward
and the predicate is never guessing.

**Caret movement alone does NOT prime it.** Look at the per-arm
`fromCaretMove`: it carries `.uno:Bold=false` only when the previous arm had
left the state true. Moving the caret between two paragraphs that share a state
broadcasts nothing. The priming comes from the load, not from the gesture — and
an engine that started reading the cache after some later point, or that lost
the load broadcast, would be back in 021's shape.

**Underline and strikeout are broadcast too**, which matters because
`probe_engine.cpp:4308-4310` justifies keeping no state cache for them with

> Neither command appears in core's `GetKitUnoCommandList()`

Core's source already contradicted that (`sfx2/source/control/unoctitm.cxx:1165ff`).
This round contradicts it a second way: both slots arrive in the load
broadcast, with values. The cache for them is not impossible; nobody wrote it.

## Answer 2 — the predicate CAN say no, on two arms, and it says no exactly where the document does

Nine arms, one document, markers resolved through their own `text:style-name`:

| arm | argument | `success` | broadcast | predicate | document |
|---|---|---|---|---|---|
| control-no-command | — | — | — | not-met | not applied |
| positive-bold-true | `{"Bold":{"type":"boolean","value":true}}` | false | `.uno:Bold=true` | met | **applied** |
| **wrong-argument-type** | `{"Bold":{"type":"string","value":"true"}}` | false | — | **not-met** | **not applied** |
| wrong-argument-name | `{"Bald":{...}}` | **true** | `.uno:Bold=true` | met | applied |
| bare-no-argument | (none) | **true** | `.uno:Bold=true` | met | applied |
| readonly-control | boolean true, view read-only | false | `.uno:Bold=true` | met | applied |
| **protected-section** | boolean true, inside `text:protected` | false | — | **not-met** | **not typed** |
| after-the-section | boolean true | false | `.uno:Bold=true` | met | applied |
| positive-bold-true-2 | boolean true | false | `.uno:Bold=true` | met | applied |

**Zero disagreements.** The predicate said not-met on both arms where the
document did not reach the requested state, and met on all seven where it did.

Two negatives rather than one on purpose: finding 037's lesson is that a guard
you expect to decline may decline for another reason or not at all, and 059's
own first refusal arm did not refuse. Asking several ways and reporting which
actually refused is the difference between measuring and assuming.

* **wrong-argument-type** — core knows `.uno:Bold`, cannot convert a string to
  the boolean the slot wants, and leaves the text normal. The marker comes back
  in a run carrying an explicit `fo:font-weight="normal"`.
* **protected-section** — the caret CAN enter the section (the arm records
  `.uno:StateTableCell=read-only : F059NegProtected` and a wave of `disabled`
  broadcasts), the dispatch is refused, and the marker is never typed at all.
  Reported as `not-typed` rather than as unstyled: "nothing was typed" and
  "text was typed and left normal" are different observations and collapsing
  them would hide a probe that had stopped typing.
* **readonly-control** — kept, and it still does not refuse. `setViewReadOnly`
  reports `success:false` and the text becomes bold anyway. The 2026-08-18
  reading of that arm stands.

## The one that inverts the field the engine currently gates on

`success: true` appears on exactly **two** arms — `wrong-argument-name` and
`bare-no-argument` — and both are arms where core **ignored the argument and
toggled**. Every arm where core honoured the parameterised form reports
`success: false`.

So on this build the field `commandResultSucceeded()` gates on
(`probe_engine.cpp:1696`) is not merely unhelpful: it is **anti-correlated**
with the caller's request being honoured. Reporting success is what core does
when it did not read your argument.

## Files

* `arms.jsonl` — the probe's raw output, one line per arm, every state change
  the round saw
* `negative-arms.odt` — the document the round produced; the oracle
* `verdict.json` — the scored report

## What this round does NOT establish

* **Anything about the WASM build.** Findings 040 and 048 are what that rule is
  for. The WASM half of the predicate change needs its own measurement.
* **That these two refusals are the only shapes core refuses in.** They are two
  that it does; there may be others, and a third would not change the verdict.
* **That the load broadcast survives everything the engine does to a session.**
  What is measured is that it happens at load. An engine that re-creates a view,
  or that starts listening later, could still be reading an empty cache — and
  the split between `unknown` and `not-met` in the analyzer exists so that case
  is visible rather than silent.

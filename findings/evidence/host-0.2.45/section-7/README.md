# Spec v29 section 7 on the installed 0.2.45 (2026-11-01)

Shakedowns through the adapter. The runners' page pin is 0.2.44's until the next K spec re-pins it, so these read cells, not the top-level `page` problem.

| item | result | evidence |
|---|---|---|
| P arm, 3 rounds | 6/6 | `production_ui_p.stdout.txt`, `production-ui-p.json` |
| `as5`, 3 x both browsers | 6/6, no letter lost | `autosave_as5.stdout.txt`, `m3-autosave/shakedown/2026-11-01T142400+0000.json` |
| `as5-held`, 3 x both browsers | 6/6 | same. `held key lost letters in 3/3` is that arm's premise: it asserts the toast when keys are lost, and goes NE if none is |
| same-second R3 at phase 0.60 | 0/6, `premise` | `same_second_r3.*`, `m3-same-second/shakedown/2026-11-01T144052+0000.json` |

**`as5`.** On v28 it lost one letter of twenty on both stacks (ddev first contact, own stack ST2). Finding 177 called that a second symptom of the same cause, by inference. On v29 it does not reproduce, 6 of 6. The inference now has its measurement.

**R3 at 0.60 is not a product result.** `premise`: X did not land in S1's second, so those runs measured nothing about 103 (S2 got 412, which is the safe outcome). On v29 S1 settles +0.345 to +0.397 s after the press, X adds 0.365 to 0.465 s, the whole takes at most 0.847 s; from phase .60 that crosses the second every time. Spec section 7 item 5 expected this.

## Prediction, committed before its run

`FOREIGN_PHASE` back to **0.05**: S1 settles near .40, X is done by .90, so both land in one second with about 0.10 s to spare. 0.05 is also the value that fitted v21, where S1 settled at 0.30 s.

Prediction: R3 at 0.05 on 0.2.45, 3 x both browsers: **6/6, `premise` holds, no red clause.** If any run is red on `premise`, the phase is wrong; if red on any other clause, that is a product result and gets a finding. The clause is not edited either way.

## Result

**The prediction held.** `check_m3_same_second.py` at `FOREIGN_PHASE = 0.05`, R3, 3 x both browsers on 0.2.45: 6/6, every run `red clauses: []` (`same_second_r3_phase05.*`, `m3-same-second/shakedown/2026-11-01T144413+0000.json`). Exit 1 is the page pin alone. The `premise` clause was not edited.

S2's outcome on the 0.60 runs (412) and the 0.05 runs (blocked with `changed`, no PUT) are both safe; only the second measures 103.

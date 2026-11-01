# Why one F3 cell moved on generation 83 (2026-11-01)

F3-83 run-01: Firefox `clear-format-removes-every-inline-format` PASS -> NOT_ESTABLISHED, everything else equal. Spec append 2: any move, stop and look. `repro.py` runs all twelve arms of the runner's `format_arm` in F3's order, with the same evaluate strings, and logs every format value and action the page exchanges with the worker.

## The mechanism, read from the logs

`#clear-format` runs four actions in a row, `await run("清除格式", ...)` each (`e2-editor-app.js:2324`), and `run()` writes the status strip after each one. The runner waits for that label, so its wait is satisfied by the FIRST of the four. It then presses the next button into the middle of the page's own loop. On `natural-v28-firefox` MKSTRON6:

```
423247.9 set-bold false            clear, step 1
423397.1 set-italic false          clear, step 2
423542.2 set-underline false       clear, step 3
423665.0 set-strikethrough true    the runner's press
423714.3 set-strikethrough false   clear, step 4 undoes it
```

Step 4 also overwrites the label, so the runner then sits out its 30 s wait. `natural-v29-firefox` MKSTRON2 shows the same thing at a different step.

## It is not new on v29

| run | arms | bad | v29 | v28 |
|---|---|---|---|---|
| Firefox, natural | 120 each | v29 2, v28 8 | 2 | 8 |
| Chrome, natural | 120 each | v29 0, v28 4 | 0 | 4 |
| Firefox, poll forced into the loop (`CLEAR_MS=1`) | 120 each | v29 0, v28 8 | 0 | 8 |

v28's bad arms come in pairs, each stall followed by the next arm starting from the wrong state, and only in later loops, where a longer document makes each repaint, and so the loop, longer: about 470 ms on v28 against about 20 ms on v29. `FAST_MS=30` forces the press path on v29 and gave 1 bad arm in 36, same shape. So v29 narrows the window; its 3 ms first step only moves where the runner lands in it.

A person cannot hit a 20 ms window. On v28 a long document gave half a second, in which a format press could be undone by the clear. That is a small existing product property, and v29 improves it. It is registered here, not fixed.

## What is not explained

F3-83 run-01's own shape was `formatCacheBefore: 'true'` on the italic arm, so the toggle asked for OFF. Across all six logs, 720 arms, no format turned on without a request asking for it; the single "unexplained" entry per Firefox run is the caret placed on the bold heading at open. So that exact shape did not repeat, and its link to this race is an inference from its neighbour (`formatPressWaitedMs` 3 in the arm before), not a measurement. The other project's `cc1plus` was running on the machine around that hour.

`../../f3-83/` re-runs F3 on the final page, Firefox three times, because one run is not a measurement.

## For the next K spec

`read_k_0244_product_path.py` wants all 46 cells equal, so this race can turn K7 red with no product cause. The derived F3 runner can wait for the clear's toast, written once after step 4, instead of the label (its REPLACEMENTS list, the bound runner not edited). Not done here: it needs its witness (section 34), and this batch does not change a check to reach green.

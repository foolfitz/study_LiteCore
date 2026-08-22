# The caret after a text commit: seven runs, read from the state, not the pixels

Arm `caret-state-after-commit`
(`wasm_sdk_probe/tools/probe_064_format_reaches_typing.py`), Chrome,
2026-08-22, against the shipped `e2-editor-v3` artifact `29ec627b…` through a
mirrored page. `evidenceClass: "diagnostic"`.

## Why this arm exists

Five earlier attempts measured the caret in PIXELS and could say *what*
happened but never *why*, because `paint()` has four ways to draw nothing and
all four look identical on a canvas: no cached tiles, no editorState or
document, no `caret` in the state, or `selection.collapsed === false` (which
suppresses the caret on purpose so a range highlight never gets one painted
inside it).

So this arm asks the page instead of the canvas. Every state update records
what the snapshot held; every `paint()` records which of the four branches it
took; both are labelled with the step that caused them.

## Result: 2 PASS / 7

| runs | `sourceSequence` across the commit | caret `x` |
|---|---|---|
| 5 (FAIL) | 3 → **5** | unchanged |
| 2 (PASS) | 3 → **6** | updates |

`paint()` reported `drew-caret` in **every** run. The page is not declining to
draw. What differs is the rectangle it is given.

Representative failing run (`f068-rep2.json`):

```
click    x   = [1418, 1418, 1418, 1598, 1598]   src = [1, 1, 1, 3, 3]
commit   x   = [1598, 1598, 1598, 1598, 1598]   src = [3, 3, 3, 5, 5]
move     x   = [1598, 1598, 1598, 2984, 2984]
```

Representative passing run (`f068-rep5.json`):

```
commit   x   = [1598, 1598, 1598, 3131, 3131]   src = [3, 3, 3, 6, 6]
```

`sourceSequence` counts every editor callback that changed state. The commit
window advances it by **two** when the caret stays put and by **three** when
the caret follows the text. The third callback is the one carrying the new
cursor rectangle, and it is missing five times in seven.

When it is missing, the caret is drawn at the **pre-commit** rectangle — i.e.
one whole run of typed characters behind where the text now ends. Type one
character and the caret sits in front of it. That is the operator's original
description, word for word, and it is now reproduced from the state rather
than argued from a screenshot.

## Two positive controls, both required

1. **Drawing.** Some `paint()` must report `drew-caret` after the move, or the
   instrument never saw the page draw a caret and its silence elsewhere means
   nothing.
2. **Staleness.** The caret `x` must change on the move, or the arm cannot
   detect an `x` that fails to change, and "it did not move after the commit"
   is unfalsifiable.

Both hold in all seven runs. The arm returns `NOT_ESTABLISHED`, not `FAIL`,
if either fails.

## What one run would have said, and why the count is the result

Run 1 of this arm failed and run 2 passed — same arm, same page, opposite
outcomes. Either one alone would have supported a confident and wrong claim:
"the caret is never updated" or "the caret follows typed text". The defect is
**intermittent**, so the number of runs is not a robustness detail here, it is
the measurement.

## What is NOT established

- **Why the third callback goes missing.** LOK's `paste()` is what commits the
  text (finding 067 measured `method: "paste"`), and this arm cannot see LOK's
  side of the boundary — only that the engine's state did not change. Whether
  paste emits the cursor callback unreliably, or emits it and the payload fails
  to parse, is unmeasured. The engine already distinguishes those: a callback
  in the cursor range whose payload does not parse emits
  `editor-callback-parse-error` (`probe_engine.cpp:2316`). Nobody has looked
  for that event during a commit; that is the next measurement and it needs no
  link.
- **Reconciliation with the pixel arm**, which found *no* caret-height run on
  that line after typing rather than one at the stale position. A caret drawn
  at the pre-commit rectangle should still leave a run somewhere on the line.
  Not forced into agreement here: this arm reads the state directly and is the
  stronger instrument, and the discrepancy stays named.

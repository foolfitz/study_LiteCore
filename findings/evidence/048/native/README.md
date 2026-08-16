# Finding 048, native arm — the click is not slow in core

Produced 2026-08-16 by `tools/run_f048_native.sh` against
`build-native-26-8/instdir`, core commit `671c848b…` — **the same commit the
`e2-editor-v2` WASM profile was built from**, so the comparison has one
variable.  The analyzer checks that commit rather than trusting this sentence.

**Nothing here describes the WASM artifact.**  Same rule as finding 016 and
finding 045: a native run cannot say what the browser build does, only what core
does when nothing else is in the way.

Predictions were registered in `PREDICTION.md` before the probe was written.
The judging is offline in `tools/analyze_f048_native.py`, whose self-test is
9/9 (every predicate that can turn the verdict was shown to move).

## The numbers

Three executions, five arms, five repetitions each (N1 is one by construction —
there is one first click per process).  All times in milliseconds, from the
`post*` call to the callback, medians:

| arm | what it is | first callback | cursor rectangle | samples |
|---|---|---|---|---|
| N1 `click-cold` | first click after load and paint | 0.6 / 0.6 / 0.6 | 0.7 / 0.6 / 0.6 | 1 of 1 each |
| N2 `click-warm` | a later click, alternating between two lines | 0.6 / 0.5 / 0.6 | **0.6 / 0.5 / 0.6** | 5 of 5 each |
| N3 `click-same` | click where the caret already is | — | — | **0 callbacks, all 15 repetitions** |
| N4 `uno-godown` | `.uno:GoDown` / `.uno:GoUp` | — | — | **not measured** (see below) |
| N5 `set-text-selection` | `setTextSelection(RESET)` at the same point | 0.5 / 0.6 / 0.5 | 0.6 / 0.5 / 0.5 | 5 of 5 each |

The browser numbers this is next to: **22–28 ms (Chrome), 23–33 ms (Firefox)**,
polled at 5 ms on the same fixture, same core commit.

## Predictions, scored as registered

| | prediction | three runs |
|---|---|---|
| P-N1 | `N1.firstCallbackMs` median < 5 ms | **HELD** (0.6 each) |
| P-N2 | cursor rectangle is not later than the click's other signals (< 2 ms apart) | **HELD** (0.1 / 0.0 / 0.0) |
| P-N3 | a click where the caret already is produces zero callbacks | **HELD** (0 in all 15) |
| P-N4 | `.uno:GoDown` latency within 2× of the click's | **NOT_MEASURED** — the command emitted no cursor rectangle at all on this fixture |
| P-N5 | `setTextSelection` no slower than the click | **HELD / FAILED / HELD** — run-2 missed by 0.1 ms.  Recorded as failed because that is how it was written; the magnitude is noise, and saying so afterwards is not the same as having predicted it |

## What this decides

**Hypothesis B is out.**  P-N2 holds in all three runs: the cursor rectangle
arrives with the click's other callbacks, not after them.  Nothing here supports
"core moves the caret promptly and the callback lags".

**Hypothesis A is out in core.**  A click is acknowledged in **0.6 ms**
natively.  The browser's 22–28 ms is roughly forty times that, on the same core
commit and the same document.

**What it does not decide.**  Per `PREDICTION.md` addendum A2, registered while
both attempts still held zero arm data: this rules core's click handling out; it
does not elect a culprit.  Finding 040 is the precedent for why — clean
natively, broken on WASM, and still upstream, because the defect was in the
Emscripten build's scheduler integration.  Separating our transport and worker
scheduling from that integration is a further measurement, and until it is made
**neither may be named as the cause**.

## Two things measured on the way that are worth keeping

**`.uno:GoDown` announces nothing on `list-contexts.odt`.**  `attempt-02` ran
the cursor-command walk on the fixture D3 measured 22–28 ms on: 186 callbacks,
177 of them `STATE_CHANGED`, exactly one
`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` — and that one from the load.  The same
walk on `styled-list.odt`, same probe binary and install, produced 23.  Clicks
on the silent fixture are not silent (N1/N2 above), so this is specific to the
cursor commands, not to the document's ability to report a caret.  **Whether the
caret moved at all was not measured** and is not claimed here.  Anything that
waits for a cursor rectangle after a cursor command would wait forever on this
document; nothing in the product does that today.

**The product's 400 ms quiet rule now rests on a measurement.**  `placeCaret`
accepts a caret already on the clicked line after 400 ms of silence, on the
grounds that a click at the same place gives the engine nothing to say.  N3
measured exactly that: **zero callbacks in 15 repetitions**.

## The directory

| | |
|---|---|
| `run-1/`, `run-2/`, `run-3/` | the three executions.  `arms.jsonl` is the raw record, `context.json` carries the core commit and fixture hash |
| `summary.json` | the offline judgement over all three |
| `attempt-01-aborted-userinstall/` | died in LO's userinstall before measuring anything: a relative `OUTPUT_DIR` makes `file://../…`.  The runner absolutises it now |
| `attempt-02-godown-silent/` | reached the walk and found the silent cursor commands.  Kept because that is the evidence for the paragraph above |

The core worktree carries the build-system patches inventoried in
`wasm-lite/patches/INVENTORY.md`; `context.json` records the modified-file count
rather than asserting a clean tree.

# Section 9 reader: v25 differs from v24's link only inside `OXSDK_E2_V25_FORMAT_PROOF`

Spec v25 section 14 owed this before any K: a tool-closed reader (CLAUDE.md section 1, form 2) for the condition the owner's carry-over ("沿用") rests on. Tool: `wasm_sdk_probe/tools/check_v25_ships_confined.py` (new). Run 2026-10-29 ~15:33 +0800 on the tree after `9450e5340` (em++ `-E` only, `taskset -c 0`; 12 cores, load 0.8, no `make`; F1 browser runs in progress, not timing runs).

## What the ships report could not see

`what_the_link_ships.py` copies only the old `.cpp` into its scratch dir (`source_at`), so on the old side `#include "ordered_format.inc"` resolves through `-Isrc` to the **live** file. Both sides read the same new `.inc`/`.h`; a change inside one is invisible. `../pre-link/ships.stdout.txt` lists two probe_engine hunks (barrier fields, `dispatched` serialisation), both in `probe_engine.cpp`. Spec v25 13 item 3 read it as "exactly the four declared places (fields, serialisation, stage, witness)"; stage (`ordered_format.inc`) and witness (`ordered_engine_reply.inc`) were not in it. That sentence of 13.3 over-read the report; section 14's owner decision cited the same report. The reader below re-derives the difference with each side's includes at its own commit (`git archive`, V0-v25's method) and closes the gap. The blind spot covers every sibling header or `.inc` a unit includes, so it is in the tool itself, not only in v25's use of it. Not fixed here: other batches' records cite the tool's output, and which of their claims rested on a sibling file is a separate item.

## Live result (`live.json`, exit 0): **CONFINED_V25_HOLDS**

Makefile compile lines (`make -n -B`) for the four product sources:

- **C** (v24's line = v25's line without `-DOXSDK_E2_V25_FORMAT_PROOF`, object path aside): true for all four.
- **B** (v24's line on the tree = on `git archive 1f95a9fca`, nonblank right-stripped `-E -P`): true for all four.
- **A** (v25 line vs the same line without the define, `-E` with line markers, every differing line mapped to file:line and required inside a branch governed by the macro): `probe_engine` **39** differing lines, **0 outside**; the other three units 0. By file: `probe_engine.cpp` 7, `ordered_engine_reply.inc` 29, `ordered_format.inc` 3. They are exactly spec v25 4.1: the two barrier fields, the `dispatched` serialisation (one `failureShape` line replaced by four), `deferOrderedFormatReply` recording `dispatched`, `stage = AwaitingResult` before the dispatch, the two witness helpers, the witness gate replacing `inlineFormatArgumentResolved` in the ordered reply, and the `witness` field.
- `notVisibleToShips`: 32 of the 39 lines (the two `.inc` files).
- Sanity of the input: the v25 probe_engine `-E` is 5,981,098 bytes, 86,110 nonblank lines from 967 files (0.25 s; em++ `-E` is fast).

## Red cases (`reds/`), each red on its own clause only

| Case | Input | Result |
| --- | --- | --- |
| leak | `reds/leak-src.patch`: a function-like macro defined inside a V25 branch, invoked outside it (empty under v24) | `CONFINED_V25_RED`: `probe_engine.cpp:8513 (+) 'static const int kV25RedCaseLeak = 1;'` outside; B, C true |
| baseline | `reds/baseline-src.patch`: V0-v25's positive-control token, unconditional | `CONFINED_V25_RED`: `v24's line on --src differs from 1f95a9fca`; A 39 lines, 0 outside |
| zero | `--src` = `git archive 1f95a9fca wasm_sdk_probe/src` (no V25 code) | `CONFINED_V25_RED`: `A found zero differing lines: nothing was judged` |
| ships-zero | `reds/ships-zero-input.json` (`changed: {}`) | `CONFINED_V25_RED`: `the ships report lists zero changed hunks`; A 39, 0 outside |

Named limits: a branch counts as governed only when its own or an enclosing condition names the macro literally, so a branch governed by a macro derived from it is outside (conservative: that is the leak case, red). A differing line in a file outside `--src` (a system header) is outside by construction.

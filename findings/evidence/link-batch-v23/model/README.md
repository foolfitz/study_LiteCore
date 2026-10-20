# The model in two modes (SPEC-M3-ordered-commands §8), 2026-10-20

`wasm_sdk_probe/tests/extend_completion_model_test.cpp` (sha256 `6201a62d…`) was built with `g++ -std=c++17 -O2 -I wasm_sdk_probe/src` (with `-Wall -Wextra`: no warnings). It was run once, which took 24 s and exited 0, ending `ok`. The full output is `test-output.txt` (sha256 `c811b5f0…`). The spec was pinned at `b9080313` before this run.

## Threaded mode: the red case that the generator is alive

It still prints condition 32's and condition 33's populations:

| count | what |
|---|---|
| **27,744** | item 5 |
| **2,448** | item 6 |
| **5,474** | typing, v20 keys |
| **3,868** | inline format, v20 keys |

The first two were already pinned. This change pins the last two as well (`fail(...)` with "stop").

Outside the new SECTION D, the output is byte for byte the output of the test before this change. Both read sha256 `bf5a4064…`: the pre-change test (sha256 `37222486…`) was built and run in the session's scratchpad first, and then compared.

## Synchronous-key mode (C): SECTION D

What the mode models (the test's header):

- a key or a command applies inside its call;
- the flush stays a posted user event;
- the poll runs only on a tick with no user event pending (`svpinst.cxx:440-444`), and does one thing;
- a command's reply goes at the next poll, and carries the engine's cache as it is then;
- a caret delete is the user's own Backspace;
- Writer-divergent means the whole end state: text, caret and mark.

| shape | v20 keys: runs / divergent / forged | all keys: runs / divergent / forged |
|---|---|---|
| moves only | 9,820 / 0 / 0 | 91,728 / 0 / 0 |
| Backspace | 235,680 / 0 / 0 | 2,201,472 / 0 / 0 |
| typing (condition 33) | 39,280 / 0 / 0 | 366,912 / 0 / 0 |
| inline format (condition 33) | 39,280 / 0 / 0 | 366,912 / 0 / 0 |

- Every shape also has 0 stale U completions, 0 refusals, 0 unanswered, and 0 guard hits.
- All eight earlier operations occur in every shape.
- Every answer the frozen client accepts under C occurs: a move by documented callback, `verified-move-readback`, `verified-key-undo`, `verified-boundary-noop`, `uno-command-result` and `inserted`.

**Red cases.** Each removes one rule of spec §5.2 that C's zero depends on, and each must print a forged reply. All keys, the four shapes summed:

| removed rule | forged | Writer-divergent |
|---|---|---|
| the reply goes at the next poll (here: in the command's own poll, before its flush) | 2,969,934 | 557,568 (Backspace: the stale snapshot picks the range form, and the gate refuses) |
| the poll runs only on a tick with no user event (here: a poll may land between two callbacks of one flush) | 2,575,890 | 0 |

The second red case forges replies but changes no end state in this model. The model's page snapshot only decides the delete's form, and the gate reads the engine's own cache by the time the delete runs. That is a fact about the model, not a claim about the product.

**The checks themselves were red once** (`red-mutation.txt`). A scratch copy moved the typing pin to 5475 and gave the main C mode the same-poll reply. It exited 1 with 18 failures: the pin, plus a forged reply and a stale U completion in every C shape, and the Writer-divergent check on "all keys, Backspace".

## Limits (printed by the test)

- A key is one event, with no hops. Only the withdrawn FIFO candidates depended on hops.
- Bold does not change a rectangle's width (condition 40).
- The page sends one item at a time (`editor-session.js:287-311`), so "one command per poll" is never contested here. **This model does not discriminate that rule.** It is kept by spec §5.2 and must be checked in the engine (§9.2).

## Corrections after two-seat review 1 (2026-10-20, appended; the text above is kept)

- **"Forged" compares geometry only.** It checks whether the reply's selection rectangles and caret differ from core's. In mode C the model chooses each completion string from its own oracle (`keyChanged`), so it cannot test a completion's meaning. The opus seat mislabelled 174,672 deletions as `verified-boundary-noop`, and the test still ended `ok` (`../review/opus-experiments-1/model/E6_lying_noop.summary.txt`). Testing meaning is the job of the native arms and the engine unit test (spec §15.1). The model gets no new mode.
- **"One command per poll … must be checked in the engine (§9.2)" pointed at nothing.** It now points at an engine unit red case in the diagnostic code, and at the §9.2 cell with its depth ≥ 2 non-vacuity rule (spec §15.4).
- **The printed run counts include duplicates.** They are 22–135× the distinct C scenarios (opus E5). The zero holds on the distinct set too.

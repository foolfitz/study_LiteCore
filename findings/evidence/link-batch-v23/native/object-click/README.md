# Object click under C, native: VERDICT O-RECORDED, every arm as seq 5/5 (2026-10-20)

The criteria are `ARMS.md`, pinned at `1085726b` before this run. The reader is `read_oc.py` (self-test 4/4, `smoke/self-test.txt`).

| item | value |
|---|---|
| run | `run_arms.py --arms-set o --modes seq,uni1f --runs 5`, 2026-10-20 09:30:54–09:50:36Z (17:30–17:50 local) |
| processes | 80, all exit 0 (`out/run-log.jsonl`, `out-runner.log`) |
| binary | sha256 `cdda2f0f…`, rebuilt in this session from `build.txt` (source `b117ccb9…`), the sha reproduced; core `native-lok-26-8` |
| fixture | `../ordered-commands/fixtures/image-aschar.fodt`, sha256 `b106deba…` (its `SHA256SUMS` line) |
| reading | `out/reader-output.txt`, exit 0, N = 5 |
| load1 | at most 3.00, over the first dozen cells (another project's build on this machine); 0.04–0.71 for the rest. Not a timing reading |

## The reading

| arm | the command after the click | uni1f against seq |
|---|---|---|
| ob-bold, ob-bold-i | `.uno:Bold` (explicit true) | as seq 5/5: the image stays, no bold run |
| ob-del, ob-del-i | Delete | as seq 5/5: the image is deleted, the caret is between `ab` and `cd` |
| ob-bksp, ob-bksp-i | Backspace | as seq 5/5: the same |
| ob-left, ob-left-i | Left | as seq 5/5: the image stays |

- **Control holds:** seq `ob-del` and seq `ob-bksp` deleted the image (0 frames) in every round, so the click selected the object.
- **Reference holds:** every arm's five seq rounds land the same.
- On the arms where the image stays selected (Bold, Left) the locator finds no caret, `["", ""]`, in both modes alike.

## What it says and what it does not

- **The race was reached by time.** In the uni1f arms without the idle, the command started 0.1–0.2 ms after the click returned, in all 20 cells (`startMs` of the command against `returnedMs` of the click, from each cell's `measured` record). That is far inside the 120 ms that Writer's `SwView::AttrChangedNotify` gives the shell switch (`view.cxx:567-574`, `:844`; ruling 2 §2.3). The `-i` arms started 150.2–155.0 ms after it.
- **Whether the switch had happened by then is not observed.** This harness sees no `SelectShell` and no `TimeoutHdl`. The source says the switch waits for the timer, and this is what the arm was built around, but it is read, not measured.
- **For these four commands the landing does not depend on it.** Delete and Backspace take the object path, and Bold and Left leave the document as the settled Writer does, whether the command comes at once or after 150 ms.
- **This is a record for a named limit, not a gate (ruling 2 §2.3).** Nothing differs, so there is nothing to decide about the engine's response now. L-object-click-shell-switch stays registered: four commands on one as-char image are not every slot on every shell (a frame, a drawing object, a command that exists on one stack and not the other).

## The interrupted first run

`out-interrupted-1726/` with `out-interrupted-1726-runner.log` is the first counted run, killed at 72 of 80 cells by the session restart (`out-interrupted-1726/NOTE.txt`). It is kept as it was and not read. The re-run above used the same binary, rebuilt and its sha reproduced, and the same arguments.

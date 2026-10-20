# Object click under C, native (SPEC-M3-ordered-commands §15.3, L-object-click-shell-switch; fable ruling 2 §2.3)

Written and committed **before the counted run**. `smoke/` is one round, not a counted reading.

## Why

A click that selects a frame or a drawing object makes Writer defer `SwView::SelectShell` to a 120 ms timer (`sw/source/uibase/uiview/view.cxx:567-574`, `:844`). Under C the page's next command can arrive within two ticks, before the timer fires, and resolve on the pre-click shell stack. Ruling 2 named the limit and asked for a native arm. The reference is the settled Writer (seq). The click's completion does not wait for the timer.

## What runs

| item | value |
|---|---|
| harness | `../ordered-commands/tool/oc_native.cpp`, binary `cdda2f0f…` (`build.txt`). It adds mode `uni1f` (one op per poll, the next op at the next poll, no idle), the idle op `I<ms>` and the click offset `C<point>+<dx>` |
| runner | `run_arms.py --arms-set o --modes seq,uni1f --runs 5` |
| fixture | `image-aschar`: `ab`, a 2 cm × 2 cm as-char image, then `cd` |

- Setup: Right ×2 records the cursor rect at the image's left edge as `img`; Home.
- Trigger: Right.
- Ops: click at `img+567` (1 cm right, inside the image; the smoke saw `GRAPHIC_SELECTION` `1644, 1418, 1133, 1133` in both modes), then one of `.uno:Bold` (explicit true), Delete, Backspace or Left. Each arm also has an `-i` variant with `I150` between the click and the command.

## The reading (`read_oc.py`)

- **Landing:** paragraphs (text and run weights, read with `read_results.shape`), plus each paragraph's frame count, plus the locator's caret.
- **Reference:** every seq round of an arm lands the same; otherwise that arm is NE.
- **Control (non-vacuity):** seq `ob-del` and seq `ob-bksp` delete the image (0 frames) in every round. That shows the click selected the object; if not, the whole reading is NE.
- **Per arm:** uni1f is either "as seq N/N" or "DIFFERS", with the landings printed. **This is a record for a named limit, not a gate**: where uni1f differs, the engine's response is decided then, with the landings in hand (ruling 2 §2.3).
- **Cleanliness:** as the other readers. Fewer than 5 rounds is not a counted reading.
- **Red cases** (`smoke/self-test.txt`): the seq control kept the image gives NE; a uni1f landing that differs is recorded as DIFFERS, not as a failure; a duplicate run-log entry gives NE.

## Default if never run (ruling 2 §2.3)

The limit stays registered, spec §4 row 11 stays "text clicks", and nothing in tiers 1 and 2 depends on it.

## Seen on the smoke (one round; recorded, not a reading)

Every arm landed in uni1f as in seq:
- Bold: the image stays;
- Delete and Backspace: the image is deleted and the caret is between `ab` and `cd`;
- Left: the image stays.

The `-i` variants landed the same.

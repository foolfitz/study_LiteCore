# NU-2 and NU-3: the Calc undo stack natively, and the bridge fix

Spec `specs/SPEC-P-calc-undo.md` section 4.4, written before these runs (`9a234eb65`). Nothing here is a link: native core 26.8 (`build-native-26-8`), the Calc bridge source with and without `OXSDK_ODS_UNDO`.

## Build

`wasm_sdk_probe/tools/build_calc_undo_native.py --out build/calc-undo-native` (2026-11-03 ~15:00, load 0.15, no make running): single-file g++ builds, `taskset -c 0`, about 10 s in all. Two variants from the same source bytes: `undo` (with `OXSDK_ODS_UNDO`) and `control` (without). Receipt copied to `build-receipt.json` here. The first attempt failed in the driver step, the tool's own snapshot layout (`../src/calc_cell_bridge.h` not found); fixed in the tool, rebuilt from scratch.

Driver `wasm_sdk_probe/tools/calc_undo_native.cpp`: `calc_cell_native.cpp` plus a document callback and `uno-wait` (post with notification, wait up to 3 s for `LOK_CALLBACK_UNO_COMMAND_RESULT`).

## NU-3: the fix (`nu3-undo`, `nu3-control`)

`probe_calc_undo_native.py --binary build/calc-undo-native/{undo,control}/calc-undo-native`, the 17 arms of `native-01`.

| Arm | native-01 | control | undo |
|---|---|---|---|
| `cell-bold`, `cell-italic` | 3 | 3 | **1** |
| `draft-then-bold` | 4 | 4 | **2** |
| the other 14 | as in native-01 | the same | the same |

NU-0 holds in both. The control equals native-01 on every arm, so the difference comes from the define, not from rebuilding. After the write, both variants read all three scripts bold (or italic), and their saved files are equal cell for cell (`sheet_state` of `cell-bold-U0.ods` and `cell-italic-U0.ods`): the fix changes how many undo actions, not what is written.

## NU-2: the stack (`nu2-stack`, `nu2-stack-02`)

`probe_calc_undo_stack_native.py --binary build/calc-undo-native/undo/calc-undo-native`: one document, a sequence of steps, after each the lists from `getCommandValues(".uno:Undo")` and `(".uno:Redo")`.

All seven preconditions hold, in both runs:

| Precondition | Counts (undo, redo) |
|---|---|
| a fresh document is empty | (0, 0) |
| a write adds one (`Input`) | (1, 0) |
| a write that changes nothing adds none (op 1 with the same text, op 7 on a range already bold) | unchanged |
| undo moves one to redo | (2, 0) → (1, 1) → (0, 2) |
| redo moves one back | (0, 2) → (1, 1) |
| a write after an undo clears redo | redo 0 |
| `saveAs` (the engine's own save call) keeps the stack | (2, 0) before and after |

Two findings that change the design:

- **The completion callback carries no information.** `.uno:Undo` and `.uno:Redo` answer `success: false` at once, both when they did undo something (the lists moved) and on an empty stack (`wasModified` is the only field that differs, and it is the document's modified flag, not the command's effect). So the engine must read the lists before and after (spec 4.2 E4); trusting the callback would report every undo as failed, or every empty one as done.
- **An input undo moves the cell cursor to the restored cell; an attribute undo does not.** `nu2-stack-02` adds `cursor-to-A1-again` before undoing F1's input: the cursor goes from A1 to F1 (`.uno:CellCursor` `6105, 0, 1274, 269, 5, 0`; its last two numbers are column and row). Undoing the range bold on A1:C2 left the cursor where it was. In `nu2-stack` the cursor already sat on F1 (the bridge's op 1 had moved it there), so that run could not show the move; the step was added for that reason, the first run is kept.

`nu2-stack-reader-red` is the first attempt: `getCommandValues(".uno:Undo")` comes back pretty-printed over several lines and the line reader died on it. `run_driver` in `probe_calc_undo_native.py` now decodes successive JSON values (identical results for one-line replies; NU-3 ran before the change, all its replies one line).

Each run's LOK user profile was deleted after the run.

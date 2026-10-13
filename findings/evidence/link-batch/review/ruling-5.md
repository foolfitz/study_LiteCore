# Ruling 5 — typing and inline formats behind a pending arrow (ruling 4 condition 33): reachable today; finding 137 broadens

Ruled by fable on the owner's behalf (same authorisation as rulings 2–4). Inputs: `19cec698` (`findings/evidence/link-batch/extend-model/README.md` appended sections "Condition 32" and "Condition 33", `test-output-2.txt`, `condition-32-population.txt`; `wasm_sdk_probe/tests/extend_completion_model_test.cpp`), finding 137 (`57d16143`, observation appended `6f384716`), spec §13 (`adf69f0f`). Conditions continue from 37.

**What I ran.** Rebuilt the second-run test into the scratchpad: exit 0, `ok`, no `STOP CONDITION`. Traced the two condition-33 first sequences: `E=none U=Right lagReg=0 lagDeadline=0 Type(lagReg2=0)` → engine `xabcd`, Writer `axbcd` (the Right is answered by the readback with its key still queued; the paste runs first); `E=uno:undo U=Left lagReg=0 lagDeadline=0 Bold(lagReg2=0)` → engine `z*abcd`, Writer `zabcd` (the Left completes on undo's late `TEXT_SELECTION` before its key is posted; `.uno:Bold` runs on the still-selected `z`).

## RULING

### Reachable on 0.2.12 and 0.2.18: yes, both shapes, under finding 137's precondition

Both releases run engine `e2-editor-v19` and the same `editor-shell/` input path (E1-C-bound). The chain is the same on both:

- **Typing.** A typed character is enqueued behind the move in the session's serial queue (`editor-shell/editor-session.js:510-511`, `_enqueue("commit-text", document.insertText)`; the drain runs one item at a time, `:287-311`). The move completes by the 250 ms readback when the core thread is silent (`probe_engine.cpp:5499-5502`, `:2300-2330`), its key still queued. The insert is a synchronous `paste()` under the SolarMutex (`:3186-3221`), so it runs ahead of the queued key. Precondition: a core-thread silence longer than `EditorMoveReadbackDeadlineMs` (250 ms, `:465`), the same as 137's item 6. Effect: the typed unit lands at the pre-move caret; the move then steps over the next unit. Not a deletion; the user sees the misplaced character.
- **Inline format.** Undo (or any `uno-command-result` operation whose late flush carries a selection, or a select-range completed early) leaves the page's snapshot collapsed while core holds a selection; the page sends the arrow bare on both releases (0.2.12 has no click-then-move; 0.2.18's click-then-move runs only when the snapshot says range, `web/e2-editor-app.js:2609-2615`); the move completes on the earlier operation's late `TEXT_SELECTION` (today's first-callback rule, `:2155-2175`, `:5470-5472`) before its own key is posted; the snapshot is now the range; Ctrl+B goes through `editorAction("set-bold")` → the gate reads the cached range and `set-bold` is offered on ranges (`e2/expected-gesture-offers.json:9-13`, pinned against the shipped manifest at every freeze) → `startUnoMutation` posts `.uno:Bold` with a listener, synchronous (`:4106-4108`; `unoctitm.cxx:655-657`), ahead of the queued Left. Precondition: the core thread silent longer than one page round trip after the earlier operation, 137's item 5. Effect: the format lands on text the user had just deselected.

### One finding, broadened; not a separate one

Finding 137 broadens from "an arrow then Backspace" to **"a document command sent behind an arrow the core has not yet run lands on the wrong state"**, with three effects listed separately in its severity row: delete (the wrong text is deleted, or one unit ahead), type (the character lands one unit early), inline format (applied to deselected text). One cause (spec §13.2: a synchronous document command — `.uno:Delete`, `paste`, `.uno:Bold` — dispatched behind a posted key the engine has reported complete without evidence that it ran), one precondition (a core-thread silence of 137's two lengths), one closure (the ordered-commands spec). Splitting it by effect would give three findings with the same cause and the same fix. The file keeps its name; the broadening is appended with a revision row; the index line changes. Severity ordering in the row: deletion first (silent loss), typing second (visible at once, repairable by the user), format third.

### v20's scope and the count: unchanged, with two text changes

- v20's scope stands as ruled in 4 (page number, C, `caretBefore` data, the count). Neither shape depends on anything v20 adds; both exist on the counted release.
- The count is unchanged: no runner induces a core-thread silence; the chain measures nothing of this class and claims nothing about it.
- The release text for v20 (ruling 4 condition 36) names the broadened class, all three effects, both releases.
- The next spec is renamed from "ordered deletes" to **ordered commands**: every document command the page asks for is applied in the order Writer would apply it. Candidate A (the user's own key, FIFO, proved by the `.uno:Undo` payload) covers deletes only; for typing and formats it becomes A′, typing as posted key events (the engine's own fallback path already posts code points, `:3195-3207`) and formats as posted accelerator keys, each to be measured natively (IME composition, 122's typing latency, Writer's accelerator handling) before being chosen; candidates B (FIFO marker) and C (single-thread engine, unipoll) cover all three by construction and keep their measurement questions.

### The executor's named limit

Accepted as a limit of the next spec, not of this ruling: in the model an inline format does not change rectangle widths, so its flush carries only its result; natively a bolder line may re-send the selection rectangles, which would make an inline format on a range a member of L-extend-prior-flush as the earlier operation. Reachability today does not depend on it (the bold divergence traced above needs no rectangle change).

## WHY (for the owner)

打字和粗體也一樣：按了方向鍵之後核心若停頓超過兩百多毫秒，引擎會先回報移動完成，緊接著打的字會貼在移動之前的位置、粗體會套到剛取消選取的字上，因為貼字和格式指令跟刪除一樣是同步執行、會插到還沒跑的按鍵前面。今天的 0.2.12 和 0.2.18 都到得了，前提和 137 完全相同。所以不另立 finding，把 137 的範圍擴大成「核心停頓時，排在方向鍵後面的文件指令會落在錯的狀態上」，三種效果分開寫清楚：刪錯、字貼錯位置、格式套錯；成因一個、修法一個。這一批要出的東西和計數都不變，只有發佈說明要把這一類三種效果都寫明。下一份規格從「有序刪除」改名「有序指令」，打字和格式也要照 Writer 的順序執行，怎麼做先在原生量。

## FACT CHECK

| claim relied on | status | where |
|---|---|---|
| second run reproduces: exit 0, no stop condition; the two traced outcomes | confirmed (ran it) | scratchpad rebuild of `19cec698`; traces `… U=Right … Type(lagReg2=0)` → `xabcd`/`axbcd`; `… E=uno:undo U=Left … Bold(lagReg2=0)` → `z*abcd`/`zabcd` |
| condition 32's population: item 5 27,744, item 6 2,448, other 0 | confirmed | README "Condition 32"; `condition-32-population.txt` (1,792 lines) |
| condition 33's counts on v20's keys: typing 5,474 of 45,776; format 3,868 | confirmed | README "Condition 33"; `test-output-2.txt` |
| typed text is enqueued behind the move and run by the serial drain | confirmed | `editor-shell/editor-session.js:510-511`, `:287-311` |
| the engine's insert is a synchronous paste | confirmed | `probe_engine.cpp:3186-3221` |
| every key-path move arms the 250 ms readback; readback serialises the cache | confirmed | `:5499-5502`, `:2300-2330`, `:465` |
| caret-start moves complete on the first callback | confirmed | `:2155-2175`, `:5470-5472` |
| `startUnoMutation` dispatches with a listener, synchronous | confirmed | `:4106-4108`; `sfx2/source/control/unoctitm.cxx:655-657` |
| `set-bold` is offered on ranges in the shipped profile | confirmed (pin) | `e2/expected-gesture-offers.json:9-13`, checked by `check_gesture_offers.py` at every freeze (`Makefile:3586-3596`) |
| 0.2.12 sends the arrow bare; 0.2.18 sends it bare when the snapshot is collapsed | confirmed (ruling 4) | 0.2.12 page via tree `7fb0ed08` (no `moveFromPoint`); `web/e2-editor-app.js:2609-2615` |
| finding 137 as registered and its appended observation | confirmed | `findings/137-….md` (`57d16143`, `6f384716`) |
| core-thread silences on the product beyond 135's one cell | not measured; stated as such |
| a bolder line re-sends selection rectangles natively | not checked; the executor's limit, assigned to the next spec |

## CONDITIONS

37. Finding 137 is broadened as above (append-only: a "範圍擴大" section, the three effects in the severity row, a revision row; the index line updated; file name unchanged), with the two traced sequences as its evidence for the new effects and "reachable on 0.2.12 and 0.2.18" stated for each.
38. v20's scope and the count are unchanged; the release text names the broadened class with its three effects and both releases.
39. The next spec is "ordered commands": deletes, typing and inline formats, with candidates A/A′, B, C and their native measurements; the model's two new shapes stay in the generator and the next spec's rule must pass them.
40. The executor's rectangle-width limit is recorded in the next spec's model section; nothing in this link depends on it.
41. Default: if 37 is never appended, the release text of condition 38 must still name all three effects; if 39 is never written, Shift+Arrow does not ship on any profile (ruling 4 condition 36 stands).

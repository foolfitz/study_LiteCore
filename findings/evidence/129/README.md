# Finding 129 — evidence: arrow keys on a selection are refused, and the toast shows the engine's developer message

Reported by the owner in the hand test of host 0.2.12 (2026-10-12): "將文字反白選取的時候，使用方向鍵會報錯". Reproduced the same day by `wasm_sdk_probe/tools/probe_hand_test_0212.py`; the reports are finding 128's (`../128/chrome-1.json`, `../128/firefox-1.json`), arms `selection` and `shift`. Host 0.2.12 `b245ae7`, served page `8909564e…`, engine v19.

## The arms

`selection`: click at (0.5, 0.010373) of `#paper` (the first body paragraph of the owner's document), drag from x 0.3 to x 0.5 on that line through the page's own pointer handler (`run_e2_c_product_path.DRAG`), wait for quiet, read `#toolbar[data-selection-shape]` (`range-single` in every arm), press ONE real key (CDP `Input.dispatchKeyEvent` in Chrome, WebDriver actions in Firefox), wait 3 s and for quiet. Once each for ArrowLeft, ArrowDown, End.

`shift`: click at the same place (a collapsed caret), press Shift+ArrowRight three times, 0.6 s apart.

## Results (both browsers identical)

| Key on a `range-single` selection | Toast | Latency line | State, generation, revision |
|---|---|---|---|
| ArrowLeft | `◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged` | `◀ 失敗` | ready, 1, 32 → 32; still `range-single` |
| ArrowDown | `下移一行：EDITOR_FORMAT_GESTURE_UNSUPPORTED：…` (same message) | `下移一行 失敗` | the same |
| End | `移到行尾：EDITOR_FORMAT_GESTURE_UNSUPPORTED：…` (same message) | `移到行尾 失敗` | the same |

Shift+ArrowRight on a collapsed caret: the sink (which rides the caret) moved 451 → 468 → 485 → 503 px, the shape stayed `collapsed` throughout, latency `▶ 37 ms` (Chrome) / `▶ 38 ms` (Firefox). The page dispatches `move-character-right` and ignores Shift. (Firefox's log has six keydowns: WebDriver's Shift key down is a keydown of its own.)

## Why (read from the sources, not measured)

- `dist/profiles/e2-editor-v19/sdk-manifest.json` `editorContract.actions`: `move-character-left`, `move-character-right`, `move-line-up`, `move-line-down`, `move-line-home`, `move-line-end` all declare `gestures: ["collapsed"]`.
- The refusal text is the engine's gesture gate (`wasm_sdk_probe/src/probe_engine.cpp`).
- The page's keydown (`web/e2-editor-app.js:2398–2405`) checks only `session.offers(action)`; `run()`'s failure toast (`:1729`) prints `${label}：${code}：${message}`.

## Native reference (`native/`, 2026-10-12)

`wasm_sdk_probe/tools/f129_native_arrow_on_selection.cpp` against native LibreOffice 26.8 (`native-lok-26-8/build/instdir`, `SAL_USE_VCLPLUGIN=svp`), fixture `wasm_sdk_probe/test-docs/f129/arrow-selection.fodt` (hashes in `native/round-20261012T020528Z/inputs.sha256`). Selection `BETA GAMMA` (offsets 9–19 of P2) made FORWARD (Shift+Right ×10 from 9: the point at 19) and BACKWARD (Shift+Left ×10 from 19: the point at 9); one key; then `#` is typed and the document's text is read (`SelectAll` + `getTextSelection`). Where `#` lands is where the caret was; had the key not collapsed the selection, `#` would have replaced it (the `control-none` arm shows that it does when no key is pressed).

Result (`native/round-20261012T020528Z/arms.jsonl`): Writer moves FROM THE POINT by the key's unit and drops the selection — forward Left 18, Right 20; backward Left 8, Right 10; Up/Down to the neighbouring paragraph at the point's x; Home 0; End 25 — not the browser/Word convention of collapsing to the selection's start or end. The `caret-shift-*` arms show Shift+key extending from the point. The first round (`native/round-20261012T020312Z-p1-instrument-fault/`) posted `.uno:GoToStartOfDoc`/`GoToStartOfPara` around the Down key without waiting for their results and made its selection in P1 (`paragraph `, offsets 9–19); the same rule holds there, Up on the first line going to the line's start. Kept as an instrument fault.

## Native: does "click at the point, then the key" reproduce Writer? (2026-10-12, task `handoff/tasks/TASK-2026-10-12c-native-page-rectangles-and-129-shapes.md` Part N2)

The page fix planned for release 0.2.13 (`specs/SPEC-M3-autosave.md` §3.7, §8.1 Q5): when text is selected and an unshifted Left/Right/Up/Down/Home/End is pressed, the page first CLICKS at the point's cursor rectangle (x = the rectangle's x, y = its y + height / 2), which collapses the selection there, and then sends the ordinary collapsed move. The engine's click is `postMouseEvent(LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0)` then the same with `MOUSEBUTTONUP` (`wasm_sdk_probe/src/probe_engine.cpp` `handleClick`). This section asks whether that emulation lands where Writer itself lands, including the hard shapes. Native only.

### Prediction (main session, before any run; copied verbatim from the brief)

- P-N2a: `emu` = `ref` in all 12 old arms.
- P-N2b: in S2, S3 and S4, `emu` = `ref` for all six keys.
- P-N2c: S1 (soft wrap) is where they may differ — the point at the wrap offset has two visual positions (end of line 1, start of line 2); predicted: Left and Right same, at least one of Home / End / Up / Down differs.
- P-N2d: S5 is a cell selection; no prediction of `ref` beyond "it is not an error"; `emu` lands inside B1.
- P-N2e: every click on a selection is answered by at least one callback within 400 ms (the selection disappearing is news).

(Written into this file before the first native run of this part; the results subsections below were added afterwards and this block was not edited.)

### Results

#### What was run

| item | value |
|---|---|
| tool | `wasm_sdk_probe/tools/f129_native_point_click.cpp` (new; `f129_native_arrow_on_selection.cpp` is untouched). Each folder below holds `tool-source-as-run.cpp` and `inputs.sha256` for the version that ran there |
| runner, analysis | `wasm_sdk_probe/tools/run_f129_native_point_click.sh`, `wasm_sdk_probe/tools/analyze_f129_point_click.py` (reads the raw `arms-r*.jsonl`, compares strings, writes `analysis.json`, `summary.md`; the exact command is in each folder's `analysis-command.txt`) |
| build | `g++ -std=c++17 -O2 -I<libreoffice-26-8>/include tools/f129_native_point_click.cpp -ldl -lpthread -o f129-native-point-click` |
| native build | `native-lok-26-8/build/instdir`, `SAL_USE_VCLPLUGIN=svp`; every round is 3 processes in parallel, each with its own profile and its own copies of the fixtures; inside a process every arm is a FRESH `documentLoad` |
| fixtures | `wasm_sdk_probe/test-docs/f129/arrow-selection.fodt` (`436ce8c3…`, the old P1/P2/P3 document), new `arrow-selection-shapes.fodt` (`34251b52…`), new `arrow-selection-wrap.fodt` (`9d6e05bb…`, extras only) |
| main round | `native/point-click-round-20261012T031459Z/` - 3 rounds x 91 arms + 1 discovery load; ended 2026-10-12T03:28:44Z |
| extra rounds | `native/point-click-extras-round-20261012T033055Z/` (ended 03:42:09Z), `native/point-click-extras-drag-round-20261012T034525Z/` (03:47:39Z), `native/point-click-extras-dragend-round-20261012T034823Z/` (03:51:29Z) |

Arms, as in the brief: for each of 7 selections (the old P2 FORWARD and BACKWARD, S1-S5) and each of Left, Right, Up, Down, Home, End: `ref-<shape>-<key>` (Writer's own key with the selection in place, then `#`, then read) and `emu-<shape>-<key>` (wait for quiet; read the latest `INVALIDATE_VISIBLE_CURSOR` rectangle; post `MOUSEBUTTONDOWN` + `MOUSEBUTTONUP` at `x = rect.x`, `y = rect.y + rect.h / 2` (integer division) with the engine's arguments `1, 1, 0`; wait for quiet; the key unshifted; `#`; read), plus one `click-only-<shape>` per shape (the click, then `#`). "Quiet" = no callback for 500 ms (cap 4 s). Reading the text: `.uno:SelectAll` + `getTextSelection`, repeated until the text stops changing (see the instrument note). The selections: old P2 `BETA GAMMA` (offsets 9..19) forward and backward; S1 the 10 characters before the first wrap offset W (W = 101, found each round by pressing Right until the cursor rectangle's y changes: `1418, 1418` after 100 presses at x 10961, `1418, 1694` after 101), forward by Shift+Right x10; S2 `visual line` of the first visual line (the point right before the `<text:line-break/>`); S3 `paragraph` + the paragraph break (the point in the empty paragraph); S4 `cell A1` inside cell A1; S5 `text` of A1 plus one more Shift+Right across the cell boundary. Navigation to S2-S5 is Ctrl+Down (next paragraph); the selection read-back (`made`) equalled the expectation in every arm of S1-S4 and of the old shapes (S5's read-back is below).

#### Main result: `emu` = `ref` everywhere the brief asked

`#` position = index in the whole-document text read back after the key (so it is a document offset: P1 = 0..23, the S1 paragraph starts at 0, etc.; ⏎ is a paragraph or line break, ⇥ a table cell separator). All 42 cells (7 shapes x 6 keys) are `same` in all 3 rounds; ref and emu were stable across rounds (no cell changed between rounds). The 12 old ref arms give exactly the text of `native/round-20261012T020528Z/arms.jsonl` in 36 of 36 (arm, round) pairs.

| shape | key | Writer's own key (`ref`): `#` at index, excerpt | click then key (`emu`): `#` at index, excerpt | verdict |
|---|---|---|---|---|
| p2-forward | Left | 43, `LPHA BETA GAMM<#>A DELTA⏎P3 thi` | (same) | **same** |
| p2-forward | Right | 45, `HA BETA GAMMA <#>DELTA⏎P3 third` | (same) | **same** |
| p2-forward | Up | 24, `aragraph above<#>⏎P2 ALPHA BETA` | (same) | **same** |
| p2-forward | Down | 75, `aragraph below<#>` | (same) | **same** |
| p2-forward | Home | 25, `ragraph above⏎<#>P2 ALPHA BETA ` | (same) | **same** |
| p2-forward | End | 50, `TA GAMMA DELTA<#>⏎P3 third para` | (same) | **same** |
| p2-backward | Left | 33, `above⏎P2 ALPHA<#> BETA GAMMA DE` | (same) | **same** |
| p2-backward | Right | 35, `ove⏎P2 ALPHA B<#>ETA GAMMA DELT` | (same) | **same** |
| p2-backward | Up | 13, `P1 first para<#>graph above⏎P2` | (same) | **same** |
| p2-backward | Down | 63, `A⏎P3 third par<#>agraph below` | (same) | **same** |
| p2-backward | Home | 25, `ragraph above⏎<#>P2 ALPHA BETA ` | (same) | **same** |
| p2-backward | End | 50, `TA GAMMA DELTA<#>⏎P3 third para` | (same) | **same** |
| s1 | Left | 100, `ber oscar papa<#> quebec romeo ` | (same) | **same** |
| s1 | Right | 102, `r oscar papa q<#>uebec romeo si` | (same) | **same** |
| s1 | Up | 0, `<#>S1 alpha bravo` | (same) | **same** |
| s1 | Down | 201, `ive six seven <#>eight nine ten` | (same) | **same** |
| s1 | Home | 101, `er oscar papa <#>quebec romeo s` | (same) | **same** |
| s1 | End | 200, `five six seven<#> eight nine te` | (same) | **same** |
| s2 | Left | 483, `rst visual lin<#>e⏎S2 second vi` | (same) | **same** |
| s2 | Right | 485, `t visual line⏎<#>S2 second visu` | (same) | **same** |
| s2 | Up | 406, `ynine thirty t<#>hirtyone thirt` | (same) | **same** |
| s2 | Down | 503, `econd visual l<#>ine⏎S3 text be` | (same) | **same** |
| s2 | Home | 464, `irtyfive end1⏎<#>S2 first visua` | (same) | **same** |
| s2 | End | 484, `st visual line<#>⏎S2 second vis` | (same) | **same** |
| s3 | Left | 541, `mpty paragraph<#>⏎⏎S3 text afte` | (same) | **same** |
| s3 | Right | 543, `ty paragraph⏎⏎<#>S3 text after ` | (same) | **same** |
| s3 | Up | 507, `d visual line⏎<#>S3 text before` | (same) | **same** |
| s3 | Down | 543, `ty paragraph⏎⏎<#>S3 text after ` | (same) | **same** |
| s3 | Home | 542, `pty paragraph⏎<#>⏎S3 text after` | (same) | **same** |
| s3 | End | 542, `pty paragraph⏎<#>⏎S3 text after` | (same) | **same** |
| s4 | Left | 586, `raph⏎S4 cell A<#>1 text⇥S4 cell` | (same) | **same** |
| s4 | Right | 588, `ph⏎S4 cell A1 <#>text⇥S4 cell B` | (same) | **same** |
| s4 | Up | 554, `h⏎⏎S3 text aft<#>er the empty p` | (same) | **same** |
| s4 | Down | 619, `ext⏎S4 cell A2<#> text⇥S4 cell ` | (same) | **same** |
| s4 | Home | 577, `pty paragraph⏎<#>S4 cell A1 tex` | (same) | **same** |
| s4 | End | 592, `4 cell A1 text<#>⇥S4 cell B1 te` | (same) | **same** |
| s5 | Left | 592, `4 cell A1 text<#>⇥S4 cell B1 te` | (same) | **same** |
| s5 | Right | 594, `cell A1 text⇥S<#>4 cell B1 text` | (same) | **same** |
| s5 | Up | 543, `ty paragraph⏎⏎<#>S3 text after ` | (same) | **same** |
| s5 | Down | 625, ` cell A2 text⇥<#>S4 cell B2 tex` | (same) | **same** |
| s5 | Home | 593, ` cell A1 text⇥<#>S4 cell B1 tex` | (same) | **same** |
| s5 | End | 608, `4 cell B1 text<#>⏎S4 cell A2 te` | (same) | **same** |


`click-only` (where the collapse itself lands; `#` typed right after the click, `selectedAfterClick` is empty in all of them):

| shape | click (x, y) | the cursor rectangle clicked | `#` at index, excerpt |
|---|---|---|---|
| p2-forward | 4152, 1832 | 4152, 1694, 0, 276 | 44, `PHA BETA GAMMA<#> DELTA⏎P3 thir` |
| p2-backward | 2565, 1832 | 2565, 1694, 0, 276 | 34, `bove⏎P2 ALPHA <#>BETA GAMMA DEL` |
| s1 | 1418, 1832 | 1418, 1694, 0, 276 | 101, `er oscar papa <#>quebec romeo s` |
| s2 | 3171, 2936 | 3171, 2798, 0, 276 | 484, `st visual line<#>⏎S2 second vis` |
| s3 | 1418, 3764 | 1418, 3626, 0, 277 | 542, `pty paragraph⏎<#>⏎S3 text after` |
| s4 | 2417, 4316 | 2417, 4178, 0, 276 | 587, `aph⏎S4 cell A1<#> text⇥S4 cell ` |
| s5 | 6403, 4316 | 6403, 4178, 0, 276 | 593, ` cell A1 text⇥<#>S4 cell B1 tex` |

In each of the seven the click lands at the offset where the visible cursor was (for the six ordinary selections that is the offset the selection ended at, for S5 the start of B1): the click collapses the selection in place.

What S5 (the cell boundary) looked like, from the raw: after Shift+Right x5 from inside A1's text `getTextSelection` returned `S4 cell A1 text⇥S4 cell B1 text⏎` - the whole contents of A1 and B1, not the 5 characters pressed for; so Writer turned it into a cell selection (A1:B1), as the brief anticipated. The visible-cursor rectangle was `6403, 4178` (B1's start); `TEXT_SELECTION_START`/`END` were `2477, 4178` / `2837, 4178` (inside A1), so for a cell selection neither selection rectangle is at the point. It is not an error: ref Left -> end of A1 (592), Right -> B1 after one character (594), Up -> start of the paragraph above the table (543), Down -> start of B2 (625), Home -> start of B1 (593), End -> end of B1 (608); that is, Writer acts from B1's start. emu: the click at `6403, 4316` produced `.uno:StateTableCell=T1:B1` (about 440 ms later) and `#` lands at B1's start (593); all six keys give the same text as ref.

#### Callbacks after the click (P-N2e)

For all 306 `emu` / `click-only` / `emuend` arms of all rounds (`analysis.json` -> `clickCallbacksPerArm`, summarised per folder in `summary.md`): a callback arrived within 400 ms in 306 of 306. The first one arrived 0.2-1.2 ms after the click (median 0.3-0.6 ms per shape). Within 400 ms the only types seen are `TEXT_SELECTION` (306, the selection disappearing: payload empty), `MOUSE_POINTER` (228) and `INVALIDATE_VISIBLE_CURSOR` (54; only in the `emuend` arms, where the click moved the caret). After 400 ms: `STATE_CHANGED` (`.uno:Cut=disabled`, `.uno:Copy=disabled`, `.uno:StateWordCount=...`, at about 420-440 ms; in S5 also `.uno:StateTableCell=T1:B1`, `.uno:MergeCells`, `.uno:SplitTable` and `RULER_UPDATE`, up to 544 ms). `getTextSelection` right after the click was empty in all arms (the selection did not survive the click).

What this means for the 400 ms grace in `editor-shell/editor-session.js` `placeCaret`: in every `emu` arm and `click-only` arm (the click lands on the rectangle the caret is already at) NO `INVALIDATE_VISIBLE_CURSOR` follows - 0 of 252 - so the only engine answer inside 400 ms is the empty `TEXT_SELECTION` (and `MOUSE_POINTER`). Whether that empty `TEXT_SELECTION` ends the page's wait early depends on it advancing `sourceSequence`: from reading `src/probe_engine.cpp` `onLokCallback` + `parseEditorSelectionRectangles` (an empty payload returns true, so `editorStateChanged` is set and the sequence is incremented) it should; that is inferred, not measured here. If it did not, the click would cost the 400 ms grace on every key press.

#### Predictions

| prediction | verdict | what the raw output shows |
|---|---|---|
| P-N2a `emu` = `ref` in all 12 old arms | **held** | 12 of 12 cells `same`, in 3 of 3 rounds |
| P-N2b `emu` = `ref` for all six keys in S2, S3, S4 | **held** | 18 of 18 cells `same`, 3 of 3 rounds |
| P-N2c S1: Left and Right same, at least one of Home / End / Up / Down differs | **missed on S1 as specified** (S1 = 6 of 6 `same`, 3 rounds); **the predicted effect exists on other shapes, in Down only** (extra shapes below: S1 reached by mouse drag, and a mid-word wrap reached by Shift+End or by drag: Down differs, the other five keys `same`) | the premise "the point at the wrap offset has two visual positions" is false for S1 as made: with Shift+Right the caret at W is displayed at the START of line 2 (`1418, 1694`), the end-of-line-1 position is offset 100 (before the trailing space, `10961, 1418`), and the two are different offsets |
| P-N2d S5 is a cell selection; ref is not an error; emu lands inside B1 | **held** | `made` = both cells' text; no error; `StateTableCell=T1:B1` after the click and `#` at B1's start; all six keys same as ref |
| P-N2e every click on a selection is answered by a callback within 400 ms | **held** | 306 of 306, first callback 0.2-1.2 ms after the click (an empty `TEXT_SELECTION` and a `MOUSE_POINTER`); no cursor callback follows an `emu` click |

#### Extra shapes (not in the brief): where the visible cursor and the selection end disagree

Why: P-N2c's premise failed on S1 (above), and the raw `selectionState` records show the visible-cursor rectangle (`INVALIDATE_VISIBLE_CURSOR`, the one the planned fix clicks at) equals `TEXT_SELECTION_END` for every forward selection of the main round, and equals `TEXT_SELECTION_START` for the old BACKWARD one - but equals neither for the cell selection (S5, above). A point at the END of a wrapped line is the other place two positions can exist, and it is how a mouse drag to the right of a line's end finishes, and CJK text (the owner's documents are Chinese, inferred from the document name and the project notes) wraps between any two characters, which is what the unbroken token imitates. So, before saying anything about wrap, three more selections were run, all with the same ref / emu arms and 3 rounds each (the tool was extended for them after the main round; the main round's source is kept as `tool-source-as-run.cpp` in its folder; against it, the current source adds the extra shapes, a drag branch around the original key presses, the `emuend` kind and the `F129_EXTRAS` switch, and gives `discoverWrap` two parameters that do not change its output; the arm list and the output without the switch are unchanged):

- `s1e`: the S1 paragraph, the 10 characters before W, selected with Shift+End (the point at the end of line 1).
- `m1r` / `m1e`: `arrow-selection-wrap.fodt`, a 330-letter unbroken token (it breaks MID-WORD: the first line has offsets 0..88, the cursor is at `11202, 1418` after 88 presses and at `1418, 1694` after 89, so B = 89), the 10 characters before B selected with Shift+Right x10 (`m1r`, the point displayed at the start of line 2) or with Shift+End (`m1e`, the point displayed at the END of line 1).
- `s1d` / `m1d`: the same two paragraphs, the selection made with the product's own mouse drag (`DOWN` at a point inside the last characters of line 1, `MOVE` and `UP` at a point to the right of the end of line 1, the arguments of `OXSDK_EDITOR_SELECTION_MOUSE_DRAG` in `probe_engine.cpp`). The drag in S1 ends at offset 101 (`made` = `scar papa ` with the trailing space).

For the three where the point was made at the end of line 1 (`m1e`, `s1d`, `m1d`) the raw `selectionState` is: visible cursor `11322, 1418` (m1e, m1d) / `11021, 1418` (s1d) - the end of line 1 - but `TEXT_SELECTION_END` `1418, 1694`, the START of line 2. `emuend` = the same emulation but the click is aimed at the `TEXT_SELECTION_END` rectangle (x, y + h/2) instead of the visible cursor.

**Extra shapes** (not in the brief; see the section below). `emuend` = the click aimed at the `TEXT_SELECTION_END` rectangle instead of the visible cursor rectangle (only run for the three shapes where the two differ).

| shape | key | `ref`: `#` at index, excerpt | `emu` | `emuend` |
|---|---|---|---|---|
| s1e | Left | 99, `mber oscar pap<#>a quebec romeo` | (same) | - |
| s1e | Right | 101, `er oscar papa <#>quebec romeo s` | (same) | - |
| s1e | Up | 0, `<#>S1 alpha bravo` | (same) | - |
| s1e | Down | 198, `r five six sev<#>en eight nine ` | (same) | - |
| s1e | Home | 0, `<#>S1 alpha bravo` | (same) | - |
| s1e | End | 100, `ber oscar papa<#> quebec romeo ` | (same) | - |
| m1r | Left | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | (same) | - |
| m1r | Right | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | (same) | - |
| m1r | Up | 0, `<#>afkpuzejotydin` | (same) | - |
| m1r | Down | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | (same) | - |
| m1r | Home | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | (same) | - |
| m1r | End | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | (same) | - |
| m1e | Left | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | (same) | (same as ref) |
| m1e | Right | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | (same) | (same as ref) |
| m1e | Up | 0, `<#>afkpuzejotydin` | (same) | (same as ref) |
| m1e | Down | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | **differs**: 270, `puzekpuzejotyd<#>insxchmrwbglqv` | (same as ref) |
| m1e | Home | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | (same) | (same as ref) |
| m1e | End | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | (same) | (same as ref) |
| s1d | Left | 100, `ber oscar papa<#> quebec romeo ` | (same) | (same as ref) |
| s1d | Right | 102, `r oscar papa q<#>uebec romeo si` | (same) | (same as ref) |
| s1d | Up | 0, `<#>S1 alpha bravo` | (same) | (same as ref) |
| s1d | Down | 201, `ive six seven <#>eight nine ten` | **differs**: 199, ` five six seve<#>n eight nine t` | (same as ref) |
| s1d | Home | 101, `er oscar papa <#>quebec romeo s` | (same) | (same as ref) |
| s1d | End | 200, `five six seven<#> eight nine te` | (same) | (same as ref) |
| m1d | Left | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | (same) | (same as ref) |
| m1d | Right | 90, `sxdinsxchmrwbg<#>lqvafkpuzejoty` | (same) | (same as ref) |
| m1d | Up | 0, `<#>afkpuzejotydin` | (same) | (same as ref) |
| m1d | Down | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | **differs**: 270, `puzekpuzejotyd<#>insxchmrwbglqv` | (same as ref) |
| m1d | Home | 89, `nsxdinsxchmrwb<#>glqvafkpuzejot` | (same) | (same as ref) |
| m1d | End | 180, `ejotydinsxchmr<#>wbhmrwbglqvafk` | (same) | (same as ref) |

Reading of the extra tables (all identical in 3 of 3 rounds): Left, Right, Up, Home, End are `same` in all five extra shapes; Down differs in exactly the three shapes whose point is displayed at the end of line 1 (`m1e`, `s1d`, `m1d`), and only for `emu`. In those, Writer's own Down goes to the start of line 3 (S1: 201, `1418, 1970`; token: 180, `1418, 1970`): it moves from the point's position in the layout, the start of line 2. After the click the Down lands elsewhere - 199 at `11054, 1694` (on line 2, near the displayed x) for `s1d`, 270 at `1418, 2246` for `m1d` / `m1e` - and these two do not follow one simple rule, so I do not claim one (why the token case goes two lines is not explained). `emuend` (the click at the selection-end rectangle) is `same` as ref in 18 of 18 cells (3 shapes x 6 keys, 3 rounds). That was run only for FORWARD selections, where the point is the selection's END; a BACKWARD selection's point is its START, and the page cannot tell the two apart from the rectangles alone (in the cases where the cursor matches neither, which end is the point is exactly what is in question), so `emuend` is a measured candidate for forward selections only, not a rule. The click-only landing is offset 101 for `s1d` and 89 for `m1d` / `m1e`, the offset the selection ended at; no cursor callback followed the click, so the caret is still displayed at the end of line 1.

#### Instrument notes

- Reading the text inside a table: `.uno:SelectAll` selects only the cell contents the first time the caret is in a table cell, then the table, then the document (a debug run with the first version of the tool read back `S4 cell A#1 text` for S4, passes of 16, 65 and 670 characters). The tool repeats SelectAll until the text stops changing (at most 4 passes; `readPasses` in the raw output, e.g. `[16, 65, 670, 670]`). In a paragraph outside a table one pass is enough and the second changes nothing, so the old 12 arms read exactly as in the earlier round (36 of 36 equal).
- Before the evidence rounds the tool was run three times in a scratch directory to check navigation (Ctrl+Down), the read-back above, and the drag shapes; those outputs were not kept and are not evidence. The evidence rounds are the four folders above. Any other tool change is visible in the `tool-source-as-run.cpp` of each folder.
- The `emu` arms wait for 500 ms of quiet BEFORE reading the cursor rectangle and clicking (so late callbacks of the selection do not count as answers to the click); a user presses the key sooner. The `ref` arms use the old tool's timings (150 ms per key, 300 ms before the read).
- "Any callback within 400 ms" counts `MOUSE_POINTER`; the stricter set that, by my reading of `onLokCallback`, would advance the page's `sourceSequence` (`INVALIDATE_TILES`, `INVALIDATE_VISIBLE_CURSOR`, `TEXT_SELECTION` incl. empty, `TEXT_SELECTION_START/END`, `CURSOR_VISIBLE`) is counted separately in `summary.md` ("page-relevant (inferred)") and gives the same 306 of 306 because of the empty `TEXT_SELECTION`.
- Navigation to S2-S5 is by Ctrl+Down and is verified only through `made`: S1-S4 and the old shapes all matched their expected read-back (`madeMismatches_excluding_s5: []` in `analysis.json`); S5 and the extra shapes have no pre-written expectation (their read-backs are in the raw files and quoted above).
- Not covered: Shift-held variants, keys with Ctrl/Alt, RTL or mixed-direction text, a selection that spans pages, a click when the selection is a graphic or when the document is read-only, and everything on WASM (this is native LibreOffice only; WASM lays out with other fonts, so wrap offsets there will differ).

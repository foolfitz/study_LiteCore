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

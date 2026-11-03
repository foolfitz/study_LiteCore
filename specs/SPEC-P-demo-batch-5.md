# SPEC-P-demo-batch-5：不用連結的兩項修正

2026-11-03 擁有者無法手測，定順序：A 盤點、B 不用連結的修法、C ordered-commands。A 的結果在 `research/RESEARCH-2026-11-03-open-findings-census-0.2.52.md`。本文件是 B。判準實作前釘死，本文件只准 append。

## 1. 要修的兩件事

都只動 `web/e2-editor-app.js`，引擎仍是 `e2-editor-v32`，不用連結，要新的殼層 generation。

### 1.1 在選取上按 Enter 被拒絕（`L-enter-over-range`）

現況：選一段字按 Enter，頁面跳 `EDITOR_FORMAT_GESTURE_UNSUPPORTED` 的原始訊息，文件不變。原因：manifest 的 `insert-paragraph-break`、`insert-line-break` 只收 `collapsed`。

**這不只是提示醜，是行為錯。** Writer 的做法是刪掉選取再斷段（`sw/source/uibase/wrtsh/wrtsh1.cxx:1461-1474`，`SwWrtShell::SplitNode`），Word 相同。manifest 已經有 `delete-selection`（`range-single`、`range-cross`），所以頁面可以照做。

設計：

- 有選取時，頁面在**同一個 tick** 依序把 `delete-selection` 和換段動作送進 session 的佇列。不等第一個完成，否則 Enter 之後緊接著打的字會排到換段前面（finding 137 那一類）。
- Shift+Enter 走同一條路。
- 判斷選取用 `selectionShapeOf(...) ?? lastSelectionShape`，和 `dispatchDelete` 相同。
- 沒有 `delete-selection` 的舊 profile 維持原樣。

### 1.2 原始錯誤碼 `CLIPBOARD_EMPTY_SELECTION`（`L-complex-copy`）

`input/clipboard-adapter.js` 在選取文字為空時丟這個碼。含 as-char 框的範圍會碰到（`select-all-v26/s1`）；游標沒有選取時按複製也走同一條，要實測。`describeError` 加一句話，其他未知錯誤維持原文，那是除錯要用的。

## 2. 判準（連結之外的第一次執行之前釘死）

工具 `wasm_sdk_probe/tools/check_writer_enter_range.py`，鏡像，真實按鍵與指標，Chrome、Firefox，判讀存出的 ODT。

**P5 的主判準是量出來的對照，不是手寫答案**：對每一種選取形狀，「選取後按 Enter、打 `q`」存出的文件，要等於「選取後按 Delete、再按 Enter、打 `q`」存出的文件，而且對照組要和原文件不同。這是逐實例性質，新增形狀不用改判準。

- **E1 形狀**：同段一個字、從段落中間跨段、全選、標題內、清單項目內、含 as-char 框的範圍、單一表格儲存格內。
- **E2 Shift+Enter**：同上的對照，用 Shift+Enter，存檔有 `text:line-break`。
- **E3 游標**：沒有選取時 Enter 只送一個 `insert-paragraph-break`，沒有 `delete-selection`。
- **E4 順序**：有選取時請求順序是 `delete-selection`、`insert-paragraph-break`；Enter 與 `q` 間隔不到 20 ms，結果等於間隔夠長的那一臂。
- **E5 復原**：連按 Ctrl+Z 回到原文件。次數寫進報告，上限 2。
- **E6 session**：每一臂結束 session 都是 `ready`，沒有紅色提示。
- **E7 複製**：游標上複製、含框範圍複製，提示是中文句子，不含 `CLIPBOARD_EMPTY_SELECTION`，文件不變。
- **紅案**：同一工具在第 87 代的頁面上跑，E1 要紅。工具的紅不是由 mutate 造出來的，是真的舊頁面。

回歸（第 88 代）：S1、Z、P1、P4、C、F4、F3、V0′，單元與突變工具。引擎與 profile 不動，四個 pin 不變，改的是頁面與殼層 digest。

宿主（0.2.53）：Files 工作流、`HOST_BATCH_HOLDS`、`LAYOUT_HOLDS`、`host_batch5` 走真實按鍵存回 WebDAV 讀回。差異只有 `e2-editor-app.js`。

## 3. 具名限制

- `L-enter-range-two-undos`：Writer 把刪除與斷段包成一個 undo 群組（同上 `:1461`、`:1474`），這裡是兩個動作，復原要按兩次。動作清單是封閉的，頁面組不出群組，要改引擎才能合併。E5 量實際次數。

## 4. 如果永遠沒做

第 87 代維持原樣：在選取上按 Enter 看到原始錯誤碼，文件不受影響。

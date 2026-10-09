# 121 — 反白之後按 Backspace 或 Delete，被拒絕、什麼都沒刪，還跳出英文錯誤

| | |
|---|---|
| **狀態** | **已確認、未修**（2026-10-09）：擁有者手測 0.2.9 時回報；Chrome、Firefox 都重現，v57 的頁面也一樣（v19 cutover 起就是如此） |
| **所在** | 我們的頁面 `wasm_sdk_probe/web/e2-editor-app.js`：`beforeinput` 把 Backspace／Delete 一律對到 `delete-backward`／`delete-forward`，而這兩個動作在 v19 的合約裡只允許「沒有選取範圍的游標」 |
| **發現日** | 2026-10-09（擁有者手測） |
| **嚴重度** | 中：不丟資料、文件沒被改動，但「選取一段再刪掉」是最基本的編輯動作之一，現在做不到，而且錯誤訊息是給開發者看的英文 |
| **可重現** | 每次（任何選取範圍＋Backspace 或 Delete） |
| **是否上游** | 否 |

## 現象

選取一段文字（拖曳反白），按 Backspace 或 Delete：toast 寫「⌫ 刪除：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged」，選取的字沒有被刪。工作階段沒事、可以繼續編輯。

## 分析

- **已觀察**（`evidence/121/`）：選取形狀 `range-single` 時，Backspace 與 Delete 都被手勢檢查在送出之前拒絕；狀態 `ready`、世代不變、文件不變。v57 的頁面相同。
- **讀原始碼**：v19 的 `delete-backward`／`delete-forward` 只開 `collapsed`；`delete-selection`（id 20）開 `range-single` 與 `range-cross`，限制 `not-characterised-in-tables-or-note-apparatus`。頁面的剪下已經在 profile 提供時改用 `delete-selection`；鍵盤沒有。

## 處置方向

頁面的 `beforeinput` 在選取範圍不是游標、而且 profile 提供 `delete-selection` 時，改送 `delete-selection`（同剪下的判斷）。只動頁面，與 finding 120 的一行修法一起，走一次頁面發佈（殼層 v59、宿主 0.2.10、重新計數）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-09 | 初版：已確認、未修 |

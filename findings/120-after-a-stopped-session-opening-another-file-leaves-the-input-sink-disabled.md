# 120 — 工作階段停下之後，在 standalone 頁面用檔案輸入開另一份文件，輸入槽一直停用，打字完全沒反應

| | |
|---|---|
| **狀態** | **已確認、未修**（2026-10-09）：兩半都量到（停下時輸入槽被停用；開新檔不會把它打開），兩個瀏覽器一致。修法登錄、與下一次頁面發佈一起出 |
| **所在** | 我們的頁面 `wasm_sdk_probe/web/e2-editor-app.js` `openDocument`；成因在被 E1-C 綁住的輸入轉接器（`setBlocked` 寫 `disabled`，`detach`／`attach` 都不還原），所以修法只能在頁面 |
| **發現日** | 2026-10-09（finding 111 的擁有者文件量測，第 6 輪之後的 59 次試驗） |
| **嚴重度** | 低：**只有 standalone 頁面**有檔案輸入；宿主把它藏起來，換檔一定是整頁重新載入。不丟資料，但使用者會以為編輯器壞了 |
| **可重現** | 每次（停下的工作階段 → 用檔案輸入開下一份 → 打字） |
| **是否上游** | 否 |

## 現象

工作階段因錯誤停下（`recoverable-error` 或 `restart-required`）之後，不按通知、直接用「📂 開啟檔案」開另一份文件：文件開得起來、點擊能放游標，但鍵盤打的字一個都沒進文件。

## 分析

- **已觀察**：停下的那一刻輸入槽被停用（`evidence/fast-delete-recovery/chrome-same-page-1.json` 第 41 次，`sinkDisabled: true`）。
- **已觀察**：輸入槽一旦被停用，用檔案輸入開新檔、再點擊，它仍是停用、沒有焦點，打字不進文件；對照組正常（`evidence/120/`，Chrome 151、Firefox 157）。
- **讀原始碼**：`input-adapter.js` 的 `setBlocked` 寫 `target.disabled`；`detach()` 只拆監聽器；`attach()` 不同步 `disabled`；新的 session 在 `_openFresh` 裡呼叫 `setBlocked(false)` 時頁面還沒把輸入槽接上（`openDocument` 先 `session.open()` 後 `session.attachInput(el.sink)`），碰不到那個元素。轉接器與基礎類別都在 E1-C 的綁定裡。

## 處置方向

頁面在 `session.attachInput(el.sink)` 之後把 `el.sink.disabled` 同步成新轉接器的 `state.blocked`（一行）。動頁面＝新的殼層世代＋重新計數，所以不單獨發佈，排進下一次頁面發佈；那時加一條單元測試（開新檔之後輸入槽可用）與 `sink_probe.py` 的殘留組當瀏覽器紅案。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-09 | 初版：已確認、未修 |

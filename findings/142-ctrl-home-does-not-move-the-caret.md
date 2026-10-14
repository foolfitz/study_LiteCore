# 142 — Ctrl+Home（以及 Ctrl+End）不會把游標移到文件開頭／結尾；接著按 Backspace 會刪到游標原本所在處的字

| | |
|---|---|
| **狀態** | **已登錄，未修**（2026-10-14）。 |
| **影響版本** | 頁面一直如此（0.2.x 全部）；在 0.2.20 手測的診斷裡第一次被量到。 |
| **所在** | `web/e2-editor-app.js:2679`：按鍵處理遇到 Ctrl／Cmd 組合鍵就 `return`，頁面不處理；隱藏的輸入 textarea 自己吃掉這個鍵，文件游標不動。引擎沒有「移到文件開頭／結尾」的動作。 |
| **發現日** | 2026-10-14，任務 10-14n 的 `press-after-ctrl-home` 臂（`findings/evidence/host-0.2.20-hand-test/README.md`）：Ctrl+Home 之後按 Backspace，刪掉第一個標題裡的一個字（verified-selection-delete，revision 0→1）——刪的是游標**實際**所在處，不是文件開頭。 |
| **嚴重度** | 中低：引擎刪的是畫面上游標所在的位置，行為本身一致；但使用者以為自己在文件開頭，會刪到不想刪的字。 |
| **可重現** | 每次都重現（Firefox、Chrome）。 |
| **是否上游** | 否 |

## 修法方向（提出，未裁決）

正解要引擎動作（`move-document-start`／`move-document-end`），進下一批連結；紅案＝`press-after-ctrl-home` 臂必須讀成邊界 no-op。連結之前的過渡選項（頁面攔下 Ctrl+Home／End 並提示「尚不支援」，或用既有動作組合模擬）未評估。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-14 | 登錄 |

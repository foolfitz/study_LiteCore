# 136 — 在表格儲存格尾端按 Delete 被拒、自動重開之後，游標被放回「下一格」，接著打的字落在別的儲存格

| | |
|---|---|
| **狀態** | **已確認，未修**（2026-10-13）；擁有者離座，交 fable 裁決處置 |
| **所在** | 我們的頁面 `wasm_sdk_probe/web/e2-editor-app.js`（`6470dec0…`）的 D（finding 134）：`reopenAfterBoundaryRefusal` 在 `restart()` 之前讀「引擎最後回報的游標」；觸發者是引擎的 merge-key barrier：`probe_engine.cpp:3600-3612` 圍欄不過時，在 K1 的一格選取還在的情況下直接回報 `anchor-mismatch` |
| **發現日** | 2026-10-13（`evidence/134/table/` run-2 與預測不符，run-3 用對照字確認） |
| **嚴重度** | 一般：字打進了別的儲存格，看得到（游標畫在那裡），不丟資料。比 0.2.15 輕（0.2.15 把游標放到文件開頭） |
| **可重現** | 兩個瀏覽器各 1/1（run-2）＋ 各 1/1（run-3，對照字） |
| **是否上游** | 否 |

## 現象（已量）

E1 的 `table-boundary.odt`（一段、2×2 表格、一段）：游標到儲存格 A1 尾端，先打 `kj`，按一次 Delete → 被拒（「這裡目前還不能這樣刪除」）→ 自動重開 → 打 `zqx` → 存。伺服器上：`kj` 在 A1，`zqx` 在 **B1**。提示沒有說游標換了位置（D 回報成功）。

同一份文件、表格前一段的段尾按 Delete（被拒的形狀是「送出了但沒能確認」）：`kjzqx` 相連在第 0 段＝D 放回原位，沒有這個問題。

## 成因（讀碼，引擎內部未量）

D 讀的是 `restart()` 之前 session 裡「引擎最後推送的狀態」（裁決 ruling-1 條件 2 就是這樣寫的）。儲存格尾端的 Delete 走 merge-key barrier：K1 先把選取往後延一格（跨進 B1），`startMergeKeyUndo` 圍欄不過，**沒有先送 `.uno:Escape` 收回選取**就以 `anchor-mismatch` 結束。所以最後推送的狀態裡游標已在 B1。文件兩端（`nothing-selected`）什麼都沒選到，兩者重合，所以 134 的驗收看不到這個。

## 證據

- `evidence/134/table/README.md`（預測、run-1 正向對照失敗、run-2、run-3）、`run-2/report.json`、`run-3/report.json`。

## 處置方向（交裁決）

- 頁面：D 改用「送出這一下刪除當下」的游標（在 `beforeinput` 送出前記下引擎回報的游標），而不是 barrier 動過之後的；文件兩端兩者相同，表格儲存格尾端才不同。
- 引擎：`anchor-mismatch` 之前先收回 K1 的選取（連結批次）。
- 或只登錄為具名限制，等擁有者。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-13 | 登錄（量測 run-2、run-3；成因讀碼） |

# 119 — 在大文件上打完字立刻按 Backspace，刪除偶爾失敗，而唯一的出口丟掉上次存檔以來的內容

| | |
|---|---|
| **狀態** | **已確認、未修**（2026-10-09）：兩次重現，都在 Chrome、都在擁有者文件、都是同一頁開過幾十份文件之後；成因的機制讀原始碼，下一層（callback 為什麼遲到）未量 |
| **所在** | 我們的引擎與殼層：selection barrier 的負向期限（`wasm_sdk_probe/src/probe_engine.cpp` 約 :3888）回 `EDITOR_STATE_UNAVAILABLE`；殼層把這個代碼判成 rollback（`editor-shell-v2/paragraph-editor-client.js` `formatFailureDisposition` 的預設），擋住佇列、刪除之前沒有檢查點 |
| **發現日** | 2026-10-09（finding 111 的擁有者文件量測裡意外碰到，之後用專門的探針重現） |
| **嚴重度** | **高（資料遺失）**，但頻率低：同一頁連續快刪約四十到六十次一次；每次換新頁的 60 次一次都沒有 |
| **可重現** | 偶發：同頁 1/41（`evidence/fast-delete-recovery/chrome-same-page-1.json`）、111 那輪同頁第 61 份文件 1 次；換新頁 0/60。Firefox 未量 |
| **是否上游** | 否 |

## 現象

在擁有者那份 563 KB 的文件裡，打兩個字、幾乎同時按 Backspace（按鍵間隔約 1 ms）。大多數時候結果只是 111 的插隊；偶爾刪除直接失敗：
toast 寫 `⌫ 刪除：EDITOR_STATE_UNAVAILABLE：selection text became visible without its required typed callback; no mutation was dispatched; start a fresh Worker（可能已經改到文件：請回到檢查點）`，
狀態變成「需要回復」，工具列（含儲存）全部停用，通知說「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來」，唯一的按鈕是「重新開啟」。
按下去，文件回到上次存檔的樣子——**打的字不見了**。

## 重現步驟（`wasm_sdk_probe/tools/probe_fast_delete_recovery.py --browser chrome --same-page`）

1. 出貨的 standalone 頁面（`dist/`，頁面 `e00ab76a…`，v19），同一頁反覆用檔案輸入開擁有者的文件；
2. 每次：點標題「一、序言」尾、End，真鍵 `X`、`Y`、Backspace 一起按；
3. 第幾十次會碰到。

**預期**：刪掉一個字；就算刪除做不到，打過的字也要留著。
**實際**：`recoverable-error`，存不了，唯一的出口丟掉打的字。

## 證據

- `evidence/fast-delete-recovery/PREDICTION.md`（預測與每一輪的結果）、`chrome.json`（換新頁 60 次 0 失敗）、`chrome-same-page-1.json`（第 41 次重現）。
- `evidence/111/browser/owner-chrome.json`（第一次：第 6 輪 Backspace／0 ms）。
- 第 41 次那一筆：修訂 1（X 已進文件）、檢查點「無」、儲存鈕停用而且按了沒有位元組、通知 `rescue: none`；按「重新開啟」之後世代 2、修訂 0，存出的第一段是「一、序言」——**沒有 X**。

## 分析

- **讀原始碼**：Backspace 走 selection barrier（先往回選一個單位、驗證、再刪）。單位的選取若在 250 ms 負向期限之後才以文字出現、卻沒有它該帶的 typed callback，引擎回 `EDITOR_STATE_UNAVAILABLE`，訊息自己說「no mutation was dispatched」（`probe_engine.cpp` `finishSelectionBarrierError` 帶 `viewRecoveryRequired`）。
- **讀原始碼**：這個錯誤沒有 barrier 細節欄位，`recoveryFor` 走到 `formatFailureDisposition` 的預設 → `rollback` → `_blockQueueIfDispatched` 把佇列擋成 `recoverable-error`（`narrow-editor-v2-session.js` 約 :716）。109 的修法（拒絕當下存檢查點、自動重開）只認 `EDITOR_BOUNDARY_UNSUPPORTED`。所以這裡沒有檢查點、存檔被擋，出口只剩上次存檔的位元組。
- **推論（未量）**：callback 遲到是因為引擎還在處理剛貼進去的字——插入在 paste 一送出就回覆（`narrow-editor-v2-session.js` 約 :254 的註解），大文件上 LOK 處理那次貼上的時間比較長，緊接著的 barrier 就等不到。只在「同一頁開過很多文件」之後才出現，可能與引擎的累積負擔有關，**沒量**。
- 111 的修法（讓刪除等前面的字）**不會**消除它：刪除照樣緊跟在最後一個字的貼上後面。

## 附帶量到的（同一份證據）

- 按「重新開啟」之後**不點擊**直接打 `Q`，沒有進文件（修訂 0 → 0）。推論：這條回復路徑沒有把焦點還給輸入槽（109 的重開有修，這條沒有）。
- 111 那一輪在失敗之後**沒按通知**、直接用檔案輸入開下一份文件：之後 59 次的打字全部沒有進文件。這一次的探針先按了通知再開檔，打字就正常。只有 standalone 頁面有檔案輸入（宿主把它藏了），**未區辨**。

## 裁決（2026-10-09，fable 依擁有者授權代為決定；原文 `evidence/fast-delete-recovery/ruling/fable-ruling.md`）

**D：現在先做殼層修法（比照 109），引擎的根因登錄為待辦；111 的修法同一次發佈一起出。**白話理由（fable 原文摘錄）：

- 這是資料遺失：引擎拒絕了刪除，殼層卻當成「可能改壞了」擋住佇列，唯一出口是上次存檔，打的字就沒了。
- 修法跟 109 同一個模子：拒絕那一刻先把引擎裡的內容存成檢查點，再自動重開——打的字全留，代價是重開約兩秒、游標回開頭。
- 不選「每次要回滾都先存檢查點」：那會把「可能已經改壞」的內容重開回來，等於為了一個代碼改掉所有回滾的意思。
- 不現在改引擎：要連結、要整套重驗，而且 callback 為什麼晚到還沒量；先登錄，量了再修。
- 措辭不能說「文件沒有被改動」：引擎四個出口裡有一個理論上在送出之後（實際幾乎到不了），要說「這一下刪除沒完成，內容已先保住」。
- 驗收：單元測試先紅再綠；瀏覽器用同頁探針跑到自然出現至少兩次、每次字都留著、不點擊就能打字；不到兩次就由「注入同一個錯誤」的臂扛，並寫明自然路徑沒量到實例。

**我對 fable 推翻我的那條事實的核對**：成立（見原文末段）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-09 | 初版：已確認、未修；兩次重現、資料遺失量到 |

# SPEC-P-key-burst：Writer 連打不掉字（finding 130 的上限）

2026-11-05 擁有者在欄列標號做完、選「先不發布」之後，挑了 B（Calc 插入／刪除欄列）和 D（Firefox 連打掉字）。本文件是 D。判準實作前釘死，本文件只准 append。

## 1. 現況

- 輸入 adapter（`input/input-adapter.js`）一個字一個 commit，前一個 commit 回來才送下一個；排隊上限 8（`DEFAULT_MAX_QUEUE_DEPTH`），第 9 個起 `INPUT_BACKPRESSURE`，字就沒了（0.2.57 起會跳「有字沒有輸入：打得比引擎處理得快」）。
- 0.2.56 實測（`findings/evidence/host-0.2.56/diag-burst-01/`）：背靠背 10 鍵掉最後 2 鍵、14 鍵只留前 8 鍵，Chrome 與 Firefox 都一樣；每鍵 150 ms 不掉。擁有者說的「Firefox 連打掉字」就是這個，兩個瀏覽器都有。
- adapter 被 E1-C 的殼層 bundle（`e1/editor-shell-bundle-v2.json`）逐位元組綁著。改它，E1-C intact 的發布閘門就轉紅；要轉回綠，得重做 E1-C 的人工驗收或再造申報機制（〈驗收判準的形式〉§4 不造機械）。E1 的頁面已不出貨。

## 2. 設計

在殼層 v2（`editor-shell-v2/narrow-editor-v2-session.js`）裡，對 session 自己的 adapter **實例**包一層：

1. **合併**：新來的打字若可合併，而佇列尾端（還沒送出的那一筆）也是可合併的打字，就把字接到尾端那一筆，不另排一筆。送出中的那一筆不動。
2. **可合併**＝`source: "beforeinput"`、`inputType: "insertText"`、不含 `\n`、`\r`、NUL（SDK 的 typed 路線，`.uno:InsertText`），同一個 generation，合併後不超過 adapter 的位元組上限。換行、輸入法、貼上、`insertReplacementText` 都不合併，照舊一筆一筆。
3. **封口**：session 收到任何不是打字的操作（`_enqueue` 的 label 不是 `commit-text`），佇列裡現有的每一筆都封口，之後的字另起一筆。finding 111 的「鍵等在它前面打的字後面」靠 request 編號當界線，封口讓界線兩邊的字不會被併在一起。
4. 被併進去的那個字，它的 promise 跟著那一筆一起成功或失敗（取消、錯誤都一樣）。
5. 上限 8 不改：它現在只管不能合併的項目（換行、輸入法、貼上、被封口隔開的段）。

依賴 adapter 的私有欄位（`_queue`、`_requestCount`、`_generation`、`_blocked`、`_maxUtf8Bytes`、`_trace`），與本檔開頭說明的既有作法相同：用單元測試釘住，而不是假設。

## 3. 判準（實作前釘死）

鏡像：dist/ 加上要量的 session 原始碼（頁面不變），observer 記錄送到引擎的每個請求。真實按鍵（`tools/v21_input.py`：Chrome CDP、Firefox WebDriver），Chrome 與 Firefox，每格一份新開的 `test-docs/t1-plain-zh.odt`，點第一段、Home，打完等引擎靜下來，按工具列「儲存」，讀存檔的 Blob。

- **K1 連打**：背靠背 14 鍵與 40 鍵（`v21_input.chain`，小寫字母、數字、空白）。存檔的第一段＝打的字＋原本的第一段，其他段不變。
- **K2 按住的速度**：60 鍵、每鍵間隔 30 ms（`v21_input` 的按住重複間隔）。判準同 K1。
- **K3 順序**：背靠背 `abc`、Backspace、`de`、ArrowLeft、`x`。存檔的第一段＝`abdxe`＋原本的第一段。
- **K4 沒有提示**：K1–K3 的每一格，頁面都沒有跳「有字沒有輸入」。
- **K5 真的有塞車**：K1 的 40 鍵那格，送到引擎的 `insertText` 請求數小於 40（合併真的發生，不是引擎剛好跟得上）。
- **K6 復原的範圍與慢打相同**：打 `ab cd ef gh`，一臂背靠背、一臂每鍵 150 ms（參考臂，不會塞車），各按一次 Ctrl+Z 再存檔。兩臂存檔的第一段相同。復原的粒度用實量的慢打當參考，不手寫。

**紅案**（各自一份報告，紅在指名的格才算）：

- **基準**：dist 現有的 session（generation 90）。K1 兩格必須紅（掉字），否則這個量測沒有鑑別力。
- **突變 `no-seal`**：拿掉 `_enqueue` 裡的封口。K3 必須紅。
- **突變 `no-merge`**：合併條件永遠不成立。K1 必須紅。

單元測試（node）：合併、封口、換行／輸入法／貼上不合併、位元組上限、取消與錯誤傳給每個被併的字、finding 111 既有測試不變。

判定：`KB_HOLDS`＝兩個瀏覽器 K1–K6 全過；紅案各自紅在指名的格。

## 4. 具名限制

- 換行、輸入法、貼上不合併：按住 Enter 若比引擎快，上限 8 照舊會擋（K2 只量字母）。
- 頁面的 held deletes（v21 §10.3）在打得比引擎快時，原本就有「連按兩次 Backspace 之後緊接著打字」的順序邊角：第二個 Backspace 在下一筆打字排入時才送出，界線落在它之後打的字後面。合併前就存在，本批不修，K3 只放一個 Backspace。
- 發布時，按請求數計數打字的回歸工具若用背靠背按鍵，請求數會變少；那是判讀工具要跟著改（〈節奏〉4），不是產品退化。

## 5. 如果永遠沒做

連打超過 8 鍵，第 9 鍵起照丟，頁面會跳提示（0.2.57 的現況）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-11-05 | 初版：判準 K1–K6、三個紅案，實作前釘死 |

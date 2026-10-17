# 154 — 宿主 0.2.25 上，關著的「貼上為 Markdown」對話框一直顯示，蓋住編輯器、吃掉點擊

| | |
|---|---|
| **狀態** | **已確認**（量測、反事實，兩個瀏覽器都做過）；修法待擁有者裁決 |
| **影響版本** | **宿主 0.2.25**：v21 頁面 `605cf24b…`、`e2-editor.html` `1d158149…`、engine 封包 `f5f0df762e1855f2`。0.2.24 沒有這個問題（它的頁面沒有對話框）。無宿主的 mirror 也沒有，因為那裡沒有 Nextcloud 的 CSS |
| **所在** | `wasm_sdk_probe/web/e2-editor.html` 的 `<dialog id="markdown-dialog">`：v21 part S（`bc6534e0`）新增，關著的時候不顯示，靠的是瀏覽器內建的 `dialog:not([open]) { display: none }`。Nextcloud 34 `core/css/server.css` 有舊式 HTML5 reset：`article, aside, dialog, figure, footer, header, hgroup, nav, section { display: block }`。它是作者樣式，會蓋過內建規則。宿主 `EditorController::editor()` 把頁面的 body 原樣放進 `#litecore-editor-root`，Nextcloud 的 CSS 因此也套到對話框上 |
| **發現日** | 2026-10-17：D2 宿主臂在 0.2.25 上 6/6 NE（`findings/evidence/link-batch-v21/shakedown/evidence/d2/d2-host-v21-*.json`）→ 診斷 `findings/evidence/154/` |
| **嚴重度** | **宿主上的編輯器不能用滑鼠放游標**。對話框固定蓋在編輯器左上角（Chrome 框 `[8, 50, 640, 335]`，視窗 1850×980），工具列左半和文件開頭都被蓋住。被扣住的第 2 項，它的 UI 因此出現在使用者面前 |
| **是否上游** | 否。是我們的頁面依賴了瀏覽器內建樣式，而宿主環境的 CSS 會蓋過它 |

## 量測（宿主 0.2.25，headless；Chrome 151、Firefox 157）

| 讀什麼 | 照出貨的頁面 | 同一頁只多加一條 `#markdown-dialog:not([open]) { display: none }` |
|---|---|---|
| 對話框 `open` | false | false |
| 對話框計算後的 `display` | **block**（`position: absolute`） | none |
| 設定 `display` 的規則 | `css/server.css`：`article, aside, dialog, …` → block | 同左，外加加上的那一條 → none |
| D2 臂第一行點擊點（620.5, 295.3）底下的元素 | **`TEXTAREA#markdown-text`**（在對話框裡） | `CANVAS#canvas` |
| 在那裡真的點一下 | **沒有 `editorPlaceCaretV2`** | 送出 `editorPlaceCaretV2`，標籤出現「定位游標」 |
| 第 2 項入口按鈕 `button[data-action="paste-markdown"]` | `hidden`、`display: none`（照設計） | 同左 |

兩個瀏覽器的讀數相同（`diag-154-chrome-20261017T170402.json`、`diag-154-firefox-20261017T170449.json`）。截圖：`as-shipped-chrome.png`、`with-rule-chrome.png`。

D2 宿主臂（`run_v21_d2.py --mode host --page v21`，N=3，兩個瀏覽器）：6/6 輪點了第一行之後，等滿 40 秒都沒有定位游標。之後的 Ctrl+Home 和 Backspace 都沒有送出任何請求，兩次存檔也都逾時。

## 為什麼之前所有證據都沒看到

v21 的證據執行全部在 mirror 上跑（無宿主），包括 `v21host` 變體。`v21host` 只是假的 `liteCoreHost`，沒有 Nextcloud 的頁面與 CSS。E0 量的是「入口按鈕存在、隱藏、沒有別的開啟者」，只量了按鈕，沒有量對話框本身。這是「harness 的路不是使用者的路」又一次：只有真的宿主臂走到使用者那條路。

## 推論，未量

- 對話框的「取消」大概關不掉它：`HTMLDialogElement.close()` 對沒開的對話框不做任何事，而顯示它的是 CSS，不是 `open`。〔推論〕
- 任何嵌入這個頁面、而且 reset 裡有 `dialog { display: block }` 的宿主都會遇到同樣的事。〔推論〕

## 修法選項（待裁決）

- **宿主那一側**：`templates/editor.php` 加 `#litecore-editor-root dialog:not([open]) { display: none }`，出 0.2.26。engine 封包、頁面、HTML、殼層都不動。
- **頁面那一側**：`e2-editor.html` 加 `#markdown-dialog:not([open]) { display: none }`。engine 封包會變（新的 buildId），宿主出 0.2.26。

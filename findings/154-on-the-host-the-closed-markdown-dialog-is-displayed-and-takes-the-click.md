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

## 裁決（fable 裁決 3，2026-10-17，擁有者交裁；原文 `findings/evidence/link-batch-v21/shakedown/review/ruling-fable-3.md`）

**選 A：修在宿主**，出 0.2.26：`templates/editor.php` 宿主自己的 `<style>` 加 `#litecore-editor-root dialog:not([open]) { display: none; }`。engine 封包、頁面、HTML、殼層都不動。

白話理由（fable 寫給擁有者）：這是 Nextcloud 的全域樣式蓋過了瀏覽器內建的「關著的對話框不顯示」，問題在宿主這一層，而宿主本來就在同一個檔案裡用同樣的方式藏頁面的其他部件。改頁面會換掉 HTML 和 engine 封包，已經跑完的第 1 項十二份報告記的 HTML 就對不上要出貨的那一份。

**修法的驗收（本 finding 自己的判準）**：
- 紅案：0.2.25 上的兩次讀數（`diag-154-chrome-20261017T170402.json`、`diag-154-firefox-20261017T170449.json`）。
- 綠：用同一支診斷工具（不改）在 0.2.26 上讀 `asShipped`。規則要出現在設定 display 的清單裡；對話框 `display: none`；點擊點底下是 `CANVAS#canvas`；送出 `editorPlaceCaretV2`；兩個瀏覽器都要過。
- 若沒做：D2 不跑，第 1 項不出貨。

**下一批（v22）的工作項**：
1. 頁面那一側也補一條 `#markdown-dialog:not([open]) { display: none }`。第 2 項真的出貨時，它的宿主判準要量對話框**關著**（不顯示、點擊點底下沒有它）與**打開**兩種狀態。server.css 的 reset 也把 `dialog` 的 `margin` 設成 0，打開時可能不在畫面中央，而是貼在左上〔由 CSS 推論，未量〕。
2. 宿主 production-UI 臂加一份由 DOM 列舉的檢查：讀所有隱藏部件計算後的 display（判準形式二）。第一次計入之前，先依 §34.3 審核一次。

**只登錄、不寫程式**：D2 的 NE 原因（「no Backspace response」）沒有帶點擊點的酬載，所以才另外需要一支診斷工具；`HOST_EXPECT` 沒有釘 buildId。

**修法驗收：通過（2026-10-17 追加；fable 裁決 3 補充 1）。** 宿主 0.2.26（`3c01876`）上，兩個瀏覽器用同一支診斷工具讀到：
- 關著的對話框 `display: none`，宿主那條規則在清單裡；
- 點擊點底下是 `CANVAS#canvas`；
- 點下去送出 `editorPlaceCaretV2`。

報告在 `findings/evidence/154/0226/`。

工具的第二臂（`withRule`）在 Chrome 讀早了，原因是延遲標籤還留著第一次點擊的「定位游標」。這一句判準撤回，具名 L-154-diag-second-click。v22 若要再用這個反事實的形狀，`measure()` 要改成點完之後等 `state == "ready"` 且 `pending == "0"`（或等標籤改變）才讀紀錄，並把 `0226/diag-154-chrome-20261017T181633.json` 當成紅案。

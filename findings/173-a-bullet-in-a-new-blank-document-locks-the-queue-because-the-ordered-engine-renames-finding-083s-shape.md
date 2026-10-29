# 173：新的空白文件按項目符號，佇列被鎖、要求「引擎需要重新開啟」——有序引擎把 finding 083 的情況改了名字，頁面不認得

| | |
|---|---|
| **狀態** | 已確認／**已修（頁面，殼層 generation 79），宿主 0.2.41 已裝（2026-10-29 23:52），待擁有者手測** |
| **Bugzilla** | —（本樹缺陷） |
| **發現日** | 2026-10-29（擁有者在宿主 0.2.40 上手測回報） |
| **嚴重度** | 中——使用者可見：新文件第一個動作按項目符號，就跳出「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來」，按下去整份重開 |
| **可重現** | v24、v25：兩臂（開檔後直接按／先點進段落再按）都重現。v22（0.2.38 的引擎）：0 次 |
| **首次出貨** | 宿主 0.2.39（v24）；0.2.40（v25）仍在；**0.2.41 修正** |

## 現象（`findings/evidence/173/run-02/`）

用宿主自己的空白範本（`blank/en-US_zh-TW_A4.odt`，zh_TW 使用者拿到的那一份），從頁面的開檔入口打開，按項目符號：

| 產品 | 失敗形狀 | dispatched（引擎紀錄／頁面） | 頁面 |
|---|---|---|---|
| v22 | `stage-deadline:awaiting-selection` | 沒送／true（推算） | 留在 `ready`，提示「動作已送出，但這一段是空的…這是檢查的極限」 |
| v24 | `select-text-returned-none` | 沒送、stage `idle`／false | `recoverable-error`，「引擎需要重新開啟」 |
| v25 | `select-text-returned-none` | **true**、stage `awaiting-result`／true | `recoverable-error`，「引擎需要重新開啟」 |

〔實測〕

## 機制（讀碼＋上面的量測）

1. 頁面的處置（`editor-shell-v2/paragraph-editor-client.js` `formatFailureDisposition`）只對兩種「已送出、但檢查無法核對」的形狀讓佇列保持開著（`dispatched-unverified`，可以按復原）：`multi-block-readback`（finding 046，文件中間的空行，選取溢到下一段）與 `stage-deadline:awaiting-selection`＋`selectionResultSeen`（finding 083，空段落的 `.uno:SelectText` 什麼都沒選到）。其他已送出的失敗一律 `dispatched-rollback`。
2. v23 起的有序引擎，把 083 的同一個情況改用新名字回報：`ordered_format.inc` 的 `finishOrderedFormatReadback` 在同步讀到的選取類型是 `LOK_SELTYPE_NONE` 時，回 `select-text-returned-none`。頁面不認得 → `dispatched-rollback` → 佇列鎖住；新文件沒有檢查點 → 「引擎需要重新開啟」。
3. v24 上是 171（`dispatched: false`）把它帶到同一個提示；v25 修好 171 之後 `dispatched` 變成 true，接著撞上這條缺的分支。
4. 文件中間的空行會選到下一段（`multi-block-readback`），F1／F3 量的就是那一種；**整份空白文件沒有下一段**，沒有任何檢查涵蓋這條路。

〔讀碼，與實測一致〕

## 普查（只列出，不外推）

有序路徑還能送出 `selection-type-not-readable`、`footnote-apparatus-readback`、`unknown-structural-tag`、`malformed-readback-nesting`、`block-extraction-failed`、`postcondition-not-met`，頁面對它們都是 `dispatched-rollback`。v22 在對應情況下是不是讓佇列開著，**沒有量**。

## 修法方向（未決定）

- 頁面（不用重新連結）：在 083 那條規則裡，把有序引擎的同名形狀 `select-text-returned-none` 也算進去（同樣要 dispatched、collapsed、`selectionResultSeen` 三個條件），提示也用 083 那句。動到 generation 78 的殼層檔與頁面 → 殼層 generation 79、新頁面雜湊、宿主 0.2.41。
- 回歸網：加一個「新空白文件＋項目符號」的檢查，v25 現況必須紅。

## 證據

`findings/evidence/173/`（重現工具 `blank_bullet.py`、`run-02/report.json`、README）。

## 修法（2026-10-29，規格 `specs/SPEC-M3-shell-v79-finding-173.md`）

上面「修法方向」的頁面那一條照做，處置規則與提示句改讀**同一份**清單（`paragraph-editor-client.js` 匯出的 `EMPTY_SELECTION_SHAPES`，只有 083 的兩個名字），083 的另外三個條件不變；其他有序形狀照舊 rollback（v22 是否讓它們開著沒有量）。「回歸網」那一條是 B1（`tools/check_v79_blank_bullet.py`）：擁有者那條路、真的滑鼠與按鍵、讀存檔，修法之前的產品必須「為 173 而紅」。

〔實測〕B1 `B1_HOLDS`（after 12/12 PASS、before 12/12 為 173 而紅，Chrome 與 Firefox）；F3-79 與 v25 run-02 逐格相同（46/46 × 2）；F4-79 24/24；宿主 0.2.41（引擎 `829a988e199ebc43`）已裝、Files 實流程 52/52。證據：`findings/evidence/shell-v79-173/`、`findings/evidence/host-0.2.41/`。

宿主那條路（Files「＋新增 → 新文件」）只有擁有者的手測量得到（規格 §6 L-mirror-open-route）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-29 | 初版（未修） |
| 2026-10-29 | 狀態改為已修、加「修法」節（generation 79、宿主 0.2.41） |

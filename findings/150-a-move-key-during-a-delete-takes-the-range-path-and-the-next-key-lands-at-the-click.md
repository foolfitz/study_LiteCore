# 150 — 刪除還在途時按移動鍵，頁面把 barrier 的選取當成使用者的範圍，接著按的鍵落在點擊處

| | |
|---|---|
| **狀態** | **已確認（量測），待裁決**（2026-10-17 凌晨；擁有者授權 fable 代為裁決） |
| **影響版本** | **0.2.24（名義出貨版）就有**，透過方向鍵；v21 未計數候選另外透過 Ctrl+Home／End |
| **所在** | 頁面 `web/e2-editor-app.js`：方向鍵的範圍路徑（約 `:3192-3197`，finding 129）與 v21 的 `sendDocumentMove`（約 `:3330-3333`）用 `selectionShapeOf(引擎推來的狀態)` 判斷「在範圍上」，**沒有** `deletesInFlight === 0` 這個條件。finding 131 的規則 A（`deleteActionFor`，約 `:2787`）、132 的畫法（`overlayEditorState`，約 `:1766`）、136 的重開游標都已經套用它 |
| **發現日** | 2026-10-17，v21 shakedown item 1 smoke 的 D8 (e)（product red）；`findings/evidence/link-batch-v21/shakedown/diag-dirty-move/` V6／V6e 量出 0.2.24 也有 |
| **嚴重度** | **刪錯字**。前提：連按兩下刪除鍵之後在 60 ms 內按移動鍵，再接著按刪除鍵 |
| **可重現** | V6e：v21 與 0.2.24、Chrome 與 Firefox 都是 3/3 |
| **是否上游** | 否 |

## 機制（讀原始碼，量測佐證）

1. 頁面送出的刪除還在途時，引擎的 barrier 先選取要刪的那一個字，並把這個範圍當成一般的編輯器狀態推給頁面。
2. 這時按下移動鍵，頁面讀到的形狀是「範圍」。profile 只把這些移動給收合的游標用，所以頁面走 finding 129 的「先在點上點一下、再移動」。
3. 點擊先排進佇列，移動要等點擊回覆之後才排。這中間按下的刪除鍵就排在兩者之間，於是刪在點擊處。

量測（`diag-dirty-move/` V6e：從「Bravo|」，Backspace @0、Backspace @20、→ @40、Delete @60）：

- 照按鍵順序應得 P2「Bra econd paragraph」。
- v21 得到「Bra scond paragraph」。請求順序：`delete-backward` ×2 → `editorPlaceCaretV2` → `delete-forward` → `save` → 移動。
- 0.2.24 得到「Brasecond paragraph」：點擊在第二下 Backspace 送出之前就出去了。

各 3/3，兩個瀏覽器相同。

V6（只按一下 Backspace，→ @20、Delete @40）在兩個頁面都沒有走點擊路徑、結果正確。為什麼多一下 Backspace 就會觸發，沒有建立。當時頁面讀到的形狀沒有記錄。

## 與 finding 137 的關係

137 是「核心還沒執行的鍵後面，接著的指令落在錯的狀態上」，前提是核心停頓，量不到。150 不需要核心停頓：頁面自己讀錯了形狀。修法是把 131 的規則 A 用到這兩處判斷，不是「等一下再送」的時間規則（137 裁決 4 禁止的那種）。

## 候選修法（量測中，`diag-dirty-move/` V10）

兩處判斷都加上 `deletesInFlight === 0 &&`（只在 mirror 套用的頁面補丁）。

## 裁決

（待 fable。）

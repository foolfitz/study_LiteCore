# 086 — 把真實文件裡一個普通段落設成標題，格式屏障判不出結果，出貨的 profile 與候選都一樣

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | tdf#______（送出後回填） |
| **發現日** | 2026-09-03 |
| **嚴重度** | 嚴重 |
| **可重現** | 兩支臂各 1/1（使用者實測）；harness 尚未重現，見「分析」 |
| **是否上游** | **未確認** ← 屏障是我方的，但它判不出結果的成因可能在核心 |

## 現象

在一份**真實的**訪談稿上，把游標放在一個普通的內文段落裡，按產品自己的「標題」按鈕，
session 進入 `recoverable-error`，並要求使用者回到檢查點或重新開啟文件。

**出貨中的 `e2-editor-v8` 與候選 `e2-editor-v12` 都會發生**，但倒在屏障的不同關卡上。
在出貨那一支上，處方是「重新開啟文件」而且**沒有檢查點**——依產品自己的說法，
「自上次儲存以來的內容不會回來」。

這是使用者在 v12 cutover 閘門的人工輪（條件 3）第 3 格按下去就遇到的，不是特意找出來的。

## 重現步驟

1. 開啟 `e20-專訪瓦特老師.odt`（35 段真實散文，段落文字**無重複**，已用程式碼核對）
2. 把游標點進第 5 段（index 4），開頭「在那之前，我的資訊能力…」
3. 按工具列的「標題」

**預期**：該段變成標題。
**實際**：`MUTATION_OUTCOME_UNKNOWN`，session 進 `recoverable-error`。

## 證據

`evidence/086/OPERATOR-REPORT.md`（兩支臂的完整狀態讀值）

出貨的 `e2-editor-v8`（頁面 `28e03e5b…`）：

```
toast : 標題：MUTATION_OUTCOME_UNKNOWN：the paragraph selected for the
        postcondition read does not cover the caret this action was dispatched from
notice: 引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。
state : recoverable-error
```

候選 `e2-editor-v12`（頁面 `3dfdcfef…`）：

```
toast : 標題：MUTATION_OUTCOME_UNKNOWN：the postcondition read describes a
        different paragraph from the one this action was dispatched on
notice: 這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。
state : recoverable-error   checkpoint: 有（r1）
```

## 分析

兩支臂倒在**同一個屏障的不同關卡**上，而關卡的先後順序解釋了差異
（`src/probe_engine.cpp`，判定路徑）：

1. `readback-is-a-different-paragraph`——指紋比對，比的是
   `gEditorState.a11yContentHash`。**這個值來自 a11y**，所以只有 a11y 的 build
   走得到這一關。
2. `selection-does-not-contain-restore-point`——涵蓋檢查，在指紋比對之後。

出貨那一支沒有 a11y，指紋那一關被跳過（`paragraphIdentityChecked` 為 false），
於是它倒在涵蓋檢查上。候選過得了涵蓋檢查，倒在指紋比對上。

**指紋為什麼會對不上，有一個說得通但尚未驗證的解釋**：指紋是
「把 `listPrefixLength` 個字元剝掉之後的內容雜湊」，而**受測的動作正好會改變
`listPrefixLength`**——派送時那段是內文（前綴 0），讀回時它已經是標題（前綴非 0，
finding 074 說 LOK 對大綱編號標題回報的這個長度有問題）。同一個段落，兩個數字。
**這是假說**：本輪沒有取到兩端的指紋原始值，取到之前不得寫進上游報告。

**兩件事已排除**：段落文字重複造成的指紋碰撞（該文件 35 段零重複，已核對）；
以及空段落（finding 083 的形狀，該段有字）。

**回歸網為什麼沒抓到**：`format-a-paragraph-changes-that-paragraph` 在八筆已押的
soak run 上全過，它驅動的是 `list-contexts.odt`——**九段的合成語料**，段落短、結構
簡單。使用者那份是 35 段、每段數百字的真實散文。**網子是綠的，因為語料造不出這個
缺陷需要的狀態**——那不是網子錯了，是語料就是語料。

**這是這棵樹第三次記下同一個形狀**：harness 的路不是使用者的路，而使用者是唯一
不共用 harness 判讀工具的觀測者。

## 對 v12 cutover 的意涵

**這不是退步，兩邊都壞**，所以事先寫好的 revert 觸發條件（「任何由人回報的、
使用者看得見的退步」）不成立。

**不得宣稱候選處理得比較好。**候選那一支有檢查點、出貨那一支沒有——但兩次的編輯
歷程不同（候選上使用者先打過字，`rev: 1`；出貨上直接開檔就按，`rev: 0`）。
**檢查點的差異由編輯歷程解釋，不是由 profile 解釋**，拿它去說 profile 的優劣就是
量了一個東西替另一個東西簽名。要比的話，兩支臂必須在同一個 revision 上。

## 環境

```
候選頁面 3dfdcfef4abfe6b7…（e2-editor-v12，＝八筆 soak 報告帶的那個）
出貨頁面 28e03e5bc9fcb8c4…（e2-editor-v8，baseline）
文件     e20-專訪瓦特老師.odt sha256 63bf89cb5d7eb891…，35 段，段落文字無重複
瀏覽器   使用者的真實 Chrome，真鍵盤，非 harness
```

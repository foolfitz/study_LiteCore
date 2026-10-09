# 111 — Delete、Backspace、方向鍵會插隊到「已經按下、還在輸入佇列裡」的字前面

| | |
|---|---|
| **狀態** | **已修**（2026-10-09，殼層 v58、宿主 0.2.9；瀏覽器重測 160/160、R′ 計數成立，見文末兩節）。舊狀態：讀原始碼＋單元層重現（2026-10-06）；瀏覽器未量；未修 |
| **所在** | 我們的產品頁面 `wasm_sdk_probe/web/e2-editor-app.js` 與輸入轉接器 `wasm_sdk_probe/input/input-adapter.js` |
| **發現日** | 2026-10-06（B1 修法的第二輪對抗性審核，第 4 條；主 session 讀原始碼確認並做了派送順序的單元檢查） |
| **嚴重度** | 中（推論）：不是資料遺失，是**編輯的順序錯**——字插在錯的位置、刪掉的不是使用者要刪的那一個；發生頻率未量 |
| **可重現** | 單元層每次（20 ms 假引擎）；真實瀏覽器上要多快的打字才會碰到，未量 |
| **是否上游** | 否 |

## 機制（讀原始碼）

- 打字走輸入轉接器：`beforeinput`／`input` → 轉接器自己的佇列 `_queue`，`_pump()` **一次只送一筆** `commitText` 進 session 佇列，前一筆完成才送下一筆（`input/input-adapter.js:348-397`）。
- Delete／Backspace 走 `beforeinput` → `editorAction()` → `session.action()`，**直接進 session 佇列**（`web/e2-editor-app.js` 的 `beforeinput` 處理器）；方向鍵走 `keydown` → 同一個 `editorAction()`。`editorAction()` **不等轉接器清空**。
- 所以「打 `a`、`b`，立刻按 Backspace」：`a` 正在送、`b` 還在轉接器裡，Backspace 先進 session 佇列、排在 `b` 前面。

## 量到的（單元層，不是瀏覽器）

- 派送順序（主 session，審核者的 fixture 加一條紀錄）：`insert a` → `action delete-backward` → 之後才輪到 `b`。那個 fixture 的修訂號對不上，所以結果本身不能當證據；**證據只有「派送順序」這一項**。
- 被拒的情形（審核者，`b1-review.test.mjs` Q5）：打 `M`、`2`，再按會被拒的 Delete → 拒絕當下存的檢查點只有 `M`，`2` 跟著被拒的 Delete 一起被退回。B1／109 的「零損失」因此要扣掉這種字（規格 §10）。

## 影響

- 一般編輯（推論，未量）：快速打字後立刻按 Backspace 或方向鍵，字可能出現在錯的位置，或刪錯字。
- 段落交界拒絕（單元層已重現）：被拒那一鍵**之前**很快打的字也可能掉。頁面的 toast 已改成照實說（2026-10-06 `04d19fcd`）。

## 處置方向（未決）

不能只是「Delete 之前等轉接器 `idle()`」：`idle()` 等的是現在**和之後**所有的字，Delete 之後才打的字會反過來排到 Delete 前面。要的是「只等排在我前面的那幾筆」的屏障，得動轉接器的內部（或讓刪除與移動也走轉接器的佇列）。另開一輪：先在瀏覽器用真鍵量發生頻率（逐字間隔掃描），再決定修法。

## 2026-10-06 補充：不只刪除與方向鍵（讀原始碼，未量）

接手的 session 讀 `web/e2-editor-app.js` 的按鍵處理器，同一個「不等轉接器」的形狀還出現在：

- **Enter／Shift+Enter**：`keydown` → `editorAction("insert-paragraph-break"／"insert-line-break")`（約 :1770）。「打一個字、立刻按 Enter」是最日常的節奏，所以分段落在最後幾個字**之前**的機會，推論比刪除更常見。
- **Ctrl+B／I／U**：`keydown` → `editorAction(formatAction)`（約 :1723）。
- **Ctrl+Z／Ctrl+Y**：`keydown` → `run(..., () => session.undo()／redo())`（約 :1687、:1697），不經 `editorAction`，同樣直接進 session 佇列。
- **Ctrl+S 與儲存鈕**：`takeSavedContent` ＝ `run("儲存", () => session.save())`（:1307），不等轉接器。推論：剛打完就存，最後幾個字可能不在存出去的位元組裡；它們之後照常送進引擎、修訂號前進，所以頁面會再變成「尚未儲存」——**不是無聲遺失**，但「已存回」那一刻的 toast 說得比實際多。

所以量測那一輪的掃描應該把 Enter 與 Ctrl+S 放進去，不只 Backspace／Delete／方向鍵；修法若是「只等排在我前面的那幾筆」的屏障，也得套在這些路徑上。

## 2026-10-09：瀏覽器量到了，裁決＝出修法（只追加）

- **量到的**（`evidence/111/PREDICTION.md`，真鍵、兩個瀏覽器）：插隊只發生在幾乎同時按下的鍵。小文件上實際按鍵間隔 1–6 ms 才會（Chrome Backspace 5/10、Enter 2/10；
  Firefox 9/10、10/10），≥13 ms 全部 0/10；擁有者那份 563 KB 的文件上窗口變寬，Firefox 在約 14 ms 也 10/10，≥24 ms 0。後果是刪錯字、分段落在最後一個字之前，不是資料遺失。
- **原型**（`evidence/111/prototype/`）：在 v2 session 子類別把「非打字的操作」排在轉接器還沒交出去的字後面；轉接器與基礎類別被 E1-C 綁著，不能動。
- **裁決**（fable 依擁有者授權，與 finding 119 同一份，`evidence/fast-delete-recovery/ruling/fable-ruling.md`）：出修法，與 119 同一次發佈（殼層 v58、宿主 0.2.9、
  一次重新計數），分開 commit；多一道守衛：被暫緩的操作若在等待期間工作階段重開了就丟掉，不在新引擎上執行。驗收是單元測試加瀏覽器重跑探針（兩份文件、兩個瀏覽器、0 插隊）。

## 2026-10-09：已修（只追加）

修法 `f26b80a6`（v2 session 子類別：非打字的操作排在轉接器還沒交出去的字後面，跨過重開就拒絕），隨殼層 v58、宿主 0.2.9 出貨。修好之後的瀏覽器重測：
兩份文件 × 兩個瀏覽器 × 間隔 0／10 ms × Backspace／Enter，160 次全部正確、0 插隊（`evidence/111/PREDICTION.md`）；`SPEC-M3-production-ui` §14 的 R′ 在 0.2.9 上
計數成立（`evidence/m3-production-ui/RESULT-0.2.9.md`）。**狀態：已修。**沒量的路徑：方向鍵、格式快捷鍵、Ctrl+S 走同一個暫緩（讀原始碼；U8 在單元層量了存檔）。


# 063 — 剪下被拒絕，而產品叫使用者把工作丟掉

| | |
|---|---|
| **狀態** | **已修（2026-08-19，殼層 v25，不需 relink）** |
| **Bugzilla** | —（**我方產品／殼層缺陷，不是上游**，不送出） |
| **發現日** | 2026-08-19 |
| **嚴重度** | **嚴重**——一個什麼都沒改到的動作，讓 session 進入 `recoverable-error`，並告訴使用者自上次儲存以來的內容不會回來 |
| **可重現** | 100%（Chrome，剪貼簿權限開啟後） |
| **是否上游** | **否** |

## 現象

拖曳選一段文字，按 Ctrl+X。結果：

- 複製那一半**成功了**；
- 刪除那一半**被拒絕**——`delete-backward` 在這份合約裡宣告成只吃收合游標，而剪下
  必然發生在範圍選取上；
- 拒絕的訊息自己寫著「**nothing was dispatched and the document is unchanged**」；
- 然後 session 進入 `recoverable-error`，通知跳出來說
  「引擎需要重新開啟。**沒有檢查點，所以自上次儲存以來的內容不會回來。**」
- 而且**畫面上一個字都沒提到剪下失敗**——那個錯誤被一個空的 `.catch(() => {})`
  吃掉了。

使用者看到的是：我按了剪下，什麼都沒發生，然後編輯器說我要重新開啟、而且會失去
所有沒存的東西。**文件根本沒有被動過。**

## 為什麼到今天才看到

**harness 從來沒有剪貼簿。** WebDriver 預設拒絕剪貼簿寫入，而產品的剪下是
「先複製、再刪除」——順序是刻意的，複製失敗就不該刪東西。所以在自動化裡複製永遠
失敗，**刪除那一半從來沒有跑過**，整條路沒有被量過。

2026-08-19 給 harness 開了剪貼簿權限（`Browser.grantPermissions` 加上
`Emulation.setFocusEmulationEnabled`——只給權限不夠，`clipboard.writeText` 還要求
文件是聚焦的）之後，複製成功了，刪除跑了，這個缺陷第一次露出來。

**這是 [[harness-path-vs-user-path]] 的同一個形狀**，而且是最貴的那一種：不是
harness 走了不同的路，是 harness **走不到**那條路。

## 重現步驟

1. 開任意文件，拖曳選一段文字。
2. 按 Ctrl+X。

**預期**：告訴使用者這個選取形狀不支援刪除，文件不變，session 照常。
**實際**（修正前）：沒有任何訊息，session 進入 `recoverable-error`，通知叫使用者
重新開啟並宣告未存內容會消失。

## 分析

兩個獨立的錯，疊在一起才變成這個樣子：

**一、錯誤被吞掉。** `web/e2-editor-app.js` 的 cut handler 把刪除放在 `.then()`
裡，而整條鏈以 `.catch(() => {})` 收尾：

```js
void run("剪下", () => session.copySelection())
  .then((result) => session.action("delete-backward", {})
    .then(() => toast(`已剪下 ${result?.codePoints ?? "?"} 字`)))
  .catch(() => {});          // ← 刪除的失敗死在這裡
```

同一個檔案往下三個 handler，finding 050 的註解就寫著「**使用者看不到的拒絕，等於
沒有人回報的拒絕**」。這裡犯的是同一件事。

**二、處置判錯。** `recoveryFor()`（`editor-shell-v2/paragraph-editor-session.js:44`）
是按 `error.details.formatBarrier` 分類的，而 `EDITOR_FORMAT_GESTURE_UNSUPPORTED`
**沒有 barrier 細節**——它是在派送之前就被 gesture mask 擋下來的
（`probe_engine.cpp`，SPEC E2-C 2.5 那道閘）。於是它掉到最底下的
`unknown-rollback` 預設，回傳 `rollback`，`_blockQueueIfDispatched` 把佇列擋住，
session 就進了 `recoverable-error`。

**一個自己聲明「什麼都沒派送、文件沒有改變」的拒絕，是最明確的 `none`。**

## 修法（已出貨，殼層 v25，不需連結）

1. `recoveryFor()` 明確把 `EDITOR_FORMAT_GESTURE_UNSUPPORTED` 映到 `"none"`。
2. cut handler 把**兩半都放進 `run()`**，所以刪除的失敗會像其他動作一樣被回報，
   帶著它的處置。

修好之後實測：

```
state='ready'
latency='剪下 失敗'
toast='剪下：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for
       this kind of selection in this profile, so nothing was dispatched and
       the document is unchanged'
notice: shown=False
```

## 沒有修的：剪下仍然剪不掉東西

這一單修的是**處置與沉默**，不是能力。`delete-backward` 在這份合約裡是
caret-only（`tools/build_e2_b_profile.py:86`：「range dispatch was characterised
for the paragraph actions, not for delete or insert」），而剪下必然在範圍上，
所以**刪除永遠會被拒絕**——今天的「剪下」實際上等於「複製」。

要讓它真的剪得掉，得把範圍刪除**先量過**再放進 manifest 的 gestures，
或者加一個刪除選取的動作。佇列項 `queue-cut-cannot-remove-text`。

## 環境

```
產品：wasm_sdk_probe/dist（artifact 29ec627bf8a5588b…，殼層 v25）
瀏覽器：Chrome（headless，剪貼簿權限與焦點模擬皆開啟）
量測：tools/run_e2_c_product_path.py 的 ctrl-x-is-handled-by-the-product
```

## 內部備註（不送出）

值得記住的一句：**這條路不是被走錯了，是走不到。** 一個因為 harness 能力不足而
無法執行的分支，和一個沒有人想到要測的分支，長得一模一樣——差別是前者連
「沒涵蓋」都不會顯示出來，因為檢查看起來是綠的（它確實驗證了「複製失敗時不刪除」，
只是永遠只走那一邊）。

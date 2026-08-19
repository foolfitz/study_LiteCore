# 061 — 檢查點寫入失敗的時候，產品告訴使用者「沒有檢查點」

| | |
|---|---|
| **狀態** | **已確認／未修**——殼層側，**不需要 relink** |
| **Bugzilla** | —（**我方產品缺陷，不是上游**，不送出） |
| **發現日** | 2026-08-19 |
| **嚴重度** | **嚴重**——使用者在「我的工作救不回來」與「我們試著救、失敗了」之間分不出來，而這兩件事會導致不同的下一步 |
| **可重現** | 100%（`--mutate checkpoint-write-fails`，Chrome 1/1） |
| **是否上游** | **否**。殼層已經把這個判斷做出來了，是產品頁沒有用它 |

## 現象

引擎卡死、產品把「回到檢查點」的通知放出來的那一刻，通知上寫的是

> 引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。

而實際發生的事情是：產品**有**試著在選取手勢之前先存一份檢查點，那次存檔**失敗
了**。狀態列的 `#s-checkpoint` 顯示「寫入失敗」，通知裡一個字都沒提。

對使用者來說，這兩句話的下一步不一樣：

- 「沒有檢查點」＝我從上次存檔之後就沒被保護過，這是我自己的節奏問題。
- 「我們試著保護你的工作，存檔失敗了」＝**保護機制壞了**，我現在應該先想辦法把畫面
  上的東西弄出來，而不是直接按下重新開啟。

產品把第二種說成第一種。

## 重現步驟

1. 讓 `_checkpointBeforeSelection()` 的存檔失敗（實測用 1 ms 的 deadline：
   `tools/run_e2_c_product_path.py --mutate checkpoint-write-fails`）。
2. 開 `endnote-frame.odt`，打幾個字（文件變 dirty），存檔，再打幾個字。
3. 拖曳選取涵蓋註腳引用記號的那一段——檢查點在這一步嘗試寫入並失敗。
4. 再做一個動作（點一下就夠）——引擎卡死，`recoverable-error`，通知出現。

**預期**：通知說明「試著保護、失敗了」，因為那正是發生的事。
**實際**：通知說「沒有檢查點」，而狀態列同時顯示「寫入失敗」。

## 證據

實測值（`recovery-returns-what-the-product-promised` 的 `observed`）：

```
checkpointAfterDrag: "寫入失敗"
declaredCheckpoint:  "寫入失敗"
branch:              "write-failed"
notice: {"shown": true,
         "text": "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。",
         "label": "重新開啟"}
savedWorkCameBack: true
unsavedWorkCameBack: false
declarationHonoured: false
```

對照組（同一個檢查、沒有突變）：`declaredCheckpoint: "有（r2）"`，通知改口成
「回到檢查點」，已存與未存的兩個標記都回來了。

## 分析

**殼層已經把這個判斷做出來了。** `editor-shell/recovery-notice.js:45`：

```js
const checkpointFailed = !hasCheckpoint && Boolean(snapshot.checkpointError);
```

它自己的註解就寫著為什麼要分開：「『沒有東西可以救』和『我們試著保護你的工作而存檔
失敗了』兩件事都以 `canRescue: false` 抵達這裡，而它們**不是對人講的同一句話**」
（SPEC-E1-C 4.1, v8）。

**產品頁沒有用那個模組。** `web/e2-editor-app.js:101-105` 自己重新推導了一個
**兩分支**：

```js
el.noticeText.textContent = snapshot.hasCheckpoint
  ? "這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。"
  : "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。";
```

`checkpointError` 在這一頁只有一個出口，就是狀態列那顆藥丸
（`web/e2-editor-app.js:96`）——所以事實**在畫面上**，但在一個給開發者看的欄位裡，
不在那則正在告訴使用者「你要失去什麼」的通知裡。

`_checkpointBeforeSelection()` 的 catch 是對的，它刻意不把背景檢查點的失敗變成
使用者手勢的失敗，但**也刻意不把它吞掉**（`editor-shell/editor-session.js:494` 起的
註解說得很清楚）。斷掉的是最後一段路：殼層交出來的區別，產品沒有接。

**這一格的形狀跟 059 是同一種**：資訊已經到了頁面，頁面選擇不呈現。

## 修法

產品頁改用 `recoveryNotice(snapshot)`，或至少把通知改成三分支。前者比較好——那個
模組存在的理由就是「主機在措辭和排版上可以不同，**不可以**在『有沒有宣稱工作被保住』
上不同」。

佇列項：`queue-checkpoint-write-failure-reads-as-nothing-to-rescue`（不擋 relink）。

## 環境

```
產品：wasm_sdk_probe/dist（殼層 v17 34289a7bd8ffc3df…，artifact d538ce0b91478426…）
瀏覽器：Chrome（WebDriver，合成事件）
量測：tools/run_e2_c_product_path.py --mutate checkpoint-write-fails
```

## 內部備註（不送出）

這是被**突變找出來的**，不是被檢查找出來的：`checkpoint-write-fails` 本來只是為了
證明 `recovery-returns-what-the-product-promised` 的第三個分支真的到得了。到得了，
而且產品在那個分支上是錯的。突變的用途因此有兩種，這一輪才看清楚——重新引入一個舊
缺陷，或**注入一個一直沒被走過的條件**。

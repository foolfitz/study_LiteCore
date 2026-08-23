# 079 — 工具列用一個**從來沒讀到過**的選取形狀決定按鈕能不能按

> **2026-08-23 改判並修好。**原標題說形狀是「過期的」。**不是過期，是根本沒有值。**
> 頁面從 `result.collapsed` 和 `result.rectangles` 讀形狀，而 v2 client 交回來的
> 信封裡這兩個欄位不存在——它們在 `result.state.selection`。兩個 `undefined` 一路
> 掉進 fallback，於是**每一次拖曳、每一個選取，形狀都算成 `collapsed`**。
> 詳見〈直接觀測到的機制〉與〈修訂紀錄〉。

| | |
|---|---|
| **狀態** | **已直接觀測、已修、已驗證**（2026-08-23） |
| **發現日** | 2026-08-23，被一個**什麼都沒發生**的突變抓到 |
| **嚴重度** | **中**：它是使用者撞到那個體驗的第二層（第一層是 finding 078 的清單沒給） |
| **可重現** | **100%**，不是間歇——修法前三個臂裡兩個必然錯 |
| **是否上游** | **否，是產品頁面的** |

## 一句話

拖曳出一段選取之後，頁面自己記的 `lastSelectionShape` 仍然是 `collapsed`——因為算
這個值的那個運算式讀的是**兩個不在那個物件上的欄位**，所以它從一開始就只會算出
`collapsed`。

## 怎麼被抓到的：一個沒有生效的突變

finding 078 的第一版突變是「當 `lastSelectionShape !== "collapsed"` 時讓格式動作
直接 return」。它應該讓新檢查變紅。**它一次都沒有觸發**——檢查照樣 PASS，兩輪都是。

也就是說那個早期 return 的條件從來不成立：**按下去的當下，頁面認為沒有選取。**

**抓到它的是「什麼都沒發生」本身。**如果我看到「突變沒讓檢查變紅」就直接換一個突變，
這件事會整個溜掉——而這棵樹的規矩裡正好有一條講這個：**每個「X 沒發生」的臂都要有
正向對照，否則「什麼都沒發生」與「機制沒跑起來」長得一樣，而且是綠的。**

## 它解釋了一個我原本當成謎的現象

在只開 `range-single` 的 `e2-editor-v6` 上：

- **按鈕是啟用的**（`{disabled: false, title: ""}`）——因為頁面算的是
  `gestures.includes(lastSelectionShape)`，而 `lastSelectionShape` 過期成
  `collapsed`，`collapsed` 有被提供；
- **引擎拒絕了**——因為它那一側看到的是一個未分類的 range，而 AND 語意要求兩個
  range 位元都在（finding 078）。

⇒ **使用者會看到一個看起來可以按的按鈕，按下去得到 `GESTURE_UNSUPPORTED`。**
這正是使用者 2026-08-23 回報的體驗，而我原本只歸因給清單沒給。**清單沒給是第一層，
按鈕騙人是第二層。**

## 頁面那一側的來源

```js
lastSelectionShape = (result?.rectangles?.length ?? 0) > 1
  ? "range-cross" : (result?.collapsed === false ? "range-single" : "collapsed");
```
（`web/e2-editor-app.js`，另一處在拖曳結束時把它設回 `"collapsed"`）

所以它依賴某一次回應裡的矩形資訊，而那個更新**沒有在按下之前完成**。

## 直接觀測到的機制（2026-08-23，`tools/probe_079_selection_shape.py`）

### 三個候選原因，量完只剩一個——而且不在那三個裡

原本列的三個候選是「更新從未發生／太晚／被重設」。**都不是。**

探針在頁面**自己的指標處理器**裡跑一次真的拖曳，然後在**同一個臂**裡同時記兩件事：
頁面怎麼想（工具列的 `title` 會把形狀名字寫出來），引擎怎麼想（產品自己的複製路徑，
`copySelection()` 回報的碼點數）。修法前：

| 臂 | 引擎說 | 頁面說 | 8 秒內變過嗎 |
|---|---|---|---|
| 只點一下不拖（正向對照） | 0 字 | `collapsed` | 沒有——**兩邊一致，對照成立** |
| 一行之內拖 | **12 字** | `collapsed` | **從頭到尾沒變過** |
| 跨兩行拖 | **34 字** | `collapsed` | **從頭到尾沒變過** |

工具列在整整 8 秒的取樣視窗內**一次都沒有變動**。所以不是「太晚」——是**從來沒發生**。

### 為什麼從來沒發生：它讀的兩個欄位不在那裡

再用一個只多一行的鏡像頁面把 `session.selectRange()` 真正 resolve 出來的物件錄下來
（`--capture-result`）：

```
頂層 keys：method, revision, completion,
          callbackSequenceBefore, callbackSequenceAfter, state
```

**沒有 `collapsed`，沒有 `rectangles`。**它們在下一層：

```
state.selection = { observed: true, collapsed: false,
                    start: {...}, end: {...}, rectangles: [ ... ] }
```

`editor-shell/editor-client.js`（**v1** 路徑）會把回應整理成
`{collapsed, text, rectangles, caret, revision}`；**v2** 路徑不整理——
`ParagraphEditorClient.selectRange` 把 worker 的信封原樣交出去。頁面讀的是 v1 的形狀。

於是那個運算式：

```js
(result?.rectangles?.length ?? 0) > 1        // undefined?.length ?? 0 → 0，不 > 1
  ? "range-cross"
  : (result?.collapsed === false             // undefined === false → false
     ? "range-single" : "collapsed");        // ⇒ 永遠是 "collapsed"
```

**沒有任何輸入能讓它算出別的答案。**這不是快取沒更新，是**沒有值可以過期**。

兩個分支都量了，不是只量一個：

| 拖曳 | `state.selection.collapsed` | 矩形數 | 正確形狀 | 頁面當時算出 |
|---|---|---|---|---|
| 一行之內 | `false` | 1 | `range-single` | `collapsed` |
| 跨兩行 | `false` | 3 | `range-cross` | `collapsed` |

### 正向對照（沒有它，上面整張表可能是在講儀器）

`--positive-control` 把 `lastSelectionShape` 的**初始值**改成 `range-single` 再開頁面：
六個 caret-only 按鈕全部停用，`title` 全部寫著「range-single」。
⇒ **這個讀法有能力顯示 range 形狀**，所以量到 `collapsed` 是在講頁面，不是在講探針。

## 修法與驗證

`web/e2-editor-app.js` 的 `pumpDrag`：改讀 `result?.state?.selection`。

並且**讀不到就不要編一個出來**：`typeof selection?.collapsed !== "boolean"` 時保留
前一個值，並在 `#toolbar` 上寫 `data-selection-unreadable="1"`。
——編一個 `collapsed` 出來正是這張單本身；編一個 range 出來會讓普通點擊之後
⌫、⌦、分段、換行四個鍵全部變灰，那更糟。

修法後同一支探針，同一台機器：

| 臂 | 引擎說 | 頁面說 | 頁面追上的時間 |
|---|---|---|---|
| 只點一下不拖 | 0 字 | `collapsed` | —— |
| 一行之內拖 | 12 字 | **`range-single`** | **52 ms** |
| 跨兩行拖 | 34 字 | **`range-cross`** | **55 ms** |

52–55 ms。**它從來就不是延遲問題。**

## 原本預測的後果是錯的，而讀程式碼就能知道

這張單原本說代價會落在 `delete-selection` 上：它只提供給兩種 range，形狀若過期成
`collapsed` 就會「該能用的時候顯示停用」。

**那個後果到不了。**`lastSelectionShape` 全檔**只有一個地方讀**——
`updateGestureAffordance()`，而它只碰 `#toolbar button[data-action]`。
工具列上**沒有** `delete-selection` 按鈕；它唯一的派送點是剪下處理器，
問的是 `session.offers("delete-selection")`，那是**清單**不是形狀。

代價落在同一道閘門的**另一邊**：六個按鈕（左右移、兩個刪除、分段、換行）只提供給
`collapsed`，所以形狀卡在 `collapsed` 會讓它們在有選取時**看起來全部可按**，
而引擎的 mask 會拒絕。**同一個缺陷，反過來，落在真的存在的按鈕上。**

## 沒有量的（因此不指認）

- **使用者按下去會看到什麼。**上面說「引擎的 mask 會拒絕」是從手勢表推的；
  沒有人真的在有選取的狀態下按過 ⌫ 然後記錄畫面。
- **`rectangles.length > 1` 是不是真的等於「跨段」。**一個換行折行的長段落也可能
  給出多個矩形。這個判準是本來就有的，這次沒有動它，也沒有量它。

## 和 078 的關係

**兩張單、兩層，修法不同。**078 是清單沒給（處方：量了再開，已做，`e2-editor-v7`）。
079 是頁面對自己的狀態說謊（處方未定——最小的可能是不要快取形狀，按下時向引擎要）。

v7 出貨之後 079 的**急迫性下降但不消失**：三種手勢全開之後，格式按鈕不會再因形狀被拒，
但任何**沒有**全開的動作仍然吃這個 bug，`delete-selection` 就是現成的一個。

## 修訂紀錄

- 2026-08-23：建檔。狀態「量到（間接），機制未直接觀測」，機制列三個候選，
  並預測後果會落在 `delete-selection`。
- 2026-08-23（同日，下一個 session）：**改判並修好。**
  - **機制不是「過期」**：`pumpDrag` 讀的 `result.collapsed` 與 `result.rectangles`
    不存在於 v2 client 交回的信封上（它們在 `result.state.selection`），所以形狀
    是**被製造出來的**而不是**沒更新的**。原標題的「過期」是錯的字，留在檔名裡
    是為了不動既有引用。
  - **原本預測的 `delete-selection` 後果到不了**——那顆按鈕不存在，它的派送路徑
    讀的是清單不是形狀。真正的代價在六個 caret-only 按鈕上。
  - 已修（`web/e2-editor-app.js`），並以 `tools/probe_079_selection_shape.py`
    在修法前後各量一次，帶正向對照。
  - 回歸網加了 `the-page-agrees-with-the-engine-about-the-selection`，
    突變 `selection-shape-from-the-wrong-place` 讓它 PASS → FAIL。
  - 連帶：`an-aborted-gesture-stops-selecting` 自 2026-08-21 起一直棄權，
    宣告寫的原因是「harness 拖不出選取」——**那是錯的**，見 finding 080。

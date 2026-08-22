# 067 — 按 Enter 什麼都不會發生，**而 revision 說它成功了**

| | |
|---|---|
| **狀態** | **已確認，未修**（2026-08-22） |
| **Bugzilla** | —（**不是上游**：兩個候選層級都在我們這一側，見〈機制〉） |
| **發現日** | 2026-08-22（operator 2026-08-21 那一輪先撞到，當時被 [066](066-the-toolbar-takes-the-keyboard-and-never-gives-it-back.md) 遮住而無法判讀；066 修好之後才問得出來） |
| **嚴重度** | **高**——使用者按 Enter 想分段，文件完全沒變，沒有任何提示，**而且進度計數器往前跳了一格** |
| **可重現** | Chrome 1/1（真實按鍵，走 CDP `Input.dispatchKeyEvent`）。Firefox 未量——需要真實按鍵 |
| **是否上游** | **否** |

## 現象

在游標已經在文字上、鍵盤焦點在編輯面（066 修好之後的預設狀態）時：

1. 打字 → 進得了文件。
2. **按 Enter。**
3. 再打字 → 也進得了文件。

**第 2 步什麼都沒發生。**段落數 9 → 9，`content.xml` **位元組完全相同**，沒有錯誤、
沒有 toast、狀態列停在 `ready`。

**而 revision 從 1 跳到 2。**

第 1 步與第 3 步是正向對照，而且它們是這張單的承重結構：**鍵盤在那顆按鍵的兩側都
是通的**，所以「Enter 沒作用」不能被解釋成「鍵盤沒作用」。

## 為什麼昨天問不出來

operator 在 2026-08-21 那一輪就撞到了——他存出的兩個檔 `content.xml` 位元組相同。
但那一輪的焦點被 [066](066-the-toolbar-takes-the-keyboard-and-never-gives-it-back.md)
停在工具列按鈕上，所以**「Enter 沒作用」與「按鍵根本沒送到編輯面」分不開**。
066 修好之後，這一臂才有前提可言。

**一個缺陷會遮住另一個缺陷**，而遮住它的那個看起來只是體驗問題。

## 證據

`findings/evidence/067/`。

## 機制：兩個候選，都在我們這一側，**都讀得到行**

### 一、輸入轉接器把 Enter 變成貼上一個 `"\n"`

`input/input-adapter.js:248-251`：

```js
if (inputType === "insertLineBreak" || inputType === "insertParagraph") {
  this._prevent(event);
  this._trace(event, "beforeinput", { action: "commit-line-break" });
  return this.commitText("\n", { source: "beforeinput", inputType, ... });
}
```

所以真人的 Enter **不會**派送 `insert-paragraph-break`，而是走 `commitText("\n")`
→ `document.insertText("\n")`。

**而工具列的 `↵ 分段` 按鈕是好的**——它走 `.uno:InsertPara`
（`src/probe_engine.cpp:4413`），回歸網每一輪都在驗。**兩條路，只有使用者那條是壞的。**

順帶一提：`insertLineBreak` 與 `insertParagraph` 在這裡被折成同一件事，而引擎有
`insert-line-break` 與 `insert-paragraph-break` **兩個**動作。

### 二、引擎不管有沒有改到東西都把 revision 加一

`src/probe_engine.cpp:2730-2755`，`handleInsertText`：

```cpp
  std::string method = "paste";
  if (!gState.document->pClass->paste(..., command.text.data(),
                                      command.text.size())) {
    method = "postKeyEvent";
    ...
  }

  ++gState.revision;
  ...
  emitJson(...);   // {"type":"inserted", ...}
```

`++gState.revision` 在**成功路徑與退版路徑之後無條件執行**，回報 `"inserted"`。
所以「貼上一個換行什麼都沒做」與「插入了文字」在協定上長得一模一樣。

**這是 022 那個形狀（安靜的 no-op）換一個位置。**

### 沒有量到的部分

`paste()` 的回傳值在這裡看不到，所以**不知道**是「paste 回 true 但 Writer 對單獨一個
`"\n"` 不做事」，還是「paste 回 false、走了 `postKeyEvent` 退版路徑而那也沒作用」。
`method` 欄位分得出來，**這一輪沒有把它接出來**——下一輪先接那個欄位，成本接近零。

## 處方（未實作，而且刻意先不做）

**主修法在轉接器**：`insertParagraph` 應該派送 `insert-paragraph-break`，
`insertLineBreak` 應該派送 `insert-line-break`，兩者分開，而不是折成
`commitText("\n")`。這是**殼層那一側**，不需要連結。

**沒有今晚動手，理由具名**：

1. `input/input-adapter.js` 是 finding 050（一個 session 只能打一次中文）住過的地方，
   它的 composition 狀態機不是可以在無人看管時順手改的東西。
2. 轉接器目前只拿得到 `commitText`；要讓它派送動作是**介面的改動**，不只是換一行。
3. 今晚已經鑄過一次殼層身分（v25 → v26），而使用者還沒看過那一次。
4. **第二個候選要不要一起修是個判斷題**：`++gState.revision` 無條件加一是引擎那一側，
   而那需要連結。在量出 `method` 之前不該把它塞進任何清單。

## 這一輪的形狀，記下來

**066 遮住 067，而 066 是 operator 報的。**自動化不可能找到 066（每個鍵盤 helper
都自己補 `sink.focus()`），而沒有 066 就問不出 067。**一個人在螢幕前看了十五分鐘，
掉出兩個高嚴重度缺陷，其中第二個是第一個修好之後才存在的問題。**

# 067 — 按 Enter 什麼都不會發生，**而 revision 說它成功了**

| | |
|---|---|
| **狀態** | **產品那一半已修並驗證**（2026-08-22，殼層 v27）；**引擎那一半未修**，需要連結 |
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

### 已經量到了（2026-08-22 補）

`method` 接出來了：**`paste`**。所以 LOK 的 `paste` **回傳 true**，引擎沒有走
`postKeyEvent` 退版路徑。故事因此是**paste 收下了一個單獨的換行然後什麼都沒做**，
不是「paste 拒絕了它」。

同一次量測還掉出一件改變處方的事：**Enter 與 Shift+Enter 在 commit 邊界上分不出來**
（兩顆都報 `insertLineBreak`，因為輸入面是 `<textarea>`；`insertParagraph` 是
contenteditable 才會報的，所以轉接器那個分支在這個頁面上是**死碼**）。
證據：`findings/evidence/067/engine-route-and-which-key.json`。

## 處方（產品那一半已實作，殼層 v27）

**綁在頁面自己的 keydown 處理器裡**，也就是這個檔案已經放了方向鍵與
Ctrl+Z／S／B／I／U 的地方，而它自己的註解就寫著理由：「走 `editorAction`，
和工具列按鈕呼叫的是同一個函式，所以快捷鍵和按鈕不會走散」。

```js
if (event.key === "Enter" && !event.isComposing) {
  event.preventDefault();
  if (!accel) {
    void editorAction(event.shiftKey ? "insert-line-break"
                                     : "insert-paragraph-break").catch(() => {});
  }
  return;
}
```

### 為什麼不放在轉接器的 commit 邊界（本來的計畫，被否掉了）

原本要在 `NarrowEditorV2Session` 裡換掉繼承來的轉接器，在 commit 邊界上分流。
**兩個獨立的理由把它殺掉，兩個都是查證過的：**

1. **基底類別的建構子把轉接器交出去了。**
   `editor-shell/editor-session.js:97` 把 `this.input` 傳給
   `PlainTextClipboardAdapter`，而剪貼簿轉接器把它存成 `this._input`
   （`clipboard-adapter.js:33`）並透過它 commit。事後替換欄位只會留下**兩個**
   轉接器：`setBlocked` 只到得了新的那個，DOM 貼上與 API 貼上會走不同的轉接器。
   一個安靜的分裂狀態。
2. **兩顆鍵在那個邊界上分不出來。**（量到的，見〈證據〉）Enter 與 Shift+Enter
   都報 `insertLineBreak`，因為輸入面是 `<textarea>`。所以任何在
   `commit(text, metadata)` 上做的決定，只能提供兩種斷行的其中一種——而原本的
   對照表會把真人的 Enter 對到**行**斷行，在畫面上像對的、在 XML 裡是錯的。

`keydown` 上的 `preventDefault` 讓瀏覽器**根本不產生 `beforeinput`**，所以轉接器
那條分支永遠不會觸發——兩條路是**構造上互斥**的，不靠註冊順序。

### 三個承重的細節

- **`!event.isComposing` 不是可選的。**IME 組字中的 Enter 是**確定組字**，在那裡
  preventDefault 會弄壞中文輸入——finding 050 的鄰居，而那個檔是凍結的，這裡犯錯
  沒辦法在那邊補救。
- **Ctrl/Cmd+Enter 被吞掉**，不往下傳。契約裡沒有分頁動作，讓它落到轉接器就會在
  那個組合鍵上重現 067。這和 Ctrl+S 加 preventDefault、Ctrl+A 不綁是同一條規矩：
  提供一個派送不出去的鍵，比不提供更糟。
- **走 `editorAction` 而不是 `session.insertBreak`**，因為前者才有 046 殘留的
  處置邏輯（`DISPATCHED_UNVERIFIED` 拆封、`_blockQueueIfDispatched`、`recovery`
  欄位），而 `run()` 的提示文字就是看那個欄位。**鍵盤走的是工具列那條路。**

### 驗證

| | |
|---|---|
| 探針 | `real-enter` 從 FAIL 轉 **PASS**：段落 9 → 10，`content.xml` 不再相同，正向對照仍然成立 |
| 出貨頁 Chrome | `the-enter-key-reaches-the-document` **PASS**，兩個臂：Enter 段落 10 → 11 且兩個標記不在同一段；Shift+Enter 段落 12 → 12 且兩者之間有 `<text:line-break/>` |
| 突變 `enter-key-not-bound` | **偵測到**，而且**只有**擁有它的那一格變紅；兩個臂的段落數都不動，正好重現 067 |
| 單元測試 | `product-page-calls.test.mjs` 釘住三件事（分支存在、Shift 對到行斷行、`isComposing` 守衛），把分支關掉會紅 |
| 殼層身分 | v26 → **v27**（`55a91f837f21…`），矩陣第五個綁定就地重述、`refreezeLog` 第三列 |

**判準是段落數，不是 revision。**這棵樹有收據：每一次壞掉的按鍵 revision 都前進了。

### 這一輪自己踩到的坑（同一個檔案兩天內第三次）

新檢查第一版放在 `the-edit-buttons-do-what-they-say` **前面**。它會**增加段落**，
而那一格是用**幾何**瞄準的——它刻意點在 y=0.28 那一行的末端，好讓斷行落在行尾。
我的區塊讓文件重排，那一下就落在段落中間，殘餘文字跟了過來，它的精確字串判準當場
失敗。**紅的是它，錯的是我。**現在移到最後一個用幾何瞄準的檢查之後、長文件區塊
之前（那一段會自己開一份文件，把我留下的東西沖掉），而且自己先重開一次 fixture。

## 引擎那一半（未修，需要連結）

`handleInsertText` 的 `++gState.revision` **無條件執行**，所以「貼上一個換行什麼都
沒做」與「插入了文字」在協定上長得一模一樣。這是 022 那個形狀（安靜的 no-op）換一
個位置，而修它要一次連結。

**現在它是可以具名的**：`method` 已經量到是 `paste`，也就是 LOK 收下了那個換行、
回傳 true、然後什麼都沒做。所以處方不是「處理 paste 失敗」，而是**在 revision 前進
之前要有證據說文件真的變了**。

**還沒放進任何清單**，因為它需要一次連結而連結的貨載目前是六項定案。

## 沒有涵蓋的路徑（具名，未量測）

一個**沒有 keydown 就到達的** `beforeinput insertLineBreak`——行動裝置的虛擬鍵盤、
自動更正——仍然會走到凍結的轉接器、仍然撞上引擎這個 no-op、仍然讓 revision 說謊。
**沒有量過**，也不該只憑推理先修：貼上那次雙重 commit 就是這樣長出來的。

## 這一輪的形狀，記下來

**066 遮住 067，而 066 是 operator 報的。**自動化不可能找到 066（每個鍵盤 helper
都自己補 `sink.focus()`），而沒有 066 就問不出 067。**一個人在螢幕前看了十五分鐘，
掉出兩個高嚴重度缺陷，其中第二個是第一個修好之後才存在的問題。**

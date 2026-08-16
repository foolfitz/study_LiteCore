# 設計：caret 用（段落, 位移）確認，而不是用矩形反推

佇列項 `queue-verify-caret-by-block-identity` 的設計。**事前寫的**——relink 還沒
發生，所以底下的預測都還有事前性。

依據兩件事：
[三輪 native 量測](../findings/evidence/queue-block-identity/README.md)，以及一份
精簡編輯器的參考實作（MarkText 的 Muya core，`/home/jiajun/Projects/marktext`）。

## 一、問題不是「少一個資料」，是映射的方向反了

三個模糊——046 驗錯段落、052 的殘留、同一行不同 x——之前被歸成「引擎沒有回報
caret 在第幾個 block」。量完之後這句話只對一半，而參考實作說明了另一半。

**Muya 的游標就是 `{offset, block, path}`**（`packages/muya/src/selection/types.ts`
的 `IAnchorFocusInfo`）。它有 `isSelectionInSameBlock` 這個一級欄位；`block` 那個
參考還特地註明是「in-memory optimization，apply 的時候會從 `path` 重新解析」——
**耐久的身分是 path，不是指標，更不是幾何**。

而幾何在 Muya 裡**只往一個方向走**：`selection/cursorCoords.ts` 從
`document.getSelection()` 算出 `DOMRect`，給 UI 定位用。**沒有任何一處從像素反推
游標。**點擊由瀏覽器解析，Muya 只負責把解析結果（DOM node ＋ offset）翻譯回自己的
模型（`TextSelection.getSelection`：`findContentDOM(anchorNode)` ＋
`getOffsetOfParagraph(...) + anchorOffset`）。

我們現在做的正好是反過來的：送出一個像素點擊，然後**從回傳的矩形去推論**「caret
是不是到了我要的地方」。三個模糊全部是這個反向映射的產物：

- `caretIsOnLine` 只有 y，所以同一行不同 x 分不出來；
- 點在文字外時「我要的那一行」根本不存在，所以幾何**永遠**判不出來（052）；
- barrier 拿 restore point 的矩形去問「選取有沒有蓋住 caret」，而它真正該問的是
  「讀回來的是不是我 dispatch 的那一段」（046）。

## 二、量到的事實（三輪 native，core 26.8）

| | |
|---|---|
| LOK 有沒有段落序號 | **沒有**。focused-paragraph 酬載只有 `content`／`position`／`start`／`end`／`listPrefixLength`；`getCommandValues` 也沒有一條回答得了 |
| 那拿得到什麼 | 段落**自己的文字**——一個指紋。兩個文字相同的段落，酬載逐位元組相同（P-BI-4，caret y 2585 → 2974 證明 caret 真的移動了） |
| 046 分得開嗎 | **分得開**。dispatch 當下 `'• '`（`listPrefixLength: 2`），`.uno:SelectText` 之後 `'BI-AFTER-EMPTY'`，讀回 `'    • \nBI-AFTER-EMPTY'`。引擎**已經收到**這個酬載，只是把 `content` 丟掉、只留 `contentLength`——而 2 對 14 連這個弱化版都分得開 |
| 052 的殘留呢 | 同一個 x 在行上讀 offset **4**、在文字下方讀 **7**（P-BI-6）。x 在行上被帶入、在文字下方被丟掉，所以文字外的每一次點擊都落在同一個 offset。**就算真的有 block index 也沒用**——caret 確實就在最後一段裡 |

## 三、052 的殘留：多一個資料救不了，換一種呼叫可以

這是量測不會自己說、參考實作才點出來的一步。

`placeCaret` 現在的成立條件是兩個代理訊號的**析取**：「引擎說了話（`sourceSequence`
前進）而且 caret 在點到的那一行」或「引擎說了話而且 caret 動了」。第二次點在同一個
文字外的位置時，**兩個都不成立**：沒有東西改變，所以引擎不發任何回呼；caret 沒動；
caret 也不在「點到的那一行」（那一行不存在）。於是它等滿 30 秒。

**多回報一個段落指紋救不了這一格**——指紋也沒有改變。真正缺的不是資料，是
**針對這一次點擊的回答**。Muya 不需要這個機制，因為它那邊沒有這道縫：瀏覽器同步
解析點擊，`getSelection()` 回來就是結果。

所以處方是把那道縫補起來：

> **`editorPlaceCaret(x, y)` 應該是一個有回傳值的呼叫**，回傳
> `{paragraph: {textHash, length, listPrefixLength}, offset, caret}`——
> 引擎送出滑鼠事件、把自己的主迴圈抽乾、然後讀 `getA11yFocusedParagraph()` 回答。
> 不是「送出點擊，然後在殼層裡觀察狀態變化」。

這樣三個模糊一起收掉，而且**不是靠比對，是靠不用再反推**：

| | 現在 | 改成呼叫之後 |
|---|---|---|
| 046 | barrier 問「選取蓋住 caret 嗎」 | 問「讀回來的是不是 dispatch 那一段」——引擎內部比，不必投影出去 |
| 同一行不同 x | `caretIsOnLine` 沒有 x | 回傳裡有 `offset` |
| 052 殘留 | 沒有訊號 → 等 30 秒 | 呼叫回來就是確認，什麼都沒變也一樣回來 |

**送出去的是雜湊不是文字。** 引擎現在刻意不把 a11y 原始酬載轉給 JS
（`probe_engine.cpp` 的註解寫明「Recorded as closed typed counters; the raw payload
is never forwarded to JS」）。那個決定要保留：殼層需要的是「是不是同一段」，不是
段落的內容。

## 四、事前預測（relink 之後才驗得了）

寫在這裡，就是為了讓 relink 之後的那一輪有東西可以打臉。

- **D-BI-1**：改成呼叫式之後，第二次點在文字外的同一點，`placeCaret` 在
  **200 ms 內**回來，而不是 30 秒。*不成立的話*：引擎抽乾主迴圈**不**蘊含那個點擊
  已經被處理，而這一整個設計的前提就垮了。
- **D-BI-2**：`getA11yFocusedParagraph()` 在點擊被處理後**立刻**是新的。三輪 native
  都是在 700 ms drain 之後讀的，**短延遲下的新鮮度沒有量過**。*不成立的話*：回傳值
  要改成等 a11y 回呼，而那條路被文字相同時不發通知的閘門擋著（core 的
  `if (m_sFocusedParagraph != sText)`）。
- **D-BI-3**：barrier 用「dispatch 段落 vs 讀回段落」判定之後，046 的空段落格從
  `EDITOR_FORMAT_POSTCONDITION_FAILED` 變成一個自己的結果，而**沒有任何一個現有的
  D1／D2／D3 格子改變判定**。*不成立的話*：這個比對的偽陽性比它修掉的還多。
- **D-BI-4**：`.uno:SelectText` 逃逸的方向由手勢決定，不是由文件決定。目前是
  **兩個資料點**（舊 pair 往上、SelectText 往下，兩份不同語料），**不是規則**——
  這一條預測相當於說「再量一份語料會看到同樣的方向」。

## 五、這個設計做不到的，先寫下來

- **兩個文字相同的相鄰段落分不出來**（P-BI-4，逐位元組相同）。指紋不是身分。
  046 的用途上這是可接受的——它問的是「是不是同一段」而不是「這是第幾段」——但
  一份「上下兩段都是空的」的文件會讓比對沉默。**這是具名極限，不是待辦。**
- **真正的段落身分要動 core**（`SwPosition::GetNodeIndex()` 那一類），而上游送出
  目前擱置，所以不在這條路上。
- **以上沒有一個字描述 WASM artifact。** 三輪都是 native core 26.8；shipped 引擎
  會不會看到同樣的酬載，要 relink 之後才知道。

## 六、佇列上要改的措辭

佇列項的檢查 `caretBlockIndex` 名字取錯了——不存在的東西不會被實作出來，這個檢查
永遠是綠的，而**永遠綠的檢查不是檢查**。改成對得上這份設計的名字，並把
「一次關掉三個模糊」改寫成量到的形狀。

# 064 — 在產品裡按下斜體／底線／刪除線，**接下來打的字沒有那個格式**

> # 撤銷（2026-08-21 改判，2026-08-22 才找到真正的原因）
>
> **這個缺陷不存在，而且原因不是我 08-21 寫的那個。**
>
> **真正的原因**：判讀工具 `inline_styles_of()` 停在「標記不在 `<text:span>` 裡，
> 所以它沒有任何格式」。**ODF 不是這樣運作的**——一個**整段一致**的段落，
> LibreOffice 把字元屬性寫進**那個段落自己的 automatic style**，完全不產生 span。
> 而「標記獨自待在自己的段落裡」正是每一臂都會產生的狀態，所以**每一個標記都被
> 讀成沒有格式**。
>
> 修好之後，把原本那個「一次存檔讀八個答案」的讀法**原封不動**重跑：
> **四個格式、兩個方向、八個臂全部正確**（`P3`…`P9` 各自帶著自己那一臂的屬性）。
>
> **是 operator 抓到的**（2026-08-22）：他在畫布上看得到粗體，而存檔讀回來是
> `bold: false`。這棵樹裡沒有任何自動化抓得到——每一個有機會抓到的檢查都在同一個
> 函式的下游。
>
> **08-21 那次改判也錯了一半。**它說「格式有到打出來的字上」——**這一句對**；
> 但它說毀掉證據的是下一臂開頭那次 `insert-paragraph-break`，並據此另立 065。
> **那個機制不存在**，065 已撤銷。斷行之後 `spans` 從 1 掉到 0 是**正確的匯出**，
> 不是遺失。
>
> 量測與原始 ODF：`findings/evidence/064/RESULT-render-between-format-and-typing.md`。
> 底下的原文全部保留——它連錯兩次，兩次都是同一個形狀（**問了文件一個它不會那樣
> 回答的問題**），這比結論本身有用。

| | |
|---|---|
| **狀態** | **撤銷（2026-08-22）**——缺陷不存在，是判讀工具讀不到段落層級格式的偽陰性 |
| **Bugzilla** | —（**不是上游**：引擎在同一顆 artifact 上做對了，見〈歸因〉） |
| **發現日** | 2026-08-21（T1 第一次驅動 `set-italic`／`set-underline`／`set-strikethrough`） |
| **嚴重度** | **高**——**四個** inline 格式從產品按下去全部等於沒有作用（含粗體）；而 2026-08-19 那次連結的**全部內容**就是讓底線與刪除線能被關掉 |
| **可重現** | Chrome 3/3（artifact `29ec627b`、殼層 v25、collapsed 游標） |
| **是否上游** | **否** |

## 現象

在出貨的產品頁上，把收合游標放在一段文字裡，按工具列的 **I**（或 U、S），
然後用產品自己的插入欄位打一段標記文字，存檔：

**標記文字身上沒有那個格式。**

**四個**格式、開與關兩個方向，八個臂全部一樣：

```
bold           on=False  off=False
italic         on=False  off=False
underline      on=False  off=False
strikethrough  on=False  off=False
```

粗體是後來才加進來量的（原本只量另外三個），因為
`bold-can-be-turned-off-again` 是綠的，而那一格的判準是 `aria-pressed`。
**加進來之後它跟其他三個一樣壞。**按鈕**沒有 disabled**
（`buttonOffered: true`），**沒有任何錯誤 toast**，狀態列停在 `ready`，
revision 每次都有前進——從產品的每一個表面看，那個動作都成功了。

## 歸因：引擎沒問題，**是產品那條路**

這是本輪最重要的一段，因為它把「不要在沒量之前指認層級」（040／048／062 的先例）
走完了。

同一顆 artifact `29ec627b`、同一個 profile `e2-editor-v3`、同一台機器，
用 **D1 自己的 harness** 問同一個問題（宣告為 diagnostic round，輸出寫在
scratch，沒有碰凍結證據）：

| 標記 | bold | italic | underline | strikethrough |
|---|---|---|---|---|
| `D1BOLDON` | **true** | false | false | false |
| `D1BOLDOFF` | false | false | false | false |
| `D1ITALON` | false | **true** | false | false |
| `D1ITALOFF` | false | false | false | false |
| `D1UNDRON` | false | false | **true** | false |
| `D1UNDROFF` | false | false | false | false |
| `D1STRKON` | false | false | false | **true** |
| `D1STRKOFF` | false | false | false | false |

**八個臂全部正確。** 所以：

1. **引擎與 artifact 沒有迴歸。**finding 059 的修法沒有壞掉這件事。
2. **判讀工具沒有問題**——同一個 `inline_styles_of()` 讀 D1 的文件讀得完全正確，
   讀產品的文件才讀不到格式。
3. 因此差別**只可能在產品那條路上**。

D1 直接驅動殼層 client；產品頁走它自己的 handler。這正是
`harness-path-vs-user-path` 那一條：**兩條路不同的時候，只有使用者那條沒被量過。**

## 機制已確立（2026-08-21 補），而且答案是這張單問錯了

**先講結果，再留下原本的候選清單當作紀錄。**

`tools/probe_064_format_reaches_typing.py` 走完一整條梯子（控制組、單臂基線、
抑制重繪、把 D1 的存檔放進重繪那一格、換成粗體、拿掉輪詢、把 runner 的
inline 區塊原樣重播、每一臂都存一次檔、把三個動作拆開一次做一個）。關鍵的
幾格：

| 臂 | 做了什麼 | 結果 |
|---|---|---|
| 控制組 | 抑制旗標的三態正向對照 | **PASS**——計數器與畫布都咬得到 |
| `baseline` | 單一 `set-italic` 臂，出貨行為，重繪照跑 | **italic: true**——**沒有重現** |
| `runner-sequence` | runner 的 inline 區塊，原樣，一次載入 | **八個臂全錯**（`set-bold` 是第一個） |
| `runner-sequence-saved` | 同上，但**每一臂存一次檔** | **打字當下八個臂全對** |
| `retention-ladder` A/B | 一次只做一個動作 | **是 `insert-paragraph-break`，單獨一個** |

`baseline` 沒重現這件事本身就是這一輪的轉折：探針的判定邏輯在負向對照沒紅的
時候**拒絕讀後面任何一臂**，所以沒有走成「重繪不是肇因，換下一個候選」。

任何時刻文件裡**只有一個 `<text:span>`**，就在剛打的那個標記上，而且帶著那一臂
要的格式。原始 ODF，在那一次單獨的 Enter 前後：

```xml
<text:p text:style-name="P3"><text:span text:style-name="T1">RETLADDERONE</text:span>1-LC-NUMBER-ONE</text:p>
```
```xml
<text:p text:style-name="P3">RETLADDERONE</text:p>
```

span 不是被清空或改寫，是**從留在原地的那段字上不見了**——而在 `retention` 那一臂
裡，它出現在**接下來打的字**身上（那一臂根本沒按任何格式鍵）。

**所以 D1 與產品那條路從頭到尾一致。**D1 每個 cell 之後各存一次檔，因此從來沒有
問過「前一個 cell 的格式還在不在」。兩邊沒有分歧，是被問了不同的問題。

### 原本列的候選（保留，全部作廢）

已知的路徑差異（列出來當作下一輪的候選，不是結論）：

- D1：`collapsedAt(client, …)` → `client.action(…, {enabled})` → `handle.insertText(marker)`
- 產品：canvas 點擊 → `session.action(action, {enabled})` → `session.commitText(text)`

`commitText` 最後也是 `document.insertText`（`editor-shell/editor-session.js:510`），
所以**插入那一段本身是同一個呼叫**。差別在外面：產品的 `run()` 在每個動作之後
`await renderDocument()`（`web/e2-editor-app.js:377-382`），也就是在「設格式」與
「打字」之間插進一次 `getDocumentSize` ＋ `paintTile`。

一次重繪會不會把 core 的 pending character attribute 清掉，**沒有量過**。
它是候選，不是答案。

## 一個量測上的陷阱，記下來因為它會再犯

第一版的檢查把六個標記**連續打在同一個位置**，六個全部併進**一個** `text:span`：

```xml
<text:span text:style-name="T1">MKITALONMKITALOFFMKUNDONMKUNDOFFMKSTRONMKSTROFF</text:span>
```

而 `T1` 是：

```xml
<style:text-properties style:text-line-through-style="none"
  style:text-line-through-type="none" fo:font-style="normal"
  style:text-underline-style="none" …/>
```

**收合游標上的格式動作會重新套用到游標所在的那個 run**，所以後面每一次按下去都
把前面已經打好的標記重新格式化了一遍，最後只剩最後一臂的狀態。

看穿它的線索是那幾個**明確寫出來的 `"none"` 與 `"normal"`**——「沒有格式」不會
把自己拼出來。處方是每一臂先按 `insert-paragraph-break`，讓標記各自待在一個空段落
裡，那裡沒有東西可以被重新套用。

（順帶一提：ODF 不用布林值表示底線與刪除線，用的是**線條樣式**，關掉的值是字串
`"none"`。判準若問「屬性在不在」，會把「明確關掉的底線」讀成「有底線」——而那正是
2026-08-19 連結出貨、至今沒有人驅動過的那個方向。`tests/test_inline_styles_of.py`
把這一條釘住了。）

## 為什麼這麼久沒被發現

`bold-can-be-turned-off-again` 是唯一驅動過 inline 格式的產品檢查，而它的判準是
**`aria-pressed`**——也就是頁面自己對「引擎說了什麼」的快取。

**這一點現在是量到的，不是推測的。**同一輪裡：

| | |
|---|---|
| `bold-can-be-turned-off-again` | **綠**。`aria-pressed` 走 `false → true → false`，完全正確 |
| 同一輪的文件側 | `MKBOLDON` 與 `MKBOLDOFF` **都沒有粗體** |

快取被寫對了，文件從來沒有被改到，而那一格檢查看的只有快取。所以
**一個 `done` 的格子，靠的是一個看不見這個缺陷的檢查**——這跟 044 是同一個形狀，
只是換了一層。`turn-formatting-off` 那一列的證據需要重新看。

`e2/product-path-coverage.json` 把 `set-italic`／`set-underline`／`set-strikethrough`
標成 `uncovered`、風險 `LOW`，而那三行風險是在**產品根本讀不回那些狀態的時候**
寫的。

## 現在怎麼標（2026-08-22 撤銷後）

`every-inline-format-reaches-the-document` **是綠的**，四個格式兩個方向，
兩個瀏覽器。`clear-format-removes-every-inline-format` 也從長期
`NOT_ESTABLISHED` 變綠。`KNOWN_RED` **空了**——這是這個檔案第三次空。

判讀工具已修（`inline_styles_of` 現在解析段落樣式並回報 `fromParagraphStyle`），
`tests/test_inline_styles_of.py` 多了四個段落載體的案例，**其中三個在修好之前
會紅**。

## 這一輪真正學到的

1. **這棵樹裡沒有任何自動化抓得到這個錯**，因為每一個有機會抓到它的檢查，都在
   同一個 `inline_styles_of()` 的下游。**判讀工具的錯不會被下游的檢查發現。**
   抓到它的是一個人的眼睛對上存檔的讀數。
2. **「不在 span 裡」不等於「沒有格式」。**這句話當初是**刻意**寫進註解裡的
   （「this asks about INLINE formatting, and text that is not in a span has
   none of it」），而它是錯的。一個被寫下理由的錯誤決定，比沒寫理由的更難發現，
   因為它看起來已經被想過了。
3. **連錯兩次的形狀是一樣的**：兩次都是問了文件一個它不會那樣回答的問題，
   然後從答案裡讀出一個機制。第一次讀出「產品那條路壞了」，第二次讀出
   「斷行會拿走格式」。兩次都很有說服力，兩次都是零。

## 下一步

1. `bold-can-be-turned-off-again` 的判準仍應從 `aria-pressed` 改成文件——理由不是
   bold 壞掉（它沒有），而是**快取不是文件**。
2. `findings/evidence/064/` 裡的五份診斷報告是**用壞掉的判讀工具跑的**，READMEs
   已標註。它們對「機制」的判讀不成立；對「哪一臂做了什麼」的紀錄仍然有效。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-21 | 首次記錄：四個 inline 格式八個臂全錯，歸因到產品那條路，機制未定，候選是 `renderDocument()` |
| 2026-08-21（同日） | 第一次改判：格式有到打出來的字上（**這一句對**）；但把毀掉證據的機制指認成下一臂的 `insert-paragraph-break`，並據此另立 065（**這一段錯**） |
| 2026-08-22 | **整張撤銷，真正的原因是 `inline_styles_of()` 看不到段落層級的格式。**修好之後連原本「一次存檔讀八個答案」的讀法都是全對的。065 一併撤銷。operator 人工輪抓到 |

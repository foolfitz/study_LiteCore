# 065 — 在剛套過格式的那段字結尾按 Enter，**那段字的格式被拿走**

> # 撤銷（2026-08-22）
>
> **這個缺陷不存在。**格式一直都在。
>
> 判讀工具 `inline_styles_of()` 停在「標記不在 `<text:span>` 裡，所以它沒有任何
> 格式」——**ODF 不是這樣運作的**。一個**整段一致**的段落，LibreOffice 會把字元
> 屬性寫進**那個段落自己的 automatic style**，而且**完全不產生 span**：
>
> ```xml
> <style:style style:name="P3" style:family="paragraph" style:parent-style-name="Standard">
>   <style:text-properties fo:font-weight="bold" .../></style:style>
> <text:p text:style-name="P3">RETLADDERONE</text:p>
> ```
>
> 而「標記獨自待在自己的段落裡」正是每一臂都會產生的狀態。所以斷行之後
> `spans` 從 1 掉到 0 是**正確的匯出**——粗體從 span 搬到了段落樣式上，
> 因為那一段變成整段都是粗體。**沒有任何東西被拿走。**
>
> 修好判讀工具之後把同一個臂原封不動重跑：
>
> ```
> a paragraph break, alone | bold True | carrier paragraph | styleName P3 | spans 0
> ```
>
> **是 operator 抓到的**（2026-08-22）：他在畫布上看得到粗體，而存檔讀回來是
> `bold: false`。這棵樹裡沒有任何自動化抓得到它——每一個有機會抓到的檢查，
> 都在同一個函式的下游。
>
> [064](064-RETRACTED-an-inline-format-set-in-the-product-never-reaches-the-text-you-type.md)
> 是同一個錯誤的另一個角度，也撤銷了。下面原文保留，因為它把這個錯誤推得夠遠，
> 遠到可以被看穿——**但它每一句結論都不成立**。

| | |
|---|---|
| **狀態** | **撤銷（2026-08-22）**——缺陷不存在，是判讀工具的偽陰性 |
| **Bugzilla** | —（**層級未確認**，不得送出；見〈歸因〉） |
| **發現日** | 2026-08-21（追 [064](064-RETRACTED-an-inline-format-set-in-the-product-never-reaches-the-text-you-type.md) 的機制時掉出來的） |
| **嚴重度** | **高**——使用者打的粗體字，在他按下 Enter 開始下一段的那一刻不再是粗體，而且沒有任何提示 |
| **可重現** | **Chrome 與 Firefox 都是 100%**——出貨的 `run_e2_c_product_path.py` 以 `formatting-survives-the-next-paragraph-break` 驅動，兩個瀏覽器都 `boldWhenTyped: true → boldAfterBreak: false`。機制的 A/B 對照臂在 Chrome 各 1/1 |
| **是否上游** | **未確認**——斷行是一個 `.uno:InsertPara`，產品那一側沒有東西夾在中間，但「不是產品」不等於「是核心」 |

## 現象

在出貨的產品頁上：

1. 把收合游標放進一段文字裡。
2. 按工具列的 **B**。
3. 用產品自己的插入欄位打一段字。**這段字是粗體的**——存檔可以確認。
4. **緊接著按 Enter**（`insert-paragraph-break`），不做別的。
5. 再存一次檔。

（「緊接著」是量到的範圍。斷行落在文件別處會不會也拿走格式，**沒有量過**，
見〈限制〉。）

**預期**：第 3 步打的那段字仍然是粗體。
**實際**：**它不再是粗體。** `<text:span>` 從留在原地的那段字上消失，整份文件的
span 數從 1 掉到 0。而如果接著再打字，**新打的字是粗體的**——格式跟著游標走了。

沒有錯誤、沒有 toast、狀態列停在 `ready`、revision 正常前進。

## 重現步驟（自動化）

```
cd wasm_sdk_probe
python3 tools/probe_064_format_reaches_typing.py --browser chrome \
    --arms retention-ladder-adjacent,retention-ladder
```

`retention-ladder-adjacent` 應該是 **FAIL**（`lostAt` = `a paragraph break, alone`），
`retention-ladder` 應該是 **PASS**。兩臂只差一件事：Enter 送出時，游標還在不在
剛套過格式那一段的結尾。

> 這支探針是為了 064 寫的診斷工具，跑的是 `dist/` 的符號連結鏡像，
> **只有一個檔不同**（`e2-editor-app.js` 頂端一個計數器＋提前 return，
> 沒有 `globalThis.__f064` 時完全惰性），`probe.wasm` 與出貨的位元組相同，
> 不寫 `dist/`。報告一律 `evidenceClass: "diagnostic"`。

## 證據

**出貨那一側**（沒有鏡像、沒有補丁、沒有探針）：
`findings/evidence/065-retracted/shipped-runner-chrome.json` 與
`…-firefox.json`——兩個瀏覽器的
`formatting-survives-the-next-paragraph-break` 都紅，觀測值完全一樣。

**機制那一側**（診斷輪）：`findings/evidence/064/product/05-retention-ladder-ab.json`，
判讀寫在 `findings/evidence/064/RESULT-render-between-format-and-typing.md`。

一次單獨的 Enter 前後，原始 ODF：

```xml
<text:p text:style-name="P3"><text:span text:style-name="T1">RETLADDERONE</text:span>1-LC-NUMBER-ONE</text:p>
```

```xml
<text:p text:style-name="P3">RETLADDERONE</text:p>
```

**承重的是 `-adjacent` 這一臂**，它是同一臂內部的前後對照，一次只做一個動作，
每一步存一次檔，每次問同一個標記：

| 步驟 | 粗體 | 全文 span 數 |
|---|---|---|
| 斷行 ＋ `set-bold` ON ＋ 打標記 | **true** | 1 |
| `move-character-left` | true | 1 |
| `move-character-right` | true | 1 |
| **`insert-paragraph-break`，單獨一個** | **false** | **0** |

`spans` 是對整份 `content.xml` 數 `<text:span`，**不是只看那一段**——所以 1→0 的
意思是那個 span 離開了**文件**，不是搬到隔壁段落。游標在 run 內部左移再右移不會
發生；一次斷行就會。

另一臂（`retention-ladder`，游標先離開再回來）那次斷行沒有拿走格式，但**它不是
一個對得起來的對照組**，見下面〈限制〉第 1 條。

## 分析

看起來像是：在收合游標上套用的 inline 格式，在游標還停在那段字尾端的期間，其
hint 仍然是「開著的」；這時候的 `.uno:InsertPara` 把那個 hint **帶進新段落**，而
不是在分割點兩邊各留一份。`retention` 那一臂直接看得到後果：斷行之後打的字**沒
有按任何格式鍵就是粗體的**。

**這是描述，不是歸因。**

## 歸因：只做到「不是產品那一側」

斷行在引擎裡是一句 `startEditorUnoAction(command, name, ".uno:InsertPara")`
（`src/probe_engine.cpp:4413`），產品只是把它派送出去；格式與遺失之間沒有任何
產品程式碼。**但這只排除了產品，沒有指認層級**——040、048、062 三次的教訓都是
同一句：沒有原生量測之前不得說是核心的。

**下一步是一輪原生對照**：在桌面／原生 LOK 上跑同樣的三步（收合游標套粗體、打字、
按 Enter），看是不是同樣掉。掉了就是上游，草稿才能開始寫；沒掉，就要往我們這一側
的 `.uno:InsertPara` 路徑上找差別。

## 已經進了回歸網

出貨的產品路徑 runner 有一格具名這張單：

```
formatting-survives-the-next-paragraph-break   （KNOWN_RED，具名 065）
```

判準是使用者的那一句：按 B、打字、按 Enter，標記在**自己那一次存檔**裡是粗體，
在**只多了一次斷行**的下一次存檔裡還要是粗體。**前置條件是這一格的一半**——標記
如果本來就不是粗體，它不能拿來證明「變成不是粗體」，那一臂報 `NOT_ESTABLISHED`
而不是紅。

`KNOWN_RED` 的宣告一旦過期（這一格變綠），runner 會讓整輪失敗，所以這張單不會比
缺陷活得久。

## 這件事的兩個限制，寫出來因為它們還沒被量

1. **「同一個 Enter 在別的位置就沒事」目前不成立，別引用它。**（2026-08-21 外部
   審核指出，我自己重讀報告確認。）活下來的那一臂和 `-adjacent` 差了**三件**事，
   不是兩件：

   - 游標離開了 run 又回來；
   - 因此那次斷行落在**段落開頭**而不是 run 的結尾——它插進去的是一個空的
     `<text:p text:style-name="P2"/>` list-item，**在標記那一段之前**；
   - 而且那一次載入的 `LINE_INK` 在 y=0.24 **沒有找到 ink**，所以點擊用的是
     退版的視窗比例（`derived: false`，near `0.06`＝左邊界），而 runner 自己的
     註解就寫著邊界上的點擊會被引擎吸到字元位置 0。**兩臂連游標怎麼瞄都不一樣。**

   所以這張單**只主張**：打完格式化的字之後緊接著的那次斷行會把格式拿走。
   **不主張**斷行落在別處就安全——那沒有被量到，而且那一臂的幾何是壞的。
   要量它，需要一次「回到 run 正好結尾」的點擊，以及一個 `derived: true` 的載入。
2. **只量了粗體。**四個格式共用同一條派送路徑，但那是推論。（瀏覽器這一半不再是限制：Chrome 與 Firefox 兩邊的回歸網格子都紅，數字相同。）

## 這件事對連結的影響（**已作廢，見開頭的撤銷**）

原文寫的是「它不在連結清單裡，但它的層級未確認」。既然缺陷不存在，就沒有東西要
歸因，也沒有東西要進清單。

## 撤銷之後剩下什麼

一格**會過**的檢查：`formatting-survives-the-next-paragraph-break` 留著，只是
不再是 `KNOWN_RED`。它問的是使用者的那一句——按 B、打字、按 Enter，那段字還是
粗體——而在這一天之前**沒有任何檢查問過**。它現在是綠的，而且它綠得有意義。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-21 | 首次記錄：斷行拿走剛打的字的格式，Chrome／Firefox 都 100%，層級未歸因 |
| 2026-08-21（同日） | 收窄主張範圍：外部審核指出兩個對照臂差了三件事（其中一臂 `derived: false`，幾何退版），撤掉「同一個 Enter 在別處就沒事」那一句 |
| 2026-08-22 | **整張撤銷。** operator 人工輪掉出判讀工具的偽陰性：`inline_styles_of()` 看不到段落層級的格式。修好之後同一個臂回報 `bold True`。缺陷不存在 |

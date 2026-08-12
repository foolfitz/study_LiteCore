# 035 — 後置條件讀取對「有字元格式或含中日韓文字」的段落一律 fail closed

| | |
|---|---|
| **狀態** | **已確認並已修（2026-08-12，引擎 `ee185b3d…`，實測關閉）** |
| **Bugzilla** | —（我方 readback 的封閉標籤集，非上游） |
| **發現日** | 2026-08-11 |
| **嚴重度** | **嚴重（產品面可能比 034 更重）**——中文文件的每一段都會踩到 |
| **可重現** | 100%（`caret-offset-discriminator/`，`bd102b4a` 與 `38168306` 兩個 build 各一次） |
| **是否上游** | **否** |

## 摘要

路線 C 的後置條件讀 `getTextSelection("text/html")`，再由 `parseFormatReadback`
掃 `<body>` 內的開標籤序列。封閉集合是：

```cpp
bool formatTagIsKnown(const std::string &tag) {
  return tag == "ul" || tag == "ol" || tag == "li" || tag == "h1" || tag == "p";
}
```

**遇到集合外的任何標籤就 `unknownTag = true` 並中止**，`formatBarrierReadbackSatisfied()`
第一行就因此回 false，動作被回報 `EDITOR_FORMAT_POSTCONDITION_FAILED`。

而序列化器對兩種**極其普通**的段落都會寫出集合外的標籤：

| 段落內容 | 實測 markup | 觸發標籤 |
|---|---|---|
| `Normal **bold anchor** and *italic anchor*.` | `<p ...>Normal <b>bold anchor</b> and <i>italic anchor</i>.</p>` | `<b>`／`<i>` |
| `第三段跨行 gamma` | `<p ...><font face="Noto Sans CJK KR"><span lang="zh-TW">第三段跨行 </span></font>gamma</p>` | `<font>`／`<span>` |

第二列是重點：**只要段落裡有中日韓文字，序列化器就會為那段字型換 run**，
包成 `<font>` + `<span>`。這不是特殊格式，是中文文件的常態。

## 為什麼 375 次判定派送一次也沒碰到

A3／A4／A5 的錨點段落是 `E1-STYLED-END`、`E1-MULTI-END omega`、`E1-PLAIN-END`
——**全部是純 ASCII、且所在段落沒有任何 run**。

fixture 裡明明有中文（`multi-paragraph` 五段有三段是中文、`plain-grapheme`
有 `臺灣中文游標測試`），但**沒有一段是被派送的那一段**。

與 [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)
是同一個形狀，換一個軸：覆蓋矩陣沒有「段落內容形態」這條軸，
所以「格式化段落」與「中文段落」從來沒有被派送過。

## 怎麼被抓到的

不是想到的，是 **034 的修法把它逼出來的**。

修法之前，`offset-zero` 的鑑別案例讀到的是**上一段**（純文字標題），所以失敗被歸因為逃逸。
修法之後 barrier 開始讀**對的那一段**——而那一段正好是唯一帶 `<b>`／`<i>` 的段落
——於是同一個案例仍然失敗，但原因換了。

當時的第一反應是「修法造成退步」。用 offset `Len()`（不可能逃逸）重跑同一段：
**兩個 build 都失敗，`unknownTag=true` 都是 true**——所以是既有缺陷，不是新的。
那一列現在留在鑑別器裡叫 `inline-formatting-readback`，就是為了讓這兩個原因
不能再被混為一談。

## 實測

證據：`findings/evidence/sdk-e2/discovery/caret-offset-discriminator/`
（`analysis.json` 有完整七列對照）。Chrome 150.0.7871.128。

| fixture ／ 案例 | `bd102b4a`（修法前） | `38168306`（修法後） |
|---|---|---|
| styled-list ／ `inline-formatting-readback` | 失敗，`unknownTag=true`，讀對段 | **完全相同** |
| multi-paragraph ／ `offset-zero-escapes-to-previous` | 失敗，`unknownTag=true`，讀**上一段** | 失敗，`unknownTag=true`，**讀對段** |

第二列同時示範了兩件事：034 的逃逸**已關閉**（讀對段了），
而本單的缺陷**照舊**（碼沒變）。

## 修法已定案（2026-08-11 實測，證據 `readback-format/native-26-8/`）

三條路都量過了，**選 (B)：HTML ＋ odfdom 形狀的結構根分類**。

### 為什麼不是 ODF

`getTextSelection` **讀得到** ODF 套件——回傳的 hex 前綴是 `504b030414`（`PK\x03\x04`，ZIP）
——但 `strlen` 只有 **5**，因為第 6 個位元組是 NUL。`convertOString`（`init.cxx:377`）
用 `memcpy` 且註解明寫容得下 NUL，**但這條 API 不回傳長度**，呼叫端無從得知資料到哪裡結束。

`getClipboard(NULL, …)` 可以：它由 core 自己列舉 `getTransferDataFlavors()`，
量到 **8 個 flavour**，ODF 那份是 **6411 bytes**。代價兩項，加起來不成比例：
它讀的是**剪貼簿**不是選取，所以每次格式動作都得 `.uno:Copy`，**洗掉使用者的剪貼簿**；
而且拿到的是 ZIP，引擎要在 WASM 裡解 `content.xml`。

（負控制 `application/vnd.oasis.opendocument.text` 回 false——探針能報失敗。）

**已列舉但未分析：`text/rtf` 與 `text/richtext`**（各 3354 bytes）。它們出現在那 8 個
flavour 裡，本輪**只量到大小，沒有看過內容**——所以 commit `78d6ac3` 的訊息
「three readback formats measured」不準確：實際被分析的是 ODF、HTML、Markdown 三種，
RTF 兩種只被列舉。不追下去的理由不是懶：RTF 的清單判定要讀 `\listoverride` 表與樣式狀態，
比掃一串標籤重得多，而 HTML 這條已經有可行解。**若 (B) 在 M2 被推翻，這裡是還沒開的門。**

### 為什麼不是 Markdown——這條差一點就成立

`text/markdown` 一度是最強候選：五個封閉動作各有乾淨前綴（`- `／`1. `／`# `／無），
三種段落形態一致，而且**中文完全沒有包裹**——本單的成因在 Markdown 裡不存在，
不是被繞過而是消失。多段防護也活得下來（區塊間是空行）。

擋下它的是一項**先列為未量、後來去量**的事：**段落文字本身就以那些字元開頭時，
匯出器有沒有跳脫？**

| 段落（純段落，非清單非標題） | Markdown 輸出 | 跳脫？ |
|---|---|---|
| `# MD-HASH …` | `\# MD-HASH …`（hex `5c23`） | **有** |
| `> MD-QUOTE …` | `\> MD-QUOTE …`（hex `5c3e`） | **有** |
| `* MD-STAR …` | `\* MD-STAR …`（hex `5c2a`） | **有** |
| `- MD-DASH …` | `- MD-DASH …`（hex `2d20`） | **沒有** |
| `1. MD-NUMBER …` | `1. MD-NUMBER …`（hex `312e`） | **沒有** |

沒跳脫的兩個，正是兩個清單標記。對照真的清單項：

```
純段落：  '- MD-DASH is a plain paragraph\n'
真清單項：'- MD-REAL-ITEM is a real list item\n'
```

**形狀上無法區分。** 於是 `set-list-unordered` 派送在一個碰巧以 `- ` 開頭的段落上，
即使清單根本沒套用也會讀成「已滿足」——**誤報**，正是整個 barrier 存在的理由所要防的方向。
標題那條軸是安全的（`#` 有跳脫），但一條軸安全救不了設計。

**考慮過而否決的搶救法**：`text/plain` 對真的清單項**不帶**標記
（`'MD-REAL-ITEM is a real list item'`），Markdown 帶——所以「markdown 減 plain」能還原標記，
原理上可鑑別。否決理由兩點：要兩次讀取加上一條被跳脫反斜線與結尾換行弄得脆弱的前綴相減規則；
而且**它依賴跳脫不完整這件事**——上游哪天把 `\-` 補上，那條相減規則就默默改變意義。
建立在缺陷上，然後把它當契約。

### 定案：(B)，而結構清單來自實測

六個 fixture、17 個錨點的標籤盤點：**在 body 層出現的只有 `p`（14）、`h1`（1）、`ul`（1）**；
`b`／`i`／`font`／`span` 的 `atBodyLevel` **全部是 0**，`li` 只出現在 `ul` 內。
**沒有任何非結構標籤出現在 body 層**——(B) 賴以成立的前提有實測支撐。

**閉標籤與巢狀盤點（2026-08-11 追加，M1）**：上面的盤點只看開標籤，而規則 2 靠的是
「深度」，深度要靠閉標籤才算得出來。於是把同一批 readback 的 25 筆輸入重掃一次
（24 筆分析、1 筆 `plain-grapheme／combining é boundary` 當初沒落到位、82 個標籤事件）：

| 問題 | 結果 |
|---|---|
| 開閉是否平衡 | **是**，24 個錨點的最終深度全是 0 |
| 深度是否曾為負 | **否**（`wentNegative` 全 false） |
| 有無 self-closing 的結構標籤 | **沒有**（`<p/>` 不存在） |
| 巢狀是否 well-formed | **是**：close 與 stack top 不符 0 次、未關閉 0 次 |
| 非結構標籤出現的深度 | **只在深度 1**（`b` 6、`font` 12、`i` 2、`span` 6 個事件），深度 0 **零次** |

盤點腳本用合成的違規片段驗過自己的每一條回報分支（深度 0 的非結構標籤、負深度、
self-closing 結構標籤、無斜線 void tag、stack mismatch、未關閉）——**能報得出違規**。

**這批 body 裡 `br` 出現 0 次，但不能讀成「void tag 不存在」**：更早的 `selecttext-result`
探針量到空段落是 `<p><br/><br/></p>`，而本語料的 empty-paragraph 錨點指的是那份 fixture
裡**有文字**的兩段，空段落本身從來沒被讀過。parser 仍必須處理 void tag。
`ol` 同理——它只出現在動作掃描那批，不在 readback 那批。

**規則三條**：

1. **結構標籤**：`p`、`h1`、`ul`、`ol`、`li`（`ol` 由動作掃描產生）。
   **結構標籤在任何深度都照常辨識與計數**——`blockCount`／`itemCount`／`listTag`／`blockTag`
   的語意一個字都不改。
2. 掃描器維護一個**結構深度**：結構開標籤 +1、結構閉標籤 −1，下限箝在 0。依位置分流的
   **只有非結構標籤**：
   - **深度 ≥ 1 的非結構開標籤 → 忽略。**（`<b>`／`<i>`／`<font>`／`<span>` 全落在這裡，
     這就是本單的成因。）
   - **深度 0 的非結構或未知開標籤 → `unknownTag` 並中止。**
   - **深度 0 的結構閉標籤 → 格式異常，同樣中止。**
3. **`unknownTag` 要最先判**，排在 `multiBlock` 與 containment 之前——現行版本把它藏在
   `formatBarrierReadbackSatisfied()` 裡，而中止時計數是被截斷的，`multiBlock` 已無意義。
   失敗碼 `MUTATION_OUTCOME_UNKNOWN`、`failureShape: "unknown-structural-tag"`，
   **並把肇事的標籤名寫進證據**（否則「拒絕過」不能回答「拒絕了什麼」）。

odfdom 的對應：`OdfElement::getComponentRoot()` 往上走到最近的 component root
（只有九個元素宣告自己是）——**是「往上找根」，不是「進了根就不再看」**。
不變式由「沒看過的標籤一律拒絕」變成「**任何可能改變答案的標籤都必須是已知的**」。

> **2026-08-11 修訂。** 本節初版的第 2 條寫的是「**進入結構標籤後，裡面遇到的任何標籤
> 一律忽略**」——**錯的，而且會把 034 的修法拆掉一半**。實測 `li` 的 `atBodyLevel` 是 0
> （它永遠在 `ul`／`ol` 裡），`<p>` 在清單裡也永遠在 `li` 裡；照初版規則兩者都會被忽略，
> `itemCount` 歸零、`blockCount` 歸零、`blockTag` 變空字串，A3／A4 會整批掛掉。
> 錯誤由外部覆核（fable）指出，經我覆算屬實。上面的版本是更正後的。

**界線**：盤點受語料所限。被探測的段落裡沒有超連結、註腳、註解錨點或行內圖片；
`table`／`td` 一次都沒出現（在表格儲存格裡 `SelectText` 序列化成單純的 `<p>`）。
「沒有違例」是量到的形態上的證據，不是對整個 ODF 的證明。
要不要把 `table`／`td`／`h2`–`h6`／`blockquote` 也納入結構清單**尚未決定**——
現在加就是憑想像列清單，而那正是這支探針存在要避免的事。

### M2 已完成（2026-08-12，證據 `paragraph-content/native-26-8/`）

新 fixture `paragraph-content`（`920ca5d5…`），21 種段落形態各選取一次讀回 HTML。
既有六份 fixture 重生成後**位元組完全相同**（對 git HEAD 的 blob 逐一比對，
語料 manifest 的 diff 只有新增、沒有任何既有列被改動）——它們的 sha256 是
A3／A4／A5 判定所綁的文件身分（[027](027-r8d-verdict-silently-outlived-its-release.md)）。

**結果：(B) 的前提成立。深度 0 出現的非結構標籤只有一個 `div`，成因只有註腳。**

| 深度 0 | 來自 |
|---|---|
| `p` | 普通段落、Title、Subtitle、超連結、書籤、註解、行內圖片、硬斷行、中文＋粗體、section 內段落、**outline level 7 與 10** |
| `h2`–`h6` | ODF outline level 2–6，一對一 |
| `pre` | Preformatted Text |
| `blockquote` | Quotations |
| `ul` | 真清單項（`li` 在內） |
| **`div`** | **僅註腳**（`<div id="sdfootnote1">`） |

`a`（4 次）、`b`、`i`、`br`、`img`、`font`、`span`、`sup` **全部只在深度 ≥1**。

**結構集合定案**：`p`、`h1`–`h6`、`pre`、`blockquote`、`ul`、`ol`、`li`。
**進集合就必須計入 `blockCount`**（`ul`／`ol` 維持容器不計、`li` 走 `itemCount`）——
收了卻不計數，選取跨進 `pre` 鄰居時 `blockCount` 仍是 1，034 的防護就漏了。
`pre`／`blockquote` 收進來**不新增任何放行路徑**：滿足判定要求 `blockTag == expected`
（expected 只會是 `p`／`h1`）或第一個標籤是 `ul`／`ol`，它們永遠滿足不了；
收錄的意義是把「未知標籤」這句謊話換成「現況不是目標」這句實話。

**h7–h10 沒有對應的 HTML 標籤，序列化器把它們寫成 `<p>`**——既沒有夾到 `h6`
也沒有硬造 `<h7>`。所以 **outline level 7 以上的標題在 readback 裡等同內文段落**，
與 Title／Subtitle 同一類收窄。今天無害（封閉動作集只有一級標題），
但「套用第 N 級標題」一旦存在，N ≥ 7 就是根本無法驗證。**這一列是補量出來的，
不是猜出來的**：先前只放了 level 2／3／6，照直覺結案會得到正確的結構集合、
卻漏掉這個收窄。

### 註腳：外部裁決 (a′)，fail closed 具名拒絕

帶註腳的段落讀回來是**兩個 body 層區塊**：

```html
<p …>PC-FOOTNOTE paragraph with a note<a class="sdfootnoteanc" …><sup>1</sup></a></p>
<div id="sdfootnote1"><p class="sdfootnote"><a …>1</a>Footnote body text.</p></div>
```

`div` 收或不收，**帶註腳的段落都會被拒絕**（不收＝深度 0 遇非結構標籤中止；
收了＝`blockCount=2` 觸發 034 的多段防護）。裁決為 **(a′)**：

- `div` **不進**結構集合；深度 0 的 `div` 若符合已量測的註腳簽名（`id` 以 `sdfootnote` 開頭），
  以**專屬** `failureShape: footnote-apparatus-readback` 拒絕，與 `multi-block-readback`、
  `unknown-structural-tag` 三者互斥。
- **駁回「`div` 內不計入 `blockCount`」**：034 的失效模式是**無聲的誤報成功**，
  而深度 0 `div` 的樣本數是 **1**。拿 n=1 的假設豁免一道已量測、已出貨的防護，方向錯了。
- **駁回「沿用 `multi-block-readback`」**：理由不是訊息誠實度而是**遙測通道**——
  每個註腳段落都灌進去之後，「034 真的攔到跨段」與「使用者碰了註腳」再也分不開。
  同理不沿用 `unknown-structural-tag`：那個通道要留給**真的沒量過**的形狀。
- 失敗碼**維持 `MUTATION_OUTCOME_UNKNOWN`**，而且這不是將就：路線 C 無條件派送，
  讀回失敗時**變更可能已經發生**。發明「已拒絕執行」類的新碼會把
  「派送了但無法驗證」謊報成「沒動你的文件」。
- 簽名**只用來選拒絕的標籤，永遠不把拒絕變放行**——比對錯誤的最壞情況是訊息標錯。

**簽名的兩項源碼更正（2026-08-12，讀 `libreoffice-26-8/sw/source/filter/html/`）**：

1. **簽名必須同時認 `sdfootnote` 與 `sdendnote`。** `htmlftn.cxx:344-356` 的
   `OutFootEndNotes()` 裡，尾註走的是另一條分支：

   ```cpp
   m_nFootNote = 0;  m_nEndNote = 0;
   for( auto *pTextFootnote : *m_xFootEndNotes ) {
       if( m_pFormatFootnote->IsEndNote() )
           sFootnoteName = OOO_STRING_SVTOOLS_HTML_sdendnote  + OUString::number(++m_nEndNote);
       else
           sFootnoteName = OOO_STRING_SVTOOLS_HTML_sdfootnote + OUString::number(++m_nFootNote);
       …  "<" + GetNamespace() + OOO_STRING_SVTOOLS_HTML_division " id=\"" …
   ```

   只認 `sdfootnote` 的話，**帶尾註的段落會掉進 `unknown-structural-tag`**——
   正是裁決要求把通道分開所要避免的污染。本節初版只寫了 `sdfootnote`，已更正。
2. **深度 0 的 `div` 不是註腳專屬，所以「讀 `id`」是源碼上的要求而不是偏好。**
   HTML writer 至少七處會寫出 `div`：註腳（`htmlftn.cxx:361,384`）、
   fly frame（`htmlflywriter.cxx:434,519,1742,2112`）、段落屬性（`htmlatr.cxx:815`）、
   section／多欄（`wrthtml.cxx:564,758`）、表格（`htmltabw.cxx:1066,1072,1121`）。
   「深度 0 的 `div` 一律當註腳」會把其中六類誤標。

**順帶一提，這比量測更強**：`div` 是字面量、id 是「固定字串＋遞增整數」，
沒有容器走訪順序、沒有 locale、沒有平台相依——簽名的穩定性**由構造保證**，
不是靠量到一次。

**這是收窄，要寫進規格**：帶註腳的段落無法套用清單或標題。要把它改成放行，
入口是下面的註腳邊界量測，不是重新論證。

### 還沒關的洞

1. **build 缺口（已縮小，未關閉）**：M2 量的是原生 26.8，barrier 出貨在 wasm `38168306`。
   既有 wasm 證據已對過重疊形態（清單／粗體斜體／中文／清單內空段落），
   **標籤結構一致但不是位元組相同**（`style` 的 CSS 屬性順序兩邊相反）。
   2026-08-12 追加兩項核對，把缺口從「是不是同一份程式碼」縮成「同一份原始碼、不同工具鏈」：
   wasm profile 的 `sdk-manifest.json` 與原生探針**同一個 `coreCommit` `671c848b…`**；
   `wasm-lite/patches/` 的八個 patch **沒有一個碰 `sw/` 或 `filter/`**
   （落點是 build makefile ×3、匯出符號清單、`vcl/qt5/QtFrame.cxx`、Qt WASM plugin ×3）。
   **這是推論不是量測**：同一份原始碼在不同 STL 下仍可能有差異，而已觀察到的那一項
   （CSS 屬性順序）正是無序容器走訪順序的典型症狀。
   **決定（使用者裁示）**：不擋 #27——擷取原本是要保護「註腳簽名」這個設計決定，
   而那個決定現在由原始碼定住（見上），比量一次更強。wasm 側的形態確認**併進 #28 的重掃**，
   那一輪本來就要跑瀏覽器。**風險已知並接受**：若 wasm 側真的不同，會在重編之後才發現。
2. **出貨的 C++ 掃描器從沒吃過這 21 份 capture**——分類全由 Python 重寫做的。
   「`<!` 註解會被跳過」目前是讀碼結論不是執行結果。
3. **只量了動作前**，沒有任何一列是動作後的形狀。
4. **註腳邊界未掃**：游標在註腳本文內、多顆註腳、尾註、跨段時 `div` 還在不在——
   034 就是在唯一沒測的 offset 被抓到的。

**M2 的陷阱（已避開，留給後人）**：`create_e1_corpus.py` 的 `NAMESPACES`、
`STYLES_XML`、`MANIFEST_XML` 與 automatic-styles 區塊是**所有 fixture 共用**的，
往那裡加東西會改掉每一份 fixture 的位元組。新 fixture 必須自帶
namespace／樣式／manifest 項目，且既有六份重生成後要位元組完全相同。

### upstream 註記（低優先，未查重、未回報）

Markdown 匯出對段落開頭的 `#`、`>`、`*` 跳脫，卻不跳脫 `-` 與 `1.`，
**它自己的輸出因此不能 round-trip**：把一個以 `- ` 開頭的純段落匯出再匯入會變成清單項。
與 034 的 `SwWrtShell::SelPara` 註記同一等級。

## 原本列出的修法選項（保留供追溯）

1. **忽略行內標籤**——把「影響判定的標籤」與「段落內可以出現的標籤」分開：
   `<b>`/`<i>`/`<u>`/`<s>`/`<font>`/`<span>`/`<br>` 略過不計，只有 block 與 list
   標籤參與判定與 `multiBlock` 計數。改動小，但要決定「略過清單」本身是不是封閉的
   ——遇到清單外的標籤還是 fail closed，才不會退回「看起來沒問題就放行」。
2. **放寬 `formatTagIsKnown`**——把行內標籤加進已知集合。**不建議**：
   `multiBlock` 與 `blockTag` 的計數會被行內標籤污染。
3. **改用不同的讀取管線**——例如 `getA11yFocusedParagraph`。範圍大，本輪不評估。

fail-closed 的設計意圖（「沒量過的形狀就拒絕」）是對的；**問題在於封閉集合是照
fixture 的樣子量的，不是照文件的樣子量的**。

## 為什麼沒有併進本次 build

本次 build（`38168306`）的改動已驗證完畢並即將綁定 A3–A5 重掃。
把標籤集的修改混進同一個 artifact，兩個改動就都無法各自對應到自己的證據
（finding 027 的 artifact 綁定）。**這是下一個 build 加下一次重掃，不是這一次的搭便車。**

## 相關

- [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)——同樣是「覆蓋軸從未存在」，而且是它的修法把本單逼出來的。
- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)——readback barrier 的由來。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 2.8 節（readback 的封閉標籤集）。

## 已修並實測關閉（2026-08-12，引擎 `ee185b3d…`）

四項改動一次 build：結構深度 parser、結構集合擴為
`p`／`h1`–`h6`／`pre`／`blockquote`／`ul`／`ol`／`li`（且進集合即計入 `blockCount`）、
`unknownTag` 提前判並拆成三個通道（附肇事標籤名）、註腳／尾註簽名。

**燒掉那一次 build 之前先關掉「掃描器從沒吃過這些 capture」這個缺口。** 做法不是抄一份
parser 出來測（那測的是副本），而是寫 `tools/test_format_readback_parser.py`
**從 `probe_engine.cpp` 切出 parser 原文編譯**，並支援 `--revision` 從 git 版本切同一段——
所以改動前後可以對照，而且以後改引擎測試會自動跟上。

| | 舊掃描器 | 新掃描器 |
|---|---|---|
| 21 份 capture 中被拒絕 | **17 列** | 1 列（註腳，走專屬通道） |
| 原本就通過的 4 列 | `PC-PLAIN`／`PC-COMMENT`／`PC-SECTION`／`PC-LIST-ITEM` | **判定完全不變，無退步** |

`PC-COMMENT` 兩邊都過，順帶**用執行結果**證實 `<!--` 會被跳過——先前那只是讀碼結論。

**變異控制兩層。** 對 parser：11 個合成案例，每條分支都觸發，其中
`bare-div-not-a-footnote → unknown-tag(div)` 證明沒有簽名的 `div` 不會被誤標，
`endnote-apparatus → footnote-apparatus` 證明 `sdendnote` 分支有接到。
對測試：把四個新守衛各關掉一次（`if (false && …)`、拿掉 `sdendnote` 分支、
把計數器加上 `depth == 0`、從述詞裡移除中止旗標），**四個變異全部被抓到**，
引擎還原後 sha256 逐位元組一致。第三個變異正是覆核當初抓到的那個致命錯誤。

**在出貨的 artifact 上驗過，不只在原始碼上。** WASM `ee185b3d` 跑 21 種形態：
19 列 verified、`pc-footnote` 回 `footnote-apparatus-readback`（不是 `multi-block-readback`
也不是 `unknown-structural-tag`）、每列 `blockCount=1`、派送段落文字在、鄰段文字不在，每列 38 ms。
舊 build `38168306` 換回來跑同一批：**16 列 `unknownTag`，通過的四列與原生切片測試算出的完全相同**。

**A3／A4／A5 重掃並重綁**：18 輪／90 派送、18 輪／270 派送、8 輪／42 case，零失敗，
判定由 `validate_e2_a.py` 發（A3_PASS／A4_PASS／A5_PASS）。44 輪每一輪跑之前都重算
artifact sha256，不符即中止——同一 session 內為了 finding 037 的對照手動換過兩次 artifact，
那個風險是實際發生過的。

**掃描途中掉出 [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)**：
含行內圖片的段落**卡死 handle**，兩個 build 都重現，未修。

## 修訂紀錄

- **2026-08-11（初版）**：三條路（ODF／Markdown／HTML）實測完畢，定案 (B)。
- **2026-08-11（更正＋補量）**：三處。
  1. **定案第 2 條寫錯了**——初版的「進了結構標籤就忽略裡面所有標籤」會連 `li` 與
     清單內的 `<p>` 一起忽略，`itemCount`／`blockCount`／`blockTag` 全毀，A3／A4 會掛。
     已就地更正為「結構標籤任何深度都照算，只有非結構標籤依深度分流」，並補上
     `unknownTag` 必須最先判、要有獨立失敗碼與肇事標籤名。外部覆核（fable）指出，覆算屬實。
  2. **補上閉標籤／巢狀盤點（M1）**——規則 2 靠深度，而初版只盤點過開標籤。
     24 個錨點最終深度全 0、非結構標籤零次出現在深度 0。同時記下 `br` 與 `ol`
     在這批資料裡出現 0 次**不等於不存在**的界線。
  3. **補記 `text/rtf`／`text/richtext` 只列舉未分析**，並更正 commit `78d6ac3`
     訊息裡「三種格式都量過」的說法。
- **2026-08-12（M2 完成）**：新 fixture `paragraph-content`、21 種形態實測，
  (B) 的前提成立（深度 0 的非結構標籤只有註腳的 `div`）；結構集合定案
  `p`／`h1`–`h6`／`pre`／`blockquote`／`ul`／`ol`／`li`，且「進集合＝進 `blockCount`」；
  補量到 **outline level 7–10 讀回 `<p>`** 這個猜不到的收窄；註腳經外部覆核裁決
  為 (a′) 具名拒絕。過程中修掉兩件會產生假結論的東西：
  **`PC-CJK-BOLD` 原本用共用的 `E1Bold`（只有西文字重 `fo:font-weight`），
  實測回來一個 `<b>` 都沒有**——那一列真正的意思是「這份文件沒有中文粗體」，
  改用帶 `style:font-weight-asian` 的 fixture 專屬樣式後 `<b>` 出現在深度 3；
  **盤點腳本的深度算術原本用引擎現行的窄集合**，於是 Heading 2 裡的粗體會被報成
  「行內標籤出現在深度 0」＝**假的推翻**（同一份合成輸入在舊集合報 `b`、新集合不報）。
  盤點腳本另加兩個檢查：每列深度 0 的結構標籤序列（單段讀取斷言）、
  以及每列的文字有沒有夾帶別的錨點的文字；變異控制擴到九條分支全部觸發。

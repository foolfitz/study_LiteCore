# 035 — 後置條件讀取對「有字元格式或含中日韓文字」的段落一律 fail closed

| | |
|---|---|
| **狀態** | **已確認（兩個 build 各三個 fixture 實測，行為一致）／未修，修法待決** |
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

1. **結構標籤**：`p`、`h1`、`ul`、`ol`、`li`（`ol` 由動作掃描產生）。
2. **進入結構標籤後，裡面遇到的任何標籤一律忽略**——對應 odfdom 的
   `OdfElement::getComponentRoot()` 往上走到最近的 component root（只有九個元素宣告自己是）。
3. **fail-closed 收窄到結構層**：未知的**結構**標籤仍然拒絕，未知的**行內**標籤忽略。
   不變式由「沒看過的標籤一律拒絕」變成「**任何可能改變答案的標籤都必須是已知的**」。

**界線**：盤點受語料所限。被探測的段落裡沒有超連結、註腳、註解錨點或行內圖片；
`table`／`td` 一次都沒出現（在表格儲存格裡 `SelectText` 序列化成單純的 `<p>`）。
「沒有違例」是量到的形態上的證據，不是對整個 ODF 的證明。
要不要把 `table`／`td`／`h2`–`h6`／`blockquote` 也納入結構清單**尚未決定**——
現在加就是憑想像列清單，而那正是這支探針存在要避免的事。

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

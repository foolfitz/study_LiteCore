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

## 修法選項（**未定案**，需要判斷）

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

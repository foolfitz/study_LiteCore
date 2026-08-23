# 074 — LOK reports the first attribute run as the list prefix, so a uniformly formatted numbered paragraph reports its whole text as prefix

| | |
|---|---|
| **狀態** | 可送出（根因確定，附最小修法方向） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-08-22（現象）／2026-08-23（根因） |
| **嚴重度** | 一般——但對任何用 `listPrefixLength` 去切內文的取用端是靜默的錯 |
| **可重現** | 是。標題（有大綱編號、字元格式一致）在 WASM build 上 3/3 |
| **是否上游** | **是** —— `sfx2/source/view/viewsh.cxx`，與平台、與 configure 旗標無關 |

## 現象

`getA11yFocusedParagraph()` 對一個標題回報：

```json
{ "content": "E1-LC-HEADING", "position": 3, "listPrefixLength": 13 }
```

`content` 長度是 13，`listPrefixLength` 也是 13 —— **整段都被宣告成清單前綴**。

測到的三個游標位置（fixture `list-contexts.odt`，profile `a11y-projection`，
core 為 `writer calc` ＋ accessibility）：

| 段落 | content | listPrefixLength |
|---|---|---:|
| `E1-LC-HEADING`（標題） | 13 字 | **13** |
| `E1-LC-ISOLATED 前後都不是清單的段落` | 25 字 | 0 |
| `E1-LC-SPACER` | 12 字 | 0 |

## 根因（讀原始碼確定，非推測）

`sfx2/source/view/viewsh.cxx:554-588`：

```cpp
sal_Int32 getListPrefixSize(const uno::Reference<XAccessibleText>& xAccText)
{
    ...
    aRunAttributeList = xAccText->getCharacterAttributes(0, {UNO_NAME_NUMBERING_LEVEL,
                                                             UNO_NAME_NUMBERING});
    ...
    if (nLevel < 0 || !bIsCounted)
        return 0;

    css::accessibility::TextSegment aTextSegment =
        xAccText->getTextAtIndex(0, AccessibleTextType::ATTRIBUTE_RUN);

    return aTextSegment.SegmentEnd;      // <- 這裡
}
```

回傳的是 **index 0 那個 ATTRIBUTE_RUN 的結尾**，而不是編號前綴的長度。兩者只有在
「前綴自成一個屬性 run」時才相等。

- **項目符號清單通常沒事**：`"• "` 的字元屬性與內文不同，所以第一個 attribute run
  恰好就是前綴。這是它平常看起來能用的原因。
- **字元格式一致的編號段落就會壞**：整段是**一個** attribute run，`SegmentEnd`
  等於整段長度。標題最常中——它有大綱編號（所以 `nLevel >= 0`、`bIsCounted` 為真，
  過得了 `:579` 的門），而標題的字元格式通常整段一致。

## 從我們這一側量到的（2026-08-23 追加）

不再只是讀 core 原始碼推斷。`src/a11y_tree_probe.cpp` 在同一個無障礙物件上做**與
`getListPrefixSize()` 相同的查詢**，並把它回傳的 `SegmentEnd` 跟它要描述的文字並排：

| 段落 | 種類 | 長度 | `attrRunEnd` | 真正的前綴長度 |
|---|---|---:|---:|---:|
| `• E1-LC-BULLET-ONE` | 項目符號 | 18 | **2** | 2（`"• "`）✓ |
| `1. E1-LC-NUMBER-ONE` | 編號 | 19 | **3** | 3（`"1. "`）✓ |
| `E1-LC-HEADING` | 標題 | 13 | **13** | **0** ✗ |

機制在一張表裡看得完：項目符號與編號的前綴**字元格式不同**，所以它自成一個
attribute run，`SegmentEnd` 與前綴長度**恰好相等**。而標題的文字裡**根本沒有編號
標籤**——真正的前綴長度是 **0**——但它帶大綱編號，所以 `bIsCounted` 為真、過得了
`:579` 的門，而它整段格式一致，attribute run 涵蓋整段。

**這比只讀原始碼能講的更強**：不是「整段被宣告成前綴」，而是**在一個前綴長度為 0
的段落上回傳 13**。

順帶一個佐證：`E1-LC-ISOLATED 前後都不是清單的段落`（25 字）的 `attrRunEnd` 是 **15**
——文字中間有個屬性 run 邊界，與編號毫無關係。它沒出事只是因為那一段 `isNumbered`
是 false，守衛先回 0 了。**守衛救的是一般情形，而標題正是它救不到的地方。**

證據：`findings/evidence/aria-projection/levels-and-lists-2026-08-23.json`。

## 為什麼這對取用端是靜默的錯

`listPrefixLength` 的合約是「前 N 個字元是編號前綴，不是內文」。取用端據此切掉前綴：

- 我們的引擎用 `content[listPrefixLength:]` 算段落指紋，於是**標題的指紋變成空字串的
  雜湊**（FNV-1a 的 offset basis, `cbf29ce484222325`）。所有空段落也是那個值，所以
  **標題和空行被折進同一格**。
- 對報讀軟體的投影而言，若照合約只念內文，標題會被念成**空的**。

沒有任何錯誤、沒有任何旗標，回傳值格式完全正確。

## 最小修法方向（未實作、未驗證）

前綴的長度應該來自**編號本身**，而不是「第一個屬性 run 有多長」。同一支函式已經拿到
`XAccessibleText`，可行的方向：

- 取編號字串（`XAccessibleContext` 的 numbering／`ListLabel` 一類的屬性）並用它的長度；
- 或至少加一道防呆：`SegmentEnd >= nLength` 時視為「量不到前綴」而回 0——**寧可少切也
  不要把整段切掉**。防呆這一版不需要新 API，且能把最糟的失效模式（整段消失）擋掉。

⚠ 兩者都**沒有量過**。這裡只寫方向，不宣稱修法。

## 影響到我們的地方

- `queue-a11y-prefix-swallows-the-paragraph` —— 兩個假說中「我們的解析把欄位配錯」
  已於 2026-08-23 由量測排除（同一格同時給出 `content` 與 `listPrefixLength`，
  解析是照名字直接讀的）；這份 finding 把剩下那一半也定案到 LOK 的一行上。
- 路線圖 §3.4 的投影：指紋不能拿來當身分（另有 08-16g 四輪量測與
  `tools/measure_paragraph_fingerprint_collisions.py` 的碰撞計數為證），這個缺陷是
  其中一個成因，但**不是唯一成因**——重複文字的段落本來就同指紋。

## 證據

- `findings/evidence/a11y-gate-0/RESULT.md`（三次一致的量測）
- `findings/evidence/aria-projection/text-reaches-the-page-2026-08-23.json`
  （`content` 與 `listPrefixLength` 同時在場的那一份）
- 原始碼：`libreoffice-26-8/sfx2/source/view/viewsh.cxx:554-588`，core commit
  `671c848b1bb8`

## 送出狀態

上游送出自 2026-08-15 起全線擱置（見 `upstream-submissions-on-hold`）。重啟時先重查
重複單；這一張附得了 patch。

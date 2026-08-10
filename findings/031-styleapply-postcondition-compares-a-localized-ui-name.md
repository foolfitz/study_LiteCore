# 031 — 段落樣式的後置條件比對的是**在地化 UI 名稱**，我方 build 已內含 zh-TW 譯文

| | |
|---|---|
| **狀態** | **已確認（原始碼追到底＋既有證據佐證＋譯文檔實查）／端到端尚未在非英文 UI 下實測** |
| **Bugzilla** | — |
| **發現日** | 2026-08-11 |
| **嚴重度** | 嚴重（潛伏：一旦 UI 語系不是英文，兩個段落樣式動作的 barrier 永遠不會完成） |
| **可重現** | 未實測（見〈為什麼還沒實測〉） |
| **是否上游** | **否**（core 的既有語意；問題在我方拿它當後置條件） |

## 摘要

E2-A 的 barrier 以整串比對判定段落樣式的後置條件：`.uno:StyleApply=Heading 1` 與
`.uno:StyleApply=Body Text`（`src/probe_engine.cpp` 的 `kHeadingReportedStyles`／
`kBodyReportedStyles`，且刻意不做前綴或模糊比對）。

那兩個字串是 **UI 顯示名稱，會隨 UI 語系改變**。在 zh-TW 之下它們是「標題 1」與「內文」，
整串比對必然失敗，於是 `set-paragraph-heading`／`set-paragraph-body` 的 barrier 逾時成
`MUTATION_OUTCOME_UNKNOWN`——**文件其實已經改對了**。

**派送那一側是安全的**：`Style` 參數送的是 ProgName（程式名），取自一份寫死、不經翻譯的陣列。
所以問題只在後置條件這一側。這也把 SPEC E2-A 2.5 節掛著的待驗證項目「`Body Text`
等 state 顯示名稱是否隨 UI locale 改變」答完了：**會變。**

## 證據鏈

**（一）payload 帶的是 UIName，不是我方送出去的字串**（已觀察，en-US）。

A2 原生與 A2-wasm 的既有證據裡：

| 我方送出（`Style` 參數） | state 回報 | ODT 存檔 |
|---|---|---|
| `Text body` | `Body Text` | `Text_20_body` |
| `Standard`（隱含，reset 時） | `Default Paragraph Style` | `Standard` |

送進去的和回報的**不是同一個字串**，所以回報值不可能是我方輸入的回音——
它來自 core 自己的名稱表。

**（二）那張表是照 UI 語系建的**（原始碼，26.8 `671c848b…`）。

```text
sw/source/uibase/app/docst.cxx:140            UIName aName;    ← 型別就是 UIName
                              :145            case SID_STYLE_APPLY:   // = .uno:StyleApply
                              :162-164            aName = pColl->GetName();
                              :166            rSet.Put(SfxTemplateItem(nWhich, aName.toString()));
                                                    ↑ 只放 UIName，沒放 ProgName
sfx2/source/dialog/tplpitem.cxx:62            aTemplate.StyleName = aStyle;   ← 就是上面那個 UIName
sfx2/source/control/unoctitm.cxx:969-975      StyleApplyPayload
                                                → "…=" + aTemplate.StyleName.toUtf8()
```

而 UIName 陣列本身：

```cpp
// sw/source/core/doc/DocumentStylePoolManager.cxx:2665-2676
const std::vector<OUString>& SwStyleNameMapper::GetTextUINameArray()
{
    const LanguageTag& rCurrentLanguage = aSysLocale.GetUILanguageTag();   // ← 以語系為 key
    static std::map<LanguageTag, std::vector<OUString>> s_aTextUINameArray;
    …lcl_NewUINameArray(STR_POOLCOLL_TEXT_ARY, …)                          // ← SwResId()
}
```

對照之下 ProgName 陣列是寫死的、不進翻譯：

```cpp
// sw/source/core/doc/SwStyleNameMapper.cxx:496-500
const std::vector<OUString>& SwStyleNameMapper::GetTextProgNameArray()
{
    static const std::vector<OUString> s_aTextProgNameArray = {
        u"Standard"_ustr, u"Text body"_ustr, …
```

**值得記一筆的不對稱**：同一份 `docst.cxx` 裡，`SID_STYLE_FAMILY2`（`:181-202`）走的是
`SfxTemplateItem aItem(nWhich, aName.toString(), aProgName.toString())`——**兩個都放**。
只有 `SID_STYLE_APPLY` 這條沒放 ProgName，所以 payload 這一側**沒有語系無關的替代欄位可用**。

**（三）我方 WASM build 已經內含 zh-TW 譯文**（已觀察）。

`wasm-lite/build-headless-probe` 的 `autogen.input` 是 `--with-lang=en-US`，但
`instdir/program/resource/` 下**確實有 `zh_TW/LC_MESSAGES/`，含 `sw.mo`**（5,354 筆）：

```text
'STR_POOLCOLL_HEADLINE1\x04Heading 1' -> '標題 1'
'STR_POOLCOLL_TEXT\x04Body Text'      -> '內文'
```

正好就是 barrier 比對的那兩個字串。

## 為什麼還沒實測

端到端要在**非英文 UI 語系**下跑一輪，才算把最後一環從推論升格為已觀察。這一環目前跑不出來，
而且**跑錯地方會得到保證的假陰性**：

- **原生 build 不能用**：`build-native-26-8` 是 `--with-lang=en-US` 且
  `resource/` 下只有 `common`，沒有任何譯文。設 `LANG=zh_TW.UTF-8` 會回退英文，
  量到「字串沒變」——那是量測環境的結論，不是產品的。
- **WASM build 有譯文，但我方沒有選語系的路**：engine 呼叫的是
  `documentLoad(kit, url)`（`src/probe_engine.cpp:1718`），沒有選項；全樹沒有任何
  `setLanguageTag`／`ooLocale`／locale 設定。

要實測需要的最小改動（**未實作**）：discovery-only 改走
`documentLoadWithOptions(kit, url, "Language=zh-TW")`。LOK 對這個選項的處理在
`desktop/source/lib/init.cxx:2843-2866`，會設 `comphelper::LibreOfficeKit::setLanguageTag()`
與 `setLocale()`，也就是 `SvtSysLocale::GetUILanguageTag()` 讀的那個——正是（二）的 key。

## 影響與修法方向（未決）

**今天是潛伏的**：沒有任何一條路徑會選非英文 UI，所以現行讀數是 en-US，barrier 比對得中。
**但這個專案的產品對象是 zh-TW 使用者**，一旦要上在地化 UI，這兩個動作會在使用者眼前
變成「明明套用了、卻回報結果未知」。

候選方向，都還沒選：

1. **後置條件改用 ODT 存檔的樣式名**（`Heading_20_1`／`Text_20_body`）。
   那是 ODF 編碼過的 ProgName，語系無關。但取得它要存檔，成本與 discovery 不同。
2. **改比對 `StyleNameIdentifier`**——目前 `SID_STYLE_APPLY` 那條**沒有填**，
   要填得改 core（上游修改，本專案預設不動 core）。
3. **把承諾縮到清單**：SPEC E2-A 第 8 節的 `PARTIAL_GO_TO_E2_B` 已經預先寫了這一條
   （「`StyleApply` 字串因 locale 不穩定而只能承諾清單」）——它本來就想到了，
   只是當時還沒證實。
4. **維持整串比對，但把在地化字串也編進去**：需要每個語系一份，且會隨上游譯文變動，
   等於把翻譯當 ABI。**不建議。**

清單那三個動作**不受影響**：`.uno:DefaultBullet`／`.uno:DefaultNumbering` 的 payload 是
布林值（`IsActivePayload`），沒有字串可在地化。

## 相關

- [019](019-e1a-paragraph-style-mapped-to-ui-alias.md)——「一個樣式三種字串」的來源；
  本單指出其中一種**還會再隨語系分岔**。
- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)——
  同一個後置條件設計的另一個問題（no-op 無廣播）。兩者互相獨立：
  030 是「該來的沒來」，031 是「來了但比不中」。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 2.5 節（本單答完的待驗證項）、
  第 4 節（固定對照表）、第 8 節（`PARTIAL_GO` 已預留的縮限）。

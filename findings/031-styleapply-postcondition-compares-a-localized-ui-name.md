# 031 — 段落樣式的後置條件比對的是**在地化 UI 名稱**，我方 build 已內含 zh-TW 譯文

| | |
|---|---|
| **狀態** | **機制已確認（原始碼追到底＋既有證據佐證）／端到端仍未實測——已試，是假陰性，因為出貨映像沒打包任何譯文** |
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

**（三）建置樹裡有 zh-TW 譯文，但\*\*出貨的 WASM 檔案系統映像沒有\*\***（已觀察）。

> **2026-08-11 更正。** 本節第一版寫「我方 WASM build 已經內含 zh-TW 譯文」，
> **那是錯的**。我看的是建置主機上的 `instdir/`，但 WASM 出貨的不是 `instdir`，
> 是打包進 emscripten 的檔案系統映像。兩者不一樣，而差別正好落在這一項。

建置樹（`wasm-lite/build-headless-probe/instdir/program/resource/`）確實有
`zh_TW/LC_MESSAGES/sw.mo`（5,354 筆），其中：

```text
'STR_POOLCOLL_HEADLINE1\x04Heading 1' -> '標題 1'
'STR_POOLCOLL_TEXT\x04Body Text'      -> '內文'
```

**但 `soffice.data` 的檔案清單（`soffice.data.js.metadata`，1,358 個檔）裡：**

| 項目 | 數量 |
|---|---|
| `.mo` 訊息目錄 | **0** |
| `/instdir/program/resource/` 下的檔案 | **1**（`common/fonts/opens___.ttf`） |
| zh-TW 的 registry langpack | 3（`Langpack-zh-TW.xcd`、`res/fcfg_langpack_zh-TW.xcd`、`res/registry_zh-TW.xcd`） |

也就是說：**zh-TW 在這個 build 是「選得到、但沒有東西可選」**——registry 說有這個語系，
訊息目錄一個都沒打包，`SwResId()` 只能回傳未翻譯的 msgid。

這本身是一項值得記下的產品事實：**今天把 UI 設成 zh-TW，介面會是英文**。
功能線要做的 heading dropdown／清單按鈕也一樣。

## 實測跑了，而且是假陰性——原因已查明

**做法**：新增隔離 profile `e2-locale-attribution`＝`e2-scheduler-attribution` 只改一件事，
engine 改走 `documentLoadWithOptions(kit, url, "Language=zh-TW")`
（`src/probe_engine.cpp`，以 `OXSDK_E2_UI_LANGUAGE` 編譯期常數隔離，JS 選不了，
是實驗不是 surface）。語系標籤由 LOK 自己消化，見
`desktop/source/lib/init.cxx:2843-2866`，會設 `comphelper::LibreOfficeKit::setLanguageTag()`
與 `setLocale()`，正是（二）那張表的 key。兩臂唯一差別就是這個標籤。

**結果**（Chrome 150，profile `e2-locale-attribution` WASM `8adca798…`）：

| | en-US 臂（`38d15ed4…`） | zh-TW 臂（`8adca798…`） |
|---|---|---|
| `set-paragraph-heading` 後回報的樣式 | `Heading 1` | `Heading 1` |
| `set-paragraph-body` 後回報的樣式 | `Body Text` | `Body Text` |
| 五個 action 的 completion | 全 `verified-format-state` | 全 `verified-format-state` |
| ODT postcondition | 5/5 | 5/5 |

**字串沒有變。而這不是本單的反證，是（三）的直接後果**：這個 build 一個訊息目錄都沒打包，
`SwResId()` 只能回英文 msgid，所以**這條路上不可能量到不同的值**。
我在上一版預測原生 build 會有這個假陰性，然後在 WASM build 上踩了同一個坑——
差別是原生我事先查了 `resource/`，WASM 我看的是 `instdir` 而不是出貨映像。

**因此本輪沒有把最後一環升格為已觀察。** 唯一新增的正面觀察是：
`documentLoadWithOptions` 帶 `Language=zh-TW` **不會弄壞任何東西**（五個 action 照常完成、
postcondition 5/5），所以之後真的要量時，這條路是通的。

**這一輪也沒有正控制**：無法區分「選項根本沒生效」與「選項生效但沒有譯文可用」。
在沒有譯文的 build 上，任何控制都問不出前者——要先有譯文才有得問。

### 真要量到，要先解決打包

兩條路，都不便宜：

1. **把 `resource/` 打進 FS 映像**（或 `--with-lang=zh-TW` 重建 wasm-lite）。
   這是**做 zh-TW 產品本來就得做的事**，不是為了量測才做的。重建成本高，且動到凍結的
   `build-headless-probe`。
2. **執行期把 `sw.mo` 寫進 MEMFS**（`/instdir/program/resource/zh_TW/LC_MESSAGES/`）。
   emscripten FS 可寫，engine 也已經有寫入 MEMFS 的路徑（`writeInputFile`）。
   便宜得多，但要新增一條 discovery-only 的檔案注入通道，且要確認 core 是在
   documentLoad 之後才第一次查表。**未實作。**

## 影響與修法方向（未決）

**今天是潛伏的，而且觸發點比原本寫的更明確**：不是「一旦有人選了非英文 UI」，
而是**一旦把訊息目錄打進 FS 映像**——而那正是做 zh-TW 產品的必要步驟。
在那之前，就算選了 zh-TW 也只會拿到英文，barrier 照樣比對得中（本輪實測即為此）。

換句話說：**這個缺陷會在「產品開始在地化」的那一刻同時被啟動**，
而那一刻通常沒有人會想到要回頭重驗 barrier 的字串比對。

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

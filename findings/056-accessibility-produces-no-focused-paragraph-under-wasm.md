# 056 — WASM 上打開 accessibility 之後,焦點段落永遠是空的;同樣的順序在原生上立刻就有

| | |
|---|---|
| **狀態** | **已確認／機制已定（2026-08-17 當日補完）／未修** |
| **Bugzilla** | —（**已判定:是我們的建置組態**,不是 LOK/VCL 的執行期缺陷;送出作業另見 [[057]]) |
| **發現日** | 2026-08-17（v3 第二次連結之後的第一次量測） |
| **嚴重度** | **嚴重**——`queue-verify-caret-by-block-identity` 整條設計的資料來源在這個平台上拿不到 |
| **可重現** | 100%（WASM 與原生各一輪,兩邊都是 core 26.8 同一個 commit） |
| **是否上游** | **否**——是我們傳了 `--with-wasm-module=writer`。但「照 configure 去修會修不好」是上游的,拆成 [[057]] |

## 現象

在 WASM 產品 build 上,`setAccessibilityState(view, true)` **有被呼叫而且成功**,
而 `getA11yFocusedParagraph()` 回來的段落**永遠是空的**——不管 caret 在哪一段。

引擎自己的回報（第二次連結新增的欄位,就是為了不再從空字串反推）:

```json
{"enabled": true, "unavailable": "", "paragraphFresh": true,
 "changeCount": 0, "unparsedCount": 0, "observed": false,
 "contentLength": 0, "position": 0,
 "paragraphFingerprint": "cbf29ce484222325"}
```

逐項讀:**開起來了**（`enabled`,而且沒有任何一個能力守衛擋下來)、
**這一次的同步讀成功了**（`paragraphFresh`)、
**而且從頭到尾沒有任何一個 `LOK_CALLBACK_A11Y_FOCUS_CHANGED` 到過**
（`changeCount: 0`,連 parse 失敗的都沒有:`unparsedCount: 0`）。
指紋 `cbf29ce484222325` 就是空字串的雜湊。

## 原生對照:同樣的順序,立刻就有

`tools/queue_native_a11y_attach_timing.cpp`,core 26.8 原生,
**刻意照產品現在的順序**做：`initializeForRendering` → `registerCallback` →
**在任何 caret 存在之前就打開 accessibility**：

| 時點 | `content` | `position` |
|---|---|---|
| 開檔就打開、還沒有任何 caret | **`BI-ANCHOR-ONE`** | 0 |
| 繪製之後 | `BI-ANCHOR-ONE` | 0 |
| 第一次點擊之後 | `BI-ANCHOR-ONE` | **5** |
| 重新掛載之後 | `BI-ANCHOR-ONE` | 5 |
| 第二次點擊之後 | **`BI-AFTER-EMPTY`** | 5 |

**原生在「還沒有任何 caret」的那一刻就已經有內容了**,而且之後跟著點擊走。

這一輪同時**推翻了我自己的假說**:我原本以為是「掛得太早」——樹裡本來就有一句
註解說「reattach 才不會拿到 early empty focus」。**原生量下去,掛在開檔那一刻完全
沒問題**,重新掛載也沒有改變任何東西。所以不是時機。

## 分界線

| | 原生 26.8 | WASM 產品 build |
|---|---|---|
| `setAccessibilityState` | 有,成功 | 有,成功（`unavailable: ""`) |
| `getA11yFocusedParagraph()` 回得了嗎 | 回得了,**有內容** | 回得了,**內容是空的** |
| `A11Y_FOCUS_CHANGED` 回呼 | 有（內容變化時） | **一次都沒有** |

同一份 core 原始碼（`671c848b…`）。差別在平台。

## 機制（2026-08-17 當日補完;原文寫的是「不指認」)

原文按 040／048 的先例拒絕指認機制。當天把它量出來了,所以指認——**但指認的依據
是編出來的東西和出貨的二進位,不是推理**。

鏈條,每一格都可查:

1. `autogen.input` 傳了 `--with-wasm-module=writer`。
2. `configure.ac:4371-4375` 對 Emscripten 先設 `ENABLE_WASM_STRIP_ACCESSIBILITY=TRUE`;
   `:4378-4388` 只有 `calc` 和 `impress` 會清掉它,**`writer`(`:4382-4384`)不會**。
3. → `config_host/config_wasm_strip.h:5` 是 `#define ENABLE_WASM_STRIP_ACCESSIBILITY 1`
   （原生同一個檔是 `0`)。
4. → `sw/Library_sw.mk:108-137` 排除 27 個物件,其中 26 個在 `sw/source/core/access/`。
   **量到的**:該目錄 WASM 2 個、原生 28 個,差額正好 26。剩下那 2 個是
   `AccessibilityCheck`／`AccessibilityIssue`——文件無障礙**檢查器**,另一個功能。
5. → `sw/source/uibase/docvw/edtwin.cxx:6532-6542`:`SwEditWin::CreateAccessible()`
   在巨集為 1 時**直接回 `{}`**。
6. → `vcl/source/window/accessibility.cxx:78-81`:`Window::GetAccessible()` 拿到的就是
   空的。
7. → `sfx2/source/view/viewsh.cxx:3489-3493`:`SetLOKAccessibilityState()` 在
   `if (!xAccessible.is()) return;` **當場靜靜返回**,`attachRecursive()` 從來沒被呼叫。

### 出貨的那顆二進位自己作證

不是在建置樹上看,是在**量測用的那顆 `probe.wasm`**（`d538ce0b9147…`,逐位元核對過)
裡數字串:

| 符號 | 命中 |
|---|---|
| `SwAccessibleMap` / `SwAccessibleDocument` / `SwAccessibleParagraph` | **0** |
| `accmap.cxx` / `accpara.cxx` | **0** |
| `LOKDocumentFocusListener` | **45** |
| `LOK_CALLBACK_A11Y_FOCUS_CHANGED` | 有 |

**會回報段落的那一半在,會產生段落的那一半不在。** 監聽器活著,而且沒有東西可以掛。
這比「a11y 沒開」精確得多——a11y 的**要求**送到了,核心那邊沒有人接。

### 為什麼它是靜靜地失敗的

`setAccessibilityState` 在 LOK 是 **`void`**。它沒有回傳值,`!xAccessible.is()` 那條
路也不記錄任何東西。所以引擎報的 `enabled: true`／`unavailable: ""`,**從頭到尾只
代表「這個呼叫沒有丟例外」**——它從來沒有辦法代表「core 那邊接受了」。這正是
第二次連結加那些欄位時沒有想到的一層:欄位問對了問題,但問的是我們自己。

## 後果

- **`queue-verify-caret-by-block-identity` 的資料來源在這個平台上拿不到。**
  046 的 barrier 比對與 caret 回答裡的段落指紋,兩個都**不會動**——不是壞掉,是
  沒有輸入。
- **`editorPlaceCaretV2` 那一半不受影響而且是好的**:文字外的第二次點擊
  38 ms／251 ms 有界回答,取代原本的 30 秒。那一半跟指紋無關。
- 這是**第二次連結真正買到的東西**:不是修好,是**把問題定位到平台差異**,而且是
  引擎自己說出來的（`enabled`／`fresh`／`changeCount`),不是從空字串猜的。

## 原文猜錯的地方,記下來

原文寫「要看的地方大概是 `LOKDocumentFocusListener` 的掛載與 VCL 的 a11y bridge
在 headless／WASM 下的初始化」。**方向錯了兩次**:

- 監聽器**在**二進位裡(45 個命中),掛載程式碼也在。不在的是 `sw` 那一側。
- `DISABLE_GUI` 看起來很像肇因(WASM 有、原生沒有),而且我原生對照是用
  `SAL_USE_VCLPLUGIN=svp` 跑的。**查下去它跟這條路無關**:`sfx2`／`sw` 裡沒有任何
  一處拿 `DISABLE_GUI` 去關掉這條路。它只是剛好也不一樣。

兩個都是「形狀看起來很像」而已。真正把它定下來的是**數編出來的物件**和
**數出貨二進位裡的符號**。

## 還缺什麼

- [x] ~~機制~~ —— 上面補完了。
- [x] ~~是不是上游~~ —— **是我們的建置組態**。但「改組態也修不好」是上游的,
      拆成 [[057]]。
- [ ] **決定 block identity 這條路要不要繼續。** 現在知道代價了:要動的是
      `configure.ac`(見 057),而且**必須重編 core**。使用者的工作,不是我的。
- [ ] **引擎要停止謊報。** 現在 `enabled: true`／`unavailable: ""` 在一個
      永遠不可能成功的 build 上照樣是這個值。處方已知而且很小:引擎編譯時
      `#include <config_wasm_strip.h>`,巨集為 1 就報
      `unavailable: "core-built-without-accessibility"`。**要一次連結**,
      不值得為它單獨花,搭下一次順風車。
- [ ] **就算 a11y 開起來了,也不保證 block identity 就能用。** codex 在對抗性
      審查裡列出 `attachRecursive` 之後還有一串各自獨立的執行期條件（100 個 child
      的遞迴上限、`MANAGES_DESCENDANTS` 只在 1–9 個 child 時走 workaround、
      focus callback 只在**段落文字改變**時發、tiled painting 期間
      `A11Y_FOCUS_CHANGED` 會被濾掉、`doc_getA11yFocusedParagraph` 讀的是
      `SfxViewShell::Current()` 而不是傳進 `setAccessibilityState` 的 view id)。
      **修好建置只買到一次測試的機會,不是買到功能。**

## 這次留下的防線

`tools/check_core_build_provides.py` —— 問的是「**core 的 build 有沒有提供產品宣稱
的能力**」,而不是「我們的呼叫有沒有編進去」(後者是
`check_product_build_reaches.py`,它**通過了**,而東西還是死的)。

兩個開關必須同時成立才算提供(見 057:它們接到不同的 configure 輸入,只查一個會
對著一個不可能運作的 build 點頭)。正向對照用的是 `build-native-26-8`——**一個真的
會過的 build,不是我們捏造的突變**。自測 5/5,對產品 build 現在是紅的。

# 056 — WASM 上打開 accessibility 之後,焦點段落永遠是空的;同樣的順序在原生上立刻就有

| | |
|---|---|
| **狀態** | **已確認（原生／WASM 對照,同一份 core 原始碼）／機制未定／未修** |
| **Bugzilla** | —（**未判定是否上游**;在確定之前不得送出） |
| **發現日** | 2026-08-17（v3 第二次連結之後的第一次量測） |
| **嚴重度** | **嚴重**——`queue-verify-caret-by-block-identity` 整條設計的資料來源在這個平台上拿不到 |
| **可重現** | 100%（WASM 與原生各一輪,兩邊都是 core 26.8 同一個 commit） |
| **是否上游** | **未確認** |

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

**機制不指認。** finding 040 與 048 是先例:在沒有量到之前指認肇因,代價是別人照著
錯的方向去修。這裡只說「兩邊不一樣,而且不一樣在哪一格」。

## 後果

- **`queue-verify-caret-by-block-identity` 的資料來源在這個平台上拿不到。**
  046 的 barrier 比對與 caret 回答裡的段落指紋,兩個都**不會動**——不是壞掉,是
  沒有輸入。
- **`editorPlaceCaretV2` 那一半不受影響而且是好的**:文字外的第二次點擊
  38 ms／251 ms 有界回答,取代原本的 30 秒。那一半跟指紋無關。
- 這是**第二次連結真正買到的東西**:不是修好,是**把問題定位到平台差異**,而且是
  引擎自己說出來的（`enabled`／`fresh`／`changeCount`),不是從空字串猜的。

## 還缺什麼

- [ ] **機制**：WASM 上 a11y 事件為什麼不流動。要看的地方大概是
      `LOKDocumentFocusListener` 的掛載與 VCL 的 a11y bridge 在 headless／WASM
      下的初始化——**但那是待查的方向,不是結論。**
- [ ] **是不是上游**：如果 WASM 的 a11y bridge 本來就沒建進去,那是我們的建置組態;
      如果建進去了而事件不流動,才可能是上游。**沒分清楚之前不要送。**
- [ ] 決定 block identity 這條路要不要繼續：目前它在這個平台上沒有輸入。

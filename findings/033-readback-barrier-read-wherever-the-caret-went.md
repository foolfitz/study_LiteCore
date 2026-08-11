# 033 — readback barrier 讀的是「游標現在在哪」，不是「命令改了哪一段」

| | |
|---|---|
| **狀態** | **已確認（A5 負向案例實測）／修法不完整——成因已改判為選取回呼不可歸屬，見下** |
| **Bugzilla** | — |
| **發現日** | 2026-08-11 |
| **嚴重度** | 嚴重（可能對錯誤的段落回報成功，且不會有任何錯誤訊號） |
| **可重現** | 100%（A5 `state-crosstalk`，兩次實測） |
| **是否上游** | **否**（我方 barrier 設計） |

## 摘要

路線 C 的 readback barrier 派送後會選起「游標所在段落」再讀 `text/html` 判定後置條件。
**但游標可能在派送與讀取之間被移走**——barrier 於是讀了另一段。

A5 的 `state-crosstalk` 案例（派送後立刻把游標移到別段）實測讀到
`EDITOR_FORMAT_POSTCONDITION_FAILED`：**fail-closed，方向是對的**。

**但那是運氣。** 那一段剛好不是目標狀態才會不符。若游標移到一段**本來就已經是目標狀態**
的段落，barrier 會讀到相符、回報 `verified-format-readback`——
而實際被改的是另一段。**沒有任何訊號會顯示這件事**。

這是 A5 存在的理由：正向矩陣（A3／A4 共 555 次派送）全部通過，這條路一次也沒被碰到。

## 修法

在**選段落來讀之前**，先把游標移回派送當時記錄的位置（`restorePoint`，
在派送**之前**就擷取，因為派送本身也可能移動游標）。

修後同一個案例：`state-crosstalk` 由 `EDITOR_FORMAT_POSTCONDITION_FAILED`
變成 `verified-format-readback`，且存檔 ODT 顯示 **heading 落在被派送的那一段**
（`E1-STYLED-END` → `Heading_20_1`），不是游標移去的那一段。

## 2026-08-11 更正：修法不完整，真正的洞不是座標

上面的修法**沒有關掉這個缺陷**，而我當時的成因判斷也錯了。

恢復 error payload 的 readback 轉發後（引擎本來就送，是 `sdk-worker.js` 把整包
`formatBarrier` 丟掉——矩陣的 `postconditionFailure` 明寫要帶原始 markup，是管線毀約），
重跑 table-boundary 的 crosstalk 案例，失敗當下讀到的 markup 是：

```html
<p style="margin-bottom: 0.08in; line-height: 100%">E1-TABLE-BEFORE</p>
```

**那是 crosstalk 段落本身**（`parsed:true`、`unknownTag:false`、`restoreConfirmed:true`）。
不是座標落錯、不是表格 API——**是 barrier 消費了一個它無法歸屬的 `TEXT_SELECTION` 回呼**：
`AwaitingSelection` 階段見到任何非空選取就前進，而 crosstalk 的 `search` 正好產生一個。

barrier in-flight 期間，`search`／`placeCaret`／`select` **目前不被 `BUSY` 擋**，
所以 caller 可以替 barrier「按下一步」。其他 fixture 通過只是時序沒對上，不是修好了。

**座標殘留仍是真的**（見下節），但它與本節是兩件事，本案例否證的是座標成因。

## 未消除的殘留（**推論，未實測**）

還原用的是**文件座標**，而派送本身可能改變該段的高度或縮排（套用 heading 會變高、
進清單會改縮排）。極端重排下，那個座標仍可能落到別段。

這條路**沒有被量測過**，也沒有被關閉。要真正關掉需要一個「段落身分」而非座標的定位方式，
那是目前 LOK 介面沒有提供的東西（`getCommandValues` 的實作已查過，見 finding 030）。

## 相關

- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)——readback barrier 的由來。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 2.8／2.9 節。

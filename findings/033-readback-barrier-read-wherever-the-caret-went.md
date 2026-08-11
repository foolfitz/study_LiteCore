# 033 — readback barrier 讀的是「游標現在在哪」，不是「命令改了哪一段」

| | |
|---|---|
| **狀態** | **已確認（A5 負向案例實測）／已修並實測驗證** |
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

## 未消除的殘留（**推論，未實測**）

還原用的是**文件座標**，而派送本身可能改變該段的高度或縮排（套用 heading 會變高、
進清單會改縮排）。極端重排下，那個座標仍可能落到別段。

這條路**沒有被量測過**，也沒有被關閉。要真正關掉需要一個「段落身分」而非座標的定位方式，
那是目前 LOK 介面沒有提供的東西（`getCommandValues` 的實作已查過，見 finding 030）。

## 相關

- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)——readback barrier 的由來。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 2.8／2.9 節。

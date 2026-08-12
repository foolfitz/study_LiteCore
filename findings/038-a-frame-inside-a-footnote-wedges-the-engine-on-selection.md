# 038 — 註腳裡的 as-char frame 會在「選取」時卡死引擎，037 的擋法擋不到

| | |
|---|---|
| **狀態** | **已確認（2/2）／未修**——**037 的擋法涵蓋不到這條路** |
| **Bugzilla** | —（與 [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)／[012](012-r6-styled-document-close-timeout.md) 同族，未送） |
| **發現日** | 2026-08-12 |
| **嚴重度** | **嚴重**——引擎執行緒之後不再回應任何命令，只有重啟 worker 能救 |
| **可重現** | Chrome 2/2；Firefox 1/1；三種選取方式各 1/1；尾註 1/1；派送動作 1/1 |
| **是否上游** | **是**（我方只發了一個滑鼠拖曳選取） |

## 摘要

一個段落，它的**註腳本文裡**有一個 as-char `draw:frame`。對**那個段落**做一次
滑鼠拖曳選取（`editorDiscoverySelect` 的 `mouse-drag`，就是 E1-D 出貨的範圍選取），
選取本身**回報完成**，然後**引擎再也不回應任何命令**：

```
FX-NOTE  drag-select          completed    39 ms   ← 選取自己回來了
         selection-rectangles failed    10001 ms   editorDiscoveryGetState 逾時
         get-selection-text   failed    10000 ms   getSelection 逾時
         selection-reset      failed    10000 ms   editorDiscoverySelect 逾時
FX-TAIL  locate               failed    10000 ms   search 逾時（下一列連錨點都找不到）
```

活性梯與 037 完全同型：**worker JS 活著、wasm 模組從主執行緒仍可呼叫、只有引擎 pthread 不動**。

## 為什麼這一單要跟 037 分開

**037 的擋法在 barrier 的讀取那一步**——讀之前先問 selection type，非 `TEXT` 就具名拒絕。
**這一條路上根本沒有讀取。** 卡死發生在一次選取之後，而選取是產品surface
（E1-D 的範圍選取，`E1_GO_ODT_EDITOR` 出貨的 48 個綁定之一）。

所以：**擋法沒有壞，但它的涵蓋範圍不包含這裡。** 這是一個開著的產品洞。

## 鑑別：是註腳，還是註腳裡的 frame

| 錨點 | 形狀 | 選取型別 | 結果 |
|---|---|---|---|
| `PC-FOOTNOTE`（`paragraph-content`） | 註腳，**裡面沒有 frame** | `text` | **正常**，讀得回文字 |
| `FX-NOTE`（`frame-contexts`） | 註腳，**裡面有 as-char frame** | 讀不到（getState 逾時） | **卡死** |
| `FX-CELL` | 表格儲存格裡的 as-char frame | `complex` | 正常（拒絕由 037 的擋法處理） |
| `FX-PLAIN`／`FX-TAIL` | 沒有 frame | `text` | 正常 |

**所以不是註腳本身**——沒有 frame 的註腳選得好好的。是**註腳本文裡的 frame**。

順帶一提：`FX-CELL` 證明**表格儲存格裡的 frame 走 037 的既有路徑**（`complex` → 被擋），
那是 037 原本列為「沒量過」的兩個情境之一，現在量過了。

## 錨點文字在段落裡，frame 在註腳裡

值得記一筆：被拖曳選取的是**段落本身**，`draw:frame` 在**註腳本文**裡——
兩者不在同一個 `text:p`。所以觸發它不需要選到 frame，
只要選到「有註腳、而註腳裡有 frame」的那個段落。

## 範圍已量（2026-08-12，證據 `038-scope/`）

**觸發它的是「做出一個範圍選取」，不是某一種輸入方式。** 三種互不相同的選取路徑
全部卡死，而**只放游標不會**：

| 選取方式 | 底層 | `FX-NOTE` | 事後引擎 |
|---|---|---|---|
| mouse-drag | `postMouseEvent` ×3 | **卡** | 逾時 |
| text-handles | `setTextSelection` RESET＋END | **卡** | 逾時 |
| keyboard | `move-line-end` ＋ `extendSelection` | **卡** | 逾時 |
| caret-only | 只放游標 | 不卡 | **alive** |
| reset-only | 只 `setTextSelection` RESET | 不卡 | **alive** |

**Firefox 153.0.1 同一形狀**（`FX-NOTE` 同一步失敗、事後引擎逾時、下一列 `search` 也逾時）。

**尾註一樣卡**：`endnote-frame`（同一份文件把 `text:note-class` 由 footnote 換成 endnote）
的 `EN-NOTE` 逐項同型。

**派送格式動作也卡，這下是量到的不是推的**：`frame-contexts` 的討論器四列——
`fx-plain` 完成 38 ms、`fx-cell` 被 037 的擋法以 `selection-type-not-readable` 拒絕 29 ms、
`fx-tail` 完成 30 ms、**`fx-note` 20000 ms 逾時、事後 handle 不可用、`selectionType` 根本沒被記下**。
**barrier 在讀取之前就先做選取**，所以 037 的擋法根本輪不到執行——這正是它擋不到的原因，
現在有直接證據而不是只有結構論證。

**一個假訊號，被活性梯擋下來了**：`caret-only` 與 `reset-only` 兩輪裡，
最後那個 `selection-reset` 步驟**每一列都失敗**——包括沒有 frame 的純段落。
那不是卡死，是探針自己的問題：診斷用的 select 路徑刻意不帶 readback deadline
（`boundedReadback=false`），所以「沒有選取可清」的 reset 不會產生 TEXT_SELECTION callback、
永遠不會完成。**分辨它們的是活性梯**——那五列事後引擎都 `alive` 1–3 ms。
**一個不管文件裡有什麼都同樣失敗的步驟，量的不是文件。** 探針已改成對這兩種方式跳過該步並記下理由。

## 沒有做的事（誠實界線）

- **不知道卡在哪個呼叫**。選取的完成事件出來了，下一個命令沒有回應，
  所以卡點在「選取完成之後」到「下一個命令被取走之前」，那中間是引擎自己的迴圈與
  callback 處理。與 037 不同，那裡沒有一個明顯的 LOK 呼叫可以指。
- **在帶名稱的 build（`150de122`）上重現過一次並取樣**，但那一輪**八條 worker 裡有四條
  的 CDP session 在取樣途中消失**（`Session with given id not found`），所以那一輪的
  「四條 parked」**是不完整的觀察，不是完整的盤點**。可比的只有控制組那一半：
  兩條 `__pthread_cond_timedwait`、五條 idle。
- **沒量「frame 要多深」**：註腳本文只試過一層。表格儲存格裡的 frame 走 037 的擋法
  （型別 `complex`），註腳裡的走這一條——**兩者差在哪還沒有解釋**。
- **沒量產品的 UI 路徑**（editor-shell 的實際手勢），只量了 SDK 這一層的三種選取。

## 相關

- [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)——同一個內容特徵
  （as-char frame），不同的入口；037 的擋法在讀取那一步，擋不到這裡。
- [012](012-r6-styled-document-close-timeout.md)——同一個內容特徵的第三個入口（`destroy()`）。
- [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)——
  帶註腳的段落在 barrier 那一側是**具名拒絕**（`footnote-apparatus-readback`），
  那條路徑不碰這個洞；這裡走的是選取，不是 barrier。

## 修訂紀錄

- **2026-08-12（初版）**：`frame-contexts` fixture 量到；2/2 重現；
  `PC-FOOTNOTE`（沒有 frame 的註腳）作為控制組正常。

# 結構 demo：用它自己的 UI 跑過，判準是存出來的檔案

**日期**：2026-08-13　**引擎**：`c89f069e…`（`e2-format-discovery`，未重連結）
**瀏覽器**：Chromium（Playwright）　**fixture**：`test-docs/e1/list-contexts.odt`
**頁面**：`web/demo-structure.html`

三次手勢，每次都是「點一下段落 → 按一個按鈕」，全部經由 demo 自己的 UI：

| # | 手勢 | 定位 | 動作 |
|---|---|---|---|
| 1 | 點 y≈1945 twips → 項目符號 | 254 ms | 52 ms，修訂 0→1 |
| 2 | 點 y≈2795 twips → 標題 | 251 ms | 39 ms，修訂 1→2 |
| 3 | 點 y≈3376 twips → 編號 | 252 ms | 33 ms，修訂 2→3 |

存出 13.0 KB。

## 判準是文件，不是狀態列

| anchor | 原始 fixture | 三次手勢之後 |
|---|---|---|
| `E1-LC-ISOLATED` | 一般段落、不在清單 | **在 bullet 清單裡** |
| `E1-LC-BULLET-ONE` | bullet 清單、無段落樣式 | **`Heading_20_1`** |
| `E1-LC-BULLET-ONE`／`-TWO` | bullet | **number** |
| `E1-LC-HEADING` | `Heading_20_1` | 不變 |
| `E1-LC-NUMBER-*`／`E1-LC-END` | 原狀 | 不變 |

## 第一次的比對太粗，差點讀成「三個手勢只有一個生效」

初版只比對「在不在清單裡」。第 2、3 個手勢的目標**本來就在清單裡**，
於是那個欄位前後都是 true，看起來像沒生效。**分不出「沒套用」和「本來就長這樣」的比對，
不是弱的比對，是不能用的比對。** 改成逐段報「解析後的段落樣式」與「清單種類（bullet／number）」
之後，三個手勢的效果各自可見。

## 這一輪不涵蓋

定位走的是 `click` ＋ 輪詢（產品 shell 的路徑），**不是** discovery 的
`selection-reset-unstable`，也不是 range 選取——那兩條在這顆 artifact 上都會卡死，
見 [finding 039](../../../039-the-discovery-selection-path-completes-at-most-once.md)。
只跑了 Chrome 一輪、一份 fixture、三個手勢；這是 demo 的可用性證據，
**不是** A3／A4／A5 那種矩陣判定。

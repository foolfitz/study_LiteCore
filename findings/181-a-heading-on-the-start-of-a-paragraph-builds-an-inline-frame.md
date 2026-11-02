# 181 — 選段落開頭幾個字按標題，得到的是行內標題框，不是標題段落

| | |
|---|---|
| **狀態** | 已確認；修法在 e2-editor-v32（`specs/SPEC-P-demo-batch-4.md` 第 5 節），等連結 |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-11-03（N3 的 complex 選取，讀碼確認成因，出貨頁面重現） |
| **嚴重度** | 一般：文件結構和使用者預期不同，一個字數不多的詞被拆進框裡，沒有任何提示 |
| **可重現** | 出貨頁面 2/2（Chrome、Firefox），原生 N4 全部 leading 臂 |
| **是否上游** | 否：是 core 的刻意功能，對我方「這一段變標題」的按鈕語意不對 |

## 現象

段落 `BRAVO plain paragraph two`，選開頭三個字，按「標題」。按鈕回報成功，存檔裡多一個框，`BRA` 變成框裡的標題，原段落不是標題。`evidence/demo-batch-4/before-v31/run-01/`。

## 分析

`SwDocShell::MakeInlineHeading`（`sw/source/uibase/app/docst.cxx:1262`）：單一段落、選取從段落開頭起、不滿整段、少於 120 字時，`.uno:StyleApply` 建立一個以字元錨定的框。所有段落樣式都走這條，內文也是。

v31 的後置條件沒抓到：範圍單段的路線先用座標把選取收掉、再選整段讀，讀到的是框外剩下的段落，或框本身。

## 修法

v32：單段範圍套段落樣式前先 `.uno:SelectText`，選取留在整段（判準 T6）。N4 widen 的 widened 臂全部乾淨。

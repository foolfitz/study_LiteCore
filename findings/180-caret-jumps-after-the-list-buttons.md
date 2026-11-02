# 180 — 按項目符號／編號之後游標跳到別的字

| | |
|---|---|
| **狀態** | 待產品路徑確認；原生已量到 |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-11-02（Codex 審核對齊設計時指出機制，N2 量到） |
| **嚴重度** | 一般：下一個按鍵打在錯的位置，文件內容不遺失 |
| **可重現** | 原生 6/6 |
| **是否上游** | 否（我方 barrier 的還原方式） |

## 現象

游標在段落中間，按項目符號或編號，段落縮排，文字往右移。barrier 用派送前的游標矩形還原，同一個座標現在是另一個字，接著打字就插到那裡。barrier 只確認選取是空的，所以回報成功。

## 量測

`evidence/demo-batch-3/native-writer-align-caret/neighbour/`：`.uno:DefaultBullet`、`.uno:DefaultNumbering` × 段落中間、清單中間、換行段落中間，插入 X 後存檔，和只派送不讀回的結果比，0/6 相同。例：`BRXAVO` 變 `BXRAVO`。

原生 harness 的 `.uno:DefaultBullet` 沒帶引擎用的 `On` 參數，機制相同但不是逐字的產品路徑。產品路徑結果見 `evidence/demo-batch-3/list-caret-product/`。標題動作走同一條路，沒有量。

## 分析

`ordered_format.inc` 的 `restoreOrderedFormatPoint`，`restorePoint` 取自派送前的 `gEditorState.caret`。對齊用 SPEC-P-demo-batch-3 第 6 節的讀法避開了這件事；清單與標題沒有換，因為那條讀法有 F3、V0′ 綁著。

## 修法

已知：同一種「選一個字元、讀、從 point 走回來」的讀法。要連結，要重驗 F3、F4。等擁有者決定。

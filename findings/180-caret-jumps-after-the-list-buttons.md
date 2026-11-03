# 180 — 按項目符號／編號之後游標跳到別的字

| | |
|---|---|
| **狀態** | 已修，等擁有者手測：e2-editor-v32（`specs/SPEC-P-demo-batch-4.md` 第 5 節，讀法不選取，所以沒有東西要還原）；宿主 0.2.52 已裝，P4 的 T4 與 `H4/caret-and-level` 都過。出貨中的 0.2.45 仍帶這個缺陷 |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-11-02（Codex 審核對齊設計時指出機制，N2 量到） |
| **嚴重度** | 一般：下一個按鍵打在錯的位置，文件內容不遺失 |
| **可重現** | 原生 6/6；產品頁面（Chrome 鏡像）3/3 |
| **是否上游** | 否（我方 barrier 的還原方式） |

## 現象

游標在段落中間，按項目符號或編號，段落縮排，文字往右移。barrier 用派送前的游標矩形還原，同一個座標現在是另一個字，接著打字就插到那裡。barrier 只確認選取是空的，所以回報成功。

## 量測

`evidence/demo-batch-3/native-writer-align-caret/neighbour/`：`.uno:DefaultBullet`、`.uno:DefaultNumbering` × 段落中間、清單中間、換行段落中間，插入 X 後存檔，和只派送不讀回的結果比，0/6 相同。例：`BRXAVO` 變 `BXRAVO`。

原生 harness 的 `.uno:DefaultBullet` 沒帶引擎用的 `On` 參數，所以再到產品頁面量（`evidence/demo-batch-3/list-caret-product/`，出貨頁、真實按鍵、0.2.50 同一批位元組）：游標放在第二段 `BR` 之後，按鈕，打 `q`，存檔。

| 按鈕 | 第二段 |
|---|---|
| 不按（對照） | `BRqAVO plain paragraph two` |
| 項目符號 | `qBRAVO plain paragraph two` |
| 編號 | `qBRAVO plain paragraph two` |
| 標題 | `BqRAVO plain paragraph two` |

## 分析

`ordered_format.inc` 的 `restoreOrderedFormatPoint`，`restorePoint` 取自派送前的 `gEditorState.caret`。對齊用 SPEC-P-demo-batch-3 第 6 節的讀法避開了這件事；清單與標題沒有換，因為那條讀法有 F3、V0′ 綁著，而且不在這批的要求內。

## 修法

已知：同一種「選一個字元、讀、從 point 走回來」的讀法。要連結，要重驗 F3、F4。等擁有者決定。

## 擁有者裁示（2026-11-02）

採建議 A：先連結 demo batch 3，180 下一輪修。下一輪的連結本來就要做 H1～H4 與切換鈕（`specs/SPEC-P-demo-batch-4.md`），一起換讀法，F3、F4 只重驗一次。

`tools/check_writer_align.py` 的 `P1c/control/list-button-still-moves-the-caret` 把這個現象釘成對照：修好時它會轉紅，要跟著拿掉。

## 修法的更正（2026-11-03）

上面「同一種選一個字元的讀法」不成立：一個字元的選取讀不到清單標籤（`evidence/demo-batch-4/native-toggle/`）。改用不選取的讀法，`src/writer_caret_bridge.cpp` 從文件讀游標涵蓋的段落，什麼都沒選，所以也沒有東西要還原。N4：168 格的存檔都等於完全不讀的對照。判準 T4。

另外，這份 finding 引用的 `neighbour/` 與 N2 的 `para-start`、`list-start` 位置不在段落開頭，見規格第 5 節。現象本身不受影響。

# SPEC-P-calc-undo：Calc 頁面的復原

2026-11-03 擁有者問 Calc 頁面有沒有復原。答案是沒有（`findings/evidence/calc-undo/README.md`）：Calc 引擎的 capabilities 沒有 undo、worker 拒絕、頁面沒有綁 Ctrl+Z。擁有者把它列進待辦。補上它需要一次連結（Calc build 的 capability bit、新的 Calc profile、頁面的按鈕與 Ctrl+Z／Y）；連結由擁有者執行。

本文件先釘**原生量測**（第 2 節）：頁面的每一種寫入，引擎要 undo 幾次才回到原狀。連結的設計等量測結果出來再 append。本文件只准 append。

## 1. 頁面會派送的寫入

封閉清單，取自 worker 的 operation 對照表（`sdk/ods-editor-v3-worker.js` 1853–1858 行），不是手列：

| worker operation | bridge op | 頁面上的手勢 |
|---|---|---|
| `cellInput` | 1 | 公式列送出、在格子裡打字後 Enter、清除 |
| `cellFormat` | 2／3／4 | 單格的粗體／斜體／底線 |
| `rangeFormat` | 7／8／9 | 範圍的粗體／斜體／底線 |
| `rangeStyle` | 10／11／12 | 範圍的字色／底色／水平對齊 |

0、5、6 是讀取，不寫。

頁面的組合：單格套格式之前，`CalcEditorSession.setFormat` 先 `_commitNow()`。格子裡有還沒送出的草稿時，一個 Ctrl+B 是**兩次**寫入（op 1 再 op 2）。

讀碼得到的疑點（`src/calc_cell_bridge.cpp` 400–423 行）：op 2、3 對西文、亞洲、複雜文字三個屬性**各呼叫一次** `setPropertyValue`；op 7／8／9 用一次 `setPropertyValues`。Calc 的每次 UNO 屬性寫入各記一個 undo 動作。

## 2. 原生量測 NU（連結之前）

工具 `wasm_sdk_probe/tools/probe_calc_undo_native.py`，用既有的原生 bridge `build/calc-style-native/calc-cell-native`（Calc v3 引擎的同一份 bridge 原始碼，原生 core 26.8；不編譯）。

每一臂一份新文件（`create_calc_edit_fixture` 的 `cell-editing.ods`）：

1. 不做任何寫入先存檔，得到 B。
2. 做該臂的寫入。
3. 最多 5 次 `.uno:Undo`，每次之後存檔得到 U_k，並用 op 0 讀目標格。

**回到原狀**＝第 0 張表每一格的內容（值、型別、公式）與解析後的格式（粗體、斜體各三種文字，底線，字色，底色，水平對齊）都和 B 相同。**步數**＝最小的 k 使 U_k 回到原狀；5 次都不同記為「回不去」。

臂：

| 臂 | 寫入 |
|---|---|
| `zero` | 不寫 |
| `two-inputs` | op 1 F1 `ONE`，op 1 F2 `TWO` |
| `input-text` | op 1 空白格 F1 `UNDOME` |
| `input-number` | op 1 空白格 F2 `123` |
| `input-formula` | op 1 空白格 F3 `=B1+1` |
| `input-overwrite` | op 1 A2 改成 `新內容` |
| `input-clear` | op 1 C2 送空字串 |
| `cell-bold`／`cell-italic`／`cell-underline` | op 2／3／4 開，B2（中文） |
| `range-bold`／`range-italic`／`range-underline` | op 7／8／9 開，A1:C2 |
| `range-textColor`／`range-backColor`／`range-align` | op 10 `#c00000`／11 `#ffe599`／12 `center`，A1:C2 |
| `draft-then-bold` | op 1 F1 `DRAFT`，再 op 2 開 F1（頁面上「有草稿時按 Ctrl+B」） |

判準：

- **NU-0 對照**：`zero` 的步數是 0，`two-inputs` 的步數是 2。儀器分得出 0、1、2；其一不成立，整輪不採計。
- **NU-1 兩個觀測者一致**：每一臂在步數那一次的存檔與 op 0 讀回同時回到原狀（目標格的內容與粗斜底線）。不一致的臂記為 NE，不進結論。
- 每一臂的步數登錄成表。「回不去」或步數大於寫入次數的臂，是 finding，不是判準失敗。

**預測**（執行前寫下）：`input-*` 各 1；`cell-bold`、`cell-italic` 各 3；`cell-underline` 1；`range-*` 各 1；`draft-then-bold` 4。

**如果永遠沒做**：連結時把頁面的一次 Ctrl+Z 對到引擎的一次 undo，不知道單格粗體、斜體要按三次——使用者會按到兩次「沒反應」。

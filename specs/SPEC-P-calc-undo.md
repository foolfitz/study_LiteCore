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

## 3. 追加 1（2026-11-03，NU 的結果）

`findings/evidence/calc-undo/native-01.md`。NU-0 成立（`zero` 0、`two-inputs` 2），NU-1 每一臂兩個觀測者一致，每一臂都和預測相同：

- `cellInput` 各種輸入、`cell-underline`、所有 `range-*`：**1 次**。
- `cell-bold`、`cell-italic`：**3 次**。每次 undo 依序還原複雜文字、亞洲、西文各一個屬性。中文格子上第一次按下去畫面沒有變化。〔已實測〕
- `draft-then-bold`（有草稿時按 Ctrl+B）：**4 次**＝送出 1＋粗體 3。〔已實測〕
- 同樣三個屬性用一次 `setPropertyValues` 寫（`range-bold`）只要 1 次，所以 op 2、3 照 op 7、8 的寫法就會是 1 次。〔推論：同一個呼叫，單格沒有另外量〕

對連結設計的意思（設計本身之後再寫）：op 2、3 要改成一次 `setPropertyValues`，否則頁面一次 Ctrl+Z 對引擎一次 undo 會在單格粗體、斜體上按兩次沒反應。有草稿時按 Ctrl+B 會留下兩個使用者看得懂的步驟（送出、粗體），和「先 Enter 再 Ctrl+B」相同。

## 4. 追加 2（2026-11-03，連結設計，實作之前）

### 4.1 已經有的，不用動

讀碼結果〔已讀碼〕：

- **SDK**：`CalcDocumentEngine` 的 document handle 繼承 `DocumentHandle.undo()`／`redo()`（`sdk/document-sdk.js` 617–640 行），送 `undo`／`redo` request。
- **worker**：v3 worker 已有 `undo`、`redo` 兩個 case 與 `undone`／`redone` 完成事件，由 manifest 的 `undo` capability 把關（`redo` 共用它）。U5 拿到的 `UNSUPPORTED_OPERATION` 就是這道關。worker 沒有依 profile 名字分支的行為。
- **引擎**：`handleUndo`／`handleRedo` 與 UNO 完成回呼在 Calc 的組態（`OXSDK_READER_PROFILE` ＋ `OXSDK_ODS_*`，沒有 `OXSDK_E2_V23_LINK_BATCH`）都有編進去。缺的是兩個匯出、capability bit。

### 4.2 連結要改的（全部在新定義 `OXSDK_ODS_UNDO` 之下，只進新的 Calc build）

- **E1 capability**：ODS 編輯器那一支加 `OXSDK_CAPABILITY_UNDO`。manifest 的 `expectedCapabilityBits` 跟著加，capabilities 加 `undo`。
- **E2 匯出**：`_oxsdk_document_undo`、`_oxsdk_document_redo`。仍然不得出現 `_oxsdk_editor_*`。
- **E3 bridge**：op 2、3 把要改的屬性收成**一次** `setPropertyValues`（op 7、8 的寫法），沒變的屬性不寫，`changed` 的意思不變。依據：NU 的 `range-bold` 一步。
- **E4 復原的前後讀取**：派送 `.uno:Undo`／`.uno:Redo` 之前，先讀 `getCommandValues(".uno:Undo")`／`(".uno:Redo")`。是空的 → 錯誤 `NOTHING_TO_UNDO`／`NOTHING_TO_REDO`、`dispatched: false`，不派送。完成回呼之後再讀一次：undo 數少 1、redo 數多 1（redo 反之）→ `undone`／`redone`，附 `undoCount`、`redoCount`。否則 → `MUTATION_OUTCOME_UNKNOWN`、`dispatched: true`。理由：現行通用路徑不管成功與否都把完成回呼當完成，空堆疊時有沒有回呼還沒量過；finding 071 的教訓是會卡住 session 的能力比沒有更糟。
- 新 profile `ods-editor-v4`，從 v3 衍生；worker 與 v3 位元組相同，除非 NU-2 逼出差異。
- ABI 與 protocol 不動。Writer 不動。

### 4.3 頁面

- 工具列：存檔鈕之後加「復原 (Ctrl+Z)」「重做 (Ctrl+Y)」，圖示、文字與 Writer 頁面相同。只在 manifest 有 `undo` 時顯示。唯讀時和其他寫入鈕一起停用。
- 鍵盤：焦點在格線（不在編輯）時，Ctrl+Z＝復原，Ctrl+Y 與 Ctrl+Shift+Z＝重做。焦點在公式列或格內編輯時不攔，維持瀏覽器自己的文字復原（U4 的現況）。
- **有草稿時按復原鈕**：丟掉草稿（`cancelEdit`），不送引擎。理由：沒送出的打字是最新的變更，和 LibreOffice 在編輯模式中按復原只回退編輯中文字一致。**不先送出**，否則復原只是把剛送出的那筆收回去，還多一筆重做。有草稿時按重做鈕：不動作，提示請先送出或取消。
- **復原之後**：用新 revision 讓圖塊全部失效；重讀目前格（公式列、粗斜底線、顏色、對齊）；多格選取時重讀範圍；重新量文件大小（`refit`）。若 NU-2 量到引擎的游標在復原後移到被還原的格子，頁面選取跟過去（和 LibreOffice 相同）；否則選取不動。
- 沒有可復原的：提示「沒有可以復原的動作」（重做：「沒有可以重做的動作」），不是紅色錯誤，session 維持 ready。
- 按鈕一律可按（Writer 頁面相同），不靠頁面自己數堆疊。

### 4.4 原生量測（連結之前）

用新的原生 driver（`tools/calc_undo_native.cpp`：`calc_cell_native.cpp` 加回呼與「派送並等完成回呼」）和帶 `OXSDK_ODS_UNDO` 的 bridge 原生編譯。單檔 g++，照 AGENTS.md 由 agent 自己編，留 receipt。

- **NU-2 堆疊**：新文件的 undo／redo 讀取是空的；op 1 寫入後 undo 數 1；`.uno:Undo` 之後 undo 0、redo 1；`.uno:Redo` 之後回來；undo 之後再寫入，redo 清空；`changed: false` 的寫入不加堆疊；存檔（`saveAs`，引擎用的同一個呼叫）之後堆疊不變；空堆疊派送 `.uno:Undo` 時完成回呼來不來、內容是什麼；復原前後 `.uno:CellCursor`。這一項是**量測**，結果登錄。前四條與「存檔之後不變」是 E4 和頁面設計的前提，任一不成立就停下來改設計，不連結。
- **NU-3 修法**：帶 `OXSDK_ODS_UNDO` 的 bridge 跑 NU 同一組臂：`cell-bold`、`cell-italic` 變 1，其他臂與 `native-01` 相同（`draft-then-bold` 變 2）。另跑不帶該定義的同一份原始碼當對照：`cell-bold` 仍是 3（證明差別出自定義，不是重編）。

### 4.5 連結之後的判準（瀏覽器，Chrome 與 Firefox，真按鍵與指標，存檔讀回）

- **CU-1**：`cellInput`、單格粗體、範圍底色各一次寫入，按一次復原鈕，存檔讀回與零編輯存檔在被動到的格子相同。
- **CU-2**：同樣用 Ctrl+Z；再按 Ctrl+Y 回到寫入後的狀態。
- **CU-3**：公式列有草稿時按 Ctrl+Z，是文字復原，文件沒有變動（與 U4 相同）。
- **CU-4**：有草稿時按復原鈕，草稿消失、文件沒有變動；再按一次，收回上一筆已送出的寫入。
- **CU-5**：新開的文件按復原，出現「沒有可以復原的動作」，沒有紅色提示，session 是 ready。
- **CU-6**：復原之後，公式列與粗斜底線的狀態是被還原後的格子，不是復原前的。
- **CU-7**：存檔之後還能復原；復原後存檔，檔案是被還原的狀態。
- **CU-8 回歸**：v4 上 Calc 的 P2、C、Calc regression 三臂照過，Writer 不動。
- **紅案**：同一工具在現行 v3 頁面上，CU-1、CU-2 紅（沒有按鈕、Ctrl+Z 沒有送出）。

**如果永遠沒做**：Calc 頁面維持沒有文件復原，只有公式列裡的文字復原。

## 5. 追加 3（2026-11-03，NU-2、NU-3 的結果；取代 4.3 的游標那一句與 4.2 E4 的理由）

`findings/evidence/calc-undo/nu2-nu3.md`。

- **NU-3 成立**：帶 `OXSDK_ODS_UNDO` 的 bridge，單格粗體、斜體各 1 次，有草稿時 Ctrl+B 2 次，其餘 14 臂與 native-01 相同；不帶定義的同一份原始碼仍是 3、3、4。兩者寫完後的存檔逐格相同。〔已實測〕
- **NU-2 的七條前提全部成立**，E4 與頁面設計照原樣：新文件是空的、一次寫入加一筆、沒改到東西的寫入不加、undo 把一筆移到 redo、redo 移回來、undo 後再寫入清空 redo、存檔不清堆疊。〔已實測〕
- **完成回呼沒有資訊**：`.uno:Undo`／`.uno:Redo` 不論有沒有做事都立刻回 `success: false`。E4 的理由改成這個量測（不再是「空堆疊時有沒有回呼還沒量過」——有，而且立刻回）。E4 的設計不變：派送前後各讀一次清單，用數量判定。〔已實測〕
- **游標，取代 4.3「若 NU-2 量到……」那一句**：輸入的 undo 會把引擎的游標拉回被還原的格子，屬性的 undo 不會。E4 在 undo 前後各讀一次 `.uno:CellCursor`（字串最後兩個數是欄、列），回覆帶 `cursor: {column, row, moved}`；`moved` 為真時頁面選取跟過去，否則不動。和 LibreOffice 的行為相同。〔已實測：A1 → F1；範圍粗體的 undo 游標不動〕

## 6. 追加 4（2026-11-03，實作與 Codex 唯讀審核之後，連結之前）

`findings/evidence/calc-undo/review/README.md`。取代 4.2、4.3 的下列細節，原文留著：

- **E2 補一處**：`sdk_api.cpp` 的 undo／redo 原本包在 `#ifndef OXSDK_READER_PROFILE` 裡，Calc 組態有這個定義，函式根本不存在，連結會失敗（Codex 抓到；`-fsyntax-only` 看不到）。改成 `!OXSDK_READER_PROFILE || OXSDK_ODS_UNDO` 時編入。新增連結前檢查 `check_calc_undo_ships.py`：v4 匯出規則裡每個名字在 v4 組態前置處理後都要有函式本體，附紅案。
- **E4 補兩處**：walk 進行中 `dispatch()` 擋下驗證步驟、圖塊繪製以外的所有命令（BUSY），驗證步驟帶序號；派送後讀 `getError`，派送失敗當場以 `LOK_COMMAND_FAILED` 收尾。
- **具名限制 `L-undo-no-deadline`**：派送既沒失敗也沒回呼（例如 `isCommandAllowed` 靜默擋下）時沒有期限；SDK 60 秒逾時讓頁面進入 uncertain。〔推論，未觀測到實例〕
- **worker**：4.2 寫「與 v3 位元組相同，除非 NU-2 逼出差異」。實作時逼出了兩處差異：worker 收到 `undone` 只轉 `revision`，計數與游標到不了頁面。v4 worker＝凍結的 v3 worker 加 `tests/ods-v4-worker-delta.json` 的兩段，**不放在 `sdk/`**，連結時由 `tools/derive_ods_v4_worker.py` 產生：Writer 的 shell bundle 會掃 `sdk/*.js`，放進去會讓第 88 代的 bundle 檢查轉紅。
- **草稿，取代 4.3 的對應句**：按下時有草稿 → 復原丟掉草稿、重做回 `{draftPending}`（不再是錯誤）；草稿是在排隊等待期間才出現的 → 兩者都回 `{draftPending}`，草稿留著、不送引擎。頁面提示「請先完成或取消目前的輸入。」
- **跨表，取代 5 的游標那條的後半**：游標移到別的工作表時，session 回 `{otherSheet}` 不自己換表；頁面照分頁標籤的流程換表（保存離開那張表的檢視），再選取被還原的格子。
- **頁面指向 v4**：連結並凍結 `dist/profiles/ods-editor-v4` 之後才改頁面的 `ENGINE_OPTIONS`，和 Writer 換 profile 相同。
- **新增判準 CU-9**（被第 5 點逼出，先於任何連結）：在 Sheet2 寫入、切回 Sheet1、按復原：顯示 Sheet2 且選取被還原的格子；切回 Sheet1 時捲動位置是離開前的位置。

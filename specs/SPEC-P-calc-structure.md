# SPEC-P-calc-structure：Calc 插入／刪除欄列

2026-11-05 擁有者在欄列標號做完、選「先不發布」之後，挑了 B（插入／刪除欄列）與 D（連打掉字，見 `SPEC-P-key-burst.md`）。擁有者去睡前授權：連結與編譯由 agent 代跑；難以決策處交 fable 代為裁決。本文件是 B。判準實作前釘死，本文件只准 append。

## 1. 現況

- 欄列標號、整欄／整列／整表選取在 dev profile `ods-editor-v6`（wasm `bd85b751`，已封存 `build/archive/ods-editor-v6-dev-bd85b751`）做完，未發布（`SPEC-P-calc-headers.md`）。
- 頁面所有寫入走 bridge 的固定 op（`src/calc_cell_bridge.cpp`，op 0–13），沒有通用 UNO 指令通道；插入刪除要新 op、要連結。
- 核心（`libreoffice-26-8`，〔已觀察〕原始碼）：`ScTableRowsObj`／`ScTableColumnsObj` 的 `insertByIndex`／`removeByIndex`（`sc/source/ui/unoobj/docuno.cxx:4650–4686、4899–`）走 `ScDocFunc::InsertCells(…, bRecord=true, bApi=true)`／`DeleteCells(…, bApi=true)`：記錄 undo、調整公式參照、送標號失效；失敗時不跳對話框、丟 `uno::RuntimeException`。`InsertCellsOperation` 在失敗的路徑上把拆開的合併格合回去並移除那筆 undo（`sc/source/ui/operation/InsertCellsOperation.cxx:709–733`）。

## 2. 決定（agent 依桌面 Calc／Collabora 的慣例定；不是難題，不送裁決）

1. **引擎路線＝UNO `insertByIndex`／`removeByIndex`**，不用 `.uno:InsertRows` 一類 dispatch。理由同 `RESEARCH-2026-11-04-calc-row-column-headers.md` §4.3：既有 op 都是同步 UNO、讀明確範圍，不從引擎的 mark 推導寫入目標；dispatch 要等 callback，混用兩種時序是 finding 178 那類競態。
2. **六個動作**：上方插入列、下方插入列、刪除列、左方插入欄、右方插入欄、刪除欄。數量＝選取涵蓋的列數（欄數），與桌面「工作表 › 插入列 › 上方插入列」相同；任何選取都可（不限整列整欄）。
3. **入口**：在欄標、列標、儲存格上按右鍵開選單（標號上只列該軸的三項，儲存格上六項都列）；在選取之外按右鍵，先把選取移到那裡（桌面行為）。鍵盤：選取是整列或整欄時 Ctrl+＋ 在上方／左方插入、Ctrl+－ 刪除；選單鍵或 Shift+F10 在作用格開選單。部分選取下的 Ctrl+＋／－ 在桌面會開對話框，本批不做。
4. **停用**：唯讀、檢視模式、受保護工作表時六項停用並寫原因；選取涵蓋全部列時列的三項停用（整欄、整表），涵蓋全部欄時欄的三項停用。
5. **之後的選取**：保持同樣的索引範圍（插入後選到新插入的空列，刪除後選到遞補上來的列），作用格重讀。與桌面相同。
6. **profile**：沿用 dev profile `ods-editor-v6` 重新連結（多一個 define），不另開 v7。理由：v6 還沒發布，〈節奏〉2「參數化，不衍生」；連結後重跑欄列標號的 P。下一個手測時段 B 若未完成，欄列標號從已封存的 `bd85b751` 發布。

## 3. 設計

### 3.1 引擎：op 14 `structure`（`OXSDK_ODS_STRUCTURE`）

- `text` 是 JSON `{"axis": "rows"|"columns", "action": "insert"|"delete", "index": i, "count": k}`；`column`／`row` 參數不用。
- 驗證：`count ≥ 1`；`0 ≤ index`、`index + count ≤ max`（插入與刪除都一樣）；不符 → `INVALID_ARGUMENT`。
- 唯讀文件或受保護工作表 → `READ_ONLY`（工作表保護的「允許插入列」選項本批不看，具名限制）。
- 呼叫 `getRows()`／`getColumns()` 的 `insertByIndex(index, count)`／`removeByIndex(index, count)`。丟 `RuntimeException` → `STRUCTURE_REFUSED`，`mutationAttempted: false`（核心在失敗路徑自行復原，N-S5 量這件事）。
- 回：`{ok, part, axis, action, index, count, maxColumns, maxRows, changed: true}`。
- `probe_engine.cpp`：op 14 是 mutation（要 revision、成功時 advance）。`sdk_api`：最大 op 14、能力位元 25 `CELL_STRUCTURE`。

### 3.2 worker／SDK／session

- worker 新操作 `calcStructure`（→ op 14），照 `calcHeaders` 的形狀加在 `tests/ods-v6-worker-delta.json`。
- SDK `changeStructure(part, {axis, action, index, count})`，回覆形狀封閉（`normalizeStructure`）；能力 `cell-structure`。
- session `insertRows(where)`、`deleteRows()`、`insertColumns(where)`、`deleteColumns()`：從目前選取算 index／count，走 mutation 佇列、標 dirty、一個 undo；之後照 2.5 保持選取並重讀作用格。

### 3.3 頁面

`#cell-context-menu`（`role=menu`，項目 `role=menuitem`，停用時 `aria-disabled` 與 `title` 寫原因），Escape 與點外面關閉；選單上的方向鍵與 Enter。完成後 `#toast` 播一句（「已在第 3 列上方插入 1 列」之類）；被拒時播原因。沒有 `cell-structure` 能力（v5）時不開選單，Ctrl+＋／－ 不攔。

## 4. 判準（實作前釘死）

形式依 CLAUDE.md〈驗收判準的形式〉§1。夾具見第 6 節。

### 4.1 原生（N：build-native-26-8，原始碼就是要連結的 `src/calc_cell_bridge.cpp`）

每格一個新的 harness session（新夾具），讀回用 op 0（`text`、`formula`、`endColumn`／`endRow`）與 op 13（隱藏欄列）。

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| N-S1 插入列 | 第 1 張表在索引 1 插入 2 列：A2、A3 空；A4＝「鄰格必須保留」；合併格移到 A5:B5；第 6 列隱藏（原第 4 列）；A1002＝「第 1000 列」；C1 公式不變。`.uno:UndoCount` 剛好 +1。一次 `.uno:Undo` 後以上每格回到夾具原狀 | 插入列視為不支援，頁面不開選單 |
| N-S2 插入欄 | 在欄索引 1 插入 1 欄：B1 空；C1＝42；D1 公式＝`=C1*2`、值 84；E 欄隱藏（原 D）；F1＝「隱藏欄之後」；AB1＝「AA 欄」；合併格變成 A3:C3（核心把橫跨插入點的合併擴大）。UndoCount +1；一次 Undo 回原狀（含合併格 A3:B3） | 同上 |
| N-S3 刪除列 | 刪除索引 1 的 1 列：A2＝「合併格」；A999＝「第 1000 列」。UndoCount +1；一次 Undo 回原狀 | 同上 |
| N-S4 刪除欄 | 刪除欄索引 1：B1 的公式含 `#REF!`（原 C1 參照的 B1 不在了）。UndoCount +1；一次 Undo 後 C1 公式＝`=B1*2`、值 84 | 同上 |
| N-S5 拒絕是乾淨的 | 受保護表（第 3 張）→ `READ_ONLY`；最後一列有資料的表插入列、最後一欄有資料的表插入欄 → `STRUCTURE_REFUSED`；陣列公式 B2:C3 的表在欄索引 2 插入（切到陣列）→ `STRUCTURE_REFUSED`；以上每一個：`mutationAttempted: false`、UndoCount 不變、該表的讀回格不變。`count: 0`、`index + count > max`、`axis: "x"` → `INVALID_ARGUMENT` | 拒絕視為「結果未知」，頁面在拒絕後重開文件 |
| N-S6 成本（量測登錄，不是判準） | op 14 四種動作的 ms | — |

紅案（紅要紅在那一格）：(a) 判讀 N-S1 時把插入的 index 當成 2（差一）→ N-S1 紅；(b) N-S3 不按 Undo 就讀「回原狀」那批格 → N-S3 紅。對照組：v6 現有 build（沒有 `OXSDK_ODS_STRUCTURE`）的 op 14 → `INVALID_ARGUMENT`。

### 4.2 頁面（P：重新連結後的 dev profile `ods-editor-v6`，Chrome 與 Firefox，鏡像，真實滑鼠與按鍵）

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| P-S1 列標選單插入 | 在列標 3 按右鍵：選單只有列的三項、焦點在第一項；選「上方插入列」：`readCell(0,2)` 空、`readCell(0,3)`＝原 A3 的字；選取＝整列 3；列標從 1 起連續；按工具列復原一次回原狀 | 只有鍵盤路徑或沒有 |
| P-S2 欄標選單插入 | 在欄標 C 按右鍵選「右方插入欄」：D 欄空、E1＝原 D1 的字（夾具的 D1 空時改讀 E 欄原 E1 移到 F1）；選取＝整欄 D | 同上 |
| P-S3 多列刪除 | 拖曳列標 2–3、在選取內按右鍵選「刪除列」：一次刪兩列（讀回 A2、A3 ＝原 A4、A5）；選取仍是 2:3 | 同上 |
| P-S4 儲存格選單 | 在 B2 按右鍵：六項都在；選「左方插入欄」：B2 空、C2＝原 B2 | 同上 |
| P-S5 鍵 | 整欄 C 選取時 Ctrl+－ 刪除 C；整列 2 選取時 Ctrl+＋ 在上方插入；部分選取時兩鍵都不動文件 | 只有選單 |
| P-S6 拒絕與停用 | 受保護表：右鍵選單六項 `aria-disabled=true` 且 `title` 非空，選了也不動；整欄選取時列的三項停用；被核心拒絕（夾具「邊界測試」表插入列）時 `#toast` 寫原因、讀回不變、頁面沒有重開文件 | 停用無說明（登錄為「有行為而沒有東西守著」） |
| P-S7 選單可用鍵盤 | Shift+F10 開選單、方向鍵移動、Escape 關閉且焦點回 `#cell-editor` | 選單只能用滑鼠 |
| P-S8 標號回歸 | `check_calc_headers.py` 在重新連結的 profile 上 `P_HOLDS`（兩個瀏覽器） | — |

紅案（頁面突變，紅要紅在那一格）：(a)「上方插入」用 index＋1 → P-S1；(b) 數量固定 1 → P-S3；(c) 停用項沒有 `title` → P-S6。

## 5. 具名限制

工作表保護的插入／刪除允許選項；部分選取的 Ctrl+＋／－ 對話框（儲存格下移／右移）；插入儲存格（不是整列整欄）；多個不相連選取；篩選列；jumbo sheet；刪除後被參照的格變成 `#REF!` 不另外提示（與桌面相同）。

## 6. 夾具

`tools/create_calc_structure_fixture.py`：`calc-headers.ods` 的三張表（`create_calc_headers_fixture.py`，不改），再加兩張：「邊界測試」（A1048576 與 XFD1 有字）、「陣列測試」（B2:C3 是一個陣列公式 `=E2:F3*2`，E2:F3 有數字）。

## 7. 如果永遠沒做

Calc 頁面不能插入或刪除欄列，要到桌面版做。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-11-05 | 初版：決定 1–6、判準 N-S1–S6、P-S1–S8 與紅案，實作前釘死 |

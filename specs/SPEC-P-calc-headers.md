# SPEC-P-calc-headers：Calc 的列標／欄標與整欄整列選取

2026-11-04 擁有者在 Calc 頁面發現沒有列標與欄標（`SPEC-P-demo-batch-3.md` §141 的具名限制），傾向 B 案（標號＋點標號選整欄整列，「因為是核心功能」），交給 fable 研究（`research/RESEARCH-2026-11-04-calc-row-column-headers.md`，`b334ef272`；主 session 核對過七項關鍵宣稱）。2026-11-05 擁有者裁示「照 fable 建議」：研究報告 §8 的 Q1–Q6 全取 A。

本文件只准 append。判準（第 4 節）在任何會算進它的量測之前釘死。

## 1. 現況與 E1（2026-11-05）

- 核心 26.8 的 `.uno:ViewRowColumnHeaders` 已經在 WASM 引擎裡用（`src/calc_cell_bridge.cpp` op 5 的點選），但資料沒有送到頁面；op 0 與 op 5 都會 `select` 儲存格〔已觀察〕。
- 範圍操作 op 6–12 用頁面給的明確矩形，不讀引擎的選取〔已觀察，`calc_cell_bridge.cpp` `accessRange`〕。65,536 格上限守在三層：bridge `kRangeCellLimit`、worker（`sdk-worker.js` 的 range 驗證）、SDK `rangeBounds`〔已觀察〕。
- worker 只把 LOK callback id 0／1 轉成事件，`INVALIDATE_HEADER`（33）在 worker 就丟掉；頁面靠 revision 知道文件變了〔已觀察〕。
- **E1**（`findings/evidence/calc-headers/e1/`，原生、零建置）：在 bridge 的 client zoom 下 A 欄 113 px，標號 px × 15 ＝ 游標 twips，到第 1000 列仍逐位相等（A1000 `yTwips` 254820 ＝ 16988 × 15）；讀標號前後游標不動；隱藏欄列的累計值與前一個相同；空矩形回兩個空陣列；一次 0.1–0.5 ms。〔已觀察〕

## 2. 裁示（2026-11-05，Q1–Q6 全 A）

1. 整欄選取＝頁面矩形＋三層上限對整欄／整列／整表放行；不接 `.uno:SelectColumn`。
2. 整欄／整列／整表碰到跨出選取的合併格：照桌面 Calc，套用明確範圍，不拒。
3. 標號用 DOM 按鈕畫。
4. 角落＝整表選取，可以套格式（前提：N-H4 的整表時間可接受，見 4.1）。
5. Ctrl+Space、Ctrl+Shift+Space（整欄）與 Shift+Space（整列）都綁。
6. 順序：E1 → 原生量測（N）→ 連結（擁有者跑）→ 頁面先畫標號（P-H1）＋紅案 → 點選與鍵（P-H2–P-H6）→ 擁有者手測時段再凍結發布。

## 3. 設計

### 3.1 引擎：op 13 `headers`（唯讀）

- `oxsdk_calc_cell_model(doc, part, 0, 0, 13, text, …)`；`text` 是 JSON `{"x", "y", "width", "height"}`，單位 twips、非負整數，`width` 與 `height` 不得同時為 0（否則 `INVALID_ARGUMENT`）。
- 做：`setActiveSheet(part)`、`setClientZoom(256, 256, 3840, 3840)`、`.uno:ViewRowColumnHeaders?x&y&width&height`。**不做** `select`、不讀 `.uno:CellCursor`。
- 回：`{ok, part, maxColumns, maxRows, columns: [{index, label, startPx, endPx, hidden}], rows: [...]}`。第一筆（數字 `text`）是起點：第 k 筆的 `index ＝ 起點 text ＋ k − 1`、`startPx` ＝ 前一筆的 `size`、`endPx` ＝ 本筆 `size`、`hidden ＝ startPx == endPx`。`label` 用核心給的字串，不由頁面計算。`maxColumns`／`maxRows` 來自 UNO 的欄列數。
- 核心兩端各多給 2 個索引、欄至少 10 列至少 25；頁面自己裁。

### 3.2 引擎：整欄／整列／整表放行

`accessRange` 裡 `whole ＝ (row == 0 && endRow == rows − 1) || (column == 0 && endColumn == columns − 1)`。`whole` 時不檢查 65,536 上限、不因 `RANGE_MERGE_BOUNDARY` 拒絕；受保護工作表與唯讀照舊拒。其他矩形規則不變。worker 與 SDK 用同一條規則，以 16384 × 1048576 為常數（引擎回的 `maxColumns`／`maxRows` 不等於它們時，SDK 拒絕標號回覆＝具名限制：jumbo sheet）。

### 3.3 worker／SDK／profile

- worker 新操作 `calcHeaders`（→ op 13）；range 驗證加上 3.2 的例外。
- SDK `readHeaders(part, rect)` 與 `normalizeHeaders`（形狀封閉：索引連續、`startPx ≤ endPx`、遞增）；`rangeBounds` 加例外。
- 新 profile `ods-editor-v6`（`build/` 底下的 dev profile，擁有者排手測時段前不進 `dist/profiles/`），manifest 加 `headersContract`。

### 3.4 頁面

研究報告 §5 照做：`#viewport` 內三個 sticky 元素（欄標、列標、角落），DOM 按鈕（`role=columnheader`／`rowheader`、`aria-label`「欄 C」「列 5」、`aria-selected`、`tabindex=-1`），隱藏欄列不產生元素；可見矩形變了才讀標號，快取鍵 `part/revision/矩形`；click／shift-click／drag／角落；鍵在 `keydown` 就攔（只在非編輯、無待送輸入、非組字時）；選取改變時 `#toast` 播一句。選取標籤顯示 `C:C`、`5:5`。

## 4. 判準（實作前釘死）

形式依 CLAUDE.md〈驗收判準的形式〉§1。夾具見第 6 節。

### 4.1 原生（N：build-native-26-8，原始碼就是要連結的 `src/calc_cell_bridge.cpp`）

| id | 判準 | 形式 | 如果永遠沒做 |
|---|---|---|---|
| N-H1 讀標號不動游標、與游標同源 | 對工具生成的每個矩形（左上、中段、第 1000 列附近、只有欄、只有列）：op 13 前後 `.uno:CellCursor` 相同；回覆通過 3.1 的形狀規則；每個非隱藏欄 c 的 `startPx × 15` 等於 op 0 讀 (c, 0) 的 `xTwips`，`(endPx − startPx) × 15 − 1` 等於其 `widthTwips`；列同理（列取矩形內每一列） | 逐實例 | 標號幾何視為未證明，頁面不畫 |
| N-H2 整欄／整列／整表寫到底、一步復原 | 夾具每一欄 A–F 與 AA、列 1、3（合併）、1000、以及整表：op 7 bold on 之後，欄讀 (c,0)、(c,999)、(c,maxRows−1)，列讀 (0,r)、(4,r)、(maxColumns−1,r)，整表讀 (0,0)、(maxColumns−1,maxRows−1)，皆 bold；一次 `.uno:Undo` 之後同一批格皆非 bold | 逐實例 | 整欄格式視為不支援，頁面停用整欄選取時的格式按鈕並寫明原因 |
| N-H3 例外是窄的 | 受保護表（第 3 張）整欄 → `READ_ONLY`、讀回不變；非整欄的 A1:B40000（80,000 格）→ `RANGE_TOO_LARGE`；非整欄的 A3:A3（跨合併）→ `RANGE_MERGE_BOUNDARY`；整欄 A（含 A3:B3）→ 套用，A3 讀回 bold | 逐實例 | 同上 |
| N-H4 成本（量測登錄，不是判準） | op 13、整欄 op 7、整列 op 7、整表 op 7 的 ms | — | — |

**N-H4 與裁示 4 的關係**：整表 op 7 若超過 2 秒，角落改成「整表選取、格式拒絕並寫原因」（研究報告 Q4 的 B），append 記錄。

紅案（要紅在那一格，不是 fatal）：(a) 用 op 0 代替 op 13 走 N-H1 的「游標不動」→ 紅；(b) 整欄改成 endRow ＝ maxRows−2 → 不是整欄，`RANGE_TOO_LARGE`，N-H2 該格紅；(c) 把 E1 之前未設 zoom 的舊回覆（A＝110 px，`m4-cell-editing/native/geometry-discovery`）交給 N-H1 的判讀 → 對齊那格紅。

### 4.2 頁面（P：dev profile `ods-editor-v6`，Chrome 與 Firefox，鏡像）

| id | 判準 | 形式 | 如果永遠沒做 |
|---|---|---|---|
| P-H1 標號對齊格線 | DOM 裡每個 `[role=columnheader]`：相對 surface 的 left 與 width 等於該欄 op 13 回覆的 `startPx`、`endPx − startPx`，並等於頁面 `readCell(c, 0)` 的 `xTwips / 15`；列同理；隱藏欄列沒有元素；捲到第 1000 列與 AA 欄之後再量一次 | 逐實例（工具讀 DOM 枚舉） | 不畫標號 |
| P-H2 點標號選整欄／整列 | 每個可點欄 c：click 後 selection ＝ `{c, 0, c, maxRows−1}`、作用格 (c,0)、選取標籤 `X:X`、該欄 `aria-selected=true`；列同理；角落＝整表 | 逐實例 | 標號只顯示、不可點 |
| P-H3 shift-click 與拖曳 | 從 c1 shift-click／拖到 c2：selection ＝ `{min, 0, max, maxRows−1}`，左右兩個方向；列同理 | 逐實例 | 只能選單欄 |
| P-H4 格式流入 | 整欄 bold 之後頁面 `readCell(c,0)`、`readCell(c,999)` 皆 bold，工具列 B `aria-pressed=true`；復原一次回來 | 逐實例 | 同 N-H2 |
| P-H5 鍵 | 焦點在 `#cell-editor`、非編輯時：Ctrl+Space 與 Ctrl+Shift+Space → 整欄，Shift+Space → 整列，且作用格內容不變、沒有待送輸入 | 逐實例 | 只有滑鼠 |
| P-H6 讀屏 | 每個標號元素有非空 `aria-label`、`tabindex=-1`；選取改變後 `#toast` 含該欄列的標籤 | 逐實例 | 標號對讀屏不可見（登錄為「有行為而沒有東西守著」） |

紅案（頁面突變，紅要紅在那一格）：(a) 欄標 left 加 1 px → P-H1；(b) 整欄的 endRow 用可見列數 → P-H2、P-H4；(c) 隱藏欄畫成 1 px 元素 → P-H1；(d) Shift+Space 不 `preventDefault` → P-H5（儲存格多一個空白）。

## 5. 不在這一批（具名限制）

凍結窗格；Ctrl+click 多選不相連的欄列；拖曳改欄寬列高；插入／刪除欄列；篩選列在整欄寫入時不跳過（與桌面對 mark 的行為可能不同）；jumbo sheet；標號失效 callback（靠 revision）。

## 6. 夾具

新工具 `tools/create_calc_headers_fixture.py` 產生 `calc-headers.ods`：`cell-editing.ods` 的三張表（A 3 cm、B 1.8 cm、C 3 cm、D 隱藏、E 3 cm；列 1 0.5 cm、列 2 1 cm、列 4 隱藏；A3:B3 合併；第 3 張受保護）＋第 1000 列 A 欄一格文字＋AA1 一格文字。夾具先用儀器自己的管道看一次（原生讀回內容與欄寬）再當前置條件。

## 7. 如果永遠沒做

Calc 頁面維持沒有列標欄標、不能選整欄整列（現況），`SPEC-P-demo-batch-3.md` §141 的具名限制不變。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-11-05 | 初版：裁示、設計、判準（實作前） |

# RESEARCH-2026-11-04：Calc 列標／欄標與整欄整列選取（B 案）

設計研究，不是實作。讀的是 `wasm_sdk_probe/`、`libreoffice-26-8/`、`cool-26-04/` 與 `findings/evidence/m4-cell-editing/native/`；沒有跑任何建置、瀏覽器或宿主。

每條宣稱標記：〔已觀察〕＝在原始碼或證據檔讀到，附 `路徑:行`；〔推論〕＝從原始碼推出、要實驗才能定案；〔研究假設〕＝設計上的選擇。

---

## 0. 結論（一段）

列標欄標的幾何**核心已經算好、WASM 引擎已經在用**：`calc_cell_bridge.cpp` 的點選（op 5）每次都讀 `.uno:ViewRowColumnHeaders` 再丟掉〔已觀察，`wasm_sdk_probe/src/calc_cell_bridge.cpp:347–352`〕。B 案最小的引擎面是**一個新的唯讀 op**（讀可見矩形的標頭、不碰游標與選取），加上**把 65,536 格上限對「整欄／整列／整張表」放行**——這條上限目前守在三層（bridge、worker、SDK），要一起放。**整欄選取本身不需要引擎的 mark**：既有範圍 op 6–12 吃的是頁面給的明確矩形，不讀引擎的選取〔已觀察，`calc_cell_bridge.cpp:199–215`〕。建議不要走 Collabora 的 `.uno:SelectColumn`，理由在 §4.3。標頭用 DOM 按鈕畫（不用 canvas），a11y 與測試都順手。第一個實驗**不用建置**：既有的原生 harness 二進位能直接讀標頭 JSON。

---

## 1. 主 session「已確立」清單的核對

| 主 session 的說法 | 核對結果 |
| --- | --- |
| 頁面：`ods-editor.html` ＋ `ods-editor-app.js`，session 在 `spreadsheet-shell/`，有 `#tab-strip` 與 `#viewport`（overflow:auto），1 CSS px ＝ 15 twips | 〔已觀察〕對。`web/ods-editor.html:52–56、127–131`；`web/ods-editor-app.js:59–63`（`place()` 除以 15）。 |
| 出貨 profile ods-editor-v5 的匯出清單；沒有通用的 getCommandValues 匯出 | 〔已觀察〕對。`dist/profiles/ods-editor-v5/sdk-manifest.json` 的 capabilities 共 16 項，沒有 command-values 類；`src/sdk_api.cpp:224–244` 只有 `oxsdk_document_cell`，op 上限 12。 |
| `access()` 分派 0..12；op 5 用 ViewRowColumnHeaders ＋ `headerIndex` 點選再 `select` 再讀 `.uno:CellCursor` | 〔已觀察〕對。`calc_cell_bridge.cpp:303–381`。 |
| 「ViewRowColumnHeaders 的資料沒有到頁面，唯一回幾何的 op 會移動游標」 | 〔已觀察〕對，而且更強：op 0 與 op 5 **都**會 `selection->select(cell)`（`:371–372`），所以 readCell 也移游標。交接文件早就記了這個陷阱（`handoff/HANDOFF-2026-10-25-calc-owner-passes-input-range-next.md:71`）。 |
| 改引擎要連結、owner 跑 make；改動留在 build/ 的 dev profile | 對（CLAUDE.md〈節奏〉第 1 條）。 |
| **漏掉的**：65,536 格上限不只在 bridge | 〔已觀察〕三層都擋：`calc_cell_bridge.cpp:114、213–214`；`dist/profiles/ods-editor-v5/sdk-worker.js:1868–1870`（worker 在呼叫 WASM 前就拒）；`spreadsheet-shell/calc-document-sdk.js:44–50`（`rangeBounds` 在送 worker 前就拒）。整欄是 1,048,576 格，三層任何一層不改都到不了引擎。 |
| **漏掉的**：worker 會不會收到 LOK callback | 〔已觀察〕引擎把每個 LOK callback 都以 `{"type":"lok","id":…}` 送到 worker（`src/probe_engine.cpp:3245–3254`），但 worker 只把 id 0／1（INVALIDATE_TILES／INVALIDATE_VISIBLE_CURSOR）轉成 `document-invalidated`，其餘丟掉（`sdk-worker.js:1309–1316`）；而頁面側沒有任何人訂閱 `document-invalidated`（在 `sdk/`、`viewer-shell/`、`spreadsheet-shell/`、`web/ods-editor-app.js` 全文找不到字串）。`LOK_CALLBACK_INVALIDATE_HEADER`（id 33）走到 worker 就停了。 |

---

## 2. 核心 26.8 的 `.uno:ViewRowColumnHeaders`（問題 1）

### 2.1 入口與形狀

`doc_getCommandValues` 解析 `?x=&y=&width=&height=`，組 `tools::Rectangle(nX, nY, nX+nWidth, nY+nHeight)`，呼叫 `ITiledRenderable::getRowColumnHeaders`〔已觀察，`libreoffice-26-8/desktop/source/lib/init.cxx:6768–6812`〕→ `ScModelObj::getRowColumnHeaders` 用 `ScDocShell::GetViewData()` 的**目前 view**〔`sc/source/ui/unoobj/docuno.cxx:1165–1176`〕→ `ScTabView::getRowColumnHeaders`〔`sc/source/ui/view/tabview.cxx:2874–3101`〕。

回傳 JSON（原生實測在 cell-editing 夾具上，〔已觀察，`findings/evidence/m4-cell-editing/native/geometry-discovery/observations.jsonl:1`〕）：

```
{ "commandName": ".uno:ViewRowColumnHeaders",
  "rows":    [ {"text": 0, "size": 0, "groupLevels": 0}, {"text":"1","size":18}, {"text":"2","size":55},
               {"text":"3","size":73}, {"text":"4","size":73}, {"text":"5","size":90}, … ],
  "columns": [ {"text": 0, "size": 0, "groupLevels": 0}, {"text":"A","size":110}, {"text":"B","size":176},
               {"text":"C","size":286}, {"text":"D","size":286}, {"text":"E","size":396}, … ] }
```

讀法（對照 `tabview.cxx:2950–2985、3045–3080`）：

- 每筆 `{text, size}` 是「標籤為 text 的那一列／欄**結束**在累計 `size` px」。第一筆是起點：`text` 是 **JSON 數字** `nStartRow+1`／`nStartCol+1`（其餘是字串），`size` 是起點的累計 px，只有第一筆帶 `groupLevels`。矩形從 0 開始時 start index 是 −1，所以第一筆是 `{"text":0,"size":0}`；從中間開始時例如 `{"text":2,"size":55}`〔已觀察，`observations.jsonl:2`〕。
- 欄標籤來自 `pColBar[SC_SPLIT_LEFT]->GetEntryText(nCol)`（「A」「AA」…），列標籤來自 `pRowBar[SC_SPLIT_BOTTOM]->GetEntryText(nRow)`〔`tabview.cxx:2979、3072`〕。**只有**在 `LOK_FEATURE_RANGE_HEADERS` 打開時才改成數字欄名並做 run-length 壓縮（同寬相鄰只留一筆）〔`tabview.cxx:2881、2974–2976、3067–3072`；`init.cxx:7614`〕。我們的引擎**沒有**呼叫 `setOptionalFeatures`（`src/probe_engine.cpp` 全文無此字串，〔已觀察〕），所以每列每欄一筆、不壓縮。bridge 的 `headerIndex` 兩種都能解（`calc_cell_bridge.cpp:83–109`）。
- 回傳範圍比要求大：`ScRangeProvider` 兩端各放大 2 個索引（`mnEnlargeX/Y = 2`，`tabview.cxx:2795–2796`），列至少 25、欄至少 10（`:2924–2926、3019–3021`）。頁面要自己裁。
- `width=0`（或 `height=0`）會**略過該軸**（`if (rRectangle.Left() < rRectangle.Right())`，`:3002`），回 `"columns": []`。〔推論〕可用來只讀一軸；矩形完全空（`IsEmpty()`）則**什麼都不寫**（`:2878–2879`），bridge 的 `get_child("columns")` 會丟例外→`CELL_MODEL_ERROR`，新 op 要先擋。

### 2.2 單位：px，且在 bridge 設的 zoom 下恰好 1 px ＝ 15 twips

- `size` 是 `ScViewData::ToPixel(twips, PPTX)` 的**逐列截尾**累計（`tabview.cxx:2553–2563`；`sc/source/ui/inc/viewdata.hxx:746–752`：`long(twips*factor)`，非零至少 1 px）。
- LOK 下 `nScreenPPTX = DPI/1440`〔`sc/source/core/data/global.cxx:500–505`〕；`initializeForTiledRendering` 設 `TextWysiwyg(true)` 並重算 output factor → 1.0〔`docuno.cxx:1404–1410`；`sc/source/ui/docshell/docsh3.cxx:388–392`〕；`setClientZoom(256,256,3840,3840)` 算出 zoom ＝ toTwips(256px)/3840 ＝ 1〔`docuno.cxx:1123–1133`〕；`CalcPPT` ＝ nScreenPPTX × zoom〔`viewdata.cxx:3429–3432`〕。
- 原生實證：bridge 設 zoom 後，點選回的 E1 是 `xTwips=4410, widthTwips=1694, heightTwips=269`〔已觀察，`findings/evidence/m4-cell-editing/native/run-03-final/hit-r1-11-observations.jsonl:1`〕。4410 ＝ 294 px × 15（A 113 ＋ B 68 ＋ C 113 ＋ D 0），1694 ＝ 113×15−1，269 ＝ 18×15−1——與 `describeCellCursorAt` 的 `round(px/PPT)`、size−1 完全吻合〔`viewdata.cxx:2794–2825`〕。所以**標頭 px × 15 ＝ 游標 twips，兩者同源**，頁面的 `/15` 沒有累積誤差問題。
- 注意 geometry-discovery 那次（A ＝ 110 px）是在**沒設 client zoom** 的預設狀態下讀的（harness 只做 `initializeForRendering`，`tools/calc_cell_native.cpp:21`；bridge 的 `setClientZoom` 只在 cell op 裡）。新 op 要**先** `setClientZoom` 再讀，跟 op 5 一樣。
- `.uno:CellCursor` 只有在 compat flag `scPrintTwipsMsgs` 下才回文件 twips〔`sc/source/ui/view/gridwin.cxx:6250–6262`〕；引擎沒設 compat flag（`probe_engine.cpp` 無 `setCompatFlag`，〔已觀察〕），維持 px 對齊路徑。**不要**為了標頭去開這個 flag，會把游標變成另一套單位。

### 2.3 隱藏、自訂寬高、合併、凍結、矩形

- 隱藏欄／列：`size` 累計不增（D 與 C 同為 286、列 4 與列 3 同為 73，〔已觀察〕上面 JSON）；`lcl_GetColWidthPx` 對隱藏回 0（`tabview.cxx:2965、3061` 的註解）。頁面畫標頭時 0 寬者**不畫、不可點**，但在整欄選取的範圍裡仍是合法索引（契約 `hiddenCells: "included"`，`sdk-manifest.json`）。
- 自訂寬高：直接反映（3 cm → 113 px、1.8 cm → 68 px、0.5 cm → 18 px、1 cm → 37 px）。
- 合併格：標頭與合併無關（只看欄寬列高）。合併只在**選取**那邊出現（§4.4）。
- 凍結窗格：`getRowColumnHeaders` 沒有任何 split 處理（整段只用 `aViewData` 的寬高 helper）；Collabora 是在**客戶端**用 SheetGeometry 自己切 split（`cool-26-04/browser/src/control/Control.Header.ts:884–920`）。我們的頁面也沒有凍結概念（`ods-editor-app.js`、`calc-editor-session.js` 無 freeze／split 字串，〔已觀察〕）。**本批不做凍結**，列為具名限制。
- 矩形座標是 twips（`bInPixels=false` 時乘 PPT，`tabview.cxx:2706–2712`）。

### 2.4 副作用（「唯讀」但不是純函式）

`getRowColumnHeaders` 會：更新 `mnLOKStart/EndHeaderRow/Col` 與 LOK 寬高 helper（`tabview.cxx:2915–2922`）；呼叫 `lcl_ExtendTiledDimension`——接近目前 max tiled row/col 時放大、送 `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED` 與 invalidation（`:2799–2860`）；可見範圍變了就 `UpdateVisibleRange()`＋`UpdateFormulas()`（`:3091–3100`）。**不碰** mark、不碰 cursor（整段沒有 `SetCursor`／`MarkRange`，〔已觀察〕）。op 5 今天已經在承受這些副作用，所以新 op 不會引入新的種類；但「放大 tiled 區」會讓下一次 paint 回報更大的 document size → 頁面 `refit()` 重排（`viewer-shell/ods-viewer-session.js:306–319`），頁面要能接受標頭讀取之後 surface 長高。

### 2.5 什麼會讓標頭失效，worker 怎麼知道文件變了

- 核心送 `LOK_CALLBACK_INVALIDATE_HEADER`（payload `column`／`row`／`all`）的地方：切換工作表（`sc/source/ui/view/tabview3.cxx:2199`，`"all"`）、改欄寬列高／隱藏顯示／插入刪除與其 undo（`notifyAllViewsHeaderInvalidation` 的呼叫者：`viewfunc.cxx:1908–2001`、`viewfun2.cxx:186、242`、`dbfunc3.cxx:97、118`、`undoblk.cxx:302–589`、`undodat.cxx:195、492、1051`、`undocell.cxx:197`、`docfunc.cxx:243`，〔已觀察〕grep）。〔推論〕`undocell.cxx:197` 在儲存格內容的 undo 裡送 ROW_HEADER，應是自動列高的緣故——**改一格內容也可能改列高**。
- 這個 callback 到 worker 就被丟掉（§1 末列）。頁面今天知道文件變了的方式是 **revision**：引擎在 cell op `changed` 時 `advanceRevision()`（`probe_engine.cpp` `handleCell`，〔已觀察〕），session 用 `scheduler.invalidateRevision(revision)` 重畫（`calc-editor-session.js:169、256、273`）；paint 的 `paintKey = part/revision`（`ods-editor-app.js:225–228`）。
- 〔研究假設〕標頭快取鍵用 `part/revision/矩形`，跟 tiles 一樣——凡是會改列高的動作都會動 revision（它們都是 cell op），所以**不需要**把 INVALIDATE_HEADER 接到頁面。代價：每次 revision 變動多一次標頭讀取（一次 getCommandValues，推論成本見 E1）。要接 callback 的話是另一條契約（worker 新事件），本批不建議。

---

## 3. Collabora 怎麼做（問題 2）

〔已觀察〕全部來自 `cool-26-04/browser/src/`：

- **畫**：三個 canvas section——`ColumnHeader`（高 19 px，`control/Control.ColumnHeader.ts:21`）、`RowHeader`、`CornerHeader`（48×19，`Control.CornerHeader.ts:22`）。`drawHeaderEntry` 畫底、文字、框線與 resize 把手（`Control.ColumnHeader.ts:117–177`）；高亮 ＝ `isCurrent || isHighlighted`。**沒有任何 ARIA**（`Control.ColumnHeader.ts`、`Control.RowHeader.ts` 無 `aria` 字串；`Control.Header.ts` 的兩處命中是註解裡的英文字 variable）。
- **幾何來源**：主要是 `.uno:SheetGeometryData`（整張表的 run-length 寬高／隱藏／篩選／群組），`.uno:ViewRowColumnHeaders` 是相容路徑（`layer/tile/CalcTileLayer.js:620–637、1121–1133`）。`HeaderInfo.update` 從 sheet geometry 取可見索引區間，`isCurrent` 來自 `app.calc.cellAddress`，`isHighlighted` 看該標頭中點是否落在任一 `_cellSelections` 矩形內（`Control.Header.ts:834–940`）。
- **失效**：`invalidateheader: column|row|all` → `refreshViewData`（`CalcTileLayer.js:119–127`）；`invalidatesheetgeometry:` → 重新要 SheetGeometryData（`:129–135`）。
- **點選**：click → `_selectColumn(col, modifier)` 送 `.uno:SelectColumn {Col: unsigned short, Modifier: unsigned short}`（`Control.Header.ts:417–445`；列是 `.uno:SelectRow {Row: long, Modifier}`，`:272–300`）。Shift／Ctrl 直接轉成 modifier 位元（`Control.ColumnHeader.ts:198–213`；`docstate.ts:24` SHIFT＝4096 ＝ vcl `KEY_SHIFT 0x1000`，`include/vcl/keycodes.hxx:29–30`）。
- **拖曳**：滑鼠移到新標頭就再送一次 SelectColumn，第二筆起帶 SHIFT（`Control.Header.ts:681–699`）。
- **角落**：select all（`Control.CornerHeader.ts:44`）。
- **選取回饋**：核心回 `cellselectionarea:` → `_cellSelections` → 標頭重畫高亮（`layer/tile/CanvasTileLayer.js:2665–2690`）。整個迴圈是 **送指令 → 等 callback → 畫**。
- **核心側**：`SID_SELECT_COL/ROW` 帶 `FN_PARAM_1`（索引）與 `FN_PARAM_2`（modifier）→ `MarkColumns(nCol, nModifier)`（`sc/source/ui/view/cellsh4.cxx:368–394`；slot 定義 `sc/sdi/scalc.sdi:4814–4830`，`ReadOnlyDoc = TRUE`）。`MarkColumns`：無 modifier → 重設 mark、從 nCol 整欄；SHIFT → `bMoveIsShift` 讓 `DoneBlockMode` 提早 return、`InitBlockMode` 因已在 block mode 而 return、`MarkCursor` 從原 anchor 延伸；CTRL → `DoneBlockMode(true)` 轉 multi-mark 再加一欄；最後 `SetCursor(nCol, 0)`（`sc/source/ui/view/tabview3.cxx:1674–1699`；`tabview2.cxx` 的 `DoneBlockMode`／`InitBlockMode`）。
- **桌面鍵**：Shift+Space ＝ `.uno:SelectRow`；Ctrl+Space ＝ `.uno:SelectColumn`；**zh-TW／zh-CN 另有 Ctrl+Shift+Space ＝ SelectColumn**（Ctrl+Space 在 CJK 系統常是輸入法切換）〔`officecfg/registry/data/org/openoffice/Office/Accelerators.xcu:1254–1257、1352–1355、1364–1369`〕。

**哪些能搬到沒有 callback 串流的頁面**：畫法（高亮規則、把手留白、角落）、click／shift-click／drag 的語意、鍵綁定。**不能搬**的是迴圈本身：我們沒有 `cellselectionarea`，也不打算讓引擎的 mark 當真值源（§4.3）。

---

## 4. 最小引擎面（問題 3）

### 4.1 (a) 讀標頭、不動游標：一個新 op

〔研究假設〕op 13 `headers`，在 `access()` 裡**走 op ≥ 6 的那條岔路之前**分出去（op 0／5 從 `:342` 起就 `setActiveSheet`＋`setClientZoom`＋`select`；新 op 要 `setActiveSheet`＋`setClientZoom`，但**不**做 `:356–381` 的 select／CellCursor）。輸入放在 `text` 的 JSON：`{x, y, width, height}`（twips，頁面用 scroll/clientWidth × 15）。輸出：

```
{ ok, part, columns:[{index, label, startPx, endPx}], rows:[…], maxColumns, maxRows }
```

bridge 把核心的「累計 end」轉成 start/end 對、把第一筆（JSON 數字）當起點、`size` 相同者標為隱藏（`hidden:true`，startPx==endPx）。`maxColumns/maxRows` 來自 `dimensions->getColumns()->getCount()`（`calc_cell_bridge.cpp:334–336`，已經在算）——頁面需要它來組整欄範圍，今天頁面不知道一張表有幾列。矩形空、或 ptree 沒有 `columns/rows` → `CELL_GEOMETRY_UNAVAILABLE`。

為什麼是窄 op 不是通用 command-values 匯出：(1) 通用匯出把 JSON 形狀的解讀推到頁面，單位（px vs twips）與第一筆的特殊語意會在三個地方各解一次；(2) 既有契約都是「引擎回正規化後的封閉形狀，SDK `normalize*` 驗」（`calc-document-sdk.js:52–98`），窄 op 延續這個紀律；(3) 窄 op 的 red case 可以在 `normalizeHeaders` 落地（§6）。

### 4.2 (b) 整欄／整列選取：不需要引擎 mark，需要放行上限

既有範圍 op 6–12 用 `sheet->getCellRangeByPosition(column,row,endColumn,endRow)`（`calc_cell_bridge.cpp:215`），完全不看引擎 mark。頁面的選取模型本來就在頁面（`rectangle(anchor, focus)`，`calc-editor-session.js:15–23`）。所以整欄 ＝ 頁面建一個 `{column:c, row:0, endColumn:c, endRow:maxRows−1}` 的矩形，anchor 用 `readCell(c, 0)`（它會把引擎游標放到 c1，與桌面 `SetCursor(nCol,0)` 一致）。需要改的只有上限：

- `kRangeCellLimit = 65536`（`calc_cell_bridge.cpp:114`）、worker 的 `>65536`（`sdk-worker.js:1869–1870`）、SDK 的 `RANGE_CELL_LIMIT`（`calc-document-sdk.js:14、47–48`）三處同時加例外：**整欄（row==0 && endRow==maxRows−1）、整列（column==0 && endColumn==maxColumns−1）、整表** 放行。頁面側需要 `maxRows/maxColumns`（來自 4.1）。
- 〔推論〕核心對整欄套樣式是便宜的：UNO `setPropertyValues` 走 `ApplyPatternArea`，屬性以 run-length 存在 `ScAttrArray`；`getPropertyState`（混合判定）同樣走屬性陣列；桌面 Calc 對整欄按粗體是即時的。但要量（E2），因為 bridge 還做 `collapseToMergedArea()`（`:218`）與三個 `rangeFormat` 讀回（`:290–296`），每一個都是整欄範圍上的呼叫。
- undo：範圍 op 是一次 `setPropertyValues` → 一個 undo action（契約 `mutation: "single-native-pattern"`）；〔推論〕整欄也是一個（`ScUndoSelectionAttr` 存範圍舊屬性，run-length）。E2 用 `.uno:UndoCount` 驗「剛好加一」。

### 4.3 為什麼不用 `.uno:SelectColumn`

- 沒有東西讀引擎的 mark：op 6–12 讀明確矩形；頁面 undo 後用 `readCell` 重讀 anchor/focus（`calc-editor-session.js:357–372`）。接 `SelectColumn` 只是多一個真值源，正是 10-25 交接文件警告的「不要從引擎游標推導寫入目標」。
- `postUnoCommand` 的結果要等 callback（COOL 的迴圈），我們的 cell op 是同步 UNO；混用兩種時序是 finding 178 那類競態的溫床。
- 真正需要 mark 的是**未來**的「插入／刪除欄」「欄寬」這類作用在選取上的指令；其中 `.uno:ColumnWidth` 可帶明確 `Column` 參數（COOL `Control.ColumnHeader.ts:229–265`），插入刪除才需要 mark。到那一步再決定，不在 B 案。

### 4.4 危害清單（整欄範圍進既有 op 6–12）

| 危害 | 現況 | 建議 |
| --- | --- | --- |
| 1,048,576 列（`MAXROWCOUNT = 1024*1024`，`sc/inc/address.hxx:60`；欄 16,384） | 三層都拒（§1） | 放行整欄／整列／整表；其他矩形維持 65,536。E2 量時間。 |
| 合併格跨欄：夾具 A3:B3 合併 | `collapseToMergedArea` 把整欄 A 擴到 B → `crossesMerge` → **拒** `RANGE_MERGE_BOUNDARY`（`:216–222、229`） | 桌面 Calc 對整欄 A 套樣式會套到 A3（合併原點）而不管 B3；〔研究假設〕整欄／整列／整表**跳過**合併邊界檢查、套明確範圍。要擁有者裁（§8 Q2）。 |
| 受保護工作表（夾具第 3 張） | `isProtected && IsLocked`（或 AMBIGUOUS）→ `READ_ONLY`（`:230–235`）；整欄的 `CellProtection` 狀態幾乎一定 AMBIGUOUS 或 locked → 拒 | 正確行為：選得到、不能套。頁面 `formatTitle` 已會寫原因（`ods-editor-app.js:69–73`）。 |
| 隱藏／篩選列 | 契約 `hiddenCells: "included"` | 維持。篩選（autofilter）夾具本批不加；〔推論〕UNO 範圍寫入不會跳過篩選列，與桌面對 mark 的行為可能不同——列為具名限制。 |
| 唯讀宿主 | `storable->isReadonly()` → `READ_ONLY`（`:228`）；頁面 `formatAvailable` 看 `state.readOnly`（`ods-editor-app.js:64–68`） | 選取不是寫入，唯讀下仍可選整欄；按鈕照舊停用。 |
| 整表（角落） | 16,384 × 1,048,576 | 同一個例外；E2 量。 |
| 標頭 op 的副作用（§2.4） | op 5 已承受 | 頁面在標頭讀取後允許 refit。 |

---

## 5. 頁面設計（問題 4）

〔研究假設〕除非另註。

### 5.1 佈局與捲動同步

`#viewport` 仍是唯一的捲動容器。在 `#surface` 之外加三個 sticky 元素：`#column-headers`（`position:sticky; top:0`，高 20 px，寬跟 surface）、`#row-headers`（`sticky; left:0`，寬 48 px）、`#corner`（sticky 兩軸）。同一個 scroll container 內的 sticky **不需要 JS 同步**；現在的 `scroll` 監聽已經會 `render`＋`paint`（`ods-editor-app.js:707`），標頭讀取掛在同一個節拍：可見矩形（含 2 欄 25 列的餘量，§2.1）變了才讀。surface 的 `minWidth/minHeight`、`revealCell`、`point()`（`:627`，從 surface 的 rect 算 twips）都要把標頭偏移算進去——這是本批最容易出 off-by-header 的地方，判準 H1 直接量它。

### 5.2 畫什麼

標頭元素是 **DOM 按鈕**，不是 canvas：每個可見欄一個 `<button type="button" role="columnheader" data-column="2" aria-label="欄 C">C</button>`，絕對定位在 `startPx..endPx`；隱藏欄（0 寬）不產生元素。文字用引擎回的 `label`（不要頁面自己算「AA」——有引擎真值就讀它，CLAUDE.md §7）。理由：可見標頭最多幾十到一百多個，DOM 成本可忽略；hover／focus／hit-test／a11y／測試（DOM 查詢＝工具封閉的枚舉）全部免費；COOL 用 canvas 是因為它要畫群組與 resize 把手、而且沒有 a11y。

高亮：`aria-selected="true"` 給落在 `state.selection` 的欄／列（頁面側判斷，用 `selection.column..endColumn`），`data-current` 給 `state.cell` 的欄／列。整欄選取時角落與全部列標高亮（COOL 的 `wholeColumnSelected` 規則，`Control.Header.ts:822–827`）。

### 5.3 手勢

- click 標頭 c：`session.selectColumns(c, c)` → anchor ＝ `readCell(c,0)`，selection ＝ 整欄矩形，`_refreshRangeFormat()` 讀 op 6 取混合狀態。
- shift-click：`selectColumns(anchorColumn, c)`。
- drag：pointer capture 在標頭列上，移到新欄就 `selectColumns(anchorColumn, c)`，重用 `extendDrag` 的 pump 與 `gesture` 世代號（`ods-editor-app.js:640–659`），每個新欄一次 session op。
- ctrl-click（多選）：**不做**——頁面矩形模型與 bridge 範圍 op 都是單矩形。具名限制。
- 角落：整表。
- 既有的 `pendingEntry` 守則照抄：有未送出的輸入時拒絕換選取（`:662`）。
- 整欄選取時視覺矩形：寬用 anchor 的 x/width，高裁到 surface 高（`scheduler.documentCssSize`）；不要去 `readCell(c, 1048575)` 拿底邊——那會把 LOK 的 tiled 區拉到底（§2.4）。`selection-label` 顯示 `C:C · 作用中 C1`（桌面 Calc 顯示 `C1:C1048576`；〔研究假設〕用 `C:C` 較短、也不會被 83 欄截）。

### 5.4 鍵盤

- Ctrl+Space ＝ 目前選取的欄變整欄；Shift+Space ＝ 整列；**同時綁 Ctrl+Shift+Space ＝ 整欄**（Calc 自己給 zh-TW 的替代鍵，§3 末；Linux 的 ibus／fcitx 預設也吃 Ctrl+Space——〔推論〕瀏覽器可能根本收不到）。
- 攔截點：打字焦點在 `#cell-editor`（`focusGrid`，`ods-editor-app.js:390–393`），Shift+Space 會以 `beforeinput` 進 `startReplacement` 變成輸入一個空白（`:575–577`）。要在 `keydown` 就 `preventDefault`，且只在 `!state.editing && !pendingEntry && !composing`。Ctrl 類鍵走既有的 window keydown（`:709–725`）。

### 5.5 無障礙（產品路線把 a11y 提前）

螢幕閱讀器應得到：(1) 每個標頭是有名字的控制項（「欄 C」「列 5」）、帶 `aria-selected`；(2) 選取改變時一句話進 live region——頁面已有 `#toast[role=status][aria-live=polite]`（`ods-editor.html:132`），送「已選取整欄 C」；(3) 不用滑鼠也能做到：§5.4 的鍵。**不要**把一百多個按鈕放進 Tab 順序（`tabindex="-1"`），標頭列本身 `role="row"`、容器 `role="rowgroup"`——這是「語意正確但不佔 Tab」的最低配置。〔研究假設〕完整的 `role="grid"` 改造不在本批：那要把儲存格也變成 DOM，是另一條線。

---

## 6. 判準與紅案（問題 5）

形式依 CLAUDE.md〈驗收判準的形式〉§1：只收逐實例性質與工具封閉的枚舉。每條附「永遠沒做」的預設結論。

### 6.1 原生（N，LOK on build-native-26-8，`tools/calc_cell_native.cpp` 系）

| id | 判準 | 形式 | 永遠沒做 |
| --- | --- | --- | --- |
| N-H1 讀標頭不動游標 | 對夾具上每個請求矩形 r：`CellCursor` 在 op 13 前後相同；回傳的每筆 `endPx×15` 等於該欄／列用 op 0 讀到的 `xTwips+widthTwips+1`（列同理） | 逐實例（矩形清單由工具生成：左上、中段、右下、只有一軸、空矩形） | 標頭幾何視為未證明，頁面不得畫 |
| N-H2 整欄寫入到底 | 對夾具每一欄 c 做 op 7（bold on）於 (c,0)-(c,maxRows−1)：讀回 (c,0)、(c,999)、(c,maxRows−1) 皆 bold；`.uno:UndoCount` 恰加 1；undo 後三格皆不 bold | 逐實例 | 整欄格式視為不支援，頁面把整欄選取的格式按鈕停用並寫明原因 |
| N-H3 拒絕原樣 | 受保護表整欄 → `READ_ONLY`；A 欄含 A3:B3 合併 → 依 Q2 裁決（拒或套） | 逐實例 | 同上 |
| N-H4 成本 | op 13 一次、op 6 整欄一次、op 7 整欄一次、整表 op 7 一次的 ms（**量測登錄，不是判準**） | — | — |

紅案（先紅再綠）：(a) 把 op 13 改成在 `select` 之後讀 → N-H1 的「游標前後相同」紅；(b) 整欄 endRow 改 `maxRows−2` → N-H2 的最後一格紅；(c) 拿 geometry-discovery 的舊 JSON（110 px，未設 zoom）當 op 13 回覆餵判讀工具 → N-H1 的 `endPx×15` 紅。紅要紅在**那一格**，不是 fatal（11-03 教訓）。

### 6.2 頁面（P，dev profile，Chrome 與 Firefox）

| id | 判準 | 形式 | 永遠沒做 |
| --- | --- | --- | --- |
| P-H1 標頭對齊格線 | 對 DOM 裡每個 `[role=columnheader]`：其 `getBoundingClientRect().left − surface.left` 等於 `__calcEditor.state`（diagnostics）記錄的 op 13 回覆的 `startPx`；對每個可見欄 c 再比一次 `readCell(c,0).xTwips/15`；列同理 | 逐實例（DOM 枚舉由工具讀） | 不畫標頭 |
| P-H2 點標頭選整欄 | 對夾具每個可點欄 c（含 A，含 E 隱藏欄後）：click 後 `state.selection` ＝ `{column:c,row:0,endColumn:c,endRow:maxRows−1}`、`state.cell` ＝ (c,0)、`selection-label` 文字 `${label}:${label}`、該標頭 `aria-selected=true`、角落與可見列標全部 `aria-selected=true` | 逐實例 | 標頭純顯示、不可點 |
| P-H3 shift／drag | 從 c1 shift-click c2、從 c1 拖到 c2：selection ＝ `{min,0,max,maxRows−1}`，方向四種（SE/NW…參考 `create_calc_range_fixture.py` 的 case 命名） | 逐實例 | 單欄而已 |
| P-H4 格式流入 | 整欄 bold 後：`readCell(c,0)`、`readCell(c,999)` 皆 bold；工具列 B 的 `aria-pressed` 由 mixed → true；undo 一次回來 | 逐實例 | 同 N-H2 |
| P-H5 鍵 | Ctrl+Space／Ctrl+Shift+Space／Shift+Space 在 `#cell-editor` 有焦點且非編輯時：selection 變整欄／整列**且儲存格內容不變、`pendingEntry` 仍為 null** | 逐實例 | 只有滑鼠 |
| P-H6 a11y | 每個標頭元素有非空 `aria-label`、`tabindex=-1`；選取改變後 `#toast` 文字含該欄標籤 | 逐實例 | 標頭對讀屏不可見（登錄為「有行為而沒有東西守著」） |

紅案：(a) 標頭 `left` 加 1 px → P-H1 紅；(b) 把 `maxRows` 改讀 `rows.length`（可見列數）→ P-H2 的 endRow 紅、P-H4 的 (c,999) 紅；(c) 隱藏欄 D 當 1 px 畫出來 → P-H1 的 DOM 枚舉多一個元素、紅；(d) Shift+Space 不 preventDefault → P-H5 的「內容不變」紅（儲存格多一個空白）。

普查（§5）：工具要**列出夾具上每個可點標頭與每個不可點標頭（隱藏）**，不是抽三個。

### 6.3 夾具

重用 `tools/create_calc_edit_fixture.py` 的 `cell-editing.ods`（〔已觀察〕已有：A 3 cm、B 1.8 cm、D 隱藏、列 1 0.5 cm、列 2 1 cm、列 4 隱藏、A3:B3 合併、第 2 張表、第 3 張受保護），**再加**：(1) 列 1000 放一格文字（量 N-H2／P-H4 的「(c,999)」與遠處對齊）；(2) 一欄在 Z 之後（AA）放文字，驗標籤來自引擎；(3) **不加**凍結窗格（頁面不畫、核心標頭不切，§2.3）。夾具先用儀器自己的管道看一次（10-30 教訓）。

哪些只能原生量：整欄寫到 `maxRows−1`（頁面 readCell 到最後一列會拉長 tiled 區，不要在頁面量）、UndoCount、受保護表的拒絕碼、合併邊界裁決、成本。頁面量：對齊、手勢、鍵、a11y、格式流入到列 1000。

---

## 7. 風險、未知、與先跑的實驗（問題 6）

### 7.1 風險與未知

1. **三層上限**（§1）——漏改一層就是靜默拒絕；既有突變 `range-limit`（`tools/check_calc_range_mutations.py:11`）只守 SDK 那層，要補 worker 層的單元測試（`sdk/tests/sdk-worker-calc-cell.test.mjs` 的樣式）。
2. **合併邊界**（§4.4 Q2）——未裁決前 N-H3 不能寫。
3. **成本**（N-H4）——整表 op 6 的三個 `rangeFormat` 讀回加三個 `rangeStyle` 讀回，是六次整表 `getPropertyState`；〔推論〕run-length 很快，但沒量過。
4. **標頭讀取的副作用**（§2.4）——頁面每次捲動讀標頭，等於每次捲動都可能放大 tiled 區；今天 op 5 只在點選時做。要看 E1 的 DOCUMENT_SIZE_CHANGED 次數。
5. **Ctrl+Space 被輸入法吃掉**——頁面量不到「沒送到」與「送到但沒反應」的差別；P-H5 要有正向對照（用 Ctrl+Shift+Space）。
6. **dist worker 是凍結位元組**——新 op 要改共用的 `sdk/sdk-worker.js`，走新 profile（ods-editor-v6），連結一次（主 session 說上次 4.5 分鐘）；在擁有者排手測時段前只在 build/。
7. **`maxRows` 的來源**——`dimensions->getRows()->getCount()` 是文件的列數（1,048,576），不是 LOK 的 `MAXTILEDROW`（同值，`address.hxx:75`）；若未來 jumbo sheet（16M 列）打開，兩者分歧——本批不管，登錄。
8. 〔未知〕WASM 引擎的預設裝置 DPI 是否 96（決定 `nScreenPPTX = 1/15`）。run-03 的 4410/1694/269 是**原生**量的；WASM 上 31/31 儲存格檢查通過（`SPEC-P-demo-batch-3.md` §8）是間接證據。P-H1 第二句（對 `readCell` 的 twips/15）直接量它。

### 7.2 先跑的實驗（只提案，不執行）

**E1（原生，零建置，最便宜）**：`wasm_sdk_probe/build/calc-range-native/calc-cell-native` 已存在（2026-10-25，〔已觀察〕`ls`），`tools/calc_cell_native.cpp` 接受 `{"action":"command-values","command":…}` 與 cell op 行（`:21–60`）。餵：
1. `{"operation":0,"column":0,"row":0}`（讓 bridge 設 client zoom）；
2. `command-values .uno:CellCursor`；
3. `command-values .uno:ViewRowColumnHeaders?x=0&y=0&width=15000&height=6000`、`?x=0&y=0&width=15000&height=0`（只有欄）、`?x=0&y=0&width=0&height=0`（空）、`?x=0&y=3840000&width=15000&height=6000`（列 1000 附近）；
4. `command-values .uno:CellCursor`（比 2.）；
5. `{"operation":0,"column":0,"row":999}` 比 3. 的列 1000 `endPx×15`。
量到：形狀在 zoom 下（A 是 113 不是 110）、第一筆數字 text、隱藏 0 寬、空矩形的回覆、游標是否移動、列 1000 的 px×15 對 twips、每次呼叫 ms、stderr 有沒有 DOCUMENT_SIZE_CHANGED 類的 log。bridge.o 是 10-25 的位元組；op 0 與 command-values 從那之後沒改語意〔推論〕——收據記 sha 不符即可，或照 `tools/build_calc_undo_native.py` 的樣式（先看 `uptime`／`pgrep -a make`、快照來源、寫 build-receipt）重編一份含 `-DOXSDK_ODS_STYLE` 的。

**E2（原生，單檔 g++，需要一行補丁）**：複製 bridge 到快照、把 `kRangeCellLimit` 的檢查改成「整欄／整列／整表放行」（補丁要出現在收據），對夾具跑：op 6 整欄 A（含合併 → 看是不是 `RANGE_MERGE_BOUNDARY`）、op 6 整欄 C、op 7 整欄 C bold on、讀 (2,0)/(2,999)/(2,1048575)、`.uno:UndoCount` 前後、`uno .uno:Undo` 後再讀、受保護表整欄、整表 op 7；每步計時。這一步的產出直接決定 §4.4 的兩個裁決與 N-H4 的數字。

**E3（頁面，連結之後）**：dev profile 上先只做 P-H1（畫、不接點選），紅案 (a)(c) 先紅。點選與鍵（P-H2–P-H6）第二批。

順序理由：E1 零成本且回答單位與副作用；E2 回答「整欄進既有 op 安不安全」，是放行上限的前提；兩者都不需要連結。連結只做一次，在 E1／E2 把契約釘死之後。

---

## 8. 給擁有者的選項

**Q1 整欄選取走哪條路**
- **A（建議）**：頁面側矩形 ＋ 三層上限對整欄／整列／整表放行，不接引擎 mark。理由 §4.2–4.3。
- B：接 `.uno:SelectColumn`／`SelectRow`（Collabora 路線），再用 `XSelectionSupplier::getSelection()` 讀回。多一個真值源、多一種時序。
- C：兩者都做（頁面矩形為準，mark 只為未來的插入刪除欄鋪路）。多做的那半現在沒人讀。

**Q2 整欄碰到跨欄合併格（夾具 A3:B3）時的格式**
- **A（建議）**：整欄／整列／整表跳過 `RANGE_MERGE_BOUNDARY`，套明確範圍（桌面 Calc 的行為）。E2 先量合併原點與被覆蓋格各自的讀回。
- B：維持拒絕，提示「請同時選取 B 欄」。一致但使用者會覺得怪。
- C：只在合併格**超出**選取時拒絕（即現狀規則不變，整欄 A 仍拒）；等於 B。

**Q3 標頭怎麼畫**
- **A（建議）**：DOM 按鈕（§5.2）。
- B：canvas，照 COOL。省不到什麼，a11y 要另外補。
- C：先 DOM，之後列數多時再換。沒有證據會需要。

**Q4 角落**
- **A（建議）**：整表選取，格式允許（前提 E2 的整表時間可接受）。
- B：整表選取、格式拒絕並寫原因。
- C：角落無動作。

**Q5 鍵綁定**
- **A（建議）**：Ctrl+Space、Ctrl+Shift+Space（整欄）與 Shift+Space（整列）三個都綁。
- B：只綁 Ctrl+Space 與 Shift+Space。
- C：本批只有滑鼠。

**Q6 第一次量測的範圍**
- **A（建議）**：E1 → E2 → 連結 → P-H1 一臂＋紅案 → 擁有者手測時段再凍。
- B：直接連結、頁面先畫出來給擁有者看，原生補量。
- C：等下一個會改引擎的功能一起連結。

---

## 9. 引用索引（本文用到的檔案）

- 頁面：`wasm_sdk_probe/web/ods-editor.html`、`wasm_sdk_probe/web/ods-editor-app.js`、`wasm_sdk_probe/spreadsheet-shell/calc-editor-session.js`、`wasm_sdk_probe/spreadsheet-shell/calc-document-sdk.js`、`wasm_sdk_probe/viewer-shell/ods-viewer-session.js`
- 引擎：`wasm_sdk_probe/src/calc_cell_bridge.cpp`、`wasm_sdk_probe/src/sdk_api.cpp`、`wasm_sdk_probe/src/probe_engine.cpp`、`wasm_sdk_probe/dist/profiles/ods-editor-v5/sdk-worker.js`、`wasm_sdk_probe/dist/profiles/ods-editor-v5/sdk-manifest.json`
- 原生 harness：`wasm_sdk_probe/tools/calc_cell_native.cpp`、`wasm_sdk_probe/tools/run_calc_cell_native.py`、`wasm_sdk_probe/tools/build_calc_undo_native.py`、`wasm_sdk_probe/Makefile:5896–5925`、`wasm_sdk_probe/build/calc-range-native/calc-cell-native`
- 夾具與工具：`wasm_sdk_probe/tools/create_calc_edit_fixture.py`、`wasm_sdk_probe/tools/create_calc_range_fixture.py`、`wasm_sdk_probe/tools/check_calc_range_mutations.py`、`wasm_sdk_probe/tests/calc-*.test.mjs`、`wasm_sdk_probe/sdk/tests/sdk-worker-calc-cell.test.mjs`
- 證據：`findings/evidence/m4-cell-editing/native/geometry-discovery/{requests,observations}.jsonl`、`findings/evidence/m4-cell-editing/native/run-03-final/hit-r1-11-observations.jsonl`
- 核心 26.8：`desktop/source/lib/init.cxx`、`sc/source/ui/view/tabview.cxx`、`tabview2.cxx`、`tabview3.cxx`、`tabvwshc.cxx`、`cellsh4.cxx`、`gridwin.cxx`、`viewdata.cxx`、`sc/source/ui/inc/viewdata.hxx`、`sc/source/ui/unoobj/docuno.cxx`、`viewuno.cxx`、`sc/source/ui/docshell/docsh3.cxx`、`sc/source/core/data/global.cxx`、`sc/inc/address.hxx`、`sc/sdi/scalc.sdi`、`include/vcl/keycodes.hxx`、`officecfg/registry/data/org/openoffice/Office/Accelerators.xcu`
- Collabora：`cool-26-04/browser/src/control/Control.Header.ts`、`Control.ColumnHeader.ts`、`Control.RowHeader.ts`、`Control.CornerHeader.ts`、`cool-26-04/browser/src/layer/tile/CalcTileLayer.js`、`CanvasTileLayer.js`、`cool-26-04/browser/src/docstate.ts`
- 規格：`specs/SPEC-P-demo-batch-3.md:141`、`specs/SPEC-M4-cell-editing-v1.md:23、51`、`handoff/HANDOFF-2026-10-25-calc-owner-passes-input-range-next.md:69–71`

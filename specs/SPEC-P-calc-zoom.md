# SPEC-P-calc-zoom：Calc 的放大縮小

2026-11-07 擁有者在 0.2.59 手測後說：「如果要連結的話，幫我加一個功能，Calc沒有頁面放大縮小」。這一項跟 `SPEC-P-calc-copy.md` 追加 2（複製帶 `text/html`）一起進同一次連結（`ods-editor-v8`）。本文件只准 append。判準（第 4 節）在任何會算進它的量測之前釘死。

## 1. 現況（2026-11-07）

- 引擎在每個儲存格操作（`calc_cell_bridge.cpp` 的 `access()`）與標頭 op 13（`accessHeaders`）都強制 `setClientZoom(doc, 256, 256, 3840, 3840)`，也就是 1 CSS px＝15 twips。op 5（點選）在 `headerIndex` 裡用 `coordinate / 15` 換成像素。〔已觀察，原始碼〕
- 頁面全程用固定的 15 換算：`place()`、`revealCell()`、輸入框位置、桌面大小都是 twips ÷ 15，`point()` 是像素 × 15（`web/ods-editor-app.js`）。標頭欄寬固定（`HEADER_LEFT=48`、`HEADER_TOP=20`），標頭的位置來自 op 13。tile 排程器已經支援 `scale`（tile 的 twips＝CSS px × 15 ÷ scale，`reader-shell/tile-scheduler.js`），但 Calc 的 viewer session 一律設 `scale: 1`（`viewer-shell/ods-viewer-session.js` `_applyPart`）。每張 tile 256 CSS px，畫布像素＝CSS 像素（沒有乘 `devicePixelRatio`）。〔已觀察，原始碼〕
- 核心怎麼畫一張比例不同的 tile：`ScModelObj::paintTile` 用 tile 自己的比例當縮放（`docuno.cxx`），`ScGridWindow::PaintTile` 呼叫 `ScViewData::SetZoom`，列高、欄寬在**那個縮放**下逐列取整數像素（`gridwin4.cxx`、`viewdata.cxx` `ToPixel`、`fillinfo.cxx`）。所以 75% 時第 100 列的上緣是 Σ floor(hᵢ × 0.75 ÷ 15)，不是 100% 位置的 0.75 倍。頁面從 100% 的座標推不回來（240 與 254 twips 在 100% 都是 16 px，在 150% 是 24 與 25 px）。〔已觀察，原始碼；subagent 讀碼，主 session 量測驗證，見下〕
- Collabora：每次縮放送 `clientzoom`（tile 像素對 twips），kit 用 `setClientZoom` 套用，另外開了 print twips 訊息與 `SheetGeometry`，讓多個不同縮放的視圖共用同一套訊息（`cool-26-04/browser/src/layer/tile/CanvasTileLayer.js`、`CalcTileLayer.js`、`SheetGeometry.ts`、`kit/ChildSession.cpp`）。我們只有一個視圖、每個操作都重新問引擎，用不到後兩者，只需要「tile 的比例＝client zoom」這一條。等級是 2^(n/4)，標「150」的其實是 141%。〔已觀察，原始碼〕
- Writer 已有縮放（`SPEC-P-demo-batch-1.md` 第 3 節，等級 50、75、100、125、150、200，工具列 `−`／百分比／`+`）。本項的具名限制 `L-calc-zoom-not-done` 就在那裡。

**試跑**（scratchpad，不計數；原生 26.8＋第 3.1 節的 bridge 改動，結構夾具，F100 塗紅）：每一級先送 op 16，再讀 F100（op 0），把 twips × 256 ÷ tileTwips 換成像素，畫一張同比例的 tile，找紅色方塊。六級都是：方塊左、上緣比回報的位置少 1 px（格線被底色蓋住），右、下緣與回報的位置差不到 0.1 px；op 13 的 F 欄、第 100 列邊界與回報的像素相同；op 5 點在格子中央回 F100；回到 100% 後 F100 的矩形與一開始完全相同；不合法的 tileTwips 回 `INVALID_ARGUMENT`。反過來，拿 100% 的座標乘比例去比：50% 差 48 px、75% 差 70 px、125% 差 22 px、150% 差 45 px、200% 差 3 px。同一張 tile 在 client zoom 留在 100% 時畫出來的方塊一模一樣：畫面只看 tile 的比例，錯的是回報的座標。〔已觀察〕

## 2. 決定（agent 依 Writer 與 Collabora 的慣例定；不是難題，不送裁決）

1. **要連結。** 頁面單獨做只有一條路是對齊的：維持 100% 的 tile、用 CSS 放大點陣圖，字會糊。不採用。
2. **等級**：50、75、100、125、150、200，與 Writer 相同。每一級的 tileTwips＝384000 ÷ 百分比，都是整數（7680、5120、3840、3072、2560、1920），所以頁面的 tile（256 px 對 tileTwips）與 client zoom 的比例完全相同。開檔是 100%，與現在一樣。
3. **引擎**：新 define `OXSDK_ODS_ZOOM`（需要 `OXSDK_ODS_COPY`），能力位元 28 `cell-zoom`。op 16 收 `{tileTwips}`（封閉清單），存在 bridge 裡；之後每個操作都用它呼叫 `setClientZoom(doc, 256, 256, T, T)`，op 5 的換算改成 twips × 256 ÷ T。op 16 不改文件：不是 mutation、不綁 revision（同 13、15），回 `{tileTwips, percent, widthTwips, heightTwips, changed: false}`，大小是新縮放下的 `getDocumentSize`。沒有這個 define 時 T 恆為 3840，行為與 v7 相同。
4. **worker**：從凍結的 v7 worker 衍生（`tests/ods-v8-worker-delta.json`，`derive_ms_formats_worker.py` 多一筆）：新操作 `cellZoom`（→ op 16），需要 `cell-zoom` 能力，tileTwips 在 worker 先驗封閉清單。
5. **縮放套用到所有工作表**（桌面 Calc 的預設是各表同步）。不存檔、重開回到 100%。
6. **頁面**：工具列最後一組，自己一條分隔線：`−`、百分比、`+`；沒有 `cell-zoom` 能力時整組不顯示。`+`、`−` 走到下一級，按百分比回到 100%。換算的 15 全部改成 15 ÷ s。輸入框的字級跟著縮放（14 px × s）。縮放時畫面中央對到的文件位置留在中央。輸入中（原地編輯、公式列、待寫入的輸入）不能縮放，按鈕停用。各表記住的捲動位置照比例換算。
7. **session**：`setZoom(percent)` 排進佇列：op 16 → 在新縮放下重讀作用格與選取的兩端 → viewer 以新比例與 op 16 回的大小重設排程器 → 重畫。

## 3. 設計

### 3.1 引擎（`OXSDK_ODS_ZOOM`）

`gTileTwips`（預設 3840）＋`applyClientZoom(doc)`，取代兩處寫死的 `setClientZoom(…, 3840, 3840)`。op 16 `accessZoom`：驗封閉清單 → `setActiveSheet` → 存 T → `applyClientZoom` → `getDocumentSize`。`sdk_api`：最大 op 16、能力位元 28；`probe_engine`：op 16 不是 mutation、不綁 revision。

### 3.2 worker／SDK／session

- worker `cellZoom`：`{part, column: 0, row: 0, tileTwips}`，JSON `{tileTwips}`，需要 `cell-zoom`。
- SDK `setZoom(tileTwips)`：回覆形狀封閉（`tileTwips` 與要求相同、`percent`＝384000 ÷ tileTwips、`widthTwips`／`heightTwips` 是整數、`changed` 是 false）；`zoomSupported`。
- viewer session `setScale(scale, {widthTwips, heightTwips})`：存比例、照目前的表重設排程器（`_applyPart` 用存起來的比例，不再寫死 1）。
- calc session `setZoom(percent)`、`state.zoom`（百分比）、`_extent()` 用 twips 而非 CSS px × 15。

### 3.3 頁面

`tw()`＝15 ÷ s，`place()`、`revealCell()`、輸入框位置、桌面大小、`headerRectangle()`、`point()` 都用它。標頭照舊讀 op 13 的像素（在新縮放下本來就是那個縮放的像素）。`__calcEditor.zoom`（百分比）給 P 讀。

## 4. 判準（實作前釘死）

形式依 CLAUDE.md〈驗收判準的形式〉§1。夾具：`tools/create_calc_structure_fixture.py`（不改）。等級清單由 N 工具從 bridge 的封閉清單取、P 工具從頁面讀（工具封閉）。

### 4.1 原生（N：build-native-26-8，原始碼就是要連結的 bridge）

一個 harness session。先用 op 11 把第 1 張表的 F100、AA1000 與第 2 張表的 C30 塗成 `#ff0000`。「紅框」＝tile 畫布上紅色像素（R>200、G<60、B<60）的外框；「回報框」＝op 0 的矩形 × 256 ÷ T 減去 tile 的起點。tile 是對齊 256 px 格線、包住回報框左上角的那一張，畫布 512×512 px、2T×2T twips（比例仍是 s，夠放下 200% 的整格）。

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| N-Z1 對齊 | 六級、三個目標：紅框四邊都在回報框對應邊的 1 px 內 | Calc 沒有縮放 |
| N-Z2 標頭 | 六級、第 1 張表兩個目標：op 13 該欄的 `startPx`／`endPx` 與該列的，都在回報框左右、上下緣（換成文件像素）的 1 px 內 | 縮放後標頭對不上格子 |
| N-Z3 點選 | 六級、三個目標：op 5 點在回報框中央（換回 twips）回的是該格 | 縮放後點不到想點的格 |
| N-Z4 回到 100% | 走完六級再設 3840：三個目標的矩形與一開始的逐值相同；op 16 回的大小與一開始相同 | 縮放會留下痕跡 |
| N-Z5 沒有副作用 | 每個 op 16 都回 `changed: false`；整段前後 undo 清單長度相同；`.uno:CellCursor` 的欄列（最後兩個數）不變 | 縮放會被當成編輯 |
| N-Z6 拒絕是乾淨的 | tileTwips 1234、0、沒有 payload → `INVALID_ARGUMENT`、`mutationAttempted: false` | 拒絕視為不明 |
| N-Z7 成本（量測登錄） | 每一級 op 16 的 ms | — |

紅案（紅要紅在那一格）：判讀 N-Z1 時回報框改用 100% 讀到的矩形乘 s（v7 的行為：client zoom 寫死 3840）→ N-Z1 在 50、75、125、150 紅。對照組：同一份原始碼用 v7 的 define → op 16 回 `INVALID_ARGUMENT`。

### 4.2 頁面（P：連結後的 dev profile `ods-editor-v8`，Chrome 與 Firefox，鏡像，真實滑鼠與按鍵）

先在鏡像上用頁面自己的底色工具把 F100 塗紅（`#ff0000`）。「紅框」＝tile 畫布上紅色像素的外框，換成頁面座標；「作用格框」＝`#active-cell` 的 `getBoundingClientRect()`。

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| P-Z1 控制項 | 三個控制項可見、可按；開檔標籤是「100%」；每按一次 `+` 從 50 走到 200 是頁面列出的每一級；按百分比回到 100% | 只有原生證據 |
| P-Z2 重畫不是拉伸 | 每一級：每張 tile 的 `canvas.width` 等於它的 CSS 寬；桌面寬＝排程器的文件寬（twips）÷ 15 × s | 字會糊 |
| P-Z3 點到的是畫的那格 | 每一級：捲到 F100、真滑鼠點紅框中央 → 名稱方塊是 F100；作用格框與紅框四邊差 2 px 內 | 縮放後點錯格 |
| P-Z4 標頭對齊 | 每一級：F 欄標頭與第 100 列標頭的邊，與作用格框的邊差 1 px 內 | 標頭對不上 |
| P-Z5 中央不跑掉 | 每次縮放：視窗中央對到的文件位置（twips）變化不超過一列高 | 縮放後找不到剛才看的地方 |
| P-Z6 縮放後打字 | 150%：點 F100、打「縮放」、Enter → F100 讀回「縮放」；打字時輸入框的字級是 21 px（14 × 1.5） | 縮放後輸入跑到別格 |
| P-Z7 不碰文件 | 整段縮放（不含 P-Z6）：revision 不變、`hasUnsavedEdits()` 是 false | 縮放會觸發自動儲存 |
| P-Z8 換表 | 75% 時切到第 2 張表再切回：標籤仍是 75%，P-Z3 在 F100 仍成立 | 換表後縮放失效 |

紅案（頁面突變，紅要紅在那一格）：`point()` 仍乘 15 → P-Z3 在 100% 以外紅；不送 op 16、只改 tile 比例 → P-Z3 或 P-Z4 在 75% 紅；縮放不保持中央 → P-Z5 紅。

**手測**：擁有者在宿主上按 `+`、`−`，點格子、打字、切表。

## 5. 具名限制

- **L-calc-zoom-headers-fixed**：欄列標頭的寬高與字級不縮放（48×20 CSS px）。50% 時列高約 8 px，列號會擠在一起。
- **L-calc-zoom-not-while-editing**：輸入中不能縮放（桌面 Calc 可以）。
- **L-calc-zoom-not-persisted**：不存進檔案，重開回到 100%。
- **L-calc-zoom-browser-keys**：Ctrl＋滾輪與 Ctrl＋± 仍是瀏覽器縮放，不攔截。
- **L-calc-zoom-hidpi**：tile 畫布像素＝CSS 像素，高解析度螢幕上本來就略糊（不是這一項造成的，現在也一樣）。
- **L-calc-zoom-levels**：只有六級，沒有「符合寬度」，也沒有自訂百分比。

## 6. 如果永遠沒做

Calc 只能用瀏覽器自己的 Ctrl＋±（整頁一起放大，連工具列）。

## 7. 追加 1（2026-11-07，工具試跑之後、計數之前）：更正 N-Z1 的容差與 N-Z4 的大小

`check_calc_zoom_native.py` 在 scratchpad 試跑（不計數）時，N-Z1、N-Z4、N-Z5 紅。N-Z5 是工具的錯：op 16 寫死送第 1 張表，把作用中的表切回去，`.uno:CellCursor` 報的就換成那張表的游標。改成 op 16 送給目前的表，判準不動。另外兩項是**判準寫錯**，在任何計數之前更正如下。

- **N-Z1**：只在 200% 紅，紅框上、左緣與回報框差 1.067 px。試跑時已經看到上、左緣固定少 1 px（底色蓋住上一條格線），200% 時 1 px＝7.5 twips、回報的 twips 是整數，又多出最多 0.067 px。「1 px 內」沒有算到這兩件事。**取代為**：紅框的上、左緣＝回報框的上、左緣減 1，差 0.5 px 內；紅框的右、下緣與回報框的右、下緣差 0.5 px 內。比原本更嚴：任何一整個像素的錯位都會紅。紅案照舊用這條判讀。
- **N-Z4 的大小**：走完六級回到 3840 時，文件大小變大了（34155×255150 → 59655×267900）。查下去是 op 0 讀遠處的格子（AA1000）時游標移過去，核心的文件範圍就撐到游標去過的地方，而且不會縮回；只做縮放、中間不讀格子時，六級走一圈回來大小逐值相同（試跑，不計數）。所以「大小與一開始相同」的前提是錯的：大小跟游標去過哪裡有關，跟縮放無關。**取代為**：塗色之後、讀任何格子之前，只送 op 16 走完六級再回 3840，回的大小與第一次相同。矩形的部分照舊。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-11-07 | 初版：現況（含 subagent 讀碼、主 session 原生試跑）、決定 1–7、設計、判準 N-Z1–Z7、P-Z1–Z8 與紅案，實作前釘死（試跑在 scratchpad，不計數） |
| 2026-11-07 | 追加 1：工具試跑後、計數前，更正 N-Z1 的容差（上、左緣固定少 1 px，200% 有半個 twip 的捨入）與 N-Z4 的大小（大小隨游標去過的範圍變大，跟縮放無關） |

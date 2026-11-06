# SPEC-P-calc-copy：Calc 的 Ctrl+C（複製格、整欄、整列）

2026-11-06 擁有者從 0.2.58 手測後提的候選裡選 A（Ctrl+C＋跨表 UI），並在得知 Ctrl+C 要連結後選 A（兩條並行：頁面端的跨表 UI 與工作表身分另見 `SPEC-P-calc-sheets.md`，Ctrl+C 的連結交擁有者跑）。本文件只准 append。判準（第 4 節）在任何會算進它的量測之前釘死。

## 1. 現況（2026-11-06）

- 頁面的全域按鍵只處理 Ctrl+S／Z／Y／B／I／U（`web/ods-editor-app.js` 的 `window` keydown）；閒置時焦點在空的 `#cell-editor`，所以 Ctrl+C 什麼都不放上剪貼簿。〔已觀察，原始碼〕
- bridge 的範圍 op（6–12）只走 UNO，不在核心裡選取範圍；worker 的 `partText` 是全選後 `getTextSelection`。〔已觀察，原始碼〕
- 核心選到整欄、整列或整表時，複製文字會裁到有資料的區域，而且起點不固定在 A1（`sc/source/ui/app/transobj.cxx:229` `lcl_reduceBlock`，用的是 `ShrinkToUsedDataArea`、非固定起點）。所以頁面不能從 `partText` 切出指定範圍。〔已觀察，原始碼〕
- LOK 的 `getTextSelection` 走 `ScModelObj::getSelection` → `CopyToTransferable` → `ScTransferObj` 的文字匯出（`desktop/source/lib/init.cxx:5912`、`sc/source/ui/unoobj/docuno.cxx:973`），跟桌面版和 Collabora 的複製是同一條路。Collabora 的 Ctrl+C 用 `.uno:Copy` 後取 `text/html` 與 `text/plain`（`cool-26-04/browser/src/map/Clipboard.js`）。〔已觀察，原始碼〕
- Writer 頁面已經有先例：攔下 `copy` 事件，非同步向引擎要文字，再呼叫 `navigator.clipboard.writeText`（`web/e2-editor-app.js` 的 sink `copy`）。擁有者在 batch 5 手測過宿主上的「複製句子」。〔已觀察〕
- **試跑**（scratchpad，不計數；原生 26.8，結構夾具）：op 15 的試作在 B1:C2 回 `42\t84\n格式測試\t待清除\n`。整欄 A 是 1000 行，從 A1 到 A1000（145 ms），隱藏的第 4 列也在裡面。整列 1 是 27 欄，隱藏欄 D 是空字串。整表 152 ms。格內的換行與定位字元變成空白，`"` 不加引號。單一格沒有結尾換行（C1 → `84`）。空白範圍時 `getTextSelection` 回 null。受保護的表也能複製。復原筆數沒有變。〔已觀察〕

## 2. 決定（agent 依桌面 Calc／Collabora 的慣例定；不是難題，不送裁決）

1. **引擎路線＝在核心選取範圍後 `getTextSelection("text/plain;charset=utf-8")`**，文字照核心給的原樣放上剪貼簿，不由頁面組 TSV。理由：桌面版、Collabora 與我們貼到別處的結果才會一致（格式化的顯示值、隱藏列、整欄裁切都由核心決定）。
2. **只放純文字**。`text/html`（貼到試算表時保留格式）列為具名限制：多一種格式就多一條 `ClipboardItem` 路徑要在兩個瀏覽器上量。
3. **範圍＝目前的選取**：單格、矩形、整欄、整列、整表。部分矩形沿用 65,536 格上限（`RANGE_TOO_LARGE`）；整欄、整列、整表照 `SPEC-P-calc-headers` 3.2 放行（核心會自己裁）。
4. **入口**：格線有焦點、不在輸入中時的 Ctrl+C（與 Ctrl+Insert）。輸入中、公式列、名稱方塊裡的 Ctrl+C 不攔，交給瀏覽器原生複製欄位裡選取的文字。剪下（Ctrl+X）與貼上不在本批。
5. **沒有副作用**：op 15 唯讀，不推進 revision、不記 undo、不標 dirty。核心的選取在 op 結束前放回原處。
6. **profile**：v6 已在 0.2.58 發布、凍結在 `dist/profiles/`，所以新開 dev profile `ods-editor-v7`（v6 的 define 再加 `OXSDK_ODS_COPY`），放在 `build/`，等擁有者排手測時段才凍結（〈節奏〉1）。

## 3. 設計

### 3.1 引擎：op 15 `copy`（`OXSDK_ODS_COPY`，需要 `STRUCTURE`）

- `column`／`row` 是起點，`text` 是 JSON `{"endColumn", "endRow"}`。端點不合法 → `INVALID_ARGUMENT`；部分矩形超過 65,536 格 → `RANGE_TOO_LARGE`。
- `setActiveSheet(part)`；記下 `getSelection()`；`select(範圍)`。核心標起來的範圍必須蓋住要求的範圍（合併格可以把它撐大，不能縮小），否則 `COPY_REFUSED`。接著呼叫 LOK 的 `getTextSelection`，再把原本的選取放回去。回 null → `COPY_UNAVAILABLE`（空白範圍就是這樣，見第 1 節）。
- 回：`{ok, part, column, row, endColumn, endRow, markedColumn, markedRow, markedEndColumn, markedEndRow, plainText, changed: false}`。
- `sdk_api`：最大 op 15、能力位元 26 `CELL_COPY`；`probe_engine`：op 15 不是 mutation，也不綁 revision（跟 13 一樣）。

### 3.2 worker／SDK／session

- worker 新操作 `cellCopy`（→ op 15），形狀照 `rangeRead` 的端點驗證，需要 `cell-copy` 能力。加在 `tests/ods-v7-worker-delta.json`，從凍結的 v6 worker 衍生（`derive_ms_formats_worker.py` 表中多一筆）。
- SDK `copyRange(part, {column, row, endColumn, endRow})`，回覆形狀封閉（`plainText` 是字串、`changed` 是 false）；能力 `cell-copy`。
- session `copySelection()`：從目前的選取取範圍，排進佇列當讀取（不是 mutation），回 `{plainText, range}`。

### 3.3 頁面

Ctrl+C／Ctrl+Insert（第 2.4 條的情形）→ `preventDefault` → `session.copySelection()` → `navigator.clipboard.writeText(plainText)`。完成時 `#toast` 播「已複製 B1:C2」（整欄寫「已複製 A 欄」、整列寫「已複製第 2 列」、整表寫「已複製整張工作表」）。`COPY_UNAVAILABLE` 播「這個範圍沒有可以複製的文字。」，剪貼簿不動。`RANGE_TOO_LARGE` 播上限。`writeText` 被瀏覽器拒絕時，照實播出原因。沒有 `cell-copy` 能力（v6）時一律不攔。

## 4. 判準（實作前釘死）

形式依 CLAUDE.md〈驗收判準的形式〉§1。夾具見第 6 節。

### 4.1 原生（N：build-native-26-8，原始碼就是要連結的 `src/calc_cell_bridge.cpp`）

一個 harness session。讀回用 op 15 的 `plainText`、`.uno:CellCursor` 與 `.uno:Undo` 的清單長度。先用 op 1 寫三格：H1＝「第一行⏎第二行」、I1＝「有"引號"⇥與定位」、J1＝`=1/3`。

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| N-C1 矩形 | B1:C2 → `42\t84\n格式測試\t待清除\n`（C1 是公式，給的是顯示值） | Calc 頁面不能複製 |
| N-C2 整欄 | 整欄 A → 以 `\n` 結尾，共 1000 行；第 1 行「原始中文 Alpha」、第 4 行「隱藏列」、第 1000 行「第 1000 列」 | 同上 |
| N-C3 整列與整表 | 整列 1 → 一行、以 tab 分成 27 欄：第 4 欄空、第 8 欄「第一行 第二行」、第 27 欄「AA 欄」。整表的第一行與它相同 | 同上 |
| N-C4 單格、別張表、受保護表 | C1 → `84`；第 2 張表 A1 → `第二表不應改動`；第 3 張表（受保護）A1:B1 → `鎖定內容\t可編輯\n` | 同上 |
| N-C5 沒有副作用 | 先選 B2 再複製 B1:C2：之後 `.uno:CellCursor` 與複製前相同。每次複製都回 `changed: false`；整批複製前後 undo 清單長度相同 | 複製會移動選取或記一筆 undo（頁面得重讀） |
| N-C6 拒絕是乾淨的 | 空白範圍 L10:M11 → `COPY_UNAVAILABLE`；A1:Z3000 → `RANGE_TOO_LARGE`；端點顛倒 → `INVALID_ARGUMENT`；每一個都是 `mutationAttempted: false` | 拒絕視為不明 |
| N-C7 成本（量測登錄，不是判準） | B1:C2、整欄 A、整表的 ms | — |

紅案（紅要紅在那一格）：判讀 N-C1 時把 `endRow` 當成不含端點（要 B1:C1）→ N-C1 紅。對照組：同一份原始碼不帶 `OXSDK_ODS_COPY`（v6 的 define）→ op 15 回 `INVALID_ARGUMENT`。

### 4.2 頁面（P：連結後的 dev profile `ods-editor-v7`，Chrome 與 Firefox，鏡像，真實滑鼠與按鍵）

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| P-C1 矩形 | 從 B1 拖到 C2、按 Ctrl+C：剪貼簿＝N-C1 的文字；`#toast` 含「B1:C2」 | 只有原生證據 |
| P-C2 整欄整列 | 點欄標 A、Ctrl+C：剪貼簿的第 1 行與第 1000 行同 N-C2。點列標 2、Ctrl+C：剪貼簿以「鄰格必須保留\t格式測試\t待清除」開頭 | 同上 |
| P-C3 不弄髒文件 | 開檔後只做 P-C1：復原鈕仍停用、`hasUnsavedEdits()` 是 false、revision 不變 | 複製會觸發自動儲存 |
| P-C4 欄位裡的原生複製 | 公式列裡選取「42」、按 Ctrl+C：剪貼簿是「42」，不是範圍文字 | 欄位裡不能複製 |
| P-C5 空白範圍 | 剪貼簿先放一個標記字串，選 L10:M11、按 Ctrl+C：剪貼簿仍是那個標記，`#toast` 寫出原因 | 空白範圍沒有回應 |

紅案（頁面突變，紅要紅在那一格）：只複製作用格（不管選取）→ P-C1 紅。

## 5. 具名限制

不放 `text/html`（格式不跟著走）；格內的換行與定位字元由核心換成空白（與桌面的純文字複製相同）；隱藏列會被複製（核心行為）；部分矩形最多 65,536 格；剪下與貼上不在本批；沒有「螞蟻線」標示。

## 6. 夾具

`tools/create_calc_structure_fixture.py`（不改）：第 1 張「編輯測試」、第 2 張「另一張表」、第 3 張「保護測試」（受保護）、第 4 張「邊界測試」、第 5 張「陣列測試」。

## 7. 如果永遠沒做

Calc 頁面不能把格子複製到別的地方，要到桌面版做。

## 8. 追加 1（2026-11-06，p-01 之後）：撤回 P-C3 的「復原鈕仍停用」

`p-01`（連結後的 `ods-editor-v7`，wasm `36d0e1b8`）裡，P-C1、C2、C4、C5 在兩個瀏覽器都過了，只有 P-C3 紅：revision 0→0，`hasUnsavedEdits()` 是 false，但復原鈕沒有停用。原因是這一句的前提是錯的。頁面的復原鈕從來不看復原堆疊（`render()` 的停用條件是 `!ready || readOnly || uncertain || waiting || selectionPending`），開檔後本來就可以按〔已觀察，原始碼〕。依〈驗收判準的形式〉§4，**撤回這一句**，換成直接量規格 2.5「不記 undo」：P-C1 之後按一次工具列的復原，`#toast` 是「沒有可以復原的動作。」，而且 revision 不變。P-C3 的另外兩項照舊。工具同時記下開檔時復原鈕的狀態，用量測佐證前提錯了。`p-01` 照實留著，結果是紅的；更正之後的是 `p-02`。

## 9. 追加 2（2026-11-07）：同時放 `text/html`（擁有者裁示 A：照 Collabora，連結一次）

**起因**：0.2.59 手測，整欄複製貼到桌面 Calc 會在空格處拆格（`findings/evidence/host-0.2.59/handtest-2026-11-06/README.md`）。剪貼簿上的 TSV 是對的；桌面 Calc 收到多行 `STRING` 會走「匯入文字」對話框、套用者上次的分隔符號，同時有 HTML 時則先貼 HTML（`viewfun3.cxx` `PasteFromSystem`）。Collabora 兩種都放（`Clipboard.js`）。〔已觀察〕

**試跑**（scratchpad，不計數；原生 26.8＋本節的 bridge 改動，同一個結構夾具）：B1:C2 的 `text/html` 是 `ScTransferObj` 匯出的整份 HTML，一個 `<table>`、每格一個 `<td>`、格內文字照原樣（C1 另帶 `data-sheets-formula`），H1 的換行變成 `<br>`。整欄 A 124 KB／181 ms，整張表 2.5 MB／233 ms。空白範圍照舊 `COPY_UNAVAILABLE`。把 A1:C2 的 HTML 用 LOK `paste("text/html")` 貼到 L20：L20:N21 六格都對，L20 是完整的「原始中文 Alpha」，42、84 是數值。〔已觀察〕

### 9.1 決定（取代第 2.2 條「只放純文字」）

1. **引擎**：op 15 在範圍還選著時（放回選取之前）再呼叫一次 `getTextSelection(doc, "text/html")`，回覆多一個 `htmlText`（字串，照核心給的原樣）；核心給 null 時沒有這個欄位。新 define `OXSDK_ODS_COPY_HTML`（需要 `OXSDK_ODS_COPY`），能力位元 27 `cell-copy-html`。
2. **profile**：`ods-editor-v8`＝v7 的 define 再加 `OXSDK_ODS_COPY_HTML`（與 `SPEC-P-calc-zoom.md` 的 `OXSDK_ODS_ZOOM` 同一次連結），dev profile 放 `build/`。**這一項不需要改 worker**：op 15 的回覆原樣轉交，worker 沒有能力白名單，`activeManifest.profile` 只出現在錯誤訊息裡（已查，finding 179 的那種名字閘門不存在）。v8 的 worker 因為縮放的 `cellZoom` 而衍生（見該規格 2.4），衍生清單裡沒有複製的條目。manifest 由 `build_ms_formats_profile.py` 多一筆（base v7）產生，能力加 `cell-copy-html`。
3. **SDK／session**：`normalizeCopy` 收選擇性的 `htmlText`（有就必須是字串）；`copySelection()` 回 `{plainText, htmlText, range}`，沒有時 `htmlText` 是 null。
4. **頁面**：有 `htmlText` 且有 `ClipboardItem` 時，`navigator.clipboard.write([new ClipboardItem({"text/plain", "text/html"})])`；沒有，或 `write` 被拒，就照舊 `writeText(plainText)`。`#toast` 不變。頁面把走了哪條路記在 `__calcEditor.lastCopy`（寫入的格式、被拒的原因），給 P 讀。
5. **寫入時機不變**：仍是等引擎回覆後才寫。Collabora 是先把 promise 塞進 `ClipboardItem` 再等（為了 Safari 的使用者啟用規則）；0.2.59 手測裡「等回覆再寫」是成功的，Safari 不在支援範圍，所以不改。

### 9.2 判準（實作前釘死）

**原生（N，build-native-26-8，原始碼就是要連結的 bridge）**。`htmlText` 用 Python `html.parser` 解析：取第一個 `<table>`，每個 `<tr>` 的每個 `<td>` 的文字（`<br>` 算 `\n`、其餘空白原樣），得到「格文字表」。

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| N-H1 表格 | B1:C2 → 剛好一個 `<table>`，格文字表＝`[[42, 84], [格式測試, 待清除]]`；`plainText` 仍＝N-C1 的文字 | 貼到桌面 Calc 照舊拆格 |
| N-H2 空格、換行、定位 | A1:A2 → `[[原始中文 Alpha], [鄰格必須保留]]`；H1:I1 → `[[第一行⏎第二行, 有"引號"⇥與定位]]` | 同上 |
| N-H3 貼回去不拆格 | 另一個 session：A1:C2 的 `htmlText` 用 LOK `paste("text/html")` 貼到 L20，L20:N21 的 op 0 文字逐格等於 A1:C2 的文字 | 同上（這是要的性質；桌面貼上走同一個 `.uno:Paste`） |
| N-H4 整欄、整表、受保護表 | 整欄 A → 1000 個 `<tr>`，第 1 列「原始中文 Alpha」、第 1000 列「第 1000 列」；整表第 1 列有 27 格；第 3 張表 A1:B1 → `[[鎖定內容, 可編輯]]` | 同上 |
| N-H5 沒有副作用 | N-C5 照舊成立（讀 HTML 也不動游標、不記 undo、`changed: false`） | 複製會動到文件 |
| N-H6 拒絕照舊 | N-C6 照舊成立，拒絕的回覆沒有 `htmlText` | — |
| N-H7 成本（量測登錄） | B1:C2、整欄 A、整表的 ms 與 `htmlText` 位元組數 | — |

N-C1–C6 在同一個 session 照舊判一次（原始碼改了，原判準要重現）。紅案：把 LOK 在核心不給 HTML 時的退路（`init.cxx` `encodeTextAsHTML`：`<pre>` 包住純文字）餵給 N-H1 的判讀 → N-H1 紅。這是 wasm 上真正的風險（HTML 匯出沒進連結時，LOK 會靜靜地回這個）。對照組：同一份原始碼用 v7 的 define → op 15 成功但沒有 `htmlText`。

**頁面（P，連結後的 `ods-editor-v8`，Chrome 與 Firefox，鏡像）**。剪貼簿用 `navigator.clipboard.read()` 讀回，記下兩個瀏覽器的版本。

| id | 判準 | 如果永遠沒做 |
|---|---|---|
| P-H1 兩種格式 | 從 B1 拖到 C2、Ctrl+C：剪貼簿有 `text/plain` 與 `text/html`；`text/plain`＝N-C1 的文字；`text/html` 的格文字表＝N-H1；`lastCopy` 寫的是兩種 | 只有原生證據 |
| P-H2 整欄 | 點欄標 A、Ctrl+C：`text/html` 有 1000 個 `<tr>`，第 1 列「原始中文 Alpha」 | 同上 |
| P-H3 退路 | 頁面上拿掉 `window.ClipboardItem` 再做 P-H1：剪貼簿只有 `text/plain`、等於 N-C1 的文字，`#toast` 仍是「已複製 B1:C2」 | 舊瀏覽器上複製整個失效 |
| P-H4 瀏覽器讀回的 HTML 貼回去 | P-H1 從瀏覽器讀回的 `text/html`（瀏覽器可能消毒過），用 N-H3 的原生 session 貼到 L20：逐格等於 A1:C2 | 消毒過的 HTML 桌面可能讀不出格子 |
| P-C1–C5 | 原判準在 v8 上重跑（P-C1、C2 讀的是 `text/plain`） | — |

紅案（頁面突變，紅要紅在那一格）：只寫純文字（`write` 那一支拿掉）→ P-H1 紅。登錄（不是判準）：瀏覽器讀回的 HTML 與引擎給的相比，`<style>`、`<google-sheets-html-origin>` 留下沒有、位元組數。

**手測**：擁有者把整欄貼到桌面 Calc，格子不拆開。P 沒辦法看到桌面的貼上，這一格只有手測。

### 9.3 具名限制（更新第 5 節）

第 5 節的「不放 `text/html`」由本節取代。新增：HTML 照核心原樣放上去，頁面不改寫（瀏覽器會不會消毒、消毒成什麼，量測登錄）；HTML 匯出含字型與欄寬，貼到別處時格式跟著走；整表的 HTML 約 2.5 MB；Safari 不在範圍（第 9.1.5 條）。

## 10. 追加 3（2026-11-07，工具試跑之後、計數之前）：更正 N-H4 與 P-H2 的列數、格數

`check_calc_copy_native.py --html` 在 scratchpad 試跑（不計數）時只有 N-H4 紅：整欄 A 的 HTML 是 999 個 `<tr>`，整表第 1 列是 26 格。少的剛好是隱藏的第 4 列（「隱藏列」）與隱藏的 D 欄；純文字兩者都有（N-C2、N-C3）。核心的 HTML 匯出本來就跳過隱藏的欄列（`sc/source/filter/html/htmlexp.cxx` 的 `ColHidden`、`RowHidden`）〔已觀察，原始碼＋試跑〕。我寫判準時假設 HTML 與純文字逐行對應，那是錯的。在任何計數之前更正：

- **N-H4 取代為**：整欄 A → 999 個 `<tr>`，第 1 列「原始中文 Alpha」、第 4 列「隱藏列之後」、最後一列「第 1000 列」，沒有一格是「隱藏列」；整表第 1 列 → 26 格，第 4 格「隱藏欄之後」；受保護表照舊。
- **P-H2 取代為**：`text/html` 有 999 個 `<tr>`，第 1 列「原始中文 Alpha」。

新增具名限制：**HTML 不含隱藏的欄列**（核心的行為），所以貼到桌面 Calc 時隱藏列會不見；純文字含有隱藏列（第 5 節），兩種格式在這一點上不一致。

## 11. 追加 4（2026-11-07，p-copy-01 之後）：P-H4 要貼 A1:C2 的瀏覽器 HTML

`findings/evidence/calc-v8/p-copy-01`（連結後的 `ods-editor-v8`，wasm `61e2a069`，Chrome 156、Firefox 157）：P-C1–C5、P-H1、P-H2 兩個瀏覽器都過；P-H4 兩個都紅，Firefox 另紅 P-H3。

- **P-H4 是判準寫錯。** 第 9.2 節寫「P-H1 從瀏覽器讀回的 `text/html` … 貼到 L20：逐格等於 A1:C2」，但 P-H1 複製的是 B1:C2，貼回來本來就只會是 B1:C2。實際貼回的 L20:M21 是 42、84、格式測試、待清除，正是 B1:C2〔已觀察〕。而且 B1:C2 沒有一格帶空格，測不到要的性質。**取代為**：P-H4 另外從 A1 拖到 C2、按 Ctrl+C，把瀏覽器讀回的 `text/html` 貼到 L20，逐格等於 A1:C2，L20 是完整的「原始中文 Alpha」。
- **Firefox 的 P-H3 是工具的錯**：`delete globalThis.ClipboardItem` 在 Firefox 沒有效果（讀回仍是 `function`，DOM 建構子刪掉之後會再被解析出來），所以頁面沒有走到退路。改成把它定義為 `undefined`，判準不動。
- 登錄（不是判準）：Chrome 讀回 1673 bytes，沒有 `<style>`，保留 `<google-sheets-html-origin>`；Firefox 讀回 1127 bytes，保留 `<style>`，去掉了那個元素。引擎給的是 1276 bytes。兩者都解析成同一張格子表（P-H1）。

`p-copy-01` 照實留著，結果是紅的；更正之後的是 `p-copy-02`。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-11-06 | 初版：決定 1–6、判準 N-C1–C7、P-C1–C5 與紅案，實作前釘死（試跑在 scratchpad，不計數） |
| 2026-11-06 | 追加 1：撤回 P-C3「復原鈕仍停用」（頁面從不依堆疊停用復原鈕），改量「按復原沒有東西可復原」 |
| 2026-11-07 | 追加 2：同時放 `text/html`（擁有者裁示 A）；決定 9.1、判準 N-H1–H7、P-H1–H4 與紅案，實作前釘死 |
| 2026-11-07 | 追加 3：工具試跑後、計數前，更正 N-H4、P-H2（核心的 HTML 匯出跳過隱藏的欄列） |
| 2026-11-07 | 追加 4：p-copy-01 之後，P-H4 改貼 A1:C2 的瀏覽器 HTML（原文拿 P-H1 的 B1:C2 去比 A1:C2）；Firefox 的 P-H3 是工具的錯 |

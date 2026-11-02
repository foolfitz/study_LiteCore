# SPEC-P-demo-batch-3：擁有者手測回報的四點

2026-11-02 擁有者手測 0.2.49 後回報：

1. Writer 的 Shift＋左右可以選取，Shift＋上下會報錯。
2. Calc 會自動存檔嗎？
3. Calc 要有文字顏色、儲存格底色。
4. Writer 和 Calc 都要有對齊（置左、置中等）。

擁有者離席，授權自主執行，判斷題可交 fable 代為裁決，可參考 Collabora Online 原始碼。
會編譯的 make 仍是擁有者的（全域規則，這次沒有說「幫我建置」）。

判準在實作前釘死；本文件只准 append。

## 1. 第 2 點的答案（問題，不是工作項）

會。`spreadsheet-shell/calc-autosave.js`：只在 Nextcloud 裡開啟時啟用（`host===true`），`AUTOSAVE_TIMING` idle 30 秒、cap 300 秒、quiet 3 秒，分頁切到背景時立刻試存一次（`visibilitychange`）。儲存格還在輸入中不存（`editing==null` 才允許），確認輸入後才算。狀態列 `#autosave-status` 寫「自動儲存已開啟」「編輯中（確認後自動儲存）」「自動儲存中…」，宿主只藏 `.statusbar`，`.calc-statusbar` 看得到。量測：`findings/evidence/calc-range-autosave/`（瀏覽器 108/108）、`findings/evidence/host-0.2.37/`（真實 Files 54/54）。

本批不改這部分。

## 2. 第 1 點：e2-editor-v30（只換 worker，不連結）

根因（finding 179，實測重現，訊息 `INVALID_ARGUMENT：editorActionV2 requires a closed action and typed options`）：`featureExtendPermitted` 寫死 `activeManifest?.profile === "e2-editor-v28"`。v29 沿用 v28 worker 的位元組，所以名字對不上：左右走 `EDITOR_V1_MOVE_ACTIONS` 不受影響，上下、Home、End 全被 worker 擋在引擎之前。

處方：新 profile `e2-editor-v30`，loader、wasm、exports 逐位元等於 v29，worker＝archived v29 worker ＋封閉差異：`featureExtendPermitted` 不再比對 profile 名字，只看 `abiVersion === 6`（＋檔頭註解）。不再改名字的理由：這個閘門每換一次 profile 就要改一次，而且忘了改的時候沒有東西會紅；ABI 6 與 `EDITOR_V23_EXTEND_ACTIONS` 已經把範圍封閉住。

### 判準

- **S1（產品路徑，真實按鍵，先紅）**：`tools/check_writer_shift_lines.py`，鏡像、Chrome 與 Firefox。在 t3-long 的多行段落裡，對 Shift＋↑、↓、Home、End、←、→ 各按一次：無錯誤 toast、請求 `ok`、引擎回報的選取是範圍（`selectionRectangles` 非空或 `selectionType` 為 TEXT）、與按鍵前不同。**v29 頁面必須紅（↑↓ Home End 四格）**，v30 必須全綠。放開 Shift 後一般方向鍵仍能收合（一格）。
- **S2（逐實例）**：`tools/check_extend_gate_instances.py`：`dist/profiles/` 裡每一個 `abiVersion === 6` 的 profile，用它自己的 worker、自己的 manifest，在 vm 裡對六個移動各送一次 `editorActionV2 {extendSelection:true}`，不得回 `INVALID_ARGUMENT`。母數由工具從目錄生成（CLAUDE.md §1 形式二）。v29 必須紅、v23–v28 必須綠；往目錄放進一個虛構的 ABI 6 profile（名字不在任何閘門裡）時，v30 worker 綠、v29 worker 紅。工具要自己檢查非空洞（掃到 0 個 profile 就紅）。接進 `make test-v30-extend-gate-static`。
- **D1（差異）**：`tests/test_v30_feature_worker_delta.py`：archived v29 worker ＋ `tests/v30-worker-delta.json` 的封閉清單逐位元等於 `sdk/v30-extend-gate-worker.js`。`tools/check_v30_extend_gate_contract.py`：manifest 除 profile 名與 worker 綁定外，每個葉子等於 v29；wasm、loader、exports 的位元組等於 archived v29。
- **回歸**：第 85 代凍結、F4（四臂）、F3（剪貼簿）、Z、V0′、宿主 0.2.50 的 Files 工作流與 `HOST_BATCH_HOLDS`、`LAYOUT_HOLDS`。Shift 選取之後的 S5 形狀（Shift 接刪除）不重算計數；擁有者要 K 再談。

如果永遠沒做：0.2.45 以來的 Shift＋上下持續報錯，名義出貨版也帶著，要在交接列為已知缺陷。

## 3. 第 3、4 點：Calc 樣式與兩邊的對齊（要連結）

Collabora 的做法（`browser/src/control/Control.TopToolbar.js`、`Control.Toolbar.js`、`ColorPicker.ts`、`Control.NotebookbarCalc.js`）：

- Calc 文字顏色 `.uno:Color`、底色 `.uno:BackgroundColor`，對齊 `.uno:AlignLeft`、`.uno:AlignHorizontalCenter`、`.uno:AlignRight`、`.uno:AlignBlock`。
- Writer 對齊 `.uno:LeftPara`、`.uno:CenterPara`、`.uno:RightPara`、`.uno:JustifyPara`。
- 顏色選擇器：一列 10 個基底色，下面 8 階明暗，加「自動／無填滿」。

本專案的 ABI 是封閉的（不接受任意 UNO 指令），所以都要新增動作。

### 3.1 Calc：`ods-editor-v3`

沿 `calc_cell_bridge.cpp` 的範圍路徑（UNO 屬性＋一次 `setPropertyValues`，不逐格寫），新增 define `OXSDK_ODS_STYLE`：

| op | 動作 | 屬性 | 值 |
|---|---|---|---|
| 10 | 文字顏色 | `CharColor` | RGB 整數，`-1`＝自動 |
| 11 | 底色 | `CellBackColor` | RGB 整數，`-1`＝無填滿 |
| 12 | 水平對齊 | `HoriJustify` | `standard`／`left`／`center`／`right`／`block` |

對應 worker 的 `rangeStyle` 操作、manifest 能力 `cell-range-styling`、`calc-document-sdk.js` 的 `setRangeStyle`、session 的 `setStyle`。讀回：範圍快照多三個鍵 `textColor`、`backColor`、`horizontalAlign`，值混合時是 `"mixed"`。

既有判斷都沿用：唯讀、保護、跨合併格在變更前整批拒絕；65,536 格上限；後置條件讀回不符回 `RANGE_POSTCONDITION_FAILED`；已是目標值時 `changed:false` 不寫入。

### 3.2 Writer：`e2-editor-v31`

四個新動作走既有的 ordered format barrier（與 `set-paragraph-*` 同一條路）：

| 動作 | wire id | UNO |
|---|---|---|
| `set-align-left` | 24 | `.uno:LeftPara` |
| `set-align-center` | 25 | `.uno:CenterPara` |
| `set-align-right` | 26 | `.uno:RightPara` |
| `set-align-justify` | 27 | `.uno:JustifyPara` |

gesture：`collapsed`、`range-single`、`range-cross`。後置條件由 HTML 讀回的區塊對齊判定，不用 state 快取（finding 021）。**實際輸出形狀先原生量再寫**（CLAUDE.md §7、「實量 Writer 的順序」）。

`kMaxExternalAction`、`kMaxInternalEditorAction` 要跟著清單走，否則 manifest 寫了、引擎無條件拒絕（CLAUDE.md 工作結論第一條）。

### 3.3 頁面

- Writer：工具列四顆對齊鈕，沿 `offers()` 的規則：profile 沒有就不顯示。
- Calc：文字顏色、底色各一顆（顏色條顯示目前選的顏色；按主鈕套用目前顏色，旁邊小箭頭開色盤），四顆對齊鈕。色盤沿 Collabora：10 欄基底＋明暗，加「自動」或「無填滿」。
- 所有新控制項在 Nextcloud 淺色、深色主題都一樣（沿 T6）。

### 判準

- **N1（原生，先量）**：`.uno:*Para` 在單段、跨段、空段落的 HTML 讀回形狀；ODT 存檔的 `fo:text-align`。`CharColor`、`CellBackColor`、`HoriJustify` 在原生橋接上的讀回與 ODS 存檔（`fo:color`、`fo:background-color`、`fo:text-align`）；混合、保護、跨合併、唯讀；寫入一次一筆 undo。
- **E1（語法）**：`-fsyntax-only` 帶 define 通過，附正向對照（故意的錯在帶 define 時被抓到）。
- **W1（差異）**：v31 worker、ods-editor-v3 worker 都是 archived 前身＋封閉清單。
- **P1（Writer，瀏覽器，連結之後）**：四種對齊 × 三種 gesture（＋空段落、最後一段、清單段落、標題段落）：存出的 ODT 的 `fo:text-align` 正確、復原一步回到原值、重新開檔還在。
- **P2（Calc，瀏覽器，連結之後）**：顏色、底色、四種對齊 × 單格、範圍、整欄（上限內）：ODS 樣式正確、重開還在、畫面有畫出來（去問狀態，再加一次取樣畫面上的像素顏色當第二證據）、復原一步回去、保護／唯讀／跨合併拒絕且文字明確。
- **P3（宿主）**：新版宿主上 Files 工作流、`HOST_BATCH_HOLDS`、`LAYOUT_HOLDS`、T6 延伸到新控制項。

如果永遠沒做（擁有者沒連結）：頁面不顯示新控制項，產品行為等於 v30，本節程式碼留在樹上不影響任何出貨。

## 4. 邊界

- 不加 Writer 文字顏色（擁有者只要 Calc 的）；不加字型、字級、垂直對齊。
- 不做 push；不動 0.2.45 的名義出貨宣告。是否成為日常候選是擁有者的決定。
- 連結由擁有者執行。工具與指令在連結手冊裡（見本批 handoff）。

## 5. 追加 1（2026-11-02，實作中，於任何連結之前）

更正與補充，上面的原文留著：

- **ABI 維持 6。** 第 3.2 節沒寫。v31 只 append 動作，ABI 6 的 client 能送的東西意思都沒變；shell 的選取與刪除路徑全都寫死 `abiVersion === 6`，升號會一次全關掉，等於把 finding 179 的缺陷用數字重演一次。
- **Calc 的讀回值是字串。** 取代第 3.1 節「值混合時是 mixed」之外的細節：`textColor`、`backColor` 是 `#rrggbb` 或 `auto`／`none`，`horizontalAlign` 是閉集五個值。文件裡有按鈕設不出來的值（`REPEAT`）時讀成 `other`，不併入鄰近的值。理由：`write_json` 把數字都變成字串，而 `-1` 不是顏色。
- **Writer worker 的差異比第 3.2 節少一項。** 原本打算把四個動作也放進 worker 的 `EDITOR_V2_PARAGRAPH_ACTIONS`。causal control 顯示它沒有可觀察的效果：非 move、非 format 的動作帶旗標本來就被拒。沒效果的差異不留。
- **P2 取消「復原一步回去」。** Calc 頁面沒有復原按鈕也沒有 Ctrl+Z 路徑，這一格量不到產品路徑。原生 N1 已量到一次寫入一步復原（`native-calc-style/run-01` 的 `sequence/*`）。Calc 頁面要不要有復原，是另一件事，本批不做。
- **N1 結果。** Writer：四個指令在段落、標題、清單項目、已置中、空段落（中段、最後一段走 `.uno:CharLeftSel` 退路）、單段與跨段範圍，HTML 都寫 `align="…"`，ODT 寫 `fo:text-align`，一步復原。Calc：30/30，包含保護、跨合併、隱藏、上限、閉集拒絕。

## 6. 追加 2（2026-11-02，連結之前，外部審核逼出來的）

Codex 唯讀審核（`findings/evidence/demo-batch-3/review/codex-review.txt`）指出第 3.2 節的設計有一個會放錯內容的缺陷：format barrier 用派送前的游標矩形還原游標，而對齊會把文字水平移開，舊座標落到另一個字上，下一個按鍵打在錯的位置。barrier 只確認「沒有選取」，所以還回報成功。

**N2（原生，`native-writer-align-caret/`）**：11 個游標位置 × 3 種對齊，每格插入一個 X 再存檔，和只派送不讀回的結果比。座標還原 **16/33 放錯**（靠左的 11 格沒有移動，當然對；靠右與置中多半錯）。改用下面的讀法 **33/33 正確**，空白文件另加 2 格也對。

**取代第 3.2 節「後置條件由 HTML 讀回」的讀法**（判準 P1 不變）：

- 游標：派送後往回選一個字元（`.uno:CharLeftSel`，引擎已有的 v28 退路指令），讀 HTML，再 `.uno:GoRight`：Writer 從 point 移動並放掉選取（finding 129），正好回到原處。不需要任何座標。游標所在段落是讀回的**最後一塊**。文件開頭往回選不到，改往前（`.uno:CharRightSel`、`.uno:GoLeft`），所在段落是**第一塊**。
- 選取範圍：不分單段或跨段，都從使用者的選取直接讀，選取留著，和 Writer 一樣。
- `L-align-blank-document`：整份文件只有一個空段落時兩個方向都選不到，結果靠 UNO 回覆與可讀的 undo 堆疊；N2 的空白文件兩格（含按第二次）存檔正確。

**Writer 工具列的選取收合**不適用對齊：其他段落動作按完會收合，對齊不會。

Codex 另外兩點：client 還沒接受四個動作（本來就排在回歸鏈之後做）；Calc 拖曳選取結束時只刷新 B/I/U、不刷新新控制項（已修，`renderFormatControls` 帶上樣式）。

## 7. 追加 3：鄰居（不是這批的）

同一支 N2 量到已出貨的項目符號、編號走同一條座標還原，6/6 放錯（finding 180）。標題動作走同一條路，沒有量。**本批不改**：那條讀法有 F3、V0′ 綁著，換讀法要重驗，而且擁有者沒有要求。修法已知（本節第 6 節的讀法），等擁有者決定。

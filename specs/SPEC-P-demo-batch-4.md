# SPEC-P-demo-batch-4：擁有者補充的 Writer 需求

2026-11-02 擁有者在 demo batch 3 連結之後補充，原文：

> 1. Heading 應該有不只一個可以選，比如說 H1 ~ H4，按下之後有下拉式選單
> 2. 幫我檢查 Heading 跟清單按鈕，能不能讓已套用的 Heading 跟清單樣式取消

本文件先記錄需求與現況，判準在實作前釘死；本文件只准 append。demo batch 3 不動這兩項。

## 1. 需求一：Heading 下拉選單（H1～H4）

工具列的「標題」按下後開下拉式選單，可選 H1 到 H4。

現況（讀原始碼，2026-11-02）：

- 工具列只有一顆 `set-paragraph-heading`，`web/e2-editor.html`。
- manifest 把它標成 `heading-level-1-only`（v31 的 `editorContract.actions`），只有一個層級。
- ABI 是封閉的動作清單，不接受任意 UNO 指令，所以新層級要新增動作、要連結。不是只改頁面。

**排程**：要連結，和 finding 180（清單與標題按鈕的游標跳位，同樣要連結）併同一次。標題按鈕正好是 180 量到的路徑之一，兩件一起改只要重驗一次。

## 2. 需求二：取消已套用的標題與清單

檢查題，先量。結果寫在本節之後的追加。

## 3. 追加 1（2026-11-02，擁有者補充）

擁有者原文：

> 套用跟取消 heading/lists 應該在同一按鈕才對，分開太違反一般使用經驗了
> 有需要可以參考 collabora online source code

所以需求二不只是檢查：標題與清單要改成**同一顆按鈕切換**，按一次套用，再按一次取消。現在的 `標題`／`內文`、`項目符號`／`編號`／`移除清單` 是分開的 setter，這是要改的設計，不是要保留的現況。

## 4. 追加 2（2026-11-02，第 2 項的量測與 Collabora 的作法）

### 現況量測

`findings/evidence/demo-batch-4/cancel-today/`：出貨頁面、真實按鍵，每按一次就存檔，讀 ODT，Chrome 與 Firefox 兩邊相同。

| 操作 | 結果 |
|---|---|
| 標題，再按一次標題 | 維持標題，**取消不了** |
| 項目符號，再按一次 | 維持清單，**取消不了** |
| 編號，再按一次 | 維持清單，**取消不了** |
| 標題，再按內文 | 回到內文 |
| 項目符號或編號，再按移除清單 | 離開清單 |
| 文件原有的標題按內文、原有的清單按移除清單 | 都能取消 |
| 項目符號，再按編號 | 換成編號清單 |
| 標題＋項目符號，再按移除清單、內文 | 兩個都能拿掉 |

所以答案是**能取消，但要按另一顆按鈕**，五顆按鈕在頁面上都看得到。另外這五顆都沒有 `aria-pressed`：工具列看不出游標目前在標題或清單裡。

### 為什麼現在不是切換

- `set-list-*` 刻意帶 `On` 參數變成 setter：finding 030 量到不帶參數時連按三次會反轉，而當時的設計不容許反轉。現在這正是要的行為，但要配上新的後置條件。
- 頁面拿不到游標的清單與標題狀態：引擎的 JSON 有 `listBullet`、`listNumber`、`paragraphStyle`，worker 的 `format` 只投影 B、I、U、刪除線（`sdk/v31-alignment-worker.js:525`）。
- 就算投影出來，finding 021 量過這些快取在 WASM 上不隨游標更新（10 次 2 次新鮮），那是舊引擎，現在的主迴圈還沒重量。

### Collabora 的作法

- 清單：工具列送**不帶參數**的 `.uno:DefaultBullet`、`.uno:DefaultNumbering`（`browser/src/control/Control.TopToolbar.js:209-210`）。切換在 core：`sw/source/uibase/shells/txtnum.cxx` 的 `bMode = !GetShell().SelectionHasBullet()`，讀的是文件本身，不經過任何快取。
- 標題：樣式下拉選單（同檔 `updateCommandValues`），選項是引擎給的 `ParagraphStyles`，前 7 個在上面，用 `.uno:StyleApply` 套用。取消就是選另一個樣式，不是再按一次。

### 設計方向（判準實作前再釘）

- **清單**：新增不帶參數的切換動作，切換讀文件本身，不依賴 worker 投影或快取。後置條件改讀 HTML 的清單標籤，連按要能反轉（finding 030 的相反判準）。
- **標題**：按鈕開下拉選單，選項是內文、H1～H4，標示目前層級；選目前的層級回到內文，和 Calc 對齊按第二次還原同一個語意。
- **工具列**：拿掉獨立的 `內文`、`移除清單`。`tools/run_e2_c_product_path.py` 還在按這兩顆，回歸工具要一起改，這是不能併進 demo batch 3 的另一個原因。
- **一次連結**：和第 1 節的 H1～H4、finding 180 併同一次連結，游標還原也一起換讀法，F3、F4 只重驗一次。
- 按鈕的按下狀態（`aria-pressed`）要有可靠來源才顯示，沒有就不顯示（`updateGestureAffordance` 的既有規則）。

## 5. 追加 3（2026-11-03，實作之前的量測，取代第 4 節的設計方向）

擁有者 2026-11-03：上一輪成果（0.2.51）人工測試通過，離座，授權自主往下執行，難決定的交 fable，可視情況交 Codex。會編譯的 make 仍是擁有者的，這次沒有說「幫我建置」，連結要再問。

### 量到的事實

- **M0，快取現在跟得上游標**（`cache-freshness/run-02`）：真實方向鍵，72 步 × 兩個瀏覽器，`paragraphStyle`、`listBullet`、`listNumber` 144/144 正確，最慢 0.355 秒。finding 021 的「10 次 2 次新鮮」在主迴圈引擎上不再成立。兩條使用規則：`formatStale` 不能當有效位元（值全對時仍有 39/144 步是 true，因為值沒變就沒有廣播）；`listNumber` 在標題上永遠是 true（core 把大綱編號算進去）。新開文件在第一次廣播之前三個欄位都是 null（`preview/run-01`），工具列這時什麼都不宣稱。
- **N3，第 4 節的讀法不成立**（`native-toggle/`）：一個字元的選取**永遠讀不到清單標籤**（`<ul>` 不出現），因為部分段落的剪貼簿拷貝不帶清單屬性。對齊讀得到是因為 `align` 在 `<p>` 上。所以「選一個字元、讀、走回來」救不了清單，finding 180 不能照第 6 節的讀法修。
- **N3 另外抓到批次 3 的量測缺口**：N2 的 `para-start`、`list-start` 兩組位置其實不在段落開頭。`.uno:GoLeft` 從選取的 point 移動（finding 129），所以落在 `BRAV|O`。批次 3 第 6 節寫的「游標所在段落是讀回的最後一塊」，N2 沒有量到真正的段落開頭。真正的段落開頭由產品路徑 P1 的 `caret-plain` 量到（108/108），結論沒翻，只是 N2 那兩組的名字是錯的。
- **N3，兩個 HTML 讀法的盲點**：範圍從段落中間開始時，第一塊不帶段落樣式（`['p', 'h1']`）；段落開頭一小段套段落樣式時，選取變成 complex。
- **第二個盲點的成因讀碼確認**：`SwDocShell::MakeInlineHeading`（`sw/source/uibase/app/docst.cxx:1262`）。選取從段落開頭起、不滿整段、少於 120 字時，core 不改段落樣式，而是建立行內標題框。所有段落樣式都走這條，包含內文。
- **N4，不選取的讀法成立**（`native-caret-read/`）：`XModel::getCurrentSelection()` 走訪涵蓋的段落，讀 `ParaStyleName`、`NumberingStyleName`、`NumberingRules`、`NumberingLevel`、`ParaAdjust`。游標臂 168 格：讀到的 168/168 等於存檔，游標位置 168/168 等於完全不讀的對照（因為什麼都沒選），164/168 達到指令目標，其餘 4 格是下面的「標題加編號」。空白文件 12/12。範圍 84 格、表格 26 格、widen 20 格，沒達到的全部可以歸類，見 `native-caret-read/reading.txt`。讀一次 45–929 µs（原生）。
- **N4 的第一輪是假的**：被我中止的 run 留下 `.~lock`，下一輪以唯讀開檔，84 格指令全部沒生效，而讀回與檔案完全一致。`run.sh` 改成每輪複製夾具。〔再踩一次「綠的東西什麼都沒量到」〕
- **出貨版的兩個缺陷**（`before-v31/run-01`，Chrome 與 Firefox 相同，真實按鍵，finding 181、182）：段落開頭選三個字按標題，存檔出現 1 個框、`BRA` 變成獨立的標題；從段落中間跨到下一段按標題，樣式其實套上了，頁面卻報 `EDITOR_FORMAT_POSTCONDITION_FAILED`，session 進 `recoverable-error`，存不了檔，提示「沒有檢查點，所以自上次儲存以來的內容不會回來」。

### 設計定案（取代第 4 節「設計方向」的讀法與清單部分）

1. **一個讀法**：v32 所有段落動作（既有五個、四個對齊、六個新動作）三條路線都用 `probe::writerSelectionParagraphs`，新單元 `src/writer_caret_bridge.cpp`，沿 `calc_cell_bridge.cpp` 的作法。派送前讀一次、派送後讀一次，不選取、不移動、不還原、沒有座標。
2. **判定**：段落數與每段文字不變（`crossIdentityHeld`），每段都達到目標（`crossStateHeld`）。不符就是既有的 shape 與錯誤碼。派送後讀不到是新 shape `paragraph-read-failed`，處置 `review`，有自己的句子。
3. **六個新動作**，wire id 28–33，internal 30–35，ABI 維持 6：`toggle-heading-1`…`-4`、`toggle-list-unordered`、`toggle-list-ordered`。方向由引擎依派送前讀到的文件決定：涵蓋的段落**全部**已是目標才取消，混合時套上。確定方向之後用的是既有 setter 的指令與參數（`On=true`、`.uno:RemoveBullets`、`.uno:StyleApply`），所以 finding 030 的量測照舊適用；這和第 4 節的「不帶參數」不同，理由：不帶參數時方向在 core、我方的後置條件要接受兩個方向，而且 `SelectionHasNumber` 把大綱編號算進去，標題上會走到不想要的分支。
4. **內文**：選單裡的「內文」是既有的 `set-paragraph-body`。選目前的層級等於回內文，由 `toggle-heading-N` 負責。
5. **段落樣式在範圍上擴成整段**：單段範圍先 `.uno:SelectText` 再套樣式，選取留在整段。避開 `MakeInlineHeading`，N4 widen 的 10 格 widened 臂全部乾淨。按鈕的語意是「這一段」。
6. **標題加編號**：`.uno:DefaultNumbering` 在標題上是 no-op，標題帶項目符號段落時甚至會拿掉符號（N4 range）。`toggle-list-ordered` 在這種選取下派送前拒絕，新錯誤碼 `EDITOR_FORMAT_NUMBERING_ON_HEADING`，句子「標題段落不能加編號。請先把它改回內文，文件沒有變動」。
7. **選取裡有表格**：派送前拒絕，`EDITOR_FORMAT_SELECTION_NOT_READABLE`，改用中文句子。先前是派送後才 `unknown-structural-tag`、處置 rollback。
8. **頁面**：標題鈕開選單（內文、標題 1–4），項目符號與編號兩顆切換鈕。沒有這六個動作的 profile 繼續顯示舊的五顆。舊五顆留在 DOM、`hidden`：`tools/run_e2_c_product_path.py` 用 `.click()` 找它們，所以不用改被綁的 runner，F3 仍然量到引擎的讀法。第 4 節「回歸工具要一起改」因此取消。
9. **工具列狀態**：`paragraphFormatShown()`，範圍上不顯示，標題上編號鈕不顯示。按鈕的方向不讀這個值。worker 的 reply 投影補上這三個欄位，否則每次動作回覆都會把狀態清掉。

**被取消的舊處置**：`L-align-blank-document`、finding 083／173／176 在空白文件上那句提示。裁決 3 的前提是「那裡讀不到任何內容，只有 undo」，現在讀得到，所以不是推翻裁決，是前提消失。

### 判準（連結之前釘死，第 6 節起只准 append）

靜態，連結前：

- **E1**（`pre-link/syntax.json`）：五個單元 `-fsyntax-only` 乾淨，四個正向對照都紅得出來。
- **E2**（`tests/test_paragraph_read_v32.py`）：`everyParagraphMeets`、`toggleTakesOff`、`numberingHasNoEffect` 用 N4 記錄的列判，母數由工具從 observations 生成。
- **W1**（`tests/v32_paragraph_worker_test.cjs`）：v31 worker ＋封閉差異逐位元等於 v32 worker；六個 id、旗標拒絕、manifest 沒有就拒絕、投影保留三個欄位，四個因果對照都紅。
- **SAME**（`pre-link/preprocess-same.json`）：v31、v29、ods-editor-v3 的前置處理輸出逐位元不變，v32 的正向對照要不同。
- **M1-1**：`check_merge_key_undo_scope` 帶 E2_V32 綠、拿掉紅。
- **U**：殼層單元測試全過。

連結之後，瀏覽器：

- **P4**（`tools/check_writer_toggle.py`，真實按鍵與指標，Chrome、Firefox，判讀存出的 ODT）：
  - T1 兩個清單連按三次是開、關、開（finding 030 的相反判準）。
  - T2 H1–H4 各自開與回內文、層級互換、內文項目。
  - T3 文件原有的標題與清單取消得掉，項目符號換編號。
  - T4 finding 180：五種按法 × 段落開頭、中間、清單、標題、換行段落、中段空段落、最後空段落，打 `q` 落在原處。
  - T5 一段空白文件：清單與 H2 開關、不跳提示、「上次操作」不寫失敗、打字落點對。
  - T6 finding 181、182：段落開頭選取不產生框、從段落中間跨段的範圍兩段都套上、再按取消、混合選取是套上。
  - T7 兩種拒絕：句子、文件不變、session ready。
  - T8 一次 Ctrl+Z 回到按之前。
  - T9 工具列狀態對得上游標。
  - T10 選單開關、鍵盤、不搶走 sink。
  - T11 重新開檔還在。
  - 紅案：`swap-levels`、`no-undo`、`no-second-press` 都要紅。
- **P1′**（`tools/check_writer_align.py`）：108 格維持全過，`P1c/control` 換成 `P1c/list-button-keeps-the-caret`（要過）。

回歸（第 87 代）：S1、Z、C、F4、F3、V0′，單元、Calc 單元與突變工具（`chain-skips-unit-and-mutation-tools`）。

**預先宣告會移動的東西**：F3 有 3 格本來就紅（`bulleting-a-blank-line-does-not-demand-a-rollback` 等）。空白文件的提示消失，依裁決 3 的前提消失處理；若有格子因此移動，要逐格解釋，不是放寬。

宿主（0.2.52）：Files 工作流、`HOST_BATCH_HOLDS`、`LAYOUT_HOLDS`、T6（Nextcloud 淺色與深色）延伸到選單；`host_batch4` 走真實按鍵存回 WebDAV 讀回，比照 `host_batch3`。

### 具名限制

- `L-number-on-heading`：標題段落不能加編號（決定 6）。
- `L-table-in-selection`：跨表格的選取不能套段落動作（決定 7）。表格內的游標與單一儲存格內的選取可以。
- `L-state-before-first-broadcast`：新開文件在第一次狀態廣播之前，工具列不顯示段落狀態。
- `L-list-style-levels`：標題帶項目符號段落、而該清單樣式只定義第一層時，標題會落在未定義的層級，讀成編號，後置條件失敗。N4 的夾具才會這樣，內建樣式每層都有定義。

### 如果永遠沒做

擁有者沒連結：頁面顯示舊的五顆，產品行為等於 v31，本批程式碼留在樹上不影響任何出貨。finding 180、181、182 維持已確認未修，要在交接列為已知缺陷。

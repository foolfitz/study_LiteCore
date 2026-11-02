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

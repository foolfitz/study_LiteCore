# 185 — 有批註的 Writer 文件：LOK 回報的文件寬度會隨 paintTile 的比例變動

| | |
|---|---|
| **狀態** | 成因讀到函式層級，公式模型重現實測數列；上游未修、未送；頁面端已繞過（`e2-editor-app.js` 的容許誤差），隨宿主 0.2.57（殼層第 90 代）上線（2026-11-04 16:04） |
| **Bugzilla** | 未查重複單（上游送出擱置中，重啟時先查） |
| **發現日** | 2026-11-04（擁有者手測宿主 0.2.56 第 1 條：放大到 100% 整個編輯區變白） |
| **嚴重度** | 對我們：高（繞過之前，有批註的文件在 100–150% 全白，某些視窗寬度連「符合視窗」都白）；對上游：低（只影響每次 paint 後重讀 `getDocumentSize` 來決定畫布大小的 LOK 用戶端） |
| **可重現** | WASM 引擎 v33（0.2.56）與 v29（0.2.47 封存），Chrome、Firefox；原生 LOK **未量** |
| **是否上游** | 推定是：程式碼在 core 的 `sw/`，我們沒有改那裡；原生未量，所以標推定 |

## 現象

`wasm_sdk_probe/test-docs/r7-compat/l1-layout-table-image.odt` 有一則批註（`office:annotation`）。每次 `paintTile` 之後讀 `getDocumentSize`，寬度會跟著這次畫的畫布寬度變：在 100% 依序是 16960、17003、17002、16961……（〔實測〕，`evidence/host-0.2.56/handtest-2026-11-04/README.md`）。沒有批註的 `t3-long.odt` 寬度不動。

我們的頁面在固定比例下用回報的寬度算畫布寬度，於是畫布寬度變 1–3 px、下一次又回報另一個寬度，永不收斂，畫面一直是白的。

## 成因（〔讀原始碼〕，fable 2026-11-04，主 session 核對）

- 有批註時，頁寬包含批註欄：`SwRootFrame::CheckViewLayout` 用 `SwPageFrame::GetSidebarBorderWidth`（`sw/source/core/layout/pagechg.cxx:2402`、`:2422`）。
- `SwPostItMgr::GetSidebarWidth`（`sw/source/uibase/docvw/PostItMgr.cxx:2453-2474`）：在 LOK 下、輸出裝置是 tile 時，`nZoom = fScaleX * 100` 存進 `sal_uInt16`（**截斷**），乘上 `DisplayWidthFactor`（3）得到像素，再經 tile 的 MapMode 轉回 twips。
- 所以批註欄的 twips 寬度是 tile 比例的函數；`SwViewShell::PaintTile` 每次設定比例後 `EndAction` 會跑 `CheckViewLayout`，文件寬度跟著變。
- 模型：`evidence/zoom-comment-loop/sidebar_width_model.py`（fable 寫，30 行），輸出在同目錄 `.stdout.txt`：100%、125%、150% 無不動點，75%（1400 寬視窗的符合視窗）與 200% 收斂，數列與實測相同；也預測符合視窗下視窗寬每約 11 px 有一段 3 px 會循環（fable 實測 780×600 白、784×600 正常）。

## 上游該怎麼修（〔假說〕，未試）

`GetSidebarWidth` 在 LOK 下不要經過「整數百分比 → 像素 → twips」的來回；批註欄的 twips 寬度應該與畫的比例無關，或文件大小不要因為 paint 而改變。

## 我們這邊

頁面不再讓畫布寬度跟著每一次回報走：只有高度有變、或寬度變超過 8 個畫布像素才重排（`RESIZE_TOLERANCE_PX`、`sizeReportMovesLayout`）。紅案：`check_writer_zoom.py --document test-docs/r7-compat/l1-layout-table-image.odt`（`evidence/zoom-comment-loop/`），以及 `page-render-bands.test.mjs` 的「0.2.56 hand test, item 1」。

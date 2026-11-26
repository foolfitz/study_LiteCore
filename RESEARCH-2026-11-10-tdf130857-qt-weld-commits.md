# tdf#130857：內容與 commit 狀態簡述

> 2026-11-10 讀取。來源：Bugzilla 頁面（以 Playwright 讀 DOM，頁面最後修改 2026-11-07）、本機 `~/LibreOffice/lo-submit` 的 `origin/master`（最後更新 2026-10-11，`016fd5d04925`）。
> 證據標記：**已觀察**＝頁面或 git 可直接確認；**推論**＝未直接驗證。

## 這張單是什麼

- 標題：qt5/qt6: implement theming using native Qt widgets (weld)
- 2020-02-22 由 Jan-Marek Glogowski 開單；Status `NEW`、Importance `medium enhancement`、Assignee 未指定；Blocks：KDE、KF5 Qt6。**已觀察**
- 目標：讓 qt5／qt6 VCL plugin 透過 weld 介面用**原生 Qt 元件**建對話框（gtk3 已經這樣做），取代原本只靠 QStyle 模仿外觀的作法。**已觀察**（開單描述）
- 性質是整個功能的**總追蹤單**，不是單一缺陷，所以至今仍是 `NEW`。

## 為什麼 commit 那麼多

1,440 則留言中，1,428 則是 Bugzilla 的 commit 自動通知：commit message 裡寫了 `tdf#130857`，就自動貼一則。真人留言只有 12 則。**已觀察**

| 項目 | 數字 |
| --- | --- |
| 作者 | Michael Weghorn 1,423；OmkarAcharekar 5 |
| 年份 | 2024：326；2025：550；2026（至 10-28）：552 |
| 分支 | `master` 1,416；cherry-pick 到發行分支 12 |
| 工作日 | 236 天；單日最多 30 個（2025-10-20） |
| Revert | 1 |

前四年沒有 commit，2024-01 才開始。工作只能一點一點推進，作者也習慣一個 commit 只做一件事。依 commit 標題分類（約略值）：**已觀察**

| 類型 | 約略數量 |
| --- | ---: |
| 開放單一對話框改走原生 Qt（`qt weld: Support "…" dialog`） | ~415 |
| 補 Qt 端 weld API 方法（`Implement QtInstanceTreeView::…` 等） | ~186 |
| 修 `.ui` 檔、讓元件照順序定義（`Define widgets in order`） | ~115 |
| weld 抽象層重構（signal blocking、SpinButton 等） | ~96 |
| 各模組配合修改（cui／sw／sc／svx／uui…） | ~89 |
| VclBuilder 重構、抽出共用基底給 QtBuilder 用 | ~46 |
| 其他 qt weld 修正與重構 | ~379 |

標準流程：先補齊某個對話框需要的 API，再修它的 `.ui` 檔，最後用一個 commit 把它加進支援清單。LibreOffice 有上千個 `.ui` 檔，數量就堆起來了。**推論**（從標題歸納，未讀 diff）

## commit 狀態

**都已合併。** 通知全部寫著 `pushed to "master"`（或發行分支），Gerrit 上未合併的 patch 不會觸發這種通知。**已觀察**

本機比對：單上 1,416 個 `master` commit 中，1,415 個是本機 `origin/master` 的祖先。唯一對不上的 `bb9ca9ffdb58`（2026-10-28）晚於本機最後更新日，屬於本機沒同步到。**已觀察**

依通知的 `available in` 欄位，各版本收到的 commit 數：**已觀察**

| 版本 | 24.8 | 25.2 | 25.8 | 26.2 | 26.8 | 27.2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| commit 數 | 15 | 241 | 306 | 278 | 357 | 231 |

## 合併了，但使用者不一定用得到

1. **預設是關的。** `a2f5b750471c`（2024-11-05，`qt weld: Make opt-in for now`）之後，除了簡單訊息框，要設環境變數 `SAL_VCL_QT_USE_WELDED_WIDGETS` 才會啟用。commit 說明的理由：已支援的只是所有對話框的一小部分，而且 QtBuilder 還沒處理所有屬性（間距、邊界、文字格式等）。**已觀察**
2. **現在是否還是預設關閉，沒有查證。** commit 標題裡沒看到改回預設開啟的 commit，但沒有讀原始碼確認。**推論**
3. **27.2 的 231 個 commit 還沒進正式版。** 照半年一版的節奏，應該是 2027 年 2 月左右發行，在那之前只有 daily build 有。**推論**
4. **不在上述數字裡的進行中工作。** macOS Qt6 支援在 Gerrit change 207229，以及分支 `private/dcbw/qt6-mac`（留言 #1304–#1307）。**已觀察**

## 待查（若需要）

- `git fetch` 更新 `lo-submit` 後，查 `vcl/qt5/` 讀取 `SAL_VCL_QT_USE_WELDED_WIDGETS` 的地方，確認目前的預設值。

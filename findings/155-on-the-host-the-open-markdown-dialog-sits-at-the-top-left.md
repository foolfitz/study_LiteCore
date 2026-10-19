# 155：宿主上，打開的「貼上為 Markdown」對話框貼在視窗左上角，不是置中

| | |
|---|---|
| **狀態** | **已量測**（H-154o，兩個瀏覽器各 3 輪），**登錄、不擋出貨**；修法排在下一個宿主版本 |
| **影響版本** | **宿主 0.2.27**：頁面 `3b96cb16…`、`e2-editor.html` `b9c2b975…`、engine 封包 `817413d5ad5bd502`。無宿主的 mirror 沒有這個問題，因為那裡沒有 Nextcloud 的 CSS |
| **所在** | Nextcloud 34 的 `core/css/server.css` 把 `dialog` 放在 reset 清單裡（`margin: 0` 等）。這是作者樣式，蓋過瀏覽器內建 `dialog:modal` 的 `margin: auto`。modal 對話框是 `position: fixed; inset: 0`，少了 `margin: auto` 就貼到左上角 |
| **發現日** | 2026-10-20：H-154o 宿主臂（`findings/evidence/host-0.2.27/h154/`）。這個結果在 2026-10-19 就由讀原始碼預先寫下（SPEC-M3-link-batch-v22 §11.5，fable 裁決 5 第 19 項） |
| **嚴重度** | **外觀**。對話框完整落在視窗內，焦點在文字框，「插入」「取消」兩顆按鈕都點得到（H-154o 的判準全過）。但它不在預期的視窗中央，而是蓋住工具列左半與文件左上 |
| **是否上游** | 否。是我們的頁面依賴了瀏覽器內建樣式，而宿主環境的 reset 蓋過它（與 154 同類） |

## 量測（宿主 0.2.27，headless；入口按鈕真的點擊之後讀）

| 瀏覽器 | 框 `[x, y, w, h]` | `margin` | 視窗 | 焦點 |
|---|---|---|---|---|
| Chrome（3 輪皆同） | `[0, 0, 640, 335]` | `0px` | 1850×980 | `#markdown-text` |
| Firefox（3 輪皆同） | `[0, 0, 640, 342]` | `0px` | 1850×994 | `#markdown-text` |

報告：`h154-chrome-20261020T032507.json`、`h154-firefox-20261020T032550.json`。判讀：`judge-host-arms.txt`（H-154c PASS、H-154o PASS）。

## 修法（裁決 5 第 19 項已預先寫好，不盲修）

- 下一個宿主版本，在 `templates/editor.php` 加一條 `#litecore-editor-root dialog[open] { margin: auto; }`，形狀同 0.2.26 的 `dialog:not([open])` 那一條。
- 只動宿主：engine 封包不動、殼層不重新凍結、第 2 項不重跑。
- 判準就是 H-154o 這一臂的框讀數：框中心要在視窗中心附近，其餘條款照舊。

## 發佈說明

0.2.27 的發佈說明照實寫：「在 Nextcloud 裡，貼上為 Markdown 的視窗會出現在畫面左上角，可以正常輸入與按插入／取消；下一版會改成置中。」

# 161：宿主 0.2.29 的頁面表檢查拿頁面的 `./` 形式去比 manifest 的 module 鍵，拒絕了自己的 package——每條 `r/` 路由都回 500

| | |
|---|---|
| **狀態** | **宿主 0.2.30 已修**（`e6e325a`，2026-10-21 00:13 由擁有者裝上）。H1–H6 在 0.2.30 上的重跑見 `findings/evidence/host-0.2.29/README.md` |
| **影響版本** | **宿主 0.2.29**（`9a349f6`）配 package `1b4d6a1fc905fb8a`（schema `litecore-engine/3`）。0.2.28 以前沒有頁面表，沒有這條檢查 |
| **所在** | `lib/Controller/EditorController.php` `engine()`：`($entry['module'] ?? null) !== $page['module']`，其中 `$page['module']` 是 `./e2-editor-app.js`（頁面 `<script src>` 的寫法），而打包工具寫進 `source.pages[*].module` 的是 `e2-editor-app.js`（`files` 的鍵）。同一行的下半句已經用 `substr($page['module'], 2)` 去掉 `./` 查 `files`——兩種形式作者都知道，比對那一處漏了 |
| **發現日** | 2026-10-20 23:46：Phase H 第一次跑，H6 在線上讀到檢視頁 500、編輯器頁 500，body 是宿主自己的訊息「the engine is not packaged for this host (engine/MANIFEST.json: litecore-engine/3 with both pages)」（`findings/evidence/m4-ods/phase-h/shakedown/2026-10-20T154120+0000.json`） |
| **嚴重度** | **功能**。不只檢視頁：編輯器路由同樣 500，ddev 上的 ODT 編輯器從 23:39（裝 0.2.29）到 00:13（裝 0.2.30）不能用 |
| **是否上游** | 否。我們自己的宿主 |

## 量測

- 容器內的 PHP 解析 manifest 正常：`is_array` true、schema `litecore-engine/3`、buildId `1b4d6a1fc905fb8a`、兩個頁面、35 個檔（`ddev exec php -r`）。所以不是檔案、權限或 symlink（`apps-extra/litecore/engine -> /var/www/html/engine`）。
- 把 `engine()` 的迴圈對活的 manifest 重放（`php -r`，主機上）：**0.2.29 的比對 → null → 500；0.2.30 的比對 → 回 manifest。**一紅一綠，同一份輸入。
- Nextcloud 的 log 沒有這筆：500 是控制器自己回的 `DataDisplayResponse`，不是例外。

## 為什麼離線閘門沒抓到

- H5-1（`check_m3_assets.py`）用**打包工具自己的頁面表**（`probe_m3_assets.PAGES`）判打包工具自己寫出的 manifest——它們永遠一致。控制器的 `PAGES` 是**第二份手寫的頁面表**（CLAUDE.md 驗收判準 §1 的形式三：成員住在別處的鏡像），在 Phase H 之前從來沒有對任何 package 跑過。
- 0.2.29 的 `php -l` 乾淨、單元測試全綠、22 個 package 紅案全紅——它們沒有一個經過控制器的 `engine()`。
- 所以裁決說「第一個紅就是量測」是對的：能抓到這件事的檢查只有宿主上的 H6／H2。

## 修法

- 宿主 0.2.30（`e6e325a`）：`$module = substr($page['module'], 2);` 比對與查 `files` 都用它。只改控制器一行與版本號；package 不動（buildId 不變）。
- 判準：H6（兩份文件 200、COOP／COEP／CSP 相同）與 H2（點 .ods 落在檢視路由）在 0.2.30 上過；H4 證明編輯器那一半回來了。
- 沒有為「兩份頁面表要一致」造新機制（CLAUDE.md §4）：宿主上的 H6 本來就是守它的檢查；登錄在 SPEC-M4 A10。

# SPEC M3：資產派送

2026-09-29 立。擁有者在 `handoff/HANDOFF-2026-09-28i-versions-correct.md` 之後指定這一項（交接裡的 C，路線圖 §5.3）。

## 1. 為什麼要有

`litecore` app 到目前為止只能在這一台 ddev 上跑：它讀的引擎檔案是 study_LiteCore 的 `wasm_sdk_probe/dist`（11 GB，
唯讀 bind mount 進容器，app 裡一個 `dist` 符號連結指過去）。路線圖 §5.3 原本把問題寫成「169 MB 靜態資產，必須 web server
直出、immutable 快取、不穿過 PHP」，以及「一部分副檔名在 Apache 白名單外是 404」。第 0 步量下來，**真正的問題不在那裡**
（第 2 節）：現在每開一次檔，兩個瀏覽器都要從伺服器重抓整整 169.6 MB，而「web server 直出」恰好是讓最大那個檔進不了
瀏覽器快取的那一種送法。

## 2. 第 0 步量到的事實（已觀察）

`findings/evidence/m3-assets/README.md`。宿主 `49cc4ab`、頁面 `fbfb59a4…`、profile `e2-editor-v8`，兩個瀏覽器。

- **閉包可以從原始碼推導，而且跟伺服器紀錄一致**：頁面 `e2-editor-app.js` 的靜態 import 圖（13 個檔，沒有動態 `import()`）、
  頁面寫死的那一個 `workerUrl`、那個 worker 的 `sdk-manifest.json` 裡的 `artifactFiles` 與 `loadAtStartup: true` 的資源包，
  加上宿主要重新包裝的 `e2-editor.html`——22 個檔、169,617,155 位元組。宣告了但從不載入的 `fallback-fonts-r5`（49 MB，
  finding 085）不在裡面。有宿主時頁面不抓 `e1-fixtures/`。
- 現在的送法：wasm 由 PHP 303 到 app 目錄的靜態檔，Apache 原樣送 115 MB（即使請求接受 gzip），`max-age` 六個月；其餘全部由
  PHP 整檔讀進記憶體再送，`no-cache`、**沒有 ETag 也沒有 Last-Modified**；`.js` 在路上被 Apache 壓縮，`.data`／`.json` 沒有。
- **快取開著，第二次開檔兩個瀏覽器都重新下載全部 169.6 MB**，包括那個 `max-age` 六個月的 wasm。之前所有 M3 的計數執行都是
  關掉快取跑的，所以沒有一次看得到這件事。本機迴路上這只是 2.5–3.2 秒；50 Mbit/s 下約 27 秒（推算，未量）。
- **為什麼 wasm 也重抓**（X1，實驗檔、兩個瀏覽器、正向對照都快取了）：Firefox 不保留編碼後大於 45–60 MB 之間某個上限的回應；
  Chrome 的上限跟著 profile 所在磁碟的剩餘空間走（14 GB 可用時 100 MB 保留、115 MB 不保留；88 GB 可用時都保留）。
  **同一個 wasm 以 gzip（41.0 MB）或 zstd（30.7 MB）的 `Content-Encoding` 送，兩個瀏覽器在每一種組態下都保留了**，
  Firefox 的上限看的是編碼後的大小。
- 壓縮：閉包 169.6 MB 原樣、約 64 MB gzip -9、約 49 MB zstd -19。wasm 115.3 → 41.0（gzip）→ 30.7（zstd）。

## 3. 宿主的改變

產品頁（`fbfb59a4…`）、殼層（v53）、引擎、profile 都不動。只動 `litecore` 宿主，加一支打包工具。

### 3.1 打包：app 自己帶著引擎

- 工具 `wasm_sdk_probe/tools/package_m3_engine.py` 從 `dist/` 依第 2 節的規則推出閉包（與 `probe_m3_assets.closure()` 同一個
  函式，不另寫一份清單），把每個檔以 gzip -9（`mtime=0`，同樣的輸入產生同樣的位元組）寫到 app 的
  `engine/files/<路徑>.gz`，並寫 `engine/MANIFEST.json`：每個路徑的原始位元組數與 sha256、gz 位元組數與 sha256，以及來源
  （頁面、profile、wasm 的 sha256、工具自己的 sha256）。
- **buildId**＝ `{路徑: 原始 sha256}` 正規化 JSON 的 sha256 前 16 個 hex。它是**解碼後內容**的函數，跟 gzip 的位元組無關。
- `engine/` 不進 app 的 git（`.gitignore`），由工具產生、隨發佈的壓縮檔出貨。app 裡的 `dist` 符號連結刪掉。ddev 的
  bind mount 設定一併刪掉；**容器要到下一次 `ddev restart` 才真的少掉那個掛載**，這一步不重啟（見 §4 K1-3e 怎麼確認沒人用它）。

### 3.2 送出：一條 PHP 路由、預壓縮、網址帶身分

- 所有引擎檔案都走 `/index.php/apps/litecore/r/<buildId>/<路徑>`。只送 MANIFEST 裡有的路徑，其餘一律 404；buildId 不是目前
  安裝的那一個也 404。
- 請求接受 gzip：直接串流 `.gz`（`StreamResponse`，不整檔讀進記憶體），`Content-Encoding: gzip`、`Content-Length`＝gz 大小。
  不接受：用 zlib 邊解邊送。兩種都帶 `Vary: Accept-Encoding`。
- 資產一律 `Cache-Control: private, max-age=31536000, immutable`（`Response::cacheFor`）。**編輯器文件本身除外**：它嵌了這個
  使用者、這個檔案的 initial state（檔案 id、ETag），維持不快取。
- 腳本照舊帶 COEP `require-corp` 與 worker 用的 CSP；`Content-Type` 依副檔名，`.wasm` 是 `application/wasm`（串流編譯需要）。
- Files 的連結不改（`/apps/litecore/r/e2-editor.html?fileId=N`），那個網址改成 303 到
  `/index.php/apps/litecore/r/<buildId>/e2-editor.html?fileId=N`。頁面裡所有相對網址（模組、`workerUrl`、worker 抓的檔）
  因此都落在同一個 buildId 底下。
- 為什麼網址前面要帶 `/index.php`：Apache 上，`.js`／`.wasm`／`.html` 這些白名單副檔名的 pretty URL 今天是經由
  「找不到檔 → `ErrorDocument 404` → `index.php`」才到得了 PHP（伺服器紀錄與 `.htaccess:207`、`:199`，讀原始碼推得）；nginx 上靠
  `try_files` 的退路。帶 `index.php` 之後兩種伺服器都直接進前端控制器，不依賴任何一條退路。

### 3.3 撤回路線圖 §5.3 的兩個前提

「必須 web server 直出」與「不穿過 PHP」撤回（驗收判準的形式第 4 節：前提被證偽就刪掉，不造機械維持它）：

- 直出的原樣 wasm 正是進不了快取的那一種（第 2 節）。要讓它以編碼後的大小進快取，伺服器得替一個靜態檔加上
  `Content-Encoding`——app 沒有辦法不經伺服器設定做到這件事（Apache 要 `.htaccess`，只有 Apache；nginx 沒有對應物）。
  PHP 可以，而且在兩種伺服器上是同一條路。
- 代價寫清楚：第一次開檔，每個大檔在傳輸期間佔住一個 PHP-FPM worker，合計約 64 MB。之後在瀏覽器快取有效期間（一年，
  或直到 buildId 改變）同一個瀏覽器不再抓。Nextcloud 自己的每一次檔案下載（WebDAV）本來就經過 PHP，這是同一種成本，
  **慢速用戶端佔住 worker 多久沒有量**。

「immutable 快取」保留，而且這一步才讓它成立。

### 3.4 為什麼是 gzip，不是 zstd／brotli

zstd 比 gzip 再省約 15 MB（wasm −25%），但 PHP 沒有內建 zstd／brotli 的解碼器，遇到不接受它的用戶端就沒有退路；gzip 用
zlib，PHP 內建。gzip 的 41.0 MB 在 Firefox 實測保留的範圍內（45 MB 保留）。zstd／brotli 列為之後的選項（第 6 節）。

## 4. 驗收判準（先於 runner 與任何計數執行寫下）

環境同版本（ddev、NC 34.0.2 tarball、Apache、admin）。評分由 `wasm_sdk_probe/tools/check_m3_assets.py` 做，**只讀報告裡的
原始欄位**。靜態條件照前幾步：`dist/` 與 `web/` 的 `e2-editor-app.js` 都仍是 `fbfb59a4…`；`make test-e2-c-static` exit 0；
**宿主 repo 沒有未 commit 的改動**（runner 拒絕否則）。

### K0 打包（離線）

1. MANIFEST 的路徑集合＝ runner 當場從 `dist/` 重新推出的閉包，不多不少。
2. 每個路徑：`engine/files/<路徑>.gz` 解壓後的 sha256＝`dist/<路徑>` 的 sha256＝MANIFEST 記的 sha256；`.gz` 本身的 sha256＝
   MANIFEST 記的 gz sha256。
3. buildId＝依 §3.1 從 MANIFEST 重算的值。
4. app 的工作樹裡沒有 `dist` 這一項（`git ls-files` 與目錄列表都沒有）。

### K1 線路（不開瀏覽器，runner 以 admin 登入）

1. MANIFEST 裡每個路徑（編輯器文件除外）以 `Accept-Encoding: gzip` 取：200；`Content-Encoding: gzip`；**回應本文的 sha256＝
   MANIFEST 的 gz sha256**（送的就是打包的位元組），解壓後＝原始 sha256；`Cache-Control` 含 `immutable` 且 `max-age`
   ≥ 31536000；`Vary` 含 `Accept-Encoding`；`Content-Type` 依副檔名表（`.wasm`＝`application/wasm`）；`.js` 帶
   `Cross-Origin-Embedder-Policy: require-corp`。
2. 同一批以 `Accept-Encoding: identity` 取：200；沒有 `Content-Encoding`；本文 sha256＝原始 sha256。
3. 以下全部 404（不得是 200，也不得是 3xx）：(a) 宣告但不載入的資源包；(b) 另一個 profile 的 wasm
   （`profiles/e2-editor-v14/probe.wasm`）；(c) `../appinfo/info.xml` 與它的百分比編碼形；(d) 正確路徑配錯的 buildId；
   (e) 舊的靜態網址 `/apps-extra/litecore/dist/profiles/e2-editor-v8/probe.wasm`。
4. `/apps/litecore/r/e2-editor.html?fileId=N` 是 303，`Location` 以 `/index.php/apps/litecore/r/<buildId>/e2-editor.html?fileId=N` 結尾。
5. 編輯器文件（帶測試檔的 fileId）：200、COOP `same-origin`、COEP `require-corp`，`Cache-Control` **不含** `immutable` 也
   不含正的 `max-age`。

### K2 瀏覽器（每次一個新的、**快取開著**的 profile）

每次：上傳測試檔 → 從 Files 開 → 等宿主 `done` → 放游標、做一個段落動作（同宿主入口 H1 的煙霧步驟）→ 回 Files → 再開一次
→ 同樣的煙霧步驟 → 回 Files。紀錄是 web 容器的 Apache access log 在每次開檔前後兩個位移之間、該瀏覽器 User-Agent 的列。

1. **第一次開檔**：`/r/<buildId>/` 底下被請求的路徑集合＝MANIFEST 的路徑集合（編輯器文件包括在內），每一列 200；app 路徑
   （含 `/apps-extra/litecore/`）底下沒有任何 4xx／5xx；`/r/` 底下除了那個 303 與上述路徑之外沒有別的。
2. **第一次開檔送出的是壓縮後的位元組**：每一個資產請求的 `%O` ＜ 該檔 gz 位元組數＋4096。
3. **第二次開檔沒有資產請求到伺服器**：`/r/<buildId>/` 底下只有編輯器文件（1 列）；303 那一列可以有。
4. 兩次開檔宿主都到 `done`、都沒有 `stranded`；兩次的煙霧步驟都成功（游標放下、動作使 revision 前進）。

次數：Chrome 3、Firefox 3。報告記下每個 profile 所在磁碟的剩餘空間（Chrome 的上限跟著它走）。

### K3 M3 的既有流程在新宿主上重跑

宿主入口、鎖與權限、版本三支 runner 以各自原本的判準對新的宿主 commit 各跑一次計數執行，判定與原本相同，紅案全紅。
runner 唯一的改動：`check_m3_skeleton_open.ROUTE` 從完整路徑改成後綴 `/e2-editor.html`（文件網址現在帶 buildId；三支 runner
都經由它判「落在編輯路由」），改動與理由寫進各 runner 的 commit。

### K4 發佈壓縮檔（量測，登錄，不是過／不過）

以 app 發佈會有的內容（`appinfo/ lib/ templates/ js/ engine/`，不含 `src/ node_modules/ .ddev/ nextcloud/`）打 `tar.gz`，
記大小。

### 紅案與計數

K0–K2 每一條至少一個突變，每個突變都要找得到它的那一條（找不到算失敗）；**先讓評分紅一次再跑計數**。計數執行照
`findings/evidence/m3-locks/README.md` 的「Counted run: rules fixed before it started」四條。K0–K2 兩個瀏覽器各 3/3 全過
＝**`ASSETS DELIVERED`**；K3 另外判，三支都照舊才算「新宿主上 M3 的流程沒有退步」。

**如果這件事永遠沒做**：app 仍然只能在這一台 ddev 上跑；每開一次檔傳 169.6 MB 的現況照舊，「immutable 快取」只是路線圖上
的一句話。K3 沒做：新宿主上開檔、存檔、鎖、版本都沒有被重新證明，**不得**說 M3 的三個計數執行仍然成立。

## 5. 明確不承諾

- **從發佈壓縮檔裝進另一台 Nextcloud** 沒有做。這一步證明的是「app 只讀它自己帶的檔」（K0-4、K1-3e、K1-1 的 gz 位元組
  只存在於 `engine/`），不是「換一台照樣裝得起來」。後者要建立或改動另一個 ddev 專案，交擁有者決定（第 6 節 B）。
- nginx、Safari 沒量。§3.2 的網址形狀是為了不依賴伺服器的退路而選的，那是設計理由，不是量測。
- 慢速用戶端下 PHP-FPM worker 被佔住多久沒量；Chrome 在剩餘空間更小的磁碟上上限落在哪裡沒量（41 MB 的 gz 在 14 GB 可用時
  有很大的餘裕，但更小的磁碟沒試）。
- 瀏覽器快取可以被清掉、被逐出；「第二次不抓」是在同一個 profile、緊接著的一次開檔上量的，不是對任意時間之後的保證。
- 資源包 `fallback-fonts-r5` 不出貨。規則是 `loadAtStartup: true` 才進閉包；哪天 SDK 有了按需載入（finding 085 說現在沒有），
  那個包會 404——規則寫在工具裡、從 manifest 推，manifest 改成 `true` 它就會自動進來，但**按需**載入的包不會。
- 未登入的使用者拿不到資產（路由照舊要求登入）。這是現況，不是這一步的判準。

## 6. 擁有者要決定的（不擋這一步）

- **A. 發佈管道**：App Store（原始碼預設上限 30 MiB，但正式站發佈過 269 MB 的 `richdocumentscode`；K4 量出來的大小要不要
  拿去問或直接試）、或安裝時從別處下載引擎（另一套機制，要寫）。
- **B. 在另一台乾淨的 Nextcloud 上從壓縮檔安裝**（例如 `litecoreprobe`，或新建一個 ddev 專案——新建會重建共用 router，
  你其他的 ddev 專案會短暫 404）。
- **C. zstd／brotli**：第一次開檔再省約 15 MB，代價是不接受它的用戶端要另外準備一份 gzip（壓縮檔變大）或沒有退路。

## 7. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-09-29 | 立。第 0 步證據 `findings/evidence/m3-assets/`。 |

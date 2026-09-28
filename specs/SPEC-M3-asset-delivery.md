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
  （頁面、profile、wasm 的 sha256、工具自己的 sha256；來源路徑寫相對的，因為 MANIFEST 會隨發佈出貨）。任何一個 `.gz` 超過
  45,000,000 位元組就**拒絕打包**：那是 Firefox 實測還會保留的最大編碼後大小，超過它 Firefox 的第二次開檔就默默失去好處
  （審核第 8 項；wasm 現在 40.9 MB）。換目錄是兩次 rename 再刪舊的，不是先刪再放。
- **buildId**＝ `{路徑: 原始 sha256}` 正規化 JSON 的 sha256 前 16 個 hex。它是**解碼後內容**的函數，跟 gzip 的位元組無關。
- `engine/` 不進 app 的 git（`.gitignore`），由工具產生、隨發佈的壓縮檔出貨。app 裡的 `dist` 符號連結刪掉。ddev 的
  bind mount 設定一併刪掉；**容器要到下一次 `ddev restart` 才真的少掉那個掛載**，這一步不重啟（見 §4 K1-3e 怎麼確認沒人用它）。

### 3.2 送出：一條 PHP 路由、預壓縮、網址帶身分

- 所有引擎檔案都走 `/index.php/apps/litecore/r/<位址>/<路徑>`，**位址＝`<buildId>-<服務政策雜湊 8 hex>`**（審核第 1 項，
  2026-09-29 改；原本只有 buildId）。快取存的是本文**加上 header**，而 worker 腳本套用的正是快取裡那份的 CSP 與 COEP：只改送法
  不改內容時，網址若不變，快取開著的瀏覽器會繼續用舊 header 直到快取放掉它。所以 controller 把每個回應的 header 從同一張
  `SERVE_POLICY` 表組出來，表的雜湊進位址——改送法就換位址。Nextcloud 自己加的 header 不在表裡（具名限制）。
- 只送 MANIFEST 裡有的路徑，其餘一律 404；位址不是目前的那一個也 404——**除了編輯器文件**：舊位址的 `e2-editor.html` 303 到
  目前的位址（重新整理、歷史紀錄、還原的分頁在升級後仍打得開；審核第 11 項）。MANIFEST 列了但檔案不在，回不帶快取 header 的
  404。`..`／NUL 的防線補回（查表之外的第二道）。
- 請求接受 gzip：直接串流 `.gz`（`StreamResponse`，不整檔讀進記憶體），`Content-Encoding: gzip`、`Content-Length`＝gz 大小。
  不接受：用 zlib 邊解邊送。兩種都帶 `Vary: Accept-Encoding`。
- 資產一律 `Cache-Control: private, max-age=31536000, immutable`（`Response::cacheFor`），並帶 `ETag`（送出的位元組的 sha256）；
  帶著它的條件請求由 Nextcloud 回 304（2026-09-29 補）。**編輯器文件本身除外**：它嵌了這個
  使用者、這個檔案的 initial state（檔案 id、ETag），維持不快取。
- 腳本照舊帶 COEP `require-corp` 與 worker 用的 CSP；`Content-Type` 依副檔名，`.wasm` 是 `application/wasm`（串流編譯需要）。
- Files 的連結不改（`/apps/litecore/r/e2-editor.html?fileId=N`），那個網址改成 303 到
  `/index.php/apps/litecore/r/<位址>/e2-editor.html?fileId=N`。頁面裡所有相對網址（模組、`workerUrl`、worker 抓的檔）
  因此都落在同一個位址底下。
- 為什麼網址前面要帶 `/index.php`：Apache 上，`.js`／`.wasm`／`.html` 這些白名單副檔名的 pretty URL 今天是經由
  「找不到檔 → `ErrorDocument 404` → `index.php`」才到得了 PHP（伺服器紀錄與 `.htaccess:207`、`:199`，讀原始碼推得）；nginx 上靠
  `try_files` 的退路。帶 `index.php` 之後兩種伺服器都直接進前端控制器，不依賴任何一條退路。

### 3.3 撤回路線圖 §5.3 的兩個前提

「必須 web server 直出」與「不穿過 PHP」撤回（驗收判準的形式第 4 節：前提被證偽就刪掉，不造機械維持它）：

- 直出的原樣 wasm 正是進不了快取的那一種（第 2 節）。要讓它以編碼後的大小進快取，伺服器得替一個靜態檔加上
  `Content-Encoding`——app 沒有辦法不經伺服器設定做到這件事（Apache 要 `.htaccess`，只有 Apache；nginx 沒有對應物）。
  PHP 可以，而且在兩種伺服器上是同一條路。
- ~~代價寫清楚：第一次開檔，每個大檔在傳輸期間佔住一個 PHP-FPM worker，合計約 64 MB。之後在瀏覽器快取有效期間（一年，
  或直到 buildId 改變）同一個瀏覽器不再抓。Nextcloud 自己的每一次檔案下載（WebDAV）本來就經過 PHP，這是同一種成本，
  **慢速用戶端佔住 worker 多久沒有量**。~~（審核第 9 項：成本寫輕了，改寫如下）
- 代價（推論，**未量**）：每個瀏覽器、每個位址第一次開檔要經 PHP 送約 64 MB，同時約三條大串流（wasm、base、cjk），
  `output_buffering=0` 之下每條在整段傳輸期間佔住一個 PHP-FPM worker。**每次換位址（引擎或送法改了），每個使用者的下一次
  開檔都要重來一次**；幾個慢速用戶端同時開檔就可能吃滿 `pm.max_children`，整台 Nextcloud 跟著卡。這不是「跟 WebDAV 下載
  一樣」——WebDAV 下載是使用者自己要的一個檔，這個是每個使用者每次升級都要付的。「一年」是 `max-age` 的上限，不是量到的
  保存時間；Firefox 使用者**每次登出**都會被 Nextcloud 清掉快取（見 §5）。
- 選 PHP 最硬的理由其實是另一個已量的事實：引擎腳本必須帶 COEP（閘門 0 的 E1：從 app 目錄直出的 worker 腳本兩個瀏覽器都在
  開機時死掉）。只要腳本得經 PHP，讓大檔也走同一條路的額外代價就是上面那一條。
- 「直出的原樣 wasm 進不了快取」是在 Apache 上量的。審核者記得 Nextcloud 文件的 nginx 設定把 `application/wasm` 列在
  `gzip_types` 裡（**未查**）；若是，nginx 上直出的 wasm 本來就會壓縮後送。

「immutable 快取」保留，而且這一步才讓它成立。

### 3.4 為什麼是 gzip，不是 zstd／brotli

zstd 比 gzip 再省約 15 MB（wasm −25%），但 PHP 沒有內建 zstd／brotli 的解碼器，遇到不接受它的用戶端就沒有退路；gzip 用
zlib，PHP 內建。gzip 的 41.0 MB 在 Firefox 實測保留的範圍內（45 MB 保留）。zstd／brotli 列為之後的選項（第 6 節）。

### 3.5 離頁解鎖提前到 `beforeunload`（finding 105，2026-09-29 補）

第一次 shakedown 撞到：快取開著的 Firefox 離開編輯頁時，宿主在 `pagehide` 送的 UNLOCK 經常沒到伺服器（新宿主 6/13 解鎖、
舊宿主 9/10），下一次開同一個檔 `LOCK` 423、只能另存副本。修法：`beforeunload` 就送 UNLOCK（兩發），`pagehide` 再送
（兩發）；宿主要問「確定離開嗎」的那一支不解鎖。~~修法後 30/30。~~修法後原本失敗的那一臂（Firefox 快取開）12/12，另 18 次
在修法前就沒失敗過的臂也全過；0/12 的 95% 上界約 26%，**殘留率低到什麼程度沒有證明**（審核第 3 項）。細節與代價見 finding 105。
**殘留**：宿主要問「確定離開嗎」的那一支（內容困在頁面、或存檔還在路上）仍然只在 `pagehide` 解鎖——正是修法前 Firefox 快取開
13 次掉 7 次的那條路，沒有量（審核第 7 項）。

### 3.6 宿主 JS 改了就要升 app 版本

`litecore-editor.js` 由 Nextcloud 以 `?v=<md5(app 版本) 前 8 碼>` 送出（`TemplateLayout::getVersionHashByPath`，讀原始碼），
Apache 對它送 `max-age=15778463, immutable`。app 版本不變，快取開著的使用者就一直用舊的宿主 JS。引擎不受此限（網址帶 buildId）。
所以這一步把 `appinfo/info.xml` 的版本升到 0.2.0（審核後的修法再升 0.2.1），之後宿主 JS 每改一次都要升；K0-6 替人記著這件事
（審核第 16 項）。

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
5. （審核後加）每個 `.gz` ≤ 45,000,000 位元組（§3.1）。
6. （審核後加）app repo 裡最後一個改到 `js/` 的 commit，不晚於最後一個改到 `appinfo/info.xml` 裡 `<version>` 那一行的 commit（§3.6）。

### K1 線路（不開瀏覽器，runner 以 admin 登入）

1. MANIFEST 裡每個路徑（編輯器文件除外）以 `Accept-Encoding: gzip` 取：200；`Content-Encoding: gzip`；**回應本文的 sha256＝
   MANIFEST 的 gz sha256**（送的就是打包的位元組），解壓後＝原始 sha256；`Cache-Control` 含 `immutable` 且 `max-age`
   ≥ 31536000；`Vary` 含 `Accept-Encoding`；`Content-Type` 依副檔名表（`.wasm`＝`application/wasm`）；`.js` 帶
   `Cross-Origin-Embedder-Policy: require-corp`。
2. 同一批以 `Accept-Encoding: identity` 取：200；沒有 `Content-Encoding`；本文 sha256＝原始 sha256。
3. 以下全部 404（不得是 200，也不得是 3xx）：(a) 宣告但不載入的資源包；(b) 另一個 profile 的 wasm
   （`profiles/e2-editor-v14/probe.wasm`）；(c) `../appinfo/info.xml` 與它的百分比編碼形（審核第 14 項：`../` 那一形在 Apache
   就被正規化掉，量到的是 Apache 不是 controller）；(d) 正確路徑配錯的~~buildId~~位址；(e) 舊的靜態網址
   `/apps-extra/litecore/dist/profiles/e2-editor-v8/probe.wasm`；（審核後加）(f) 只有 buildId、沒有政策雜湊的舊形位址；
   (g) `engine/` 目錄的靜態網址（`/apps-extra/litecore/engine/MANIFEST.json`；Apache 上量，nginx 上審核者推論會 200，未量——
   內容本來就是公開的引擎）。
4. `/apps/litecore/r/e2-editor.html?fileId=N` 是 303，`Location` 以 `/index.php/apps/litecore/r/<~~buildId~~位址>/e2-editor.html?fileId=N` 結尾，
   不以 `//` 開頭；（審核後加）位址是 `<MANIFEST 的 buildId>-<8 hex>`；舊形位址（只有 buildId）的 `e2-editor.html` 也 303 到同一個網址。
5. 編輯器文件（帶測試檔的 fileId）：200、COOP `same-origin`、COEP `require-corp`，`Cache-Control` **不含** `immutable` 也
   不含正的 `max-age`；（審核後加）文件的 initial state 裡 `editor.sourceSha256`（它實際重新包裝的那一份頁面）＝MANIFEST 裡
   `e2-editor.html` 的 sha256（審核第 10 項：否則舊的 dist 掛載還在，讀錯來源也會過）。
6. （2026-09-29 補，見修訂紀錄）第 1 條的每個回應都帶 `ETag`；帶著它（`If-None-Match`）再以 gzip 取一次：304、本文 0 位元組。

### K2 瀏覽器（每次一個新的、**快取開著**的 profile）

每次：上傳測試檔 → 從 Files 開 → 等宿主 `done` → 放游標、做一個段落動作（同宿主入口 H1 的煙霧步驟）→ 回 Files → 再開一次
→ 同樣的煙霧步驟 → 回 Files。紀錄是 web 容器的 Apache access log 在每次開檔前後兩個位移之間、該瀏覽器 User-Agent 的列；
每次回 Files 之後，runner 以 admin 輪詢測試檔的 `nc:lock` 10 秒（K2-5，2026-09-29 補）。（審核後加）每次宿主 `done` 之後，
runner 也以 admin 讀一次 `nc:lock`。記錄檔裡解析不了的列、以及別的 User-Agent 打到 app 路徑的列都記下；**有任何一列，該次
判紅**（儀器被污染，審核第 13 項）。

1. **第一次開檔**：`/r/<位址>/` 底下被請求的路徑集合＝MANIFEST 的路徑集合（編輯器文件包括在內），每一列 200；app 路徑
   （含 `/apps-extra/litecore/`）底下沒有任何 4xx／5xx；`/r/` 底下除了那個 303 與上述路徑之外沒有別的。（審核後加，第 5 項）
   **第二次開檔也套用**「沒有 4xx／5xx」「`/r/` 底下沒有別的位址」「編輯器文件恰好一列、200」三條。
2. **第一次開檔送出的是壓縮後的位元組**：每一個資產請求的 `%O` ＜ 該檔 gz 位元組數＋~~4096~~1500（審核第 13 項：量到的 header
   是 875–930 位元組；1500 之下仍有三個小檔 gzip 省不到 600 位元組、這一條看不見，它們的位元組由 K1-1 核對）。
3. ~~**第二次開檔沒有資產請求到伺服器**：`/r/<buildId>/` 底下只有編輯器文件（1 列）；303 那一列可以有。~~
   ~~**第二次開檔沒有任何資產帶本文回來**（2026-09-29 改，見修訂紀錄）：`/r/<buildId>/` 底下編輯器文件恰好 1 列；其餘每一列都是
   304；303 那一列可以有。~~
   （審核第 5 項後再改）**第二次開檔，資產只有「產品自己要求每次確認」的那些可以到伺服器，而且只能是 304**：那份清單由 runner
   從閉包的原始碼推出（`fetch(new URL("./x", self.location.href), {cache: "no-cache"})`，目前只有 `sdk-manifest.json`），不手寫。
   其他任何資產出現在第二次開檔的紀錄裡——304 也算——就是紅：`immutable` 沒被遵守。
4. 兩次開檔宿主都到 `done`、都沒有 `stranded`；兩次的煙霧步驟都成功（游標放下、動作使 revision 前進）。
5. （2026-09-29 補，見修訂紀錄）~~**兩次開檔宿主的鎖都是 `held`**~~——第二次沒有被第一次留下的鎖擋成 423；**每次離頁之後 10 秒內
   伺服器上沒有鎖**。（審核第 6 項後改：不讀宿主自己下的結論）每次 `done` 之後伺服器的 `nc:lock` 是 `1`、宿主的 `LOCK` 是 200
   且 `verified` 是 `true`；離頁後最後一次讀到的 `nc:lock` **恰好是空字串**（讀不到屬性不算解鎖）。

次數：Chrome 3、Firefox 3。報告記下每個 profile 所在磁碟的剩餘空間（Chrome 的上限跟著它走）。Chrome 的 profile 在 `/tmp`，
這台機器上是 **tmpfs**（審核第 8 項）；Firefox 的在 `/home`（ext4）。

### K3 M3 的既有流程在新宿主上重跑

宿主入口、鎖與權限、版本三支 runner 以各自原本的判準對新的宿主 commit 各跑一次計數執行，判定與原本相同，紅案全紅。
runner 的改動：`check_m3_skeleton_open.ROUTE` 從完整路徑改成後綴 `/e2-editor.html`（文件網址現在帶位址；三支 runner
都經由它判「落在編輯路由」）；`check_m3_versions.HOST_COMMIT` 改指新的宿主 commit（那是綁定，不是判準）。改動與理由寫進 commit。
**K3 的三支 runner 都是快取關著跑的**：finding 105 那一類只有快取開著才出現的行為，K3 看不到——那是 K2 的工作。

### K4 發佈壓縮檔（量測，登錄，不是過／不過）

以 app 發佈會有的內容（`appinfo/ lib/ templates/ js/ engine/`，不含 `src/ node_modules/ .ddev/ nextcloud/`）打 `tar.gz`，
記大小。

### 紅案與計數

K0–K2 每一條至少一個突變，每個突變都要找得到它的那一條（找不到算失敗；判定看問題字串是否以該條款開頭）；**先讓評分紅一次再跑計數**。計數執行照
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
- **Firefox 使用者每次登出，快取就被 Nextcloud 清掉**：登出回應對 HTTPS、非 Chrome 的 User-Agent 送 `Clear-Site-Data: "cache",
  "storage"`（`core/Controller/LoginController.php:96-100`，讀原始碼；審核第 4 項）。下一次開檔又是經 PHP 的 64 MB。Chrome／Edge
  不受影響。沒有 K2 臂登出。
- Firefox 在剩餘空間小的磁碟上會不會收 40.9 MB 的 gz 沒量（審核者記得 Firefox 也有「單筆不超過快取容量 1/8」、容量隨剩餘空間
  縮放，未查）；X1 的 Chrome 對照組同時換了檔案系統（tmpfs 對 ext4），「跟著剩餘空間走」是兩個變因一起動的結果。
- 升級之後，開著的舊分頁裡 SDK 的「崩潰後重啟」會在舊位址建新的 worker；Chrome 會因為 manifest 要重新確認而拿到 404，
  重啟失敗（Firefox 從快取拿得到）。沒有量，重新整理就好（文件會被 303 到新位址）。
- nginx 上 `engine/` 目錄可能被靜態直出、不必登入（審核者依 Nextcloud 文件的 `try_files` 推論，未量）；內容是公開的引擎。
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
| 2026-09-29 | **K3**：版本 `VERSIONS CORRECT`（`m3-versions/runs/2026-09-28T173014+0000.json`）、鎖 `LOCKS LAND`（`m3-locks/runs/2026-09-28T174346+0000.json`）在宿主 `5e53362` 上照舊成立，紅案 68、87 全紅，主 session 從報告重新評分。**宿主入口跑不起來**：它的 runner 寫在宿主會上鎖之前（上一次計數執行綁 `0dcb745`），關瀏覽器不離頁、鎖留約 306 秒，下一次重設上傳 423。這不是這一步的退步；它檢查的東西除了 H5（頁面拒絕壞宿主，頁面沒動）都已由版本與鎖在新宿主上覆蓋。runner 要退役還是改寫，留給下一個 session。執行者「有東西在主動重新上鎖／孤兒 geckodriver」的讀法查過是錯的（access log：上鎖的是 runner 自己的 HeadlessChrome）。 |
| 2026-09-29 | **計數執行：`ASSETS DELIVERED`**（`findings/evidence/m3-assets/runs/2026-09-28T172628+0000.json`，Chrome 3/3、Firefox 3/3，宿主 `5e53362` 乾淨、位址 `9076b0b425222c0e-566647db`、頁面 `fbfb59a4…`、runner `9e970440…`；從報告重新評分同一判定；紅案 84 個全紅；`make test-e2-c-static` exit 0；期間沒有容器被建立）。判準沒有再動。K3 另判。 |
| 2026-09-29 | 立。第 0 步證據 `findings/evidence/m3-assets/`。 |
| 2026-09-29 | **任何計數執行之前：加 K2-5、§3.5、§3.6。**逼出它的是第一次 shakedown（`shakedown/2026-09-28T161410+0000.json`：Firefox 第二次開檔 `LOCK` 423）與分辨探針 `leave-unlock-*.json`（finding 105）。形式：逐實例性質（每一次開檔、每一次離頁）。截止：計數執行落地即封閉。計數語意：沒有計數執行存在，不涉及歸零。K3 的鎖與權限 runner 全部是快取關著跑的，**看不到**這個缺陷；所以它放在 K2，不是 K3。宿主 commit 因此從 `7a11a4b` 往後移。 |
| 2026-09-29 | **任何計數執行之前：K2-3 改寫、加 K1-6、§3.2 加 ETag。**逼出它的是第二次 shakedown（`shakedown/2026-09-28T164501+0000.json`）：Chrome 第二次開檔重抓了 `sdk-manifest.json`（200、2,894 位元組），Firefox 沒有。原因讀原始碼：worker 以 `cache: "no-cache"` 抓它的 manifest（出貨的 `sdk-worker.js:513`），也就是**產品刻意每次向伺服器確認**；我們的回應沒有 validator，確認的結果只能是整份重送。原本的 K2-3 是為「沒有請求」這個處方寫的，而那個處方與產品的設計衝突（頁面與 profile 的位元組不動）。改寫的理由：我們要擋的是「重抓位元組」（第 2 節的 169.6 MB），所以新的 K2-3 對**任何**帶本文的資產回應都仍然是紅，只允許 304。形式：逐實例性質。截止：計數執行落地即封閉。宿主加 `ETag`（gzip 與原樣各用自己送出的位元組的 sha256），Nextcloud 的 `NotModifiedMiddleware` 對完全相符的 `If-None-Match` 回 304。 |
| 2026-09-29 | **對抗性審核（opus，唯讀）之後、任何計數執行之前：判準與宿主修訂。**審核原文與逐項處置在 `findings/evidence/m3-assets/review-2026-09-29-opus.md`。宿主（`5e53362`，0.2.1）：位址加上服務政策雜湊（第 1 項，HEAVY：快取也存 header）、舊位址的文件 303 到目前的、缺檔回不帶快取的 404、補回 `..`／NUL 防線、「頁面還在」的檢查不再跳過隱藏分頁。打包：`.gz` 超過 45 MB 拒絕、來源路徑改相對、換目錄改兩次 rename。判準：加 K0-5、K0-6、K1-3(f)(g)、K1-4 的位址形與舊位址、K1-5 的 `sourceSha256`；K2-1 的三條套用到第二次開檔；K2-2 slack 4096→1500；K2-3 的 304 只放行從原始碼推出的 `no-cache` 路徑（之前任何資產都可以 304，`immutable` 等於沒在測）；K2-5 改讀伺服器（開檔後 `1`、`verified` 為真、離頁後恰好空字串）；記錄檔解析不了的列與別的用戶端的列判紅。§3.3 的成本改寫（每次換位址每個使用者重付 64 MB、FPM 可能被吃滿、一年是上限）、§5 補登出清快取等五條。紅案 84 個全紅（`shakedown/2026-09-28T172209+0000.json`）。形式都是逐實例或工具封閉；截止＝計數執行落地；沒有計數執行存在，不涉及歸零。 |

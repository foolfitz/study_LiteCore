# SPEC M3：引擎的 zstd 表示（交接的 G）

> 2026-09-30 立。判準與預測寫在任何實作、runner 改動與瀏覽器量測之前（第 4 節）。
> 證據標記照 `doc-conventions`：**已觀察**＝量過、**讀原始碼**＝沒量、**推論**。

## 1. 為什麼要有

交接 `HANDOFF-2026-09-29h` 的優先序是 A（發佈管道，要擁有者對外動作）、G（本件）、F。H＋J 由擁有者挑時間。G 是下一個
不需要擁有者動手的項目。資產派送規格 §6 C 把它寫成「第一次開檔再省約 15 MB」。

第 0 步量出第二個理由，而且比較重（**已觀察**，2026-09-30，`findings/evidence/m3-zstd/offline-sizes-2026-09-30.json`）：

- a11y 候選 profile `e2-editor-v14` 的 wasm 是 135,237,060 位元組，**gzip -9 之後 47,987,197 位元組，超過打包工具的
  `MAX_GZ_BYTES`＝45,000,000**（資產派送 §3.1、K0-5：Firefox 156 實測會保留的最大編碼後大小）。現行打包工具**會拒絕**這顆
  core。同一個 wasm 以 zstd -19 是 36,078,637 位元組。
- 所以 a11y cutover 若只有 gzip，只有兩條路：放寬 K0-5（Firefox 的第二次開檔默默失去快取，資產派送第 2 節的 169.6 MB 問題
  回來一半），或先做這一步。這件事之前沒有任何文件寫過。

出貨中的 v8 引擎：閉包 169,625,763 位元組，gzip 63,858,483，zstd 48,527,295（−15.3 MB，−24%）。資產派送 §3.3：**每次換位址，
每個使用者的下一次開檔都要經 PHP 付這一筆**，而且每條大串流在傳輸期間佔住一個 PHP-FPM worker。

## 2. 事實

- **已觀察**（資產派送第 0 步 X1，`findings/evidence/m3-assets/README.md` S0-4）：同一個 wasm 以 `Content-Encoding: zstd`
  送（30.7 MB），Chrome 151 與 Firefox 156 都解成正確的 115,297,503 位元組，而且三種 profile 組態下都存進了 HTTP 快取。
- **已觀察**（2026-09-30 離線）：v8 閉包 22 個檔逐檔的 gzip／zstd 大小如下（gzip 取自 `engine/MANIFEST.json`，
  buildId `7f4f4e2204b4a9ec`；zstd 是 libzstd 1.5.7 level 19）。三個大檔的 frame window 是 8,388,608（2²³），其餘是
  single-segment（window＝內容大小，最大 181,072）。

  | 檔 | 原樣 | gzip | zstd | 差 |
  | --- | ---: | ---: | ---: | ---: |
  | `profiles/e2-editor-v8/probe.wasm` | 115,297,503 | 40,878,530 | 30,670,578 | 10,207,952 |
  | `profiles/resources/cjk-r5….data` | 19,484,784 | 15,503,708 | 12,170,785 | 3,332,923 |
  | `profiles/resources/base-r5….data` | 34,178,400 | 7,312,172 | 5,532,678 | 1,779,494 |
  | `profiles/resources/base-r5….metadata` | 181,072 | 19,054 | 16,084 | 2,970 |
  | `profiles/e2-editor-v8/probe.js` | 143,998 | 36,283 | 33,638 | 2,645 |
  | `e2-editor-app.js` | 94,138 | 33,971 | 31,441 | 2,530 |
  | 其餘 16 個 | | | | 每個 ≤ 999；`state-machine.js` 是 −3（zstd 比 gzip 大） |

- **讀原始碼**：宿主 `369e6ed` 只認 gzip（`EditorController::acceptsGzip`）；不接受 gzip 的請求拿原樣（zlib 邊解 `.gz` 邊送）。
  回應的 header 全部由 `SERVE_POLICY` 組出，它的雜湊是位址的一部分（資產派送 §3.2）。
- **已觀察**：本機有 `zstd` CLI 與 Python 3.14 的 `compression.zstd`（libzstd 1.5.7）；**沒有** brotli（CLI 與 Python 模組都沒有）。
- **推論**（沒量）：Chrome 151 與 Firefox 156 在 HTTPS 上對每一種請求都送 `Accept-Encoding: gzip, deflate, br, zstd`。
  第 4 節 Z2-1 就是它的量測。

## 3. 改動範圍（先寫死）

產品頁（`fc80050c…`）、殼層（v54）、引擎、profile、`dist/` 都不動。只動打包工具、`litecore` 宿主的 PHP 與評分工具。

### 3.1 打包

- 每個檔除了現有的 `engine/files/<路徑>.gz`，再寫一份 `engine/files/<路徑>.zst`：zstd **level 19**、單執行緒、libzstd 的
  預設 frame 參數（帶 content size 與 checksum）、**不用** long mode、**不用** level 20 以上。
- 理由：`zstd` 這個 content coding 的 window 上限是 8 MB（RFC 9659，**讀規格**，本件沒查原文逐字），level 19 的 windowLog 是
  23＝8 MiB，level 20 以上與 long mode 都會超過。X1 量過的正是 level 19 的產物。
- `engine/MANIFEST.json` 的 schema 改成 `litecore-engine/2`：每個路徑加 `zstBytes`、`zstSha256`；`totals` 加 `zstBytes`；`source`
  加 `zstd: {level, libzstd}`。**buildId 規則不變**（解碼後內容的函數），所以預測仍是 `7f4f4e2204b4a9ec`。
- 任何一個 `.zst` 超過 45,000,000 位元組就拒絕打包（同 K0-5 的理由：Firefox 拿到的會是 zstd）。`.gz` 的 K0-5 **不動**（§5）。

### 3.2 送出

- 表示的選擇（伺服器的偏好序）：請求接受 `zstd` → `.zst`；否則接受 `gzip` → `.gz`；否則原樣（照舊 zlib 邊解 `.gz` 邊送）。
  「接受」＝`Accept-Encoding` 裡有該 token（不分大小寫）且它的 `q` 不是 0；`*` 不算（跟現在的 gzip 判斷一樣）。不依 `q` 值
  排序：瀏覽器不送 `q`，伺服器在可接受的表示之間依自己的偏好選，HTTP 允許。
- zstd 回應：`Content-Encoding: zstd`、`Content-Length`＝`zstBytes`、`ETag`＝`zstSha256`；其餘 header（型別、快取、`Vary`、CSP、
  COEP）與 gzip 回應同一張表。每一種表示的 `ETag` 都是它自己送出的位元組的 sha256。
- `SERVE_POLICY` 的編碼欄改成偏好序列表 → 政策雜湊變 → **位址變**：每個快取開著的瀏覽器的下一次開檔重抓一次（約 48.5 MB）。
  這是資產派送 §3.2 的設計（改送法就換位址），不是退步。舊位址的文件照舊 303 到新位址。
- 宿主版本升 0.2.5（只改 PHP；`js/` 不動，K0-6 不受影響）。

### 3.3 為什麼是 zstd，不是 brotli

- 工具：zstd 本機就有，brotli 要新裝依賴（R8-B 的規矩：新依賴要先取得確認）。
- 量測：X1 已量兩個瀏覽器收 zstd 並快取；brotli 在這裡沒量過。
- Safari：支援 brotli；是否支援 zstd **未查**。Safari 在這條研究線本來就沒量（§5）；它不宣告 zstd 就拿 gzip，與今天相同。
- brotli 之後要加，是偏好序多一項、打包多一份，不與本件互斥。

## 4. 驗收判準（先於 runner 改動與任何計數執行寫下）

環境同資產派送（ddev、NC 34.0.2 tarball、Apache、admin）。評分由 `wasm_sdk_probe/tools/check_m3_assets.py` 做，**只讀報告裡
的原始欄位**。靜態條件照舊：`dist/` 與 `web/` 的 `e2-editor-app.js` 都是 `fc80050c…`；`make test-e2-c-static` exit 0；宿主 repo
沒有未 commit 的改動。

**資產派送的 K0–K2 條文全部照舊**，在新宿主上重新判。K2-2（`%O` ＜ gzip 位元組＋1500）在送 zstd 時仍然成立，保留；更緊的
條件是 Z2-1。

### Z0 打包（離線）

1. MANIFEST 列的每個路徑都有 `engine/files/<路徑>.zst`；它的 sha256＝MANIFEST 的 `zstSha256`；解壓後的 sha256＝MANIFEST 的
   `sha256`＝`dist/<路徑>` 的 sha256＝runner 當場從 `dist/` 推出的閉包值。
2. 每個 `.zst` 恰好是一個 zstd frame、後面沒有位元組；frame header 算出的 Window_Size ≤ 8,388,608（single-segment frame 的
   window＝它宣告的內容大小）。
3. 每個 `.zst` ≤ 45,000,000 位元組。
4. MANIFEST 的 `schema`＝`litecore-engine/2`，`buildId`＝`7f4f4e2204b4a9ec`（綁定，寫在跑之前：解碼後的內容沒有變）。

### Z1 線路（不開瀏覽器，runner 以 admin 登入）

以 `B`＝`gzip, deflate, br, zstd`（§2 推論的瀏覽器字串）。

1. MANIFEST 每個路徑（編輯器文件除外）以 `Accept-Encoding: B` 取：200；`Content-Encoding: zstd`；本文 sha256＝`zstSha256`；
   解壓後＝`sha256`；`Content-Length`＝`zstBytes`；`ETag` 的值（去引號）＝`zstSha256`；`Cache-Control`、`Vary`、`Content-Type`、
   `.js` 的 COEP 與 K1-1 同一套條件。
2. 表示的選擇，對 `sdk/document-sdk.js` 逐列（選擇邏輯與路徑無關，**讀原始碼**；所以只用一個檔）。表示同時以
   `Content-Encoding` 與本文 sha256 判：

   | `Accept-Encoding` | 應得 |
   | --- | --- |
   | `zstd` | zstd |
   | `ZSTD` | zstd |
   | `gzip;q=0, zstd` | zstd |
   | `zstd;q=0, gzip` | gzip |
   | `gzip, deflate, br` | gzip |
   | `zstd;q=0` | 原樣 |
   | `br` | 原樣 |

3. 條件請求（每個路徑，編輯器文件除外）：`B`＋`If-None-Match: <zstd 的 ETag>` → 304、本文 0 位元組；`B`＋`If-None-Match:
   <gzip 的 ETag>` → 200、zstd 本文（別的表示的 validator 不得讓這一份 304）；`gzip`＋`If-None-Match: <zstd 的 ETag>` → 200、
   gzip 本文。
4. 每個路徑的三種表示（zstd、gzip、原樣）的 `ETag` 兩兩不同。

### Z2 瀏覽器（K2 的每一次，快取開著；另加一組拿掉 zstd 的 Firefox）

`D`＝{編輯器文件以外、`gzBytes − zstBytes ≥ 1500` 的路徑}，由 runner 從 MANIFEST 算，不手寫。1500 是 K2-2 的 slack：
對 `D` 的檔，送 gzip 時 `%O` ≥ `gzBytes` ≥ `zstBytes＋1500`，一定落在 Z2-1 的紅側。**非空洞**：`D` 必須含 wasm 與兩個 `.data`，
否則該次判紅（預測 `D` 是 §2 表上的 6 個檔，佔 zstd 位元組的 99%）。

1. Chrome、Firefox 每一次的第一次開檔：`D` 裡每個路徑在紀錄裡的每一列，`%O` ＜ `zstBytes`＋1500。
2. **退路臂 `firefox-nozstd`**：Firefox 以 pref `network.http.accept-encoding.secure`＝`gzip, deflate, br` 開；K2 的全部條文
   照樣要過（第二次開檔同樣不得重抓：40.9 MB 的 gzip wasm 在 Firefox 的保留範圍內，資產派送已量）；第一次開檔 `D` 裡每個路徑
   的每一列 `gzBytes` ≤ `%O` ＜ `gzBytes`＋1500。這一臂同時是 pref 的正向對照：pref 沒生效，列會是 zstd 的大小而轉紅。
3. 次數：`chrome` 3、`firefox` 3、`firefox-nozstd` 3。

### Z3 其他五支 M3 runner 在 0.2.5 上重新計數

頁面誠實化、鎖與權限、版本、宿主入口、同秒存檔各一次計數執行，判定與 0.2.4 上相同、紅案全紅。它們都是快取關著跑；若 Z2-1
的預測成立，它們拿到的引擎檔也是 zstd。只改綁定常數（宿主 commit／版本），寫在跑之前，改動與理由寫進 commit。

### Z4 發佈壓縮檔（量測，登錄，不是過／不過）

照資產派送 K4 的指令打 `tar.gz`、記大小。預測：約 107 MiB（K4 的 60.5 MiB 加上約 46 MiB 的 `.zst`）。

### 預測（跑之前寫；落空就照實登錄，判準不動）

- **P1**：Z2-1 在兩個瀏覽器每一次都過——也就是頁面模組、worker 的 `importScripts`、worker 的 `fetch`、pthread 各自的
  請求都宣告了 zstd（`D` 涵蓋這四種請求；worker 腳本本身不在 `D`，見 §5）。
- **P2**：退路臂的 `D` 各列是 gzip 的大小，K2 全過。
- **P3**：buildId 仍是 `7f4f4e2204b4a9ec`，位址的政策雜湊變了。
- **P4**：第一次開檔 app 路徑的位元組約 48.5 MB 加 header（對照 `ASSETS DELIVERED` 的約 63.9 MB）。

### 紅案與計數

Z0–Z2 每一條至少一個突變，每個突變都要找得到它的那一條（判定看問題字串是否以該條款開頭）；K0–K2 的既有紅案照舊全紅。
**先讓評分紅一次再跑計數**。計數執行照 `findings/evidence/m3-locks/README.md` 的「Counted run: rules fixed before it started」四條。

K0–K2＋Z0–Z2 在 `chrome`、`firefox`、`firefox-nozstd` 各 3/3 全過＝**`ZSTD DELIVERED`**（也就是 `ASSETS DELIVERED` 在 0.2.5 上
重新成立）。Z3 五支照舊＝「0.2.5 上 M3 的流程沒有退步」，另判。

**如果這件事永遠沒做**：gzip 照舊，第一次開檔約 63.9 MB；a11y core（v14 形）在現行 K0-5 下打包不了——cutover 之前必須放寬
K0-5（Firefox 失去第二次開檔的快取）或回來做這一步。Z3 沒做：**不得**說 M3 的六個計數判定在 0.2.5 上仍然成立。

## 5. 明確不承諾

- Safari、Edge、nginx 沒量。Safari 若不宣告 zstd，拿 gzip，與今天相同（推論）。
- `D` 以外的 16 個檔（包括 worker 腳本本身、`sdk-manifest.json`、編輯器文件）兩種大小差不到 1500，瀏覽器裡**分不出**拿到哪一種；
  它們的位元組由 Z1-1 在線路層核對。**worker 腳本這一種請求（`new Worker`）因此沒被 Z2 觀察到**；它的差是 999 位元組。
- 瀏覽器解 zstd 的 CPU 時間沒量。K2 記下的「到宿主 `done` 的秒數」照記，不設門檻。
- **a11y core 的 gzip 超過 45 MB（§1）**：K0-5 在 cutover 時要重新判。那時 Chrome／Firefox 拿 zstd，gzip 只給不宣告 zstd 的用戶端，
  K0-5 的依據（Firefox 的快取上限）對 gzip 已不適用；改不改、怎麼改，寫在 cutover 那一步並寫理由（「驗收條件是為某個處方寫的」）。
  **這裡不預先放寬**：出貨的 v8 兩種都在 45 MB 以內。
- Firefox 使用者每次登出，快取照舊被 Nextcloud 清掉（資產派送 §5）。
- 大於 8 MiB window 的 frame 會不會被瀏覽器拒絕沒量（我們不產生，Z0-2 擋）。
- Apache `mod_deflate` 不重壓已經帶 `Content-Encoding` 的回應：gzip 已由 K1-1 量到；zstd 由 Z1-1 量。ddev router（Traefik）同。

## 6. 擁有者要決定的（不擋這一步）

- **J**（從發佈壓縮檔在 `litecoreprobe` 重裝）：若 G 先落地，J 改在 0.2.5 的壓縮檔上跑；0.2.4 的壓縮檔不再是要裝的那一份。
- **A**：壓縮檔變大（K4 的 60.5 MiB → 約 107 MiB，Z4 會量）。App Store 原始碼預設的 30 MiB 兩者都超過（K4 已記），A 的問題
  形狀不變；若 A 選「安裝時從別處下載引擎」，大小與 app 壓縮檔脫鉤。

## 7. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-09-30 | 立。第 0 步證據 `findings/evidence/m3-zstd/`（離線大小、a11y 候選 wasm 的 gzip 超過 `MAX_GZ_BYTES`）。 |

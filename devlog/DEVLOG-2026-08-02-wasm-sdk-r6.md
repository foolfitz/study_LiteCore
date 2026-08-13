# R6 WASM Document SDK：協作 Reference Application

日期：2026-08-02（Asia/Taipei）

## 執行原則

- 執行順序固定為 R6-A discovery、R6-A reader shell、R6-B contract／service、R6-C 整合。
- 優先沿用 R5 `writer-review`，不修改 `libreoffice-26-8` tracked files。
- 不使用 last-write-wins、raw UNO、unoembind、任意 `.uno:*` passthrough，亦不解析未承諾的 callback payload。
- 觀察、推論與待驗證分開記錄；失敗嘗試與負向 evidence 不以最後成功結果覆蓋。

## 進場基線

### 已觀察

- `libreoffice-26-8` HEAD 是 `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`。
- tracked／untracked 狀態與交接清單一致；原始輸出保存於
  `findings/evidence/sdk-r6/baseline/core-status-before.txt`。
- R5 `writer-review` SDK 為 `0.5.0-r5`、C ABI 1.1、Provider contract 1.0、capability bits 2047。
- R5 `writer-review` loader SHA-256 是
  `35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566`；WASM SHA-256 是
  `ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`。
- 現有 `DocumentHandle.search()` 底層送出 `SearchItem.Command=0`，對應 LibreOffice
  `SvxSearchCmd::FIND`，不是 `FIND_ALL`。
- 公開 `SearchResult.selections` 保留 `part` 與 opaque `rectangles`；R6 不把 rectangles 格式升格為
  application contract。

### 推論

- R6-A viewport 可直接使用 `getDocumentSize()` 暴露的 width／height 與公開 region render；仍須以真實
  R5 artifact 驗證邊界、相鄰 tile 與長文件捲動。
- 唯一 anchor 可能可透過同一 document version／revision 內重複公開 search，將 selection object
  當短生命週期 opaque occurrence signature 來偵測 wrap；這不等於跨版本永久 ID。

### 待驗證

1. Writer width／height 是否涵蓋完整可渲染文件，邊界 clamp 是否可決定性重跑。
2. opaque selection signature 對唯一、遺失與重複 quote 是否足以保守判斷候選數。
3. mutation 後的 semantic invalidation 是否足以觸發全 revision tile cache 清除。
4. 多筆 render 的序列順序、queued abort 與 late completion 行為。
5. Chrome／Firefox 是否都能在 R5 `writer-review` artifact 重現上述結果。

## 實驗歷程

### 2026-08-02：唯讀接手與基線

- 預期：R5 artifact 與 core 工作區維持交接狀態。
- 實際：HEAD、dirty 清單、artifact SHA-256 與 R5 summary 一致。
- 決定：R6 不重連 core；先建立只依賴公開 SDK 的 discovery harness。

### 2026-08-02：Discovery 嘗試 1 — readiness parser 錯誤

- 輸入：以 `run_r6_discovery.py --browser chrome` 啟動 loopback static server，等待
  `r6-discovery.html`。
- 預期：HTTP 200 後啟動 Chrome 並執行真實 WASM checkpoint。
- 實際：runner 重用了 `run_browser_probe.wait_http()`；該 helper 會把 response 當 JSON 解析，HTML 雖已
  回應仍反覆得到 `Expecting value: line 1 column 1`，30 秒後逾時。
- 是否可重現：是；錯誤發生在 browser／WASM 啟動前。
- 決定：這是 R6 runner 自身的錯誤，不是 SDK finding。改用只檢查 HTTP 200 的 `wait_page()`，保留本段
  失敗歷程後重跑相同輸入。

### 2026-08-02：Discovery 嘗試 2 — search-not-found payload 正規化缺口

- 輸入：Chrome 150、R5 `writer-review`、`t1-plain-zh.odt`，搜尋不存在的
  `R6-ANCHOR-DOES-NOT-EXIST`。
- 預期：公開 SDK 回 `found=false` 與空 selections。
- 實際：`LOK_CALLBACK_SEARCH_NOT_FOUND` 帶回純查詢字串，R5 Worker 無條件 JSON.parse，得到
  `RESULT_PARSE_ERROR`。原始 JSON、log、截圖保存在 `findings/evidence/sdk-r6/discovery/chrome.*`。
- 是否可重現：Chrome 1/1；發生在相同固定輸入。
- 已觀察：R5 loader／WASM 已正常啟動，open、render queue 與 cancel 已發生；失敗點只在 not-found
  response adapter。
- 推論：我方 Worker adapter 缺少 callback taxonomy normalization；不是 core 或 C ABI 缺口。
- 決定：建立 finding 011。只修改 R6 使用的 Worker adapter，在 `found===true` 時解析 JSON；R5
  `dist/profiles/writer-review/` 原始 worker 與 large artifact 保持 byte-for-byte 不變。

### 2026-08-02：Preflight status 比對假陰性

- 預期：修補只位於外層 workspace，core status 仍與進場一致。
- 實際：artifact hash 全數通過，但 preflight 把 `git status` stdout 做 `.strip()`，恰好移除第一筆
  porcelain status 的前導空白，使 ` M desktop/...` 變成 `M desktop/...` 並誤判漂移。
- 決定：改成只移除結尾換行的 `.rstrip("\n")`；不放寬預期 dirty 清單。

### 2026-08-02：Discovery 嘗試 3 — t2 close 30 秒逾時

- 輸入：search-not-found 修補後，以同一 engine 依序跑 t1、t2、t3 discovery。
- 預期：三份文件都完成 open／render／search／close。
- 實際：t1 所有 checkpoint 通過；t2 已 open 並完成 render queue/cancel，但 `finally` 的 `close()` 使用
  SDK 預設 30 秒，回 `TIMEOUT`，使 t2 尚未寫入完成結果。原始事件仍保存在 Chrome discovery JSON。
- 已觀察：t1 width/height、相鄰 tile、部分越界 tile、unique/not-found anchor、queued abort 與 mutation
  invalidation 均成立。
- 待驗證：t2 是單次 lifecycle 延遲，或 search/close 可重現阻塞；目前不升格為 finding。
- 決定：加入單 fixture 重跑入口，close 使用既有 browser flow 對文件操作採用的 180 秒上限；先單獨重跑
  t2，再重跑完整 checkpoint。

### 2026-08-02：Discovery 嘗試 4 — t2 close 180 秒再次逾時

- 輸入：只跑 `t2-styled.odt`，其餘 region／queue／search 步驟不變，close timeout 提升為 180 秒。
- 預期：若前次只是短暫延遲，close 應在 180 秒內完成。
- 實際：再次取得 `TIMEOUT`，無 `closed` response；原始結果保存為
  `findings/evidence/sdk-r6/discovery/chrome-t2-styled.*`。
- 已觀察：相同阻礙 2/2；建立 finding 012。
- 推論：尚不能判定是 styled 內容、表格搜尋、queued cancel 或組合操作造成。
- 決定：不再盲目重跑同組合。本輪 viewport corpus 改用規格允許的既有多頁 `t3-long.odt`；t2 不計入
  R6 GO 必要 corpus。若 t1／t3 也無法正常 close，才觸發 R6-A lifecycle gate 重新評估。

### 2026-08-02：R6-A discovery checkpoint — GO

#### 已觀察

- Chrome 150 與 Firefox 152 均以 R5 原始 loader／WASM／resource 成功跑完 t1 與 t3。
- t1 metadata 為 1 part、12474×17406 twips；t3 為 22 parts、12474×376968 twips。t3 首區與下一區
  tile hash 在兩瀏覽器均不同，width／height 足以排程完整長文件 viewport。
- 相鄰與部分超出右下邊界的 region 都回傳精確 `width*height*4` RGBA buffer。
- 連續 render 的完成順序是 first→third；中間 queued request 的 public Promise 得 `ABORTED`，Worker
  cancel-result 是 `OK`，late result 未覆蓋後續狀態。
- t1 mutation 後兩瀏覽器都收到 semantic `document-invalidated`；event 不含穩定 dirty rectangle。
- 同一 version/revision 內，唯一 quote 第二次搜尋回相同 opaque selection、重複 quote 第二次回不同
  opaque selection、零命中回 found=false。三者均以 `getSelection().text` 驗證 exact quote。

#### 推論與安全退化

- Reader 可以用公開 width／height 建立跨 viewport scheduler。
- 不解析 `rectangles` 字串，因此 R6-A 不宣稱 search highlight；只顯示命中狀態與 selection text。
- mutation 時清除該 revision 全部 tile，不嘗試自行解讀 raw invalidation payload。
- opaque selection signature 只在同一 open version/revision 內用於判斷「至少兩個候選」，不保存為跨版本
  anchor，也不以座標打破歧義。

#### 判定

- R6-A discovery 為 **GO**，沒有觸發未穩定 raw callback、revision cache 不可區分或正常 scroll 無界成長
  的停止條件。
- finding 011 已由 R6 Worker adapter 修正並跨瀏覽器驗證。
- finding 012 保留為 styled fixture lifecycle 限制，不阻擋規格允許的 t1＋多頁 t3 路徑。

### 2026-08-02：Reader browser 嘗試 1 — 初始 invalidation 後未重排 tile

- 輸入：Chrome 150、R6 reader shell、t1 v1；runner 等待 ready 且 first visible tile。
- 預期：open 後 visible viewport 至少完成一張 tile。
- 實際：state 已到 ready，但 tile draws 維持 0。live CDP state 保存於
  `findings/evidence/sdk-r6/browser/r6-a/reader-chrome-hang-live.json`。
- 已觀察：open 後到達 `document-invalidated`，scheduler 依安全策略取消當時 generation；cancel-result 分別
  是 `NOT_CANCELLABLE` 與 `OK`。舊 tile 沒有畫入，符合 generation 防線。
- 根因：reader UI 沒有在 semantic invalidation 清 cache 後重新排 visible viewport。
- 決定：onEvent 只辨識公開的 `document-invalidated` 名稱，以短 debounce 重新 schedule；仍不解析 callback
  detail 或 dirty rectangle。

### 2026-08-02：R6-A reader shell — GO

#### 已觀察

- Node 單元測試 11/11 通過，涵蓋狀態轉移、local bytes reload guard、worker crash、anchor 保守分類、
  CSS/twips 換算、邊界 clamp、visible-before-prefetch、最多 2 個 in-flight、revision cache、舊 generation
  late completion 防線與 LRU byte ceiling。
- Chrome 150 與 Firefox 152 各 3/3 browser samples 通過；原始 JSON、console log 與 screenshot 位於
  `findings/evidence/sdk-r6/browser/r6-a/`。
- Chrome first tile 為 1683.98～1750.56 ms；Firefox 為 2070.12～2102.58 ms。所有樣本都捲到
  y=1280 tile，Latin/CJK 搜尋 selection text 精確相符，且遠端 v2 event 進入 stale 後以新 worker reload。
- 故意觸發的 worker error 均映射為 `WORKER_CRASHED`，復原後 worker generation 增加；復原 generation
  每次完成 20 張 tile、取消 4 個舊 request，max in-flight=2，close 後 late draw=0。
- 最初只檢查 `firstTileMs` 的證據不夠嚴格：重建後 scheduler 曾顯示 completed=0。已保存該輪 JSON，
  隨後改成每一代 scheduler history，且 reload／crash recovery 後都必須取得 stable generation 新 tile。

#### 推論與判定

- public SDK 足以支撐 bounded viewport reader 與 worker-isolated lifecycle；R6-A 不需要 core rebuild。
- zoom 1.5→1.0 以重疊 Promise 產生真正的 generation 競爭；舊 generation 只能取消或成為 stale
  completion，不能繪入現行畫面。
- R6-A 判定 **GO**。進入 R6-B collaboration contract；finding 012 仍為非必要 styled fixture 限制。

### 2026-08-02：R6-B contract 實作與失敗嘗試

#### 嘗試 1：fixture URL 錯誤

- `node --test collaboration/tests/*.test.mjs` 在載入前因 URL 少了 `collaboration/` 層而得到 `ENOENT`。
- 此輪未進入 domain mutation；修正測試相對路徑後重跑，未隱藏原始失敗。

#### 嘗試 2：oversized HTTP request 沒有形成 typed error

- 純 domain adapter 12/12 通過；HTTP adapter scenario 4 的超長 replacement 得到 `TypeError: fetch
  failed`，而不是預期 `INVALID_ARGUMENT`。
- 已觀察：reference service 一超過 64 KiB 就在 request stream 中途 throw，尚未消耗的 request body 讓
  Node fetch 將連線視為失敗。
- 修正：仍只保存上限內資料，但把剩餘 loopback input 丟棄完再回 typed response。重跑後 HTTP adapter
  12/12 通過，scenario 耗時由約 6 秒降為約 91 ms 的整套 HTTP conformance。
- 架構影響：body limit 必須同時定義「拒絕語意」與 transport drain 行為；本問題未涉及 SDK/core，未另立
  finding。

### 2026-08-02：R6-B collaboration contract — GO

#### 已觀察

- contract `1.0`、strict mutation validator、fixed Alice/Bob identity、strong ETag／SHA-256、immutable
  version metadata、presence TTL、sidecar comment/suggestion、single lease、CAS、idempotency、event replay 與
  snapshot fallback 已由同一 domain implementation 提供。
- loopback HTTP service 只綁 `127.0.0.1`；錯誤 envelope 不回 stack/path/token，event/audit 不含 lease
  token 或文件 bytes。`http-audit.json` 以 `secret-r6-token|UEsDB` 掃描為空。
- 12 項 conformance 以同一 canonical fixture 分別跑 pure domain 與真 HTTP adapter：兩者皆 12/12，
  `adaptersEquivalent=true`。證據位於 `findings/evidence/sdk-r6/contract/`。
- commit-before fault 不增加 version；commit-after response interruption 已留下完整 v2 與 idempotency
  result，同 key 重試取回 v2，沒有 v3。wrong／expired／cross-document token 均為 typed rejection。

#### 推論與判定

- reference service 的單程序 atomic section 已足以證明 R6 contract 不採 last-write-wins，且 blob version
  與 suggestion decision 不會形成半套 state；此結果不外推 production durability/security/scalability。
- R6-B 判定 **GO**。進入 R6-C 雙 context reference app 與文件實際 round-trip。

### 2026-08-02：R6-C reference application 與 browser matrix

#### 已觀察

- reference service 同時提供 loopback API、ordered event replay 與 COOP／COEP 靜態頁面。Alice／Bob 是
  不同 browser process／profile、Document Worker、Provider Worker、ReaderSession 與 JS object graph；
  沒有共享 parent state。
- 首個 Chrome+Chrome S1～S7 run 一次通過；正式矩陣為 Chrome+Chrome 3/3、Firefox+Firefox 3/3，
  Chrome Alice+Firefox Bob 的 S1／S2／S3／S5 1/1。
- S1：雙 presence、comment/reply/resolve 與 deterministic TTL expiry 成立，sidecar 前後 v1 SHA-256
  都是 `bda964…ec02`，SDK revision 不變。
- S2：Bob 的 R4 Provider operation 只建立 sidecar；Alice 重新驗證 version／unique anchor／exact selection／
  revision，save 後以 lease+If-Match+SHA-256 提交唯一 v2。Bob event replay 後是 stale，明確 reload 才將
  canvas v1 換成 v2，並找到 `R4 Provider：LibreOfficeKit`。v1 bytes 未改。
- S3：Alice 持有 lease 時 Bob 得 `LEASE_HELD`；Bob 的本機 ODT bytes 成功 save 並保留，但 Alice 先提交
  v2 後，Bob 的 v1 ETag PUT 得 `VERSION_CONFLICT`。server 僅 v1／v2，沒有 v3 或 lost update。
- S4：t3 的不存在 quote 與重複 `English compatibility text` 分別得到 `ANCHOR_NOT_FOUND`／
  `ANCHOR_AMBIGUOUS`，suggestion 轉 conflict，blob hash／version／SDK revision 不變。
- S5：保留完整 gap 時 replay；event retention 淘汰 gap 時 snapshot fallback。snapshot 到達後 Bob 的 UI
  同時顯示 local canvas=v1／authority=v2，不把舊 canvas 偽標為 v2；reload 後才收斂。
- S6：generic `.uno:*`、未知 operation、錯 endpoint、過長 replacement、cancel late result 全被 R4
  validator／abort guard 擋下；Provider Worker crash 後 Document Worker 仍能搜尋，重建 Provider 後可再 invoke。
- S7：Document Worker crash 前若已 save，UI 保留可下載 bytes；未 save 則明示不可恢復。兩者都不自動
  重送 mutation，權威 version 維持 v1。

#### 推論與判定

- R6 reference app 證明 review-first＋短效單 writer lease 能在現有公開 SDK 上形成完整產品切片；它不是
  Office blob CRDT，也不宣稱 production auth、durability、scale 或 offline merge。
- 所有競爭與斷線由 fixture clock／event retention／命令 barrier 控制，不依賴人工 timing。
- R6-C browser matrix 判定 **GO**，沒有觸發 mixed-browser 部分 GO 或停止條件。

### 2026-08-02：ODT／PDF round-trip

- 保存 7 份 S2 v2 ODT（兩個完整矩陣各 3，加 mixed 1）。每份 ZIP CRC、所有 XML parse、必要原文、
  原始 styles 與 replacement 恰好一次全部通過。
- `BOB-FORBIDDEN-STALE-R6`、missing／ambiguous replacement、S7 crash 文字與 `.uno:` 均不存在。
- 桌面 LibreOffice `26.2.4.2 620(Build:2)` 對 7/7 ODT exit 0，產出 7 份 87,193-byte PDF；ODT／PDF
  hashes 保存在 `findings/evidence/sdk-r6/roundtrip/summary.json`。
- v2 ZIP bytes 因 ODF metadata／封裝細節可不同，但每份 semantic／structure gate 相同；不把 binary
  不同誤判為協作分支。

### 2026-08-02：R1～R5 regression 與工作區保護

- `make test-r5`：Document SDK 9/9、Provider SDK 11/11、C++ ABI header、Worker syntax、R5 profile／resource
  classifier 2/2 全通過。
- R5 review Chrome／Firefox、reader Chrome／Firefox、Provider conformance Chrome／Firefox 全通過；
  loader/WASM 仍為 `35d96f…c63566`／`ba257b…dfc6`。
- R3 ABI 與 semantic flow／comment+tracked-change desktop round-trip、R2 10 次 lifecycle＋真 worker crash、
  R1 legacy＋desktop round-trip 全通過。
- 最終 preflight：core HEAD `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`；五筆 tracked dirty 與
  一筆 untracked 檔案和進場完全一致。R6 沒有改 core、沒有重連結 R5 large artifact。
- 外層 workspace 不是 Git repository，因此無可用 repo 可切 R6 commit；`libreoffice-26-8` 既有 dirty
  changes 未納入、未 commit。

## 最後判定

**GO**。

- R6-A、R6-B、R6-C、round-trip、R1～R5 regression 與 preflight 所有 release checks 均為 true。
- Machine summary：`findings/evidence/sdk-r6/summary.json`；計數為 reader 6 samples、contract 24 scenario
  executions、同瀏覽器完整 S1～S7 6 runs、mixed 1 run、ODT/PDF 7 samples。
- finding 011 已結案。finding 012 保留待最小化：只影響 t2 styled fixture 的特定 discovery 操作組合；
  規格必要 t1／t3 在 Chrome／Firefox 與雙 context 流程均正常，不降低 R6 判定。
- R7 只在 roadmap 中是下一候選，尚未取得執行授權。

### 2026-08-02：人工驗收回報 — accept 後 edit 使用舊 quote

- 使用者回報按「本機 edit + save」得到 `ANCHOR_NOT_FOUND: local edit quote is missing`。
- 已重現：初始 v1 edit 正常；接受人工 suggestion 將 `LibreOfficeKit` 換成 `alice-manual-R6` 後，按鈕仍
  固定搜尋 `LibreOfficeKit`，因此 public search 正確回 not-found。這不是 SDK anchor 漏失，而是 UI
  沒有把 edit intent 綁定目前搜尋欄，也未在 accepted version 更新欄位。
- 修正：edit 按鈕明確使用搜尋欄 quote；accept／local replace 後把搜尋欄同步成 replacement。若使用者輸入
  的 quote 確實不存在，仍保留 `ANCHOR_NOT_FOUND` 並顯示可操作訊息，不猜測其他位置或自動換目標。
- 回歸：R6-C S2 加入 accept 後從搜尋欄 local edit，再 undo 的 browser assertion。
- Chrome Alice+Firefox Bob 與 Firefox Alice+Chrome Bob 各 1/1 通過；兩端 edit 均產生本機 ODT bytes、
  undo 後 `localBytesAvailable=false`，authority `versionCount=2`。證據在
  `findings/evidence/sdk-r6/browser/r6-c/edit-regression/`。

### 2026-08-02：引導式人工驗收 — GO

#### 已觀察

- 修正後，Alice 以目前搜尋欄的 `alice-manual-R6` 執行 `localEditFromSearch`，得到 18,732-byte 本機
  ODT、SHA-256 `aae3b918…392a0bf`，SDK revision 由 1 前進至 2；搜尋可命中
  `alice-local-R6`。`undoLocal` 後 revision 前進至 3、本機 bytes 清空，新字串不再命中，原字串恢復。
- 重置 `t1-plain-zh.odt` fixture 後，以 Alice／Bob 兩個獨立 browser context 驗收：雙方 presence 都看到
  Alice、Bob `view=v1`；Bob 建立 `comment-1`，Alice 建立 `comment-2 reply→comment-1` 並 resolve 根留言，
  兩端 sidecar 顯示一致。
- Bob 的 Provider suggestion 由 Alice 接受成 v2。Alice commit、Bob 明確 reload 的 ETag／blob SHA-256
  都是 `2b29b36…a4bfaddd`；Bob reload 後以 SDK revision 0 精確搜尋到
  `R4 Provider：LibreOfficeKit`。
- Alice 持有 lease 時 Bob acquire 得 typed `LEASE_HELD: document already has an active lease`；Alice release
  後 Bob acquire／renew／release 均成功。驗收結束時 service `lease=null`。
- Bob 的 Document Worker 故障事件為 `WORKER_CRASHED`，Reader 進入 `recoverable-error`；未 save 的本機
  mutation 沒有 bytes 可恢復，也沒有自動重送。明確 reload 後回到同一 v2／revision 0，權威 replacement
  仍可精確搜尋。
- 權威 ODT 與 Bob 未提交 ODT 分開下載；使用者確認前者包含 `R4 Provider：LibreOfficeKit`、後者包含
  `bob-local-R6`。Undo 後權威文字恢復可搜尋。
- 最終唯讀 service snapshot：`currentVersion=v2`、`versionCount=2`、`eventSequence=18`、
  `idempotencyCount=18`、current bytes 18,934、`lease=null`；comment 2 筆、accepted suggestion 1 筆。
  原始 machine-readable 摘要在
  `findings/evidence/sdk-r6/manual/manual-acceptance-2026-08-02.json`。

#### 推論

- 最終仍只有 v1／v2，且 v2 hash 與 Provider accept response 相同，因此人工本機 edit、下載、Undo 與
  Worker crash 沒有靜默發佈 v3，也沒有覆寫權威文件。
- 人工驗收證實回報的 edit intent/UI 綁定問題已修復；它補強產品操作可理解性，不取代既有 deterministic
  browser matrix、fault barrier 與 round-trip machine evidence。

#### 待驗證／未由本次人工重跑

- `ANCHOR_AMBIGUOUS`、event-retention snapshot fallback、Provider invalid／late-result matrix 與 commit
  interruption idempotency 本次沒有再用人工 UI 操作；它們仍由正式 R6-C／R6-B 自動證據覆蓋。

#### 判定

- 引導式人工驗收判定 **GO**；沒有 lost update、silent anchor misapply、錯誤版本標示或未經 validator
  mutation，R6 總判定維持 **GO**。

#### 留痕後驗證

- `jq empty findings/evidence/sdk-r6/manual/manual-acceptance-2026-08-02.json` 通過；
  `python3 wasm_sdk_probe/tools/validate_r6_release.py` 重新彙整後仍為 **GO**，14 項 R6／回歸／preflight
  checks 全為 true。
- 首次額外執行 `sha256sum dist/profiles/writer-review/soffice.js
  dist/profiles/writer-review/soffice.wasm` 失敗，原因是 R5 content-addressed dist 實際檔名為 `probe.<hash>`，
  並沒有這兩個非雜湊別名；這是驗證命令路徑錯誤，不是 artifact 遺失。
- 改從 `findings/evidence/sdk-r6/baseline/preflight-after.json` 取得實際路徑重驗：loader
  `35d96f…c63566`、WASM `ba257b…dfc6`，均與 R5 基線一致。core HEAD 仍為
  `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，五筆 tracked dirty 與一筆 untracked 檔案未變。

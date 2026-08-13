# DEVLOG 2026-08-04 — LibreOffice WASM SDK R8

## 範圍與授權

- 本輪先完成R8-A delivery discovery checkpoint，再依另行確認的精確範圍完成R8-B；不修改LibreOffice core、
  不重建R5 `writer-review` artifact、
  不安裝依賴、不使用root或外部帳號。
- 以R5 loader／WASM與R7 reference assets為release graph來源；只新增host delivery、schema、Service Worker、
  browser runner、validator、tests與evidence。
- R8-C～D尚未修改；R8-B是在A結案、列出精確檔案／命令並取得確認後才執行。

## 進場基線（已觀察）

- Core HEAD：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`。
- 原有工作現場為五個tracked dirty與`LibreOffice_VCL_Qt6_研究報告.md`；before／after完全一致。
- R5 loader：`35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566`。
- R5 WASM：`ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`，115,265,157 bytes。
- Python 3.14.4、Node 24.16.0、gzip 1.14、Chrome 150.0.7871.128、Firefox 153.0.1 Snap、
  geckodriver 0.37.0；沒有Brotli CLI。

## 實作與凍結輸出

- 建立JSON Schema與deterministic manifest generator；closed allowlist共17 roles，未知role、重複role、危險URL、
  size/hash mismatch與artifact漂移都會拒絕。
- Release ID：`writer-review-82cfce600c80ed6e`；canonical manifest SHA-256：
  `9328e2738fffd6feade8e5499c40744430c7e09570fa9be9cb191789cab0bf6a`。
- 15個required artifact合計169,353,155 raw bytes；base+CJK mandatory、fallback fonts optional。
- 建立獨立R8 deterministic server、T0 same-origin／T1 cross-origin、header contract、request journal與fault
  scenarios；沒有修改原有`web/serve.py`產品基線。
- 建立discovery Service Worker，僅cache release entry、loader與115 MB WASM測試子集；初始session寫入並驗證，
  browser restart後再驗證，最後delete cache並unregister。
- 凍結integrity規則：SHA-256作用於browser decoded artifact bytes；media type與content encoding另行驗證，
  transport rejection不能取代raw bytes與hash。
- Font v1 policy：zh-TW啟動前mandatory base+CJK；fallback為使用者明確fidelity選項。Public SDK沒有document font
  inventory時不得解析未承諾callback自動猜測。

## 失敗嘗試與修正

### Preflight attempt 1

- **已觀察**：第一次before preflight只因Git預設把中文untracked檔名輸出成quoted octal而判core status不符。
- **推論**：工作區沒有漂移，是validator字串正規化不足。
- **修正**：使用`git -c core.quotepath=false status`；失敗保留於
  `findings/evidence/sdk-r8/discovery/baseline/preflight-before-attempt-1.json`。

### Unit test fixture attempt

- **已觀察**：新增profile parent test時使用不可寫的虛構`/workspace`，18 tests中1個fixture error；原有17個通過。
- **修正**：測試改用自動清除的temporary directory；重跑18/18通過。這不是產品實作失敗。

### Firefox persistent profile attempt 1

- **已觀察**：Firefox session在navigation前回`Failed to set preferences: unknown error`；無custom profile可啟動。
- **推論與驗證**：Firefox是strict-confined Snap，看不到host `/tmp`的persistent profile；相同preferences改用
  `/home`專案路徑即啟動成功。
- **修正**：R8 runner把temporary profile放在`dist/r8/`下並於結束清除。原始分類證據：
  `findings/evidence/sdk-r8/discovery/browser/firefox/attempt-1-session-error.json`。

### Finding 015：truncated response oracle

- **已觀察**：第一次fixture傳完整22-byte body但宣告29 bytes；Chrome T0/T1 reject，Firefox T0/T1 resolve完整body，
  使原本要求`fetch` rejection的fault check為false。
- **推論**：Content-Length／連線結束不能作跨browser完整性oracle。
- **修正與重驗**：fixture改成宣告22、實傳15 bytes；Chrome以reject、Firefox以15-byte decoded size/hash mismatch
  都得到`detected: true`。Finding：`findings/015-firefox-fetch-content-length-mismatch.md`。

### Aggregate before after-snapshot

- **已觀察**：第一次執行aggregate顯示STOP，唯一false是尚未執行的`preflightAfter`。
- **判定**：這是依執行順序預期的incomplete state，不是停止條件。完成回歸與after快照後正式判定改為PARTIAL_GO。

## 測試結果

- R8 unit/static：18/18通過；JavaScript syntax與Python compile通過。
- Chrome 150：T0、T1 initial/restart、headers、faults、large cache全部通過。
- Firefox 153：T0、T1 initial/restart、headers、faults、large cache全部通過。
- 兩browser皆維持secure context、`crossOriginIsolated`、SharedArrayBuffer、Service Worker與CacheStorage；
  測試結束cache清空且registration unregister。
- R5、R6-C、R7-D static與Finding 012 remediation回歸全部通過。
- After preflight確認core HEAD／dirty與R5 loader／WASM hash不變。

## R8-A 判定

**PARTIAL_GO**。所有可自動化gate為true，未觸發停止條件。完整GO缺項：

- 本機無Brotli CLI，A只完成identity與gzip decoded邊界；
- 真storage quota沒有安全、可重現的browser控制面，不以mock冒充；
- public SDK無document font inventory，採locale＋使用者明確fidelity policy；
- T2 user-approved HTTPS deployment不是R8-A必要環境。

Machine summary：`findings/evidence/sdk-r8/discovery/summary.json`。下一步是依凍結schema、Finding 015與門檻實作
R8-B verified direct delivery；不得先寫production Service Worker activation／rollback。

## R8-B：versioned direct delivery（已觀察）

- 產出standard `writer-review-5fa3ca0d38f2b46d`（15 required roles，169,355,716 raw bytes）與
  full-fidelity `writer-review-687bd4d891114d62`（17 required roles，218,473,422 raw bytes）。bundle generator
  對既有release目錄只接受完全相同tree，不覆寫同release ID的不同bytes。
- 每個logical artifact都有identity與deterministic gzip（Python gzip level 9、mtime 0）；完整manifest與compression
  index保存在`findings/evidence/sdk-r8/delivery/{manifests,compression}/`，沒有偽造不可用的Brotli variant。
- `verified-loader`依closed schema驗證URL/origin、role、media type、encoding、encoded length、decoded bytes與SHA-256；
  mandatory graph全部驗證後才允許Document Worker，release/profile/sdk/core/capability與pack mapping再由Worker
  handshake比對。fidelity熱切換固定回`FONT_PACK_RESTART_REQUIRED`。
- T1只把WASM、base/CJK/fallback data與metadata映射到allowlisted resource origin；Document SDK、Worker與loader
  保持app/release origin，以維持module/Worker與pthread限制。跨origin response另驗證CORP；CORS仍由browser強制。
- Chrome 150與Firefox 153各完成T0 44 case、T1 39 case，共166 browser cases。identity/gzip在每一browser／topology
  都有3 cold＋3 warm；88個manifest／HTTP／bytes／media／encoding／timeout／cancel／stale／redirect／isolation
  negative全為typed拒絕，Worker=0、document mutation=0，之後known-good recovery成功。
- 每個browser各保存R6 plain、R7 t1、R7 t2與full-fidelity font輸出；8/8 ODT通過ZIP CRC、全部XML parse、全文
  等價與desktop LibreOffice PDF page count（t2 3→3，其餘1→1）。

## R8-B 失敗嘗試與修正

### Verified loader fixture attempt

- **已觀察**：最初新增media-type test時，mock helper在只改header的案例誤把body設成`undefined`，7項中1項先
  觸發size而非media typed error。
- **推論**：產品loader的判定順序沒有錯，是fixture把兩個維度一起改壞。
- **修正**：mock保留原body、只改media type；正式9/9 Node tests通過。

### Artifact fault query collision

- **已觀察**：第一次Chrome完整矩陣完成T0正向21 case後，`optional-pack-404`停在空頁；request journal顯示
  `fault=http-404`被HTTP server套到`r8-delivery.html`本身，頁面根本未執行。runner等待約3分29秒後由本輪
  主控安全中斷；已完成case保留，未偽裝成成功。
- **推論**：頁面控制參數與server fault參數共用名稱造成測試harness歧義，與LibreOffice runtime無關。
- **修正**：分離`deliveryFault`（由app加到目標artifact request）與`serverFault`（頁面header fault）；server tests
  重過後以resume只補未完成case，Chrome與Firefox完整矩陣全通過。

### Round-trip aggregate attempt 1

- **已觀察**：第一次roundtrip glob納入早期discovery留下的2份smoke output，10 case中Firefox T1舊smoke缺source
  path而使aggregate false；8份正式case其實全為true。
- **修正**：validator只接受凍結的四個正式case ID×兩browser；失敗結果保留為
  `findings/evidence/sdk-r8/delivery/roundtrip/summary-attempt-1.json`，正式8/8 summary為true。

### `locateFile()` closure pre-final audit

- **已觀察**：第一輪166個browser cases與8份roundtrip雖通過，結案逐項對照凍結契約時發現bundle內的
  `sdk-worker`仍保留`artifactFiles[path] || path`；已知logical file都走manifest mapping，但未知名稱會退回原始
  path。第一輪release與完整證據保留於
  `findings/evidence/sdk-r8/delivery-attempt-before-locatefile-closure/`，沒有覆寫或假裝成最終結果。
- **推論**：已通過的journal只能證明目前corpus沒有要求未知檔名，不能證明Emscripten動態路徑已被manifest封閉；
  若直接結案，會接近本spec「manifest無法約束動態路徑」的停止條件。
- **修正**：bundle generator只接受凍結的worker source shape，將`locateFile()`改為未知logical artifact立即丟出
  `R8_UNKNOWN_LOGICAL_ARTIFACT`；若上游source形狀漂移則build直接失敗。bundle validator也要求fail-closed marker。
- **重驗**：修正後release ID改為`writer-review-5fa3ca0d38f2b46d`／`writer-review-687bd4d891114d62`；Chrome與
  Firefox完整166 cases、正式8/8 roundtrip、R5/R6-C/R7-D/Finding 012回歸及before/after preflight重新全數通過。

## R8-B 回歸與判定

- R8-B unit/static：Python 14 tests（bundle/server/gate）與Node 9 tests全通過；JS syntax/Python compile通過。
- R5、R6-C、R7-D static與Finding 012 remediation全通過。after preflight再次確認core HEAD、既有六筆dirty、
  R5 loader/WASM hash及bundle完全未漂移。
- **判定：`PARTIAL_GO`，可進R8-C。** 所有安全閘門為true，沒有觸發防混版停止條件。
- 部分GO缺口一：本機沒有Brotli CLI，只實證identity與deterministic gzip。
- 部分GO缺口二：full-fidelity required graph 218,473,422 bytes超過R8-A凍結的200,000,000-byte limit；實際
  Chrome/Firefox可啟動且font roundtrip通過，但不因此放寬預算。standard graph仍在門檻內。
- **待驗證**：R8-C Service Worker staging/activate、offline、rollback、quota/eviction與last-known-good；R8-D
  production-shaped/T2與Brotli（若環境可用）。Machine summary：
  `findings/evidence/sdk-r8/delivery/summary.json`。

## R8-C：Service Worker原子更新、offline與rollback

### 已觀察

- 建立固定A／B／C release set；Service Worker以per-release CacheStorage、current＋valid backup metadata、
  activation journal、client pin與有界retention管理版本。所有mandatory artifact在寫cache前驗證media、encoding、
  bytes與SHA-256；atomic repair先建立並驗證新cache，再切換metadata cache name。
- Chrome／Firefox的T0／T1 full suite全數通過。after-preflight確認core HEAD、既有dirty狀態、R5 loader／WASM
  與release set未漂移。正式判定`PARTIAL_GO`，只保留真quota與顯式reload缺口。

### 失敗嘗試與修正

- staging最初未加`representation=identity`，browser取得gzip後被loader正確拒絕；保留attempt並補明確identity。
- cached fetch把`Request`物件直接傳給`URL`，造成synthetic cache key miss；正規化為`Request.url`。
- synthetic cached Worker response缺COOP／COEP，Worker被browser隔離阻擋；補回與app shell一致的isolation header。
- expected error頁雖`pass:true`，卻未在catch後保存current／known-good state，7個negative gate缺證；補唯讀status
  snapshot後重跑51案全過。
- Firefox headless的iframe old-client probe等待900秒，current仍為A；完整截圖與結果保存在attempts。改用同一
  profile三個WebDriver tab後約6秒完成，直接量到A／B兩個client pin，正式full suite通過。

### 推論與待驗證

- Firefox多client正式自動化應使用獨立tab，不把iframe ready當client ownership同步點。
- deterministic cache write reject證明known-good與cleanup語意，但不等同真quota exhaustion。
- T2 HTTPS／CDN與真quota留待授權環境；Service Worker不cache user document／clipboard／協作資料。

Machine summary：`findings/evidence/sdk-r8/service-worker/summary.json`。

## R8-D：production-shaped驗證（執行中）

### Active cached release corpus嘗試

- Chrome第一版把28份異質文件共用單一engine；`l0-t2`在search-first序列timeout並留下BUSY，污染後續文件。
  改為R7已驗證的四tile→search序列後`l0-t2`通過，但跨文件engine reuse仍在hyperlink文件留下in-flight。
- 依`startVerifiedEngine` one-time Worker與R8-A Firefox每頁3-generation預算，改為每案重新驗證同一active cached
  release、每頁預估最多2個一般Worker；Finding 012文件計2個generation。第一次3一般Worker頁實測為4，gate
  正確拒絕；保守分批後Chrome 28/28通過，6頁批次實測max=3，總12 generations。
- Chrome recovery delta顯示`l0-t2`與table/image ODT各產生一次bounded replacement；這些是已觀察的SDK close
  邊界，不是release混版。所有中間失敗保存在`production/attempts/`。
- Firefox在完成R8-C大量快速session後，R8-D fresh init長時間無batch結果，候選為Finding 014跨process累積。
  每批獨立process與單一process同origin navigation兩種策略都在第一批開始前等待900秒且沒有頁面結果；兩份
  `pass:false`原始證據均已保存，未把它歸因特定ODT或改寫成成功。
- R8-D因此不繼續消耗同一Firefox生命週期的generation。正式部分GO組合要求同時存在R7 Firefox 28份完整
  corpus、R7 Firefox 30分鐘soak、R8-C Firefox active-release update/offline/rollback，以及Finding 014；Firefox
  R8-D compatibility／longevity summary本身仍維持`pass:false`並列出formal gap。

### Longevity runner失敗嘗試與修正

- 第一版在同一已pin A的client啟用B health，正確收到`CLIENT_ALREADY_PINNED`；改由同origin iframe建立新B
  client，保留A長壽session而不熱換Worker。
- 第二版只跑固定cycle數，很快結束而沒有達到30分鐘；正式runner依wall-clock產生60秒間隔cycle與進度檔。
- 第三版在同一engine第二輪search timeout；R7已證明的50-cycle reuse路徑實際是render／close，故長壽cycle
  改為render-only，最後server-down時再由同頁第三個全新Worker做offline open／render／search健康檢查。
- 0.1分鐘短測通過後，啟動Chrome正式30分鐘run；A→B、offline A runtime、rollback A與每頁最多3 generations
  都由runner直接量測。正式結果待run完成後回填，不先宣稱通過。

### 額外檢查命令筆誤

- 正式Makefile測試之外，第一次手動`node --check`誤寫不存在的`web/r8-production.js`，因此得到
  `MODULE_NOT_FOUND`；實際前端檔是`r8-update-app.js`。改用現有檔名後JS syntax與Python compile通過；這是
  額外檢查命令筆誤，不是產品或build失敗。

### Final aggregate attempt 1

- Chrome正式30分鐘run已`pass:true`，但第一次執行`validate_r8_d.py`在效能統計讀取一個預期negative case時，
  因該case的`verified`為JSON `null`而不是物件，拋出`AttributeError`；browser evidence與longevity summary未受影響。
- 修正統計只採非null的verified／document timing，不把negative case虛構為零；新增單元測試涵蓋null detail後重跑
  aggregate。第一次額外`sha256sum`也誤指不存在的`artifacts/`目錄；正式preflight已用`dist/profiles/`正確路徑
  驗證R5 hashes，後續人工核對也改用該路徑。

## R8-D正式結果與R8結案

- Chrome active cached release A完成28/28份R7 corpus，6個頁面批次、12個Worker generations、每頁最高3個；
  所有case為true。
- Chrome正式soak為30.038415分鐘、30/30 cycles、4個Worker generations、每頁最高3個；A→B、server-down
  offline A runtime、rollback A與最後offline新Worker open／render／search全部通過。high-water：PSS
  1,448,559,616 bytes、RSS 2,510,135,296 bytes、storage usage 353,178,451 bytes、release cache
  338,711,481 bytes；本輪只記實測值，不由單一loopback run宣稱通用production budget。
- Regression runner的8組命令全通過；R8-D static最終為Python 5項、Node 18項，JS syntax／Python compile通過。
- Final validator的13項safety checks全部為true，machine decision為`PARTIAL_GO_LOCAL_DELIVERY`、`pass:true`。
- 正式缺口：未提供T2 HTTPS/CDN、真browser quota未驗證、candidate採用需顯式reload；Firefox 28份active-cache
  corpus與R8 update＋30分鐘soak未形成單一combined run，產品須維持Finding 014 bounded generation／reload策略。
- After preflight與人工hash核對確認core HEAD仍為`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`、既有dirty
  完整保留，R5 loader／WASM SHA-256仍為`35d96f5f...c63566`／`ba257beb...dfc6`。未修改LibreOffice core、
  未重建R5 artifact、未使用raw UNO／unoembind／任意`.uno:*`或last-write-wins。
- R8主線結案。下一步依roadmap是ODT-first基本編輯器discovery與正式spec；R9 automation仍為需求驅動backlog，
  R10深層減量需等待基本編輯器corpus／reachability凍結。

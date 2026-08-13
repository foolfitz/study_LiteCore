# LibreOffice WASM Document SDK R7 實驗紀錄

> 日期：2026-08-02  
> 範圍：R7「輸入、Clipboard、格式相容性與長期穩定性」；目前執行 R7-A discovery checkpoint。

## 留痕原則

- **已觀察**：由命令、瀏覽器或檔案直接取得，並附 evidence 路徑。
- **推論**：由已觀察結果推導，尚未等同已驗證的 SDK 承諾。
- **待驗證**：尚未完成或必須由 headed／人工步驟確認。
- 失敗嘗試保留於本檔與 raw evidence，不只記錄最後成功結果。

## 2026-08-02：R7-A 進場與執行授權

### 已觀察

- R1～R6 已完成；R7 規格盤點已建立 R7-A → R7-B → R7-C → R7-D 順序。
- `libreoffice-26-8` HEAD 基線為 `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，既有 dirty files 由使用者指定保留。
- R7-A 沿用 R5 `writer-review` artifact 與 R6 worker manifest；本階段不重建或修改 LibreOffice core。
- 使用者已確認 R7-A 的確切新增／修改檔案、build／test 指令與預期產物，可在核准範圍內連續執行。

### 推論

- 現有公開 SDK 足以先驗證 host composition adapter、Unicode insertion、ODT baseline 與格式辨識；若 DOCX 因內部固定 `.odt` 路徑失敗，必須保存 runtime evidence 後另提窄幅 SDK 修正，不能在 discovery 階段偷改 SDK。

### 待驗證

- Chrome／Firefox synthetic composition、clipboard 分支與 Unicode commit。
- Fcitx Chewing 的真 OS IME headed evidence，以及實際 user-gesture clipboard。
- ODT／DOCX／corrupt／unknown bytes 的 open 分類與 Worker recovery。
- 10 次 lifecycle、3 次 crash／restart 的 process 與 WASM memory baseline。

## R7-A 執行紀錄

本節隨每個可獨立驗證單位即時追加。

### 失敗嘗試：第一次 R7 preflight 誤判 core dirty baseline

- **已觀察**：第一次 `python3 tools/validate_r7_preflight.py --phase before` 產生
  `preflight-before.json`，artifact 與 manifest 全數通過，但 core `pass:false`。
- **原因**：驗證器共用 command helper 對 stdout 使用 `.strip()`，把 Git porcelain 第一行用來表示 index
  狀態的前導空白移除，造成第一個既有 dirty file 與已核准 baseline 不相等。
- **修正**：只移除行尾 CR/LF，保留 stdout 的前導空白；第一次失敗 JSON 會由修正版重跑覆蓋，失敗事實保留於本 DEVLOG。
- **推論**：這是新驗證器的序列化錯誤，不是 core 狀態漂移；artifact SHA-256 無異常。

### 已完成單位：preflight 與最小 frozen corpus

- **已觀察**：修正後 R7 preflight `pass:true`；core HEAD／既有 dirty baseline、R6 worker manifest 與
  8 個 `writer-review` artifact／resource SHA-256 均通過。環境盤點保存於
  `findings/evidence/sdk-r7/baseline/`。
- **已觀察**：以既有 `t1-plain-zh.odt` 建立 `r7-plain.odt`，並用隔離的 LibreOffice 26.2.4.2
  user profile 轉換 `r7-plain.docx`；另建立兩個 deterministic 257-byte truncation 與一個 unknown bytes fixture。
- **已觀察**：manifest 固定 5 個 corpus 項目的 exact bytes／SHA-256、來源／license、預期 open 與 derivation；
  第二次無 `--force` 執行 generator 回報 `frozen-valid`，沒有自動接受新 hash。
- **已觀察**：ZIP CRC／XML／ODF mimetype／OOXML content type／macro／external relationship／size limits
  validator `pass:true`；Python unit tests 2/2 通過。
- **證據**：`findings/evidence/sdk-r7/corpus/manifest-validation.json`、
  `wasm_sdk_probe/test-docs/r7/manifest.json`。

### 已完成單位：host input adapter 與靜態 discovery 資產

- **已觀察**：host adapter Node tests 5/5 通過：composition exactly-once、duplicate beforeinput suppression、
  cancel／empty／teardown 零 mutation、`text/plain` only、UTF-8 上限與 mutation serialization。
- **已觀察**：R7 discovery 頁、corpus dist copy、Chrome／Firefox runner 與 Python aggregator 已建立；
  `make r7-discovery-assets`、`make test-r7-a-static`、JS/Python syntax 全數通過。
- **已觀察**：在任何 R7-D 正式結果產生前，已於 R7-A spec 凍結 50 cycles、10-cycle block、
  512 MiB／35% post-close growth、64 MiB block median slope、256 MiB WASM heap step 等門檻。

### Chrome discovery 第一次執行：保留失敗與架構發現

- **已觀察**：synthetic composition 只產生 1 次 `臺灣合成-R7` SDK mutation；cancel 的 request delta 為
  0 且 anchor not found。Unicode、astral CJK、emoji、ZWJ family、combining/NFC、換行與連續 commit 均可
  search，輸出 ODT 20,137 bytes。
- **已觀察**：無 user gesture 的 Chrome clipboard read 得到 `NotAllowedError`，SDK mutation delta 為 0；
  synthetic `ClipboardEvent` 同含 HTML／plain text 時只送入 plain text，anchor found。
- **已觀察**：正常 t1 lifecycle 10/10 open／first tile／close 通過。
- **已觀察**：相同 DOCX bytes（SHA-256 `3f8c5645…708ce`）使用 `plain.docx` 得
  `INVALID_ARGUMENT`，改用不實的 `plain.odt` 則 open/render/search/close 通過；ODT bytes 配 `.docx` 也被拒。
  建立 finding 013，R7-A 的 DOCX 結論降為安全的部分 GO 候選，不新增 `open-docx` capability。
- **失敗嘗試**：第一次 crash cycle 在 intentional crash 後、`engine.restart()` 前直接拿舊 handle render；
  由於 generation 尚未在 restart 前變更，request 送到已終止 Worker 後等到 60 秒 `TIMEOUT`。隨後 restart
  與 control ODT recovery 成功。這不是不可恢復 crash，但測試順序不符合現有「restart 後舊 handle stale」
  contract。
- **修正方向**：重跑時先以 `engine.open()` 驗證 crash state 立即 `WORKER_CRASHED`，呼叫 `restart()` 後再
  以舊 handle 驗證 `STALE_DOCUMENT`，最後 open/render/close control fixture。第一次 raw JSON、log 與 278 筆
  process samples保留於 `findings/evidence/sdk-r7/discovery/`，不得只以重跑成功覆蓋歷程。

### 2026-08-03：Chrome 重跑與 Firefox 第一次 discovery

- **已觀察**：修正 crash 測試順序後，Chrome 自動 discovery `pass:true`、`PARTIAL_GO`；10/10
  lifecycle、3/3 crash/restart，crash state 得 `WORKER_CRASHED`、restart 後舊 handle 得
  `STALE_DOCUMENT`，control ODT recovery 全通過。15 個 Worker 建立／15 個終止。
- **已觀察**：Firefox 的 input、Unicode ODT、format 7-case、10/10 lifecycle、3/3 crash/restart 均通過；
  finding 013 的 DOCX name-dependent 結果與 Chrome 一致。Firefox 不提供
  `performance.measureUserAgentSpecificMemory`，runner 仍保存 63 筆 process-tree RSS/PSS samples。
- **失敗嘗試**：Firefox 接受 synthetic `ClipboardEvent` constructor 與 `DataTransfer`，但 dispatch 後
  `clipboardData.getData('text/plain')` 是空字串；adapter 因空字串而零 mutation，原先 probe 把 anchor not
  found 判為整體失敗。此 evidence 保存在 `discovery/attempt-1/clipboard/firefox.json`。
- **修正方向**：先保存 synthetic event 無 payload 的 browser observation，再明確使用 adapter fixture fallback
  驗證 `text/plain`／HTML discard 分支。fallback 仍標 `synthetic=true`，不取代 headed user-gesture clipboard。

### 失敗嘗試：逐項 search 改變 selection，造成後續 insert 取代前一筆

- **已觀察**：Firefox clipboard fallback 修正後兩 browser 頁面級自動條件可通過，但第一次
  `validate_r7_a.py` 得 `automaticDecision: STOP`；Chrome／Firefox 輸出 ODT `content.xml` 都缺少多數先前
  已在 browser 當下 search found 的 Unicode probe。
- **原因**：probe 使用 `insertText(item) → search(item) → insertText(next)`。公開 `search()` 會建立
  selection；下一次 `insertText()` 的 `paste` 語意因此取代目前選取，而不是在原 caret 後追加。這是測試
  編排錯誤，不是無操作介入時的 SDK silent loss。
- **修正**：所有 composition／Unicode／clipboard mutation 先依序完成，只記 revision；最後、沒有後續
  mutation 時才執行全部 search，再保存 ODT 並由 Python 直接檢查 `content.xml` code points。
- **證據**：失敗 aggregator、兩份輸出 ODT 與 raw browser evidence 已保存到
  `findings/evidence/sdk-r7/discovery/attempt-2/`。

### 失敗嘗試：第一筆 paste 後 selection 未由 host 明確 collapse

- **已觀察**：移除 mutation 間 search 後的 Chrome 輸出 ODT 從 20,137 bytes 增至 24,838 bytes；12 個
  Unicode 案例與 clipboard 均存在，只有第一筆 composition `臺灣合成-R7` 被下一筆 `臺灣文件測試` 取代。
- **推論**：第一次 LOK paste 後仍有可被下一次 paste 取代的 selection；host 不能把「commit 完成」推論成
  caret 一定已 collapse。後續 sequential commits 可累積，表示不是一般的每次 insert 都互相取代。
- **修正**：composition commit 完成後，以既有公開 `click()` 明確放置 caret，再開始其他獨立 commit；
  cancel/not-found 與所有正向 search 保持在最後執行。
- **證據**：24,838-byte ODT、browser JSON 與 process samples保存於
  `findings/evidence/sdk-r7/discovery/attempt-3/`。

### 已完成單位：R7-A automatic matrix、desktop round-trip 與回歸

- **已觀察**：host 在 composition commit 後以公開 `click()` 明確放置 caret；Chrome／Firefox 最終頁面
  均 `pass:true`、`PARTIAL_GO`。兩份輸出 ODT XML 所有預期 Unicode 均各存在，cancel anchor 不存在。
- **已觀察**：desktop LibreOffice 26.2.4.2 將 Chrome／Firefox 輸出 ODT 轉為有效 1-page PDF；PDF 分別
  107,222／107,088 bytes。
- **已觀察**：Chrome 171 筆 process samples，PSS 約 279→323 MB、peak 2,273 MB；Firefox 62 筆，PSS
  約 503→850 MB、peak 1,748 MB。Firefox 變化位於預註冊 10-cycle warmup，尚不能判定 plateau 或 leak；
  R7-D 不得跳過 50-cycle正式 blocks。
- **已觀察**：R5 SDK 9/9、Provider 11/11、profile Python 2/2；R6 reader shell 11/11、contract domain／HTTP
  24/24 與 R6 release gate 全通過。R7 after-preflight `pass:true`，core/artifact 未漂移。
- **判定**：R7-A automatic **PARTIAL GO**；`finalDecision=PENDING_MANUAL`，等待 headed Chrome／Firefox
  Chewing commit/cancel 與 user-gesture clipboard evidence。

### Chrome headed manual attempt 1：真 Chewing 成立，但前一 commit 未保留

- **已觀察**：operator 提供的 Chrome 150 evidence 中，Fcitx5 Chewing 的 `compositionstart`、多筆
  `compositionupdate` 與 `beforeinput(insertCompositionText)` 都是 `isTrusted:true`；注音 preedit 序列與
  候選字變化完整。Chrome 暴露的 `compositionend` 為 `isTrusted:false`，但它前面的整段 user event chain
  是 trusted，因此記為 browser event 特性，不能誤標成全 synthetic。
- **已觀察**：cancel probe 的 final data 為空、request delta 0；native paste `isTrusted:true`；Clipboard API
  write/read、單次 commit 與 anchor search 通過。
- **驗證器錯誤**：兩筆 newline commit 被 public search 判 not found；newline 本來就不適合作 search anchor，
  應由 saved ODT 驗證，不能使 manual gate false。
- **內容失敗**：`開始中文輸入` 與後續 `測試取消輸入` 在 final search 不存在，後續較短 composition／
  clipboard anchors 存在。這是真內容保留失敗，不能被 newline false-negative 掩蓋。
- **推論**：manual harness 每筆 commit 後都在相同 twips 座標 click，可能被 LOK 視為連續 multi-click 而留下
  selection，使下一次 paste 取代前文；尚未證實為根因。
- **下一個區分測試**：caret placement 改為兩個不同座標交替，newline 從 search gate 排除，只再做一次乾淨
  Chrome run；若仍遺失，依 R7-A composition loss 停止條件建立 finding。
- **證據**：`findings/evidence/sdk-r7/discovery/input/chrome-manual-attempt-1.json`。

### Chrome headed manual clean rerun：GO for browser slice

- **已觀察**：使用不同 twips 座標交替放置 caret 後，兩筆獨立 Chewing composition
  `第一筆中文輸入`／`第二筆中文輸入` 均保留且 final search found；revision 0→1→3 單調前進，中間一筆
  trusted newline 另由 save 保留，不再錯用 search 驗證。
- **已觀察**：trusted composition start/update/beforeinput、cancel trusted preedit＋空 commit＋零 mutation、
  trusted native paste、Clipboard API write/read、Unicode search、21,786-byte ODT save 均通過。
- **已觀察**：Chrome／Fcitx 的 compositionend trust values 仍只有 `false`；因同一 composition 的 start、
  update 與 insertCompositionText beforeinput 均為 trusted，保留為 browser-specific event observation。
- **判定**：Chrome headed slice `pass:true`。前一次固定座標內容取代屬 harness caret policy 問題，失敗 evidence
  不刪除；R7-B 正式 host 必須採明確 caret placement，不可假設 paste 後 selection 已 collapse。
- **證據**：`findings/evidence/sdk-r7/discovery/input/chrome-manual-pass.json`。

### Firefox headed manual attempt 1：IME／paste 通過，Async Clipboard read 被拒

- **已觀察**：Firefox 152／Fcitx5 Chewing 的 composition start/update/beforeinput/end 均為 trusted；兩筆
  `第一筆中文輸入`／`第二筆中文輸入` 均 commit 且 final search found。cancel probe 為 trusted preedit、空
  compositionend、request delta 0；原生 Ctrl+V paste 為 trusted 且 Unicode anchor found。
- **失敗嘗試**：`navigator.clipboard.writeText()` 通過，但後續 `readText()` 回傳 `NotAllowedError: Clipboard
  read operation is not allowed.`，commit delta 0；因此本輪 `pass:false`。拒絕後未誤送 mutation，沒有觸發
  R7-A「clipboard denied 後仍 mutation」停止條件。
- **已觀察**：正式中文 composition 前已有 `2`、`u`、`4`、`u`、空白五筆 trusted `insertText`，推定為輸入法
  尚未切換成功時的按鍵；雖然內容都能搜尋到，clean rerun 應排除以免混淆 fixture。
- **外部契約確認**：Mozilla MDN 記載 Firefox 的 clipboard read 不採 Chromium 持久 permission；在 transient
  activation 下可能顯示暫時性的 Paste context menu，約一秒後可選。未由 operator 確認該 prompt 前，不把
  `NotAllowedError` 歸因於 SDK、adapter 或文件 mutation。
- **下一個區分測試**：乾淨 reload；先確認 Chewing 已啟用，再進 manual session。寫入 fixture 後按 read，等待
  Firefox 的 Paste／貼上暫時選單啟用並明確點選，再 verify。不得啟用 `dom.events.testing.asyncClipboard` 或其他
  繞過安全檢查的測試偏好。
- **證據**：`findings/evidence/sdk-r7/discovery/input/firefox-manual-attempt-1.json`。

### Firefox headed manual clean rerun：GO for browser slice

- **已觀察**：operator 在不修改 Firefox 安全偏好的前提下，於 `readText()` 所觸發的暫時性 Paste 授權選單
  明確確認後，Clipboard API read 成功；fixture 只 commit 一次、anchor found，write/read 皆 passed。
- **已觀察**：clean rerun 無先前 `2/u/4/u/空白` 雜訊；兩筆真實 Chewing composition、cancel trusted preedit
  且 request delta 0、trusted native paste、四個 searchable anchors 與 22,438-byte ODT save 全部通過。
- **判定**：Firefox headed slice `pass:true`。第一次 `NotAllowedError` 是未完成 Firefox per-operation Paste 授權，
  不是 SDK／adapter mutation 失敗；拒絕路徑與允許路徑的 evidence 都保留。
- **證據**：`findings/evidence/sdk-r7/discovery/input/firefox-manual-pass.json`。

## R7-A 最終整合：PARTIAL GO

- **機器判定**：`tools/validate_r7_a.py` 已將 Chrome／Firefox manual raw evidence 納入 release gate；兩端
  browser／artifact／Chewing、expected commits、revision monotonic、trusted composition、cancel zero mutation、
  native paste、clipboard write/read、search 與 output 共 14 項檢查皆通過。Machine summary 為
  `automaticDecision=PARTIAL_GO`、`manual.status=passed`、`finalDecision=PARTIAL_GO`、`pass:true`。
- **測試**：R7-A input adapter 5/5、corpus unit 2/2 與 JS/Python static checks 通過；R5 SDK 9/9、Provider
  11/11、profile 2/2；R6 reader 11/11、collaboration domain＋HTTP 24/24、R6 release `GO` 全通過。
- **工作區保護**：after-preflight `pass:true`；core HEAD 仍為
  `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，五筆 tracked dirty＋一筆 untracked 文件與進場完全一致；
  `writer-review` loader／WASM／resources 未漂移，未 rebuild、未修改 LibreOffice core。
- **最終判定**：R7-A **PARTIAL GO**。ODT、輸入、clipboard、typed negative、desktop round-trip、10-cycle
  lifecycle 與 3-crash recovery 可進下一階段；部分 GO 原因是 finding 013 的 DOCX public open unsupported。
  Firefox warmup PSS 只作 R7-D 風險輸入，不在 R7-A 宣稱 leak 或無 leak。
- **後續**：依順序可規劃 R7-B；R7-B 尚未獲本輪變更授權，開始前需列出確切檔案、命令與產物等待確認。

## 2026-08-03：R7-B input／clipboard 正式執行

### 已完成單位：bounded host input 與 clipboard typed contract

- **已觀察**：host adapter 增加 8 筆 queue ceiling、`idle/composing/committing/blocked/recoverable-error`
  狀態、composition ID、stale/teardown queue invalidation 與 `INPUT_BACKPRESSURE|INPUT_BLOCKED|INPUT_CANCELLED|
  INPUT_COMPOSITION_MISMATCH`；被取消的 queued mutation 不會在恢復後重送。
- **已觀察**：plain-text clipboard adapter 將 browser 拒絕分類為 `CLIPBOARD_DENIED|CLIPBOARD_UNAVAILABLE`，
  沒有 user gesture、空內容與非 `text/plain` 都是零文件 mutation；HTML＋plain 只提交 plain。
- **測試**：input／clipboard Node contract 14/14 通過，JS/Python static checks 通過。

### Firefox automatic attempt 1：長 phrase 被後續輸入插入其中

- **已觀察**：Chrome 三次正式 R7-B synthetic run、ODT XML exact-count 與 desktop PDF 全通過。Firefox 三次
  browser run 的 12 次 SDK mutation與 revision 0→12 均完成；cancel、backpressure、stale queue、blocked、
  clipboard denied／unsupported與 desktop PDF均通過，但長 phrase exact search/ODT count失敗。
- **原始內容**：Firefox ODT 不是刪除長 phrase，而是將後續 `😀👨‍👩‍👧‍👦` 插入 phrase中段；所有 code points
  仍在文件內。三次結果一致，已保存於
  `findings/evidence/sdk-r7/browser/input/firefox/attempt-1/`。
- **推論**：Reference App在每次 commit後交替點擊固定 twips；Firefox版面上的該座標後來落入已插入的長
  phrase，使後續文字在 phrase內插入。這是 host caret placement測試編排問題，不是 SDK silent text loss，
  但仍不符合 phrase完整性 gate，不能計通過。
- **失敗嘗試 2**：只在第一筆 commit 後 collapse caret 仍會使後續 phrase 插入既有內容；完整 raw evidence
  保留於 `findings/evidence/sdk-r7/browser/input/firefox/attempt-2/`，未以最終成功覆蓋。
- **最終修正**：每次 commit 後以公開 `click()` 把 caret 放到文件末端附近的兩個不同位置，避免固定位置落入
  新增 phrase。Chrome／Firefox 各 3/3 synthetic run、exact ODT anchor count與 desktop PDF均通過。
- **階段狀態**：R7-B automatic 已通過；集中 headed Chewing／Cangjie／Pinyin、clipboard、keyboard evidence
  尚未執行，因此 `input-summary.json` 保持 `PENDING_MANUAL`，未冒稱 GO。

## 2026-08-03：R7-C corpus／Reference App 實作

- **已觀察**：建立 28 份 frozen L0～L4 corpus、manifest與無第三方依賴的 ODT ZIP preflight；L3 negative
  對 unsupported／corrupt／too-large 使用 typed error，DOCX 依 finding 013 明確拒絕，不使用任意路徑。
- **已觀察**：L4 `l4-stress-100.odt` 含 100 個 page anchor 與重用 PNG，SHA-256
  `ae648d6bae96d82ce6636434c9dbba3ec75af07489a59b9fcce4c7af07f5e2ef`；corpus validator 28/28 通過。
- **已觀察**：R7-C app以全新 Worker逐檔 preflight、open、首／中／末 tile、search、comments／tracked changes、
  revision-guarded mutation與 ODT save；不解析 raw callback、不用 UNO／unoembind。
- **測試**：R7 corpus Python 2/2、R7 JS 7/7與所有 Python／JS static checks通過。
- **狀態**：依 R7-B→C 順序，B manual gate 未完成前未啟動正式 C browser matrix；後續又因 R7-D deterministic
  stop而不再耗時執行，故 R7-C 沒有 GO／部分 GO 判定。

## 2026-08-03：R7-D usability／longevity 與停止判定

### 已完成單位：host usability 與 longevity instrumentation

- **已觀察**：page/location adapter 明確標示 approximate hint；first／previous／next／last clamp通過 3/3 unit。
  hyperlink只允許 `http:`／`https:`／同文件 bookmark，拒絕 `javascript:`、`file:`、macro與未知 scheme。
- **已觀察**：Chrome CDP AX tree與 Firefox DOM/WebDriver usability smoke均通過 control name、role/status、focus、
  page intent、zoom、search與安全 hyperlink policy；文件內容 accessibility仍明確為 unsupported。
- **已觀察**：新增 S1～S5 harness、process-tree RSS/PSS sampler、50-cycle block median／Theil-Sen slope分析，
  WASM／JS／tile缺值保持 `unavailable` 而非補 0；分析單元 4/4 通過。
- **smoke**：Chrome S1 100頁 open/render/search/save/close、S3四個 crash barrier、S4三個短 interval＋三次 restart
  均通過。這些是 harness diagnostic，不取代規格要求的正式 3-run／50-cycle／20-crash／30-minute矩陣。

### 失敗嘗試與最小化：finding 012 擴大為 normal close

- **第一個已觀察失敗**：t2 `render + listComments + search + close` 在 Chrome完整 180秒 timeout；文件 handle
  `closed=0`，只有 `engine.dispose()` 終止 Worker，未把強制終止計為 close pass。
- **區分測試**：全新 Worker分別測 `open`、`render`、`search`、`reader(render+search)`、`comments`與
  `semantic(render+comments+search)`；六個 10秒 close全 timeout，否證「只有 queue/cancel組合才觸發」。
- **最小重現**：純 `open → close` 使用凍結 180,000 ms上限，Chrome 150（open約523 ms）與 Firefox
  153.0.1（open約351 ms）都得到 `SdkTimeoutError/TIMEOUT`；兩端各保存176筆 process sample。
- **已觀察**：artifact/core完全未變；loader SHA `35d96f…3566`、WASM SHA `ba257b…dfc6`、fixture SHA
  `0f6990…8d31`。跨瀏覽器摘要見
  `findings/evidence/sdk-r7/longevity/finding-012-audit/summary.json`。
- **推論**：觸發不需要 render、comments、search或cancel；可能在 t2內容 teardown或 SDK Worker close路徑，
  尚不能歸因至 LibreOffice core。
- **待驗證**：逐步移除 t2 styles／table／image／comment以找最小物件，並以 native LOK區分 core與 Worker；
  不能以 raw callback／UNO或修改 core假裝修復。

### R7 最終執行判定：STOP

- `SPEC-R7-D` 明定 normal close反覆 timeout即停止。Chrome／Firefox純 open→close均在完整上限重現，故
  R7 判定 **STOP**，finding 012升級為阻斷。
- 正式 S1～S5長矩陣、R7-C formal matrix與集中 headed三輸入法／keyboard／Orca均未再執行；它們無法改變
  deterministic stop，省略人工驗收符合「人工次數降到最低」，不是把 pending項目計為 pass。
- Machine result：`findings/evidence/sdk-r7/summary.json`；R7-A維持既有 PARTIAL GO，R7-B只記 automatic pass／
  manual pending，R7-C只記 implemented-not-run，R7-D與整體 R7為 STOP。

## 2026-08-03：finding 012 第一階段 feature 最小化

### Corpus與方法

- **已觀察**：以t2 byte-identical source建立table／image／annotation／page-break的2⁴=16種ODF package組合；
  變更只在ZIP/XML層移除對應元素與manifest relationship，不使用UNO、raw SDK callback或core修改。
- **已觀察**：16/16通過ZIP CRC、所有XML解析、feature presence assertions與desktop LibreOffice PDF；原始variant
  SHA仍為`0f699060…8d31`，embedded PNG為640×360 RGB、SHA `f2e18c7c…f57f`。
- **工具**：`create_finding_012_corpus.py`、專用allowlist close minimizer、跨瀏覽器runner與boundary validator；
  corpus unit 3/3及R7完整static chain通過。

### 10秒分類結果

- **Chrome已觀察**：8個含image組合全timeout；8個不含image組合全close-pass。table、annotation、page break
  單獨或彼此組合都不觸發。
- **Firefox已觀察**：與Chrome 16/16逐項完全相同，沒有divergent或flaky結果。
- **推論**：在四個預註冊控制變因內，image presence是必要且充分的觸發特徵；尚不能把它等同於PNG decoder
  或core bug。

### 完整180秒邊界確認

- **成功側**：保留table＋annotation＋page break、只移除image。Chrome 3/3 close 18.55～22.81 ms；Firefox
  3/3 close 7.54～8.08 ms。
- **失敗側**：在成功側加入原始embedded image，也就是byte-identical t2。Chrome 180000.42 ms、Firefox
  180005.28 ms均`TIMEOUT`，各保留約175／170筆process samples並明確記forced Worker termination。
- **Machine判定**：`MINIMIZED`、`candidateTriggerFeatures=["image"]`，證據位於
  `findings/evidence/012/r7-minimization/summary.json`。
- **待驗證**：下一階段需分解frame／relationship／PNG bytes與尺寸／anchor，再決定是否需要diagnostic-only
  artifact或native LOK重現；本階段沒有修改、relink或替換`writer-review`。
- **新增反例**：L4 100頁stress ODT使用完全相同PNG SHA、`as-char`／onLoad relationship，且S1已正常
  render/save/close；因此PNG bytes與一般embedded-image能力不是充分條件。後續優先分解t2特有的`fr1`
  graphic style、paragraph wrapper、mime attribute、name/z-index與frame geometry。

## 2026-08-03：finding 012 第二階段 image-object 軸最小化

### Corpus、失敗嘗試與驗證

- **已觀察**：以byte-identical t2為控制，建立9份image-axis ODT，分解`draw:mime-type`、style reference、
  name/z-index、clip、全部graphic properties、直接paragraph wrapper與L4 geometry/frame形狀；所有變體保留
  相同embedded PNG SHA `f2e18c7c…f57f`。
- **失敗嘗試**：第一次desktop batch執行時，9份ZIP/XML驗證通過，但本機LibreOffice IPC在受限執行環境不可用，
  因而得到9份desktop validation false；保留該失敗，不把它解讀為ODT失敗。改在可使用既有desktop環境重跑後
  9/9均成功產生PDF。
- **測試**：corpus／selector單元6/6、Finding 012 static chain、JavaScript／Python靜態檢查與R7 after-preflight
  全部通過；core HEAD、既有dirty現場與R5 `writer-review` artifact hash前後一致。

### 跨瀏覽器結果

- **已觀察**：Chrome／Firefox的9份10秒分類逐項一致。只有移除image frame直接外層`text:p`的
  `t2-image-unwrapped`為close-pass；原始t2與其餘7種單軸變體全部timeout。
- **已觀察**：完整180秒確認中，unwrapped在Chrome 3/3 close 18.22～20.80 ms、Firefox 3/3 close
  6.60～9.74 ms；byte-identical原始t2在Chrome 180000.41 ms、Firefox 180000.90 ms仍timeout。
- **Machine判定**：`MINIMIZED`、`candidateTriggerAxes=["frame.wrapper"]`；證據位於
  `findings/evidence/012/r7-image-axis/summary.json`。

### 推論、待驗證與判定

- **推論**：已排除PNG bytes、mime、style reference、name/z-index、clip、graphic properties與geometry各自為
  充分條件；最小公開可觀察邊界是image frame作為`text:p`直接子節點，或該wrapper與image／anchor teardown的
  交互作用。
- **待驗證**：仍未區分ODF import、native LibreOfficeKit、WASM core teardown與專案Worker close queue；本階段
  沒有建立diagnostic artifact、修改core或以強制終止取代public close。
- **判定**：第二階段完成且不需人工驗收；Finding 012仍未修復，所以R7維持`STOP`。

## 2026-08-03：finding 012 第三階段 native／WASM 層級歸因

### 方法與隔離性

- **已觀察**：系統已有LibreOffice 26.2.4、native compiler、Emscripten、既有linkdeps與filesystem image；
  不需root、新依賴或core rebuild。
- **實作**：新增以公開LibreOfficeKit C API執行load／document destroy的native probe；另建
  `finding-012-diagnostic` WASM profile，只在document destroy前後發出stage。production路徑預設不啟用，
  R5 loader／WASM SHA前後不變。
- **失敗嘗試**：第一次整批Makefile patch因測試target上下文不符而完全拒絕，沒有留下部分修改；改依實際段落
  拆分後，dry-run、建置與static checks通過。
- **測試**：歸因validator單元4/4完成RED→GREEN；Finding 012與完整R7 static chain、before／after preflight
  均通過。瀏覽器原始紀錄與process samples位於`findings/evidence/012/r7-attribution/`。

### 已觀察

- **Native control**：LibreOfficeKit 26.2.4對byte-identical原始t2與unwrapped各3/3都出現
  `document-destroy-enter`與`document-destroy-return`並正常結束，完整程序約243～269 ms。
- **Diagnostic WASM**：Chrome 150與Firefox 153.0.1的原始t2在10秒分類及180秒確認都只出現
  `document-destroy-enter`，沒有return；unwrapped在兩browser各3/3有enter／return並正常close。
- **Machine判定**：`DOCUMENT_DESTROY_BOUNDARY_CONFIRMED`；Chrome／Firefox皆為
  `WASM_DOCUMENT_DESTROY_BLOCKED`，system native為`NOT_REPRODUCED_SYSTEM_NATIVE`。

### 推論、待驗證與判定

- **推論**：Worker與engine command queue確實派送close，阻塞位於same-commit WASM
  `LibreOfficeKitDocument::destroy()`呼叫內或其下層；不是SDK等待一個從未排入queue的close。
- **待驗證**：system native版本較舊，不能用其反例排除26.8 core regression；仍需same-commit native LOK build
  區分core版本變更與Emscripten特有teardown，也尚未定位destroy內部的具體subsystem。
- **判定**：第三階段完成且無需人工驗收；public close仍未修復，R7維持`STOP`。

## 2026-08-03：finding 012 第四階段 same-commit native 最終歸因

### Build與保護

- **已觀察**：以detached worktree固定`671c848b1bb8…`，在獨立builddir使用`CPLinux-LOKit` headless設定；
  關閉LTO、symbols、runtime Python與package generation，使用既有external tarball cache，未安裝依賴或修改core。
- **人工接手點**：configure checkpoint通過後，長時間`make -j8`由operator手動增量完成，exit 0；完整
  configure／build log均保存在`findings/evidence/012/native-26-8-attribution/`。
- **產物**：runtime回報`LibreOffice 26.8.0.1.0 671c848…`；validator保存autogen、config、logs與
  `libmergedlo.so`的size／SHA，detached source完成後仍clean。

### 失敗嘗試與控制

- **受限環境失敗**：第一次runner中原始與unwrapped都已依序出現document destroy enter／return／complete，
  隨後受共同執行環境限制影響而非零結束；兩份結果完全一致，不能解讀為Finding 012重現。
- 該輪原始證據保存在`native-sandbox-failed/`。相同probe、runtime與fixtures在可用環境重跑，6/6正常，
  沒有刪除或覆蓋失敗嘗試。

### 已觀察、推論與決策

- **已觀察**：same-commit native原始t2與unwrapped各3/3均有`document-destroy-enter`、
  `document-destroy-return`、`complete`並正常結束；WASM Chrome／Firefox則只對原始t2卡在enter。
- **推論**：同commit native不重現，排除LibreOffice 26.8 core版本本身為充分條件；結合Worker queue已排除，
  最終候選層級為Emscripten組態／runtime特定的document teardown。
- **Machine判定**：`EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY`、candidate layer
  `emscripten-document-teardown`、next action `wasm-fix`。
- **判定**：Finding 012歸因在第四階段結束；後續改為R7 remediation，不再新增finding診斷階段。public close
  尚未修復，因此R7目前仍`STOP`。

## 2026-08-04：Finding 012 remediation與R7最終矩陣

### Bounded close recovery

- **已觀察**：Document SDK加入10秒`closeRecoveryTimeoutMs`。只有`SdkTimeoutError`會啟動recovery；Abort仍是
  typed failure，不會假稱close完成。recovery先發`document-close-recovery-started`，終止擁有該handle的Worker，
  建立新generation後發`document-close-recovery-complete`；舊handle維持stale，不自動重送mutation。
- **測試**：SDK unit 11/11；原始t2在Chrome／Firefox各3/3使用bounded recovery完成close，Worker created=
  terminated、active handle/Worker皆0，engine可再開文件。R5 loader／WASM完全未重建，hash不變。
- **推論**：產品生命週期已從無限等待改成bounded recovery；但Emscripten document destroy沒有回傳，底層
  root cause仍存在。這是SDK containment，不是宣稱core teardown修復。

### R7-C相容性正式矩陣與失敗嘗試

- **失敗嘗試1**：`l1-review-odt`使用tracked-deleted `Del 16`當selection anchor；search可命中但public selection
  text為空。改用唯一可見`Lorem ipsum`後通過。這是fixture assertion錯誤，不是內容loss。
- **失敗嘗試2**：`l3-ratio-limit`原1 MiB payload實際ZIP ratio約61，未超過預註冊200。改為8 MiB後ratio約337，
  typed `DOCUMENT_TOO_LARGE` gate才真正成立；manifest hash與生成理由同步更新。
- **失敗嘗試3**：Firefox在同頁建立第4個大型WASM engine後init／paint timeout。先切2-document batches，
  又在快速啟動第15個Firefox session時WebDriver navigation卡死；固定冷卻仍在第13次啟動重現。
- **解法與已觀察**：每個logical group只用一個Firefox process，batch間切新page context，每頁Worker budget=3；
  aggregate驗證exact case IDs、hash、輸出ODT與desktop PDF，未減少case。Chrome repeat3＋full1、Firefox
  repeat3＋full1全部通過；desktop baseline、fidelity與DOCX typed unsupported六項gate為true。
- **判定**：`PARTIAL_GO_ODT_FIRST`；DOCX依finding 013保持unsupported。

### R7-D正式矩陣與Finding 014

- **Chrome已觀察**：S1 3/3、S2 reuse/fresh各50、S3 20、S4 30分鐘、S5 normal/known全通過。
- **Firefox已觀察**：S1 3/3、S2 reuse 50、S4 30分鐘、S5 normal/known通過；Finding 012不再觸發STOP。
- **Firefox失敗嘗試**：S2 fresh原始單頁完成33 cycles後第34個init 120秒timeout；同process切page context
  完成37後仍timeout；10-cycle／process分批完成37後timeout；5-cycle／process最終完成35後，第8個process
  首次init timeout。10-cycle分批失敗raw evidence已另存attempt目錄，最後5-cycle結果保留在正式run。
- **Firefox S3**：20次crash event都被觀察；前19次recovery、stale rejection與no-replay通過，第20次recovery
  init timeout。已完成cycle的active Worker／handle歸零。
- **推論**：reuse 50與30分鐘soak通過、PSS沒有無界趨勢，因此不是已證明的公開handle leak；候選為Firefox／
  Emscripten／大型WASM instance反覆初始化的process或系統資源耗盡。建立finding 014，不再靠更碎分批假裝
  長壽單工作階段能力。
- **待驗證**：以同pthread／memory設定的非LibreOffice最小WASM重現、Firefox process map/thread high-water、
  Snap與非Snap／ESR比較，以及產品可觀測Worker-generation budget。
- **判定**：R7-D部分GO。一般閱讀、reuse、30分鐘、S5及Chrome完整壓測可用；Firefox fresh-engine／crash-storm
  不列為完整能力，host應優先reuse並在generation budget前要求reload。

### 輸入、人工負擔與最終判定

- R7-B automatic Chrome／Firefox各3/3；沿用R7-A兩瀏覽器Fcitx5 Chewing真實composition／cancel、trusted
  paste、Clipboard API與ODT輸出。Cangjie／Pinyin未收集，明列限制，不增加operator驗收。
- 自動usability兩瀏覽器通過；完整headed keyboard／Orca、document-content accessibility與hyperlink activation
  未驗證或缺公開能力，維持safe fallback。
- **R7總判定：`PARTIAL_GO_ODT_FIRST`**。不使用raw UNO、unoembind、任意`.uno:*`、last-write-wins或未承諾
  callback補洞。

### 回歸與工作區保護

- SDK 11/11、Provider 11/11、R6 reader 11/11、R6 collaboration domain／HTTP 24/24、R7 input 14/14、
  R7 compatibility／longevity unit、Finding 012 remediation unit與所有static checks通過。
- R6 round-trip及release validator仍為GO，R1～R5 regression為true；R7 after-preflight通過。
- Core HEAD仍為`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，原有5筆tracked dirty與1筆untracked文件原樣保留。
- R5 loader SHA仍為`35d96f…c63566`，WASM SHA仍為`ba257b…dfc6`。外層／probe不是Git repository，無commit可切。

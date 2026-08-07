# SPEC R7-D：Viewer 可用性、accessibility spike 與長時間穩定

> **日期**：2026-08-02  
> **狀態**：完成（**仍為部分 GO，但理由已剩一項**）。~~Firefox Worker generation受finding 014限制~~
> ——該限制 2026-08-08 撤回：正式九輪矩陣以修好的 harness 重跑**全數通過**（見§10.3）。
> 部分 GO 現在**只**掛在 document-content accessibility／完整 headed keyboard／Orca 未收集，
> 與 longevity 無關。  
> **上層規格**：[SPEC R7-000](./SPEC-R7-000-overview.md)  
> **前置閘門**：[R7-A](./SPEC-R7-A-discovery-corpus.md) memory門檻已凍結；
> [R7-B](./SPEC-R7-B-input-clipboard.md) 已完成並留下判定；
> [R7-C](./SPEC-R7-C-document-compatibility.md) L4 fixture單次流程通過

## 1. 目標

確認R6 reader shell從「可自動操作」提升到基本可使用，並在100頁含圖片與長時間Worker lifecycle下維持
正確version/revision、可復原狀態與有界memory。R7-D是spike，不宣稱完整Web Writer accessibility。

## 2. Usability 最小範圍

### 2.1 鍵盤與focus

- 所有host controls可用Tab／Shift+Tab到達，順序與視覺排列一致；有可見focus indicator。
- Search、zoom、page location、reload、download、input sink與error recovery都有可讀label／快捷鍵說明。
- Enter／Space只觸發focused control一次；長按、composition或Worker busy時不重複mutation。
- modal／error region不劫持focus；reload後focus回到可預期control，不落到已銷毀canvas。
- canvas viewport本身不是假textarea；輸入由R7-B host sink承接。

### 2.2 Status 與 accessibility tree

- document ID／version、SDK revision、page/location hint、loading／ready／stale／recoverable-error與next action
  都有DOM文字，不只用顏色或canvas像素。
- 動態狀態使用適量`role=status`／`aria-live`，避免每張tile完成都干擾screen reader。
- Chrome以CDP accessibility tree、Firefox以DOM/WebDriver assertions驗證name／role／state；Orca只做headed
  人工spike並標manual，不以單一screen reader代表完整相容。
- 文件內文字、caret與semantic reading order若沒有公開SDK資料，明確標`document-content-accessibility:
  unsupported`；不得OCR canvas或解析raw callback來假裝支援。

### 2.3 Page/location

- 顯示viewport推算的page/location時必須標為hint；不能把固定像素高度誤稱永久page ID。
- 提供first／previous／next／last page intent；adapter以R7-C凍結的document dimensions與manifest page landmarks
  驗證移動，不超出邊界。
- 搜尋命中後若公開geometry不可用，只顯示selection與「命中但無法精確捲動」；不解析opaque rectangles。
- zoom／scroll／page intent共用R6 generation scheduler，舊tile不得覆蓋新位置。

### 2.4 Hyperlink spike

- 使用R7-C hyperlink ODT／DOCX fixture探測公開SDK是否有安全的target與activation intent。
- 若沒有公開target／geometry，UI可以將hyperlink標為`unsupported`或只由外部manifest列示已知fixture link；
  不讀raw LOK callback、不從畫面OCR、不猜座標。
- 若建立窄capability，回傳值只能是已驗證URL／internal bookmark與same-document revision；外部navigation需
  user gesture、scheme allowlist與明確確認。`javascript:`、`file:`、macro與未知scheme拒絕。
- R7-D部分GO可接受hyperlink activation未成立，但不得出現無提示外部navigation。

## 3. 100頁與stress fixture

L4 fixture由R7-C generator建立，至少：

- 100頁，每頁固定heading、唯一page anchor、數段CJK／Latin與一張自有PNG；
- 圖片採有限數量可重用asset，manifest同時記logical image count與ZIP entry count；
- 首／中／末頁以及跨page search anchors；
- desktop LibreOffice頁數與PDF baseline；
- bytes、expanded ZIP、pixel count與page count均低於R7-A凍結上限。

不得用無界隨機內容製造壓力；同一seed可重建semantic等價fixture，hash變更需記LibreOffice版本與原因。

## 4. Lifecycle scenarios

### S1：單次大文件閱讀

- cold open、first tile、first／middle／last page、100%／150% zoom、CJK／Latin search、download與close。
- 驗證tile cache ceiling、generation cancel與close後零late draw。

### S2：重複 open／render／close

- Chrome／Firefox各至少50 cycles；每cycle全新document handle，按R7-A決定同Worker reopen與新Worker兩組。
- 每10 cycles保存block summary與process snapshot；failure後保留該cycle所有log，不只跑到最後成功。

### S3：Worker crash／restart

- 至少20 cycles，在open、render queue、local unsaved、saved local bytes四個barrier輪替crash。
- 未save mutation不可恢復、不自動重送；已save bytes仍可下載；restart使用新handle／tile generation。

### S4：30分鐘soak

- 每分鐘執行有界scroll／zoom／search序列，固定間隔採memory、Worker、tile、latency sample；注入3次Worker
  crash與明確restart。
- 不以`setInterval`堆積重疊工作；下一輪只在上一輪完成或typed timeout後開始。

### S5：finding 012 audit

- t2 normal reader sequence與已知discovery sequence分開各跑；記錄close stage、pending request、Worker
  termination與memory。
- 若normal產品流程也出現close timeout或長時間資源不釋放，finding 012升級為R7阻礙；不能只以強制kill
  計為pass。

## 5. Memory 方法與預註冊閘門

R7-A在正式run前將數值寫入machine-readablethreshold file；至少包含：

```ts
type LongevityThresholds = {
  browser: "chrome" | "firefox";
  sampleIntervalMs: number;
  warmupCycles: number;
  blockSize: number;
  cycleCount: number;
  maxPostCloseGrowthBytes: number;
  maxPostCloseGrowthRatio: number;
  maxBlockMedianSlopeBytes: number;
  maxWasmHeapStepBytes: number;
  maxWorkersAfterClose: number;
  openTimeoutMs: number;
  closeTimeoutMs: number;
};
```

量測規則：

- `psutil`聚合runner啟動的browser process tree；能讀時另存`/proc/<pid>/smaps_rollup` PSS。其他session的
  Chrome／Firefox不可混入。
- browser RSS/PSS、WASM heap size／sbrk、JS heap、tile cache bytes分欄；缺指標標`unavailable`，不可用0補。
- WASM linear memory通常不縮小，所以判斷plateau／block growth，不要求回到cold baseline。
- 比較warmup後首／末block median、robust slope與每cycle failure；GC可在diagnostic run記錄但不可依賴非產品
  強制GC才通過。
- process退出後允許有界browser cache，但Document Worker／document handle／tile buffer count必須回到
  threshold；zombie／持續增加的Worker直接fail。
- threshold在正式evidence產生後不可放寬；若instrumentation錯誤，保留失敗資料、修正方法並開新run ID。

**無界成長判定**：超過預註冊absolute或relative post-close growth、連續三個block median同方向超過允許
slope、WASM heap在後半每block持續step-up、或Worker/tile count不回落，任一即fail並建立finding。

## 6. Browser／manual matrix

- Chrome／Firefox：S1各3次；S2／S3／S4各至少1次完整run；S5 normal與known sequence各1次。
- Accessibility automated：兩browser的DOM name／role／state／focus assertions；Chrome另存AX tree。
- Headed manual：兩browser各1次純鍵盤流程；Orca至少1個browser做status／control announcement spike。
- Hyperlink：安全target、blocked scheme與無public-capability fallback各至少1個deterministic fixture。
- 所有run記錄browser PID tree、版本、session type、artifact/resource hashes與corpus hash。

## 7. Evidence

```text
findings/evidence/sdk-r7/browser/usability/<browser>/
findings/evidence/sdk-r7/manual/accessibility/
findings/evidence/sdk-r7/longevity/<browser>/<scenario>/
findings/evidence/sdk-r7/longevity/thresholds.json
findings/evidence/sdk-r7/longevity/summary.json
```

每個longevity sample至少含monotonic time、scenario/cycle/block、process IDs、RSS/PSS、WASM／JS／tile memory、
document version/revision、Worker/handle count、open/render/close latency與typed error。process termination與
forced kill分開計數。

## 8. 驗收與判定

**GO**：host controls在Chrome／Firefox可全鍵盤操作且DOM accessibility狀態正確；page/location不誤標、
hyperlink安全處理或明確unsupported；100頁功能流程通過；50-cycle、20-crash與30-minute soak在預註冊
threshold內，無zombie Worker／late draw／錯version；finding 012不影響normal產品流程。

**部分 GO**：閱讀、鍵盤、page hint與longevity通過，但document-content accessibility、Firefox AX細節或
hyperlink activation缺少公開能力。保留安全fallback與unsupported標示，不能宣稱完整accessibility／link。

**停止回報**：normal close反覆timeout、memory無界、Worker／tile累積、crash後錯handle／錯version、
unsaved mutation自動重送、keyboard一次觸發多次mutation、外部link無user gesture開啟，或需raw callback／
UNO／OCR才完成。保存process samples、event trace、tiles與失敗bytes，建立finding。

## 9. 交付物

- keyboard/focus/status/page/hyperlink spike與自動／人工evidence。
- 100頁deterministic fixture與desktop baseline。
- 預註冊memory threshold、process/WASM/tile samples與longevity summary。
- finding 012 audit結果與任何新memory／accessibilityfinding。
- 提供R8 delivery/font與R10 reachability/size工作的實際corpus與high-water輸入。

## 10. 執行結果

- R7-A threshold已原樣複製至`findings/evidence/sdk-r7/longevity/thresholds.json`，未在結果後放寬。
- Usability diagnostic：Chrome CDP AX tree與Firefox DOM/WebDriver均通過host control name／role／focus、
  page hint、zoom、search與安全hyperlink fallback；document-content accessibility維持unsupported。
- Longevity harness diagnostic：Chrome S1、四種S3 barrier與短版S4皆通過；memory analyzer以PSS優先、RSS fallback、
  block median與robust slope實作，optional metric缺值明確為unavailable。
- S5 finding 012 audit先以六種操作組合最小化，再以凍結180秒上限重跑純`open → close`。Chrome 150與
  Firefox 153.0.1均為`TIMEOUT`，closed handle為0，只能由dispose強制終止Worker。
- **判定：STOP**。這是本spec明定的「normal close反覆timeout」停止條件。未啟動正式50-cycle／20-crash／
  30-minute矩陣，也未要求headed keyboard／Orca，因它們不能推翻已成立的deterministic stop。
- 原始與摘要證據：`findings/evidence/sdk-r7/longevity-smoke/s5-minimize-open-180s/`、
  `findings/evidence/sdk-r7/longevity/finding-012-audit/summary.json`、finding 012。
- 後續finding 012第一階段以16種table／image／annotation／page-break組合最小化：兩browser的8個含image組合
  全timeout、8個無image組合全正常；最大無image邊界各3/3通過，加入image後各1/1完整180秒timeout。
  結論為`MINIMIZED`／candidate `image`，但尚未修復，故本spec與R7 STOP判定不變。
- L4以相同PNG及基本as-char/onLoad relationship正常close，故machine的`image`分類只代表t2 feature軸；
  不宣稱所有embedded image失敗。
- Finding 012第二階段以9種image-object軸分解style reference、mime、name/z-index、clip、graphic properties、
  paragraph wrapper與L4 geometry/frame。Chrome／Firefox均只有`t2-image-unwrapped`正常close，其餘含原始t2的
  8種皆timeout；完整確認為unwrapped各3/3成功、原始t2各1/1達180秒timeout。machine判定為`MINIMIZED`／
  candidate axis `frame.wrapper`，證據在`findings/evidence/012/r7-image-axis/summary.json`。
- 上述結果是ODF結構邊界，不是core／Worker根因判定，也沒有修復public close，故本spec與R7 STOP維持不變。
- Finding 012第三階段以系統native LOK與隔離diagnostic WASM做層級歸因。Native LibreOffice 26.2.4對原始t2與
  unwrapped各3/3正常；同commit diagnostic WASM則在Chrome／Firefox都對原始t2發出
  `document-destroy-enter`後180秒不返回，而unwrapped各3/3有enter／return並正常close。
- Machine判定為`DOCUMENT_DESTROY_BOUNDARY_CONFIRMED`：已排除Worker／engine queue沒有派送close，候選縮為
  WASM build或版本特定的LOK document teardown；尚無same-commit native結果，不能宣稱一般native core bug。
  證據在`findings/evidence/012/r7-attribution/summary.json`，public close仍未修復，R7 STOP不變。
- Finding 012第四階段以detached worktree建立same-commit headless native LOK 26.8。原始t2與unwrapped各3/3
  均正常進出document destroy；相同commit WASM仍只在原始t2阻塞。最終machine判定為
  `EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY`，排除core版本差異與Worker未派送，next action為`wasm-fix`。
- 第四階段是最後歸因閘門；後續工作轉為R7 remediation，不再追加Finding 012最小化階段。修復尚未完成，
  故本spec與R7 STOP判定仍不變。

### 2026-08-04 remediation 最終結果（取代上述舊STOP判定）

- Document SDK以10秒bounded Worker recycle處理Emscripten-specific document destroy timeout；原始t2在
  Chrome／Firefox各3/3 recovery close，engine可重用。S5 normal與known兩瀏覽器均通過，Finding 012不再是
  normal close停止條件；底層destroy root cause仍保留。
- Chrome正式S1 3/3、S2 reuse/fresh各50、S3 20、S4 30分鐘、S5 normal/known全部通過。
- Firefox正式S1 3/3、S2 reuse 50、S4 30分鐘、S5 normal/known通過；S2 fresh在35/50後因新Firefox
  process init timeout，S3前19個recovery通過、第20個recovery init timeout。已完成樣本沒有無界PSS成長、
  active Worker／handle歸零；建立finding 014，不宣稱完整Firefox crash-storm／fresh-engine longevity。
- host usability自動檢查兩瀏覽器通過；document-content accessibility、完整headed keyboard與Orca仍unsupported／
  未收集，安全fallback維持。
- **判定：部分 GO**。一般閱讀、reuse、30分鐘soak、S5與Chrome完整壓測成立；~~Firefox反覆建立大量大型WASM
  Worker有明確上限，產品必須優先reuse並在generation budget耗盡前要求重新載入工作階段。~~
  **（末句 2026-08-08 撤回，見 §10.3。）**

### 10.3 2026-08-08 Firefox 正式矩陣重跑：九輪全過，finding 014 的限制撤回

上面那條 Firefox 限制的成因不是瀏覽器，是我們自己的 harness——
[finding 023](../findings/023-sdk-init-wedges-at-fixed-session-depth.md) 那條沒人讀的
`serve.py` 請求 log pipe（64 KiB 滿了之後 HTTP handler 卡在送出回應**之前**）。
以修好的 harness、同一組 artifact 與 fixture 重跑**完整 `FORMAL_PLANS` 九輪**：

| 情境 | 2026-08-04 | 2026-08-08 |
|---|---|---|
| S1 ×3、S2-reuse、S4 30 分鐘、S5 normal／known | 通過 | 通過 |
| **S2-fresh** | 35/50，第 36 個 worker init 逾時 | **50/50**（worker 50 建 50 拆、handle 50 開 50 關、active 0） |
| **S3** | 前 19 個 recovery 通過、第 20 個 init 逾時 | **20/20**（第 20 輪 `staleRejected: true`） |
| **summary** | `pass: false` | **`pass: true`**，九輪皆無 `knownDegradation` |

記憶體閘門同時翻正：S2-fresh 的 `robustSlopeBytesPerBlock` 從 +34 MB 變 **−5.4 MB**、
`postCloseGrowthRatio` 從 +2.75% 變 **−3.36%**，且樣本數補滿 50。
（2026-08-04 那次的 `pass: false` 其實是樣本數不足的衍生結果，三個門檻值當時就全部合格。）

歸因不是靠「修了就好了」——修法同時動了兩條 pipe。解出 `serve.py` 請求 log 的成本模型
（**877 B／導覽 ＋ 1614 B／cycle**，三種形狀解、回代誤差 0.07%）可**預測**各分批形狀的牆：
5-cycle 分批 36.6、10-cycle 分批 38.5，對上實測的 36／38，連「批次越大牆越晚」的方向都對。

**這一輪改變什麼、不改變什麼：**

- **改變**：本 spec 對 Firefox longevity 的保留取消。「Firefox 有明確 Worker generation
  上限、產品必須優先 reuse」**不再有證據支持**。
- **不改變**：判定仍是**部分 GO**——§8 的 GO 要求 DOM accessibility 狀態正確，而
  document-content accessibility、完整 headed keyboard 與 Orca 至今仍 unsupported／未收集
  （見上一節）。**longevity 這一半移除後，部分 GO 只剩 accessibility 這一半。**
- **不自動外溢**：R8、E1、E4、R10 各自引用 finding 014 的限制（generation budget、
  「每頁 Worker generation 上限為 3」等）**不因本節生效而解除**，要各自重跑對應矩陣。

證據：`findings/evidence/sdk-r7/longevity-post-023-fix/firefox/`（九輪 ＋ `summary.json`；
2026-08-04 的原始證據在 `.../longevity/` 完整保留，一個位元組未動）。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。定義viewer keyboard/accessibility/hyperlink spike與100頁、50-cycle、20-crash、30-minute longevity gates。 |
| 2026-08-03 | v2。記錄跨瀏覽器最小open→close timeout與R7-D STOP；正式長矩陣未啟動。 |
| 2026-08-03 | v3。記錄finding 012 image-axis第二階段，將邊界縮至frame直接paragraph wrapper；STOP不變。 |
| 2026-08-03 | v4。記錄native／diagnostic WASM歸因，確認停在WASM LOK document destroy；STOP不變。 |
| 2026-08-03 | v5。same-commit native不重現，最終路由至Emscripten特定`wasm-fix`；STOP待修復。 |
| 2026-08-04 | v6。bounded Worker remediation解除Finding 012 STOP；完成正式矩陣並以Finding 014限制判定部分GO。 |
| 2026-08-08 | v7。新增§10.3。Firefox正式九輪以修好的harness重跑全過（`summary.pass: true`），finding 014的Worker generation限制撤回——成因是finding 023的unread pipe，成本模型預測牆36.6/38.5對上實測36/38。判定仍為部分GO，但理由只剩accessibility。 |

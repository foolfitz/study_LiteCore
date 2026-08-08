# 014 — Firefox 長壽程序反覆建立大型 WASM Worker 後 init 耗盡

## 狀態

**本檔已全數撤回（2026-08-08）。三組觀察全部歸屬到我方 harness，沒有一組是 Firefox 缺陷：**

| 本檔觀察 | 歸屬 |
|---|---|
| R7-D `s2-fresh`／`s3` 的牆 | [finding 023](023-sdk-init-wedges-at-fixed-session-depth.md)（unread `serve.py` pipe） |
| R7-C 單頁多 Worker 耗盡 | 同上 |
| R8-D 兩策略各等滿 900 秒 | [finding 025](025-webdriver-script-injection-never-ran-on-firefox.md)（注入腳本從未執行） |

三組都以重跑證明：R7-D 正式九輪 `summary.pass: true`、R7-C 單頁 19 Worker 19/19、
R8-D compatibility 28/28 ＋ soak 30.07 分鐘。**「每頁 Worker generation 上限為 3」的前提
亦被兩種工作量各自推翻**（單頁 50 代、單頁 19 Worker）。

---

**核心證據（R7-D `s2-fresh`／`s3`）的撤回經過：那不是 Firefox 缺陷，
是我們自己的 harness——[finding 023](023-sdk-init-wedges-at-fixed-session-depth.md) 那條
沒人讀的 `serve.py` 請求 log pipe。**用修好的 harness 原封不動重跑，兩個情境都全通：

| 情境 | 2026-08-04（pipe 未修） | 2026-08-08（pipe 已修） |
|---|---|---|
| `s2-fresh` | 35/50 cycle，第 36 個 worker `init timed out after 120000 ms` | **50/50 全過**，worker 50 建 50 拆、handle 50 開 50 關、active 0 |
| `s3` | 20 個 crash cycle 的第 20 個 recovery init 逾時 | **20/20 全過**，第 20 輪 `staleRejected: true` |

記憶體閘門同時翻正：`robustSlopeBytesPerBlock` 從 +34 MB 變成 **−5.4 MB**、
`postCloseGrowthRatio` 從 +2.75% 變成 **−3.36%**、`memoryAnalysis.pass: true`。
（2026-08-04 那次 `pass: false` 其實是**樣本數不足的衍生結果**——三個門檻值當時就全部合格，
只是 50 輪只跑到 35 輪。）

證據：`findings/evidence/sdk-r7/longevity-post-023-fix/firefox/{s2-fresh,s3}/run-1/result.json`
（寫在新目錄，2026-08-04 的歷史證據一個位元組都沒動）。

**歸因是算出來的，不只是「修了就好了」**——見下節的位元組帳。

~~**機制已於 2026-08-07 歸因並確認為上游 Firefox 缺陷**~~ ——那一版（2026-08-07）把本檔
掛到 [finding 024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md) 上，
**已撤回**。024 本身完全成立（它的數字是 pipe 全修之後重測的，Nightly 對照還走無 driver
模式），但**本檔這幾個數字不是它的證據**。

## 影響

- Chrome 150 的 R7-D 50-cycle fresh/reuse、20-crash、30-minute soak 全部通過。
- Firefox 的一般使用、單 Worker reuse 50 cycles、30-minute soak、Finding 012 bounded recovery 與正常 S5
  均通過。
- ~~Firefox 在同一長壽工作階段大量反覆建立／重啟 `writer-review` 大型 WASM Worker 時，最終會在 SDK `init`
  階段達 120,000 ms timeout；因此不能宣稱 Firefox 通過 50 fresh-engine 與 20-crash-storm 正式門檻。~~
  **（2026-08-08 撤回）**：pipe 修好後 `s2-fresh` 50/50、`s3` 20/20 全過。
  Firefox R7-D longevity 的九個情境**現在全數通過**（其餘七個 2026-08-04 當時就過）。

### 下游影響（2026-08-08，逐項處理中）

本檔的產品限制被 **15 個規格檔**提到（全庫 `grep`），其中 **11 份帶現行規範性條文**
（R7-D／R7-000 的條文已隨重跑撤回；`SPEC-R8-A`、`SPEC-R6+` 只是沿革敘述）；另有
**7 個程式碼站點與 1 份凍結矩陣**把它寫死成可執行的閘門。全部建立在這個已撤回的機制上：

| 規格 | 引用內容 |
|---|---|
| ~~`SPEC-R7-D`~~ | **已處理（2026-08-08，§10.3）**：Firefox 正式九輪重跑 `summary.pass: true`，限制撤回。判定仍為部分 GO，但理由只剩 accessibility |
| ~~`SPEC-R7-000`~~ | **已處理（2026-08-08，v6）**：總判定保留項刪去「Firefox 無限 Worker generation」 |
| `SPEC-R8-000`／`SPEC-R8-D` | **只處理了一半（2026-08-08，R8-D §10.1、R8-000 三處）**：Firefox combined-run 缺口補齊——compatibility 28/28、soak 30.07 分鐘、R8-C t0 46／t1 37，成因是 [finding 025](025-webdriver-script-injection-never-ran-on-firefox.md)；T2 缺口與本檔無關，`PARTIAL_GO_LOCAL_DELIVERY` 判定不變。**但兩份各自的 generation budget 條文（R8-000 §5「接近上限時要求重新載入 session」、R8-D §4「generation budget 與 reload 提示可觀察」）原封未動**，2026-08-08 第三次才就地標註 |
| `SPEC-E1-A` §4、`SPEC-E1-C` §2.1／§C2／§C4 | **「每頁 Worker generation 上限為 3」——前提已被實測推翻並就地標註，但條文未改**（見下節）。放寬與否會改變 E1-C 對外承諾與產品 reload 行為，屬產品決定 |
| `SPEC-R8-B`、`SPEC-R8-C`、`SPEC-E4-000`、`SPEC-R10-000` | generation budget／沿用上限：同樣已就地標註指回本檔，條文未改 |
| `SPEC-E1-000` §3、`SPEC-E2-000` §5、`SPEC-E3-000` §2.1／§8 | **2026-08-08 第三次補列**：三份都寫「Firefox generation 有界」／「沿用 finding 014 的 generation budget」，先前**漏列也漏標**，現已就地標註，條文未改 |

（`SPEC-R8-A` §2 與 `SPEC-R6+-roadmap` 只在輸入清單與判定沿革裡提到本檔，不含條文，不列入。）

**程式碼與凍結矩陣裡的引用者（2026-08-08 第三次補列）**——這些不是文字，是會執行的閘門，
規格撤限之後它們仍會擋下重跑：

| 位置 | 寫死的內容 |
|---|---|
| `tools/validate_r8_d.py:80,86` | `generation_limit = 4 if browser == "firefox" else 8`，據以判 `boundedWorkerGenerations` |
| `tools/validate_r8_d.py:87` | `boundedWorkerGenerationsPerPage`：`maxWorkerGenerationsPerPage <= 3` |
| `tools/validate_r8_d.py:265` | 缺口字串「Firefox worker-generation budget requires bounded reuse and full browser reload guidance」 |
| `tools/run_r8_production.py:316` | 每頁 `generation_count + weight > 2` 就切批（**每頁 2 代**，比規格的 3 還嚴） |
| `tools/run_r8_production.py:634,640` | `worker_generations = 4`、`"maxWorkerGenerationsPerPage": 3` —— **兩個都是字面值，不是量到的**；`:656` 再拿它跟 4／8 比對後寫進 `pass` |
| `tools/run_r7_compatibility.py:78,288` | `worker_budget: int = 3`（docstring 已改寫，預設值未動） |
| `tools/run_r7_longevity.py:299` | Firefox `s2-fresh` 每 5 cycle 換一個瀏覽器行程 |
| `e1/validation-matrix-v1.json:176` | `bounded-worker-generation` 屬性（**凍結矩陣**，動它要重跑 E1-C） |

**這些不會因為本檔撤回而自動失效**——要撤掉限制得各自重跑對應矩陣。**在那之前不得
把「上限已解除」寫進任何規格或產品。**（截至 2026-08-08：R7-D、R7-000 兩份已用重跑證據
處理完畢；R8-000、R8-D 只補齊了 combined-run 缺口，generation 條文未動；
E1-000／E1-A／E1-C／E2-000／E3-000／R8-B／R8-C／E4／R10 只標註前提不成立，
**條文一律未改**；上表七個程式碼站點與那份凍結矩陣**一個都沒動**。）

進度：

- **R7-D 已完成**（2026-08-08 重跑正式九輪，`summary.pass: true`，證據
  `evidence/sdk-r7/longevity-post-023-fix/firefox/`）。
- **R8-D compatibility 已完成**（2026-08-08 **28/28**，證據
  `evidence/sdk-r8-post-023-fix/production/compatibility/firefox/`）——成因是
  [finding 025](025-webdriver-script-injection-never-ran-on-firefox.md)，注入腳本
  在 Firefox 上從未執行。
- **E1 的「每頁 Worker generation 上限為 3」前提已被實測推翻（2026-08-08）**，見下。

（R7-D 的判定並沒有因此變成完整 GO——§8 的 GO 還要求 DOM accessibility 狀態正確，
而 document-content accessibility／完整 headed keyboard／Orca 至今未收集。
**longevity 這一半移除後，部分 GO 只剩 accessibility 那一半。**）

### 「每頁 Worker generation 上限為 3」：前提已被推翻（已觀察，2026-08-08）

`SPEC-E1-C` §C2 與 `SPEC-E1-A` §4 寫的是「每頁 Worker generation 上限為 3，達上限前
要求完整 page reload，**不以無界 restart 規避 Finding 014**」。這條的唯一依據就是本檔。

判別實驗：R7-D `s2-fresh` 加一個預設關閉的 `--firefox-single-session`，把 50 個 cycle
全部跑在**同一個瀏覽器行程的同一個頁面**裡（不導覽、不 reload），對照 2026-08-04
同形狀的原始單頁測試（當時第 34 個 worker 逾時）：

| | 2026-08-04 | 2026-08-08 |
|---|---|---|
| 單頁 engine generation | 33 完成，第 **34** 個 `init timed out` | **50/50 全過** |
| worker | — | 50 建 50 拆、active **0** |
| handle | — | 50 開 50 關、active 0 |
| 記憶體 | — | 斜率 **+22.4 MB**／block（門檻 67 MB）、post-close **+4.09%**（門檻 35%）、`pass: true` |

`sessionType: headless-automatic`（非分批）、`batches: null`——確認是單一 session 單一頁面。
**實測到的每頁世代數至少 50，是規格所寫上限的 16 倍以上。**
證據：`findings/evidence/sdk-r7/single-page-generations/firefox/s2-fresh/run-1/result.json`。

**我沒有動那兩份規格的要求條文。**理由：E1-C 是**凍結矩陣**且已判 `E1_GO_ODT_EDITOR`，
其證據是在「每頁 ≤3 代」這個約束下取得的。放寬約束不會使既有證據失效
（在更嚴格的約束下通過，仍然通過），但它會**改變 E1-C 對外承諾的內容**，
也會改變 `SPEC-R8-B`／`SPEC-R8-C` 的 generation budget 與「耗盡時要求整個 session reload」
這條產品行為。那是產品決定，不是量測結論。**本檔只負責記錄前提已不成立。**

**第二個獨立的資料點（真實 corpus，不是壓力檔）**：R7-C 的 `firefox_batches()` 也硬寫著
`worker_budget: int = 3`，docstring 明說是「Firefox observed large-WASM Worker ceiling」。
把它開到 64 之後，full group 的 **19 份文件在同一個頁面**跑完——19 個 Worker 建 19 拆、
19/19 全過、只用 1 個 batch（原本 7 個）。證據
`findings/evidence/sdk-r7/compatibility-single-page/firefox/full/run-1/`。

**這份證據的 `workerBudget` 欄位不可信，別拿它對帳**：`run_r7_compatibility.py:232` 當時
把它寫死成字面值 `3`，不反映 `--firefox-worker-budget`，所以 `result.json` 記的是
`workerBudget: 3`——**與這一輪實際跑的 64 相反**。真正佐證這一輪的是同一個檔案裡的
`batchSizes: [19]`（單一 batch）、`workers: {created: 19, terminated: 19}` 與 19 筆
`casePass: true`。該欄位已於 2026-08-08 改成記錄實際值；既有證據一個位元組都沒動，
旁邊補了 `NOTE.txt` 說明。

所以「每頁 3 個」在**兩種完全不同的工作量**下都被推翻：合成壓力檔（s2-fresh 單頁 50 代）
與正式相容性 corpus（R7-C 單頁 19 個 Worker）。

順帶一提，R7-D 對 Firefox `s2-fresh` 的**每 5 cycle 換一個瀏覽器行程**的分批策略、
以及 R7-C 的每頁 3 個上限，都是為了規避本檔而寫的；上面兩輪表示它們都可以退休
（**未執行**——改預設值會改變既有證據的取得形狀，屬產品／流程決定）。

### 那 50 代到底有沒有靠近某道牆？`dom.workers.maxPerDomain` 判別（已觀察，2026-08-08）

上面「50/50 全過」只證明上限不是 3，**不證明沒有上限**。而且有一個令人不安的巧合：
引擎形狀是 `PTHREAD_POOL_SIZE=7`，**每代 8 個 worker**，50 代 ＝ **400 個**——
[finding 024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md) 量到的
`dom.workers.maxPerDomain` 預設是 **512**，牆落在第 65～66 次導覽（≈520 個）。
也就是說那一輪停在已知唯一硬天花板的 **78 %**，一次都沒有跨過去。
`workers.terminated: 50 / active: 0` 是**我們自己的引擎級計數器**，不是 Firefox 的
per-domain 那本帳；而 024 已經證明 Firefox 那本帳會落後。所以「頁內 `dispose()`
到底有沒有即時歸還名額」當時仍是**推論**。

用 024 的同一根探針把預算縮小，看牆會不會跟著搬：

| 條件 | 名額預算 | 若名額會漏，預測的牆 | 實測 |
|---|---|---|---|
| **正控制** `maxPerDomain=4`（比一代所需的 8 還少） | 4 | 第 **1** 代 | **第 1 代就死**：`init timed out after 120000 ms`、worker 建 1 拆 0 active 1、handle 開 0、`lifecycle: 0` |
| **判別** `maxPerDomain=64` | 64 | 第 **8** 代（64 ÷ 8） | **50/50 全過**，50 建 50 拆 active 0 |

正控制是這個實驗的必要條件：它證明 pref **真的送進瀏覽器且機制對它敏感**——
否則「加了 pref 還是 50/50」跟「pref 根本沒生效」無法區分。死法與 024 的
「靜默排隊」簽章一致（零 worker 錯誤，只有 init 逾時）。

**結論（已觀察）：頁內 `dispose()` 會即時歸還 worker 名額。**預算縮小 8 倍（512→64）
之後仍然跑完 50 代，是「名額會漏」所預測之牆的 **6.25 倍**。024 的惰性回收
**只咬導覽拆除，不咬頁內 dispose**——這與 024 自己的產品對策
（`pagehide` 時明確 `dispose()`）完全一致。`openMs` 全程平坦（前五 330／398／407／424／385，
後五 316／320／297／309／319，最大 424 ms），沒有逼近任何排隊行為的跡象。
證據：`findings/evidence/sdk-r7/single-page-generations-pref/maxperdomain-{4,64}/firefox/s2-fresh/run-1/result.json`。

**但記憶體殘留這條沒有被清掉，而且複製出來了。**兩輪各自的 post-close block 中位數
都是**單調上升**：

| 輪次 | block 中位數（MB） | 逐塊差 | robust 斜率 | 首末成長（**相距 30 代**） |
|---|---|---|---|---|
| stock | 1403.3 → 1406.3 → 1435.0 → 1460.7 | ＋3.0、＋28.7、＋25.7 | 22.4 MB／block | ＋57.4 MB（4.09 %） |
| `maxPerDomain=64` | 1400.0 → 1413.8 → 1468.2 → 1470.3 | ＋13.8、＋54.4、**＋2.1** | 25.9 MB／block | ＋70.3 MB（5.02 %） |

**先修兩個數字（2026-08-08 第三次）**：`postCloseGrowthBytes` ＝ `blocks[-1] − blocks[0]`，
而 block 是 cycle 11–20／21–30／31–40／41–50 的中位數，**首末相距 30 代，不是 40 代**
（`tools/r7_longevity_analysis.py:73-76`）。所以每代殘留是 **1.9～2.3 MB**（首末成長）
或 **2.2～2.6 MB**（斜率），先前寫的下限 1.4 MB 是用 40 這個錯分母算的。線性外推到
harness 自己的絕對門檻（`maxPostCloseGrowthBytes` ＝ 512 MiB）落在**第 207～281 代**
（先前寫的 374 同樣出自那個錯分母）；把 35 % 比例門檻（0.35 × 1403 MB ＝ 491 MB）
一併算進去，最早約第 **190** 代。

**再修一個閘門敘述**：這兩輪**不是**靠 `continuousThreeBlockGrowth` 放行的。
`r7_longevity_analysis.py:92-103` 的 `pass` 是四項連乘——首末成長 ≤ 512 MiB、
比例 ≤ 35 %、斜率 ≤ 64 MiB／block，且非 `continuousThreeBlockGrowth`——兩輪**四項全過**，
斜率餘裕 2.5～2.9 倍、比例 7～9 倍、絕對值 7.6～9.4 倍。`continuousThreeBlockGrowth`
在只有 4 塊時確實近乎失效（只剩一個窗，要三塊各超過 64 MiB ⇒ 總量 >192 MiB），
但它不是本案的把關者。正確的說法是：**四道門檻全部為「失控」校準，沒有一道抓得到
「小而單調」。**

**線性外推撐不住，而且反證就在同一批資料裡（推論）**：

- 每輪只有 4 個 block、每個條件只有 1 輪。stock 的 Theil-Sen 兩兩斜率是
  3.0／15.8／19.1／25.7／27.2／28.7 MB／block（中位數 22.4，與檔案一致）——
  **估計量自身跨度 10 倍**，這種斜率不該外推 5 倍。
- 兩輪形狀相反：stock 先平後升，**`maxPerDomain=64` 先升後平，最後一塊 10 代只漲
  2.1 MB**——那正是 plateau 的樣子。「單調上升」在 4 點下的隨機機率是 1/24 ≈ 4 %。
- 兩輪的 `memoryAnalysis.wasm.status` 都是 `unavailable`：**證據裡沒有任何東西把這 4～5 %
  歸給引擎。**取樣是 post-close 停留 1.1 s、沒有強制 GC／CC，而 finding 024 的主張正是
  「Firefox 對剛拆掉的 worker 是惰性回收」——「GC 落後」不是憑空的對手假說，
  是隔壁檔已經在同一個瀏覽器、同一條拆除路徑上立過的假說。
- 要分開「殘留」與「回收延遲」，得在最後一代之後放著再取樣，或走 memory-pressure
  強制回收。**沒有任何一輪做過（待驗證，見第 9 項）。**

所以本節能寫的只有：**post-close PSS 在 50 代裡漂了 4～5 %，兩輪形狀不一致，
無法歸因到引擎，離四道門檻 3～9 倍。**先前那句「我們現行判 pass 的那組門檻本身就隱含
一個位於低百位數的有限上限」是把測試閘門當成產品上限、再乘上一個站不住的線性外推，
**2026-08-08 第三次降級為推論**：要主張有限上限，得先量到 50 代以上並排除回收延遲。

**適用範圍（已觀察，必須寫清楚）**：以上三輪都是 Firefox 153.0.1、headless、
單一合成壓力檔（`l4-stress-100`）、各一輪，跑的是 R7 的 `writer-review` probe
（wasm `ba257beb…`），不是 E1-C 條文所管的產品 artifact（`835b453d…`／`e1-editor-v1`）。

**但「換 artifact」在決定算術的兩個量上是可證明相同的，不是相近**：

| | `writer-review`（R7） | `e1-editor-v1`（E1） |
|---|---|---|
| link 巨集 | `link_r5_product`（`Makefile:516`） | **同一個**（`Makefile:562`） |
| 旗標 | `-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7` | **逐字相同**（`Makefile:502`） |
| coreCommit | `671c848b…` | `671c848b…` |
| wasm | 115,265,157 B | 115,272,506 B（＋7.3 KB，**0.006 %**） |
| resource packs | base-r5＋cjk-r5 | 同 |
| 頁面側拆除 | `sdk/document-sdk.js` 的 `this._worker.terminate()` | **同一份檔案、同一條路徑** |

每代 8 個 worker、每代 1 GiB heap 兩邊相同，所以**名額那條算術可以搬**；而
`maxPerDomain=64` 的判別等於把預算壓縮 8 倍在測，比「上限放寬到 16」所需的 3 倍餘裕
嚴苛得多。真正沒被涵蓋的是另外三件事：

- **worker 側的拆除程式碼不同**：`sdk-worker.js` 698 行（R7）對 1,038 行（E1）。
  頁面側 `terminate()` 相同，**worker 側的 dispose 不是同一份**。
- **工作量不同**：s2-fresh 每代只是開 `l4-stress-100`、畫一張 tile、關（約 3 s／代）；
  E1-C 每代是編輯、IME、選取、存檔。名額不受工作量影響，**記憶體殘留受**。
- **Chrome 的單頁多代資料一筆都沒有**（024 的各 rung 乾淨，但那是導覽形狀，不是頁內
  世代），而且各條件 n＝1、單一 fixture；失效是懸崖不是斜坡，n＝1 只給得出
  「這個形狀 ≥50」。

要把上限放寬到接近 50，這三個缺口得先補。放寬到遠低於 50 的值（例如 16）不需要新量測：
名額側餘裕充分，記憶體側按上一節實測的最壞速率（2.59 MB／代）也只有約 41 MB／16 代。

## 2026-08-08 重新分類（本檔三組觀察各自的歸屬）

下方〈已觀察〉全文保留為 2026-08-04 的原始紀錄，不修改；這裡只標歸屬。

| 本檔觀察 | 歸屬 | 依據 |
|---|---|---|
| `s2-fresh`／`s3` 的牆（第 34／36／37／38 個 worker） | **finding 023 的 `serve.py` pipe（已確認，實驗＋算術）** | 見下「位元組帳」與上表的重跑結果 |
| R7-C 單頁多 Worker／快速多 session 的 init、navigation 耗盡 | **finding 023 的 `serve.py` pipe（已確認，實驗）** | 標準組態重跑全過（repeat ×3 ＋ full，28 case）。判別輪把 `--firefox-worker-budget` 由 3 開到 64，讓 full group 的 **19 份文件全部擠在同一個頁面**：**19 個 Worker 建 19 拆，19/19 全過，只用 1 個 batch**（原本要切 7 個）。每頁 3 個的規避策略不再需要 |
| R8-D 兩種策略都等滿 900 秒且沒有任何頁面結果 | **[finding 025](025-webdriver-script-injection-never-ran-on-firefox.md)（已確認，實驗）** | 注入腳本在 Firefox 上**從未執行**（`evaluate()` 包成 `return`＋換行 → ASI）。修好後同一相位 **28/28 全過**，且這次沒先跑 R8-C，條件比當年更乾淨。三條 pipe 全部排除：server 端 `log_message` 是 no-op，driver 端 900 秒全程僅 **926 B** |

### 位元組帳：牆的位置是算得出來的（已觀察）

`serve.py` 的請求 log 在 2026-08-04 寫進一條沒人讀的 64 KiB pipe。量三輪不同形狀的工作量
（`tools/measure_geckodriver_stderr.py` 的 `serve.log`，見〈證據〉）解出成本模型：

```
每次導覽    877 B
每個 cycle 1614 B
```

擬合只用了 attempt-02（6 批 × 5 cycle，53,681 B）與 attempt-03（6 批 × 1 cycle，14,945 B）
兩個**位元組總量**；回代第三種形狀 attempt-01（4 導覽＋20 cycle）：預測 35,787 B ／
實測 35,813 B，誤差 0.07 %。**被預測的那兩道牆（36／38）是 2026-08-04 的獨立資料，
沒有進到擬合裡。**

**但模型有第三個參數，初版沒寫出來：pipe 的起始存量。**`run_r7_longevity.py` 的 `main()`
一次 invocation 只開一個 `serve.py`，`--all` 會讓多個情境接力共用同一條 pipe——所以
「牆落在第幾個 cycle」取決於該情境開跑時 pipe 裡已經有多少位元組。**這個初始條件必須
逐輪認定，不能預設為零**，否則模型有一個自由參數可以吸收任何誤差，兩次命中就不可證偽。

用 `processSamples[].monotonicSeconds`（`CLOCK_MONOTONIC`，跨行程可比）重建 2026-08-04
的時間軸，就能逐輪認定：

| 段落 | monotonic | 與前段間隔 | 判讀 |
|---|---|---|---|
| `s1` run-1／2／3 → `s2-reuse` | 49865 → 49977 | 12.5／12.4／12.6 s | 正好是 runner 的 `time.sleep(12)` ⇒ **同一次 `--all` invocation、同一條 pipe** |
| （空窗） | 49977 → 50740 | **763.4 s** | 原始單頁那輪落在這裡；其 `result.json` 被 00:40 的正式輪覆蓋 |
| 10-cycle attempt | 50740 → 51032 | （承上空窗） | ⇒ 另一次 invocation，**pipe 全新** |
| `s2-fresh` run-1（正式） | 51129 → 51523 | 97.4 s | ⇒ 另一次 invocation，**pipe 全新** |

代進三種有證據的分批形狀。前兩列用**精確帳**（不攤提），因為決定阻塞的是累計位元組：

| 形狀 | 起始 pipe | 到牆那個 cycle 的累計 | 距 64 KiB | 實測牆 |
|---|---|---|---|---|
| 5 cycle／process | 空（前隔 97.4 s） | 8×877＋36×1614 ＝ 65,120 B | 差 **416 B** | **36**（第 8 批的首個 init） |
| 10 cycle／process | 空（前隔 763.4 s） | 4×877＋38×1614 ＝ 64,840 B | 差 **696 B** | **38**（完成 37 後逾時） |
| 單頁不分批 | **非空**（接在 `s2-reuse` 後 12 s） | 877＋34×1614 ＝ 55,753 B | 差 **9,783 B** | 34 |

前兩列在空 pipe 前提下各差不到一個 cycle，而且缺口**同號同量級**（416／696 B）——那正是
模型沒計入的固定量：每次 invocation 的 `wait_page()` 輪詢與每個 session 的 favicon 請求
（每行約 108 B，八個 session 就超過 800 B）。**方向也對**：批次越大、每 cycle 攤到的導覽
越少、牆越晚，實測 36 → 38 相符。

第三列的 9,783 B 缺口**不是模型的反證，是初始條件不同**：那一輪接在 `s1`×3 與 `s2-reuse`
之後，共用同一條已經裝了東西的 pipe（光四次導覽就 3.5 KB）。**（待驗證，見第 9 項）**
把 `s1`×3＋`s2-reuse` 用會寫檔的 harness 重跑、量它們產生多少位元組，才能把這一列從
推論升格為已觀察；在那之前它只算「與模型相容」，不算獨立佐證。

（初版表格還有第四列「同 process 換頁 ~38」。那一輪沒有任何保存下來的證據，連 cycle 數
都是約值，**2026-08-08 第三次已從預測表移除**，只留在下方〈已觀察〉的原始紀錄裡。）

**這也解釋了 2026-08-04 最反直覺的那一格**：第 8 批的第一個 init 就逾時。批次之間不共用
瀏覽器——每批新開 geckodriver、新開 WebDriver session，而 `open_session()` 走
`FirefoxSession("cold")`、`profile_dir=None`，profile 由 geckodriver 現造在 temp 目錄、
disk／memory cache 全關，**所以 per-profile 累積在結構上就不成立**。跨批次共用的只剩那
一個 `serve.py`（以及機器本身）。

三個必須寫清楚的限制（2026-08-08 第三次補）：

- **`browserRootPids` 記的是 geckodriver 的 pid，不是 Firefox 的。**
  `run_r7_longevity.py:309` 存的是 `session.process.pid`，而 `FirefoxSession.process` 是
  geckodriver 的 `Popen`（`run_browser_probe.py:103`）。八個值各不相同是**已觀察**；
  「八個全新 Firefox 行程」是**推論**（新 driver ＋新 session ＋新 profile ⇒ 新瀏覽器）。
  Firefox 自己的 pid 從頭到尾沒有被記錄過。
- **機器層資源從未被量測排除。**`r7_support.py:42` 的 `process_snapshot()` 只走
  `psutil.Process(root_pid)` 及其子孫；系統層 MemAvailable、`/dev/shm`、fd／執行緒數、
  前一批殘留的行程都沒有取樣。它是被位元組帳與重跑**間接**排除的，不是被量測排除的。
- **跨批次共用的是「`serve.py` 這個行程」，不是「那條 pipe」。**ThreadingHTTPServer 的
  執行緒與 socket 同樣跨批次共用；把範圍縮到 pipe 的是位元組帳，不是 pid 論證。

批次 8 的取證與 pipe 一致（`batches/batch-8/result.json`）：頁面本身 **92 ms 就到
`checkpoint: ready`**（HTML／CSS／app.js 都送達），接著 `workers.created: 1／terminated: 0`、
`init timed out after 120000 ms`、`lifecycle: 0`。**頁面資產送得到、引擎資產送不到**，
正是 pipe 只剩約 2 KB 時的形狀；記憶體壓力會在 instantiate 丟出錯誤，不會先把頁面乾淨
載完、再靜默吊滿 120 秒。

**一個補不了的洞（已觀察）**：本檔的重跑宣稱「用修好的 harness 原封不動重跑」，但
`study_LiteCore` 是 2026-08-08 才進版控（`c7b899e`），08-04 與 08-08 之間探針是否還有
別的差異，在庫裡無從查證。

### geckodriver 那條 pipe：量過了，不是本檔的成因，但沒被完全排除（已觀察）

`FirefoxSession` 當年用 `Popen(stderr=PIPE)` 從不讀取（2026-08-07 才改
`DEVNULL`＋`--log error`，`tools/run_browser_probe.py:72-78`）。實測：

- **正常量極小**：一個 session 跑 30 個 cycle／6 次導覽，driver stderr 全程 **1,290 B**
  （四輪一致；`--log error` 與預設等級無差別——那些位元組是 Firefox 自己的 stderr，
  不受 `--log` 影響）。
- **但會爆量**：attempt-01 的兩個 session 各寫出 **101,845 B 與 109,921 B**，內容是
  Firefox 的 `RemoteSecuritySettings`／CRLite 下載失敗（各 38 次）與 Nimbus 實驗警告。
  **超過 64 KiB。**後續三輪重跑（含 90 秒純 idle 對照）都沒再出現，所以它是
  **偶發、依網路狀態**，不隨我們的工作量增長。

→ 對 `s2-fresh`：driver pipe 是 **per-session**（每批新開一個 geckodriver），
**產生不了跨批次累積的第 36 格牆**，所以不是它的成因。

→ 對 R8-D：本節初版寫「同一 session 等滿 900 秒，爆量形狀對得上，**不能排除**」。
**已排除（2026-08-08）**：把 driver stderr 導成檔案重跑那 900 秒的停擺，**全程只有 926 B**
（離 64 KiB 差 70 倍），且 R8-D 的成因已由
[finding 025](025-webdriver-script-injection-never-ran-on-firefox.md) 確認為注入腳本
從未執行。證據 `evidence/sdk-r8-post-023-fix/driver-stderr/`。

## 已觀察

- S2-fresh 原始單頁測試先完成 33/50 cycles；第 34 個 Worker 得到
  `SdkTimeoutError/TIMEOUT: init timed out after 120000 ms`。前 33 次 handle 都 closed、Worker 都 terminated。
- 同 Firefox process 切換頁面 context仍在累計約第 38 個 Worker timeout，排除只限單一 DOM page context。
- 10-cycle／process 分批完成 37 cycles後仍 timeout；5-cycle／process 最終完成 35 cycles，第 8 個乾淨
  Firefox process 的首個 init timeout。這顯示同時存在 Worker累積與快速 process啟停／系統層資源限制，
  不能靠無限分批形成產品承諾。
- S3 的 20 個 crash event全部被觀察；前19個 recovery皆通過，stale handle拒絕且未重送 mutation；第20個
  recovery init timeout。最終active Worker與handle皆為0。
- S2已完成樣本的PSS block median沒有無界上升；失敗是未達50-cycle樣本數，不是越過既定growth threshold。
- R7-C 也曾在單頁多 Worker及快速多 Firefox session呈現相同類型的 init／navigation耗盡；正式相容性矩陣
  最終以每個邏輯group單一browser process、每頁最多3 Worker完成，但該策略不足以滿足D的長壽fresh/crash門檻。
- R8-C Firefox完整T0／T1矩陣通過後，R8-D先用每批獨立process、再改用單一process同origin navigation；兩種
  策略都在第一批corpus執行前等待900秒且沒有頁面結果。因尚未進入任何文件案例，不能歸因特定ODT；這是
  Finding 014在R8 active-cache campaign的新增觀察，不是R8 cache混版或文件內容失敗。

## 推論

- 已完成 cycle 的handle／Worker歸零，且reuse 50 cycles通過，所以「每次 close 都洩漏一個公開 SDK handle」
  不是充分解釋。
- 失敗與反覆建立大型LibreOffice WASM instance高度相關；候選層包括Firefox process的WASM／thread資源、
  Emscripten pthread teardown、SharedArrayBuffer映射及LibreOffice runtime初始化。
- 現階段安全產品策略是Firefox優先reuse單一Worker；bounded close/crash recovery次數超過策略上限時，要求host
  重新載入browser工作階段，不宣稱無限Worker generation。

## 待驗證

1. ~~建立不含LibreOffice core、但使用相同Emscripten pthread／WASM memory設定的最小重現，區分browser與core。~~
   **已完成（2026-08-07，[finding 024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md)）**：
   `minimal` rung＝40 KB 模組、同款 `-pthread -sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7`，
   Firefox 牆 66、Chrome 120 乾淨；自包含重現包在 `findings/repro/024-firefox-worker-reclaim/`。
   **結論：是 browser，不是 core。**
2. ~~記錄每次init前後的Firefox process map、thread、SharedArrayBuffer與WASM memory high-water。~~
   **已完成（2026-08-07，finding 024）**：RSS 階梯（1.45→5.49 GB、+0.6～0.7 GB／導覽）、
   maxVms 12→41 GB、執行緒序列（308→平頂 ~500–512→死，約 +4.6／導覽）都已記錄。
3. ~~比較非Snap Firefox、Firefox ESR與相同版本原生安裝~~ **已無必要（2026-08-08）**：
   本檔的牆不是瀏覽器造成的，換 Firefox 版本測不到東西。（此項對 finding 024 仍有意義，
   已移交該檔。）
4. ~~為產品定義可觀測的Worker-generation budget與typed「請重新載入工作階段」狀態~~
   **前提消失（2026-08-08）**：R7-D 形狀的 generation 上限本來就不存在。
   產品若仍要 budget，須以 024（導覽不 dispose）為依據重新定義，不是以本檔。
5. ~~**（新）補「不導覽的同頁 worker churn」rung**，把 s2-fresh 的牆對上 024。~~
   **已完成（2026-08-08）——而且做法比原計畫直接**：不必造替身 rung，直接用修好的
   harness 重跑 `s2-fresh` 本尊，**50/50 全過**。牆是 pipe，不是同頁 churn。
6. ~~**（新）量 headless Firefox 經 geckodriver 的 stderr 產出量**~~
   **已完成（2026-08-08）**：正常 1,290 B／session；偶發爆量 ~101～110 KB（CRLite／
   RemoteSettings 失敗）。對本檔已排除（per-session，產生不了跨批次的牆），
   **對 R8-D 未排除**。見上節。
7. **（新）R7-C 與 R8-D 用修好的 harness 重跑**——這兩組是本檔僅剩未重測的觀察，
   目前歸屬「未定」。R8-D 特別要一併觀察 driver stderr 量（同一 session 等 900 秒，
   正是那條 pipe 唯一可能咬到的形狀）。
8. **（新）下游規格的限制要不要撤**——見〈下游影響〉。每一條都要各自重跑對應矩陣才能撤，
   不能靠本檔撤回自動生效。**另有七個程式碼站點與一份凍結矩陣把上限寫死**，撤規格條文
   之前先看那張表。
9. **（新，2026-08-08 第三次）量 `s1`×3＋`s2-reuse` 的 `serve.log` 位元組量**——這是把
   「單頁那輪的牆 34」從推論升格為已觀察的唯一實驗。模型要求那段前綴約 9.8 KB；
   量到就閉合，量不到就得承認單頁那一列仍未解釋。成本約 6 分鐘機時。
10. **（新，2026-08-08 第三次）分開「記憶體殘留」與「回收延遲」**——在最後一代之後
   讓頁面閒置再取樣，或走 memory-pressure 強制回收，並把單頁世代數推到 50 以上。
   現有兩輪各 4 個 block、各 1 輪，形狀還互相矛盾（一輪先平後升、一輪先升後平），
   不足以支撐任何線性外推。

## 證據

- `findings/evidence/sdk-r7/longevity/firefox/s2-fresh/run-1/result.json`
- `findings/evidence/sdk-r7/longevity/firefox/s2-fresh/run-1/batches/`
- `findings/evidence/sdk-r7/longevity/firefox/s2-fresh/attempts/20260804-multi-process-10-cycle-batches-37-of-50/`
- `findings/evidence/sdk-r7/longevity/firefox/s3/run-1/result.json`
- `findings/evidence/sdk-r7/longevity/firefox/s4/run-1/result.json`
- `findings/evidence/sdk-r7/longevity/chrome/summary.json`
- `findings/evidence/sdk-r8/production/attempts/compatibility-firefox-after-r8c-generation-exhaustion/result.json`
- `findings/evidence/sdk-r8/production/attempts/compatibility-firefox-single-process-navigation-timeout/result.json`
- `findings/evidence/sdk-r8/production/compatibility/firefox/summary.json`
- `findings/evidence/sdk-r8/production/longevity/firefox/summary.json`

2026-08-08 重跑與量測：

- `findings/evidence/sdk-r7/longevity-post-023-fix/firefox/s2-fresh/run-1/result.json`（50/50）
- `findings/evidence/sdk-r7/longevity-post-023-fix/firefox/s3/run-1/result.json`（20/20）
- `findings/evidence/sdk-r7/geckodriver-stderr-volume/`（`result.json` ＋ `serve.log`
  ＋ `geckodriver-*.log`；`attempt-02`／`attempt-03` 是解成本模型用的另兩種形狀）
- `findings/evidence/sdk-r7/single-page-generations/firefox/s2-fresh/run-1/result.json`（單頁 50 代）
- `findings/evidence/sdk-r7/single-page-generations-pref/maxperdomain-{4,64}/firefox/s2-fresh/run-1/result.json`
- `findings/evidence/sdk-r7/compatibility-single-page/firefox/full/run-1/`（R7-C 單頁 19 Worker；
  **`workerBudget` 欄位不可信，見 `NOTE.txt`**）

2026-08-08（第三次）對抗性複核所引用的既有證據：

- `findings/evidence/sdk-r7/longevity/firefox/s2-fresh/run-1/batches/batch-8/result.json`
  （牆那一批的取證：頁面 92 ms `ready`、engine init 逾時）
- 各輪 `result.json` 的 `processSamples[].monotonicSeconds`（重建 08-04 invocation 邊界，
  用以認定每一輪的 pipe 起始存量）

## 環境

2026-08-04 原始證據：

- Core：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- writer-review loader：`35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566`
- writer-review WASM：`ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`
- Chrome：150系列；Firefox：153系列（headless WebDriver）

2026-08-07 收窄限制的那一輪：

- Profile：`e1-editor-v1`（wasm `835b453d…`、loader `1fe83aed…`、worker `e4f37ffe…`）
- Firefox 153.0.1 headless／geckodriver（stderr 已改 `DEVNULL`）
- 指令：`python3 tools/run_e1_c_session_depth.py --browser firefox --rung full --iterations 60`

2026-08-08 重跑那一輪：

- Profile：`writer-review`（wasm `ba257beb…`）配 `l4-stress-100`，與 2026-08-04 同一組
- Firefox 153.0.1 headless／geckodriver（`serve.py` 與 driver stderr 皆已非 pipe）
- 指令：`python3 tools/run_r7_longevity.py --browser firefox --scenario {s2-fresh,s3}
  --evidence-root findings/evidence/sdk-r7/longevity-post-023-fix`
- 位元組量測：`python3 tools/measure_geckodriver_stderr.py`（另兩輪加
  `--batches 6 --cycles {5,1} --log-level default`）

## 修訂紀錄

- **2026-08-08（第三次）：對抗性複核（目標是推翻本檔，結論未被推翻，但正文有五處要修）。**
  數字一律回核 `findings/evidence/` 下的 `result.json`／`serve.log`／原始碼。
  (1) 成本模型**不是循環論證**——擬合只用位元組總量，兩道牆沒進去；但它有一個沒申報的
  參數「pipe 起始存量」，已補上，並用 `monotonicSeconds` 重建 08-04 時間軸，證明前兩列
  確實是空 pipe（前隔 97.4 s／763.4 s），改用精確帳後兩列各差 416 B／696 B。
  單頁那列（34）改判為**初始條件不同**（接在 `s1`×3＋`s2-reuse` 後 12 s 共用 pipe），
  列為待驗證 9；無證據的第四列「同 process 換頁 ~38」從預測表移除。
  (2) `browserRootPids` 記的是 **geckodriver** 的 pid；per-profile 已由結構排除，
  **機器層資源從未被量測排除**；補上 batch-8 取證（頁面 92 ms `ready`、引擎資產送不到）
  與「08-08 前無版控，單變數宣稱不可查證」。
  (3) 記憶體節：`postCloseGrowth` 的首末相距 **30 代不是 40 代**，每代殘留改為
  1.9～2.6 MB、外推改為**第 207～281 代**（原 374 出自錯分母，190 是比例門檻）；
  這兩輪**四道門檻全過**，不是靠 `continuousThreeBlockGrowth` 放行；補上
  `maxPerDomain=64` 末塊只漲 2.1 MB 的 plateau 訊號與「回收延遲」對照假說；
  「門檻隱含低百位數上限」降級為推論，新增待驗證 10。
  (4) 換 artifact 的疑慮**比原本寫的小**：兩個 profile 共用同一個 `link_r5_product`、
  旗標逐字相同、wasm 只差 7.3 KB、頁面側 `terminate()` 同一份程式碼；真正的缺口改列為
  worker 側 dispose 不同、工作量不同、Chrome 無資料。
  (5) 引用者清單**漏了一半**：補列 `SPEC-E1-000`／`SPEC-E2-000`／`SPEC-E3-000`
  （先前漏列也漏標），把 R8-000／R8-D 由「已處理」改為「只處理了一半」，
  並新增七個程式碼站點與凍結矩陣的表。另修 `run_r7_compatibility.py:232` 寫死的
  `workerBudget`，並在該輪證據旁補 `NOTE.txt`。
- **2026-08-08（第二次）：把「50 代之上還有沒有牆」從推論變成已觀察。**
  新增〈`dom.workers.maxPerDomain` 判別〉：正控制 `=4` 讓第 1 代就死（證明 pref 生效
  且機制對它敏感）、判別 `=64` 仍 50/50 全過（若名額會漏，預測牆在第 8 代）。
  **頁內 `dispose()` 會即時歸還 worker 名額；024 的惰性回收只咬導覽拆除。**
  同時記錄記憶體殘留在兩輪都複製出來（+57.4／+70.3 MB，約 1.4～2.6 MB／代），
  並點明 `continuousThreeBlockGrowth` 閘門抓的是失控而非小而單調，
  以及三個涵蓋面缺口（僅 Firefox／單一壓力檔／R7 artifact 非 E1 產品 artifact）。
  `tools/run_r7_longevity.py` 新增 `--firefox-pref`（強制另給 `--evidence-root`，
  pref 輪永遠不會覆蓋正式序列）。條文仍未改。
- **2026-08-08：核心歸因撤回並改判。**用修好的 harness 重跑 `s2-fresh`（50/50）與
  `s3`（20/20）皆全過，記憶體斜率同時翻負；解出 `serve.py` 請求 log 的成本模型
  （877 B／導覽＋1614 B／cycle），預測 5-cycle 與 10-cycle 分批的牆為 36.6／38.5，
  實測 36／38。**牆是 finding 023 的 pipe，不是 Firefox。**2026-08-07 掛到 finding 024
  的歸屬已撤回（024 自身不受影響）。待驗證 3～6 結案，新增 7、8；新增〈下游影響〉
  列出八份規格的引用，並明寫不得自動撤限。2026-08-04 的〈已觀察〉全文仍未改。
- 2026-08-07：機制歸屬到 [finding 024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md)
  （上游 Firefox、Nightly 155.0a1 已修）；待驗證 1、2 標記完成；新增〈2026-08-07 重新分類〉
  逐項標歸屬，並記下兩件還沒對上的事（同頁 churn 未測、geckodriver stderr pipe 未排除）；
  以 `full` rung Firefox 60/60 把產品限制從「只能 reuse 單一 Worker」收窄成「必須明確拆除」。
  2026-08-04 的〈已觀察〉全文未改。

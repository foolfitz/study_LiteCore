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

本檔的產品限制被八份規格引用，全部建立在這個已撤回的機制上：

| 規格 | 引用內容 |
|---|---|
| ~~`SPEC-R7-D`~~ | **已處理（2026-08-08，§10.3）**：Firefox 正式九輪重跑 `summary.pass: true`，限制撤回。判定仍為部分 GO，但理由只剩 accessibility |
| ~~`SPEC-R7-000`~~ | **已處理（2026-08-08，v6）**：總判定保留項刪去「Firefox 無限 Worker generation」 |
| ~~`SPEC-R8-000`／`SPEC-R8-D`~~ | **已處理（2026-08-08，R8-D §10.1、R8-000 三處）**：Firefox combined-run 缺口補齊——compatibility 28/28、soak 30.07 分鐘、R8-C t0 46／t1 37。成因是 [finding 025](025-webdriver-script-injection-never-ran-on-firefox.md)。**T2 缺口與本檔無關，`PARTIAL_GO_LOCAL_DELIVERY` 判定不變** |
| `SPEC-E1-A` §4、`SPEC-E1-C` §2.1／§C2／§C4 | **「每頁 Worker generation 上限為 3」——前提已被實測推翻並就地標註，但條文未改**（見下節）。放寬與否會改變 E1-C 對外承諾與產品 reload 行為，屬產品決定 |
| `SPEC-R8-B`、`SPEC-R8-C`、`SPEC-E4-000`、`SPEC-R10-000` | generation budget／沿用上限：同樣已就地標註指回本檔，條文未改 |

**這些不會因為本檔撤回而自動失效**——要撤掉限制得各自重跑對應矩陣。**在那之前不得
把「上限已解除」寫進任何規格或產品。**（截至 2026-08-08：R7-D、R7-000、R8-000、R8-D
四份已用重跑證據處理完畢；E1／R8-B／R8-C／E4／R10 只標註前提不成立，**條文一律未改**。）

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

所以「每頁 3 個」在**兩種完全不同的工作量**下都被推翻：合成壓力檔（s2-fresh 單頁 50 代）
與正式相容性 corpus（R7-C 單頁 19 個 Worker）。

順帶一提，R7-D 對 Firefox `s2-fresh` 的**每 5 cycle 換一個瀏覽器行程**的分批策略、
以及 R7-C 的每頁 3 個上限，都是為了規避本檔而寫的；上面兩輪表示它們都可以退休
（**未執行**——改預設值會改變既有證據的取得形狀，屬產品／流程決定）。

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
每個 cycle 1614 B      （用 attempt-02/03 解，回代 attempt-01：預測 35,787 B ／實測 35,813 B，誤差 0.07%）
```

代進本檔四種分批形狀，和 2026-08-04 實測的牆並排：

| 形狀 | 每 cycle 位元組 | 預測撞 64 KiB 的 cycle | 實測 |
|---|---|---|---|
| 5 cycle／process | 1789 | **36.6** | **36**（第 8 個乾淨 process 的首個 init） |
| 10 cycle／process | 1702 | **38.5** | **38**（完成 37 後逾時） |
| 單頁不分批 | 1614 | 40.6 | 34 |
| 同 process 換頁 | 1614 | 40.6 | ~38 |

前兩列各差不到 1 個 cycle。更關鍵的是**方向**：批次越大、每 cycle 的導覽分攤越少、
牆越晚——實測 36 →38 完全符合。（第三列的 34 偏早，原始單頁那輪的組態沒有留在證據裡，
不強行對齊。）

**這也解釋了 2026-08-04 最反直覺的那一格**：第 8 個**全新** Firefox process 的第一個
init 就逾時（8 個 pid 各不相同，已查證）。瀏覽器行程內的累積解釋不了它；跨批次唯一共用
的東西就是那一個 `serve.py`。

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
   不能靠本檔撤回自動生效。

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

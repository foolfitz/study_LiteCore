# 023 — 同一個瀏覽器 session 反覆開檔到固定深度後，SDK init 永久卡住

| | |
|---|---|
| **狀態** | **已歸因（第二次）、已修**——機制是**探針基礎設施自己的 pipe 阻塞**：runner 用 `Popen(stderr=PIPE)` 啟動 `serve.py` 但從不讀取，HTTP 請求 log 塞滿 64 KiB pipe 後，handler 執行緒卡在 `log_message()`（在回應本體送出**之前**），之後所有 fetch 永遠等不到回應。修法＝server 輸出改導檔案（同時成為請求數證據）。 |
| **Bugzilla** | 不適用（我方 harness bug，非上游） |
| **發現日** | 2026-08-06（誤判為主機負載）／2026-08-07（第一次歸因：錯）／2026-08-07（第二次歸因：pipe，接手完成） |
| **嚴重度** | ~~高（阻斷 E1-C）~~ → **對產品零影響**；對 harness 是阻斷，已修。**但對「歷史結論」的破壞力比原先估的大**：2026-08-08 確認它也是 [finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)（Firefox 長壽 Worker 耗盡）的成因，而 014 的限制被 15 個規格檔（11 份帶現行條文）、7 個程式碼站點與 1 份凍結矩陣引用（2026-08-08 第三次複核更正，原記「八份規格」） |
| **可重現** | 100%，深度確定（修復前）；**修復後牆消失**（全部驗證輪通過） |
| **是否上游** | **否**——我方探針基礎設施 |
| **影響範圍** | 所有用 `Popen(stdout=PIPE, stderr=PIPE)` 開 `serve.py` 且不讀 pipe 的 runner（`run_e1_c.py`、`run_e1_c_session_depth.py` 已修；`run_r7_*.py`、`run_r8_*.py`、`run_finding_012.py` 同型未修，見「善後」） |

## 現象（不變，已觀察）

`run_e1_c.py` 把四個相位跑在同一個瀏覽器 session 裡。跑到某一次導覽時 init 再也不會完成：

```
SdkTimeoutError: init timed out after 120000 ms
workers: { created: 1, terminated: 0 }
operations: []
```

Chrome 有時死得更低層：driver 的 `Page.navigate` 等 180 秒等不到 readyState。
深度固定：正式矩陣（重工作）Firefox 22／Chrome 30；探針（輕工作）26／34。逐次重現。

## 第二次歸因：機制是 harness 的 pipe，不是瀏覽器、不是引擎

### 判別階梯全表（2026-08-07 接手後補完）

同一 `serve.py`、同一 navigate 迴圈，逐層抽換頁面內容。「牆」＝第一次失敗的導覽序號；
`—`＝跑滿未失敗（只證明牆＞迭代數，不證明無牆）：

| rung | 每次導覽做的事 | Chrome | Firefox |
|---|---|---|---|
| `inert` | 只設兩個 global | —(60) | —(60) |
| `worker` | 1 個 module worker，答一句即 terminate | —(60) | —(60) |
| `buffer` | ＋256 MiB SAB | —(60) | —(60) |
| `pool` | 8 worker 共用 1 GiB SAB，即 terminate | —(60) | —(60) |
| `wasmmem` | worker 內配 1 GiB shared `WebAssembly.Memory`，即 terminate | —(60) | —(60) |
| `wasmmem-keep` | 同上，**不 terminate**（導覽拆除） | —(60) | —(60) |
| `pool-keep` | pool 不 terminate | —(60) | **60** |
| `compile` | fetch＋`WebAssembly.compile` 真的 115 MB probe.wasm | —(60) | —(60) |
| `minimal` | 40 KB 模組、引擎同款連結參數（1 GiB shared memory＋7 pthread pool） | **62** | **55**（兩輪同） |
| `realinstant` | 真的 probe.js/probe.wasm 實例化＋FS 映像，不呼叫 engine_start | **54**（兩輪同） | **8** |
| `enginestart` | 真的 SDK init 鏈（含 `oxsdk_engine_start`），不開文件 | —(45) | **8** |
| `full` | 真的 E1-C 頁 | **34**（三輪同） | **26**（兩輪同） |

（已觀察）牆的位置與「每次導覽產生幾行 HTTP 請求 log」成反比：請求越多，牆越淺。
Firefox 的 `realinstant`／`enginestart` 死在 8 是**另一個機制**（見 finding 024），不在本表的規律內。

### 現場鐵證（已觀察，2026-08-07 14:09）

full／chrome 卡在第 34 次導覽的當下，從 `/proc` 直接看：

- `serve.py` 的 handler 執行緒 `wchan=anon_pipe_write`——**卡在寫 log**；
- **chrome 全行程樹沒有任何執行緒阻塞**（同刻掃描 `blocked:none`）；
- 幾分鐘後接手跑的 `realinstant` runner，它的 `serve.py` 也已有執行緒卡在 `anon_pipe_write`。

存檔：`evidence/sdk-e1/editor-validation/session-depth/pipe-forensics/live-wchan-capture.txt`。

機制鏈（已觀察＋標準庫語意）：`BaseHTTPRequestHandler.send_response()` 先呼叫
`log_request()` 才送狀態列與 headers → log 寫進的是 runner `Popen(stderr=PIPE)`
**從不讀取**的 pipe → 累積 64 KiB 後 `write()` 阻塞 → 該請求連狀態列都送不出去 →
後續每個請求排隊撞上同一條滿的 pipe → 整個站停止回應。HTML 請求先撞上→
`Page.navigate` 逾時；資源請求先撞上→ SDK init 逾時、零事件。**兩種死法、一個機制。**

### 為什麼深度固定、重工作先撞牆（已觀察→推論）

每次導覽的請求序列固定 → log 位元組數固定 → 累積穿過 65536 的導覽序號固定。
重工作＝每格請求更多（壓力檔、崩潰情境重載）＝更早穿過。兩瀏覽器請求模式不同
（cold 模式下 Firefox 平均每導覽 2431 B、Chrome 1902 B）→ 牆不同。

### 對帳（已觀察，修復後的 serve.log 實測）

| 執行 | 實測 log／導覽 | 65536 穿過點（預測牆） | 原觀察牆 |
|---|---|---|---|
| full／chrome | 1902 B | 第 35 次 | **34** |
| full／firefox | 2431 B | 第 28 次 | **26**（原始輪 geckodriver 少量輸出共用同 pipe，會再早一點） |

### 驗證輪（已觀察，修復後）

| 執行 | 修復前牆 | 修復後 |
|---|---|---|
| full／chrome 45 輪 | 34（三輪同） | **45/45 全過** |
| full／firefox 30 輪 | 26（兩輪同） | **30/30 全過** |
| minimal／chrome 120 輪 | 62 | **120/120 全過** |

## 撤回的結論（保留為紀錄，別再引用）

- ~~「剩下只有載入並初始化 LibreOffice WASM 模組那一層會卡」~~——階梯當時還沒把
  server 這一層放進變因裡。**對照組跟實驗組共用同一個帶 bug 的 server**，於是「牆」
  跟著每導覽請求數走，被讀成了「跟引擎有關」。
- ~~「真實使用者開分頁工作一天會踩到同一件事」（產品影響段）~~——真實部署沒有
  「把 server 的 stderr 接到 64 KiB 沒人讀的 pipe」這種東西。**產品不受此機制影響。**
  產品在 Firefox 上另有真實風險，見 [finding 024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md)。
- ~~「heavy host load」（2026-08-06）~~——維持撤回。

## 方法論教訓（寫給下一個做判別階梯的人）

1. **對照組與實驗組共用的基礎設施，本身就是一個 rung。**這次所有 rung 共用同一個
   `serve.py`，而變因恰好藏在「頁面產生多少請求」——一個看似中性的共用層把
   工作量變因偷渡成了基礎設施變因。
2. **「60/60 通過」只證明牆＞60。**minimal／chrome 第一輪 60 輪全過，第二輪 120 輪
   死在 62。差兩輪就把一個 rung 誤判成乾淨。
3. **量測要含「量測設施自己」**：這次真正破案的是 `/proc` 的 `wchan`，不是頁面內的
   任何數字。

## 修法（已完成）

- `tools/run_e1_c_session_depth.py`、`tools/run_e1_c.py`：server 輸出改導
  evidence 目錄下的 `serve.log`（行緩衝；log 同時成為每導覽請求數的證據），
  並在每輪記錄 `serveLogBytesAfter`。
- `tools/run_browser_probe.py`：`ChromeSession`／`FirefoxSession` 的瀏覽器行程
  輸出改 `DEVNULL`（原本也是沒人讀的 PIPE，同型潛在 bug）。

## 善後（2026-08-07 完成）

- [x] **同型 `Popen(PIPE)` 已掃遍全部 tools**（2026-08-07）。修了 20 個檔：
  - serve.py 未讀 pipe → `DEVNULL`＋註解：`run_r7_compatibility`、`run_r7_input`、
    `run_r7_usability`、`run_r7_longevity`、`run_finding_012`、
    `run_finding_012_remediation`、`run_finding_016_scheduler`、
    `run_finding_016_selection_barrier`、`run_e1_bold_noop`、`run_e1_discovery`、
    `run_e1_b`、`run_e2_discovery`、`run_r6_browser`、`run_r6_discovery`、
    `run_r7_discovery`、`run_r6_reference`（node server 同型）。
  - r8 系（stop 時把 stdout/stderr 收進證據，`communicate()` 排空得太晚）：
    `run_r8_production`、`run_r8_delivery`、`run_r8_service_worker`、
    `run_r8_discovery` 改 `spawn_captured()`（導暫存檔）＋ `drain_captured()`
    （停止時讀回），證據形狀不變。
  - 確認無虞而未改：`subprocess.run(...)`（即排空）、
    `run_finding_012_attribution`（`communicate(timeout)` 即排空）、
    `create_test_docs` 的 soffice（輸出遠低於 64 KiB）。
- [x] ~~**r7 longevity 歷史已重看**（2026-08-07）：其執行形狀是「一兩次導覽＋頁內
  循環」，請求量遠低於任何 64 KiB 穿過點——**歷史結論無需因 pipe 作廢**。
  兩筆 firefox 失敗（`s2-fresh`、`s3`）都不是 init 卡死：`s2-fresh` 35 輪全過、
  敗在記憶體成長閘門（+34 MB/block、post-close +2.75%）——此形狀與
  [finding 024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md)
  的惰性回收一致（推論，未重跑驗證）；`s3` 是非掛死的屬性失敗。~~
- [x] **上一條整條作廢（2026-08-08 重跑推翻）。**三個事實都反了：
  1. **兩筆都是 init 卡死。**`s2-fresh` 敗在 batch 8（`.../batches/batch-8/result.json`）、
     `s3` 敗在第 20 個 crash cycle，錯誤字串同為
     `SdkTimeoutError: init timed out after 120000 ms`。`s2-fresh` 的記憶體閘門
     `pass: false` 是**衍生**——三個門檻值當時就全部合格，只是 50 輪只跑到 35 輪、
     樣本數不足。
  2. **請求量遠遠不低。**每個 cycle 都會重新抓引擎模組；量出來是
     **877 B／導覽＋1614 B／cycle**，5-cycle 分批＝1789 B／cycle，
     **第 36.6 個 cycle 就填滿 64 KiB**（實測牆 36），10-cycle 分批預測 38.5（實測 38）。
     當年是「一兩次導覽」這個印象錯了——導覽少，但頁內每輪都在抓 115 MB 模組。
  3. **歷史結論必須作廢。**用修好的 harness 原封不動重跑：`s2-fresh` **50/50**、
     `s3` **20/20** 全過，記憶體斜率從 +34 MB 翻成 −5.4 MB。
     證據 `evidence/sdk-r7/longevity-post-023-fix/firefox/{s2-fresh,s3}/run-1/result.json`。

  →**本 finding 的影響範圍比原本記的大**：它不只咬 E1-C，也是
  [finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) 的成因，
  而 014 的產品限制被 **15 個規格檔（11 份帶現行條文）、7 個程式碼站點與 1 份凍結矩陣**引用
  （見該檔〈下游影響〉；2026-08-08 第三次複核更正，原記「八份規格」）。
  教訓照抄一次：**「執行形狀看起來很輕」是印象，不是量測。**把同一件事量成位元組只花了幾分鐘。
- [x] **E1-C 四個自動相位已用修復後 harness 重跑**（2026-08-07，chrome＋firefox
  `--phase all` 皆 `pass: true`——lifecycle 首次在單一 session 內完整跑完）。
  `validate_e1_c.py`：`automaticPass: true`、`artifactBinding` **48 個 case 全數
  綁定 `835b453d…`（0 superseded）**、裁決 `E1_PARTIAL_GO_ODT_EDITOR`，唯一缺
  `trustedManualDelta`＝人工 Chewing 輪（需操作者，`ssh -L 8765:127.0.0.1:8765`，
  見 SPEC E1-C §11.5）。

## 重現（修復前的行為，僅為歷史紀錄）

修復後已不可重現。歷史序列都在
`evidence/sdk-e1/editor-validation/session-depth/<rung>/<browser>/`（首輪）與
`.../attempt-NN/`（後續輪）；`serve.log` 只存在於修復後的輪。

## 時間軸

- 2026-08-06 矩陣首見，誤判 heavy host load
- 2026-08-07 上午 第一次歸因：判別階梯四 rung，誤結論「只剩引擎層」；交接
- 2026-08-07 下午 接手：階梯補到 12 rung；`minimal`（零 LibreOffice）也撞牆 →
  引擎排除；`/proc` 抓到 `serve.py` 卡在 `anon_pipe_write` → 機制確定；
  修 runner；三個驗證輪牆全部消失；位元組對帳吻合（差 1–2 導覽）
- 2026-08-07 下午 Firefox 側「8 的牆」與 worker 名額惰性釋放獨立成 finding 024
- 2026-08-08 「r7 longevity 歷史無需作廢」被自己的重跑推翻：`s2-fresh` 50/50、
  `s3` 20/20，成本模型（877 B／導覽＋1614 B／cycle）預測牆 36.6／38.5 對上實測 36／38；
  finding 014 的成因確定為本 finding

## 修訂紀錄

- 2026-08-08（第三版）：撤回 2026-08-07 的「r7 longevity 歷史無需作廢」善後結論——
  該結論的三個前提（不是 init 卡死、請求量低、無需作廢）逐一被證據推翻。
  補上位元組成本模型與兩個情境的重跑結果；影響範圍改寫，接上 finding 014。
- 2026-08-07（第二版，接手改寫）：歸因由「LibreOffice WASM 模組載入初始化層」
  改為「探針基礎設施 pipe 阻塞」；撤回產品影響段；補全階梯、現場證據、對帳、
  驗證輪；狀態改「已修」。第一版全文脈絡保留於
  [HANDOFF-2026-08-07-finding-023.md](../handoff/HANDOFF-2026-08-07-finding-023.md)。
  （原文寫「保留於 git 歷史與 HANDOFF」——**當時沒有 git 歷史**，本樹到 2026-08-08
  才建 repo，第一版原文只存在於那份 HANDOFF。已更正，不留錯誤指路。）

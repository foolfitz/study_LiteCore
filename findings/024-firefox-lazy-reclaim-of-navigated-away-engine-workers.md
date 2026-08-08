# 024 — Firefox 對導覽拆除的 pthread 池 worker 惰性回收：記憶體與 worker 名額兩種預算，先到先死

| | |
|---|---|
| **狀態** | 已確認，且**上游已在 Nightly 155.0a1 修復**（2026-08-07 實測；153 現行 release 仍中）。是否回報（如請求 uplift）待使用者決定 |
| **Bugzilla** | Mozilla（不是 tdf）：查重完成、未送 |
| **發現日** | 2026-08-07（finding 023 判別階梯的副產物；與 023 的 pipe 機制**無關**，probe 基礎設施修復後仍完整重現） |
| **嚴重度** | 產品面：一般（只咬「導覽離開卻不先 dispose」的模式；有明確產品側對策；且上游已修，隨版本淘汰） |
| **可重現** | 100%（記憶體預算三輪皆第 8 次；worker 名額 stock 牆 65～66、pref=64 牆 9；driver 與無 driver 兩種 harness 數字一致） |
| **是否上游** | **是（Firefox 153.0.1）**；**Nightly 155.0a1（BuildID 20260806211740）已修**；Chrome 150 不受影響（同 rung 全部乾淨） |

## 現象

同一個 Firefox session 裡反覆「導覽到一個會實例化 pthread wasm 引擎的頁面」，
**且頁面不在導覽前明確 terminate worker**，數次之後 init 再也不會完成。
兩種收場，看哪個預算先用完：

1. **記憶體**：`WebAssembly.instantiate` 快速 `abort`（emscripten
   `instantiateArrayBuffer` 路徑），前幾輪行程 RSS 呈階梯上升。
2. **worker 名額**：init 靜默逾時、零錯誤零事件——新 worker 被
   `dom.workers.maxPerDomain`（預設 512）的排隊機制吊住，永不啟動。

## 證據（全部在 `evidence/sdk-e1/editor-validation/session-depth/`）

引擎形狀：`-pthread -sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7`（1 個 worker ＋
7 個池 worker 共用 1 GiB shared `WebAssembly.Memory`）。「keep」＝worker 存活到
導覽拆除（真 harness 的形狀）；probe server 的 pipe bug（finding 023）修復前後
各測，本 finding 的數字**修復後不變**。

### 預算一：記憶體（已觀察）

| rung | 每導覽實例化 | Firefox 牆 | RSS 階梯 |
|---|---|---|---|
| `realinstant` | 真的 115 MB probe.wasm＋FS 映像 | **8**（修復前後、共三輪） | 1.45→5.49 GB（+0.6～0.7 GB/導覽） |
| `enginestart` | 同上＋`oxsdk_engine_start` | **8** | 1.77→7.19 GB（+0.9 GB/導覽）；maxVms 12→41 GB |

第 8 輪的失敗是 `abort@…probe.js / instantiateArrayBuffer`，1.9 秒內——是配置
失敗，不是逾時。（推論：死在配下一個 1 GiB shared memory 或大型模組結構；
前 7 輪的實例還沒被 GC 回收。）

### 預算二：worker 名額（已觀察）

| rung | 條件 | Firefox 牆 | 執行緒序列 |
|---|---|---|---|
| `minimal`（40 KB 模組、同連結參數） | stock（512） | **66**（server 修復後） | 308 → 平頂 ~500–512 → 死 |
| `minimal` | `dom.workers.maxPerDomain=64` | **9** | ~356 就死（cap 64 ÷ 每導覽漏 8 個 ≈ 8） |

死法是「engine-shape worker did not answer within 120000 ms」——**零錯誤**。
與 [Firefox 的 worker 排隊語意](https://searchfox.org/firefox-release/source/modules/libpref/init/all.js)
一致：超過 per-domain 上限的 `new Worker()` 排隊等既有 worker 死亡，不報錯。
pref 把牆等比例搬動＝歸因閉合。

### 對照（已觀察）

- **Chrome 150 全部同型 rung 乾淨**：`wasmmem-keep` 60、`pool-keep` 60、
  `enginestart` 45、`minimal` 120（server 修復後）——Chrome 對導覽拆除的
  worker／記憶體回收得夠快。
- **`pool-keep`（8 個純 idle module worker ＋ 1 GiB SAB，keep-alive）Firefox
  修復後 80/80 乾淨**、執行緒全程平坦——惰性的是**阻塞在 futex 等待的
  pthread 池 worker**，不是任何 worker。
- **`full`（每導覽 close→terminate）Firefox 30/30 乾淨**——明確拆除完全避開
  兩種預算。這就是產品對策。

## 分析

Firefox 導覽離開頁面後，該頁的 dedicated worker（尤其阻塞在 `Atomics.wait`／
futex 的 emscripten pthread 池）與其持有的 shared wasm memory **等 GC 才回收**，
且 GC 在連續導覽的壓力下追不上（已觀察：執行緒數僅以 ~+4.6/導覽爬升而非 +8，
表示有部分回收但淨值持續為正）。近緣的已知問題：
[Mozilla bug 1576829「Memory leak on page refresh」](https://bugzilla.mozilla.org/show_bug.cgi?id=1576829)、
[emscripten #8571（Chrome 版同型抱怨，2019）](https://github.com/emscripten-core/emscripten/issues/8571)。
（推論：worker 名額釋放同樣綁在這條惰性路徑上，所以兩種預算同根。）

### 與 finding 014 的關係（2026-08-08 改寫）

[finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)（2026-08-04，
「Firefox 長壽程序反覆建立大型 WASM Worker 後 init 耗盡」）曾在 2026-08-07 被掛到本
finding 名下。**2026-08-08 已撤回那個歸屬**：014 的核心證據（R7-D `s2-fresh`／`s3`）
用修好的 harness 重跑後 **50/50、20/20 全過**，牆的成因是
[finding 023](023-sdk-init-wedges-at-fixed-session-depth.md) 的 `serve.py` unread pipe
（成本模型 877 B／導覽＋1614 B／cycle，預測牆 36.6／38.5，實測 36／38）。

留下的仍然成立：

- 014 的待驗證第 1 條——「建立不含 LibreOffice core、但使用相同 Emscripten
  pthread／WASM memory 設定的最小重現，區分 browser 與 core」——**正是本 finding 的
  `minimal` rung**，該問題已由本 finding 回答（就本 finding 自己的形狀而言：是 browser）。
- 014 的 R7-C／R8-D 兩組觀察**歸屬未定**（原記本 finding，已降級）：同一支 harness、
  同一條 pipe 當時都在，未重跑。R8-D 那筆的 server pipe 已排除
  （`r8_delivery_server.py:73` 的 `log_message` 是 no-op），但 geckodriver 轉發 Firefox
  stderr 的那條未排除——實測正常僅 1,290 B／session，卻曾偶發爆到 101～110 KB
  （CRLite／RemoteSettings 失敗），而 R8-D 正是「同一 session 等滿 900 秒」的形狀。

**本 finding 自身完全不受影響**——數字是在三條 pipe 全修之後重測的，Nightly 對照
還走無 driver 模式，`minimal` rung 也不經過 `serve.py` 的重工作量路徑。

## 產品影響與對策

會踩到的形狀：**SPA 以外的「每份文件一次導覽」部署**，或使用者直接關頁籤前
的任何導覽——若頁面不先拆引擎，Firefox 使用者在單一分頁連續開 ~7 份（大檔）
或 ~60 份（小引擎）之後 init 靜默卡死。

對策（產品側，已由 `full` rung **Firefox 60/60** 驗證同型有效——執行緒全程在 274–292
之間振盪、無單調上升，行程樹記憶體亦無階梯（對照 `enginestart` 的 +0.9 GB／導覽）；
證據 `.../session-depth/full/firefox/attempt-04/result.json`。
（該輪原本是為了越過 finding 014 的第 36 個 worker 才加跑到 60；014 那道牆
2026-08-08 已改判為 finding 023 的 pipe，但這 60/60 對**本 finding**的對策仍是有效證據。））：
- **pagehide／beforeunload 時明確 `engine.dispose()`**（terminate SDK worker →
  池 worker 隨之死亡、名額即時歸還、記憶體可即回收）。
- 現行 `EditorSession` 生命週期（close→terminate）已是這個形狀；要補的是
  「使用者沒走 close 就導覽」的路徑。

**「名額即時歸還」已由直接量測證實（已觀察，2026-08-08）**，不再只是推論：把預算縮到
`dom.workers.maxPerDomain=64`（＝8 代份的名額）後，**同一個頁面連續 50 代全過**
（50 建 50 拆、active 0）——若頁內 `dispose()` 也像導覽拆除那樣惰性，牆會在第 8 代。
同組的正控制 `=4`（比一代所需的 8 還少）讓**第 1 代**就以本 finding 的靜默排隊簽章死掉
（`init timed out after 120000 ms`、零 worker 錯誤），證明 pref 確實生效。
**本 finding 的惰性回收只咬導覽拆除，不咬頁內 dispose**——這正是上述對策有效的機制。
證據：`findings/evidence/sdk-r7/single-page-generations-pref/maxperdomain-{4,64}/firefox/s2-fresh/run-1/result.json`
（詳見 [finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)〈`dom.workers.maxPerDomain` 判別〉）。

## 還缺什麼才能送（Mozilla）

- [x] **最小重現頁已完成並自測**（2026-08-07）：
  [`findings/repro/024-firefox-worker-reclaim/`](repro/024-firefox-worker-reclaim/)
  ——自包含（自我重導覽頁＋40 KB pthread 模組＋COOP/COEP server＋stdlib-only
  的 `check.py` 自動化）。stock Firefox 153 實測：worker 名額路徑 **WEDGED at 65**
  （與 probe 的 66 同帶；頁面請求重量不同）。過程插曲：第一版 `?touch` 分支從
  位移 0 `fill` 整塊記憶體，把 runtime 靜態區輾平——commit 頁面要從記憶體頂端
  往下填。
- [x] **Bugzilla 查重完成**（2026-08-07）：無現成票描述「名額被已導覽離開頁面的
  pthread worker 佔住」。最近緣：
  [1052398](https://bugzilla.mozilla.org/show_bug.cgi?id=1052398)（超額 worker
  靜默排隊，行為本身 by design）、
  [1286895](https://bugzilla.mozilla.org/show_bug.cgi?id=1286895)（512 上限的
  由來）、[1592227](https://bugzilla.mozilla.org/show_bug.cgi?id=1592227)（wasm
  worker busy count／GC，經 bug 1836700 大修）、
  [1576829](https://bugzilla.mozilla.org/show_bug.cgi?id=1576829)（重整記憶體
  洩漏）。回報時應引用這四張說明增量。
- [x] **Firefox Nightly 155.0a1 重測完成（2026-08-07）：已修。**
  無 driver 模式（snap 系統版讀不到 /tmp profile，geckodriver 0.37 又拒認
  nightly 的 binary，故以 serve.log 的 `?n=K` 序列判讀進度；此模式先以 stock
  153 驗證——牆 65／pref64 牆 9，與 driver 模式完全一致）：
  - default：**1343** 次導覽無牆（200 秒；stock 153 牆 65）
  - pref `dom.workers.maxPerDomain=64`：**624** 次無牆（stock 153 牆 9）
  - touch=700：**286** 次無牆
  每輪皆實測 worker.js×1＋minimal.js×8＋wasm×1（pool 完整起動）。
  證據：`evidence/sdk-e1/editor-validation/session-depth/finding-024-nightly/`。
- [x] M2（記憶體預算）極小化**兩次嘗試都失敗，負結果已記錄**：commit shared
  memory 頁（頂端填充）與 700 MiB JS-heap 壓艙物都跑到 worker 名額牆（65）而
  非記憶體牆——FF 對 SAB commit 與有 GC 壓力的 JS heap 都回收得掉；@8 的
  abort 需要「大模組編譯碼＋綁定的 1 GiB shared memory」組合（真引擎 115 MB
  模組三輪重現）。極小頁只覆蓋 M3；M2 對 Mozilla 需引導其用大型 pthread
  模組重現。
- [ ] 送出與否（需使用者決定與帳號）：上游已修，回報價值剩「請求 uplift 到
  release／beta」或 webcompat 紀錄；亦可用 mozregression 定位修復 changeset
  佐證（未做）。

## 環境

Firefox 153.0.1（headless，geckodriver）；Chrome 150.0.7871.128（headless=new）；
Linux 7.0.0-28-generic；emscripten 4.0.10。

## 時間軸

- 2026-08-07 finding 023 階梯中發現（`realinstant`/FF 死在 8 與其他 rung 的規律不合）
- 2026-08-07 pref 實驗（`dom.workers.maxPerDomain=64` → 牆 9）釘死 worker 名額機制
- 2026-08-07 probe server 修復後全數重現不變 → 與 023 切割、獨立成案
- 2026-08-07 回頭接上 [finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)：
  014 的待驗證 1、2 由本 finding 完成；`full` rung 加跑到 60/60
- 2026-08-08 **014 的歸屬撤回**：其 R7-D 證據重跑全過，牆改判為 finding 023 的 pipe。
  本 finding 的證據、機制與對策不受影響（見上節）

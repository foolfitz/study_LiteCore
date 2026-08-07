# Findings — 上游問題紀錄

發現當下記完整，之後統一回報。

相關：[`../QA-GUIDE.md`](../QA-GUIDE.md)（怎麼參與 QA）、[`../wasm-lite/README.md`](../wasm-lite/README.md)（建置規劃）

---

## 清單

| # | 標題 | 狀態 | 嚴重度 | 上游？ | tdf# |
|---|---|---|---|---|---|
| [001](001-wasm-configmgrwriter-crash.md) | WASM `--disable-symbols` 破壞 C++ 例外處理，啟動即崩潰 | **可送出** | 阻斷 | 是 | — |
| [002](002-vcldemo-missing-fs-image.md) | qt_vcldemo.html 沒連結 fs image，README 卻要人跑它 | 可送出 | 一般 | 是 | — |
| [003](003-unpackedtarball-dir-race.md) | UnpackedTarball.mk 的 .version 缺 .dir 相依，-j 下 race | 可送出 | 一般 | 是 | — |
| [004](004-emscripten-install-partial-symbols.md) | Emscripten 部分符號建置未產生 soffice `.dwp`，封裝失敗 | 待驗證 | 一般 | 未確認 | — |
| [005](005-qt5-wasm-no-input-context.md) | Qt5 WASM 無 input context，CJK 輸入完全不可行 | 可送出 | 嚴重 | 是 | — |
| [006](006-qt6-wasm-stale-eventlistener-export.md) | Qt 6.10 WASM/JSPI 仍匯出已移除的 EventListener 符號 | 待驗證（連結通過） | 阻斷 | 未確認 | — |
| [007](007-qt6-wasm-pointerenter-null-dom-node.md) | Qt 6.10 WASM/JSPI 延遲 pointer-enter 以 null DOM 節點退出 | 本地修補已驗證 | 阻斷 | 未確認 | — |
| [008](008-qt6-wasm-inputcontext-invalid-emval-value.md) | Qt 6.10 WASM input context 跨 pthread 使用 DOM emval handle | 本地修補已驗證 | 阻斷 | 未確認 | — |
| [009](009-qt6-wasm-duplicate-english-key-input.md) | Qt6-WASM Writer 英文按鍵重複輸入 | 待驗證（首度觀察） | 嚴重 | 未確認 | — |
| [010](010-probe-export-list-requires-unoembind.md) | Core Emscripten exports 清單與「不連 unoembind」的外部 probe 規格衝突 | 已解決 | 阻斷 | 否（專案規格） | — |
| [011](011-sdk-worker-search-not-found-json-parse.md) | Document SDK Worker 將 search-not-found 純文字 payload 當 JSON 解析 | 已修（跨瀏覽器／R1～R5 回歸） | 嚴重 | 否（專案 Worker） | — |
| [012](012-r6-styled-document-close-timeout.md) | writer-review 對t2 image frame直接paragraph wrapper的open→close不回應 | **SDK bounded Worker recovery已修；core teardown根因保留** | 阻斷 | 未確認 | — |
| [013](013-sdk-open-name-rejects-docx-before-content-detection.md) | Document SDK 在 content detection 前拒絕 `.docx` 名稱，DOCX import 邊界與 bytes 能力不一致 | 已確認 | 嚴重 | 否（專案 SDK） | — |
| [014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) | ~~Firefox長壽程序反覆建立大型WASM Worker後init耗盡~~ | **2026-08-08 核心歸因撤回：不是Firefox，是[023](023-sdk-init-wedges-at-fixed-session-depth.md)的unread `serve.py` pipe。**修好後原封重跑`s2-fresh` **50/50**、`s3` **20/20**全過，記憶體斜率翻負；成本模型877 B/導覽＋1614 B/cycle預測牆36.6／38.5，實測36／38。~~歸屬024~~已撤回（024自身不受影響）。geckodriver pipe已量（常態1,290 B/session、偶發101～110 KB）：對本檔排除，**對R8-D未排除**。R7-C／R8-D歸屬**未定**，未重跑。**八份規格引用的Worker generation限制須各自重跑才能撤** | ~~嚴重~~→**已撤回（我方harness）** | ~~是~~→**否** | — |
| [015](015-firefox-fetch-content-length-mismatch.md) | Firefox對部分Content-Length不符回應仍可能resolve fetch | **已確認／R8-A/B完整性契約已驗證** | 一般 | 否（browser相容性） | — |
| [016](016-lok-forward-delete-completion-gap.md) | forward delete已改文件，但SDK未建立可歸屬completion | **已修（selection barrier）；邊界拒絕後需fresh Worker** | 已解除阻斷 | **否** | — |
| [017](017-lok-collapsed-selection-readback.md) | selection reset後文字readback回unsupported UTF-16 flavor，SDK無法表示空selection | **已修（SDK側）／實測通過，不再阻斷** | 阻斷 | 未確認 | — |
| [018](018-lok-line-navigation-completion-nondeterministic.md) | Writer line navigation callback completion不具重複執行確定性 | **已確認；2026-08-06 已歸因**：移動沒壞，壞的是 visible-cursor completion 訊號需要活迴圈；Shift 模式兩 profile 皆 36/36 | 一般 | 未確認 | — |
| [019](019-e1a-paragraph-style-mapped-to-ui-alias.md) | E1-A段落樣式映射到UI別名，該名稱不是可派送命令 | **已確認／E2-A已定位修法** | 嚴重 | 否（專案SDK映射） | — |
| [020](020-lok-list-command-result-contradicts-document.md) | LOK清單命令的command result與文件實際結果矛盾 | **已確認（原生26.8＋WASM兩瀏覽器）／待搜重複單** | 嚴重 | 候選為是 | — |
| [021](021-wasm-format-state-not-refreshed-by-caret-movement.md) | WASM段落格式state不隨caret移動更新，barrier前置條件會讀到別段的值 | **已歸因到底：缺口在PEI語意；產品路線C＝不讀前置狀態，上游暫緩** | 嚴重 | **否** | — |
| [022](022-e1-release-set-bold-false-noop.md) | 已出貨的e1-editor-v1回報假`documented-state-noop`，按粗體／斜體／取消粗體都可能什麼都沒發生 | **已修並重新凍結**（WASM `94b38437…`→`97e605ee…`；兩瀏覽器驗證關閉、E1＋R6～R8全回歸） | 嚴重 | **否** | — |
| [023](023-sdk-init-wedges-at-fixed-session-depth.md) | 同一瀏覽器session反覆開檔到固定深度後SDK init永久卡住（Firefox 22／26、Chrome 30／34，逐次重現） | **已歸因（第二次）、已修**：機制是探針基礎設施的pipe阻塞（runner從不讀serve.py的stderr pipe，64 KiB塞滿後HTTP handler卡在`anon_pipe_write`）；`/proc`現場鐵證＋位元組對帳＋修復後牆全消失（full 45/45、30/30；minimal 120/120）；產品不受影響。**2026-08-08：善後那條「r7 longevity歷史無需作廢」已撤回**——它也是[014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)的成因（`s2-fresh` 50/50、`s3` 20/20重跑全過），影響範圍比原估大 | ~~高~~→harness（但作廢的歷史結論更多） | **否（我方harness）** | — |
| [024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md) | Firefox對導覽拆除的pthread池worker惰性回收：連續導覽~8次（1 GiB引擎、記憶體預算）或~65次（worker名額預算，`dom.workers.maxPerDomain`）後init靜默卡死 | **已確認、Nightly 155.0a1已修**（153仍中）：pref=64把牆從65移到9（歸因閉合）；nightly 1343/624次無牆；自包含重現`findings/repro/024-firefox-worker-reclaim/`；Chrome不受影響；產品對策＝pagehide明確dispose()。2026-08-08 **[014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)的歸屬已撤回**（那是023的pipe），本finding自身證據不受影響 | 一般 | **是（FF 153；155已修）** | 未送（僅剩uplift價值，待使用者） |

**狀態**：`待驗證` → `可送出` → `已回報` → `已修` ／ `撤銷`

---

## 為什麼要這樣記

「先做完再一起回報」有兩個必然的損耗，這份結構就是在擋它們：

1. **細節會蒸發。** 版本號、確切的錯誤訊息、你當時排除過哪些可能 —— 三天後就模糊了，而這些正是 triager 判斷要不要收單的依據。所以**證據存檔案，不存腦袋**。
2. **會忘記自己還沒證明什麼。** 每張單都有「還缺什麼才能送」的核取清單。這是最重要的一段 —— 沒它的話很容易把還沒驗證的猜測當成結論送出去，被退一次之後，你之後的回報都會被當成低品質來源。

---

## 實驗型專案的留痕層級

不是每個觀察都是上游 bug，但值得影響後續判斷的資訊都不能只留在 console、聊天或記憶裡。依下表
選擇紀錄位置：

| 情況 | 紀錄位置 | 最低內容 |
|---|---|---|
| 當輪假設、嘗試、否證、取捨或已知限制 | 對應 `DEVLOG-<日期>-*.md` | 做了什麼、預期、實際、因此決定什麼 |
| 測試／量測原始輸出 | `findings/evidence/<finding 或 sdk-rN>/` | 環境、artifact hash、輸入、原始結果 |
| 可重現且會影響架構、SDK 邊界、相容性或排程的發現／阻礙 | 編號 finding | 最小重現、證據、事實／推測、影響、下一步 |
| 可送 LibreOffice／工具鏈上游的問題 | 編號 finding + Bugzilla 欄位 | 另補上游預設組態、重複單搜尋與 component |

編號 finding 可以是上游問題，也可以是「我方規格或架構假設被否證」。`是否上游` 欄位必須如實標記，
不能因為不準備送 Bugzilla 就不記錄。

### 何時應立即停下來寫

- 同一失敗已重現兩次，下一次嘗試沒有新增可區分原因的證據。
- 結果迫使我們改 API、協定、資料模型、建置 profile 或 Go／No-Go 條件。
- 不同瀏覽器、artifact 或 build 得到互相矛盾的結果。
- workaround 會擴大公開 surface、修改 LibreOffice core 或降低資料完整性保證。
- 一個「暫時限制」可能被後續工作誤認為已完成能力。

先保存當下環境與原始輸出，再整理文字。每則結論分成：

- **已觀察**：由原始輸出、hash、程式碼或可重現步驟直接支持。
- **推論**：目前最合理的解釋，但尚缺決定性實驗。
- **待驗證**：下一個能區分推論的最小測試。

里程碑結束時，machine summary 只負責回答閘門；DEVLOG／finding 必須保留失敗路徑與限制，不能用最後
一次 `pass: true` 覆蓋實驗歷程。

---

## 怎麼新增一張

```bash
cd findings
cp TEMPLATE.md 004-短描述.md
mkdir -p evidence/004
./env-snapshot.sh > evidence/004/env.txt     # ← 一定要在發現當下跑
```

然後把 `004` 加進上面的清單。

### 存證據的時機

**發現當下就存，不要等。** 重編、換分支、改旗標之後就重現不出來了。

| 要存的東西 | 怎麼取得 |
|---|---|
| 環境 | `./env-snapshot.sh > evidence/NNN/env.txt` |
| 瀏覽器主控台 | `wasm-lite/tools/pw/probe.js`（見下） |
| 建置錯誤 | 從 `wasm-lite/logs/*.log` 節錄，含前後文 |
| 原始碼片段 | 一定要附 commit hash，行號會漂 |
| 截圖 | probe.js 會自動存 |

---

## 工具

### `env-snapshot.sh`

產生環境區塊。會自動偵測原始碼樹**有沒有本地修改** —— 這點很關鍵：帶著本地 patch 重現出來的問題，不講清楚就送出去等於浪費雙方時間。

```bash
./env-snapshot.sh                              # 預設 wasm-lite/build
BUILDDIR=../wasm-lite/build-stock ./env-snapshot.sh
```

### `wasm-lite/tools/pw/probe.js`

用 Playwright 開一個無頭 Chromium，把主控台、網路請求、page error、worker 事件全部按時間軸記下來，最後印出頁面狀態並截圖。

```bash
cd wasm-lite/tools/pw
node probe.js <URL> [秒數] [截圖路徑]
```

001 和 002 的區別就是靠它的**網路請求時序**分辨出來的（vcldemo 從頭到尾沒請求 `soffice.data`）—— 人工看 DevTools 很容易漏掉「某個請求沒發生」這種負面證據。

首次使用需要 `npm i playwright` 與 `npx playwright install chromium`（已裝好）。

---

## 送出前的檢查

不管哪一張，送出前都要能回答：

1. **在上游預設組態上重現過了嗎？** 自訂旗標上的問題，上游有正當理由不收。
2. **搜過 Bugzilla 沒有重複嗎？** 重複單是 triager 最大的時間黑洞。
3. **哪些是事實、哪些是推測？** 推測要標明是推測。猜錯不丟臉，把猜測寫成結論才會傷信用。
4. **一張單只講一件事嗎？** 三個問題塞一張會整張卡住。

送出後把 `tdf#` 回填到單子和上面的清單。

---

## Bugzilla

- 送單：<https://bugs.documentfoundation.org>
- QA 入門：<https://wiki.documentfoundation.org/QA/GetInvolved>
- bibisect（定位是哪個 commit 造成的）：<https://wiki.documentfoundation.org/QA/Bibisect>

**Version 欄位填 `26.8.0.1 rc`。** 26.8 的時程：RC1 2026-07-13、正式版 2026 年 8 月底 —— 八月中之前送的還有機會進正式版，之後只能進 26.8.1。

# R2 WASM Document SDK：穩定 binding 與 Worker runtime

日期：2026-08-01（Asia/Taipei）

## 一分鐘版

**R2 技術閘門：GO。** R1 的裸 C／Emscripten probe 已收斂為可由應用程式使用的
SDK boundary：

```text
Application
  → ES module + TypeScript declarations
  → versioned Worker protocol v1
  → Dedicated Worker（唯一持有 Emscripten runtime）
  → C ABI 1.0（request id／opaque handle／owned buffer）
  → single engine pthread → LibreOfficeKit
```

- Chrome 150、Firefox 152 各跑 3 次 open／render／click／insert／save／close，6/6 通過。
- 6 份 ODT 全數通過 ZIP/XML、中文字增量 +1、0.998609 文字相似度與桌面 LibreOffice
  26.2.4.2 開啟／轉 PDF。
- 兩個瀏覽器均通過 13 項 lifecycle／ownership／error-boundary checks，包括實際 timeout
  cancel、真實 Worker error 後 restart，以及各 10 輪 open／render／close smoke soak；主執行緒
  沒有 `createProbeModule`、`FS`、`HEAPU8`。
- Node SDK tests 6/6 與 C ABI header compile test 通過；真實 WASM 中 12 個 `oxsdk_*`
  exports 完整存在。
- Runtime raw 259.76 MiB、gzip -9 84.59 MiB；較 R1 僅增加約 0.012%。依決策只記錄漂移，
  體積最佳化全部延後至 R5。

機器可讀摘要見
[`findings/evidence/sdk-r2/summary.json`](../findings/evidence/sdk-r2/summary.json)。

## 實作內容

### C ABI 1.0

[`wasm_sdk_probe/src/sdk_api.h`](../wasm_sdk_probe/src/sdk_api.h) 使用 `oxsdk_` prefix、固定寬度
整數及 opaque `uint32_t` document handle。ABI 版本為 `0x00010000`，capability bits 明列
open ODT、RGBA tile、insert、save 與 queued cancel。

公開的 12 個 exports 是：版本／capability 查詢、engine start、open、paint、click、insert、
save、close、request cancel、buffer alloc／free。同步 return code 只表示輸入與 queue 接受
狀態；LibreOfficeKit 結果走非同步事件。輸入 bytes／UTF-8 在 C call 返回前同步複製；tile
與 ODT output 由 Worker 複製後恰好 free 一次。

Engine 保持單一文件與單一 LOK pthread，request ID 不可為零且不可重複。每次 open 取得單調
遞增 handle；close 後舊 handle 回報 `INVALID_HANDLE`，文件修改會更新 revision。LOK callback
id 70 只在內部轉譯成 `view-ready`，不成為 public protocol。

### Dedicated Worker 與 public SDK

[`wasm_sdk_probe/sdk/sdk-worker.js`](../wasm_sdk_probe/sdk/sdk-worker.js) 是唯一載入 Emscripten
loader、存取 heap／FS、呼叫 C ABI 的 context。訊息以 protocol version、request ID 與
structured-clone object 對應，ODT、RGBA pixels 與 save output 都使用 transferable
ArrayBuffer。

[`wasm_sdk_probe/sdk/document-sdk.js`](../wasm_sdk_probe/sdk/document-sdk.js) 提供
`createDocumentEngine`、`DocumentEngine`、`DocumentHandle` 與 typed errors；對外操作是 Promise，
支援 timeout、AbortSignal、明確 input ownership、restart 與 dispose。完整 TypeScript surface
在 [`document-sdk.d.ts`](../wasm_sdk_probe/sdk/document-sdk.d.ts)，不需把 TypeScript compiler
或 npm dependency 加入 R2 技術閘門。

Timeout／AbortSignal 會立即拒絕 Promise 並送 best-effort cancel。C queue 尚未 dispatch 的
工作可取消；已進同步 LOK call 的 request 回報 `NOT_CANCELLABLE`，不使用 thread kill。
Worker crash 會拒絕全部 pending work；restart 會提升 generation，使先前的 document object
成為 `STALE_DOCUMENT`。

## 驗證結果

### SDK 與 ABI

`make test-r2` 結果：

- Node tests 6/6：version handshake／correlation、ownership／idempotent public close、timeout、
  AbortSignal、模擬 Worker crash／restart stale handle、protocol mismatch。
- C++17 header syntax／static assertions：ABI version、整數 layout、status 與 capability 通過。
- Emscripten 4.0.10 增量 `make all` 通過；R2 首次完整重連結 3.87 秒、max RSS
  1,928,904 KiB、swap 0。
- 真實 `probe.wasm` 可列出全部 12 個 `oxsdk_*` exports；exports 清單不含 unoembind，建置
  參數不含 JSPI／`PROXY_TO_PTHREAD`。

### 瀏覽器垂直切片

以下為正式 cold 樣本中位數，單位毫秒；每個瀏覽器 3 次。樣本數只供 R2 regression 判讀，
不定義正式效能 SLA。

| 瀏覽器 | 通過 | ready | open | first tile | insert | save |
|---|---:|---:|---:|---:|---:|---:|
| Chrome 150 | 3/3 | 2635 | 143 | 157 | 1.88 | 212 |
| Firefox 152 | 3/3 | 3272 | 489 | 145 | 1.82 | 306 |

每輪都確認 `input_transferred=true`、`main_thread_isolated=true`，插入路徑為 paste。原始 JSON、
console 與 screenshots 位於
[`findings/evidence/sdk-r2/browser-raw`](../findings/evidence/sdk-r2/browser-raw)。

### Lifecycle／ownership／boundary conformance

Chrome 與 Firefox 對下列 13 項皆回報 PASS：

| 檢查 | 預期結果 |
|---|---|
| Worker restart 後使用舊 document | `StaleDocumentError` |
| 大 tile 阻塞期間取消排隊 render | public `SdkAbortError`，C cancel `OK` |
| 大 tile 阻塞期間讓排隊 render timeout | public `SdkTimeoutError`，C cancel `OK` |
| close 後以舊 handle paint | `INVALID_HANDLE` |
| 再次以舊 handle close | `INVALID_HANDLE` |
| 以 ABI 2.0 初始化 ABI 1.0 Worker | `INCOMPATIBLE_ABI` |
| 以 request ID 0 初始化 | `INVALID_ARGUMENT` |
| 以 `.txt` 名稱送 open | `INVALID_ARGUMENT` |
| `transfer:false` 開檔 | caller input byteLength 保持不變 |
| `transfer:true` 開檔 | caller input 被 neuter（byteLength 0） |
| render／save output | 收到尺寸正確的 transferable ArrayBuffer |
| 連續 open／render／close | 每個瀏覽器 10/10，handle 單調遞增 |
| 真實 browser Worker 丟出 error | pending request 拒絕、crash event、restart 後真實 WASM 可重開 |

兩個瀏覽器同時確認主執行緒的 `createProbeModule`、`FS`、`HEAPU8` 都是 undefined。證據位於
[`findings/evidence/sdk-r2/conformance`](../findings/evidence/sdk-r2/conformance)。

Closure hardening 後另以兩個瀏覽器各重跑 1 次完整垂直切片，2/2 通過；其輸出亦通過相同
ZIP/XML、中文字增量、文字相似度與桌面 PDF round-trip。新增證據在
[`findings/evidence/sdk-r2/hardening-regression`](../findings/evidence/sdk-r2/hardening-regression)
與
[`findings/evidence/sdk-r2/hardening-roundtrip.json`](../findings/evidence/sdk-r2/hardening-roundtrip.json)。

### Round-trip

正式 6 份輸出全部滿足：ODT ZIP CRC 正常、`content.xml` 可 parse、「測」增量 +1、文字
相似度 0.998609，且桌面 LibreOffice 26.2.4.2 能無互動轉成 PDF。細節見
[`findings/evidence/sdk-r2/roundtrip.json`](../findings/evidence/sdk-r2/roundtrip.json)。

R1 legacy harness 另以 Chrome 重跑 1 次，相同 runtime 仍完成五步驟與 round-trip，表示新增
ABI 沒有破壞既有 probe 路徑；證據在
[`findings/evidence/sdk-r2/r1-compat-smoke`](../findings/evidence/sdk-r2/r1-compat-smoke)。

## 產物與體積漂移

| 產物 | R2 raw bytes | gzip -9 bytes | SHA-256 |
|---|---:|---:|---|
| `probe.js` | 365,785 | 90,700 | `014f710a83d6f4421be0dc7b2840a2a57d68bca4b2da2c62ab00c4c6fa77613b` |
| `probe.wasm` | 169,242,199 | 45,639,578 | `0b6cb1a9ba8c0bccbffaf352eb4eb711fc86d920fbe966ee3801a31192747839` |
| `soffice.data` | 102,765,226 | 42,969,853 | `68b80e0ddc9253de50e9580eccecbcfd0d2243f845af6ebb5735952e32ca19c6` |
| **合計** | **272,373,210（259.76 MiB）** | **88,700,131（84.59 MiB）** | — |

R1 合計為 raw 272,341,191、gzip 88,690,004 bytes；R2 分別增加 32,019 與 10,127 bytes，
約 0.0118%／0.0114%。這裡只建立 regression baseline。optimization level、assertions／
profiling、scripting、字型、registry、filters 與分包不在 R2 調整，已確認集中到 R5 A/B。

## 實作中遇到的整合問題

- `MAIN_THREAD_EM_ASM` 內的 JavaScript strict equality 會先經 C preprocessor；`===` 被切成
  `==` 與 `=` token 而使產生的 loader 語法錯誤。內嵌片段改用 `==` 並加註原因後，C++
  compile、link 與 `node --check` 均通過。
- Worker 以 `importScripts(probe.js)` 載入 modularized Emscripten runtime 後，
  `self.location` 仍指向 `sdk-worker.js`；若不指定 `mainScriptUrlOrBlob`，pthread pool 會錯把
  `sdk-worker.js` 當成 pthread entrypoint 而卡住。Module options 明確設為 `probe.js` URL 後，
  Chrome／Firefox 都能穩定啟動。這是 Worker host 的整合邊界，不需修改 LibreOffice core。

## 工作區完整性與下一步

- `libreoffice-26-8` 仍只有進場前已存在的 5 個 tracked 修改與 1 份未追蹤報告；R2 未改動
  core source，也未碰 Qt6 build 線。
- Workspace 根目錄不是 Git repository，因此 R2 外部 probe／spec／evidence 無法在此切 commit；
  交付以檔案、測試 JSON 與 artifact hashes 追溯。
- R2 v1 仍只支援一份 Writer ODT、程式化文字輸入、queued cancel；10 輪 smoke soak 已通過，
  但不宣稱真 IME、多文件、DOCX corpus、production security 或長時間 soak 已完成。

R2 的 application/runtime boundary 已成立，可進 R3：在既有 typed SDK 上逐一加入
selection、search、replace、undo、comment 與 redline；避免把 UNO／LOK raw details 重新漏回
應用層。體積最佳化維持延後至 R5。

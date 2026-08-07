# SPEC R2-000：穩定 binding 與 Worker runtime

> **日期**：2026-08-01  
> **狀態**：已完成（GO，v1）  
> **依據**：[R1 實測](../DEVLOG-2026-08-01-wasm-sdk-probe.md)、
> [SDK 主報告 §5、§10](../RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)

## 1. 目標

把 R1 的裸 probe 收斂成可由應用程式使用的第一版 SDK boundary：

```text
Application
  → TypeScript-first SDK（Promise／AbortSignal／typed errors）
  → versioned Worker protocol（request id／transferable buffers）
  → dedicated Worker（唯一持有 Emscripten runtime）
  → versioned C ABI（opaque handle／pointer+length／error code）
  → single engine pthread → LibreOfficeKit
```

通過後，主執行緒應用程式不得接觸 WASM pointer、`Module.FS`、`HEAPU8`、UNO object 或
原始 LOK callback。

## 2. v1 範圍

- 單一 engine、同時最多一份 Writer 文件。
- 由 `ArrayBuffer` 開啟 ODT、RGBA tile render、click、UTF-8 文字插入、另存 ODT、close。
- ABI／Worker protocol major/minor version negotiation。
- 非零 request id；每個 request 恰好一個完成或錯誤結果。
- document handle 與 revision；close 或 Worker restart 後舊 handle 必須失效。
- transferable input／output／pixel buffers，ownership 規則可測。
- timeout、`AbortSignal`、尚在 queue 中的 cancel、Worker crash／restart。
- 明確的 `view-ready` SDK 狀態，不讓應用程式依賴 LOK callback id 70 的文字 payload。

## 3. 明確不在 R2

- **體積最佳化**：已確認延後至 R5，以獨立 A/B 處理 optimization、scripting、字型、
  registry、filter 與分包；R2 不以減少 bytes 為目標。
- selection/search/replace/undo/comment/redline（R3）。
- Provider contract（R4）、資源 profile（R5）、協作應用（R6）。
- 真 IME composition、DOCX corpus、多人同時編輯、多文件並行。
- 在執行中的同步 LOK call 內做不安全的硬中斷。

## 4. C ABI v1

公開 header 使用 `oxsdk_` prefix、固定寬度整數、opaque `uint32_t` handle；不公開 STL、UNO
或 LibreOfficeKit 型別。ABI version 編碼為 `(major << 16) | minor`，v1.0 為 `0x00010000`。

| API | 語意 |
|---|---|
| `oxsdk_abi_version`／`oxsdk_capabilities` | 同步查詢，不啟動引擎 |
| `oxsdk_engine_start` | 協商 ABI，非同步初始化 LOK |
| `oxsdk_document_open` | 同步複製 borrowed input bytes，非同步回傳 document handle |
| `oxsdk_document_paint` | 非同步回傳 owned RGBA buffer |
| `oxsdk_document_click` | 非同步定位游標 |
| `oxsdk_document_insert_text` | 同步複製 borrowed UTF-8，非同步回傳新 revision |
| `oxsdk_document_save` | 非同步回傳 owned ODT buffer |
| `oxsdk_document_close` | 銷毀 document 並使 handle 失效 |
| `oxsdk_request_cancel` | 取消尚在 queue 的 request；執行中回報不可取消 |
| `oxsdk_buffer_alloc`／`oxsdk_buffer_free` | Worker 與 WASM 間唯一公開 buffer ownership 入口 |

同步 return code 只表示「參數／版本是否有效、是否已接受入 queue」；LOK 結果一律由事件
回傳。輸入 pointer 在 C call 返回後仍由 caller 擁有；C ABI 已完成同步複製。tile/save 事件
交出的 pointer 由 caller 擁有，且必須恰好呼叫一次 `oxsdk_buffer_free`。

事件至少含：`schemaVersion`、`type`、`requestId`、`documentHandle`、`revision`。錯誤另含穩定
字串 code 與 message。LOK callback 可作 diagnostics event，但不能直接成為 public API 契約。

## 5. Cancel、timeout 與 crash 邊界

- C queue 中尚未 dispatch 的 request：`cancel` 必須成功，原 request 收到 `cancelled`。
- 已進入同步 LOK call：回傳 `NOT_CANCELLABLE`；不得用 thread kill 破壞 core state。
- TypeScript timeout／AbortSignal：立即拒絕 Promise，送出 best-effort cancel。
- timeout 或 Worker error 後，SDK 必須能終止舊 Worker、拒絕 pending requests、建立新 Worker；
  restart 前取得的 document objects 全部成為 stale。

## 6. Worker protocol v1

訊息是 structured-clone object：

```text
request  = {protocolVersion:1, kind:"request", requestId, operation, payload}
response = {protocolVersion:1, kind:"response", requestId, ok, result|error}
event    = {protocolVersion:1, kind:"event", event, documentHandle?, revision?, detail?}
cancel   = {protocolVersion:1, kind:"cancel", requestId}
```

ODT、tile 使用 transferable `ArrayBuffer`。Worker 是唯一能載入 `probe.js`、存取 `FS`／heap
與呼叫 C ABI 的環境；主執行緒 bundle 不得 import Emscripten loader。

## 7. TypeScript-first package

本環境沒有 TypeScript compiler，R2 不為此安裝依賴。交付採可直接在瀏覽器／Node 執行的
ES module，加上完整 `.d.ts` 宣告與無依賴 conformance tests；這仍提供 TypeScript public
surface，同時避免把 npm toolchain 變成本技術閘門的未知數。

最小 public API：

```ts
const engine = await createDocumentEngine(options)
const doc = await engine.open(input, { transfer: true, signal, timeoutMs })
const tile = await doc.render({...}, { signal, timeoutMs })
await doc.click(...)
await doc.insertText("測")
const output = await doc.save({ format: "odt" })
await doc.close()
await engine.restart()
engine.dispose()
```

## 8. 驗收

1. C ABI header 有 compile-time layout/version assertions；invalid version、argument、request id、
   handle 與 double-close 均有測試。
2. SDK unit tests 覆蓋 request correlation、buffer transfer、timeout、AbortSignal、worker error、
   restart 與 stale document。
3. Chrome／Firefox 都從 dedicated Worker 完成 t1 的 open/render/click/insert/save/close，至少
   各 3 次，輸出通過桌面 round-trip。
4. 瀏覽器主執行緒驗證 `createProbeModule`、`FS`、`HEAPU8` 均未暴露。
5. ABI mismatch、queued cancel、close 後再操作及 restart 後舊 handle 的錯誤可重現。
6. 不修改 `libreoffice-26-8` tracked files；不連 unoembind、不用 JSPI／PROXY_TO_PTHREAD。
7. 交付 R2 DEVLOG、protocol/ABI 文件、console/screenshots 與機器可讀測試摘要。

## 9. Go／No-Go

**Go**：上述驗收成立，應用層只看 typed SDK；可進 R3 semantic review operations。

**停止回報**：dedicated Worker 無法穩定承載 pthread module、buffer transfer 造成可重現壞檔、
或需要修改 core 才能建立基本 lifecycle／error boundary。

## 10. 執行結果（2026-08-01）

**判定：GO。**

- C ABI 1.0、Worker protocol v1、Dedicated Worker、ES module 與 `.d.ts` 已交付。
- Node SDK tests 6/6、C ABI header compile test 通過。
- Chrome 150／Firefox 152 各 3 次完整垂直切片通過；6 份 ODT 都通過桌面 round-trip。
- 兩瀏覽器均通過 13 項 conformance：Abort／timeout queued cancel、stale／invalid handle、
  double-close、ABI mismatch、零 request ID、invalid argument、input／output ownership、10 輪
  open／render／close smoke soak 與真實 Worker error/restart recovery；主執行緒 Emscripten
  runtime 隔離成立。
- Closure hardening 另增加 Chrome／Firefox 各 1 次完整垂直切片及桌面 round-trip，2/2 通過。
- `libreoffice-26-8` tracked files 未因 R2 改動；未連 unoembind，未用 JSPI／
  `PROXY_TO_PTHREAD`。
- R2 runtime 較 R1 raw／gzip 僅增加約 0.012%；依決策只記錄，體積最佳化維持延後至 R5。

完整數字與限制見
[`DEVLOG-2026-08-01-wasm-sdk-r2.md`](../DEVLOG-2026-08-01-wasm-sdk-r2.md)，機器可讀證據見
[`findings/evidence/sdk-r2/summary.json`](../findings/evidence/sdk-r2/summary.json)。

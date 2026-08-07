# R3 WASM Document SDK：Semantic review operations

日期：2026-08-01（Asia/Taipei）

## 一分鐘版

**R3 技術閘門：GO。** R2 的版本化 Worker SDK 已擴充為受控的 Writer review API：

```text
search → selection → replace → stale revision guard → undo
       → comment add/list/undo
       → track changes → replace → list redlines
       → save ODT → desktop round-trip
```

- C ABI 由 1.0 向後相容升為 1.1；1.1 runtime 接受 1.0 client，拒絕 1.2 與 2.0 client。
- 公開 SDK 新增 search、selection、replace、undo、comment 與 tracked-change 語意方法；沒有
  generic UNO command passthrough。
- Mutation 必須帶單調遞增的 `expectedRevision`。Chrome 與 Firefox 都證明 stale revision
  會得到帶 expected/current details 的 typed `StaleRevisionError`，文件不會被修改。
- Chrome 150、Firefox 152 各 3 次完整流程，6/6 通過；6 份 ODT 都保有取代文字、1 個註解、
  2 個 changed regions、1 組 insertion/deletion，且桌面 LibreOffice 26.2.4.2 可轉成 PDF。
- R2 conformance 在兩個瀏覽器全數通過，含每邊 10 輪 soak；R1 legacy flow 兩邊 2/2 通過。
- Node SDK tests 8/8、C ABI header compile、Emscripten strict undefined-symbol link 均通過。
- Runtime raw 259.78 MiB、gzip -9 84.60 MiB；較 R2 僅增加 22,982／9,804 bytes。依既定決策
  只記錄漂移，體積最佳化維持延後至 R5。

機器可讀摘要見
[`findings/evidence/sdk-r3/summary.json`](./findings/evidence/sdk-r3/summary.json)。

## 實作內容

### C ABI 1.1 與相容規則

[`wasm_sdk_probe/src/sdk_api.h`](./wasm_sdk_probe/src/sdk_api.h) 將 ABI 編碼升為
`0x00010001`，並新增 search、selection text、replace selection、undo、comments、tracked
changes 六組 capability bits。ABI handshake 採 same-major、client-minor 不高於 runtime 的規則，
所以既有 1.0 client 不必因 1.1 runtime 重編；不同 major 或較新的 client minor 回報
`INCOMPATIBLE_ABI`。

新增八個固定用途 exports：

```text
oxsdk_document_search
oxsdk_document_get_selection
oxsdk_document_replace_selection
oxsdk_document_undo
oxsdk_document_add_comment
oxsdk_document_list_comments
oxsdk_document_set_track_changes
oxsdk_document_list_changes
```

加上 R2 exports，真實 WASM export allowlist 共 20 個 `oxsdk_*` entry points。所有字串輸入仍
在 C call 返回前同步複製，工作由單一 engine pthread 依序送入 LibreOfficeKit。

### Semantic adapter 與 revision guard

[`wasm_sdk_probe/src/probe_engine.cpp`](./wasm_sdk_probe/src/probe_engine.cpp) 只包含固定 adapter：

- search 固定使用 `.uno:ExecuteSearch`，結果轉為 found／rectangles／revision；
- selection 只讀 `getTextSelection("text/plain;charset=utf-8")`；
- replace 使用既有純文字 paste，undo 固定使用 `.uno:Undo`；
- comment 只使用 `.uno:InsertAnnotation`／`.uno:ViewAnnotations`；
- tracked changes 只使用 `.uno:TrackChanges`／`.uno:AcceptTrackedChanges` 的查詢結果。

呼叫端不能提供 `.uno:*` 名稱，也拿不到 UNO object 或 raw LOK callback。replace、undo、comment
與 track-changes 都先比較 `expectedRevision`；成功 mutation 才將 adapter-local revision 加一，
undo 也不會讓 revision 倒退。

[`wasm_sdk_probe/sdk/sdk-worker.js`](./wasm_sdk_probe/sdk/sdk-worker.js) 把 search rectangles、comments
與 redlines 正規化為 structured-clone data；
[`document-sdk.js`](./wasm_sdk_probe/sdk/document-sdk.js) 則提供 Promise API、revision propagation
與 typed `StaleRevisionError`。TypeScript declarations 同步更新。

### R3 browser harness

[`wasm_sdk_probe/web/r3.html`](./wasm_sdk_probe/web/r3.html) 的 **Run R3 Review Flow** 使用一份真實
ODT 依序驗證：

1. 搜尋並讀回 `LibreOfficeKit` selection。
2. 取代為 `LOK-R3`，再故意以舊 revision 寫入 `SHOULD-NOT-APPEAR`。
3. 確認 stale error 的 expected/current details，undo 後重新讀到原文字。
4. 對 `臺灣軟體工程` 新增註解、列出、undo、確認消失，再重新新增。
5. 開啟 change tracking，將 `English words` 取代為 `English terms` 並列出 redlines。
6. render、save、close；成功流程最終 revision 必須為 7。

## 驗證結果

### SDK、ABI 與公開邊界

`make test-r3` 結果：

- Node tests 8/8：保留 R2 的 handshake／ownership／timeout／abort／crash tests，並加入 R3
  revision propagation 與 typed stale error details。
- C++17 header compile/static assertions 通過 ABI 1.1 與 capability layout。
- Emscripten 4.0.10 `make all` 在 `ERROR_ON_UNDEFINED_SYMBOLS=1` 下完成；八個新增 exports 均在
  allowlist，建置不連 unoembind，也沒有 JSPI／`PROXY_TO_PTHREAD`。
- Chrome／Firefox ABI conformance 都確認 1.0 接受、1.2／2.0 拒絕、semantic capability 完整、
  主執行緒沒有 Emscripten runtime，公開 SDK 沒有 generic UNO surface。

ABI 證據位於
[`findings/evidence/sdk-r3/conformance`](./findings/evidence/sdk-r3/conformance)。

### 瀏覽器 semantic flow

以下是 cold 樣本中位數，單位毫秒；每個瀏覽器 3 次。這組小樣本只作 regression 判讀，不是
production SLA。

| 瀏覽器 | 通過 | ready | open | first tile | replace selection | save |
|---|---:|---:|---:|---:|---:|---:|
| Chrome 150 | 3/3 | 2440 | 143 | 156 | 7.15 | 205 |
| Firefox 152 | 3/3 | 3075 | 486 | 144 | 7.66 | 307 |

每輪的 input transfer、Worker isolation、search/selection、replace/undo、stale guard、comment
round-trip、tracked changes 與 final revision 7 都是 PASS。原始 JSON、console、輸出 ODT 與
screenshots 位於
[`findings/evidence/sdk-r3/browser-raw`](./findings/evidence/sdk-r3/browser-raw)。
最終 strict link 與文件收斂後，兩個瀏覽器又各重跑 1 次相同流程及 desktop round-trip，2/2
通過；證據位於
[`findings/evidence/sdk-r3/final-smoke`](./findings/evidence/sdk-r3/final-smoke)與
[`final-smoke-roundtrip.json`](./findings/evidence/sdk-r3/final-smoke-roundtrip.json)。

### ODT 與桌面 round-trip

正式 6 份輸出全數滿足：

- ODT ZIP CRC 正常且 `content.xml` 可解析；
- `English terms` 存在，故意 stale 的 `SHOULD-NOT-APPEAR` 不存在；
- `R3 review note` 與 1 個 annotation 存在；
- 每份都有 2 個 changed regions、1 個 insertion、1 個 deletion；
- 桌面 LibreOffice 26.2.4.2 均可無互動輸出非空 PDF。

完整結果見
[`findings/evidence/sdk-r3/roundtrip.json`](./findings/evidence/sdk-r3/roundtrip.json)。

### R2／R1 回歸

- Chrome 與 Firefox 的 R2 conformance 全部維持 PASS，包括 cancel／timeout、handle／ownership、
  真實 Worker crash recovery 與每邊 10/10 open-render-close soak。
- R1 legacy harness 在 Chrome、Firefox 各跑一次，2/2 完成 paste 路徑並通過桌面 round-trip。

證據分別位於
[`findings/evidence/sdk-r3/r2-regression`](./findings/evidence/sdk-r3/r2-regression)與
[`findings/evidence/sdk-r3/r1-regression`](./findings/evidence/sdk-r3/r1-regression)。

## 產物與體積漂移

| 產物 | R3 raw bytes | gzip -9 bytes | SHA-256 |
|---|---:|---:|---|
| `probe.js` | 367,855 | 90,960 | `e6d5d2adbde87d7e58d4a79f8930ef970ededa4ba386bddda865d7a901fe7dfd` |
| `probe.wasm` | 169,263,111 | 45,649,122 | `23e765aa8464e832f2e0150252244403b252744173243de1eb628df959327e62` |
| `soffice.data` | 102,765,226 | 42,969,853 | `68b80e0ddc9253de50e9580eccecbcfd0d2243f845af6ebb5735952e32ca19c6` |
| **合計** | **272,396,192（259.78 MiB）** | **88,709,935（84.60 MiB）** | — |

相較 R2，raw 增加 22,982 bytes（約 0.0084%），gzip -9 增加 9,804 bytes（約 0.0111%）。
這裡只建立 R3 drift baseline；optimization、scripting、字型、registry、filters 與分包 A/B
仍全部延後到 R5。

## 實作中確認的整合行為

- `.uno:InsertAnnotation` 的 command-result callback 早於 comment 實際寫入；若收到 command-result
  就立刻 list，會得到空陣列。Adapter 現在以固定 `.uno:Escape` 完成輸入，並等待
  `LOK_CALLBACK_COMMENT` Add 後才 resolve，因此 comment add/list/undo 可穩定跨瀏覽器重現。
- 部分無回傳值 UNO command 的 result payload 會帶 `success:false`，即使命令效果已完成。R3
  不把該欄位當語意成功判準，而將 callback 視為 completion barrier，再以 selection、comments
  或 redlines 的後續查詢確認真正效果。

這兩點都封裝在固定 semantic adapter 內，沒有把 raw callback 或任意 command 能力暴露給應用層。

## 工作區完整性與下一步

- `libreoffice-26-8` 仍只有進場前既有的 5 個 tracked 修改與 1 份未追蹤報告；R3 沒有改動
  core source，也沒有碰 Qt6 build 線。
- Workspace 根目錄不是 Git repository，因此外部 probe／spec／evidence 無法在此切 commit；
  交付以檔案、測試 JSON 與 artifact hashes 追溯。
- R3 v1 仍不含 regex／replace-all、多 selection、comment 編修／回覆、redline accept/reject、
  Markdown parser、DOCX corpus、真 IME 或 production security model。

R3 已建立足夠窄且可驗證的 review operation boundary，可進 R4：讓第一個 provider 只產生經
validator 檢查、帶 `expectedRevision` 的 operation，不直接取得文件、UNO 或 Emscripten internals。
體積最佳化維持延後至 R5。

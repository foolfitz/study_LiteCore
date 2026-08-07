# R4 WASM Document SDK：Provider SDK contract

日期：2026-08-01（Asia/Taipei）

## 一分鐘版

**R4 技術閘門：GO。** R3 的 semantic review API 上已建立 Provider contract 1.0：

```text
discover → selection snapshot → Provider Worker transform/progress/cancel
         → validate closed operation + revision → host-mediated replace → save
```

- `ProviderRegistry`、`ProviderHost`、descriptor／input／operation validators、Web／desktop contract
  adapters 與 Dedicated Worker transport 已完成，並附 TypeScript declarations。
- 第一個 `text.translate` fixture 將 `English words` 非同步轉成 `R4 Provider：英文詞彙`；同一份
  descriptor、input 與 expected operation 在 Node Web／desktop adapter 得到完全相同結果。
- Provider 只收到 immutable、structured-clone-safe selection snapshot、`AbortSignal` 與 progress
  callback；不取得 `DocumentHandle`、engine、UNO、Emscripten `Module` 或文件 mutation callback。
- 未知 operation、錯誤 revision、額外 `.uno:*` 欄位、過大輸出與取消後 late result 都不會觸發
  document sink。
- Chrome 150、Firefox 152 各 3 次正式流程，6/6 通過；每輪都刻意在 Provider 執行期間插入較新
  文件修改，舊 snapshot 結果被 R3 stale guard 擋下，undo 後才重新呼叫並成功套用。
- 6 份 ODT 都含預期 Provider 文字、不含 concurrent edit 或 `.uno:Paste`，且桌面 LibreOffice
  26.2.4.2 全數可轉成 PDF。
- R3 完整 review flow、R2 conformance／每邊 10 輪 soak、R1 legacy flow 與 strict Emscripten link
  均通過。
- Core 三項 artifact 與 R3 byte-for-byte 相同；R4 browser harness + Provider runtime 新增 raw
  45,229 bytes、分檔 gzip -9 合計 12,028 bytes。依決策只記錄，體積最佳化仍在 R5。

機器可讀摘要見
[`findings/evidence/sdk-r4/summary.json`](./findings/evidence/sdk-r4/summary.json)。

## 實作內容

### Provider contract 1.0

[`provider-sdk.js`](./wasm_sdk_probe/provider-sdk/provider-sdk.js) 定義獨立於 Document C ABI／Worker
protocol 的 Provider contract 1.0。R4 的 closed surface 只有：

- reverse-DNS provider identity、semver、`text.translate` capability；
- `selection.text` input snapshot；
- `replaceSelection` output operation；
- progress、`AbortSignal`、typed errors；
- 每筆 operation 必須保留 snapshot 的 `expectedRevision`。

Descriptor、input 與 operation 都先做 structured clone，再移除可變參照並 deep-freeze。Validator
拒絕未知欄位、未支援 capability／operation、非 scalar parameters、錯誤 revision 與超過 1 MiB 的
UTF-8 replacement。Provider contract version 已寫入 SDK manifest，但 R3 C ABI 維持 1.1、Document
Worker protocol 維持 v1，R4 沒有新增 C export。

### Host-mediated document adapters

`ProviderHost.invokeSelection()` 持有 document adapter，但只把 selection 的 text、revision 與有限
parameters 傳給 Provider。Provider 完成後，Host 才執行：

1. endpoint／capability lookup；
2. operation schema 與 UTF-8 limit 驗證；
3. operation revision 必須等於 snapshot revision；
4. 呼叫 adapter 的 `applyValidatedOperation()`。

Web adapter 最終只映射到 R3 `DocumentHandle.replaceSelection()`。Desktop adapter 則接受
`readSelection()`／`replaceSelection()` 受控 sink callback；本輪驗證的是 domain contract 與 sink
邊界，**不是**宣稱已完成真正 UNO／`.oxt` desktop binding。

### 獨立 Provider Worker

瀏覽器範例的主執行緒只載入 descriptor；實際轉換程式由
[`text-translate-worker.js`](./wasm_sdk_probe/providers/text-translate-worker.js) 在另一個 Dedicated
Worker 執行。Provider Worker protocol 支援 ready handshake、request ID、progress、result、error
與 cancel。Runtime evidence 顯示該 Worker 的 `document`、`createProbeModule`、`FS`、`HEAPU8` 都是
`undefined`，也沒有載入 Document SDK。

這是文件能力隔離，不是完整 hostile-code sandbox：R4 沒有實作 network policy、CPU／memory quota、
套件簽章或 remote Provider trust model。

### R4 browser harness

[`r4.html`](./wasm_sdk_probe/web/r4.html) 的正式流程使用真實 ODT：

1. 搜尋 `English words`，Host 建立 revision 0 selection snapshot。
2. Provider Worker 回報第一筆 progress 後，測試端先寫入 `R4-CONCURRENT-EDIT`，revision 變為 1。
3. Provider 的 revision 0 operation 回來時得到 typed `StaleRevisionError`，不得覆蓋新內容。
4. Undo concurrent edit，revision 單調增加為 2；重新搜尋並呼叫同一 Provider。
5. 通過 validator 的 `replaceSelection` 成功套用，revision 變為 3。
6. 搜尋確認 `R4 Provider：英文詞彙`，render、save、close。

## 驗證結果

### Unit、contract 與建置

`make test-r4` 結果：

- Document SDK 既有 tests 8/8；
- Provider SDK tests 11/11，含四個 invalid-operation subtests 與 Worker crash 後續呼叫防護；
- C++17 ABI header compile 通過；
- Emscripten 4.0.10 `make all` 在 `ERROR_ON_UNDEFINED_SYMBOLS=1` 下通過，不連 unoembind、不使用
  JSPI 或 `PROXY_TO_PTHREAD`。

Provider tests 證明同一 JSON fixture 在 Web／desktop adapter 等價、snapshot/context 沒有 document
surface、input 不可變、取消不落地，以及 Worker handshake／progress／隔離成立。

### 瀏覽器 Provider flow

以下為 cold 樣本中位數，單位毫秒；每個瀏覽器 3 次。100 ms 是 fixture Provider 故意加入的
非同步延遲，用來穩定製造 concurrent-edit race，不是引擎成本。

| 瀏覽器 | 通過 | ready | open | Provider | stale Provider | first tile | save |
|---|---:|---:|---:|---:|---:|---:|---:|
| Chrome 150 | 3/3 | 2492 | 293 | 110.11 | 106.41 | 141.86 | 197.44 |
| Firefox 152 | 3/3 | 3066 | 488 | 111.58 | 112.84 | 133.44 | 286.70 |

全部 6 輪的 input transfer、main／Provider Worker isolation、discovery、三段 progress、stale
rejection、undo recovery、validated replace、output selection 與 final revision 3 都是 PASS。正式證據
位於 [`browser-raw`](./findings/evidence/sdk-r4/browser-raw)。Strict link 後又各跑 1 次，2/2 與
desktop round-trip 通過，位於 [`final-smoke`](./findings/evidence/sdk-r4/final-smoke)。

### Provider public-surface conformance

Chrome／Firefox 都確認：

- contract 1.0 handshake、descriptor discovery 與 immutable metadata；
- Dedicated Provider Worker 與 document runtime 隔離；
- `rawUno` operation 在 validator 被拒絕且 sink call count 為 0；
- Worker invocation 取消得到 `PROVIDER_ABORTED` 且沒有 late mutation；
- public Provider API 沒有 generic UNO 或 raw document handle surface。

證據位於 [`conformance`](./findings/evidence/sdk-r4/conformance)。

### ODT 與桌面 round-trip

正式 6 份 R4 ODT 全數滿足：

- ZIP CRC 與 `content.xml` 正常；
- `R4 Provider：英文詞彙` 存在；
- `R4-CONCURRENT-EDIT` 與 `.uno:Paste` 不存在；
- 桌面 LibreOffice 26.2.4.2 可無互動輸出非空 PDF。

完整結果見 [`roundtrip.json`](./findings/evidence/sdk-r4/roundtrip.json)。

### R3／R2／R1 回歸

- R3 conformance 在兩個瀏覽器通過，R3 完整 review flow 各 1 次、2/2 最終 revision 7，兩份 ODT
  comment／tracked-change round-trip 通過。
- R2 conformance 在兩個瀏覽器全部通過，含 cancel／timeout、handle／ownership、真實 Worker crash
  recovery 與每邊 10/10 open-render-close soak。
- R1 legacy flow 各 1 次、2/2 通過；兩份 ODT 通過 ZIP/XML、文字保留與桌面 PDF round-trip。

證據位於 [`r3-regression`](./findings/evidence/sdk-r4/r3-regression)、
[`r2-regression`](./findings/evidence/sdk-r4/r2-regression)與
[`r1-regression`](./findings/evidence/sdk-r4/r1-regression)。

## 產物與體積漂移

Core artifacts 與 R3 完全相同：

| 產物 | R4 raw bytes | gzip -9 bytes | SHA-256 |
|---|---:|---:|---|
| `probe.js` | 367,855 | 90,960 | `e6d5d2adbde87d7e58d4a79f8930ef970ededa4ba386bddda865d7a901fe7dfd` |
| `probe.wasm` | 169,263,111 | 45,649,122 | `23e765aa8464e832f2e0150252244403b252744173243de1eb628df959327e62` |
| `soffice.data` | 102,765,226 | 42,969,853 | `68b80e0ddc9253de50e9580eccecbcfd0d2243f845af6ebb5735952e32ca19c6` |
| **合計** | **272,396,192（259.78 MiB）** | **88,709,935（84.60 MiB）** | — |

R4 新增的瀏覽器 Provider layer（harness HTML／app、Provider SDK、descriptor、implementation、
Worker entry）合計 raw 45,229 bytes；各檔 gzip -9 合計 12,028 bytes。它不會使大型 WASM 重新
打包，也沒有改變 core bytes。Minify、code split、cache header 與 provider package optimization
全部留到 R5 一起評估。

## 工作區完整性與下一步

- `libreoffice-26-8` 仍只有進場前既有的 5 個 tracked 修改與 1 份未追蹤報告；R4 沒有改動 core
  source 或 Qt6 build 線，HEAD 仍為 `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`。
- Workspace 根目錄不是 Git repository，因此外層 Provider SDK／spec／evidence 無法切 commit；
  本輪以內聚檔案、JSON fixtures、browser evidence 與 artifact hashes 追溯。
- R4 v1 只支援 `text.translate` + `selection.text` → `replaceSelection`。完整 schema UI、identity／
  secret、remote adapter、streaming、artifact insertion、scaffolder 與 marketplace 仍未實作。

R4 已證明 Provider 能擴充文件能力而不直接持有文件；下一步可進 R5，以相同 R1～R4 回歸矩陣
開始資源、profile、cache 與體積最佳化。

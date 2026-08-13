# SPEC R4-000：Provider SDK contract

> **日期**：2026-08-01  
> **狀態**：已完成（GO）  
> **依據**：[R3 結果](../devlog/DEVLOG-2026-08-01-wasm-sdk-r3.md)、
> [SDK 主報告 §4.3、§10](../research/RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)

## 1. 目標

在 R3 已驗證的 semantic review API 上建立第一版 transport-neutral Provider contract，讓外部功能
可以取得受控的 selection snapshot、非同步產生結果，再提出一個由宿主驗證與套用的文件操作：

```text
discover provider → snapshot selection → async invoke/progress/cancel
                  → validate operation/revision/capability
                  → host applies replaceSelection → save ODT
```

Provider 不取得 `DocumentHandle`、UNO object、Emscripten `Module` 或任意 `.uno:*` command；它只能
回傳 closed operation。文件仍由 Document SDK／desktop sink adapter 修改。

## 2. R4 v1 範圍

- 獨立版本的 Provider contract 1.0，不改動 R3 C ABI 1.1 或 Worker protocol 1。
- Provider descriptor 註冊、發現、重複 ID 防護與 closed capability taxonomy。
- 第一個 capability 使用 `text.translate`，endpoint 輸入為純文字 selection snapshot。
- 非同步 invocation，支援進度事件、`AbortSignal` 取消、typed error 與一次完成語意。
- Provider output 僅允許 `replaceSelection` operation；validator 檢查型別、UTF-8 大小、
  `expectedRevision`、capability 與 endpoint 宣告。
- Web document adapter 將通過驗證的 operation 映射到 R3 `replaceSelection()`。
- Desktop contract adapter 使用相同 descriptor、input fixture 與 operation schema，將結果交給受控
  sink；R4 不搬 UNO IDL 或 `.oxt` lifecycle。
- 瀏覽器參考 Provider 放在獨立 Worker，以 structured clone 傳入 snapshot、傳回 operation；Provider
  Worker 不載入 Document SDK。
- 同一份 domain fixture 在 Node Web adapter、desktop adapter 與 Chrome／Firefox 真實文件流程通過。

## 3. 明確不在 R4

- 任意 UNO／LOK passthrough、raw document object、直接 mutation callback。
- 將桌面 `XOSSIIServiceProvider` IDL、`.oxt`、VCL／weld UI 或 protocol handler 搬進 Web。
- 完整 schema UI renderer、OAuth／secret broker、remote HTTP adapter、串流文字逐段寫回。
- 多 operation transaction、圖片／artifact insertion、Calc／Impress target。
- 不受信任程式碼的完整沙箱。Worker 提供文件隔離，但不是網路與 CPU 資源安全邊界。
- Provider marketplace、scaffolder、套件簽章與 production policy。
- **體積最佳化**：仍延後到 R5，R4 只記錄 JS 與整體 artifact drift。

## 4. Canonical descriptor 與 invocation

Descriptor 的最小形狀：

```ts
interface ProviderDescriptor {
  contractVersion: "1.0"
  id: string                    // reverse-DNS stable identity
  version: string               // semver
  displayName: string
  capabilities: readonly ["text.translate"]
  endpoints: readonly [{
    id: "translate-selection"
    capability: "text.translate"
    input: "selection.text"
    outputOperations: readonly ["replaceSelection"]
  }]
}
```

宿主建立 immutable、structured-clone-safe input：

```ts
interface SelectionTextInput {
  kind: "selection.text"
  text: string
  revision: number
  parameters: Record<string, string | number | boolean>
}
```

Provider 只能完成為：

```ts
interface ReplaceSelectionOperation {
  type: "replaceSelection"
  text: string
  expectedRevision: number
}
```

`expectedRevision` 必須與 snapshot revision 完全相同。Provider 執行期間若文件已被其他操作修改，
最後仍由 R3 revision guard 回報 `STALE_REVISION`，不得重抓 selection 後靜默套用。

## 5. 執行與錯誤語意

- 每個 invoke 由宿主產生 request ID，最多接受一次 terminal result。
- Progress 是觀察資訊，不可攜帶文件 operation，也不改變 revision。
- 呼叫前已取消、執行中取消或 Worker 收到 cancel，都回報 `PROVIDER_ABORTED`。
- timeout 由呼叫端經 `AbortSignal` 組合；Provider SDK 不自行猜測產品 SLA。
- Descriptor／input／operation 驗證錯誤分別回報 `INVALID_DESCRIPTOR`、`INVALID_INPUT`、
  `INVALID_OPERATION`。
- 未註冊 Provider、未知 endpoint、能力不符與 Worker crash 都是 typed Provider SDK error。
- Provider 原始例外只轉成可序列化 code/message/details，不把 Worker stack 或宿主 internals 當 API。

## 6. Adapter 邊界

```text
Provider code/worker
    │ snapshot + progress + result operation
    ▼
ProviderHost + OperationValidator
    │ validated closed operation only
    ├── Web adapter ───────► DocumentHandle.replaceSelection()
    └── Desktop adapter ───► controlled Data Sink callback
```

兩個 adapter 必須共用 canonical descriptor、fixture 與 validator。Desktop adapter 只證明 domain
contract 與 sink boundary；真正 UNO binding、SolarMutex 與 `.oxt` packaging 不在本輪範圍。

## 7. 驗收

1. Node tests 覆蓋 descriptor discovery、共用 fixture、Web／desktop adapter 等價、進度、取消與
   typed errors。
2. 惡意／錯誤 Provider 嘗試回傳未知 operation、錯誤 revision、未宣告 operation、過大文字或
   多次完成時，都不能觸發 document sink。
3. Provider invocation context 不含 document／engine／UNO／Module／apply callback；輸入不可變。
4. Chrome／Firefox 各至少 3 次完成 selection → Provider Worker transform → validated replace →
   stale rejection → save。
5. 每個瀏覽器都證明 Provider Worker 與 Document Worker 分離，且公開 Provider surface 沒有 generic
   UNO 或 raw document mutation API。
6. 輸出 ODT 包含 fixture 預期文字、不含故意注入的文字，ZIP／XML 正常且桌面 LibreOffice 可開啟。
7. R3、R2 conformance 與 R1 legacy smoke 仍通過；`libreoffice-26-8` tracked 狀態不變。
8. 交付 Provider contract declarations、範例 Provider、conformance tests、R4 DEVLOG 與機器可讀
   evidence summary。

## 8. Go／No-Go

**Go**：同一 Provider domain fixture 在 Web／desktop adapter 得到相同 validated operation，真實
瀏覽器流程可安全套用；所有繞過 validator、錯誤 revision 與取消案例都不會修改文件。

**部分 Go**：in-process contract 與 Web 文件流程成立，但獨立 Provider Worker 在某瀏覽器不穩定；
保留 contract／validator，將 Worker adapter 標示 experimental 並記錄證據。

**停止回報**：Provider 必須取得 document／UNO 物件才能完成最小任務、operation validator 無法
阻止未授權 mutation，或 R3 stale guard 在 Provider 非同步流程中失效。

## 9. 2026-08-01 實測結果

**判定：GO，可進 R5。**

- Provider contract 1.0、registry、host、validators、Dedicated Worker transport、Web／desktop
  contract adapters、TypeScript declarations 與 `text.translate` fixture 已完成。
- 同一 domain fixture 在 Node Web／desktop adapter 產生相同 validated `replaceSelection` operation；
  Provider context 沒有 document／engine／UNO／Module／apply surface，input 為 immutable snapshot。
- Document SDK tests 8/8、Provider tests 11/11、ABI header compile 與 Emscripten strict undefined-
  symbol link 通過。未知 operation、錯誤 revision、額外 `.uno:*` 欄位、過大文字與取消 late result
  都未觸發 sink。
- Chrome 150、Firefox 152 各 3 次完整 Provider flow，6/6 通過；兩邊都穩定重現 concurrent edit
  導致的 stale rejection，undo 後再以 revision 2 snapshot 成功套用，最終 revision 為 3。
- 6 份 ODT 都含 `R4 Provider：英文詞彙`，不含 concurrent edit／`.uno:Paste`，桌面 LibreOffice
  26.2.4.2 全數可轉成 PDF。
- R3 完整 review flow、R2 conformance（每邊 10 輪 soak）與 R1 legacy flow 均跨兩個瀏覽器
  回歸通過。
- Core artifacts 與 R3 byte-for-byte 相同；R4 browser Provider layer raw 45,229 bytes、各檔 gzip -9
  合計 12,028 bytes。只記錄漂移，最佳化仍在 R5。
- `libreoffice-26-8` tracked 狀態與進場前相同，未修改 core 或 Qt6 build。

完整數字與限制見
[R4 DEVLOG](../devlog/DEVLOG-2026-08-01-wasm-sdk-r4.md)及
[機器可讀摘要](../findings/evidence/sdk-r4/summary.json)。

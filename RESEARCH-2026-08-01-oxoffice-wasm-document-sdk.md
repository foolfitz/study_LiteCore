# OxOffice WASM Document SDK 獨立研究線

> **日期**：2026-08-01  
> **研究狀態**：架構與移植策略研究，尚非 API 規格、專案排程或產品承諾  
> **實作基線**：LibreOffice 26.8（`libreoffice-26-8`，檢視時 commit `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`）  
> **客製化參考來源**：OxOffice 12.1.0／R12（檢視時主樹 commit `41791af563e947fb0b0efa92de43eafc9ab53606`，`ossii_extension` commit `331fa6ad9edafc33463c8b9b925118edba365b7b`）  
> **相關研究**：[LibreOffice WASM 輕量協作編輯器研究報告](./RESEARCH-2026-08-01-wasm-collaboration-editor.md)、[COWASM co-26.04 參考研究筆記](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)

---

## 0. 文件定位

本文件把「OxOffice WASM Document SDK」列為一條獨立研究線，回答以下問題：

1. 是否能以 LibreOffice 26.8 的 WASM 能力為底座，做出可供多個 Web 產品使用的文件 SDK？
2. OxOffice 已有的「從文件核心接出一條客製開發線」經驗，哪些能搬到新基線？
3. 桌面版以 UNO、`.oxt`、VCL 與原生元件完成的功能，在瀏覽器應改成什麼契約？
4. 如何讓前一份報告提出的輕量協作編輯器成為 SDK 的第一個使用者，而不是唯一用途？

本文刻意不做以下事情：

- 不宣稱現有 OxOffice Core 可以直接編譯成瀏覽器 SDK。
- 不凍結 C ABI、TypeScript API、套件名稱或版本政策。
- 不建立 branch、worktree、套件倉庫，也不移植任何原始碼。
- 不把目前完整 Qt6-WASM 的成功建置等同於 headless Document SDK 已經可用。
- 不預先承諾 Calc、Impress、巨集、完整 UNO automation 或瀏覽器內原生 `.oxt`。

本文沿用三種證據標記：

- **已觀察**：可由目前本機原始碼、文件或建置產物直接確認。
- **推論**：由已觀察事實推導，但仍須實驗。
- **研究假設**：值得驗證的方向，不能當成既定能力。

---

## 1. 摘要與建議

### 1.1 建議成立獨立 SDK 研究線

建議將整體工作拆成三條互相供應成果、但可以各自驗收的研究線：

| 研究線 | 目的 | 主要產物 |
|---|---|---|
| Qt6-WASM QA | 驗證 LibreOffice 26.8 完整 UI 路徑、回報上游問題 | 可重現建置、瀏覽器錯誤紀錄、上游修補 |
| **OxOffice WASM Document SDK** | 把文件核心整理成穩定、可嵌入的 Web 能力 | C ABI、Worker runtime、TypeScript SDK、Provider 契約 |
| 輕量協作編輯器 | 驗證 SDK 是否能支撐實際產品需求 | review-first 參考應用、協作整合、UX 實驗 |

三者的關係不是三套 LibreOffice fork。較合理的方向是共用同一個 LibreOffice 26.8 實作基線：

```text
LibreOffice 26.8 + 少量、可稽核的核心修補
                    │
           Document Engine SDK
          ┌─────────┴─────────┐
          │                   │
  Collaboration Editor   其他 OxOffice Web／客製產品
          │                   │
          └──── Provider SDK ─┘
```

### 1.2 LibreOffice 26.8 應是唯一實作基線

這個選擇是正確的。理由不是版本號較新而已，而是 26.8 已經具備更直接的 WASM 建置路徑：

- **已觀察**：`static/README.wasm.md` 明確區分「含 Qt 的 LibreOffice WASM」與「供其他產品使用、無 UI 的 LibreOffice Technology WASM」。
- **已觀察**：headless 範例使用 `--disable-gui --with-wasm-module=writer --with-package-format=emscripten`，並明載「No Qt needed」。
- **已觀察**：26.8 的 Emscripten `soffice` 連結路徑已納入 LibreOfficeKit 初始化程式碼與 UNO embind；Writer 模組也已有 Markdown 匯入相關能力。
- **已觀察**：OxOffice R12 的基底是較早的 Collabora `co-25.04` 系列，既有客製 patch 的上下文與 26.8 已不同。

因此，不應把 26.8 的 WASM 改動倒灌到舊 OxOffice 主樹；應反過來把 OxOffice 的**契約、行為與少量必要核心服務**重新落在 26.8。

### 1.3 核心原則：移植設計，不移植年代

OxOffice 客製化可以搬，但必須採下列原則：

> **以 LibreOffice 26.8 為真相來源，逐項移植可驗證的行為與契約；不要把舊分支的檔案快照或 ABI 假設整批搬過來。**

每一項舊改動都先回答：

1. 26.8 是否已經有等價或更好的上游實作？
2. 需求是否屬於 Document SDK，還是只屬於桌面 OxOffice UI？
3. 能否用既有 LibreOfficeKit／UNO command 完成？
4. 若必須新增核心介面，能否做成窄、可測試、可上游討論的服務？
5. Web 契約是否能脫離特定 LibreOffice 內部 ABI？

只有五題都通過，才進入移植候選清單。

---

## 2. 「WASM 輕量 SDK」的輕量是什麼

輕量不能只看 `.wasm` 檔案大小。這條研究線至少要同時管理四種重量：

| 面向 | 問題 | 量測方式 |
|---|---|---|
| 傳輸重量 | 首次開啟要下載多少？ | gzip／Brotli 首載、完整下載量、字型包大小 |
| 執行重量 | 瀏覽器吃多少記憶體與 CPU？ | WASM heap、Worker 數、開檔／渲染／存檔時間 |
| API 重量 | 客製應用要理解多少 LibreOffice 細節？ | 公開方法數、事件數、資料型別、版本相容成本 |
| 伺服器重量 | 每個使用者是否要一個常駐 office process？ | session 成本、運算位置、同步與儲存需求 |

完整 Qt6-WASM 可作為功能與 QA 基線，但 Document SDK 預設不應包含 Qt 桌面 UI。第一份研究報告已量到完整 Qt6-WASM 產物的原始體積與壓縮體積，SDK 研究應用相同量測方式產生 headless 對照，不能先以「拿掉 Qt」直接宣告成果。

SDK 的「輕量」目標應寫成相對目標：

- 只編入 Writer 與實際需要的 filters／services。
- debug 資訊不進正式傳輸產物，但保留獨立可除錯 profile。
- 字型、字典、範本、圖庫與非首載 filter 可分包或延遲取得。
- 以明確、窄的文件 API 隔離 LibreOffice 內部複雜度。
- 網路協作與產品 UI 留在 JavaScript，不塞回 C++ 文件核心。

在做出第一個 headless SDK 產物前，不宜承諾固定 MB 數字。

---

## 3. 從 OxOffice 現況學到什麼

### 3.1 值得保留的是 Core／Provider 分工

OxOffice 的 `ossii_extension` 已經證明一個重要模式：

- Core 不理解特定 Provider 的商業語意。
- Provider 透過一致的 discovery、capability、invocation 與 callback 契約被呼叫。
- Provider 不直接操作文件，而把結果交給 Core 的 Data Sink。
- 非必要 Core／Provider 不存在時，主程式 hook 應靜默 no-op。
- UI 可以由 Provider 提供 schema，宿主統一渲染與套用風格。

這些都是可跨桌面與 Web 的架構資產。特別是「Provider 不直接寫文件」，能讓 SDK 統一控制：

- undo／redo 邊界；
- 選取範圍是否仍有效；
- 文件版本與協作 lease；
- 可接受的變更種類；
- 寫回失敗時的錯誤與復原。

### 3.2 不應照搬的是原生桌面整合方式

現有 `ossii_extension` 是原生 C++ 元件，連結 `comphelper`、`cppu`、`editeng`、`framework`、`sfx`、`svx`、`vcl` 等 14 個 LibreOffice 內部 library。既有可分離發佈研究也明確指出，它雖可分開打包，仍與編譯時的 OxOffice 版本 ABI 鎖步。

這對瀏覽器有兩個直接含意：

1. 把 `libossii_extension.so` 的概念直接翻成一個 WASM 動態外掛，不是目前的安全起點。
2. NotebookBar、Sidebar、context menu、VCL custom paint 與 native installer 都不屬於 Document SDK 的核心價值。

LibreOffice 的 WASM／cross build 本來就偏向 `--disable-dynamic-loading` 與靜態 component 組合；瀏覽器的擴充性應優先放在 JavaScript、Web Worker 或遠端服務，而不是要求每個 Provider 重新連結大型 WASM。

### 3.3 「窄核心服務」是值得延續的模式

OxOffice 的 `XMarkdownRenderer` 是一個有用案例：它沒有把整個 Writer UNO 物件圖暴露給 Provider，而是把一段既有 Writer／md4c 能力包成較小的服務，並用 opaque handle 管理可回復狀態。

這不代表該介面可原封不動搬到 26.8。26.8 已經有不同的 Markdown 匯入路徑，必須重新比對行為、ownership、錯誤語意與 undo。真正應保留的是設計方法：

> 當 LOK／UNO command 無法穩定表達產品所需操作時，新增一個窄、語意化、可單獨測試的核心能力，而不是把內部 UNO 任意物件直接公開給 Web。

### 3.4 既有工程治理也可移植

以下做法比個別 patch 更有長期價值：

- `UPSTREAM_PATCHES.md` 類型的最小主樹修補清單。
- Provider scaffolder 與一致的識別字、capability、package metadata。
- optional component 缺席時的 no-op 合約。
- 能力清單與 schema 版本化。
- Core 與 Provider 各自測試、各自發佈的邊界。

在 WASM 線上，這些做法應改寫成 SDK 的 ABI manifest、feature manifest、size report 與 TypeScript conformance tests。

---

## 4. 建議的 SDK 分層

### 4.1 總體架構

```text
┌──────────────────────────────────────────────────────────────┐
│ Web application / Collaboration editor / Customer product   │
├──────────────────────────────────────────────────────────────┤
│ Provider SDK                                                 │
│ capability、async result、schema UI、identity host callback  │
├──────────────────────────────────────────────────────────────┤
│ TypeScript Document SDK                                      │
│ open、render、search、selection、edit、save、events           │
├──────────────────────────────────────────────────────────────┤
│ Worker runtime + message protocol                            │
│ request id、cancel、progress、buffer transfer、error mapping  │
├──────────────────────────────────────────────────────────────┤
│ versioned C ABI / narrow core services                       │
│ opaque handles、pointer+length、LOK adapter、operation adapter│
├──────────────────────────────────────────────────────────────┤
│ LibreOffice 26.8 Writer-only headless WASM core              │
│ LOK、Writer、filters、layout、ODF storage                      │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Document Engine SDK

這一層服務所有嵌入式產品，處理：

- engine 初始化與 profile；
- 從 `ArrayBuffer`／虛擬檔案載入文件；
- 文件與 view handle 生命週期；
- tile／page preview 渲染；
- 游標、選取、搜尋與命中結果；
- 少量、受控的文件操作；
- callback／invalidations／進度／錯誤；
- 另存 ODT、DOCX 或 PDF；
- 資源包與字型載入。

這層不應包含 OAuth、產品 toolbar、留言資料庫或多人同步協定。

### 4.3 Extension Provider SDK

這一層承接 OxOffice 客製化經驗，讓公司內部或客戶功能能以統一方式接上 Document SDK：

- Provider 註冊與發現；
- versioned capability descriptor；
- 非同步 invoke、stream、progress、cancel；
- schema-driven UI；
- host-mediated identity／secret；
- 受控的文件輸入與輸出操作；
- JS package、Worker 或 remote provider adapter。

Provider SDK 不應假設瀏覽器可以安裝桌面 `.oxt`。桌面 `.oxt` 與 Web provider 可以共用「領域契約」，但使用不同 binding。

### 4.4 一份領域契約，兩種宿主 binding

可以把共同語意整理成傳輸中立的 schema，再提供兩個 adapter：

| 領域概念 | 桌面 OxOffice binding | Web SDK binding |
|---|---|---|
| Provider identity | UNO service／`.oxt` metadata | package manifest／`registerProvider()` |
| Endpoint | `XOSSIIServiceEndpoint` | TypeScript descriptor |
| Invocation | UNO callback／ticket | `Promise`、事件串流、`AbortSignal` |
| Data input | `DataDescriptor` | discriminated union／transferable buffer |
| Target | `ServiceTarget` | closed operation type |
| Data Sink | Writer／Calc／Impress adapter | `applyOperation()` |
| UI | `.ui`、VCL／weld、UNO schema provider | DOM renderer／host component |
| Identity | `IdentityBroker` | host callback／server token exchange |

canonical contract 不應直接使用 UNO struct。否則 Web API 會被 UNO 的型別系統、例外與生命週期綁死，未來也難以讓非 LibreOffice provider 實作。

---

## 5. 公開 API 的研究方向

### 5.1 API 應以使用情境為中心

LibreOfficeKit 已經提供載入、tile rendering、鍵鼠事件、callback、UNO command 與存檔等能力，但其 tiled API 仍標記為 unstable，且微功能不適合無限制增加 C++ 方法。SDK 應在其上建立自己的版本化 facade。

概念上的 TypeScript 使用方式可接近：

```ts
const engine = await createDocumentEngine({ profile: "writer-review" })
const doc = await engine.open(inputBuffer)

const page = await doc.render({ page: 0, scale: 1.25 })
const match = await doc.search("待修正文字")

await doc.apply({
  kind: "replace-text",
  range: match.range,
  text: "修正後文字",
  expectedRevision: doc.revision,
})

const outputBuffer = await doc.save({ format: "odt" })
await doc.close()
```

以上只是研究介面，不是規格。重要的是它揭露「文件操作」，而不是要求呼叫端理解 `XTextCursor`、`Any`、service manager 或任意 UNO object graph。

### 5.2 C ABI 應比 C++／UNO 邊界更穩定

建議 production binding 以窄 C ABI 為中心：

- engine、document、view、range 使用明確寬度的 opaque handle；
- 所有 handle 有 create／retain 或 ownership／close 規則；
- 字串與二進位資料使用 pointer + length，不依賴 C++ STL ABI；
- error code 與結構化 detail 分離；
- callback payload 帶 schema version 與 document revision；
- 長操作支援 request id、progress 與 cancel；
- ABI version 可在初始化時協商。

Emscripten 現有 UNO embind 可作為研究探針或診斷工具，甚至可放在日後的 `writer-automation` profile；但不建議成為預設 SDK 表面。對外暴露完整 UNO 會擴大下載量、API 面、相容承諾與錯誤空間。

### 5.3 Worker 是預設隔離邊界

SDK 應預設把 LibreOffice WASM 放在 Worker：

- 避免排版與存檔長任務阻塞主執行緒；
- 把 callback、handle 與記憶體管理集中在一處；
- 以 transferable `ArrayBuffer` 降低大文件複製；
- 讓 UI framework 與引擎版本分離；
- 將崩潰、assert 與重啟策略包在 runtime 層。

OffscreenCanvas、pthread／SharedArrayBuffer 與 cross-origin isolation 應視 profile 與瀏覽器支援選擇，不能成為最初單執行緒探針的必要條件。

**2026-08-01 修正**：COWASM 對照顯示 LibreOffice WASM core 實際以 pthreads（SharedArrayBuffer，部署需 COOP/COEP）運作，COOL 也沒有提供單執行緒產品路徑；探針不應以「單執行緒」為目標，正確的最小組態是「`-pthread`、無 JSPI、無 PROXY_TO_PTHREAD，模組先在主執行緒 host、運算在 pthreads」。詳見 [COWASM 參考筆記 §3](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)。

---

## 6. 建置 profile，而不是執行期塞滿所有功能

建議先研究四個 build profile：

| Profile | 用途 | 預期內容 |
|---|---|---|
| `writer-reader` | 閱讀、預覽、搜尋 | Writer、必要 filters、render、search、save/export 最小集合 |
| `writer-review` | 協作編輯器 | reader + selection、replace、comment／redline 研究能力 |
| `writer-automation` | 企業客製與進階 provider | review + 受控 UNO command／選定 automation surface |
| `full-qa` | 相容與回歸驗證 | 較完整元件、診斷與 debug 資訊，不作首載產品 |

理由如下：

- **已觀察**：26.8 configure 已有 `--with-wasm-module=writer/calc/impress` 與對應 strip 開關。
- **已觀察**：WASM build 支援／依賴 static component 組合，動態載入不是預設可依賴的擴充模型。
- **推論**：以 build-time profile 控制 C++ 能力，比在單一巨型 WASM 內用 runtime flag 隱藏功能更能降低實際傳輸與攻擊面。
- **推論**：Provider 的動態性應由 JS／Worker／remote service 提供；只有確實需要文件內部能力的部分才編進 core。

字型與資源不必完全跟 profile 綁死。較合理的是：

- core profile 決定程式碼與 component；
- resource manifest 決定字型、字典、filter data 與範本；
- host app 決定首載、延遲載入與快取政策。

---

## 7. OxOffice 客製化移植矩陣

### 7.1 A 類：直接沿用概念與文件治理

| 項目 | 沿用內容 | 在新線上的形式 |
|---|---|---|
| Core／Provider 分工 | Core 不認得特定 Provider | Engine SDK + Provider SDK |
| endpoint／capability | closed list、版本化能力 | JSON／TypeScript manifest |
| async contract | ticket、success、stream、progress、error | Promise + event stream + `AbortSignal` |
| Data Sink 規則 | Provider 不直接寫文件 | versioned `applyOperation()` |
| schema UI | Provider 描述、宿主渲染 | JSON schema + DOM component |
| optional no-op | Core／Provider 缺席不破壞主程式 | capability negotiation |
| patch manifest | 精確列出主樹整合點 | upstream patch + ABI／feature manifest |
| scaffolder | 統一 package 與 metadata | Provider SDK project generator |

這一類不需要先搬 C++，可先抽出契約與 conformance fixtures。

### 7.2 B 類：保留語意、重寫 binding

| 桌面實作 | 不直接搬的原因 | Web 改寫方向 |
|---|---|---|
| UNO Provider IDL | 瀏覽器與 JS provider 不需要 UNO lifecycle | transport-neutral schema + TS interfaces |
| `AsyncInvoker` | ticket map 與 UNO callback 屬桌面宿主 | request id + Promise／stream／cancel |
| `SinkRouter` | Writer／Calc／Impress desktop frame 耦合 | SDK operation validator + document adapter |
| `IdentityBroker` | secret 不應由 WASM core 持有 | host callback 或 server-side exchange |
| `ossii.ui/1` VCL renderer | VCL style／event loop 不適用 DOM | 保留 schema 精神，重新定義 Web renderer |
| dispatch URL | desktop protocol handler 與 frame 耦合 | provider registry + explicit invoke API |

這一類應用共用測試向量證明「相同輸入語意得到相同操作」，而不是追求原始碼共用。

### 7.3 C 類：候選核心服務，需在 26.8 語意移植

| 候選 | 為何可能需要 | 移植前閘門 |
|---|---|---|
| Markdown 插入／render service | Provider 常回傳結構化文字，純貼上會失去語意 | 先比對 26.8 既有 `ReadMarkdown`，補 native 測試 |
| selection／range snapshot | 非同步 Provider 回來時需確認選取仍有效 | 定義 revision／stale range 行為 |
| replace／insert operation | review-first 只需窄修改 | 必須是一個可 undo 的 transaction |
| artifact insert／validation | 圖片或生成文件結果可能需要 | 嚴格 MIME、大小、來源與文件型別限制 |
| redline／comment semantic API | 協作版可能以建議修改為主 | 先驗證 LOK／UNO command 是否已足夠 |

這些能力應先在 native LibreOffice 26.8 上用 CppUnit／UITest 驗證，再接到 WASM binding。不能因為 OxOffice 舊線已有類似程式，就跳過 26.8 的行為稽核。

### 7.4 D 類：第一階段不移植

- NotebookBar tab injection。
- Sidebar panel factory 與 VCL custom paint。
- 桌面 context-menu interceptor。
- Addons menu 與 `vnd.ossii.ext://` protocol handler UI 路徑。
- Windows／RPM／DEB 的原生 Core installer。
- `mergelibs` re-export 與原生 `.so` 可分離打包技巧。
- PyUNO provider runtime 及桌面 `.oxt` 安裝流程。
- OxOffice branding、預載範本、全套字型與非 SDK 必要資產。
- Calc、Impress、Base、巨集與任意 automation。

這些不是永遠禁止，而是不能阻塞第一個 Writer Document SDK 垂直切片。

---

## 8. 在 LibreOffice 26.8 上的實作治理

### 8.1 原始碼角色

建議把三種內容分清楚：

| 位置／倉庫 | 角色 | 原則 |
|---|---|---|
| `libreoffice-26-8/` | 唯一 LibreOffice core 與 WASM build 基線 | 只收必要、可測、可上游化或 feature-gated 的修補 |
| 獨立 SDK 倉庫（工作名） | Worker、TypeScript API、Provider SDK、文件、範例 | 不依賴 LO 私有 C++ header |
| `OxOffice/` 舊線 | 行為與架構參考、desktop 相容來源 | 唯讀比對；不作 WASM build 真相來源 |

SDK 的 C/C++ adapter 若必須參與 gbuild，可能仍需以子目錄或 submodule 掛入 LibreOffice build；但其 public headers、ABI schema 與 TypeScript 套件應能獨立版本化。這要用最小探針確認後再決定，現在不應先建立複雜倉庫拓樸。

**2026-08-01 更新（已觀察）**：此問題已由 COWASM co-26.04 對照解答——探針與 SDK adapter 可以**完全不進 gbuild**。26.8 的 Emscripten build 在 `DISABLE_DYNLOADING` 下會產出 `soffice.js.linkdeps`（完整 `-l` 清單），外部 Emscripten 專案以自己的 `main()` 加 `$(cat soffice.js.linkdeps)` 連結整個靜態 core，並複用 core 的 exports 檔、`environment.js` 與 fs image pre-js；COOL 的 `wasm/Makefile.am` 就是這個模式的產品級實作。詳見 [COWASM 參考筆記 §2](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)。

### 8.2 移植不是 cherry-pick 清單

已觀察到 26.8 與 OxOffice 在 Writer Markdown 路徑、NotebookBar 實作位置及 surrounding code 都已有差異。因此每個舊 patch 應採語意 rebase：

1. 寫出舊 patch 要維持的外部行為。
2. 在乾淨的 26.8 行為上建立失敗測試。
3. 檢查 26.8 是否已解決或改變需求。
4. 只補最小差距。
5. 分別跑 native 與 WASM 測試。
6. 記錄 patch 是否適合送上游、只適合 OxOffice，或應刪除。

特別是 Markdown／CJK／BOM 等改動，不可單看 diff 相似度。輸入 stream endian、filter option 與 paste 行為必須用 corpus 測試決定。

### 8.3 建議的 feature boundary

可研究一個明確的 build feature，例如工作名 `OX_WASM_DOCUMENT_SDK`，但正式命名應等探針後決定。理想效果是：

- 上游一般 LOK／WASM bugfix 不帶 OxOffice 品牌。
- SDK 所需的通用窄介面盡量以中性命名提出上游。
- OxOffice 專屬 Provider contract／branding 留在獨立 SDK 倉庫。
- feature 關閉時不改變一般 LibreOffice desktop 行為。
- 每個 core patch 都有 native test，避免只有瀏覽器手測才能維護。

### 8.4 工作樹注意事項

本次研究時的 LibreOffice 26.8 worktree 已有 Qt6-WASM 診斷與資源修補，OxOffice 工作樹也有既存變更。後續開始實作前，應先建立可追蹤的基線與 patch inventory，不能把研究線的新改動混入尚未分類的既有變更。

本文件只描述策略，未變更上述兩棵原始碼樹。

---

## 9. SDK 與協作編輯器的責任邊界

前一份報告主張的 review-first editor 應改成 SDK 的第一個 reference application：

```text
Collaboration editor
  ├─ 閱讀／搜尋／selection UI
  ├─ 留言、presence、版本、edit lease
  ├─ 桌面版交接
  └─ 呼叫 OxOffice WASM Document SDK
       ├─ open／render／save
       ├─ narrow edits
       └─ format compatibility
```

SDK 不負責：

- WebSocket／WebRTC 連線；
- 使用者、群組與 ACL；
- 留言資料庫；
- ODT CRDT；
- 檔案鎖與 object storage；
- toolbar／routing／產品設計。

SDK 可以提供協作需要的 primitive：

- document revision；
- selection／range token；
- deterministic operation result；
- invalidation event；
- save snapshot／export；
- stale operation error；
- undo transaction boundary。

第一版協作仍建議採「單一權威文件版本 + edit lease + sidecar comments」。這能先驗證 SDK，而不讓 ODT 內部模型與即時多人合併同時成為未知數。

---

## 10. 研究階段與決策閘門

### R0：差異與能力盤點

產物：

- OxOffice upstream patch／Core service／Provider contract inventory；
- 對應 LibreOffice 26.8 的「已有／需改寫／不需要」矩陣；
- Writer-only headless configure 與 artifact inventory；
- 可量測的 native、Qt6-WASM 與 headless profile 基線。

通過條件：沒有任何舊 patch 被當成當然必要；每個移植候選都有使用情境與測試入口。

### R1：Document SDK 最小探針

只做一條垂直切片：

```text
ArrayBuffer → open ODT → paint tile → 定位／輸入一個中文字 → save ArrayBuffer
```

同時記錄：

- `.wasm`、`.data`、JS glue 的 raw／gzip／Brotli；
- 首次開啟、首張 tile、存檔時間；
- peak WASM memory；
- Chromium／Firefox 的結果；
- 桌面 LibreOffice 26.8 round-trip。

通過條件：五個步驟可由 JavaScript 重複完成，不靠 Qt widget，也不需人工操作 WASM 內部 UI。

**2026-08-01 補充**：

- 實作依據：探針採 COWASM 式核外連結（不進 gbuild），自帶 `main()` 與最小 C shim；shim 即未來版本化 C ABI 的種子。具體輪廓見 [COWASM 參考筆記 §9](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)。
- 執行緒模型：`-pthread`，模組先在主執行緒 host、運算在 pthreads；不用 JSPI、不用 PROXY_TO_PTHREAD，與 Qt6 線組態明確切開；Worker host 留到 R2。
- embind 不連結：最終核外 probe 確實未連 `unoembind`，但 core exports 不能原樣沿用；需排除
  bridge RTTI、保留檔案載入 catch 必需的單一 UCB exception RTTI，並 wrap 未使用的 JS UNO
  scripting 初始化。詳見 [finding 010](./findings/010-probe-export-list-requires-unoembind.md)。
- CJK 閘門措辭：「輸入一個中文字」指以 LOK API 程式化插入；真 IME composition 屬 R2+ 的 JS UI 工程，不作為 R1 的 No-Go 判準。
- 執行 spec：[specs/SPEC-R1-000-overview.md](./specs/SPEC-R1-000-overview.md)（A 建置／B 探針程式／C 量測驗收，2026-08-01 定稿）。

**2026-08-01 結果：GO。** Chrome 150 與 Firefox 152 均可自動完成完整五步驟；三份文件
共 24 份輸出全數通過桌面 round-trip。Probe runtime raw 259.72 MiB、gzip 84.58 MiB，較
Qt6-WASM 基線分別小 8.74%／5.96%；可行性成立，但體積降幅尚不足以宣稱已達輕量產品目標。
完整數字、限制與 R2 建議見
[R1 實測 DEVLOG](./DEVLOG-2026-08-01-wasm-sdk-probe.md)。

### R2：穩定 binding 與 Worker runtime

產物：

- 最小、版本化 C ABI；
- handle lifecycle tests；
- Worker message protocol；
- TypeScript wrapper；
- crash／timeout／cancel／buffer ownership 測試。

通過條件：應用程式不接觸 raw pointer、UNO object 或 Emscripten runtime 細節。

**2026-08-01 執行決策**：R2 只處理 binding、Worker 隔離與 lifecycle；體積最佳化已確認
延後至 R5，不在建立 ABI／protocol 的同時改動 link graph 或資源集合。可執行邊界與驗收見
[SPEC R2-000](./specs/SPEC-R2-000-overview.md)。

**2026-08-01 結果：GO。** C ABI 1.0、Worker protocol v1、Dedicated Worker 與
TypeScript-first SDK 已完成。Chrome 150／Firefox 152 各 3 次正式垂直切片及兩邊 13 項
lifecycle／ownership／error-boundary conformance 全數通過；closure hardening 再增加各 1 次
完整流程與 round-trip。主執行緒未暴露 Emscripten runtime。R2 runtime 相較 R1 raw／gzip
只增加約 0.012%，依決策僅記錄漂移、不做最佳化。完整數字、限制與 R3 交接見
[R2 DEVLOG](./DEVLOG-2026-08-01-wasm-sdk-r2.md)。

### R3：review operations

依序驗證：

1. search／selection；
2. replace short text；
3. undo transaction；
4. comment／redline 可行性；
5. Markdown 或結構化結果插入。

通過條件：每個操作都有 stale revision、undo 與 desktop round-trip 測試。

**2026-08-01 執行決策**：R3 使用 ABI 1.1 backward-compatible minor bump，公開
search／selection／replace／undo／comment／tracked-change 語意方法與單調 revision guard；不提供
任意 UNO command passthrough。Markdown parser 不納入本輪，先以 validated
`replaceSelection` operation 驗證結構化結果寫入。可執行邊界見
[SPEC R3-000](./specs/SPEC-R3-000-overview.md)。

**2026-08-01 結果：GO。** ABI 1.1 semantic review SDK 已完成 search／selection／replace／
undo／comment／tracked-change 與單調 revision guard。Chrome 150、Firefox 152 各 3 次完整流程
6/6 通過；輸出 ODT 均保有 comment 與 tracked-change markup，桌面 LibreOffice round-trip
全數通過。1.0 client 相容、較新 minor／不同 major 拒絕、R2 conformance 與 R1 legacy flow
也都跨兩個瀏覽器通過。Runtime 相較 R2 raw／gzip 僅增加約 0.0084%／0.0111%，依決策只記錄
漂移。完整結果與 R4 交接見
[R3 DEVLOG](./DEVLOG-2026-08-01-wasm-sdk-r3.md)。

### R4：Provider SDK

先做一個最簡 provider，例如「取得目前選取文字 → 非同步轉換 → 提出 replace operation」。不要先搬完整 oxmsp_ai 或整套 sidebar。

通過條件：同一份 provider domain fixture 可在桌面 adapter 與 Web adapter 上通過，且 provider 無法繞過 operation validator 直接修改文件。

**2026-08-01 執行決策**：R4 定義獨立 Provider contract 1.0，第一個 closed capability 為
`text.translate`，只接受 immutable `selection.text` snapshot、只產生帶 snapshot revision 的
`replaceSelection` operation。瀏覽器 Provider 使用獨立 Dedicated Worker；Host 持有 Web／desktop
document adapter 並在套用前驗證 operation。完整 schema UI、identity／secret、remote transport、
streaming、scaffolder 與完整 hostile-code sandbox 不納入本輪。可執行邊界見
[SPEC R4-000](./specs/SPEC-R4-000-overview.md)。

**2026-08-01 結果：GO。** Provider registry／host／validator、Worker transport、Web／desktop
contract adapters 與共用 fixture 已完成；同一 fixture 在兩種 adapter 得到相同 operation。Chrome
150、Firefox 152 各 3 次真實文件流程 6/6 通過，含 progress、取消不落地、concurrent edit stale
rejection、undo recovery 與 validated replace。6 份 ODT 均通過桌面 round-trip，R3／R2／R1 回歸
也全部跨兩個瀏覽器通過。Core artifacts 與 R3 byte-for-byte 相同；R4 browser layer raw 新增
45,229 bytes，僅記錄、不在本輪最佳化。完整結果與 R5 交接見
[R4 DEVLOG](./DEVLOG-2026-08-01-wasm-sdk-r4.md)。

### R5：資源與體積 profile

R1 實測後已確認：所有體積最佳化集中於本階段；R2～R4 只持續記錄產物是否意外成長，
不以調整 optimization、scripting、字型、registry 或 filter 作為各階段工作。

產物：

- reader／review／automation／full-qa 對照；
- 字型 fallback pack 與可選 CJK pack；
- 必要 filter／registry／configuration inventory；
- cache、分包與首載策略。

通過條件：每個減量都有功能回歸測試，不以刪檔後「剛好能啟動」作成功標準。

**2026-08-01 執行決策**：R5 產出 `full-qa`、`writer-review`、`writer-reader`，但
`writer-automation` 在受控 operation／權限契約定義前保持 `not-shippable`。資源拆為 base、startup
CJK 與 optional fallback-font packs，hash artifact 與 entry／manifest 採不同 cache policy。可執行
邊界見 [SPEC R5-000](./specs/SPEC-R5-000-overview.md)。

**2026-08-01 結果：GO。** Review WASM raw 由 169.26 MB 降為 115.27 MB；中文首載資源由
102.77 MB 降為 base 34.18 MB + CJK 19.48 MB，其餘 49.10 MB fallback fonts 延後載入。Chrome 150／
Firefox 152 的 review 6/6、reader cold 6/6、reader warm-cache 6/6 通過，18 份產品 profile ODT 均通過
ZIP／XML、內容與桌面 LibreOffice round-trip；R1～R4 回歸、profile exports、resource integrity 與
cache contract 也全數通過。完整限制與數據見 [R5 DEVLOG](./DEVLOG-2026-08-01-wasm-sdk-r5.md)。

### R6：協作 reference application

以前一份報告的閱讀、留言、少量修改與桌面交接需求驗證 SDK。第一版維持「不可變文件版本 + sidecar
留言／建議 + 單一短效 edit lease + ETag compare-and-swap」；遠端更新採明確 reload，不把 ODT 當
CRDT，也不允許 last-write-wins。

**2026-08-02 執行規劃**：R6 分成 reader shell、collaboration contract／reference service，以及雙
client reference app 驗收。建議 anchor 只在 base version 相符且 quote 唯一時自動套用；selection
token、tile 座標與頁碼不視為跨版本穩定 ID。重要失敗、架構限制與瀏覽器差異必須在發現當下寫入
DEVLOG／finding 並保存原始 evidence。可執行邊界見 [SPEC R6-000](./specs/SPEC-R6-000-overview.md)，
後續候選與進入條件見 [R6+ 路線圖](./specs/SPEC-R6+-roadmap.md)。

若 R6 只能靠修改 LibreOffice core、暴露 raw UNO／Emscripten surface、靜默猜測 anchor 或放寬成
last-write-wins 才成立，應停止並評估 server-native LOK + 精簡 JS UI，而不是為維持 WASM 名義擴大
fork。

---

## 11. QA 與相容策略

### 11.1 測試金字塔

1. **Native core tests**：Writer operation、filter、undo、Markdown、round-trip。
2. **C ABI tests**：handle、memory、error、cancel、version negotiation。
3. **Worker／TypeScript tests**：serialization、transfer、事件順序、重啟。
4. **Browser integration**：open／render／input／save、CJK、IME、clipboard。
5. **Document corpus**：ODT、DOCX、字型缺失、複雜段落、表格、圖片、track changes。
6. **Product workflow**：留言、edit lease、版本衝突、桌面交接。

### 11.2 QA profile 與產品 profile 分離

`full-qa` 可以保留 assertion、符號與較完整 component，產品 profile 則關閉 debug 並減少資產。兩者應由同一 commit 產生並共享功能測試，避免「只有 release 會壞」或「為減肥而失去診斷能力」。

### 11.3 必須優先覆蓋 CJK

本次 Qt6-WASM 實驗已顯示中文輸入與英文重複輸入可能受平台 input context 影響。Document SDK 若不使用 Qt，會避開該條 Qt input context 路徑，但不能因此假設 IME 已解決。Worker boundary、composition event、selection replacement、全形標點、surrogate pair 與 clipboard 都需獨立測試。

### 11.4 相容版本政策尚待研究

至少要區分：

- SDK npm package 版本；
- Worker／message protocol 版本；
- C ABI 版本；
- LibreOffice 26.8 core revision；
- Provider contract version；
- resource pack version。

初期應把這些版本寫進產物 manifest，禁止 JS package 與不相容 WASM 靜默混用。

---

## 12. 主要風險

| 風險 | 影響 | 研究對策 |
|---|---|---|
| LOK tiled API 仍不穩定 | 上游升版可能破壞 adapter | 自有窄 ABI、conformance tests、最小上游 patch |
| headless WASM 不含可用 tile path | 核心產品假設失效 | 風險已下修：`--disable-gui` 即 headless svp backend（COWASM 生產路徑）；R1 改聚焦驗證無 COOL 中間層的裸 LOK 啟動序 |
| 靜態 component 隱含相依 | linker 成功但 runtime 找不到 service | component manifest、啟動 smoke、逐 profile 測試 |
| Writer core 仍然很大 | 首載不符合產品需求 | 實測 profile、資源分包、快取；必要時 server fallback |
| memory growth／大文件 | 瀏覽器分頁崩潰 | 文件限制、page/tile cache policy、壓力測試 |
| raw UNO API 膨脹 | SDK 無法穩定、Provider 權限過大 | UNO 只放 automation profile，預設 semantic API |
| API scope creep | 最後又變成完整 Web Office | review-first capability budget、桌面交接 |
| 舊 OxOffice patch 誤移植 | 回歸或重複上游功能 | semantic rebase、先測試、逐項刪除過時 patch |
| WASM 原生 plugin 期待 | 每個 Provider 都要重連大核心 | JS／Worker／remote provider 優先 |
| fork 維護成本 | 26.8 更新困難 | 主樹 patch 最小化、通用修正優先送上游 |
| 授權、商標與散布方式 | SDK 產品化受限制 | 另做 MPL／第三方套件／商標法律檢視；本報告不下法律結論 |

---

## 13. 上游與 OxOffice 的分工策略

### 13.1 優先送上游的內容

- LibreOffice 26.8 可重現的 Qt6／headless WASM bugfix。
- 不帶 OxOffice 產品假設的 LOK 修正。
- Writer filter、CJK、round-trip 與 undo 的一般性修正。
- 通用、窄而有測試的 document operation，若上游接受其 API 方向。
- WASM build profile、component dependency 與 size diagnostics 改善。

### 13.2 留在 OxOffice SDK 的內容

- Provider capability taxonomy。
- schema-driven product UI contract。
- identity host integration。
- 客戶後端、AI provider、企業 policy。
- SDK npm package、Worker orchestration 與 reference application。
- OxOffice 品牌、發佈與商業支援政策。

### 13.3 可雙邊共用但不同 binding 的內容

- provider descriptor fixtures；
- operation schema；
- error／progress taxonomy；
- Markdown／artifact insertion corpus；
- capability conformance suite。

這個分工可以避免為了 Web SDK 把所有 OxOffice 客製化塞進 LibreOffice core，也避免桌面與 Web 兩套 Provider 生態完全分裂。

---

## 14. 近期最小工作建議

真正開始實作時，建議順序如下：

1. 凍結一個可重現的 LibreOffice 26.8 + Emscripten toolchain 基線。
2. 對現有 26.8 worktree 的 Qt6-WASM 修補先分類，避免與 SDK 實驗混線。**已完成（2026-08-01）**：五個修改已落成具名 patch 並分類兩線歸屬，見 [INVENTORY.md](./wasm-lite/patches/INVENTORY.md)。
3. 建立 Writer-only、`--disable-gui` 的 headless build profile。
4. 盤點產物是否實際含 LOK init、document load、tile、input、callback 與 save 路徑。
5. 寫最小 `wasm_sdk_probe`，只完成 `open → paintTile → input → save`。
6. 量測產物與記憶體，再決定 C ABI 與 Worker 的第一版範圍。
7. 垂直切片成功後，才移植第一個 OxOffice 窄能力；候選是 selection-safe replace 或重新評估過的 Markdown insert。
8. 最後才開始 Provider SDK 與 collaboration editor 整合。

不建議第一步就把整個 `ossii_extension/` 複製到 LibreOffice 26.8。那會先引入 VCL、framework、sfx、svx、UNO registration 與 desktop packaging 相依，卻仍未回答 Document SDK 最核心的 open／render／save 是否成立。

---

## 15. 初步 Go／No-Go 準則

### Go

- Writer-only headless WASM 可以從 JS 完成 open／render／narrow edit／save。
- 產物體積、首張畫面時間與記憶體明顯優於完整 Qt6-WASM 基線。
- C ABI 可把 LOK／UNO 細節封裝在 Worker 內。
- ODT 與目標 DOCX corpus 的 round-trip 可接受。
- CJK／IME 的核心操作可跨主要瀏覽器重現。
- 第一個 Provider 能透過受控 operation 完成任務，不直接持有文件內部物件。

### Pivot

- headless WASM 長期無法提供可靠 tile／input／save；
- 瀏覽器記憶體或初始化成本仍不適合目標裝置；
- 受控少量編輯仍需暴露大量不穩定 UNO；
- 文件相容性或存檔 round-trip 無法達到 QA 門檻。

Pivot 不代表整個 SDK 概念失敗。TypeScript Document API、Provider contract 與 reference application 仍可改接 server-native LibreOfficeKit，使前端與客製開發投資保留。

---

## 16. 結論

「OxOffice WASM Document SDK」值得成為獨立研究線，而且應以 LibreOffice 26.8 為唯一實作環境。OxOffice 舊線最有價值的不是其較早基底或原生元件打包方式，而是已經形成的 Core／Provider 分工、受控 Data Sink、非同步契約、schema UI、窄核心服務與 patch 治理經驗。

建議的長期形態是：

> **LibreOffice 26.8 Writer headless WASM 提供文件引擎；窄、版本化 C ABI 與 Worker 封裝核心；TypeScript Document SDK 服務應用；Provider SDK 承接 OxOffice 客製生態；輕量協作編輯器成為第一個 reference application。**

這也回答了「可否把 OxOffice 客製化搬到上游版本」：**可以，但應搬語意、契約、測試與必要窄服務；不應整包搬桌面 UI、舊 ABI 與舊分支歷史。**

下一個能真正降低風險的里程碑仍是小而明確的 `wasm_sdk_probe`。在它證明 open／paintTile／input／save 以前，SDK 架構保持研究狀態；一旦通過，才有足夠證據進入 API spec 與正式移植計畫。

---

## 17. 本機資料來源

### 17.1 本研究工作區

- [LibreOffice WASM 輕量協作編輯器研究報告](./RESEARCH-2026-08-01-wasm-collaboration-editor.md)
- [Qt6-WASM 開發紀錄](./DEVLOG-2026-08-01-qt6-wasm.md)
- [LibreOffice 26.8 WASM 建置說明](./libreoffice-26-8/static/README.wasm.md)
- [LibreOfficeKit 說明](./libreoffice-26-8/libreofficekit/README.md)
- [LibreOfficeKit C API](./libreoffice-26-8/include/LibreOfficeKit/LibreOfficeKit.h)
- [LibreOfficeKit callbacks／events](./libreoffice-26-8/include/LibreOfficeKit/LibreOfficeKitEnums.h)
- [Emscripten `soffice` 連結設定](./libreoffice-26-8/desktop/Executable_soffice_bin.mk)
- [Emscripten filesystem image 規則](./libreoffice-26-8/static/CustomTarget_emscripten_fs_image.mk)
- [COWASM co-26.04 參考研究筆記](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)
- [worktree patch inventory](./wasm-lite/patches/INVENTORY.md)

### 17.2 OxOffice 參考資料

- [OSSII Extension Framework Provider reference](/home/jiajun/LibreOffice/OxOffice/ossii_extension/devtools/oxext-new/REFERENCE.md)
- [Provider scaffolder README](/home/jiajun/LibreOffice/OxOffice/ossii_extension/devtools/oxext-new/README.md)
- [`ossii.ui/1` schema 研究](/home/jiajun/LibreOffice/OxOffice/ossii_extension/docs/ui-schema.md)
- [可分離發佈模式研究](/home/jiajun/LibreOffice/OxOffice/ossii_extension/docs/separable-release-packaging.md)
- [Markdown native replacement 與上游關係](/home/jiajun/LibreOffice/OxOffice/ossii_extension/docs/markdown-native-replacement-and-upstream-relation.md)
- [Markdown UNO API proposal](/home/jiajun/LibreOffice/OxOffice/ossii_extension/docs/markdown-uno-api-proposal.md)
- [OxOffice upstream patch manifest](/home/jiajun/LibreOffice/OxOffice/ossii_extension/UPSTREAM_PATCHES.md)
- [Provider IDL](/home/jiajun/LibreOffice/OxOffice/ossii_extension/com/ossii/ext/dispatch/XOSSIIServiceProvider.idl)
- [Data Sink IDL](/home/jiajun/LibreOffice/OxOffice/ossii_extension/com/ossii/ext/sink/XOSSIIDataSink.idl)
- [Markdown renderer IDL](/home/jiajun/LibreOffice/OxOffice/offapi/com/sun/star/text/XMarkdownRenderer.idl)

---

## 18. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-01 | 初版。將 OxOffice WASM Document SDK 建立為獨立研究線；確立 LibreOffice 26.8 實作基線；整理 OxOffice 客製架構的移植分級、SDK 分層、研究階段與 Go／No-Go 準則。 |
| 2026-08-01 | 併入 COWASM co-26.04 對照：確認核外連結機制（§8.1 倉庫拓樸問題解答）、R1 執行緒模型與 CJK 閘門措辭、headless tile path 風險下修、單執行緒探針假設修正；worktree patch inventory 完成。 |
| 2026-08-01 | 完成 R1-A～C：雙瀏覽器垂直切片與 24 份 ODT round-trip 通過，判定 GO；回填體積／時間／記憶體限制，並修正「unoembind 可自然省略」的 exports 與 exception RTTI 邊界。 |
| 2026-08-01 | 啟動 R2；定稿版本化 ABI／Worker runtime 邊界，並確認體積最佳化全部延後至 R5。 |
| 2026-08-01 | 完成 R2：C ABI 1.0、Dedicated Worker 與 TypeScript-first SDK 通過雙瀏覽器垂直切片、lifecycle conformance 及桌面 round-trip，判定 GO；體積最佳化維持延後至 R5。 |
| 2026-08-01 | 啟動 R3；定稿 ABI 1.1 相容升版、semantic review operations、revision guard 與無 generic UNO passthrough 邊界。 |
| 2026-08-01 | 完成 R3：ABI 1.1 semantic review operations、revision guard、comment／tracked-change ODT round-trip 與 R1／R2 雙瀏覽器回歸全數通過，判定 GO；體積最佳化維持延後至 R5。 |
| 2026-08-01 | 完成 R4：Provider contract 1.0、隔離 Worker、Web／desktop adapters 與 operation validator 通過雙瀏覽器及 R1～R3 回歸，判定 GO。 |
| 2026-08-01 | 完成 R5：review／reader product profiles、resource packs、content hash／cache contract、18 份 ODT round-trip 與 R1～R4 回歸通過，判定 GO；Automation 保持 not-shippable。 |
| 2026-08-02 | 規劃 R6：以 reader shell、sidecar collaboration、edit lease、ETag CAS 與雙 client reference app 驗證完整 review-first 工作流；建立 R6+ evidence-driven 路線圖。 |

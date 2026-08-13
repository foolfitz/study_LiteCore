# LibreOffice WASM 輕量協作編輯器研究報告

> **日期**：2026-08-01  
> **研究狀態**：初步可行性研究，尚非需求規格、技術規格或專案計畫  
> **研究對象**：以 LibreOffice Technology／LibreOfficeKit 與 WebAssembly 為文件核心，建立偏重閱讀、審閱與少量文字修改的瀏覽器協作工具  
> **產品假設**：進階編輯應回到桌面版 LibreOffice；Web 端不追求重製完整 Collabora Online  
> **資料基準**：LibreOffice 26.8、Qt 6.10.2、Emscripten 4.0.10 的本機實驗結果

---

## 0. 文件定位

這份文件的目的是整理目前證據、比較可能架構、列出研究假設，並設計下一輪最小實驗。它刻意不做以下事情：

- 不凍結 API、網路協定、資料庫 schema 或部署拓樸。
- 不承諾時程、人力或正式 MVP 範圍。
- 不把尚未在本機跑通的 LibreOfficeKit WASM 路徑描述成既有能力。
- 不假設只要「拿掉 Qt」就會自動得到小型且成熟的 Web 編輯器。
- 不把本報告中的體積推估視為正式產品預算。

本文使用三種標記：

- **已觀察**：可由本機產物、原始碼或上游文件直接確認。
- **推論**：由已知證據推導，但還沒有完成端到端實驗。
- **研究假設**：值得用實驗驗證，現在不能當成結論。

---

## 1. 摘要

### 1.1 建議方向

目前最值得研究的方向不是繼續把完整 LibreOffice 桌面 UI 塞進瀏覽器，也不是直接用 JavaScript 重寫一套 ODT／DOCX 排版引擎，而是：

> **用 JavaScript 建立精簡的閱讀與協作介面，以瀏覽器內的 LibreOffice WASM 核心負責文件解析、排版、少量編輯與存檔；伺服器只保管檔案、版本與協作狀態。**

暫稱此方向為「review-first editor」，而不是「Web 版 LibreOffice」。它的核心價值是：

1. 文件顯示與存檔仍盡量沿用 LibreOffice 的格式相容性。
2. 日常伺服器不必替每位使用者持續執行完整 LibreOffice process。
3. JavaScript UI 可以只提供閱讀、搜尋、留言、建議修改及少量文字更正。
4. 遇到複雜表格、圖片錨點、樣式、巨集或版面調整時，明確交接給桌面版。

### 1.2 最重要的保留條件

此方向仍是**研究賭注**，不是已成熟的上游產品路徑。LibreOfficeKit 已有載入文件、圖磚渲染、鍵鼠輸入、選取、貼上、存檔、多視圖及 callback 等 C/C++ API，但目前還需要證明：

- 它能否以合理的 Emscripten binding 暴露給 JavaScript。
- headless／LOK WASM 建置是否真的包含可用的 tile rendering，而不只是 UNO 文件模型。
- Writer 的 CJK 輸入、選取、游標、搜尋、複製與存檔能否在 Web Worker 邊界正確運作。
- 拿掉 Qt UI 後的實際 `.wasm` 體積，而不是憑模組名稱推估。
- 文件重新存檔後，桌面版 LibreOffice 是否能維持可接受的版面與格式 round-trip。

因此，下一階段不應先寫完整協作系統，而應先做四個串起來的技術閘門：

1. JavaScript `ArrayBuffer` 能載入一份 ODT。
2. LibreOffice 核心能渲染至少一張 Writer tile 到 `<canvas>`。
3. 使用者能定位游標並插入一個中文字元。
4. 文件能輸出為新的 `ArrayBuffer`，且桌面版 LibreOffice 可正常開啟。

四項全部通過後，才值得把它發展成閱讀器與協作產品。

### 1.3 與 TDF 2026 策略的關係

TDF 於 2026 年 5 月公布的 Web／Mobile 策略提案，本身也明確表示它不是技術規格。提案主張：

- Web 版可以採精簡操作介面，進階工作回到桌面版。
- 高成本運算應盡量留在客戶端。
- 文件伺服器應便宜且容易架設，面向「許多小型雲端」。
- 協作先採 client-server 與單一權威狀態，再研究 P2P。
- Qt 6 + WebAssembly 原型是 2026 年要繼續改善的正式研究方向。

本報告的產品方向與上述原則高度相容；主要差異是：TDF 目前公開主線著重打磨完整 Qt6-WASM 原型，本報告另外提出「LOK WASM + JavaScript 精簡 UI」作為較貼近 review-first 需求的研究分支。

---

## 2. 需求重新定義

### 2.1 真正要取代的是工作流程，不是整個 Collabora Online

「取代 Collabora Online」容易被理解為重做完整辦公套件，但目前需求其實更窄：

- 多數時間是閱讀文件。
- 協作重點是知道誰在看、針對內容留言、標記問題與提出修正。
- 直接編輯只需更正幾個字、短句或明顯錯字。
- 不要求在 Web 完成複雜排版。
- 使用者願意在必要時切換到桌面版 LibreOffice。

因此，成功指標不該是「支援多少 LibreOffice toolbar command」，而應是：

- 文件打開得夠快，閱讀版面可信。
- 多人審閱不會互相覆蓋。
- 少量修改可保存並追溯。
- 可以清楚知道目前看到的是哪個版本。
- 從 Web 切到桌面版的成本低。

### 2.2 建議的產品語彙

產品若稱為「編輯器」，使用者自然會期待完整格式工具。研究期間較適合使用以下定位：

- LibreOffice Review
- 文件協作閱讀器
- Review-first document editor
- Lightweight document review client

這不是純命名問題。名稱會反過來約束 UI：主畫面應優先放搜尋、留言、建議修改、版本與「以桌面版開啟」，而不是複製桌面版選單與 toolbar。

### 2.3 初步功能邊界

**Web 端候選功能：**

- 開啟 ODT；DOCX 是否納入第一階段取決於 round-trip 實測。
- 分頁閱讀、縮放、捲動及頁面縮圖。
- 搜尋、文字選取、複製。
- 留言、回覆、resolve。
- presence：顯示在線使用者與所看頁面，避免一開始就同步每個游標。
- 以「建議替換」提交短文字修改。
- 在取得編輯租約後，直接更正少量文字。
- 儲存成新版本，而非靜默覆蓋舊檔。
- 下載、WebDAV 回存或交給桌面版開啟。

**第一階段明確排除：**

- 完整 Writer 選單、Sidebar、Notebookbar 與對話框。
- 複雜段落／頁面樣式、目錄、欄位、交叉參照。
- 表格重構、圖片錨點、繪圖物件與精細排版。
- 巨集、擴充套件、郵件合併、資料來源。
- Calc、Impress、Draw 的完整編輯。
- 多位使用者同時直接改動同一份 Writer model。
- 以 CRDT 直接描述所有 ODF／OOXML 語意操作。

這些不是永遠禁止，而是用來保護研究焦點。

---

## 3. 目前 Qt6-WASM 實驗基線

### 3.1 已完成事項

依本機 [DEVLOG-2026-08-01-qt6-wasm.md](../devlog/DEVLOG-2026-08-01-qt6-wasm.md)：

- LibreOffice 26.8 已用 Qt 6.10.2 與 Emscripten 4.0.10 完成 WASM 建置。
- Start Center 與 Writer 已能在瀏覽器啟動。
- 經執行緒／event loop 修補後，中文輸入可用。
- 英文實體按鍵仍有一次輸入兩個字元的問題。
- 這證明「LibreOffice 26.8 + Qt6 + WASM」在本機不是紙上架構，而是已跨過建置與第一次執行期啟動的原型。

這條路對 LibreOffice 26.8 QA 與上游貢獻仍很有價值，即使產品日後改採 JavaScript UI。它提供：

- Qt6 VCL backend 的 WASM 測試案例。
- CJK IME 與鍵盤事件問題的可重現環境。
- 完整桌面 UI 行為的比較基準。
- 評估「拿掉 Qt UI」到底省多少的對照組。

### 3.2 目前 runtime 體積

量測對象：

`wasm-lite/build-qt6-poc/instdir/program/`

| 檔案 | 未壓縮 bytes | 約略 MiB | `gzip -9` bytes | 約略 MiB |
|---|---:|---:|---:|---:|
| `soffice.wasm` | 194,985,858 | 185.95 | 51,215,990 | 48.84 |
| `soffice.data` | 102,087,692 | 97.36 | 42,877,250 | 40.89 |
| `soffice.js` | 1,349,015 | 1.29 | 214,410 | 0.20 |
| **合計** | **298,422,565** | **284.60** | **94,307,650** | **89.94** |

另有 `soffice.wasm.debug.wasm`：203,270,779 bytes，約 193.85 MiB。它是外部除錯資訊，不是正常 runtime 首載所必需，因此不能把它加進產品下載量；但正式發佈仍應確認 web server 沒有意外預載或公開錯誤引用。

### 3.3 「整體首載」與「gzip 首載」

- **整體首載未壓縮體積**是瀏覽器解壓後要處理、編譯或放入虛擬檔案系統的資料量。本機約 284.60 MiB。
- **gzip 首載體積**是第一次使用、快取為空時，網路實際傳輸量的近似值。本機約 89.94 MiB。
- gzip 並不會讓瀏覽器只承擔 89.94 MiB。資料下載後仍要解壓，WASM 還要驗證／編譯，`.data` 還要映射進 Emscripten 檔案系統。
- 第二次載入若 HTTP cache、Service Worker cache 與瀏覽器的 WASM code cache 命中，體感可能比第一次好很多。因此產品研究必須分別量測冷啟動與熱啟動。

### 3.4 `soffice.data` 實際組成

本次不是只以目錄名稱猜測，而是讀取：

`soffice.data.js.metadata`

其中每個檔案都有在 `.data` 裡的起訖位址。依路徑分類後：

| 類別 | bytes | 約略 MiB | 佔 `.data` |
|---|---:|---:|---:|
| 字型 `/instdir/share/fonts` | 72,945,990 | 69.57 | 71.5% |
| UI／圖示設定 `/share/config` | 18,989,824 | 18.11 | 18.6% |
| Registry | 3,303,062 | 3.15 | 3.2% |
| Filter 資料 | 1,829,164 | 1.74 | 1.8% |
| liblangtag | 1,820,589 | 1.74 | 1.8% |
| program 資料 | 1,774,194 | 1.69 | 1.7% |
| Gallery | 979,519 | 0.93 | 1.0% |
| Android 範例文件 | 284,865 | 0.27 | 0.3% |

最大的單一檔案是自行加入的 `NotoSansCJK-Regular.ttc`：19,484,784 bytes，約 18.58 MiB。其餘內建字型合計仍約 50.99 MiB。

這項量測帶來兩個直接結論：

1. 字型是目前 `.data` 最值得先處理的項目。
2. 完整 Qt UI 的設定與圖示資產也占了約 18 MiB；改用 JS UI 可能同時省掉部分程式碼與這些資料，但必須用新產物量測，不能直接把 18 MiB 全數相減。

---

## 4. 技術背景：JavaScript UI 能取代什麼

### 4.1 Qt 在目前建置中的角色

Qt6 是 LibreOffice VCL 的平台 backend，負責把桌面視窗、輸入、事件迴圈與 canvas／瀏覽器平台接起來。它不是 Writer 文件模型本身，也不是 ODT／DOCX filter。

因此，「以 JavaScript 重寫 UI」理論上可以取代：

- Start Center、選單、toolbar、Sidebar 與多數 dialog。
- Qt widget 的繪製與瀏覽器輸入轉接。
- 大量完整桌面 UI 資產。

但它不能自動取代：

- Writer 文件 model。
- ODF／OOXML 載入與儲存 filter。
- VCL 的文件繪圖抽象與 headless rendering。
- 字型解析、HarfBuzz shaping、ICU 斷行。
- 圖片、表格、欄位、頁面樣式與 Writer layout。

所以，JavaScript UI 是一條合理的產品方向，但不等於把 186 MiB 的 `soffice.wasm` 變成幾 MiB。真正能省多少，要看新的 link graph、啟動元件與 filter 範圍。

### 4.2 LibreOfficeKit 提供的邊界

LibreOfficeKit（LOK）是外部軟體嵌入 LibreOffice 的 C/C++ API。官方文件將 tiled rendering 標為 experimental／unstable，但目前 26.8 headers 已包含：

- `documentLoad`
- `initializeForRendering`
- `paintTile`（32-bit BGRA bitmap）
- `registerCallback`
- `postKeyEvent`、`postMouseEvent`
- `setTextSelection`、`getTextSelection`
- `paste`
- `saveAs`
- `createView`、`setView`、`setViewReadOnly`
- tile invalidation、游標、選取範圍及其他 callback

這組 API 很接近 JS 文件畫布需要的最小邊界：JS 傳入輸入事件，LOK 回傳 bitmap 與狀態變更。

但要特別區分：

- **原生 LOK + JS 前端**已由 Collabora Online 長期產品化。
- **把 LOK 本身搬進同一個瀏覽器 WASM instance**仍需完成 binding、threading、輸入與輸出實驗。
- LibreOffice 的 headless WASM README 說明它可供其他 UI 軟體使用，也提到 COWASM；這不能直接證明上游已提供一個裸 LOK 的瀏覽器 SDK。

**2026-08-01 更新**：COWASM 的 co-26.04 實作已完成對照研究（本機 `cool-26-04/`，見 [COWASM 參考筆記](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)）。兩個要點：（1）COWASM 以核外連結把整個 COOL stack 編進瀏覽器 WASM，證明 headless core + tile rendering 在瀏覽器可運作，「裸 LOK 探針」的風險由「是否可行」下修為「啟動序工程」；（2）Collabora 已把 LOK 改名為 COKit 自行演化（`include/LibreOfficeKit` 在其 engine 已消失），LOK unstable 是現實而非警語，客戶端必須包自己的窄 adapter。

### 4.3 UNO／ZetaJS 是另一種邊界

allotropia 的 LOWA／ZetaJS 使用 Embind 把 UNO 映射到 JavaScript。這證明 JavaScript 可以控制瀏覽器內的 LibreOffice 文件模型，例如列舉段落或修改文字屬性。

但 UNO binding 與 LOK tile rendering 解決的是不同問題：

- UNO 適合模型操作與自動化。
- LOK 適合把既有排版結果繪成 tile，並回報游標、選取與 invalidation。

一個 review-first 產品可能最後同時需要兩者：用 LOK 顯示與基本互動，用很窄的 UNO bridge 完成「替換選取文字」等語意操作。不過第一個實驗應只選一條最短路徑，避免同時承擔兩套 binding。

---

## 5. 架構選項比較

| 選項 | UI | LibreOffice 運算位置 | 優點 | 主要問題 | 與本需求契合度 |
|---|---|---|---|---|---|
| A. 完整 Qt6-WASM | Qt/VCL 桌面 UI | 瀏覽器 | 已在本機啟動；最大程度沿用桌面碼 | 首載大、桌面 UI 不符合精簡需求、WASM 平台 bug 多 | 中，適合 QA／參考實作 |
| B. LOK WASM + JS | 自製 JS review UI | 瀏覽器 | 保留 LO 排版與格式、UI 可極簡、伺服器便宜 | 瀏覽器 binding 與 tile/input/save 尚未跑通 | **高，但屬研究路徑** |
| C. 原生 LOK + JS | 自製 JS UI | 伺服器 | 最成熟；可參考 Collabora | session 運算與記憶體留在伺服器，與輕主機目標衝突 | 中，適合作為 fallback |
| D. 純 JS 文件模型 | 自製 JS UI | 瀏覽器 | 可做到最小首載、Web 原生協作容易 | 必須重做格式解析、排版與 round-trip，相容性風險最高 | 低，除非只支援自有格式 |
| E. COWASM 型離線 fallback | Collabora JS UI | 平時伺服器、離線時瀏覽器 | 已有產品脈絡；斷線可編輯 | 仍帶完整 COOL 架構與較完整 UI，並非本需求的最小解 | 中低，可借鏡而非照搬 |

### 5.1 為什麼暫時偏向 B

B 同時保留三個最有價值的東西：LibreOffice layout、JS UI 自由度、client-side compute。它也最符合「只看、留言、改幾個字；重編請回桌面版」的產品界線。

不過，B 是否能成立取決於 LOK-WASM POC。若 POC 無法在合理時間內完成 tile rendering、輸入及存檔，應退回 C，而不是無限期重構 LibreOffice core。

### 5.2 可能的混合 fallback

產品可以允許兩種 engine：

- 平常優先在瀏覽器使用 WASM engine。
- 瀏覽器不支援 SharedArrayBuffer、記憶體不足或文件超過門檻時，改用伺服器原生 LOK renderer。

這會提高維護成本，因此不應放入第一個 POC；但它比要求所有瀏覽器都下載並執行同一份巨型 WASM 更有實務彈性。

---

## 6. 建議研究架構

```text
瀏覽器
├── JavaScript Review UI
│   ├── 頁面／tile 畫布
│   ├── 搜尋、選取、複製
│   ├── 留言與建議修改
│   ├── presence 與版本提示
│   └──「以桌面版開啟」
│
├── Document Engine Worker
│   ├── LibreOfficeKit WASM
│   ├── Writer model / layout / filters
│   ├── tile cache 與 invalidation
│   └── 載入、少量編輯、另存新版本
│
└── Collaboration Client
    ├── WebSocket / SSE：事件與 presence
    └── HTTP / WebDAV：文件版本與上傳下載

輕量伺服器
├── 認證與權限
├── 文件 blob / object storage
├── 版本、ETag 與 audit log
├── 留言／建議修改 sidecar
├── presence
└── 短期 edit lease
```

### 6.1 為什麼文件 engine 應放 Worker

- 大型 WASM 的啟動、排版與 tile rendering 不應阻塞瀏覽器主 UI。
- Emscripten 的同步檔案與 module splitting 在 Web Worker 上較有操作空間。
- Pthreads／SharedArrayBuffer 的需求可集中處理。
- JS UI 與文件核心之間可以建立明確、可記錄的 message protocol。

代價是所有 tile、輸入事件與狀態都要跨 worker 邊界。應避免把整份畫布像素頻繁複製，研究 `Transferable`、共享記憶體或 `OffscreenCanvas` 是否合適。

### 6.2 JS 與 WASM 的最小訊息邊界

研究期間只需要概念層，不先凍結 schema：

- `open(documentBytes, options)`
- `renderTile(rect, scale)`
- `pointer(event)`
- `key(event)`／`composition(event)`
- `search(query)`
- `selection()`
- `replaceSelection(text)`
- `save(format)`
- events：`tileInvalidated`、`cursorChanged`、`selectionChanged`、`documentSizeChanged`、`error`

如果為了支援一個 UI 動作，需要把大量任意 UNO 物件直接暴露到 JS，代表邊界可能太寬，產品會重新長成完整辦公套件。

---

## 7. 協作模型：先協作審閱，再協作 model

### 7.1 不要一開始把 ODT 當 CRDT

ODT／DOCX 不是單純字串。一次使用者操作可能改變樣式 run、欄位、註腳、表格、圖片錨點與 layout。把鍵盤事件或 UNO 呼叫直接轉成可交換的 CRDT operation，需要穩定的語意 ID 與衝突規則；目前 LibreOffice 並沒有為 Web 客戶端提供這種保證。

因此，MVP 應把協作分成兩層：

1. **Sidecar 協作資料**：留言、回覆、presence、建議修改，可用一般資料庫或 CRDT。
2. **Office 文件本體**：維持單一權威版本；實際存檔採租約與 compare-and-swap。

### 7.2 建議修改比直接共編更符合需求

一筆「建議替換」可以記錄：

- `baseVersion`
- 被選取的文字 quote
- 前後文 context
- 建議的新文字
- 作者、時間與狀態
- 可選的頁面／座標提示

它不必立即改寫 ODT。文件擁有者可以接受建議，由當下取得 edit lease 的客戶端套用並產生新版本。這種方式：

- 保留審核軌跡。
- 不讓多位瀏覽器同時直接改 Writer model。
- 文件更新後仍能用 quote + context 嘗試重新定位。
- 定位失敗時可要求人工處理，不會靜默改錯位置。

### 7.3 少量直接編輯的安全模型

若要支援直接改幾個字：

1. 客戶端向伺服器取得短效 edit lease。
2. lease 包含 `baseVersion` 與逾時時間。
3. 使用者在本機 WASM model 編輯。
4. 儲存時帶 `If-Match`／base version。
5. 伺服器只在版本仍相符時接受新 blob。
6. 成功後建立不可變的新版本，廣播 `document-updated`。
7. 其他閱讀者選擇重新載入，而不是把二進位 diff 強塞進現有 model。

這不是即時多人共編，但對「閱讀為主、偶爾改字」可能是更可靠的產品設計。

### 7.4 何時才研究真正 multi-writer

至少要先證明：

- 每個內容節點有跨存檔仍穩定的識別方式。
- 文字、樣式、表格與物件操作能形成可重播的語意 operation。
- LibreOffice 能在遠端 operation 插入時維持 cursor 與 undo stack。
- 網路斷線、重連與版本分支有可解釋的合併規則。

在此之前，multi-view API 可以用於渲染多視圖或 QA，但不能直接等同於分散式同步演算法。

### 7.5 上游動態：yrs 留言協作實驗（2026-08-01 補充）

**已觀察**：上游 LibreOffice 26.8 已內建一個實驗性的 yrs（Yjs 的 Rust CRDT，經 yffi C FFI）整合，以 `--with-yrs`／`ENABLE_YRS` 編入；`README.yrs` 在 26.8 與 Collabora co-26.04 engine 逐字相同。範圍：**只同步 Writer 留言**（插入／刪除／內文編輯含格式），文件本體要求唯讀模式，明言超出留言範圍的並行編輯會 crash；transport 目前是 hard-coded pipe。

對本報告的含意：

- 上游自己也選擇「先協作留言、文件本體單一權威」，與 §7.1 的分層判斷一致，是路線的獨立佐證。
- 差異在留言資料的位置：yrs 實驗把留言同步進文件模型（EditDoc 鏡射到 YDocument），本報告提案把留言放 sidecar。兩者可長期收斂，MVP 設計應保留轉換空間。
- §7.4 的「何時研究真 multi-writer」新增一個低成本策略：追蹤上游 yrs 實驗演進，不必自己先養 CRDT。
- 第一版產品與探針不應啟用 `--with-yrs`（多 Rust toolchain 相依與實驗性 crash 面）。

---

## 8. 體積與載入策略

### 8.1 四種不同的「切分」

參考 [libreoffice-wasm-切分策略參考.md](/home/jiajun/Downloads/libreoffice-wasm-切分策略參考.md)，可把問題分成四個維度：

| 維度 | 問題 | 對本研究的價值 |
|---|---|---|
| 時間切分 | 連線與離線時用不同 engine | 中；可借鏡 COWASM，但非第一優先 |
| 資料／程式碼切分 | 字型、locale、gallery 是否必須首載 | **高；可最早實驗** |
| 程式碼熱度切分 | 未走到的函式是否延遲載入 | 高資訊價值；需 PGO 實驗 |
| 運算／狀態切分 | 文件在哪裡算、版本在哪裡存 | **已成為建議架構主軸** |

「功能切分完全做不到」需要更精確地表述：

- 很難把同一份已載入文件的 layout 留在客戶端，卻把依賴同一 model／layout 的任意操作透明 RPC 到伺服器。
- 仍可以在**建置模組、支援格式、UI 資產、語系、字型與產品可操作範圍**上做功能精簡。
- 也可以把整個文件 engine 當作邊界，在 browser WASM 與 server-native LOK 間選擇；只是兩邊的 runtime state 不會天然同步。

### 8.2 先處理 `.data`

Emscripten 的 preload 會把檔案放在獨立 `.data`，並允許分開 host；file packager 也支援多個 datafile。這使下列拆分值得實驗：

```text
core.data             啟動 Writer 必要資料
fonts-fallback.data   跨瀏覽器的最小 fallback 字型
fonts-cjk.data        依語系或文件需求載入
locale-zh-tw.data     zh-TW registry／語言資料
ui-review.data        review UI 真正需要的圖示或資產
legacy-filters.data   舊格式出現時才載入
gallery.data          不載入或延遲
```

「多個 `.data`」本身不會降低完整功能的總體積，但能降低第一次閱讀一份普通 ODT 時的必要下載量。也能讓字型包、語系包擁有較長 cache lifetime，不必隨每次 `soffice.wasm` 更新重新下載。

在動手拆包前，應先用 Emscripten 的讀檔記錄功能蒐集最小閱讀、搜尋、輸入與存檔路徑真正讀過的檔案。只看安裝目錄名稱，容易移除啟動階段隱性依賴。

### 8.3 字型策略與推估

根據目前 `.data` inventory：

- 全部 bundled fonts：約 69.57 MiB raw。
- 全部移除後，`.data` 的 raw 下限約 27.79 MiB；這只是算術下限，不代表無字型可正常啟動或排版。
- 先前以現有封包做的近似壓縮分析顯示，無 bundled fonts 時整體 gzip 首載約可落到 54 MiB 左右。
- 若保留約 3–5 MiB 的 zh-TW／Latin fallback subset，整體 gzip 首載可粗估約 56–58 MiB。

上述 54／56–58 MiB 是研究估值，不是重新連結後的正式產物。字型不是單純裝飾；移除或 subset 會影響：

- CJK glyph 是否存在。
- 字寬與換行。
- DOCX 常見字型替代。
- 頁數與版面 fidelity。
- 不同使用者看到的結果是否一致。

較實際的產品策略是：

1. 永遠帶一份很小、授權清楚、跨瀏覽器一致的 fallback subset。
2. 依文件缺字 callback 或語系按需載入額外字型包。
3. 在支援的瀏覽器上，讓使用者選擇授權存取本機字型。
4. 伺服器保存文件使用的字型清單與缺字警告，但不任意上傳使用者的本機字型。

### 8.4 Qt 6.10.2 的本機字型能力

較短筆記引用 Qt 5 文件，寫成「Qt WASM 拿不到系統字型」。對本次 Qt 6.10.2 原始碼，這已不是絕對限制：

- `qwasmfontdatabase.cpp` 會檢查並呼叫 `window.queryLocalFonts()`。
- 使用 `local-fonts` permission。
- `qtloader.js` 提供 `localFonts.requestPermission`、`familiesCollection` 與 `extraFamilies`。
- 目前產生的 `qt_soffice.html` 沒有主動啟用請求，因此不能假設現有 POC 已使用本機字型。

Local Font Access API 仍有重要限制：

- MDN 將其標示為 Limited availability／experimental，不是所有主流瀏覽器都支援。
- 需要 secure context；正式部署應使用 HTTPS。
- 需要使用者授權，也可能被 Permissions Policy 阻擋。
- 字型清單具有 fingerprinting 風險。
- 本機字型會讓不同使用者的排版結果不完全一致。

結論是：它適合當**可選加速與 fidelity 增強**，不適合成為所有瀏覽器唯一的字型來源。若產品部署環境被限定為受管 Chromium，才可以另外評估「幾乎完全依賴本機字型」。

### 8.5 除錯資訊與 symbols

外部 `.debug.wasm` 可在正式部署排除，不影響正常 runtime。至於 `--disable-symbols`，舊 Qt5 產物顯示：

| 舊 Qt5 案例 | raw wasm | gzip wasm |
|---|---:|---:|
| 帶 symbols 的 t3 | 191,306,566 bytes | 50,901,507 bytes |
| `--disable-symbols` | 130,971,980 bytes | 44,455,000 bytes |

這組歷史比較顯示 symbols 對 raw 體積影響很大，但 gzip 傳輸量只差約 6.15 MiB。它不能直接套用到 Qt6 產物，而且舊的無 symbols 產物曾有執行期問題。正確做法是先保留可診斷 build，再建立相同 source／flags 的 release build 做 A/B 驗證。

### 8.6 `wasm-split`

`wasm-split` 與 Emscripten 的 `MAIN_MODULE`／`SIDE_MODULE` 動態連結不是同一機制。它在完整連結後，把低頻函式分到 secondary module；primary 保留原始 imports／exports，函式第一次被呼叫時再載入 secondary。

這對 LibreOffice 值得做低成本 PGO 實驗，但不宜先承諾收益：

- Writer、VCL、UNO、filters 與共用 libraries 的啟動路徑可能非常廣，primary 仍可能很大。
- 正確 profile 必須涵蓋開檔、渲染、搜尋、中文輸入與存檔；只跑 Start Center 會得到失真的切分。
- 多執行緒程式目前可能在每個 thread 各自 fetch／compile secondary；HTTP cache 可減少下載，但編譯成本仍需量測。
- lazy secondary 不能透明地在 browser main thread 同步載入；官方文件建議 worker／`PROXY_TO_PTHREAD` 類型的執行方式。這與目前為解決 Qt6 emval 問題而採 main-thread 路線存在張力。
- 它主要改善**首載**，不會讓完整使用路徑最後需要的總程式碼消失。

對建議的 LOK Worker 架構，`wasm-split` 反而比目前完整 Qt6 main-thread POC 更契合，因此應在 LOK-WASM POC 成功後再測。

### 8.7 WasmFS 與 lazy file

Emscripten 目前將 WasmFS 描述為 stable 但尚未達到舊 FS 的完整功能；它具備多執行緒設計，可減少舊 JS FS 把檔案操作代理回主執行緒的成本。

`FS.createLazyFile` 則依賴同步 XHR。Emscripten maintainer 明確指出不適合直接搬進 WasmFS，只提到未來可能以 JSPI 類機制處理。因此本研究優先順序應是：

1. 手動多包 `.data`。
2. 記錄實際讀檔路徑。
3. 再評估 WasmFS fetch backend。
4. 不把 `createLazyFile` 當長期產品基礎。

### 8.8 還缺一個關鍵數字：拿掉 Qt 後的 WASM

現在無法負責任地回答「JS UI 取代 Qt 後能降到多少」，因為：

- Qt code、LibreOffice desktop UI code 與 Writer core 都靜態連結在一起。
- linker dead-code elimination 能移除多少，取決於實際入口與 component registration。
- headless UNO build 不等於具備 LOK tile renderer 的 build。

需要建立三個相同 commit、相同 Emscripten、相同格式與字型設定的對照產物：

1. 完整 Qt6-WASM。
2. headless Writer + UNO bridge。
3. headless Writer + 最小 LOK tile bridge。

只有這組比較才能把「拿掉 Qt UI 的收益」從印象變成數據。

---

## 9. 效能、部署與瀏覽器限制

### 9.1 應分開量測的時間

- HTML／JS shell 可互動時間。
- core `.data` 可用時間。
- WASM compile／instantiate 完成時間。
- 第一份文件載入完成時間。
- 第一張可見 tile 出現時間。
- 全部可見 tiles 完成時間。
- 第一次輸入到畫面更新的 latency。
- 儲存並得到新 blob 的時間。
- 冷 cache、HTTP cache、Service Worker cache、WASM code cache 各自結果。

平均值不夠，應至少記錄 p50／p95，以及文件頁數、圖片數、格式與裝置記憶體。

### 9.2 記憶體比下載量更可能成為硬限制

大型 WASM 下載 50–90 MiB 雖然明顯，但瀏覽器還要承擔：

- WASM linear memory。
- 解壓後的 `.data` 與虛擬檔案系統。
- 文件 model、layout 與圖片解碼。
- tile cache 與 canvas backing store。
- 多個 worker／thread stack。

上游 README 的歷史 Qt 設定曾使用 1 GiB `TOTAL_MEMORY`；wasm32 位址空間本身也有限。行動裝置與多分頁環境應早期測試，不應等桌面瀏覽器 POC 完成才處理。

### 9.3 COOP／COEP

若使用 pthreads 與 SharedArrayBuffer，部署通常需要：

```http
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

這會影響：

- 第三方字型、圖片、CDN 與 iframe。
- Nextcloud 或其他宿主應用的嵌入方式。
- OAuth／彈出視窗流程。
- reverse proxy 是否保留正確 headers。

因此「能在本機 HTTP server 跑」不等於「能嵌進 Nextcloud」。整合宿主應是獨立 QA 軸。

### 9.4 預壓縮與快取

正式部署不應每次 request 現場壓縮 195 MiB 的 WASM。應在建置階段產生 gzip／Brotli 版本，使用 immutable、content-hash 檔名與長效快取。後續需補做 `brotli -q 11` 實測；通常 Brotli 對 WASM 可能比 gzip 更好，但本報告沒有先填入未量測數字。

---

## 10. 主要風險與開放問題

| 風險 | 為何重要 | 早期驗證方式 |
|---|---|---|
| LOK-WASM 沒有現成可用 bridge | 架構 B 的根基 | 風險已下修：COWASM co-26.04 是可運作的產品級參考（核外連結、pthreads、MEMFS I/O）；探針改聚焦無 COOL 中間層的裸 LOK 啟動序，見 [COWASM 參考筆記 §9](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md) |
| tiled API 為 unstable | 上游變更可能破壞客戶端 | pin 26.8，包一層窄 adapter，追蹤 headers diff |
| 中文 IME／英文重複輸入 | 已在 Qt6 POC 遇到平台事件問題 | 對 LOK key/ext-text-input 建立組合輸入矩陣 |
| 沒有 DOM text layer | 搜尋、複製、選取、a11y 不會由 canvas 自動得到 | 研究 LOK selection/a11y API 與可見文字 overlay |
| 字型不同造成版面差異 | 審閱座標與頁數可能漂移 | 固定 fallback font pack，比較本機字型開／關 |
| ODT／DOCX round-trip | 少量改字也可能重寫結構 | 建立文件 corpus，XML diff + 視覺 diff + 桌面重開 |
| 版本衝突 | 多人可能從舊版本修改 | edit lease + ETag CAS + 永不靜默覆寫 |
| 記憶體不足 | 下載成功仍可能崩潰 | 大文件與低記憶體裝置的 peak memory 測試 |
| worker／thread 架構衝突 | `wasm-split`、Qt與 JSPI 的限制不同 | LOK POC 單獨選 worker 模式，不沿用 Qt 假設 |
| 桌面 handoff 不順 | 產品定位依賴它 | WebDAV URL、下載檔與 custom protocol 分別研究 |
| 權限與隱私 | 本機字型及文件內容敏感 | permission UX、CSP／Permissions Policy、威脅模型 |

### 10.1 Canvas 閱讀器不只是一張圖

LOK tile 可以解決「看起來像文件」，但產品還需要：

- 文字選取與 clipboard。
- 搜尋結果定位。
- 游標與 selection overlay。
- hyperlink hit testing。
- 螢幕閱讀器可理解的文字與結構。
- 高 DPI 與縮放時的 tile cache 策略。

這些工作可能比畫出第一張 tile 更久。POC 應在第一階段就加入「選取並複製一段中文」，避免最後才發現只有視覺畫面而沒有可用的閱讀介面。

### 10.2 「改幾個字」仍可能觸發完整排版

使用者操作雖小，Writer 仍可能重新斷行、重排後續頁面、更新欄位或索引。因此產品可以限制 UI 功能，但不能假設核心運算成本與字數成正比。這也是讓排版與存檔留在同一 LibreOffice instance 的理由。

---

## 11. 建議研究順序與 Go／No-Go 閘門

### 階段 R0：建立可比較基線

目標：讓體積與效能數據可以重現。

- 固定 LibreOffice commit、Qt／Emscripten 版本與 configure flags。
- 保存 full Qt6 build 的 raw／gzip／Brotli、metadata inventory 與冷熱啟動結果。
- 準備 5–10 份最小文件 corpus：純文字、中文、樣式、表格、圖片、註解、DOCX。

**通過條件**：另一輪建置能得到可解釋的相近結果。

### 階段 R1：LOK-WASM 最小垂直切片

只做：

```text
ArrayBuffer → documentLoad → initializeForRendering
            → paintTile → Canvas
            → click / key / composition
            → save → ArrayBuffer
```

**Go 條件：**

- 可渲染第一張 Writer tile。
- 可定位游標並插入中英文。
- 可保存新 ODT，桌面版重開正常。
- 新產物體積與 peak memory 已量測。

**No-Go／轉向條件：**

- headless build 無法提供可維護的 tile rendering。
- binding 必須暴露大部分不穩定內部物件才能工作。
- 單一小文件在目標瀏覽器就超過可接受記憶體。

若 No-Go，優先轉向原生 server LOK + JS 精簡 UI，而不是立刻重寫排版引擎。

### 階段 R2：閱讀器

- viewport tile scheduling 與 cache。
- 縮放、捲動、頁面定位。
- 搜尋、文字選取、複製。
- 超連結。
- 基本 accessibility spike。
- 大檔與多頁效能。

**通過條件**：它已是一個可日常閱讀的工具，而不只是 canvas demo。

### 階段 R3：Sidecar 審閱協作

- 文件版本與 ETag。
- 留言、回覆、resolve。
- suggestion quote/context anchoring。
- presence 與頁面位置。
- 文件更新通知與重新載入。

這一階段可以在 R1 後與閱讀器部分並行設計，但不需要碰 ODT 內部多人合併。

### 階段 R4：少量直接編輯

- edit lease。
- 短文字插入、刪除、取代。
- 接受 suggestion。
- 新版本儲存、失敗復原、衝突提示。
- 桌面版 handoff。

**通過條件**：衝突時不遺失資料，且使用者知道何時必須回桌面版。

### 階段 R5：輕量化

依序測量，而不是一次砍完：

1. release／symbols A/B。
2. 最小 fallback fonts 與按需 CJK pack。
3. 移除完整 Qt UI 專用 config／icons。
4. Writer-only 與 format filter allowlist。
5. 多 `.data` 包。
6. `wasm-split` PGO。
7. LTO／最佳化旗標。
8. Brotli、HTTP cache 與 Service Worker。

每一步都必須重跑開檔、中文輸入、存檔、桌面重開與 corpus round-trip，否則「體積下降」可能只是「功能悄悄壞掉」。

---

## 12. QA 與 LibreOffice 上游貢獻方向

### 12.1 目前 Qt6-WASM 路徑

可以提交或補強的上游工作包括：

- Qt 6.10／Emscripten 4.0.10 對應的建置文件與版本檢查。
- 已淘汰 embind export symbol 的建置修正。
- split DWARF／`.dwp` 安裝規則。
- JSPI、event loop、main-thread／worker 的可重現測試。
- `invalid emval handle` 診斷與跨執行緒 ownership 問題。
- 中文 composition 與英文重複按鍵的 Bugzilla ticket、最小重現與 regression range。

這些工作即使不直接進入 review-first 產品，也會改善 TDF 公開規劃中的 Qt6-WASM 原型。

### 12.2 LOK-WASM 研究若成功

較適合上游的產出是通用的小單位，而不是直接提交整套產品：

- 一個最小 LOK-WASM Writer tile 範例。
- 輕薄、文件化的 C／Embind adapter。
- `ArrayBuffer` 載入與輸出範例。
- CJK input 與 selection 測試。
- `.data` 檔案使用追蹤與體積報表腳本。
- Writer-only component／filter 清單的可重現配置。
- tiled rendering API 在 wasm32 上的 QA。

### 12.3 建議測試矩陣

| 軸 | 最小集合 |
|---|---|
| 瀏覽器 | Chromium 穩定版、Firefox；Safari 視 pthread/local font 能力另列 |
| 輸入 | 英文實體鍵盤、注音／倉頡／拼音 composition、貼上、emoji |
| 文件 | ODT、DOCX；純文字、樣式、表格、圖片、註解、修訂 |
| 字型 | bundled fallback、本機字型授權、拒絕授權、缺字 |
| 網路 | 冷 cache、熱 cache、慢速、斷線、更新中途失敗 |
| 協作 | 唯讀多人、同時 suggestion、lease 過期、版本衝突 |
| 裝置 | 桌面高記憶體、低記憶體筆電、行動裝置 |

---

## 13. 建議的近期研究問題

以下問題目前比撰寫正式 spec 更重要：

1. 26.8 的 headless WASM 產物中，哪些 LOK tile symbols／components 實際存在？
2. 最小 binding 應使用穩定 C API、C++ wrapper，還是 Embind + UNO？
3. 文件是否能直接由記憶體載入，或必須先寫入 Emscripten FS？
4. `saveAs` 如何安全輸出到 JS `ArrayBuffer`，且不殘留暫存檔？
5. Writer tile rendering 的最低 component set 是什麼？
6. 不載入完整 Qt UI config 時，哪些 registry／resource 仍是 VCL headless 必需？
7. 中文組合輸入要用 LOK `postKeyEvent`、extended text input，還是窄 UNO operation？
8. LOK 提供的文字 selection／a11y 資料，能否建立 DOM overlay？
9. 不同字型策略下，頁數與 selection anchor 漂移到什麼程度？
10. `wasm-split` 在「開檔、閱讀、搜尋、改字、存檔」profile 後，primary 實際剩多少？
11. 多 `.data` 包能否在 LO global initialization 前可靠掛載？
12. 一份 100 頁含圖片 DOCX 的 peak memory 與首次可見時間是多少？
13. Nextcloud iframe／WebDAV／COOP-COEP 能否共存？
14. 桌面版 handoff 應以下載、WebDAV URL、瀏覽器 protocol handler 還是 Nextcloud integration 完成？

**2026-08-01 註**：問題 2 與 3 已有參考答案——（2）採穩定 C API + 自建窄 shim，不以 Embind + UNO 為預設（COKit 分岔佐證 LOK 不可直接依賴，embind 在核外連結可省略）；（3）COWASM 一律經 MEMFS（fetch → FS → `file://` URL → documentLoad；save 反向），探針第一版照走，不先發明記憶體直通 API。其餘問題維持開放。

---

## 14. 暫時結論

### 14.1 產品判斷

這個方向值得繼續，而且需求邊界比「做另一個 Collabora Online」健康得多。閱讀與 review-first 讓協作價值可以先成立，而不必先解掉完整多人 Writer model 合併。

### 14.2 技術判斷

- 完整 Qt6-WASM 已是有價值的 QA 基線，但不應直接等同最終產品 UI。
- JavaScript UI 有機會取代 Qt desktop UI，卻不會取代 LibreOffice 文件核心。
- LOK WASM + JS 最符合需求，但必須先證明 tile/input/save 垂直切片。
- 協作先採 sidecar + 單一權威文件版本 + edit lease，避免第一版挑戰 ODT CRDT。
- 體積優化先從字型與 `.data` inventory 開始，再做相同條件的 headless／LOK artifact 比較。
- 多 `.data` 與 `wasm-split` 的主要價值是降低首載，不是讓完整總體積憑空消失。
- 本機字型可在部分 Qt6／Chromium 環境使用，但仍需小型跨瀏覽器 fallback。

### 14.3 下一個最小決策

下一個值得投入的開發工作不是協作後端，也不是 UI mockup，而是：

> **建立一個 Writer-only、無完整 Qt UI 的 LOK-WASM 技術探針，完成 `open → paintTile → input → save`。**

這個探針會回答架構、體積、輸入、存檔與 Worker 邊界五個核心問題。成功後再進入閱讀器研究；失敗則可及早轉向 server-native LOK + 精簡 JS UI。

---

## 15. 量測重現方式

以下命令均為唯讀量測；路徑以本研究工作區為準。

### 15.1 Raw size

```bash
stat -c '%n %s bytes' \
  wasm-lite/build-qt6-poc/instdir/program/soffice.js \
  wasm-lite/build-qt6-poc/instdir/program/soffice.wasm \
  wasm-lite/build-qt6-poc/instdir/program/soffice.data \
  wasm-lite/build-qt6-poc/instdir/program/soffice.wasm.debug.wasm
```

### 15.2 Gzip size

```bash
gzip -9 -c wasm-lite/build-qt6-poc/instdir/program/soffice.wasm | wc -c
gzip -9 -c wasm-lite/build-qt6-poc/instdir/program/soffice.data | wc -c
gzip -9 -c wasm-lite/build-qt6-poc/instdir/program/soffice.js | wc -c
```

### 15.3 `.data` 檔案清單

```bash
jq -r \
  '.files[] | [.filename, (.end-.start)] | @tsv' \
  wasm-lite/build-qt6-poc/instdir/program/soffice.data.js.metadata \
  | sort -k2,2nr
```

---

## 16. 資料來源

### 16.1 本機資料

- [DEVLOG-2026-07-31-wasm.md](../devlog/DEVLOG-2026-07-31-wasm.md)
- [DEVLOG-2026-08-01-qt6-wasm.md](../devlog/DEVLOG-2026-08-01-qt6-wasm.md)
- [litecore-analysis.md](../litecore-analysis.md)
- [COWASM co-26.04 參考研究筆記](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)
- [worktree patch inventory](../wasm-lite/patches/INVENTORY.md)
- [LibreOffice WASM 切分策略參考](/home/jiajun/Downloads/libreoffice-wasm-切分策略參考.md)
- [LibreOffice upstream `static/README.wasm.md`](../libreoffice-26-8/static/README.wasm.md)
- [LibreOfficeKit C API](../libreoffice-26-8/include/LibreOfficeKit/LibreOfficeKit.h)
- [LibreOfficeKit callbacks／events](../libreoffice-26-8/include/LibreOfficeKit/LibreOfficeKitEnums.h)
- [Qt 6.10.2 WASM font database](../wasm-lite/tools/qtbase-everywhere-src-6.10.2/src/plugins/platforms/wasm/qwasmfontdatabase.cpp)
- [Qt 6.10.2 loader 設定](../wasm-lite/tools/qtbase-everywhere-src-6.10.2/src/plugins/platforms/wasm/qtloader.js)

### 16.2 LibreOffice／TDF／Collabora

- TDF, [Web and Mobile Development Strategy Proposal](https://blog.documentfoundation.org/blog/2026/05/30/web-and-mobile-development-strategy-proposal/), 2026-05-30.
- TDF, [New Web and Mobile Strategy for LibreOffice](https://blog.documentfoundation.org/blog/2026/05/27/new-web-and-mobile-strategy-for-libreoffice/), 2026-05-27.
- LibreOffice, [LibreOfficeKit documentation](https://docs.libreoffice.org/libreofficekit.html).
- LibreOffice core, [`static/README.wasm.md`](https://github.com/LibreOffice/core/blob/master/static/README.wasm.md).
- Collabora Online, [source repository](https://github.com/CollaboraOnline/online)；包含現行 `wasm/` 與 WASM deployment 設定。
- Tor Lillqvist, [Collabora Online and WASM](https://mautic.collaboraoffice.com/asset/213:fosdem23-tor-lillqwist-cool-wasmpdf), FOSDEM 2023.
- allotropia, [LibreOffice, JavaScript'ed](https://blog.allotropia.de/2024/04/30/libreoffice-javascripted/), 2024-04-30.
- allotropia, [ZetaJS repository](https://github.com/allotropia/zetajs).

### 16.3 Emscripten／WebAssembly

- Emscripten, [Packaging Files](https://emscripten.org/docs/porting/files/packaging_files.html).
- Emscripten, [Module Splitting](https://emscripten.org/docs/optimizing/Module-Splitting.html).
- Emscripten, [File System API／WasmFS](https://emscripten.org/docs/api_reference/Filesystem-API.html).
- Emscripten issue, [`FS.createLazyFile` in WasmFS?](https://github.com/emscripten-core/emscripten/issues/19608).
- Web Almanac 2025, [WebAssembly](https://almanac.httparchive.org/en/2025/webassembly).

### 16.4 字型與瀏覽器能力

- Chrome for Developers, [Use advanced typography with local fonts](https://developer.chrome.com/docs/capabilities/web-apis/local-fonts).
- MDN, [`Window.queryLocalFonts()`](https://developer.mozilla.org/en-US/docs/Web/API/Window/queryLocalFonts).
- WICG, [Local Font Access draft](https://wicg.github.io/local-font-access/).

---

## 17. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-01 | 初版。整合 Qt6-WASM 實測、LOK/UNO 架構、review-first 協作模型、體積量測，以及資料分包、`wasm-split`、運算／狀態切分研究。 |
| 2026-08-01 | 補入 COWASM co-26.04 對照（§4.2、§10、§13）與上游 yrs 留言協作動態（§7.5）；LOK-WASM bridge 風險下修。 |

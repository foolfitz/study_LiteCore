# SPEC R6+：R5 之後的實驗路線圖

> **日期**：2026-08-02  
> **狀態**：規劃基線（R6 GO；R7部分GO；R8 local-delivery部分GO；E1 `E1_GO_ODT_EDITOR`；
> E2進行中；E3／E4規格已立、未授權執行；R9未啟動；R10方法規格已立、前置條件未成立不可啟動）  
> **依據**：[R5 GO](./SPEC-R5-000-overview.md)、[R6](./SPEC-R6-000-overview.md)

## 1. 文件定位

這份文件回答「R5 完成後，哪些未知數值得依什麼順序處理」。它不是一次授權執行全部工作，也不凍結
R7 以後的 API／產品範圍。每個里程碑都要依前一輪 evidence 另寫可執行 spec，再取得執行確認。

2026-08-04 更新：R7 已依[`SPEC-R7-000`](./SPEC-R7-000-overview.md)判定ODT-first部分GO；R8已建立
[`SPEC-R8-000`](./SPEC-R8-000-overview.md)與A～D子規格；R8已判定`PARTIAL_GO_LOCAL_DELIVERY`並結案。
2026-08-05後續更新：E1-A縮限能力後完成，E1-B窄版產品contract判定`GO_TO_E1_C`，E1-C完成後E1判定
`E1_GO_ODT_EDITOR`。其後建立E2（段落層級格式）與E3（讀取完整性）；E2-A的A2先決條件已完成，A2-wasm與
A3～A7未執行，E2-A尚無判定。同日稍後建立[E3-000](./SPEC-E3-000-overview.md)、
[E4-000](./SPEC-E4-000-overview.md)與[R10-000](./SPEC-R10-000-overview.md)三份規格，均未授權執行。

**R9至今無規格檔**，維持需求驅動backlog。R10已立方法規格（[SPEC R10-000](./SPEC-R10-000-overview.md)，
只定義方法與閘門，不列裁切目標）；因E2／E3／E4會改變功能corpus，前置條件仍不成立、不可啟動，
見第8節與第10節。

規劃原則：

- 先證明使用者工作流，再為真實工作流做相容性與部署；
- 先建立 corpus／reachability 證據，再裁切 LibreOffice core 或資源；
- 受控 Automation 是獨立產品能力，不混入協作 UI；
- 每輪只解一組主要未知數，避免功能、體積、部署與安全同時變動而無法歸因；
- No-Go 是有效實驗結果，必須留下可重現證據與替代路徑。

## 2. 建議路線

```text
R1–R5 SDK／Provider／profile 已成立
                │
                ▼
R6 協作 reference application
                │
                ▼
R7 真實輸入、文件相容與可用性 corpus
                │
        ┌───────┴────────┐
        ▼                ▼
R8 正式載入／復原      R9 受控 Automation（獨立候選線）
        │
        ▼
E1 ODT-first 基本編輯器（完成，GO）
        │
        ▼
E2 段落層級格式（清單、標題）
        │
   ┌────┴─────┐
   ▼          ▼
E3 讀取完整性  E4 Markdown 讀寫
（DOCX 為     （順位高於 E3
  低順位選項）   的 DOCX）
   └────┬─────┘
        ▼   ← 功能 corpus 與 reachability 需求要到這裡才真正凍結
R10 以 corpus／reachability 為證據的深層減量
```

R9 不阻擋 review-first 產品線；若沒有具體企業 automation 使用情境，可以持續留在 backlog。

**E2／E3／E4 都必須排在 R10 之前。** 原本的規劃是 E1 完成即可凍結功能 corpus 並進 R10，但 E2 會新增清單
與段落樣式、E4 會啟用 markdown 濾鏡、E3 若承諾 DOCX 會啟用整套 Word 匯入路徑；三者都會擴大「哪些 core
程式碼與資源不可移除」的集合。先裁切再補能力，等於保證要重編一次 corpus 與 A/B artifact。

E3 與 E4 無技術相依，順序依產品優先度決定。目前的產品順位是 **E4 的 markdown 高於 E3 的 DOCX**。

## 3. R6：協作 reference application（完成，GO）

核心問題：現有 Document／Provider SDK 能否支撐安全的雙 client review-first 工作流？

範圍：reader shell、sidecar comment／suggestion、presence、短效 lease、ETag compare-and-swap、遠端更新
reload、Provider suggestion 與桌面 round-trip。

主要不確定性：

- viewport tile／search geometry 是否已有足夠穩定的公開資料；
- quote/context 在沒有跨版本 range ID 時能安全做到哪個程度；
- event replay、snapshot fallback 與 Worker lifecycle 是否能維持一致 UI 狀態。

決策文件：[SPEC R6-000](./SPEC-R6-000-overview.md)。

## 4. R7：真實輸入、文件相容與可用性（完成，ODT-first部分GO）

只有 R6 證明完整工作流成立後才展開。R7 應將 probe fixture 擴成產品風險 corpus：

- 真 IME composition：注音／倉頡／拼音、全形標點、emoji、surrogate pair、composition cancel。
- clipboard：複製、純文字貼上與權限拒絕；不以 generic HTML／UNO paste 擴大 surface。
- ODT／DOCX：多頁、樣式、表格、圖片、註解、修訂、缺字型、損壞或不支援文件。
- viewer usability：超連結、頁面定位、基本鍵盤操作與 accessibility spike。
- 大檔與長時間：100 頁含圖片文件、重複 open／render／close、Worker crash／restart、記憶體 high-water。
- 多文件需求只先量化；除非有清楚使用情境，不直接改成同 Worker 多文件。

預期閘門：目標 corpus 的內容與版面差異可解釋、IME 不重複／漏字、失敗文件有 typed error、長時間測試
不呈現無界成長。若 DOCX round-trip 不可接受，產品可明確縮回 ODT-first，而不是隱藏限制。

## 5. R8：正式載入、更新與復原（完成，local-delivery部分GO）

R5 只證明 loopback cache contract；R8 才處理接近 production 的 delivery：

- 依 locale、fidelity policy 與可取得的 document font inventory 決定 fallback pack；需要重啟 engine 時
  提供明確狀態與可取消流程。
- 預壓縮 gzip／Brotli、content type、COOP／COEP、CORS 與 immutable hash artifact。
- Service Worker install／activate、manifest 更新、舊版 cache eviction 與 rollback；禁止 JS／WASM／data
  混版。
- 慢網、斷線、部分下載、hash mismatch、storage quota 與更新中途關頁的復原。
- 評估 range request 是否真的改善目前 artifact；沒有量測證據就不增加複雜度。
- 在實際 HTTP 環境量 cold／warm network、WASM compile、resource mount、engine ready 與 first tile。

預期閘門：全新安裝、熱快取、版本升級、離線／中斷與 rollback 都不會啟動混版 runtime；fallback 字型
政策不造成靜默版面降級。CDN 數據需標示實際拓樸，不沿用 loopback 數字。

執行規格：[SPEC R8-000](./SPEC-R8-000-overview.md)，順序為R8-A delivery discovery → R8-B versioned
artifact delivery → R8-C offline/update/rollback → R8-D production-shaped validation。R8-A已凍結closed release
graph、T0/T1與bytes/hash完整性契約；R8-B direct delivery已完成166 browser cases與8份desktop roundtrip，
安全gate全通過。R8-C的atomic update／offline／rollback與R8-D的Chrome 28份active-cache corpus、30分鐘soak、
R6/R7回歸也已完成；Firefox Finding 014 combined-run、T2 HTTPS/CDN、真quota與顯式reload保留為正式缺口。
最終判定`PARTIAL_GO_LOCAL_DELIVERY`，下一步可為ODT-first基本編輯器建立正式編號與discovery spec。

## 6. E1：ODT-first基本編輯器（完成，`E1_GO_ODT_EDITOR`）

R1～R8的產品主線是review-first；現有`click()`、`insertText()`、selection replace、Undo、comment、redline與
ODT save只能形成受控窄修改，不等於一般authoring editor。此能力沒有混入R8 delivery；R8結案後已正式編為
E1，先做caret／selection／keyboard／delete／newline／Redo與最低格式的discovery，再決定窄ABI。

候選最小範圍：

- 公開caret／selection模型及座標、revision與跨render穩定性discovery；
- click／方向鍵／Home／End、滑鼠拖曳選取、backspace／delete、Enter／換行與exactly-once mutation；
- Undo／Redo與stale／Worker recovery後的local edit邊界；
- 最低限度粗體、斜體、段落／heading與list closed operations，不提供任意UNO command；
- IME／clipboard沿用R7 host-owned state machine，另驗證caret移動與composition的交互；
- ODT save、desktop round-trip、accessibility limitation與Chrome／Firefox鍵盤矩陣。

停止邊界：若基本操作只能靠raw UNO、unoembind、任意`.uno:*`或解析未承諾callback，建立finding並縮小產品
能力，不用DOM／canvas假caret掩蓋SDK缺口。

這個里程碑必須在R10深層裁切前完成或至少凍結功能corpus與reachability需求，避免R10移除authoring依賴。

規格入口：[SPEC E1-000](./SPEC-E1-000-overview.md)。[E1-A](./SPEC-E1-A-editing-discovery.md)曾因forward delete
completion缺口停止；Finding 017修正selection readback，Finding 016的verified-selection barrier再經兩browser與
desktop round-trip解除阻斷。A最終縮限line navigation、Redo、drag／handles、paragraph/list與structural boundary
editing，判定`PARTIAL_GO_TO_E1_B`。

[E1-B](./SPEC-E1-B-narrow-editor-contract.md)已將成立能力凍結為八個產品action與typed state，完成Chrome／Firefox
shell及ODT round-trip並判定`GO_TO_E1_C`。[E1-C](./SPEC-E1-C-editor-validation.md)已規劃E1-B×R7 input／clipboard、
五份ODT、recovery、bounded lifecycle及每browser最多一次headed Chewing delta；尚未授權實作。E1仍不以legacy
raw key、任意state callback、sleep或自動retry作產品contract。

## 6.1 E2：段落層級格式與精簡編輯器補完（A2完成／部分通過，尚無判定）

E1交付的八個action全是inline或字元層級。產品目標「編輯功能精簡、讀取完整」還缺清單、標題與基本導覽。
E2只處理編輯側；讀取完整性（DOCX與其他格式）另編E3，兩者無技術相依，順序可調換。

規格入口：[SPEC E2-000](./SPEC-E2-000-overview.md)、
[E2-A](./SPEC-E2-A-paragraph-format-discovery.md)。

A2原生state-readback已完成並推翻E2-A v1前提：這些命令多半有回UNO command result，真正的缺陷是我方把段落
樣式映射到不存在的UI別名（[finding 019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)），以及
command result的`success`／`wasModified`與文件矛盾
（[finding 020](../findings/020-lok-list-command-result-contradicts-document.md)）。barrier因此改為
command result（歸屬）＋state（真值）雙條件。

A2-wasm已於2026-08-05完成並**部分通過**：三個payload在Chrome 150與Firefox 153都會抵達，派送後的
state與存檔ODT逐項相符（5/5），`crosstalkCount`／`earlyStateCount`皆為0，finding 020在WASM完整重現
（不是Emscripten特有）。但state**不隨caret移動更新**，barrier的前置條件會讀到別段的值，可能產生
靜默no-op，記為[finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)。

該finding的三步歸因已於同日完成：同commit原生四種移動方法（含WASM逐字序列）全部正常；WASM失敗
位置的watched payload抵達數為0（排除我方解析失敗）；而在隔離profile中推進一次VCL scheduler後，
四個位置的狀態全部正確且與原生一致。**結論是我方engine迴圈從不推進scheduler，非上游問題** ——
LOK的status update是idle job，原生由VCL主迴圈推動，我方探針核外連結、自帶命令迴圈則無人推進。
修法方向因此改為讓狀態可靠而非繞開它，但正規推進機制未定（`unit_lok_process_events_to_idle()`
是unit-test掛鉤，不得作為產品機制）。**A3仍不啟動。** A3～A7未執行，E2-A尚無判定。

## 6.2 E3 候選：讀取完整性（規格已立，未授權執行）

產品目標的另一半是「開檔案要完整」。目前ODT 28份corpus已跨瀏覽器與desktop fidelity通過。E3處理其餘的
讀取缺口，例如更多ODT邊界情形、document-content accessibility，以及公開`open()`的格式辨識邊界。

**DOCX在本實驗中是低順位選項，不是E3的主體。**（2026-08-05 產品決定）目前DOCX依
[finding 013](../findings/013-sdk-open-name-rejects-docx-before-content-detection.md)明確unsupported：
公開`open()`在content detection前就以副檔名拒絕`.docx`，而相同bytes配`.odt`名稱可完整讀取。最小安全修法
已在該finding框定 —— 改成allowlisted `format`列舉，讓驗證、實際MEMFS path與manifest capability三者一致，
不公開任意path或raw filter名稱。真正昂貴的是後續：要用R7-C那套逐檔corpus對DOCX重跑open／render／search／
ODT save／desktop round-trip與fidelity分類。在有明確需求前不啟動這一段。

E3規格已於2026-08-05建立（[SPEC E3-000](./SPEC-E3-000-overview.md)：三條主線為ODT邊界情形、
document-content accessibility與公開`open()`格式辨識邊界；DOCX獨立成低順位節，有明確需求才啟動；
corpus沿用R7-C 28份不重生）；未取得執行授權。

## 6.3 E4 候選：Markdown 讀寫（規格已立，未授權執行）

順位高於E3的DOCX選項。理由是成本可能低一個量級：**LibreOffice 26.8 已內建Writer的Markdown濾鏡，而且是
雙向的**，不需要自己寫parser。

### 已觀察（原始碼層級，2026-08-05）

- `filter/source/config/fragments/filters/Markdown.xcu`：flags為`IMPORT EXPORT ALIEN`，
  `DocumentService`為`com.sun.star.text.TextDocument`，`UserData`為`Markdown`。
- `filter/source/config/fragments/types/generic_Markdown.xcu`：副檔名`md markdown`，media type
  `text/markdown`，偵測走`PlainTextFilterDetect`。
- 兩者都列在`filter/Configuration_filter.mk`（generic_Markdown、Markdown）。
- 實作在`sw/source/filter/md/`：`swmd.cxx`（讀）、`wrtmd.cxx`（寫），另有`mdnum`、`mdtab`、`mdcallbcks`。
- reader已在`sw/source/filter/basflt/fltini.cxx:101`註冊為`ReadMarkdown`，並對應`READER_WRITER_MD`。
- 剪貼簿另有`SotClipboardFormatId::MARKDOWN`，`sw/qa/filter/md/md.cxx`有貼上markdown的測試。

### 待驗證

- 這個濾鏡在本專案的WASM profile是否**實際被連結進來且可用**。完全未測；`filter`註冊存在不等於WASM
  build裡reachable。
- 若可用，`save({format:"md"})`與`open()`的markdown偵測要以什麼closed surface公開，不得暴露raw filter名稱。
- Markdown是有損格式。ODT→MD→ODT不是round-trip，必須明確定義哪些內容會被丟棄，不能靜默降級。

E4規格已於2026-08-05建立（[SPEC E4-000](./SPEC-E4-000-overview.md)：第一道閘門G0即為上列
「待驗證」第一項的WASM reachability，靜態inventory→native對照→WASM probe三步、不通過即停止；
另定義native損耗矩陣與不靜默降級的產品契約）；未取得執行授權。與E2／E3無技術相依。

## 7. R9 候選：受控 Automation profile（未啟動，無規格檔）

只有出現明確、可測的企業 automation 使用情境時才寫正式 spec。最低前提：

- 每項 operation 有名稱、schema、版本、capability、權限與資源上限；
- allowlist 是 closed taxonomy，不接受任意 `.uno:*`、UNO object graph、macro 或 unoembind；
- dry-run／validate、revision guard、transaction／undo、timeout／cancel 與 audit event 有定義；
- document scope、Provider／automation isolation 與 hostile input corpus 可測；
- `writer-automation` profile 的 exports、artifact 與錯誤語意可由 machine validator 證明。

第一個候選應是單一窄操作，例如依 schema 取代固定 selection 或讀取受控 document metadata；不要以
「執行任意 command」當作 MVP。

預期閘門：automation client 無法取得通用 document internals，超出權限與 stale request 零 mutation，
且同一 fixture 在 Web／desktop adapter 語意一致。未達成前維持 R5 的 `not-shippable`。

## 8. R10 候選：深層 code／resource 減量（**前置條件未滿足，尚不可啟動**）

2026-08-05：方法、進場閘門（含基線可重建閘門）、每個裁切單位的證據要求與停止條件已定義於
[SPEC R10-000](./SPEC-R10-000-overview.md)；該規格**不列裁切目標**，也不構成啟動授權。具體目標
待E2／E3／E4定案後逐單位另立R10子規格。

### 8.1 前置條件

R10 唯一的輸入是「產品確定會用到什麼」。這份清單目前**還在變動中**：

| 前置 | 狀態 | 對 R10 的影響 |
|---|---|---|
| R7 功能 corpus | 已凍結 | 可用 |
| R8 delivery contract | 已完成（`PARTIAL_GO_LOCAL_DELIVERY`） | 可用；缺 T2 不影響裁切 |
| E1 編輯能力 | 已完成（`E1_GO_ODT_EDITOR`） | 可用 |
| **E2 段落層級格式** | **進行中** | 會新增清單／編號與段落樣式的 core 相依，這些不可移除 |
| **E3 讀取完整性** | **尚未建立規格** | 若承諾 DOCX（低順位），整套 Word 匯入 filter 不可移除 |
| **E4 Markdown 讀寫** | **尚未建立規格** | 若承諾 markdown，`sw/source/filter/md/` 與 Markdown filter 註冊不可移除 |

先裁切再補能力，等於保證要重編一次 corpus、重跑一次 A/B artifact 與 round-trip。**R10 必須等 E2、E3 與 E4
的能力範圍定案。**

### 8.2 內容

R5 已完成安全的 product flags 與字型分包；下一個顯著 WASM 降幅不能再靠縮 exports。R10 的輸入必須是
R7／R8／E1～E3 的實際功能 corpus與 link evidence：

- filter allowlist：先固定 ODT／目標 DOCX corpus與 round-trip，再 A/B component／filter 移除。
- UI／config／gallery／sample 資源：逐類建立 access inventory、缺檔負向測試與替代策略。
- core libraries：使用 link map、symbol reachability、size attribution 與功能 trace，不依 library 名稱猜測。
- scripting：在 macro／script 明確不支援的產品 policy 下 A/B；確認啟動與 filter side effect。
- LTO、`wasm-split`／PGO 或其他工具鏈最佳化：固定工具版本並驗證 browser compile／runtime memory，
  不只量 raw bytes。
- bit reproducibility：區分 deterministic content、artifact hash 更新機制與真正 bit-reproducible build；
  不把三者混為一談。

每一個裁切單位都需獨立 inventory、A/B artifact、功能 corpus、桌面 round-trip 與 rollback。若只能靠修改
大量 LibreOffice core 且維護成本高於下載收益，應保留 R5 profile 並停止該方向。

## 9. 每輪共同的實驗交付

未來每個里程碑至少要有：

1. `specs/SPEC-RN-000-overview.md`：目標、範圍、非範圍、驗收、Go／部分 Go／停止條件。
2. `DEVLOG-<日期>-wasm-sdk-rN.md`：包含失敗嘗試、限制與決策，不只寫成功摘要。
3. `findings/evidence/sdk-rN/summary.json`：機器可讀閘門與 artifact／環境識別。
4. 原始 browser、network、round-trip、memory 或 build evidence。
5. 遇到可重現的重要發現／阻礙立即建立 finding；上游問題與我方規格問題分開標示。
6. R1～前一輪回歸與 `libreoffice-26-8` 工作區完整性證據。

## 10. 排程決策規則

- R7 corpus 是 R10 深層裁切的必要依賴；不得顛倒順序。
- R8已完成並形成local delivery contract；若未來取得T2環境，只補deployment evidence，不重做已通過的T0/T1。
  R8的六項formal gap（T2 HTTPS/CDN、真quota、顯式reload、Firefox combined-run等）不阻擋E2／E3／R10，
  可在取得部署環境後單獨補齊。
- **R10不得在E2、E3與E4的能力範圍定案前啟動。** E1完成曾一度使功能corpus看似可凍結，但E2新增清單／段落
  樣式、E4可能承諾markdown、E3可能承諾DOCX，三者都會擴大不可移除集合。此規則優先於「E1完成即可進R10」
  的舊敘述。
- E2、E3與E4彼此無技術相依，順序依產品優先度決定；但都必須在R10之前。
- **DOCX在本實驗是低順位**（2026-08-05產品決定），順位低於E4的markdown讀寫。不得因finding 013已框定修法
  就自動排入主線。
- R9 由需求驅動，不因 profile 名稱已存在就自動排入主線；它與E2／E3／E4／R10互不阻擋。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | 初版。R6 定為下一個可執行里程碑；R7～R10 保留為 evidence-driven 候選。 |
| 2026-08-02 | R6 完成並判定 GO；R7 成為下一個待另立 spec／授權的候選。 |
| 2026-08-04 | R7完成並判定ODT-first部分GO；R8維持候選，未自動取得執行授權。 |
| 2026-08-04 | 建立R8 overview與A～D執行規格；基本編輯器延後至R8後並列為R10前置能力閘門。 |
| 2026-08-04 | R8-A完成並判定PARTIAL GO；closed release graph與Chrome／Firefox T0/T1契約通過，下一步R8-B。 |
| 2026-08-04 | R8-B完成並判定PARTIAL GO；versioned direct delivery與防混版成立，下一步R8-C。 |
| 2026-08-04 | R8-C／D完成；local safety gate全通過，因缺T2與Firefox Finding 014缺口，R8判定PARTIAL_GO_LOCAL_DELIVERY。 |
| 2026-08-04 | ODT-first基本編輯器正式編為E1；建立overview、E1-A discovery與凍結matrix，R9／R10編號維持。 |
| 2026-08-04 | E1-A完成並因Finding 016判定STOP_OR_RESCOPE；E1-B／C不啟動，待上游ack或安全縮範圍決策。 |
| 2026-08-05 | Finding 017 SDK readback已修；Finding 016經原生對照改判為我方缺LOK主迴圈，E1下一步改為最小scheduler驗證。 |
| 2026-08-05 | Finding 016最小scheduler實驗否證主迴圈缺口；E1下一步改為closed typed completion barrier評估。 |
| 2026-08-05 | Finding 016解除阻斷、E1-A縮限通過、E1-B判定GO_TO_E1_C；建立E1-C產品驗證規劃與凍結矩陣。 |
| 2026-08-05 | E1-C完成，E1判定`E1_GO_ODT_EDITOR`。 |
| 2026-08-05 | 建立E2（段落層級補完）與E3（讀取完整性）編號；E2-A A2-native完成並建立finding 019／020，E2-A尚無判定。 |
| 2026-08-05 | 修正排程：R10前置條件加入E2與E3，路線圖改為E1→E2→E3→R10；R10標為前置條件未滿足、尚不可啟動。R9維持需求驅動。 |
| 2026-08-05 | 產品決定：DOCX降為E3的低順位選項；新增E4 Markdown讀寫並記錄26.8內建雙向Markdown濾鏡的原始碼證據。E3與E4並列於E2之後、R10之前。 |
| 2026-08-05 | 建立E3-000（讀取完整性）、E4-000（Markdown讀寫）與R10-000（只寫方法與閘門，不列裁切目標）三份規格；均未授權執行，R10維持不可啟動。 |
| 2026-08-05 | E2-A A2-wasm完成並部分通過：payload抵達、後置條件與歸屬成立、finding 020跨平台重現；state不追隨caret（finding 021），A3暫不啟動。E2-A仍無判定。 |
| 2026-08-05 | finding 021三步歸因完成：原生四種移動方法皆正常、失敗位置watched payload抵達數為0、推進scheduler後狀態正確。改判為我方engine迴圈未推進VCL scheduler，非上游；上游候選分類撤回。 |

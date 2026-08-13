# SPEC R10-000：深層 code／resource 減量——方法與閘門

> **日期**：2026-08-05  
> **狀態**：方法定義；**前置條件未成立，不可啟動**；本規格不列任何裁切目標  
> **依據**：[R6+ roadmap 第 8、10 節](./SPEC-R6+-roadmap.md)、[SPEC R5-000](./SPEC-R5-000-overview.md)

## 1. 文件定位

R10 唯一的輸入是「產品確定會用到什麼」。這份清單要到 E2、E3、E4 的能力範圍定案才會凍結，而
目前 E2 進行中、E3／E4 規格剛立且未授權執行——**前置條件不成立**。

因此本規格只定義四件事：**方法、進場閘門、每個裁切單位的證據要求、停止條件**。任何具體裁切
目標——哪個 filter、哪個 library、哪類資源——都不在本文件內；列目標的部分明確**待 E2／E3／E4
定案後另立子規格**（R10-A 起，逐份獨立取得執行授權）。在那之前，本文件的存在不構成任何裁切
授權，也不得被引用為「R10 已啟動」的依據。

寫下方法而不寫目標的理由：方法不依賴 E2～E4 的結果，現在凍結可以防止未來在體積壓力下臨場
放寬證據標準；目標依賴 E2～E4 的結果，現在寫就是猜——E2-A v1 已示範過猜測的前提會整份垮掉。

## 2. 進場閘門（P1～P5 全部成立，才可立第一份 R10 子規格）

| 閘門 | 要求 | 現況（2026-08-05） |
|---|---|---|
| P1 | E2 判定完成，段落層級能力範圍凍結 | **未成立**（E2-A 尚無判定） |
| P2 | E3 判定完成，讀取能力與 unsupported 邊界凍結 | **未成立**（規格剛立，未授權） |
| P3 | E4 判定完成，markdown 濾鏡去留凍結 | **未成立**（規格剛立，未授權） |
| P4 | 功能 corpus 聯集凍結：R7-C corpus 加 E2／E3／E4 追加 fixture 合併為單一版本化 manifest | 未成立（依賴 P1～P3） |
| P5 | 基線 build 可重建：R10 依賴 A/B 建置，進場前所有作為 baseline 的 profile 必須能從現有 source 重建出與凍結 hash 一致的 artifact | **未成立**——已觀察：R5 `writer-review` 目前無法從現有 source 重建（`SelectionReadback` 的 `#ifdef` 範圍與 boost include 兩個既存問題，見 [E2 DEVLOG](../devlog/DEVLOG-2026-08-05-wasm-sdk-e2.md) 與 [SPEC E2-A 第 10.3 節](./SPEC-E2-A-paragraph-format-discovery.md)） |

P1～P3 的「定案」指該里程碑留下正式判定（GO／部分 GO／停止都算）；停止也是定案——例如 E4
判 `STOP_OR_RESCOPE`，則 markdown 濾鏡確定不在不可移除集合內，這對 R10 是可用的輸入。

P5 是本規格新增的閘門，理由：A/B 的 before 端如果建不出來，任何 after 端的差異都無法歸因。
修復 P5 屬既有 finding 017 遺留問題的收尾，不是 R10 工作。

## 3. 裁切單位的定義

一個「裁切單位」是**可獨立 A/B、可獨立 rollback 的最小變更集合**——例如一組 filter 註冊、
一類資源目錄、一個 library 的連結去留、一項工具鏈旗標。

- 不得把多個單位打包成一次變更。無法歸因的減量視同失敗——這是 roadmap「每輪只解一組主要
  未知數」在 R10 的形式。
- 單位的邊界在其凍結矩陣（第 4.2 節）中定義，正式 run 開始後不得移動。

## 4. 每個裁切單位的證據要求（缺一即不得合併）

### 4.1 獨立 inventory

移除**前**先列清單：這個單位包含哪些檔案／符號／設定條目，各自的 size attribution（raw 與
gzip 分列），以及「誰引用它」的 reachability 證據——link map、symbol reachability、資源
access trace、功能 trace。**不得以 library 名稱或目錄名稱猜測用途**（roadmap 8.2 原則）。
R5 第 5 節的原則延續：尚未觸發的相依不等於無用相依，inventory 要能區分「沒人引用」與
「這輪 corpus 沒踩到」。

### 4.2 凍結矩陣

正式 A/B 前，把單位範圍、預期收益、驗證項目、門檻與判定規則寫成機器可讀 JSON 並凍結。寫法
沿用 [`e2/discovery-matrix-v1.json`](../wasm_sdk_probe/e2/discovery-matrix-v1.json)：
`schemaVersion`、baseline hash、provenance（注明每個數字是量測還是推測）、`thresholds`、
`decisionPolicy`；**正式結果產生後不得放寬**。門檻在結果之前寫死，是防止「量到多少就把門檻
改成多少」的唯一結構性手段。

### 4.3 A/B artifact

before／after 各自完整建置並記錄 hash。量測至少包含 raw bytes、gzip -9、瀏覽器 cold
compile／engine ready 與 runtime memory 各一組——**只量 raw bytes 不構成證據**（roadmap 8.2：
工具鏈最佳化必須驗證 browser compile 與 runtime memory，不只 raw bytes）。

### 4.4 功能 corpus 全量

P4 凍結的 corpus 聯集在 after artifact 上**全量**通過，含全部 typed negative 案例；不得抽樣，
不得只跑「與本單位相關」的子集——單位間的隱性相依正是抽樣抓不到的東西。

### 4.5 desktop round-trip

after artifact 的輸出文件經 desktop LibreOffice reopen 與 PDF export 驗證，比照 R7-C 流程。

### 4.6 rollback

單位可獨立回退，回退後 artifact hash 回到 before 記錄值；rollback 步驟**實際演練過**並留下
hash 證據，不是紙上宣稱。E2 DEVLOG 的 `e1-editor-v1` 誤重建事件已示範過「逐字還原、hash 回到
記錄值」的標準，R10 沿用。

### 4.7 缺檔負向測試

被移除資源的缺檔行為是 typed、可解釋的——不是 crash、不是 silent 降級、不是「剛好還能啟動」。
以刪檔後「剛好啟動」作成功標準是 R5 第 1 節明文禁止的，R10 繼承。

## 5. 每單位的執行順序

```text
inventory（4.1）→ 凍結矩陣（4.2）→ A/B build（4.3）
    → 功能 corpus 全量＋round-trip＋負向（4.4～4.7）→ 判定 → 合併或 rollback
```

順序不可顛倒。沒有 inventory 的 A/B 等於「刪掉看會不會壞」，禁止；沒有凍結矩陣的量測等於
事後湊門檻，禁止。單位判定後才開始下一個單位；不並行多個未判定單位，避免歸因混淆。

## 6. 停止條件

- **維護成本紅線（總停止條件，優先於任何體積目標）**：若減量只能靠修改大量 LibreOffice core，
  且維護成本高於下載收益，**保留 R5 profile 並停止該方向**。這是 roadmap 第 8.2 節的明文條款；
  「維護成本」至少要以受影響的 core 檔案數、與上游的 rebase 衝突面、每次升版需重驗的 corpus
  範圍來量化，不得只用主觀估計。
- 單一單位 A/B 後功能 corpus 出現任何不可解釋失敗 → 該單位 rollback 並記錄；**不得「先合併
  再修」**。
- 減量造成缺檔 silent 降級且無法 typed 化 → 停止該單位。
- 工具鏈最佳化使瀏覽器 compile 時間或 runtime memory 回退、raw bytes 收益不抵 → 停止該項。
- build 非決定性（同輸入不同 hash）→ 先修 build 決定性再繼續；在非決定性 build 上做 A/B 沒有
  意義。注意：E2 DEVLOG 觀察到「相同前處理輸入產生位元相同 WASM」是**單一正例**，不得外推為
  全建置決定性——這正是 bit reproducibility 三分法（第 7 節）要防的混淆。
- 任何時點停止都是有效實驗結果（roadmap 規劃原則：No-Go 是有效結果），必須留下可重現證據與
  替代路徑，不得為了「讓 R10 有交付」而降低證據標準。

## 7. 量測規則

- raw 與 gzip -9 分列；不把 gzip sum 當網路 SLA（沿用 R5 第 6 節）。
- cold／warm browser ready 與 WASM compile 至少在 Chrome 量測；引用數字必須標示量測拓樸
  （loopback／local delivery），不冒充 production CDN（沿用 R8 教訓）。
- bit reproducibility 三分，不得混為一談（roadmap 8.2）：deterministic content、artifact hash
  更新機制、真正 bit-reproducible build。每個單位的矩陣要寫明自己依賴哪一層。
- Firefox 量測沿用 finding 014 的 Worker generation 上限；Firefox 缺席的量測項標 `unavailable`，
> **2026-08-08 更正**：此處把 finding 014 的限制列為「已觀察」，但該 finding 的成因已改判為我方 harness，**同頁 50 個 generation 實測全過**（上限所寫的 16 倍以上）。見 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)〈每頁 Worker generation 上限為 3〉一節。條文未改，僅記錄前提不成立。
>
> **2026-08-08 第二次更正（這一條數錯了東西）**：上面說的「每頁 Worker generation」是
> **每頁引擎實例化次數**，而**產品從來沒有實作過它**。產品唯一實作的是
> `editor-shell/editor-session.js` 的 `maxWorkerGenerations`（預設 **3**），數的是
> **同一個 `EditorSession` 的崩潰／boundary 回復次數**：首次 `open()` 算第 1 代，
> 之後每次 `restart()` ＋1；`close()` 之後不能再開，下一份文件是新的 session、計數器歸零。
> 兩者只有在「一頁只有一個 session」時才碰巧一致。見
> [finding 026](../findings/026-generation-cap-means-two-different-things.md)。
>
> **決定（2026-08-08）：產品維持 3。**理由是崩潰回復深度本來就該有界，
> 與 finding 014 無關、也不因 014 撤回而需要改動；
> **「每頁」這個承諾撤除**——它沒有任何產品側實作，且 014 撤回後也沒有任何已量測的理由
> （單頁 100 代通過，記憶體是回收延遲不是殘留，見 finding 014〈待驗證 10 結案〉）。
> 佐證：出貨 artifact `835b453d…` 在回復軸上 Chrome／Firefox 各 **16/16**，
> 第 17 次仍以 `WORKER_GENERATION_LIMIT`＋`requiresPageReload` 擋下，fail-closed 未被移除。

  不以 Chrome 數字補。

## 8. 裁切目標（本規格明確不列）

候選**方向**見 roadmap 第 8.2 節：filter allowlist、UI／config／gallery／sample 資源、core
libraries、scripting、工具鏈最佳化、reproducibility。那是方向清單，不是目標清單。

具體目標必須待 P1～P5 全部成立後，依第 3～4 節的格式**逐單位另立 R10-A、R10-B…子規格**，
每份子規格獨立取得執行授權。本文件不預先為任何方向背書順序或收益預估——目前沒有任何一個
方向有 inventory 證據，寫預估就是猜。

## 9. 判定語彙

R10 整體不設單一 GO。逐單位判定：

| 判定 | 條件 |
|---|---|
| `MERGED` | 第 4.1～4.7 七項證據齊備，判定後合併 |
| `ROLLED_BACK` | 任一驗證失敗，已回退且 hash 回到 before 記錄值 |
| `STOPPED` | 觸發第 6 節任一停止條件，方向終止 |

R10 的結束狀態由已 `MERGED` 單位總結；全部 `STOPPED` 且保留 R5 profile 也是有效結束——它的
證據價值是「深層減量在目前架構下不划算」，這個結論值得留痕，不是失敗。

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。只定義方法、進場閘門（P1～P5，含 P5 基線可重建）、裁切單位證據要求（4.1～4.7）、停止條件與判定語彙；明確不列裁切目標，目標待 E2／E3／E4 定案後另立子規格。前置條件未成立，不可啟動。 |
| 2026-08-08 | 更正。更正 Worker generation 上限的**語意**：規格原本寫「每頁」，但產品唯一實作的是每個 `EditorSession` 的崩潰／boundary 回復次數（`maxWorkerGenerations`，預設 3）。**產品維持 3，「每頁」承諾撤除**（無實作，且 finding 014 撤回後無已量測理由）。條文與註記已就地修訂；未動任何閘門，判定不變。見 finding 026。 |

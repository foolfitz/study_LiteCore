# SPEC E4-000：Markdown 讀寫（候選）

> **日期**：2026-08-05  
> **狀態**：規劃；尚未執行，未取得執行授權  
> **依據**：[R6+ roadmap 第 6.3 節](./SPEC-R6+-roadmap.md)、[E1 `E1_GO_ODT_EDITOR`](./SPEC-E1-000-overview.md)、
> [R7-C `PARTIAL_GO_ODT_FIRST`](./SPEC-R7-C-document-compatibility.md)、
> [finding 013](../findings/013-sdk-open-name-rejects-docx-before-content-detection.md)

## 1. 文件定位

產品目標是「編輯功能精簡、讀取完整」的 Writer WASM。E4 處理 Markdown 的讀取與匯出，順位高於
E3 的 DOCX 選項（2026-08-05 產品決定，見 roadmap 第 10 節）。順位理由是「LibreOffice 26.8 已內建
雙向 Markdown 濾鏡，成本可能低一個量級」——這句話的前半是原始碼層級**已觀察**（第 2.1 節），
後半是**推論**。本規格的第一道閘門 G0 就是驗證這個推論的最便宜實驗；G0 不通過，本文件其餘各節
的一切能力描述**全部作廢**，不構成承諾。

本文件是 overview：定義閘門順序、有損格式的產品契約要求與 closed surface 邊界。E4-A 及其後
子規格待 G0 方向確認與執行授權後另立。E4 與 E2／E3 無技術相依；三者同為 R10 前置條件。

## 2. 進場基線

### 2.1 已觀察（原始碼層級，2026-08-05；引自 roadmap 第 6.3 節，不重查）

- `filter/source/config/fragments/filters/Markdown.xcu`：flags 為 `IMPORT EXPORT ALIEN`，
  `DocumentService` 為 `com.sun.star.text.TextDocument`，`UserData` 為 `Markdown`。
- `filter/source/config/fragments/types/generic_Markdown.xcu`：副檔名 `md markdown`，media type
  `text/markdown`，偵測走 `PlainTextFilterDetect`。
- 兩者都列在 `filter/Configuration_filter.mk`（generic_Markdown、Markdown）。
- 實作在 `sw/source/filter/md/`：`swmd.cxx`（讀）、`wrtmd.cxx`（寫），另有 `mdnum`、`mdtab`、
  `mdcallbcks`。
- reader 已在 `sw/source/filter/basflt/fltini.cxx:101` 註冊為 `ReadMarkdown`，對應 `READER_WRITER_MD`。
- 剪貼簿另有 `SotClipboardFormatId::MARKDOWN`，`sw/qa/filter/md/md.cxx` 有貼上 markdown 的測試。

### 2.2 已觀察（專案層級）

- E1-B closed enum 慣例：產品 ABI 只接受固定 enum、內部映射固定、JS 拿不到 command string
  （[SPEC E1-B](./SPEC-E1-B-narrow-editor-contract.md) 第 3～4 節）。E4 的格式 surface 沿用同一慣例。
- finding 013 已框定 allowlisted `format` 列舉方向：驗證、實際 MEMFS path、manifest capability
  三者一致，不公開任意 path 或 raw filter 名稱。
- R5 政策是不刪除 filter data／registry／configuration（[SPEC R5-000](./SPEC-R5-000-overview.md)
  第 5 節）；資源分包只動了字型。
- native 26.8 對照 harness 已存在並在 E2-A A2-native 實際使用過（`build-native-26-8`、
  `wasm_sdk_probe/tools/run_e2_a_native.sh` 模式）；桌面 round-trip validator 目前是
  LibreOffice 26.2.4.2。

### 2.3 推論（進場時即須誠實標記，全部待 G0／G1 升格或否證）

- 「sw 靜態連結進 probe.wasm，且 `ReadMarkdown` 被 `fltini.cxx` 的 reader 表引用，因此 md 讀取
  程式碼大概率在 WASM binary 裡」——推論。`-Oz` 與連結期 GC 可能移除；filter 註冊存在不等於
  WASM build 裡 reachable。
- 「R5 不刪 registry，因此 Markdown filter 條目在凍結 `soffice.data` 的打包 registry 裡」——推論。
  26.8 的打包內容從未針對此點驗證。
- 「成本低一個量級」——推論。G0 或 G1 任一失敗，此順位理由即不成立，順位決策交回 roadmap。

### 2.4 待驗證

- G0：濾鏡在本專案 WASM profile 是否實際連結且可用（第 4 節）。
- 桌面 26.2.4.2 是否支援 md 開啟／匯出——影響 round-trip validator 的選擇（第 9 節邊界）。
- `swmd.cxx` reader 實際支援哪些 markdown 構件；`wrtmd.cxx` writer 實際丟棄哪些 ODT 內容（第 5 節）。

## 3. 主要未知數

> 26.8 內建的雙向 Markdown 濾鏡，在本專案的 WASM profile 是否 reachable 且可用；若可用，
> 這個**有損**轉換能否以不靜默降級的 closed contract 公開？

## 4. 第一道閘門 G0：WASM reachability（不通過即停止）

這是本規格唯一的進場實驗，依成本由低到高分三步。每一步都可能單獨產生決定性否定；否定即停止，
判定 `STOP_OR_RESCOPE`，不往下寫任何能力承諾。

### G0.1 靜態 artifact inventory（零重建、零新程式碼）

- 在**凍結 artifact** 上搜尋 Markdown 濾鏡的註冊與實作痕跡：`soffice.data`（base pack 來源）打包
  registry 中的 Markdown filter／type 條目；`full-qa` 與 `writer-review` 兩個 probe.wasm 中可辨識的
  實作字串。兩個 profile 都要查——若只在 `full-qa` 存在，正好證明「註冊存在不等於產品 link
  reachable」。
- 判讀規則：**否定是決定性的**——打包 registry 沒有條目，或兩個 binary 都無實作痕跡，現行
  artifact 即不可用，G0 失敗。**肯定不是決定性的**——存在只允許進 G0.2，不得直接宣稱可用。
- 失敗時記錄「補上需要什麼」（重新打包 registry？重新連結？），停止。此時 E4 的順位理由消失，
  roadmap 須重新比較 E4 與 E3 DOCX 的相對成本。

### G0.2 native 26.8 對照（ground truth）

- 在 `build-native-26-8`（同 core commit `671c848b`）以最小文件執行 md 開啟與 md 另存，保存
  輸入輸出原始 bytes 與 stderr。
- 理由與 E2-A A2 相同：WASM 的否定結果分不出「core 沒有」與「我方沒接到」；native 先給出濾鏡
  本身行為的 ground truth，也是後續損耗矩陣唯一安全的量測地。
- native 失敗＝上游功能自身不成立，建立編號 finding，停止。

### G0.3 WASM 最小 runtime probe（隔離 artifact）

- 建立 `e4-md-discovery` 隔離 diagnostic artifact（不重建、不覆寫 R5 與 E1-B 凍結 artifact），
  以內部固定路徑對同一份最小 md 執行開啟與另存，逐項比對 G0.2 的 native 結果。
- 通過標準：開啟不 crash、讀出文字與 native 一致；另存 bytes 與 native 語意等價（不要求
  bit-identical）。
- 失敗時區分兩種情況並各自建立 finding：「濾鏡不在」（連結／打包缺，回頭修正 G0.1 的判讀）與
  「在但行為錯」（WASM 特定行為）。任一情況都停止。

G0 全程不修改 LibreOffice core。若 G0.1 顯示必須重新打包 `soffice.data` 或改動連結才能繼續，
那是能力範圍決策，須另行取得確認，不得順手做。

## 5. G1：native 損耗矩陣（先量，再寫契約）

G0 通過後、任何契約凍結前，在 native 26.8 量測並凍結兩份矩陣。這是 E2-A「先量再寫死」教訓的
直接應用：猜出來的損耗清單會把自己的錯誤偽裝成濾鏡的 bug。

- **export 損耗矩陣（ODT→MD）**：以特徵矩陣文件逐項量測——粗體／斜體、標題各層級、有序／
  無序／巢狀清單、表格（含 merged cell）、圖片、超連結、註解、追蹤修訂、頁首頁尾、分頁、
  字型／顏色／對齊／行距、CJK 與 Unicode 邊界字元。每項分類為 `preserved`／`degraded`／`dropped`，
  逐項附輸出 bytes 證據。
- **import 支援矩陣（MD→ODT）**：markdown 構件逐項量測——標題、強調、清單、圍欄程式碼、
  行內 code、表格、連結、圖片、引用、HTML 片段、跳脫字元。同樣三分類。
- 矩陣寫法沿用 [`e2/discovery-matrix-v1.json`](../wasm_sdk_probe/e2/discovery-matrix-v1.json)：
  機器可讀 JSON、provenance 欄位注明「量測而非推測」、正式結果產生後不得放寬。
- 沒有量到的特徵一律標 `dropped-unknown`，對使用者揭露時視同 `dropped`。**寧可低報保真度，
  不可高報。**

已知的結構性事實（推論，G1 要把它量化成逐項事實）：**ODT→MD→ODT 不是 round-trip**。Markdown
是有損格式，這不是缺陷而是格式本質；規格的責任是讓損耗可枚舉、可揭露，而不是假裝不存在。

## 6. 有損格式的產品契約（不得靜默降級）

以下是契約**要求**，G0／G1 通過後由 E4-B 依凍結矩陣落實；此處不預先承諾任何一項成立。

1. **權威格式仍是 ODT。** md 是匯入來源與顯式匯出目標，不是 working format。開啟 md 得到一份
   新文件，其後續 save 預設仍是 ODT；md 匯出不改變文件的 ODT 保存語意，也不把文件「切換」成
   markdown 模式。
2. **匯出必須顯式。** save 的格式參數是 closed enum（沿用 finding 013 框定的 allowlisted
   `format` 方向），預設 `odt`；`md` 必須由呼叫端顯式指定。UI 首次觸發 md 匯出須有明確的
   「這是有損匯出」確認。不得把 md 做成預設路徑或任何情況下的靜默 fallback。
3. **損耗揭露是 typed 結果的一部分。** md 匯出的回傳至少包含 `fidelity:"lossy"` 與來自凍結
   export 矩陣的損耗類別清單。「逐文件偵測本份文件實際含有哪些會丟失的內容」是否可行，由
   E4-A 以實驗決定；最低標準是類別級的固定揭露。逐文件偵測不成立時，不得以任何方式假裝有。
4. **匯入不假裝完整。** md 開啟結果標注 import 矩陣版本；不在矩陣 `preserved` 內的構件不得
   宣稱支援。
5. **靜默降級是停止條件。** 任何「轉換完成但內容丟了、使用者無從得知」的路徑，比照 R7-C
   silent loss 處理：保存 bytes、建立 finding、停止。

## 7. Closed surface（不暴露 raw filter 名稱）

- JS 只看得到 closed enum（候選：`format` 增列 `"md"`）。`Markdown`（filter 名稱／UserData）、
  內部 MEMFS path、filter flags 全部留在 Worker／C++ 的固定映射，與 E1-B「JS 拿不到 command
  string」同一慣例。
- 名稱與格式驗證沿用 finding 013 的結論：驗證、實際 MEMFS path、manifest capability 三者一致；
  不公開任意 path；`.md` 名稱的接受由 enum 驅動，不做字串猜測。若 E3 同期進行 `open()` 邊界收斂，
  兩者必須共用同一 enum taxonomy，不得各自定義。
- 偵測面風險（推論）：`generic_Markdown` 走 `PlainTextFilterDetect`，代表任意純文字都可能被
  當成 markdown 收下。公開 `open()` 對 md 的接受條件必須顯式，不得繼承偵測器的寬鬆。

## 8. 子階段路由

| 階段 | 內容 | 前置 |
|---|---|---|
| E4-A discovery | G0（reachability）＋ G1（損耗／支援矩陣）＋ WASM 對照 readback | 本 overview；執行授權 |
| E4-B contract | closed `format` enum、typed 損耗揭露、manifest capability、隔離 product artifact | E4-A 判定 |
| E4-C validation | 雙瀏覽器矩陣、md corpus、desktop round-trip、R6～E2 回歸 | E4-B 判定 |

順序固定 E4-A → E4-B → E4-C。本文件不預先授權任何一段；各子規格另立。

## 9. 邊界（不可退讓）

- 不修改 LibreOffice core。
- 不重建、不覆寫 R5 `writer-review` 與 E1-B `e1-editor-v1` 凍結 artifact；discovery 一律用隔離
  artifact（教訓來源：E2 DEVLOG 記錄的 `e1-editor-v1` 誤重建事件）。
- 不暴露 raw filter 名稱、任意 path、任意 UNO；新增 surface 一律 closed enum。
- 每筆結果標已觀察／推論／待驗證；`pass:true` 不得掩蓋縮限。
- 桌面 round-trip validator：26.2.4.2 是否支援 md 屬待驗證。若不支援，md 輸出的驗證改以
  native 26.8 為 validator，並明確標注其獨立性較弱（與 WASM 同一 source tree）；不得因 validator
  缺位而讓 md 輸出免驗。
- Worker generation 上限沿用產品預設（每個 `EditorSession` 3 代＝最多 2 次回復）。
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


## 10. 判定

**`GO_TO_E4_B`**：G0 三步全通過；G1 兩份矩陣凍結且逐項有 bytes 證據；WASM 與 native 行為一致；
損耗揭露機制（至少類別級）可實作。

**`PARTIAL_GO_TO_E4_B`**：僅單向成立（例如 import 成立、export 縮限，或反之）；或逐文件損耗
偵測不可行、只能類別級揭露。縮限項目必須明列並反映在 manifest 與 UI。

**`STOP_OR_RESCOPE`**：G0 任一步決定性失敗；WASM 行為與 native 不一致且無法歸因；出現任何
靜默內容丟失路徑；或補齊需要修改 core／重新打包且成本不再低於替代選項。此時順位決策交回
roadmap 第 10 節，本規格不得為維持順位而放寬條件。

## 11. Evidence contract

```text
findings/evidence/sdk-e4/
  reachability/static-inventory.json        <- G0.1（registry 條目、binary 痕跡、判讀）
  reachability/native-26-8/                 <- G0.2（輸入輸出 bytes、stderr、SHA-256）
  reachability/wasm/<browser>/              <- G0.3（逐 attempt 保存）
  loss-matrix/export-matrix-v1.json         <- G1 凍結
  loss-matrix/import-matrix-v1.json         <- G1 凍結
  loss-matrix/fixtures/                     <- 特徵矩陣文件與逐項輸出
  summary.json
```

每次失敗 attempt 獨立保存不覆寫；原始 bytes 與 stderr 逐字保存。可重現且影響 SDK／core 邊界的
新問題建立編號 finding；上游問題與我方問題分開標示。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。建立 E4 候選規格：G0 reachability 第一道閘門（靜態 inventory → native → WASM probe）、G1 native 損耗矩陣、有損揭露契約與 closed surface 邊界。未授權執行。 |
| 2026-08-08 | 更正。更正 Worker generation 上限的**語意**：規格原本寫「每頁」，但產品唯一實作的是每個 `EditorSession` 的崩潰／boundary 回復次數（`maxWorkerGenerations`，預設 3）。**產品維持 3，「每頁」承諾撤除**（無實作，且 finding 014 撤回後無已量測理由）。條文與註記已就地修訂；未動任何閘門，判定不變。見 finding 026。 |

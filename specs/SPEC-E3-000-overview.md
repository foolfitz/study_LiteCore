# SPEC E3-000：讀取完整性（候選）

> **日期**：2026-08-05  
> **狀態**：規劃；尚未執行，未取得執行授權  
> **依據**：[R7-C `PARTIAL_GO_ODT_FIRST`](./SPEC-R7-C-document-compatibility.md)、
> [R7-D 部分 GO](./SPEC-R7-D-usability-longevity.md)、
> [finding 013](../findings/013-sdk-open-name-rejects-docx-before-content-detection.md)、
> [R6+ roadmap 第 6.2 節](./SPEC-R6+-roadmap.md)

## 1. 文件定位

產品目標的另一半是「開檔案要完整」。R7-C 已證明 28 份 ODT corpus 跨 Chrome／Firefox 逐檔通過並
完成 desktop fidelity 分類；E3 處理其餘的讀取缺口。

**E3 的主體不是 DOCX。** DOCX 在本實驗是低順位選項（2026-08-05 產品決定，roadmap 第 10 節）；
finding 013 已框定最小安全修法，但**框定不等於排程**，不得因此自動排入主線。DOCX 獨立於第 7 節，
有明確需求才啟動。

E3 的三條主線：

1. **ODT 邊界情形**——28 份 corpus 之外，會影響「完整可信讀取」宣稱的邊界文件；
2. **document-content accessibility**——R7-D 至今明確 unsupported 的文件內容可及性；
3. **公開 `open()` 的格式辨識邊界**——名稱驗證先於 content detection 的拒絕行為
   （finding 013 的一般化面，不只 DOCX）。

## 2. 進場基線

### 2.1 已觀察

- R7-C：28 份 L0～L4 corpus 已凍結（manifest：`wasm_sdk_probe/test-docs/r7/manifest.json`），
  corpus validator、typed error taxonomy、fidelity 四層分類與 desktop round-trip 流程全部存在且
  通過；判定 `PARTIAL_GO_ODT_FIRST`，DOCX typed unsupported。
- R7-D：document-content accessibility 明確 unsupported——文件內文字、caret 與 semantic reading
  order 沒有公開 SDK 資料；該規格明令不得 OCR canvas 或解析 raw callback 假裝支援。此狀態在
  R7-D 部分 GO 與 E1-B 產品 contract 中都未改變。
- finding 013：公開 `open(bytes, {name})` 在 content detection 前以名稱後綴拒絕——
  `src/sdk_api.cpp:67-82` 對非 `.odt` 結尾同步回 `INVALID_ARGUMENT`；SDK input path 固定為
  `/tmp/oxsdk-input-<request>.odt`（`src/probe_engine.cpp:478-489`）；manifest 只宣告 `open-odt`。
  相同 DOCX bytes 配 `.odt` 名稱可完整讀取，Chrome／Firefox 皆重現。
- finding 012：image frame 直接 paragraph wrapper 的 close timeout 已由 bounded Worker recovery
  處理，core teardown 根因保留——這是一個已定位的 ODT 結構邊界，屬第 5.1 節的既知候選軸。
- finding 014：Firefox 長壽程序反覆建立大型 WASM Worker 有明確上限；E3 任何瀏覽器矩陣都必須
  沿用其 generation budget。

### 2.2 推論

- 「28 份 corpus 之外還存在會影響產品宣稱的 ODT 邊界」——推論。E3-A 的第一項工作就是把它變成
  可枚舉清單，而不是憑感覺追加測項。
- 「名稱驗證與 content detection 的不一致是系統性 surface 風險，不是 DOCX 單一事故」——推論。
  finding 013 只量了四個組合；大小寫、複合副檔名、超長與非 ASCII 名稱等行為完全未測。
- 「accessibility 若要成立，只能從既有公開 typed 資料組出，不能擴大 surface」——這是繼承自
  R7-D 與 E1-B 的邊界；能不能組出任何東西是待驗證。

### 2.3 待驗證

- `open()` 名稱處理矩陣的實際行為（第 4 節 G0.1）。
- 候選 ODT 邊界文件在現行 profile 的 typed 行為（開得起來？typed reject？silent 降級？）。
- 既有公開 surface（E1-B typed state、selection readback、search）能提供的最低限度內容可及性。

## 3. 主要未知數

> 「讀取完整」目前的證據邊界就是那 28 份 corpus。在 corpus 之外與 surface 邊界上，哪些可以
> 升格為承諾、哪些必須 typed reject、哪些維持明示 unsupported——並且每一類都有證據而不是預設？

## 4. 第一道閘門 G0：零重建邊界量測（不通過即停止）

最便宜的實驗：全部在**凍結 artifact 與既有 corpus** 上進行，不重建任何 profile、不生成任何新
fixture、不改 SDK。三項都是量測，不是能力驗證：

### G0.1 `open()` 名稱矩陣

以既有 corpus bytes 配名稱變體——大小寫（`.ODT`）、複合副檔名（`.odt.bak`）、無副檔名、超長
名稱、非 ASCII 名稱、內含 path 分隔符——建立行為矩陣：接受／拒絕、error code、是否進 queue、
Worker 是否健康。只記錄，不修改驗證邏輯。

### G0.2 讀取缺口 inventory

以 R7-C manifest 的特徵欄位為基準，逐特徵列出「28 份 corpus 覆蓋了什麼、沒覆蓋什麼」的機器
可讀清單；每個未覆蓋項標注來源（ODF 規格特徵、R7-C L2 當時未選、finding 012 相鄰結構、加密／
巨集／表單／嵌入物件等 R7-C L3 只測過 negative 面的類別）。

### G0.3 accessibility 現況盤點

列出現有公開 typed surface 能與不能提供的內容存取，逐項對照 R7-D 的 unsupported 聲明，形成
「可能的最低限度可及性」候選清單（允許為空）。

G0 的產出是一份凍結 scope 矩陣（寫法沿用
[`e2/discovery-matrix-v1.json`](../wasm_sdk_probe/e2/discovery-matrix-v1.json)：機器可讀、附
provenance、正式結果後不得放寬）；E3-A 之後的所有工作只能在矩陣範圍內進行，不得中途擴編。

**停止條件**：G0.1 出現不可重現或不可解釋的行為——同 bytes 同名稱跨 run 結果不一致，或拒絕
行為無法對應到任何可指出的驗證程式碼——即停止並建立 finding。surface 行為不可預測時，任何
「讀取完整」的宣稱都不成立，後續階段沒有意義。

## 5. 主線範圍

### 5.1 ODT 邊界情形

- 候選軸由 G0.2 inventory 定案，不在此預先凍結。目前已知候選（推論）：加密 ODT、含巨集、
  表單控制、嵌入 OLE、外部連結資源、異常但合法的 ZIP 結構、finding 012 相鄰的 frame 包裝
  結構、深巢狀清單與超長段落。
- **corpus 政策：沿用 R7-C 那 28 份與其 manifest／validator，不重新生成。** 邊界 fixture 是
  追加，corpus manifest 版本遞增；每個新 fixture 必須有 deterministic recipe 與 desktop
  baseline，比照 R7-C L1／L3 規則。desktop baseline 失敗的 fixture 分類為 invalid，不得拿來
  判 WASM regression。
- 判定語彙沿用 R7-C fidelity 四層與 typed error taxonomy，不另創分類。可接受的結論包括
  「typed reject」與「明示 degraded」；不可接受的是 silent loss 與未分類 crash。

### 5.2 document-content accessibility

- 目標**不是**完整 Web Writer accessibility——R7-D 已劃界，E3 不重開。要回答的是：最低限度的
  文件內容可及性（例如目前 viewport 的文字、selection 文字的結構化揭露）能否只靠既有公開
  typed 資料成立。
- 允許的結論是「維持 unsupported」，但必須留下否證證據——試過哪條路、為何不安全或不成立——
  避免下一輪重跑死路。與 E2-A A6 同一原則：這條線**不得**成為 E3 判定的否決條件。
- 不可用手段（沿用 R7-D 與 E1-B）：OCR canvas、解析 raw callback、把 diagnostic counters 升格
  為產品 state、為 a11y 單獨開 escape hatch。

### 5.3 公開 `open()` 的格式辨識邊界

- 以 G0.1 矩陣為基礎，決定名稱／格式驗證是否收斂為 closed `format` enum（finding 013 框定的
  方向）。驗收條件：驗證、實際 MEMFS path、manifest capability 三者一致；拒絕一律 typed 且
  可解釋；不公開任意 path。
- 若 E4 先行或同期進行，`format` enum taxonomy 必須與 E4 共用同一份定義，不得各自宣告。
- 這條線改的是**拒絕行為的明確性**，不自動帶入任何新格式承諾——enum 收斂後 DOCX 仍是
  unsupported，除非第 7 節被明確啟動。

## 6. 子階段路由

| 階段 | 內容 | 前置 |
|---|---|---|
| E3-A discovery | G0 三項量測＋scope 矩陣凍結＋邊界 fixture 追加與實測 | 本 overview；執行授權 |
| E3-B contract | `open()` 驗證收斂、能力與 unsupported 的 manifest／UI 明示 | E3-A 判定 |
| E3-C validation | corpus 全量（28＋追加）、雙瀏覽器、desktop round-trip、回歸 | E3-B 判定 |

順序固定 E3-A → E3-B → E3-C；各子規格另立，本文件不預先授權。

## 7. DOCX（低順位；有明確需求才啟動）

- 現況：依 finding 013 明確 typed unsupported。「相同 bytes 換 `.odt` 名稱可完整讀取」是已觀察
  事實，但只證明 content detection 對**那一份**最小 DOCX 成立，不得升格為能力，應用也不得以
  偽造名稱假裝支援。
- 最小安全修法已在 finding 013 框定（allowlisted `format` enum、三者一致）。真正昂貴的不是修法
  本身，是其後整套 R7-C 式義務：逐檔 DOCX corpus 的 open／render／search／ODT save／desktop
  round-trip 與 fidelity 分類。順位決策（2026-08-05）正是基於這個成本。
- **啟動條件**：出現明確、可指名的產品需求，且 roadmap 順位決策原地修訂。啟動時另立子規格
  （E3-D 或獨立編號），其判定獨立於 E3-A～C——DOCX 的成敗不影響三條主線的結論。
- 在此之前，UI 與 manifest 維持明確 unsupported；不以 experimental 按鈕或文案暗示將支援。

## 8. 邊界（不可退讓）

- 不修改 LibreOffice core；不重建、不覆寫 R5 與 E1-B 凍結 artifact；需要新 build 時一律隔離
  artifact。
- 任何邊界情形都不得以 raw callback、任意 UNO、OCR 或 sleep 補齊。
- 每筆結果標已觀察／推論／待驗證；`pass:true` 不得掩蓋縮限。
- Firefox 每頁 Worker generation 上限沿用 finding 014；負向與 crash 類案例後的恢復比照 R7-C
  「同 Worker 新 engine 開 t1」的驗證方式。

## 9. 判定

**`GO_TO_E3_B`**（E3-A 層級）／**GO**（E3 整體）：三條主線各自形成有證據的明確結論——能力
成立、typed reject、或明示 unsupported 加否證證據；追加 fixture 通過 R7-C 式驗證；`open()`
邊界行為收斂且跨 run 可重現；回歸通過。**「維持 unsupported」是合法的 GO 組成**，前提是它被
明示且有證據，而不是被遺漏。

**部分 GO**：某條主線已劃界但未收斂（例如名稱矩陣完成、enum 收斂延後），且未收斂處不影響
既有 28 份 corpus 的承諾。未收斂項必須明列。

**停止**：`open()` 邊界行為不可重現或不可解釋；追加邊界暴露 silent content loss 且無法 typed
化；任何主線只能靠禁止 surface 補齊；或既有 28 份 corpus 的承諾在實測中回退。保存 bytes 與
trace，建立編號 finding。

## 10. Evidence contract

```text
findings/evidence/sdk-e3/
  scope-matrix/scope-matrix-v1.json         <- G0 凍結產出
  open-boundary/<browser>/                  <- G0.1 名稱矩陣逐案例
  corpus-gap/inventory.json                 <- G0.2
  accessibility/inventory.json              <- G0.3 與後續否證證據
  corpus-delta/                             <- 追加 fixture、recipe、desktop baseline
  browser/<browser>/                        <- E3-A 之後逐檔結果
  summary.json
```

每次失敗 attempt 獨立保存不覆寫。可重現且影響 SDK／browser／core 邊界的新問題建立編號
finding；上游與我方問題分開標示。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。建立 E3 候選規格：三條主線（ODT 邊界、document-content accessibility、open() 格式辨識邊界）、G0 零重建量測閘門、corpus 沿用政策；DOCX 依產品決定獨立成低順位節，有明確需求才啟動。未授權執行。 |

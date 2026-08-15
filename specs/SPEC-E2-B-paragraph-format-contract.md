# SPEC E2-B：段落格式併入窄版契約

| | |
|---|---|
| **狀態** | **草擬中（v3，2026-08-15）。第 3 節閘門已執行——七臂過、G3 失敗、G1 判 void。ABI 未凍結。** |
| **提出日** | 2026-08-15 |
| **前置** | [E2-A](./SPEC-E2-A-paragraph-format-discovery.md) 總判定 `PARTIAL_GO_TO_E2_B`（2026-08-14），**進場條件兩半已於 2026-08-15 滿足**（10.14） |
| **授權依據** | [SPEC-E2-000](./SPEC-E2-000-overview.md) 第 7 節（127–134 行）：「A 未完成前不凍結新 ABI」、「B 與 C 的規格待 A 有結果後另寫」。**A 已有結果，故本規格得以撰寫；該節禁止的是提前凍結，不是提前撰寫。** |
| **外部意見** | 形狀由 2026-08-15 的外部裁決訂定（第 3.1 節）；v1 草稿經對抗性審查後大幅改寫，被打掉的東西記在第 8 節的修訂紀錄，**不隱藏** |

## 1. 目的

把 E2-A 已成立的段落層級格式能力，併進出貨 `e1-editor-v1` 的**下一版**窄版契約，
使 `demo-structure` 展示的五個動作能在**產品** artifact 上執行。

E2-B 完成只代表契約與 shell 可以進入 E2-C。**本規格不擴大 escape hatch。**

## 2. 起點

### 2.1 E2-A 判定為可承諾的五個動作

`set-list-none`／`set-list-unordered`／`set-list-ordered`（explicit closed enum，**不是 toggle**）、
`set-paragraph-heading`（**只承諾第 1 級**）、`set-paragraph-body`（後置條件是「**不是 heading**」）。

證據：A3 25 runs／125 次派送、A4 18／270、A5 8／42，綁定 `c89f069e…`，兩瀏覽器；
A7 round-trip 406 份 ODT、406/406 桌面重開。

### 2.2 一併繼承的六項縮限（E2-A 10.14）

1. `set-paragraph-body` 的後置條件是「不是 heading」，不是「是 Text body」。
2. heading 只承諾第 1 級（承諾範圍是 H1；量測極限是 level ≥7 不可分，2–6 讀得回 `h2`–`h6`）。
3. readback markup 是序列化器輸出，不是有文件的契約。
4. ~~barrier 收尾的選取還原會讓下一次選取請求失敗~~ → **已於 v23 撤除**（任務 #49）。
5. `changed` 永遠不宣稱（一律 `null`）——路線 C 的直接後果。
6. 不提供前置格式狀態讀取：產品無法回答「目前這一段是什麼格式」。
7. 只驗證過從收合游標派送 → **本規格第 3 節的閘門就是處理這一項。**

編號保留不重排（第 4 項已撤），**現存為六項**。

### 2.3 繼承的 typed failure：**要分成兩類，不能都叫「拒絕」**

E2-A 的清單抄成自然語言會讓 host 做錯 recovery。照實際的 shape 分開：

| 類別 | 情境 | 頂層 code | `failureShape` | mutation |
|---|---|---|---|---|
| **派送前拒絕**（零 mutation） | 空段落 | `EDITOR_FORMAT_*` | — | **沒有發生** |
| **派送後無法驗證** | 帶註腳／尾註 | `MUTATION_OUTCOME_UNKNOWN` | `footnote-apparatus-readback` | **可能已發生** |
| **派送後無法驗證** | 含 as-char frame（finding 037，**core 端未修**） | `MUTATION_OUTCOME_UNKNOWN` | `selection-type-not-readable` | **可能已發生** |
| **派送後無法驗證** | 讀回涵蓋一段以上 | `MUTATION_OUTCOME_UNKNOWN` | `multi-block-readback` | **可能已發生** |
| **階段逾時** | per-stage 期限 | — | `stage-deadline:<stage>` | 不保證 |

> **後三類的訊息是「動作已經送出去了，但我們驗不了」**，不是「什麼都沒做」。
> per-stage 期限只保「stage 不會無限等」，**不保「barrier 一定收場」**。
>
#### v10：B' 帶進來的 shape 名稱，**在 relink 之前釘死**

字串是編進二進位檔的。**在實作時才命名，就是讓事後的產物偏離事前登記的東西**
——本輪已經有過一次（分析器悄悄換掉判準）。所以先寫在這裡：

| shape | 何時 | 類別 | mutation |
|---|---|---|---|
| `routing-selection-not-readable` | **派送前**的路由讀取拿到非 TEXT 型態 | **派送前拒絕** | **沒有發生** |
| `gesture-not-permitted` | manifest 的 gesture mask 不允許這個手勢（5.7 v10） | **派送前拒絕** | **沒有發生** |
| `block-count-changed` | 派送後 block 數與派送前不符 | 派送後無法驗證 | 可能已發生 |
| `block-text-mismatch` | 逐 block 文字對不上 | 派送後無法驗證 | 可能已發生 |
| `block-extraction-failed` | html 抽不出 block | 派送後無法驗證 | 可能已發生 |

> **前兩個是新的一類，而且是好消息**：現行的 037 型態守衛
> （`formatBarrierSelectionIsReadable()`，`probe_engine.cpp:3189`）**在 barrier 裡面、
> 派送之後**才跑，所以含 as-char 圖的選取今天只能拿到派送後的
> `MUTATION_OUTCOME_UNKNOWN`。B' 的路由讀取在派送**之前**，
> **同一個型態檢查搬到那裡就變成零 mutation 的乾淨拒絕。**
>
> **但這也是個陷阱**：路由讀取是 `getTextSelection("text/html")` 的**新呼叫點**，
> 而 finding 037 講的正是「這個呼叫在某些選取上不可以做」。
> **路由讀取必須先檢查型態再讀 html**，否則會在派送前就把引擎卡住
> ——連 stage deadline 都沒有，因為 barrier 還沒開始。

> **另外，`multi-block-readback` 這一列的意思在 v2 變了。**
> 在 `blocks >= 2` 那條路由上，讀回涵蓋一段以上是**預期的基材**，不是失敗。
> 本表每一列都要標明它屬於哪一條路由。

> **v9 更正：~~host 的訊息必須叫使用者去看文件並在需要時 undo~~——那句話在
> 現行 shell 不可執行。** `undo()` 自己也走 `_enqueue()`
> （`editor-session.js:434`），而這幾類的 code 是 `MUTATION_OUTCOME_UNKNOWN`，
> 它在 `RECOVERY_ERRORS` 裡（`:15`），會先把 queue 擋掉（`:272`）——
> 所以使用者按下 undo 只會拿到 `EDITOR_NOT_READY`。引擎的字串那樣寫沒有錯
> （它面對的是**人**），但**協定不能把它當成 host 的動作**。
> 正確的處置見 5.13。

### 2.4 繼承的上游 workaround，**以及它的移除測試**

引擎的範圍選取是 `RESET`＋`START`＋`END`，而不是 LOK 文件與上游測試示範的
`RESET`＋`END`。這是 [finding 043](../findings/043-fn-select-para-leaves-the-shell-in-selection-mode-and-the-next-lok-range-selection-is-silently-dropped.md)
的版本相容 workaround，**不是產品語意**。

**移除條件不綁定上游採用哪一種修法**（043 列了兩個方向）。
**移除的判準是一個會失敗的測試，不是一句條件**：

1. 在目標上游 build 上**停用** `START`（不是只是「上游宣稱修了」）。
2. 派送 `.uno:SelectText`。
3. 第一次 `RESET`＋`END` 必須建立**精確預期的文字、回呼與幾何**。
4. **保留一個在修復前必定變紅的對照**——沒有它，這個測試證明不了任何事。
5. 再跑完整第 3 節與 A3／A4／A5。
6. **靜態檢查產品路徑確實不再插入 `START`。**

> 只跑第 3 節不能證明可以移除：**workaround 還開著時它一樣會綠。**

## 3. 第一道閘門：在範圍選取上派送

> 規則沿用 [E1-D](./SPEC-E1-D-range-selection.md) 第 2 節：**規格的第一道閘門必須是
> 最便宜的驗證實驗，通不過就停止。**

### 3.1 為什麼閘門在規格裡，而不是規格之前

1. SPEC-E2-000 第 7 節禁的是**提前凍結**，不是提前撰寫。先量再寫，寫的時候已知答案，
   **恰好繞開本專案的核心紀律**——規格先寫、預測先 commit、失敗分支先寫。
   事後寫的規格永遠不會錯，而永遠不會錯的文件在這裡沒有證據價值。
2. **縮限 7 自己就把這筆量測指派給 E2-B**（「E2-B 的產品側掃描矩陣要補的是這一格」）。
3. 暗格比原本以為的小——見 3.2。

### 3.2 暗格的實際大小

解析任務 #49 的 WASM 輪（`940b7723…`，三類 fixture × 兩瀏覽器）：
**每份 `result.json` 各有 4 筆 `dispatchSelectionCollapsed: false` 的格式派送，共 24 筆**，
全部完成、`failureShape` 為空、`dispatchSelectionRectangles` 為 1。

**那 24 筆撤不了縮限**——附帶觀察，沒有人事先把它寫成問題去問。
**但它們把暗格縮小了。** 仍然暗的是：

| 維度 | 24 筆涵蓋到的 | 仍然暗的 |
|---|---|---|
| 動作 | `.uno:DefaultBullet` 一個 | 其餘四個（`StyleApply` 兩個方向、`DefaultNumbering`、`RemoveBullets`） |
| 幾何 | `dispatchSelectionRectangles == 1` | **同段跨視覺行（多矩形）**、**跨段**、**反向** |

> **`dispatchSelectionRectangles == 1` 只描述視覺幾何，不等於單段。**
> 要主張單段必須有文字或 block 邊界的證據。本規格的臂因此**一律以存出來的 ODT 判定**。

### 3.3 八臂

跑在**組合 artifact**上（第 3.6 節說明為什麼合法）。每一臂各開一顆引擎（finding 038 的教訓）。
**每一臂 1 fixture × 2 瀏覽器 × 3 次，合計 48 個 run。**

**動作維度**（幾何固定為單段正向範圍）：

| 臂 | 動作 | 底層指令 | 為什麼暗 |
|---|---|---|---|
| **A1** `bullet-from-range` | `set-list-unordered` | `.uno:DefaultBullet` | **橋接臂**：把那 24 筆附帶觀察升格為預先登錄的可綁定證據 |
| **A2** `ordered-from-range` | `set-list-ordered` | `.uno:DefaultNumbering` | 未涵蓋 |
| **A3** `list-none-from-range` | `set-list-none` | `.uno:RemoveBullets` | 未涵蓋，而且**語意不同**（是離開清單） |
| **A4** `heading-from-range` | `set-paragraph-heading` | `.uno:StyleApply` | 未涵蓋，參數與期望 tag 都不同 |
| **A5** `body-from-range` | `set-paragraph-body` | `.uno:StyleApply` | 未涵蓋，**與 A4 參數相反、期望 tag 相反** |

**幾何維度**（動作固定為 `set-list-unordered`，因為它是刻畫得最清楚的那一個）：

| 臂 | 幾何 | 為什麼暗 |
|---|---|---|
| **G1** `wrapped-line-range` | **同一段內跨視覺行**，多個 selection rectangle | 24 筆全是單矩形 |
| **G2** `reverse-range` | `END` 在 `START` 左邊 | #49 的 AJ／AK 只量過反向**建立選取**，沒量過反向**派送** |
| **G3** `cross-paragraph-range` | 跨兩段 | 24 筆全是單段。**見 3.5，這一臂的判準與其他七臂不同** |

**fixture 與座標由 `PREDICTION.md` 指定並在跑之前 commit**，但本規格先釘死兩件：
A1–A5 與 G1／G2 用 `list-contexts.odt`（錨點可辨識、清單與非清單皆有），
G3 用 `multi-paragraph.odt`（五段、各有獨立錨點，改了哪一段看得出來）。

### 3.4 每一個正向臂都必須先證明「範圍真的存在」

> **這一節是 v1 缺的，而缺了它整個閘門是無效檢查。**
> 五個動作都是**段落層級**的。若範圍建立失敗、退回收合游標，
> 對游標所在那一段做 heading 或 bullet，**存出來的文件仍然完全符合後置條件**。
> 也就是說：**把被測的能力關掉，檢查照樣綠。**

A1–A5、G1、G2 每一臂在派送**之前**必須全部成立，否則該 run 作廢（不是失敗，是無效）：

1. 選取讀回的**文字**等於預期字串；
2. **`dispatchSelectionCollapsed == false`**；
3. `dispatchSelectionRectangles` 與該臂預期的幾何相符（G1 要求 **> 1**）；
4. 選取端點方向與該臂預期相符（G2 要求反向）。

派送**之後**必須全部成立才算通過：

5. **存出來的 ODT** 中，該臂宣告會變的段落全部達到目標狀態；
6. **相鄰未選取的段落逐字未變**；
7. 最終選取**收合**（`restoreConfirmed`）。

> 第 6 項是 v1 沒有的。沒有它，「這一段變成標題了」證明不了「只有這一段變成標題」。

### 3.5 G3 的判準不同，而且 v1 把它接錯了機制

**v1 寫「跨段範圍必須以 typed `multiBlock` 拒絕」。那個判準是錯的**，理由是機制不對：

- `multiBlock` 是從 **barrier 自己建立的後置條件選取**算出來的
  （`probe_engine.cpp:601`），而 barrier 用 `.uno:SelectText`（`FN_SELECT_PARA`）
  **永遠只選一段**；
- 格式指令早在 `:3549` 就派送出去了，`multi-block-readback` 是**派送之後**的判讀
  （`:3320`），**不是派送前的拒絕**；
- 所以跨段輸入**結構上走不到那個分支**：指令套用到兩段，barrier 收合回 restorePoint、
  選一段、驗一段、回報成功——**第二段被改了卻沒被驗證**。

**G3 要問的因此不是「會不會拒絕」，是「會不會靜默地驗證不足」。** 判準：

| 讀數 | 判為 |
|---|---|
| 具名失敗（任一 `failureShape`），且 ODT 顯示**零** mutation | **通過**：派送前拒絕，最乾淨 |
| 具名失敗，ODT 顯示有 mutation | **通過但要記**：這是 2.3 的「派送後無法驗證」，host 必須提示 undo |
| **回報成功，而 ODT 顯示兩段都變了** | **失敗**——**靜默的驗證不足**，這是本臂存在的理由 |
| 回報成功，ODT 只有一段變 | **失敗**：那表示指令沒有套用到整個範圍，語意與使用者預期不符 |

### 3.6 為什麼閘門可以跑在組合 artifact 上

閘門量的是**引擎行為**，用的是診斷 client（`FormatDiscoveryClient`），
與 #49 的 P1／P2 同一條路。**它不驗證產品協定**——產品協定的問題在第 5 節，
那些擋的是凍結，不是閘門。

### 3.7 兩個分支——**必須在跑之前 commit**

預測檔放 `findings/evidence/sdk-e2/discovery/e2b-gate/PREDICTION.md`。
成本模型引那 24 筆：完成、走 callback、約 30 ms、派送後選取收合。

| 分支 | 判準 | 處置 |
|---|---|---|
| **通過** | A1–A5、G1、G2 全部滿足 3.4 的七項；G3 落在 3.5 的兩個「通過」格 | 範圍派送進 ABI，**並把「派送後選取收合」寫成契約**（見 3.8） |
| **不通過** | 任何一臂失敗 | 見下方決策規則 |

**不通過時的決策規則（v1 缺這一條，導致失敗後可以事後挑一條看起來能動的路）：**

- **只有 G3 失敗** → 範圍派送進 ABI，但**跨段範圍以派送前 typed 拒絕**，
  且該拒絕必須零 mutation、必須有自己的 shape 名稱、必須另跑一輪驗證。
- **任一動作臂（A1–A5）失敗** → **該動作**不接受範圍派送，其餘可接受；
  以 capability 的動作層欄位明示，不是靠 UI 文案。
- **G1 或 G2 失敗** → 範圍派送**整條不進 ABI**，v2 只承諾收合游標派送。
- **選 collapse-first（派送前自動收合）需要另一份預測與另一輪**：
  它會改變使用者的選取與作用目標，**不是實作細節**，不得在失敗後直接採用。

### 3.8 通過時要一併釘死的收合語意

若閘門通過，契約必須寫明：派送之後選取**必定收合**；
**收合到哪裡不承諾**（`only-collapsed, location unspecified`），
除非閘門的資料足以支持更強的承諾。每一臂的最終 typed state 都要記錄，
不是只記「成功」。

### 3.9 閘門與凍結之間：**產品 build 上重跑**

閘門跑在組合 artifact 上，而 E2-B 出貨的是產品 profile。那是一次 relink，
**會產生新的 hash**（[finding 036](../findings/036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)：hash 不是原始碼的函數）。

> **凍結之前，第 3.3 節八臂必須在產品 build 上重跑並通過，且 A3／A4／A5 一併重掃通過。**
> 閘門在組合 artifact 上通過**不構成**凍結條件，只構成「值得付那次 relink」的條件。
> **sweep 與 freeze 之間不得再重編。**

> **v12 更正：A3／A4／A5 的「一併重掃」這一條，前提已經不成立。**
> 這句話是在「產品 build ＝ 把現有 E2 引擎重連結一次」的假設下寫的——
> 那樣做會換掉 `c89f069e`，E2-A 的判定就得重來。
> **實際做出來的不是重連結，是一個獨立的建置變體**（5.12），
> `c89f069e` 一個位元都沒動：`validate_e2_a.py` 重跑，`summary.json`
> **逐位元不變**，`decision` 仍是 `A3_PASS`，仍綁在 `c89f069e` 上。
>
> **所以那條重掃義務不成立**——但要接的話不是「跳過」，是**換一個東西接**：
> v2 artifact 上五個動作的涵蓋面由**第 7 節的矩陣**提供，
> 而它比 A3／A4／A5 更嚴（三個手勢類別、判在文件上、含未瞄準段落逐字未變）。
> E2-A 的判定留在自己的 artifact 上，不跟著搬。

> **v4 更正：那不是一次 relink，是一個尚不存在的建置變體。**
> 產品 objects 沒有 `-DOXSDK_E2_FORMAT_BARRIER`（`Makefile:538`），
> 而路線 C 整段包在那個 `#ifdef` 裡（`probe_engine.cpp:2991`／`:3611`）——
> **產品 build 根本沒有把路線 C 編進去**。詳見第 5 節第 8 項。

> **產品重跑另外被觀測性擋住**：產品 worker **不轉發 `formatBarrier.failureShape`**
> （`sdk/sdk-worker.js` 的 error 分支只轉五個欄位；診斷 profile 是由
> `tools/build_e2_discovery_profile.py:64`–`81` 另外 patch 上去的）。
> **所以第 5 節必須先解決：產品 worker 要不要轉發它。** 不解決就無法在
> 「完全相同的最終產品三件組」上判 G3。

## 4. 候選 ABI（**閘門通過且第 5 節解決後**才凍結）

- `OXSDK_EDITOR_ABI_VERSION == 2`；沿用現行的十個 action（1–10）並新增 11–15：
  `SET_LIST_NONE`／`SET_LIST_UNORDERED`／`SET_LIST_ORDERED`／
  `SET_PARAGRAPH_HEADING`／`SET_PARAGRAPH_BODY`。

> **十個是現況，不是 E1-B 的原文。** E1-B 只凍結八個（第 2 節），
> 底線與刪除線是 [E1-C](./SPEC-E1-C-editor-validation.md) 擴進同一份 v1 契約並重新綁定的。
> **這段歷史正好支持這次真的升 v2，而不是再一次原地擴 v1。**

## 5. 凍結之前必須解決的協定問題（**目前全部未解**）

對抗性審查指出候選 ABI 目前**穿不過現行的 worker 與 client**。逐項列出，
**每一項都是凍結的擋路條件**。

#### 十四項的現況（2026-08-15 收盤）

| # | 事情 | 狀態 |
|---|---|---|
| 1 | worker 的兩道 v1 閘門 | **已定案 → 5.5**（新操作族，字尾比對整條拿掉） |
| 2 | action map／`internalAction()` 只有 1–10 | **已定案 → 5.11**（v1 enum 不動，另開 v2 enum） |
| 3 | 產品 client 拒絕路線 C 的結果 | **已定案 → 5.6**（逐動作放寬） |
| 4 | ~~no-op 的 revision 語意~~ | **已撤回**（v4，判為錯誤） |
| 5 | 產品 worker 不轉發 `formatBarrier` | **已定案 → 5.5**（與 1、9 同一個改動） |
| 6 | capability 表達不了部分 GO | **已定案 → 5.7**（`actions` 改成 map，帶 `limits`） |
| 7 | freeze 的 negative matrix | **已定案 → 5.10**（十列，每列只動一件事）；第 7 節其餘門檻未訂 |
| 8 | **產品 build 沒編路線 C** | **已定案 → 5.12**（新建置變體＋relink 守衛＋補兩件欠著的） |
| 9 | 產品 state 投影以字串相等判斷 | **已定案 → 5.5** |
| 10 | manifest 的 action allowlist runtime 不執行 | **已定案 → 5.7**（交集，只能收窄） |
| 11 | 沒有產品 v2 的 profile builder | **已定案 → 5.8**（獨立 builder，fail closed） |
| 12 | 派送後失敗的 revision／dirty／recovery | **已定案 → 5.13**（全部視為 B；B ＝ rollback 到 checkpoint，不前進 revision） |
| 13 | `abiVersion` 沒有 consumer | **已定案 → 5.4**（新的 C symbol，必須進 relink） |
| 14 | 公開型別與 header 測試落後 | v1 那半**已補**（`c5cde7d`）；v2 那半**已定案 → 5.9** |

**會動到 relink 的只有 2、8、12、13。** 其餘是 JS／Python／資料，
但依 5.2 一樣要在最終量測之前定稿。

> **v4 更正**：以下各項在 2026-08-15 由 codex 逐項回到原始碼覆核，我再自己複驗。
> **第 4 項判為錯誤已撤回**，第 1、3 項描述不精確已改寫，並新增第 8–14 項——
> 其中**第 8 項（產品 build 根本沒有編入路線 C）足以推翻第 3.9 節「那是一次
> relink」的說法**。v1–v3 的第 5 節是從審查意見寫的，不是從原始碼重讀寫的。

1. **worker 的 v1 閘門其實有兩道，不是一道**。先是 capability 對照表
   （`OPERATION_CAPABILITIES`，`sdk-worker.js:37`）在 `:729` 檢查
   `editorActionV1`／`editorGetStateV1`／`editorSelectRangeV1` 三個操作名各自
   要求 `narrow-editor-v1`；之後才是字尾比對
   `request.operation.endsWith("V1") && !editorV1Enabled()`（`:752`），而
   `editorV1Enabled()` 寫死 `narrow-editor-v1` ＋ `version === 1`（`:98`）。
   **v2 profile 若只宣告 v2，現行十個動作通常在第一道就被拒**，根本走不到字尾比對。
   → 兩道都要處理。另外 client 端也把 `editorGetStateV1`／`editorSelectRangeV1`
   寫死在呼叫點（`editor-shell/editor-client.js:190`、`:218`），
   所以「新增 `editorActionV2`」不足以描述要動的範圍。
2. **worker 的 action map 只有 1–10**（`sdk-worker.js:47`），
   **C++ 的 `internalAction()` 對 11–15 落到 `default: return 0`**
   （`editor_api.cpp:46`／`:69`），在 `:86` 同步回 `INVALID_ARGUMENT`。
3. **產品 client 現在連派送都不會派送**——比 v3 寫的更早就擋掉了。
   五個動作不在 `ACTION_SET`（`editor-shell/editor-client.js:16`），
   `action()` 在 `:92` 直接丟 `EDITOR_ACTION_UNSUPPORTED`，
   **到不了 `:78`–`:86` 的結果驗證**。等到 v2 正確把五項加進 mutation 分類，
   才會撞上真正的衝突：驗證要求 `changed === true` ＋ revision `+1` ＋
   `completion === "uno-command-result"`，而路線 C 回 `changed: null` ＋
   `verified-format-readback`（`probe_engine.cpp:1200`–`1211`）。
   衝突是真的，順序不是 v3 寫的那樣。
   （另：檔案在 `editor-shell/`，不是 `sdk/`。v3 的路徑寫錯。）
4. ~~**no-op 的 revision 語意是版本差異**~~ —— **撤回，這一項是錯的。**
   `SPEC-E1-B:82` 確實寫著「format no-op 可回 `changed:false` 且 revision 不變」，
   但那是**規格原文**，不是**現行實作**：finding 022 之後
   inline format 的前置狀態捷徑已從引擎移除（`probe_engine.cpp:3595` 的註解寫明
   「停止讀前置狀態」），成功一律 `advanceRevision()`（`:2024`），
   client 也明文拒絕 `documented-state-noop`（`editor-client.js:79`）。
   路線 C 同樣每次成功 `+1`。**所以 v1 與路線 C 在 revision 上沒有差異**，
   差的是 `changed` 與 `completion`——那已經是第 3 項。
   **要做的是把 `SPEC-E1-B:82` 那句話標成已被 finding 022 取代**，不是在這裡列擋路條件。
5. **產品 worker 不轉發 `formatBarrier`**。成功路徑只對非 v1 操作補
   `selectionBarrier`（`sdk-worker.js:521`／`:537`），error 路徑只轉五個欄位
   （`:650`）；引擎的 `failureShape` 掛在 `formatBarrier` 上
   （`probe_engine.cpp:1119`）。診斷 profile 是 builder 另外 patch 上去的
   （`build_e2_discovery_profile.py:56`／`:74`）——**那正好證明共用的產品 worker 沒有轉發**。
6. **單一 capability 表達不了部分 GO 的限制**（只單段範圍／不支援範圍派送／只 H1／
   無前置狀態）。現行 manifest 只有 `narrow-editor-v1` 這種整體字串
   （`build_e1_b_profile.py:47`／`:51`），worker 也只比對整體字串（`sdk-worker.js:729`）。
   → manifest 需要動作層與 gesture 層的欄位。
7. **凍結不等於雙重 gating**。沿用 E1-B 第 6 節的 freeze 條件：header／manifest／
   worker map／client allowlist 四者全等；capability 缺一、version 錯一、
   把 11–15 送進 v1、未知 action、錯誤 options、stale revision——
   **每一種都要以文件 bytes 證明零 mutation**；產品 export inventory 不含 discovery symbol。
   **附帶事實**：目前唯一同時具備產品 C API 與路線 C 的 `e2-combination`
   **明確匯出三個 discovery symbol**（`Makefile:619`），因此它本身**不可能**當產品 artifact。

### 5.1 v4 新增的擋路條件（覆核時才發現的）

8. **產品 build 根本沒有把路線 C 編進去。** 產品 objects 的旗標是
   `-DOXSDK_EDITOR_DISCOVERY -DOXSDK_FINDING_016_SELECTION_BARRIER`
   （`Makefile:538`），**沒有 `-DOXSDK_E2_FORMAT_BARRIER`**；只有 `e2-combination`
   有（`Makefile:610`）。而路線 C 的入口整段包在 `#ifdef OXSDK_E2_FORMAT_BARRIER`
   裡（`probe_engine.cpp:2991`／`:3611`）。
   **所以第 3.9 節說的「產品 build 上重跑是一次 relink」是錯的**：那是一個
   **尚不存在的產品建置變體**。只加 action ID 11–15 而不改旗標，會掉進非路線 C 的
   fallback——其中段落樣式用的是註解已判定不可派送的
   `.uno:TextBodyParaStyle`／`.uno:Heading1ParaStyle`（`:3673`），
   清單開啟也不會帶路線 C 需要的顯式 `On:true` 參數（`:3031`）。
9. **worker 的產品 state 投影是以操作名相等判斷的**：
   `operation === "editorActionV1" ? productEditorState(event.state) : event.state`
   （`sdk-worker.js:521`），且對所有非 v1 操作補上診斷用的 `selectionBarrier`（`:537`）。
   **只新增 `editorActionV2` 會讓十五個動作全部收到原始診斷 state**，
   那既擴大產品 ABI，也牴觸 E1-B 禁止 a11y／scheduler／raw diagnostic state 的約束。
10. **manifest 的 action allowlist 目前在 runtime 不被執行。** worker 只查自己
    寫死的 `EDITOR_V1_ACTION_IDS`，不讀 `activeManifest.editorContract.actions`
    （派送路徑在 `sdk-worker.js:866`）。
    **所以第 7 項「capability 缺一必須零 mutation」不是加個 schema 就能達成**——
    worker 必須真的去執行 manifest 的 allowlist 與限制欄位。
11. **沒有產品 v2 的 profile builder。** `build_e1_b_profile.py` 寫死
    `e1-editor-v1`／`version: 1`／`abiVersion: 1`（`:40`／`:48`），
    而 `build_e2_discovery_profile.py` 一定會加上 diagnostic capability 與
    patch 過的 worker（`:166`／`:205`）。**目前沒有任何資料路徑能產生
    「v2、無 diagnostic capability、無 discovery export」的三件組。**
12. **派送後失敗的 revision 與 host 的 dirty／recovery 語意未定。**
    成功走 `advanceRevision()`，所有失敗都不走（`probe_engine.cpp:1236`），
    但有些失敗明確發生在派送之後、訊息自己承認文件可能已改（`:3282`／`:3293`）。
    host 只在成功後蓋 dirty／content stamp（`editor-session.js:249`），
    而 `RECOVERY_ERRORS` 只含 `MUTATION_OUTCOME_UNKNOWN`，
    **不含 `EDITOR_FORMAT_POSTCONDITION_FAILED` 或 `EDITOR_SELECTION_NOT_RESTORED`**
    （`editor-session.js:15`）。這比「轉發 failureShape」大得多，
    而且**必須與第 4 項一起決定**：等產品 artifact 量完才發現 handle 不能安全續用，
    就是第二次 relink。
13. **`editorContract.abiVersion` 沒有任何 consumer。** builder 寫得出來
    （`build_e1_b_profile.py:51`），但 worker 與 client 都只看 `version`
    （`sdk-worker.js:98`、`editor-client.js:46`），初始化時檢查的是 Document SDK 的
    `oxsdk_abi_version` 而不是 editor ABI（`sdk-worker.js:693`），
    `OXSDK_EDITOR_ABI_VERSION` 只是 header 巨集（`editor_api.h:12`）。
    → 要明定它是 build-time inventory invariant，還是需要 runtime gate；
    **選後者就得在那唯一一次 relink 裡加 symbol。**
14. ~~**公開型別與 header 測試已經落後現行 v1。**~~ —— **v1 的那一半已補（2026-08-15，`c5cde7d`）。**
    `editor-client.d.ts` 曾只列到 `set-italic`、`setInlineFormat` 只允許
    bold／italic，`tests/editor_abi_header_test.cpp` 只 assert 動作 1–8 且完全
    沒碰 `oxsdk_editor_select_range`——**那支測試存在的理由就是釘住 header，
    而它在兩顆出貨 artifact 期間只釘住十個動作裡的八個**。兩邊都補齊，
    並新增 `editor-shell/tests/declaration-drift.test.mjs` 直接讀 `.d.ts` 與
    runtime 比對，三個新檢查各做過突變控制。header test 是 `-fsyntax-only`，
    不產生 object，不影響任何 artifact。
    **仍然開著的是 v2 那一半**：`EditorSession` 只有 `setInlineFormat()`、
    沒有清單／段落的方法（`editor-session.js:426`），
    且固定實例化只接受 v1 的 `NarrowEditorClient`（`:125`）。

### 5.3 第 12 項：~~三分類提案~~ **已被對抗性審查打掉，退回「全部視為 B」**

> **2026-08-15 裁決：不要依這一節做 relink。** codex 的覆核打掉了提案的核心，
> 我複驗全部屬實。**留原文在下面不刪**，因為打掉它的理由本身是要帶進 relink 的。
>
> **一、class C 的前提是錯的。** 我寫「後置條件通過所以文件已驗證正確」——
> barrier 驗的只有**它自己用 `.uno:SelectText` 重選的那一段**的 html
> （`:3210`／`:3223`），不驗呼叫端原選取涵蓋的所有段落、不驗鄰段未動、
> 不驗文字身分、也不驗這個狀態**是不是這次 dispatch 造成的**（`:1213` 的註解明說）。
> 跨段路徑套用兩段卻只驗一段——**那正是 3.5 已經寫著的洞**，我在提案裡把它忘了。
>
> **二、`restoreConfirmed` 不是我以為的東西。** 它就是
> `restoreConfirmed = gEditorState.selectionRectangles.empty()`（`:3261`），
> 不比對 caret 是否回到 restorePoint、不比對原 range 是否恢復。
> 所以「選取不是呼叫端留下的那個」這個描述不準確。
>
> **三、C 幾乎是死碼。** 正常 restore 失敗時 finish 根本不會被呼叫，
> 會走 stage deadline 變成 `MUTATION_OUTCOME_UNKNOWN`（B），不是 C。
> 唯一明確可達的是 `!restorePointValid` 那條（`:3410`），
> 而 `restorePointValid` 只是 dispatch 當下 `caret.available`（`:3533`）。
> **在找到 deterministic 重現之前，C 不成立。**
>
> **四、B 前進 revision 得不到我寫的那個 stale error。** B 會 `_blockQueue()`，
> 所以根本沒有「下一個 mutation」——對那個 session generation 而言就是結束。
> 而且 error payload 完全沒有 `revision`（`:1236`），worker 也不轉發。
>
> **五、「提示使用者 undo」在現行 shell 不可執行。** `undo()` 自己也走
> `_enqueue()`（`editor-session.js:434`），queue 一擋就先被 `EDITOR_NOT_READY` 拒掉。
> 所以 B 只能二選一：**「這個 generation 結束、只能 rollback／restart」**，
> 或**提供受限的 resync／undo 流程**——不能兩句話一起寫。
>
> **六、我自己的「更正」算錯了。** 我寫十個失敗點裡八個發
> `MUTATION_OUTCOME_UNKNOWN`——**是七個**，而沒被涵蓋的是**三個**不是兩個
> （多一個 `EDITOR_STATE_UNAVAILABLE`，`:3093`，也發生在派送之後）。
> **數字就在我自己印出來的那張表裡，我數錯了。**
>
> **暫定裁決**：A 維持不前進 revision／不 dirty／不擋；
> **所有現存的派送後失敗一律視為 B**；C 不凍結進協定，
> 直到（a）逐 block 驗證涵蓋完整作用範圍、（b）有可重現的紅、
> （c）C 改成 success-with-warning 或 error payload 能原子帶上 revision／state／dirty。

#### 以下為原提案，保留備查（2026-08-15）

第 12 項必須和跨段處置**同時**定案，否則就是第二次 relink。以下是提案，
**尚未經對抗性審查**。

#### 先更正覆核報告裡的兩處不精確

- `RECOVERY_ERRORS` 有**六個**成員（`TIMEOUT`／`WORKER_CRASHED`／
  `WORKER_RESTARTED`／`STALE_DOCUMENT`／`MUTATION_OUTCOME_UNKNOWN`／
  `EDITOR_RESULT_INVALID`，`editor-session.js:15`），不是一個。
- barrier 的**十個**失敗點裡有**八個**發的是 `MUTATION_OUTCOME_UNKNOWN`
  ——**那個碼本來就在 `RECOVERY_ERRORS` 裡**。所以缺口比報告寫的小得多，
  真正沒被涵蓋的只有兩個碼。

#### 沒被涵蓋的那兩個，而且它們不是同一類

| 碼 | shape | 行 | 派送後文件的狀態 |
|---|---|---|---|
| `EDITOR_FORMAT_POSTCONDITION_FAILED` | `postcondition-not-met` | `:3338` | 讀回顯示**沒有**到達目標狀態——可能沒變、可能變了一半 |
| `EDITOR_SELECTION_NOT_RESTORED` | `selection-not-restored` | `:3349` | **後置條件已經通過**（`:3336` 的檢查先跑），文件**已經到達目標**，錯的只有選取沒還原 |

**第二個是這次讀出來的重點**：它在 `formatBarrierReadbackSatisfied()` 通過
**之後**才可能發生，程式自己的註解也寫著「the mutation happened and the
evidence says so」。**那不是「結果未知」，那是「結果已驗證、但旁狀態不對」。**
把它和 postcondition 失敗歸成同一類會讓 host 對一份**內容正確**的文件做
recovery——那是白付代價。

#### 提案：三類，各有自己的 revision／dirty／queue 語意

| 類 | 意思 | revision | dirty | queue |
|---|---|---|---|---|
| **A 派送前拒絕** | 零 mutation | **不前進** | 不設 | 不擋 |
| **B 已派送、結果未驗證** | 可能變了 | **前進** | **設** | **擋（recoverable-error）**，host 提示 undo |
| **C 已派送且已驗證、旁狀態未還原** | 內容正確，選取不是呼叫端留下的那個 | **前進** | **設** | **不擋**，但要明白告訴呼叫端選取不是它的 |

**B 為什麼要前進 revision**：revision 的工作是辨識文件狀態。文件可能變了而
revision 沒動，等於對下一個 mutation 說「上次之後什麼都沒發生」——
而 `requireRevision`（`:1738`）只比對相等，**它會放行**，於是後續操作建立在
一個假前提上。前進之後 host 手上的 expectedRevision 變成過期，
下一個 mutation 得到 stale revision——**fail-closed，這是對的方向**。

**現況與提案的差距**：現在**所有**失敗都不前進 revision（`failFormatBarrier`
`:1236` 沒有 `advanceRevision()`），而 host 只在成功分支蓋 dirty 與 content
stamp（`editor-session.js:249`–`259`）。所以今天 `selection-not-restored` 之後：
**文件已經改了、host 認為它是乾淨的、revision 守衛會放行下一個 mutation。**

> 這條路是 `OXSDK_E2_FORMAT_BARRIER` 才編進去的，**不在出貨的 v1 裡**，
> 所以這是 E2-B 的設計項目，不是既有缺陷。

#### 這個提案要自己的一輪

三類各要一個能製造出來的紅：A 用跨段（B' 的派送前路由）、
B 用註腳段落（`footnote-apparatus-readback`，已知可製造）、
C 目前**沒有已知的製造方法**——**那是這個提案最弱的一格**，
在找到之前 C 的語意是推理不是量測。

### 5.4 第 13 項的決定：**`abiVersion` 要有 runtime consumer，而且那是一個新的 C symbol**

**已有完全對稱的先例**，不是新發明：Document SDK 的 `oxsdk_abi_version()`
是一個匯出的 C symbol（`src/sdk_api.h:43`、`src/sdk_api.cpp:39`，
export list `Makefile:487`／`:708`／`:733`），worker 在 init 時 `ccall` 它
（`sdk-worker.js:693`），拿**二進位檔實際回報的值**去比對 client 要求的值。

現在的 editor 這一側沒有這個東西：`OXSDK_EDITOR_ABI_VERSION` 只是 header 巨集
（`editor_api.h:12`），builder 把 `abiVersion` 寫進 manifest
（`build_e1_b_profile.py:51`），而 worker 與 client 都只看 `editorContract.version`
（`sdk-worker.js:98`、`editor-client.js:46`）。
**manifest 是宣稱，二進位檔是事實**，而 finding 027／036 整個講的就是這兩者會分家：
hash 不是原始碼的函數，profile 是組裝出來的，一顆過期的 wasm 配一份新的 manifest
在今天**跑得起來而且沒有人會知道**。

**決定：加 `oxsdk_editor_abi_version()`，匯出，worker 在 init 時比對。**
所以**它必須在那唯一一次 relink 裡**——這正是第 13 項要現在決定的原因。

#### 一個刻意不採用的做法：借用 major/minor 相容區間

Document SDK 的規則是「major 相等且 requested minor ≤ actual minor」
（`sdk-worker.js:695`）。照抄很誘人，因為 v2 剛好是 v1 的超集
（動作 1–10 不動、11–15 新增），在那個規則下它是一次 minor bump。

**不採用。** editor 契約是一份 **allowlist**，allowlist 的版本是**身分**不是區間。
把區間語意混進來，正是 E1-C 能夠原地把底線刪除線擴進 v1、
而**凍結測試只釘住十個裡的八個**還沒有人發現的那種鬆動（今天才補，`c5cde7d`）。

所以：**flat integer，runtime 要求完全相等**。
「v2 要不要服務 v1 的呼叫端」是**操作層**的問題（第 1 項），
在那裡解決，不要用版本號的區間去含糊帶過。

### 5.5 第 1 項的決定：**v2 profile 就是 v2 profile，字尾比對整條拿掉**

現況的兩道閘門都以「V1」這個**字串形狀**為準：
capability 表以操作名為 key（`sdk-worker.js:37`，`:729` 檢查），
之後 `request.operation.startsWith("editor") && request.operation.endsWith("V1")
&& !editorV1Enabled()`（`:752`），而 `editorV1Enabled()` 寫死
capability `narrow-editor-v1` ＋ `editorContract.version === 1`（`:98`）。

**決定（與 5.4 同一個理由：allowlist 的版本是身分不是區間）：**

1. **新的操作族**：`editorActionV2`／`editorGetStateV2`／`editorSelectRangeV2`，
   新的 capability `narrow-editor-v2`，`editorContract.version === 2`。
2. **v2 profile 不宣告 `narrow-editor-v1`。** 一個 v1 client 打到 v2 profile
   會在 capability 閘門乾淨地拿到 `UNSUPPORTED_OPERATION`——**這是誠實的**，
   因為若讓它通過，它會拿到下面第 4 點說的原始診斷 state。
3. **字尾比對整條拿掉。** 改成明確的表：每個操作名對應它需要的
   capability 與 contract version。字尾比對之所以要死，不是因為它現在錯，
   是因為它把「這個操作屬於哪個契約」編碼進**名字的形狀**——
   而那正是 `endsWith("V1")` 會在 v2 profile 上把現行十個動作全部拒掉的原因。
4. **產品 state 投影必須改成看「這是不是產品 editor 操作」，不是字串相等。**
   現在是 `operation === "editorActionV1" ? productEditorState(...) : event.state`
   （`:521`），而且對所有非 v1 操作補上診斷用的 `selectionBarrier`（`:537`）。
   **只加 `editorActionV2` 而不改這裡，十五個動作會全部收到原始診斷 state**
   ——那既擴大產品 ABI，也牴觸 E1-B 禁止 a11y／scheduler／raw diagnostic state
   的約束。這是第 9 項，**它和第 1 項是同一個改動，不能分開做**。

> **第 5 項在這裡一併解決**：`formatBarrier` 的轉發要寫進同一張表——
> 承諾了 typed failure shape 就必須轉發它，否則 2.3 那張表在產品上是空頭支票。
> 診斷 profile 現在是 builder 另外 patch 上去的
> （`build_e2_discovery_profile.py:56`／`:74`），**那正好證明共用的產品 worker 沒有轉發**。

**這一節全部是 JS，不重連結**——但依 5.2，它必須在最終量測**之前**定稿，
否則 evidence 一樣會 stale。

### 5.6 第 3 項的決定：v2 的結果驗證**逐動作**放寬，不是整條放寬

現行 client 對每個 mutation 要求 `changed === true` ＋ revision `+1` ＋
`completion === "uno-command-result"`（`editor-client.js:78`），
而路線 C 回 `changed: null` ＋ `verified-format-readback`
（`probe_engine.cpp:1200`–`1211`）。

**決定：v2 的驗證器對這五個段落動作接受
`changed === null` ＋ `completion === "verified-format-readback"` ＋ revision `+1`，
其餘動作的判準一個字都不動。**

理由要說清楚，因為「放寬驗證」聽起來就是壞事：

- `changed: null` **不是「不知道有沒有成功」**，是「**沒有讀前置狀態**，
  所以說不出它變了沒有」。那是 finding 022 之後**刻意**的設計
  （`probe_engine.cpp:3595` 的註解：停止讀前置狀態，而不是讓它變可信）。
- 這五個動作的**後置條件是 barrier 驗過的**——`verified-format-readback`
  這個字面意思就是它。所以 client 放棄的是一個**它本來就拿不到**的前置狀態宣稱，
  換到的是一個**引擎已經驗證過的後置條件**。
- **但這必須逐動作。** 若把 `changed === null` 對 delete 也放行，
  finding 022 的無聲 no-op 就整個回來了——delete 的判準
  （`completion === "verified-selection-delete"` ＋ `changed === true`）
  是 E1-B 明文凍結的，**不在本規格的變更範圍內**。

> **順帶**：五個動作現在連結果驗證都到不了——它們不在 `ACTION_SET`
> （`editor-client.js:16`），`action()` 在 `:92` 先丟 `EDITOR_ACTION_UNSUPPORTED`。
> 所以第 3 項的實作順序是：先進 allowlist，才會撞到驗證器。

### 5.7 第 6 ＋ 第 10 項的決定：manifest 從「描述」變成「約束」，但**只能收窄**

這兩項是同一個改動。第 6 項說 capability 表達不了部分 GO 的限制，
第 10 項說 manifest 的 action allowlist 在 runtime 根本不被執行——
**而第 7 項的凍結條件要求「capability 缺一必須以文件 bytes 證明零 mutation」。
只加 schema 達不到那個要求**：worker 只查自己寫死的 `EDITOR_V1_ACTION_IDS`
（派送路徑 `sdk-worker.js:866`），**從來不讀 `activeManifest.editorContract.actions`**，
所以 manifest 少寫一項，worker 照樣派送。

#### v2 的 `editorContract.actions` 從名字清單改成 map

現在是十個字串的陣列（`build_e1_b_profile.py:13`）。v2 改成：

```
"actions": {
  "set-list-unordered": { "id": 12, "gestures": [...], "limits": [] },
  "set-paragraph-heading": { "id": 14, "gestures": [...],
                             "limits": ["heading-level-1-only",
                                        "no-precondition-state"] },
  ...
}
```

`limits` 就是 2.2 那六項縮限的機器可讀形式——**部分 GO 靠這個欄位表達，
不是靠 UI 文案**，這正是第 6 項要的東西。
**v1 的 manifest 不動**：它是凍結的，而且 5.4 已經定案版本是身分不是區間。

#### 執行的方向只有一個：**交集，manifest 只能收窄**

```
可派送 = worker 寫死的 map  ∩  manifest 的 actions
```

**這個方向是刻意的。** 反過來（manifest 說有就派送）會讓一份被改過的 manifest
擴大 ABI；而交集語意下，manifest 最多只能把已經編進二進位檔的能力**關掉**，
永遠打不開沒有的東西。**凍結的 negative matrix 因此變得可以做**：
拿掉 manifest 裡的一項，那個動作就必須零 mutation，而且是**可證的**。

#### gesture 由誰執行：**engine，不是 worker**

`gestures` 欄位宣告的是「這個動作接受哪些手勢」
（收合游標／單段範圍／跨段範圍）。**但 worker 判不了手勢**——它只看得到
動作名與座標。判得了的是 engine：9.9 已經定案用**派送前的 block 數**路由。

所以分工寫死：**worker 執行 `actions` 的交集，engine 執行 gesture，
manifest 兩者都宣告。** host 拿 `gestures` 決定按鈕要不要 disable
（第 9 節的遷移條款要求的正是這個），而不是靠使用者按下去才發現沒作用。

> **v10 補：engine 收不到那個宣告，所以要加一個入口。**
> `probe_engine.cpp` 與 `editor_api.cpp` 對 `manifest` 的引用是 **0 次**——
> engine 從來不讀 manifest。而 gesture mask 也**不能搭在每次派送的 options 上**：
> 5.11／N7 要求動作 11–15 的兩個旗標嚴格為 0。
> 因此需要一個**新的匯出 C symbol**（`oxsdk_editor_set_action_gestures(action, mask)`），
> worker 在 init 時依 manifest 呼叫一次，engine 在路由時據以拒絕，
> 拒絕要有自己的 shape 名稱。**這是 relink 的內容，不是 P2 的內容。**
>
> 沒有它，7.2 的 `PARTIAL_GO_TO_E2_C`（某個手勢類別不成立）
> **在 manifest 上寫得出來、在 runtime 執行不了**——
> 那正是第 10 項要殺掉的「manifest 只描述不約束」。
> 而且它會在 P3 之後才被發現，**那就是一次必然的第二次 relink**。

> **這一節全部是 JS／Python／資料，不重連結**——但依 5.2 必須在最終量測之前定稿。

### 5.8 第 11 項的決定：獨立的 `build_e2_b_profile.py`，而且它要**拒絕**產出不合格的三件組

現況沒有任何資料路徑能產生「v2、無 diagnostic capability、無 discovery export」：
`build_e1_b_profile.py` 寫死 `e1-editor-v1`／`version: 1`／`abiVersion: 1`（`:40`／`:48`），
而 `build_e2_discovery_profile.py` 一定加上 diagnostic capability 與 patch 過的 worker
（`:166`／`:205`）。

**決定：新寫一支 `build_e2_b_profile.py`，不是給既有的加旗標。**
理由與 5.4 同一條：版本是身分。**一支能用旗標從 v1 變 v2 的 builder，
就是一支能不小心把 v1 profile 標成 v2 的 builder**——而 E1-C 原地擴 v1
那次，正是「同一條路徑兩種身分」造成的。共用 hash／複製的 helper 可以，
共用進入點不行。

它產出：`profile: "e2-editor-v2"`、capability **`narrow-editor-v2`（不含 v1）**、
`editorContract.version = 2`／`abiVersion = 2`、`actions` 用 5.7 的 map、
`diagnostic` 欄位 pop 掉。

#### builder 要 fail closed，因為檢查已經存在了

**export inventory 的檢查不必發明**：`validate_e1_b.py:126`–`128` 已經在做——
exports 必須含 `_oxsdk_editor_action` 與 `_oxsdk_editor_get_state`，
且**不得含任何 `editor_discovery`**（讀 `build/e1/editor-v1/exports.txt`，`:112`）。

v2 的 builder 要**在寫出 manifest 之前**跑同一條檢查並在不合格時拒絕產出。
理由：`e2-combination` 明確匯出三個 discovery symbol（`Makefile:619`），
**它本身永遠不可能是產品 artifact**，而最容易犯的錯就是把它餵給 builder。
讓 builder 拒絕，比讓 validator 事後抓到便宜——事後抓到時，
證據可能已經跑完了。

### 5.9 第 14 項 v2 那半的決定

> **v11 補（實作時發現，計畫沒抓到）：`editor-client.js` 與 `editor-session.js`
> 是 hash 綁定的，改它們會解除出貨判定。**
>
> E1-C 的 shell bundle（`e1/editor-shell-bundle-v1.json`，digest `f9b1a52f…`）
> 把這兩支列在 `included`，而 `E1_GO_ODT_EDITOR` 的成立條件包含
> **source 與 dist 兩側的 hash 都要等於 manifest 裡登記的值**
> （`validate_e1_c.py:186`–`206`）。原本 5.9 寫「editor-client.js 加五個方法」
> ——**照做就會把已出貨的判定解綁**。
>
> 而且不能只是新增檔案：驗證同時要求
> `available - included - excluded` 為空（`:194`、`:205`），
> 其中 `available` 是 `editor-shell/*.js` 與 `input/*.js` 的 glob。
> **在 `editor-shell/` 底下新開一支 v2 檔案一樣會讓 E1-C 失敗。**
>
> **決定：v2 的 shell 放在新目錄 `editor-shell-v2/`。**
> 那個目錄不在 glob 裡，也不在 `web/e1-editor-validation-app.js` 的 import
> 追蹤範圍內（`:101`–`:117`），所以 E1-C 的 bundle 一個位元都不會動。
> v2 從 v1 匯入是可以的——匯入不改變被匯入檔案的位元組。
>
> 這與 5.4／5.8 是同一條理由的第三次出現：**版本是身分**。
> 一支能同時是 v1 又是 v2 的檔案，就是一支沒有人能說清楚它是哪一版的檔案。


v1 那半已補（`c5cde7d`）。v2 這半要跟著 5.5 的操作名走：

- `editor-client.d.ts`：新增五個動作的型別、v2 的操作名、
  以及 5.6 允許的 `changed: null` 結果型別；
- `EditorSession` 目前只有 `setInlineFormat()`（`editor-session.js:426`）、
  且固定實例化只接受 v1 的 `NarrowEditorClient`（`:125`）——
  兩者都要跟著 v2 走；
- `tests/editor_abi_header_test.cpp` 要斷言 11–15 與新的 ABI 版本常數。

**`declaration-drift.test.mjs` 已經會擋住宣告與 runtime 分家**（今天新增），
所以這一項的回歸風險已經先降下來了。header test 是 `-fsyntax-only`，
不產生 object，**不影響任何 artifact**。

### 5.10 第 7 項的決定：negative matrix，每一列只動一件事，零 mutation 判在 bytes 上

**兩條規則先寫死，因為它們決定這張表有沒有用：**

1. **每一列都是從一個會通過的基準只改一件事得到的。** 一次改兩件，
   「它拒絕了」就歸因不到任何一件。這是 #49 臂 G 被 codex 打掉的同一個毛病
   （「中間什麼都沒發生」是假的），不要再犯第二次。
2. **零 mutation 判在存出來的 bytes 上，不是判在回傳值上。**
   基準＝同一顆引擎開檔即存（e2b-gate 的教訓：原始 fixture 不是基準）；
   判準＝`<office:body>` **逐位元相同**。這個判準已經被 #50 用過並且穩定
   （標題→復原、移除清單→復原兩次都逐位元相同），所以它不是新發明的門檻。

#### 表

| # | 動的那一件事 | 期望的 typed 拒絕 | 為什麼這一列存在 |
|---|---|---|---|
| N1 | manifest 的 `actions` 拿掉 `set-list-ordered` | `UNSUPPORTED_OPERATION`（worker 交集，5.7） | **證明 manifest 真的在約束**，不是在描述 |
| N2 | manifest capability 拿掉 `narrow-editor-v2` | `UNSUPPORTED_OPERATION`（capability 閘門，`sdk-worker.js:729`） | 5.5 的第一道閘門 |
| N3 | manifest `editorContract.version` 改成 1 | 拒絕（5.5 的操作表） | 版本是身分，不是區間（5.4） |
| N4 | manifest `abiVersion` 與二進位檔不符 | 拒絕（`oxsdk_editor_abi_version()`，5.4） | **這一列是 5.4 存在的唯一理由**——沒有它，過期 wasm 配新 manifest 跑得起來 |
| N5 | 把 action ID 11–15 送進 **v1** profile | `INVALID_ARGUMENT`（`internalAction()` 回 0，`editor_api.cpp:69`） | v1 不得被 v2 的動作污染 |
| N6 | 未知 action 名 | `EDITOR_ACTION_UNSUPPORTED`（`editor-client.js:92`） | 現有行為，要釘住 |
| N7 | 錯誤 options（對段落動作送 `extendSelection: true`） | `INVALID_ARGUMENT` | 現行 v1 已有此檢查（`sdk-worker.js:876` 一帶），v2 要涵蓋 11–15 |
| N8 | stale revision | stale revision 錯誤（`probe_engine.cpp:1651`） | 樂觀並行的守衛 |
| N9 | 送 `unoCommand`／`keyCode`／`command` 欄位 | `INVALID_ARGUMENT`（forbidden-field 檢查） | forbidden-field inventory 的執行證據 |
| N10 | 拿 `e2-combination` 當產品 artifact 餵給 builder | **builder 拒絕產出**（5.8） | 它匯出三個 discovery symbol（`Makefile:619`），永遠不合格 |
| **N11** | manifest 把某動作限成 `[collapsed, single-range]`，卻在**跨段**範圍上派送 | **engine 拒絕**（gesture mask，5.7 v10 補） | **原本整張表沒有任何一列測 gesture 限制**——N1 測的是動作交集。沒有這一列，部分 GO 的手勢限制是不可證的 |

**N1–N9 每一列都要存檔並證明 `<office:body>` 逐位元不變。**
N10 不產生文件，判準是 builder 的非零退出。

> **N4 與 N10 是新的**，其餘是把現行行為釘住。
> 新的那兩列各自對應一個今天量到的真實缺口：manifest 與二進位檔會分家
> （finding 027／036），以及唯一同時具備產品 C API 與路線 C 的 artifact
> 剛好是不合格的那一顆。

**還沒訂的**：第 7 節的其餘門檻——每個動作每個瀏覽器的次數、歸屬欄位、
no-op 的 revision 方程式、validator 的突變控制。**那是下一項。**

### 5.11 第 2 項的決定：新增五個常數，**v1 的 enum 一個字不動**

`internalAction()` 對 11–15 落到 `default: return 0`（`editor_api.cpp:46`／`:69`），
`:86` 同步回 `INVALID_ARGUMENT`。要加的東西本身很小，**難的是加在哪裡**。

**決定：`oxsdk_editor_v1_action` 這個 enum 一個字不動，
另開 `oxsdk_editor_v2_action`，只含 11–15。**

- 1–10 的線上編號在 v2 完全不變，所以 v2 呼叫端送的就是 v1 的那十個常數；
- 這樣 `tests/editor_abi_header_test.cpp` 對 1–10 的斷言**逐字仍然成立**，
  不必為了 v2 去改一份釘住 v1 的測試——**去改它，就是把凍結測試變成
  跟著實作跑的東西**，而它今天才剛因為漏釘兩個動作被補過（`c5cde7d`）。

#### options：五個段落動作**兩個旗標都必須是 0**

現行規則寫在 header 的註解：`extend_selection` 只有兩個移動動作接受，
`enabled` 只有 inline format 動作接受。**五個段落動作兩者都不接受**，
必須是嚴格的 0，否則 `INVALID_ARGUMENT`。這就是 negative matrix 的 N7。

**`set-paragraph-heading` 不帶 level 參數**：縮限 2 是 H1 only，
所以層級是隱含的，ABI 的形狀不變。**等哪天支援 H2–H6，那是加參數的破壞性改動，
不是今天順手留一個沒有測過的欄位。**

### 5.12 第 8 項的決定：產品 v2 是新的建置變體，而且要掛上既有的 relink 守衛

產品 objects 的旗標是 `-DOXSDK_EDITOR_DISCOVERY
-DOXSDK_FINDING_016_SELECTION_BARRIER`（`Makefile:538`），
**沒有 `-DOXSDK_E2_FORMAT_BARRIER`**，而路線 C 整段包在那個 `#ifdef` 裡
（`probe_engine.cpp:2991`／`:3611`）。所以要的不是重連結，是**新的建置變體**。

以 `E1_B_BUILD` 為樣板（`Makefile:872`–`885`），v2 的目標要滿足：

1. **objects 帶三個旗標**：v1 那兩個 ＋ `-DOXSDK_E2_FORMAT_BARRIER`；
2. **export list 只加三個產品 symbol**（`_oxsdk_editor_action`／
   `_oxsdk_editor_get_state`／`_oxsdk_editor_select_range`）**加上 5.4 的
   `_oxsdk_editor_abi_version`**，**不得**沿用 `e2-combination` 的聯集
   （`Makefile:619` 有三個 discovery symbol）；
3. **掛 `refuse_unasked_relink`**（`Makefile:784`）：這個守衛已經在保護
   出貨的 `835b453d`，v2 的 artifact 一旦被綁定判定，就該受同一個保護。
   訊息裡要寫清楚它承載什麼。

#### 兩件欠著的一起補，因為改 Makefile 只有這一次機會

- `f049_native_select_after_format.cpp` 進 `test-e2-a-static` 的語法檢查；
- E2-B 閘門的 harness 與 `dist/e2b-fixtures/` 的 target
  （現在是手動 `cp`），連同 `e2b_native_crossparagraph.cpp`。

**finding 042：`Makefile` 是每個 `.o` 的前置依賴，改它就會重編重連。**
所以這三件事只有在同一次動 Makefile 時做才不用付第二次代價。

### 5.13 第 12 項重做：**全部視為 B，而 B 的意思是「回到上一個安全點」**

三分類提案已被打掉（5.3）。重做的結論很短：

**一、所有派送後失敗一律是 B。** 不特別處理 `EDITOR_SELECTION_NOT_RESTORED`
——它在既有 build 上幾乎不可達（正常 restore 失敗會走 stage deadline 變成 B），
而且它「驗過」的只有 barrier 自己重選的那一段。
**沒有可重現的紅之前，不給它獨立語意。**
`EDITOR_STATE_UNAVAILABLE`（`:3093`）也是派送後的，**一併歸 B**——
codex 指出它是我漏掉的第三個碼。

**二、B 不前進 revision。** 提案原本要前進，理由是「文件可能變了而 revision
沒動，守衛會放行」。**那個理由在 B 會擋 queue 的前提下不成立**：擋了 queue
就沒有「下一個 mutation」，session generation 就結束了。
而且 error payload 根本沒有 `revision`（`:1236`），worker 也不轉發——
**要前進就得同時改 engine、worker、client、session 四層，換到的是一個
走不到的錯誤路徑。** 不做。

**三、B 的處置是 rollback，不是 undo。** host 進 `recoverable-error`，
從**上一個 checkpoint bytes**（沒有就 authority bytes）重開。

**這條之所以可以接受，是因為 checkpoint 的時機剛好**：
`_checkpointBeforeSelection()` 在**每一次範圍選取之前**存檔
（`editor-session.js:346`／`:352`，條件是文件已 dirty 且內容自上次 checkpoint
後有變）。而 v2 的手勢就是「拖曳選取 → 按按鈕」——
**checkpoint 落在那次拖曳，格式動作緊接在後。**
所以 B 的 rollback **最多只損失那一個失敗的動作本身**，
而那個動作的結果本來就是未知的。

> **這是本規格第一次把「損失多少」算出來而不是含糊帶過。**
> 前提是那個手勢順序；若 host 改成不經拖曳就派送（收合游標直接按按鈕），
> **checkpoint 就不在那裡了**，這條理由跟著失效。
> 因此第 9 節的遷移條款要加一條：**產品展示的格式按鈕必須跟在選取手勢之後**，
> 或在派送前自行 checkpoint。

**四、redo 不進 v2。** `SPEC-E1-B:33` 明訂 Redo unsupported，
產品面 `DocumentHandle`／`NarrowEditorClient`／`EditorSession` 都沒有 redo。
rollback 語意不需要 redo，**所以這一項不因 E2-B 而開**。

#### 這個結論要的驗證，比原提案少得多

只要一列：**B 發生後，從 checkpoint 重開，文件回到派送前的 `<office:body>`。**
可製造的紅已經有了——註腳段落走 `footnote-apparatus-readback`
（`native-round1` 已知可製造）。

**不需要**「C 類的可重現紅」，因為 C 不進協定。

### 5.2 唯一一次 relink 要帶什麼進去

finding 042：改 `Makefile` 會重連結。所以下列**必須同一次做完**，
否則就是第二次 relink：

- `src/editor_api.h`／`src/editor_api.cpp`：ABI 版本、外部 ID 11–15 與對應。
- `src/probe_engine.cpp`：**跨段的處置**（3.5／9.5 的兩條路之一）、
  ~~G1 結果導出的範圍限制~~、以及第 12 項的 revision 決策。
  > **v10 更正**：G1 通過了（9.6），所以沒有「G1 導出的限制」要編進去。
  > 7.1 已經把同段多矩形歸成 **fixture 變體**、走 `blocks == 1` 的同一條路由。
  > 這一句是 v4 寫的、G1 還是 void 的時候留下的，**現在作廢**。
- `Makefile`：**產品 v2 的 object／link／profile target，產品 objects 必須帶
  `-DOXSDK_E2_FORMAT_BARRIER`**，export list 只留產品 symbol（不得沿用
  combination 的聯集）；**同時補上兩件欠著的**——
  `f049_native_select_after_format.cpp` 進 `test-e2-a-static`、
  E2-B 閘門 harness 與 `dist/e2b-fixtures/` 的 target。

**不重連結**（但在最終量測前必須定稿，否則 evidence 一樣會 stale）：
`sdk/sdk-worker.js`、`editor-shell/*`、profile builder、validator 與 negative matrix、
`tests/editor_abi_header_test.cpp`（獨立 host test，不參與 probe.wasm 連結）。


## 6. 不在範圍

沿用 SPEC-E2-000 第 9 節，並補上本規格自己的兩項：**H2–H6**（縮限 2）、
**前置格式狀態讀取**（縮限 6，工具列按鈕只反映我們自己上次設了什麼）。

## 7. 驗收與停止條件

### 7.1 門檻（2026-08-15 訂定）

沿用 E2-A 第 5 節那張表的形狀與數字，**不另立一套**：

| 項目 | 值 | 出處 |
|---|---|---|
| 正向重複次數／瀏覽器 | **3** | E2-A 門檻表 |
| 負向重複次數／瀏覽器 | **1** | 同上（負向是確定性拒絕） |
| barrier 上限 | 10,000 ms | 同上 |
| operation timeout | 30,000 ms | 同上 |
| open／save timeout | 180,000 ms | 同上 |
| Worker generation 上限 | 3 | 同上（finding 026 更正後的意思） |

#### 涵蓋面：**動作 × 手勢類別 × 瀏覽器**

手勢類別就是 9.9 的路由分界，不是別的切法：

| 類別 | 判準 |
|---|---|
| G-collapsed | 收合游標 |
| G-single | 範圍，派送前 `blocks == 1` |
| G-cross | 範圍，派送前 `blocks >= 2` |

**五個動作 × 三個手勢 × 兩瀏覽器 × 3 次 ＝ 90 個正向 run。**

#### 六個補上的格（v10，覆核指出）

**90 個 run 是骨架，這六格是覆核找出來的缺口**：

| 格 | 內容 | 為什麼缺不得 |
|---|---|---|
| **反向範圍** | G2 的幾何，`set-list-unordered`，≥1／瀏覽器 | **3.9 明文要求八臂全部在產品 build 重跑**，而 G2 對不到三個手勢類別的任何一格——照 90 格的切法它會整個掉出去 |
| **清單轉換** | 對已經是 bullet 的段落派送 `set-list-ordered`，判在 ODT 上 | 「清單切換造成 ODT 結構 silent loss」是**停止條件**，而目前**沒有任何一輪從非基準狀態出發**——那個停止條件現在燒不起來 |
| **清單中段離開** | G-cross × `set-list-none` 打在 ≥3 項清單的第 2–3 項 | 這是**清單被切開**的情形，ODT 結構上最險；也順帶是編號起始值 ≠ 1 的脈絡 |
| **混合狀態跨段** | ¶1 已是清單、¶2 是純段落 | 逐 block 抽取只在**同質**的一對上量過；`<ul><li><p>…</li></ul><p>…` 是沒量過的讀回形狀 |
| **no-op 兩個指令族** | 重複派送 `set-list-unordered` **與** `set-paragraph-heading` | finding 020：結果欄位對 list 指令**說謊的方式不同**。一族測不了另一族 |
| **rollback 驗收** | 註腳紅 → B → 從 checkpoint 重開 → `<office:body>` 逐位元相同 | 5.13 的整個結論靠這一列，而 P3 原本沒列 |

再加 **9.9 自己要求的自我紅臂**：期望 `ol` 卻派送 bullet，逐 block 狀態檢查必須紅。

> **一個刻意保留的重複**：G-collapsed × 五個動作與 A3／A4／A5 重掃涵蓋範圍重疊。
> 保留是為了 harness 一致，代價只有牆鐘時間——**寫下來，免得之後被當成疏漏**。

> **同段多矩形不是第四個手勢類別**——它的 `blocks` 一樣是 1，走同一條路由
> （9.6 實測 3 個矩形、1 個 block）。它是 **fixture 變體**，門檻另計：
> `wrapped-paragraph.odt` 至少要在 `set-list-unordered` 上、每瀏覽器出現一次。

#### 歸屬欄位

「completion 無法歸屬到單一 request」是停止條件，所以它必須是**可檢查的**。
每一個 run 的紀錄必須自帶：`requestId`、`action`、手勢類別、瀏覽器、
以及 loader／wasm／worker **三個 hash**。validator 對現場 artifact **重算** hash
（finding 027），輸出 `allEvidenceIsCurrentBuild` 與 `staleBuilds`，
**任何 stale 或缺漏一律不計入門檻次數**。

#### no-op 的 revision 方程式

v4 撤回第 4 項之後，事實是：路線 C **每次成功都 `advanceRevision()`**，
而 `changed` 恆為 `null`。所以方程式是——

> **每一次 completed 的動作，`revision_after == revision_before + 1`，
> 包含什麼都沒改變的那一次。**

**這要量，不能假設。** no-op 臂：對同一段連續派送兩次 `set-list-unordered`，
第二次必須**照樣** `+1`，且存出來的 `<office:body>` 與第一次之後**逐位元相同**。
每瀏覽器 3 次。

> 目前**沒有任何一輪測過重複派送**——閘門每一臂都是開檔、派送一次、存檔。
> **這一格是新的，不是把既有資料換個說法。**

#### forbidden-field inventory

worker 現在擋三個欄位（`keyCode`／`unoCommand`／`command`，`sdk-worker.js:867` 一帶），
manifest 也宣告 `arbitraryUnoCommandAccepted: false` 等旗標。門檻是：
**清單裡每一個欄位各送一次**（每瀏覽器 1 次），必須 `INVALID_ARGUMENT`
且 `<office:body>` 逐位元不變。**一次送一個**——一次送三個只證明「至少一個被擋」。

#### validator 的突變控制

**產生判定的每一支 validator 都要有突變測試**：把它檢查的那件事翻掉，
確認它變紅。這不是新規矩，是本輪已經做過三次的做法
（`analyze_e2b_identity_gate.py` 的四個抽取器對照、header test 的兩次突變、
`declaration-drift.test.mjs` 的移除測試）。

具體要求：validator 提供 `--self-test`，逐條翻掉自己的判準並斷言變紅，
**其輸出列入凍結證據**。理由寫在本輪的錯誤表裡——
**事後寫的分析器把預先登記的判準悄悄換掉過，而且換的方向讓那一臂變綠。**

### 7.2 判定

**`GO_TO_E2_C`**：90 個正向 run 全部達門檻；negative matrix（5.10）十列全過；
no-op 方程式成立；forbidden-field inventory 全過；
validator 的 `--self-test` 全紅；證據全部綁在同一顆產品 artifact 上。

**`PARTIAL_GO_TO_E2_C`**：某個動作或某個手勢類別不成立，其餘成立。
限制以 **5.7 的 `limits`／`gestures` 欄位**表達，**不是靠 UI 文案**。

**部分 GO**：依 3.7 的決策規則，限制以 **capability 欄位**與 UI 同時明示。

**停止**：completion 無法歸屬到單一 request；no-op 與遺失不可區分；
清單切換造成 ODT 結構 silent loss；或補齊需要 raw UNO／任意 command string／sleep／自動 retry。

## 8. Evidence 與綁定

`findings/evidence/sdk-e2/discovery/e2b-gate/`，依 `AGENTS.md`（2026-08-15）**用英文**。

**資料夾名稱不是綁定。** 每一份 result 必須自記 loader／WASM／worker 三個實際 hash，
validator 對現場 artifact **重算**，任何 stale 或缺漏一律不計入，
並輸出 `allEvidenceIsCurrentBuild` 與 `staleBuilds`（finding 027 的規則）。

## 9. `demo-structure` 的遷移，列入 GO

產品 build 出現之後：

- 產品展示改接 v2 client 與產品 profile；
- provenance 與 loader／WASM／worker 綁定同步更新；
- 現行 `demo-structure`（釘死 `c89f069e…`、走 discovery profile）**保留為歷史實驗檯並改名**，
  不是原地改掉——它是 E2-A 證據的一部分；
- **若範圍派送未通過閘門**，產品展示必須在拖曳選取後**停用格式按鈕或明示 collapse-first**，
  不得讓使用者按下去才發現沒作用。

- **格式按鈕必須跟在選取手勢之後，或在派送前自行 checkpoint（5.13 新增）。**
  5.13 的 rollback 語意之所以只損失一個動作，靠的是
  `_checkpointBeforeSelection()` 落在拖曳那一步。**收合游標直接按按鈕的話
  checkpoint 就不在那裡了**，B 的損失會回推到更早的安全點。

**這一項列入 GO，不留到 E2-C。**

## 9.5 閘門的執行結果（2026-08-15）

**落在 3.7 的「只有 G3 失敗」分支，外加一格未被實測。**
兩瀏覽器逐格相同，各三輪，跑在 `940b7723…` 上。
證據與三個比較器錯誤的自陳記在
[`findings/evidence/sdk-e2/discovery/e2b-gate/README.md`](../findings/evidence/sdk-e2/discovery/e2b-gate/README.md)。

| 臂 | 結果 |
|---|---|
| A1–A5（五個動作）、G2（反向） | **通過 3/3**，兩瀏覽器 |
| **G3**（跨段） | **失敗 3/3**——**但文件結果是對的** |
| **G1**（同段多矩形） | 第一輪 **void 3/3**；**第二輪以真的會換行的 fixture 重跑，通過 3/3**（見下） |

**G3 失敗的是宣稱不是文件**：兩段都變成項目符號、其餘三段未動——使用者要什麼就得到什麼。
失敗的是引擎回報成功，而 barrier 用 `.uno:SelectText` 只讀得回一段。
`verdict.json` 另記 `documentOutcomeCorrect: true`。
~~因為它影響該怎麼修：**拒絕一個結果正確的操作是有代價的**，
而 3.5 已經寫著另一個選項是「驗證所有受影響段落」。~~
**（後半句 v5 刪除：3.5 從來沒有寫過那一條，見下方更正。）**

**因此依 3.7 的決策規則**：範圍派送可以進 ABI，但跨段範圍必須**派送前** typed 拒絕、
零 mutation、有自己的 shape 名稱，且該拒絕要另跑一輪。

> **v5 更正（2026-08-15）：上面這一段原本還接著「**或**改成驗證範圍內每一段」，
> 並寫著「3.5 已經寫著另一個選項是『驗證所有受影響段落』」。**那句引用是假的。**
> grep 全文，那個說法只出現在 9.5 自己這一節——**是本節寫的，不是 3.5 寫的**。
> 3.5 的四格判準表沒有這一條，v2 沒有，v4 也沒有；
> `PREDICTION.md` 的「預先登記的處置」同樣只寫拒絕。
> **預先登記的處置是「派送前拒絕」一條，不是兩條。**
> 那句「拒絕一個結果正確的操作是有代價的」也不是新資訊：
> `PREDICTION.md` 在跑之前就預測「指令會套用到**兩段**（Writer 就是這樣做的）」。
> **我事前就知道文件結果會是對的，而且事前就選了拒絕。**
> 是外部裁決（fable）指出來的，我逐項複驗屬實。要偏離請看 9.7，不要靠這一段。

## 9.6 G1 的第二輪：那一格已經關掉（2026-08-15）

第一輪的 G1 判 void，因為 `第三段跨行 gamma` 是**段落很高不是跨行**。
第二輪新增 `dist/e2b-fixtures/wrapped-paragraph.odt`（1319 字，自己的目錄與
manifest，**凍結的 E1 corpus 一個位元都沒動**），G1 改瞄它，並新增對照臂 **G1c**。

跑在同一顆 `940b7723…` 上，兩瀏覽器各三輪，**逐格相同**。證據在
[`e2b-gate-round2/`](../findings/evidence/sdk-e2/discovery/e2b-gate-round2/README.md)，
預測在跑之前 commit（`1b41131`）。

| 臂 | 結果 |
|---|---|
| **G1**（同段多矩形） | **通過 3/3**，兩瀏覽器 |
| **G1c**（同一份文件裡不換行的段落，對照） | **通過 3/3**，恰好 1 個矩形 |
| 其餘七臂 | 與第一輪逐格相同（A1–A5、G2 通過，G3 失敗） |

G1 六次讀數完全一致：**3 個矩形**貼齊地鋪滿 `y=1807`→`4290`
（第一行、中間整寬的併合塊、最後半行），選取 584 字全在同一段內，
只有那一段變、其餘三段逐字未變，派送後收合，
`completion` 為 `verified-format-readback`。

**因此「範圍派送已刻畫完成」現在成立**——但要加兩句限定：

- **殘留一格**：G1 的範圍兩端都落在段落內部（掃描視窗到 4400 就停）。
  A 臂涵蓋「整段」、G1 涵蓋「多矩形」，**兩者的交集沒有量**。
  這比第一輪留下的那格小得多，但它存在。
- **預測的數字錯了、判準對**：預測猜 8–20 個矩形，實際是 3，
  因為 LOK 會把中間整寬的行併成一個高矩形。判準寫的是 `> 1`，那一條成立。

**順帶修掉分析器的一個問題**：把 G1 改瞄新 fixture 之後，以臂名為鍵的對照表
會讓分析器判不出第一輪的結果——**那正是第一輪第三個比較器錯誤的形狀**
（事後寫的判準悄悄偏離）。已改成以 `(arm, fixture)` 為鍵，並實測第一輪的
`verdict.json` 兩瀏覽器都**逐位元重現**。

第一輪的 G1 因此成了這條判準的**負向對照**：同一支分析器、同一條判準、
一份不會換行的 fixture，那一臂不會變綠。

## 9.7 跨段的處置：**明著偏離預先登記的那一條**（2026-08-15）

### 先講清楚偏離了什麼

**預先登記的處置只有一條：派送前 typed 拒絕。** 出處兩個，都在跑之前 commit：

- v2 的 3.7：「只有 G3 失敗 → 範圍派送進 ABI，但**跨段範圍以派送前 typed 拒絕**，
  且該拒絕必須零 mutation、必須有自己的 shape 名稱、必須另跑一輪驗證。」
- `PREDICTION.md` 的「Dispositions, pre-registered」：同一句話的英文。

「或驗證每一段」**不是**預先登記的。它是我在跑完之後寫 9.5 時加上去的，
而且我把它算在 3.5 頭上——**3.5 從來沒有寫過那一條**。

而且我不能拿「文件結果是對的」當偏離的理由：`PREDICTION.md` 在跑之前就寫著
「指令會套用到**兩段**（Writer 就是這樣做的）」。**事前就知道了。**
拿事前已知的事當事後改判準的新理由，正是 3.7 那條決策規則存在的原因
（v2 審查第九項：「失敗後可以事後挑一條看起來能動的路」）。

**這一節就是那條規則要求的代價**：偏離要明著寫、要在跑新一輪**之前**寫、
要說明為什麼，而不是讓它從一句假引用長出來。

> 是外部裁決（fable）抓到的。我逐項複驗：v2 的 3.7、`PREDICTION.md` 的處置段、
> 全文 grep 那句話的出處、以及 `PREDICTION.md` 對兩段都會變的事前預測——**全部屬實**。

### 決定：採 B'（驗證，驗不了就落回已預先登記的失敗），但**半新半舊**

- **舊的那一半（已預先登記）**：3.5 判準表第二列寫著「具名失敗、ODT 顯示有 mutation
  → **通過但要記**，這是 2.3 的『派送後無法驗證』」。**B' 的退路是預先登記過的。**
- **新的那一半（本節偏離）**：跨段範圍在驗證成立時**回報成功**，而不是一律拒絕。

理由，且刻意不引用「文件結果是對的」：

1. **A 會拒掉這個動作的主要用途。** 選好幾段做成清單就是 `set-list-unordered`
   存在的理由。
2. **A 不會把說謊的 barrier 修掉，只會把它藏到分類器後面。** 任何被派送前檢查
   誤判的範圍（parser 邊角、未知 tag 路徑）仍然走到現行 barrier，驗一段、報成功
   ——**G3 的缺陷原封不動，只是變成潛伏的**。所以 A 的引擎 diff **並沒有比較小**：
   選 A 一樣得把 readback 修到看得見多 block。
3. **A 的判準要修**：`blockCount > 1` 漏掉「一個 block 兩個 `li`」的情形。
   `:601` 用的是 `blockCount > 1 || itemCount > 1`，兩條都要。

### B' 只有一種寫法是誠實的，另外兩種不是

**不可用之一——用座標重新建立範圍。** containment 的註解（`:3125`–`:3130`）說它
「撐不過劇烈 reflow」，而跨段正是最會 reflow 的情形（轉標題會大幅改變高度）。
用派送前的像素在派送後重選，接不回被改的那兩段，而且**可能假通過**——
`list-contexts.odt` 的鄰居本來就是清單。**這條否決。**

**不可用之二——只把 readback 的每個 block 都檢查一遍。** G3 自己的證據就說明為什麼：
六輪的 `containment` 全是 `{checked: true, held: true}`
（`selectionTop 1807`／`selectionBottom 2154`／`restoreCentre 1981`）。
**只要讀到的東西包含 restore point，containment 就成立**——它在最要緊的情形下
不會失敗。若派送後選取悄悄縮成一段，逐 block 檢查會每一格都過、回報驗證成功，
**G3 的謊言在修法內部原地重建**。依本專案的規矩，不能失敗的檢查比沒有檢查更糟：
**containment 降級為證據，不得當成範圍身分的檢查。**

**可用的那一種——驗「存活下來的原始選取」，並以派送前後文字相等當閘門。**

- 派送**前**用 `getSelectionTypeAndText("text/plain…")`（037 安全的那一支，
  `:3177`–`:3181`）取範圍的純文字；
- 派送**後**讀回的文字必須**逐字相等**——段落層級的格式不改文字內容，所以相等是精確的；
- 不相等、選取為空、或型態不是 TEXT → 回 2.3 的「已派送、驗不了」typed failure。

**這個檢查會失敗**（選取縮掉、跑掉、掉了都抓得到），而且**有不必重編就能製造的紅**：
第二段裡放註腳 → `footnote-apparatus-readback`（`:3293`）；
範圍內任何位置放 as-char 圖 → 型態守門擋下的 `selection-type-not-readable`（`:3282`）。

**基材已經量到了**：G3 六輪的 `selectionBeforeDispatch.text` 都是
`"E1-MULTI-START alpha\n第二段中文 beta"`——**跨段選取的純文字讀取在這顆 artifact 上就是通的。**

### 進 relink 之前必須先跑的三個否證檢查（**全部零 relink**）

三個任一成立就退回 A，而且都能在 `940b7723` 或原生上跑完：

| # | 檢查 | 成立的話 |
|---|---|---|
| 1 | **基材**：`getTextSelection("text/html")` 對一般跨段選取會不會卡、回來的 markup parser 能不能逐 block 列舉 | B' 沒有驗證基材 → **A** |
| 2 | **存活**：派送格式指令之後，選取在**常見**情形下會不會以相同文字存活 | B' 退化成「永遠走退路」，每次多段按下去都回「可能改了，請檢查並復原」——那比 A 乾脆拒絕更糟 → **A** |
| 3 | **undo**：跨段格式派送在這顆 build 上是不是**單步** undo | 2.3 要求的退路訊息（叫使用者 undo）對這一類是不誠實的 → **A** |

**這三個各要自己的預測，且要在 relink 之前跑完。**
把「選錯要付第二次 relink」當成盲賭是我的框架錯誤——這三件事現在就能量。

### 對 5.2 的影響

5.2 寫「兩條路之一」進 relink。裁決指出還有第三種安排：**把選擇放在不重連結的那一層**
（`sdk-worker.js` 與 manifest，5.2 自己列為不重連結），一次 relink 同時帶進拒絕分支與
B' 的驗證，讓兩條預先登記的輪次跑在**同一顆** artifact 上，凍結時再選一條。
那會把不可逆的賭注換成量測後的選擇。**列為選項，未採納**——採納它同樣需要本節這種
明著寫的偏離說明，而且它把 relink 的內容變大。

## 9.8 三個否證檢查跑完了：一三過，**二把 9.7 採用的寫法打斷兩處**（2026-08-15）

原生、零 relink、三臂三輪，**每臂九筆逐格相同**。證據與兩份預測在
[`e2b-crossparagraph/`](../findings/evidence/sdk-e2/discovery/e2b-crossparagraph/PREDICTION.md)。

| 檢查 | 結果 |
|---|---|
| **一 基材** | **過**。跨段選取的 `text/html` 0 ms 返回、630 bytes、**2 個 block**；兩支單段臂各 **1 個**。可逐 block 列舉，而且計數會判別 |
| **三 undo** | **過**，判在文件上。九次都是：派送有套用（跨段兩段、單段一段），**一次 `.uno:Undo` 讓五段的簽章全部回到派送前** |
| **二 存活** | **選取存活了，但相等閘門不成立。斷兩處。** |

### 斷點一：讀回值會在跨段時注入清單裝飾

跨段派送前 `"E1-MULTI-START alpha\n第二段中文"`，派送後
`"    • E1-MULTI-START alpha\n    • 第二段中文"`。

第一輪的對照臂有**我自己設計進去的混淆**（選的是段落內的部分文字，
所以和測試臂差了「一段 vs 兩段」與「部分 vs 整段」兩件事）。
加了 `single-paragraph-whole` 並**先寫預測**，機制拆出來了：
**整段**變成清單項目時讀回值**沒有標記**（`textEqual: true`），而它的 html 是 `items: 1`。
**標記追蹤的是「選取有沒有跨過段落邊界」，不是「有沒有變成清單」。**

於是逐位元相等會在**每一次成功的跨段清單派送**上失敗——正是 B' 存在要驗的情形。
B' 變成永遠走退路，而那是 9.7 自己寫的取消條件。

### 斷點二：部分選取讀回來完全沒有清單結構——**預測與裁決都沒想到**

對照臂的段落在文件上確實已經是清單項目（存檔判讀說是），
它的 html 讀回卻是 `items: 0`、`blocks: 1`。

**所以「驗存活下來的使用者選取」在選取是部分時是偽陰性**——而拖曳出來的範圍
通常就是部分的。

現行 barrier 沒撞上這點，只因為它**丟掉使用者的選取**、用 `.uno:SelectText` 重選整段
——而那正是只選得到一段、因此 G3 會失敗的那支呼叫。
**兩半是同一支呼叫的兩面：整段讀回才誠實，只讀一段才不完整。**

### 斷點二的範圍是我誇大的，**推翻它的是同一輪的資料**

我寫「使用者選取只要是**部分**就是偽陰性」。**錯。**
跨段臂的第二段本來就是部分選到的——fixture 的全文是「第二段中文 beta」，
範圍只取到「第二段中文」——而它三輪都回 `blocks: 2`、`items: 2`。
**跨段選取裡的部分段落帶有完整的清單結構。**

偽陰性只限於**不跨段落邊界**的選取，而那正是現行 `.uno:SelectText` barrier
本來就處理得誠實的情形（A 各臂、G1、G2 全過）。
所以「兩半是同一支呼叫」也跟著溶解。**上面那句過寬的話用刪除線留著**——
那種句子正是之後會被拿來殺掉一個其實殺不掉的寫法的句子。

### 第三輪把最後那格暗的關掉了（`native-round3/`）

`cross-paragraph-partial-head`：範圍從第一段的三分之二處起（切在字中間）
跨到第二段，**兩端都是部分**。讀回 `blocks: 2`、派送後 `items: 2`、
文件上兩段都變、一次 undo 復原，三輪相同。

**所以判別在兩側都成立**：決定讀回值帶不帶 block 結構的是
**選取有沒有跨過段落邊界**，不是覆蓋了多少。
修好的寫法在**最常見的拖曳手勢**上沒有結構性的洞。

## 9.9 修好的 B'：路由在派送前的 block 數上（2026-08-15，第二次裁決）

**決定維持 B'，改的是寫法不是結論。** 第二次裁決的理由記在這裡，
連同它自己指出的翻案條件。

| 派送前 `blocks` | 走哪條 | 為什麼 |
|---|---|---|
| `== 1` | **現行 `.uno:SelectText` barrier，原封不動** | 單段它處理得誠實（48/48 加第二輪全過），而斷點二只發生在這一格——路由讓它根本不走存活選取那條 |
| `>= 2` | **派送 → 讀存活下來的選取 → 身分閘門 → 逐 block 狀態檢查** | 跨段的讀回帶完整結構，兩端都是（第三輪測到） |

**身分閘門跑在 html 讀回值的逐 block 文字上**（v7 改；前一版寫的是純文字
加裝飾正規化，已被實測取代，見下）：

1. **block 數與派送前相等**（縮掉一段就會少一個 block）；
2. **逐 block 的文字前後逐字相等**，文字＝該 `<p>` 內所有 inline 標記
   （`<font>`、`<span>`）串接起來的內容；
3. 不做任何裝飾正規化，**因為 html 序列化把數字放在 `<ol>` 裡、文字保持乾淨**；
4. 抽不出 block、或文字對不上 → typed cannot-verify。

> **v7：這是同一位裁決者對自己前一版寫法的第二次修訂**，觸發它的是我樹裡
> 本來就有的證據——A2 臂在 **wasm artifact 上**的 barrier readback 是
> `<ol><li><p …>E1-LC-ISOLATED <font …><span …>前後都不是清單的段落</span></font></p></li></ol>`：
> **一個編號段落，文字內容裡沒有數字。**
> 前一版要求「量過的裝飾前綴封閉集合」，而第三輪量到編號的裝飾是
> 「    1. 」「    2. 」**逐行遞增**、字串集合無界——那個難題只存在於
> **純文字**序列化。換到 html 之後它整個消失，
> 而且 `set-list-unordered` 與 `set-list-ordered` **驗法完全相同**，
> manifest 上那一對仍然是一對。
>
> **一定要逐 block，不能整個 body 去標籤。** 實測（`--show-body`）：
> `</li>\n<li>` 會在派送後的段落之間留下一個 tab，把單段包進 `<ul><li>` 也一樣，
> 所以整體比對會在**每一次成功的清單派送**上報出差異——正是純文字閘門那個
> 失敗模式。逐 block 抽取沒有那道接縫：五臂三輪十五比十五全部逐字相同。

**逐 block 狀態檢查**：list-on 要 `items == blocks`，list-none 要 `items == 0`，
heading／body 要每一個 block tag 都對。

**這一輪必須帶自己會紅的臂**：例如期望 `ol` 卻派送 bullet。
第一、二輪的不相等讀數已經證明閘門看得到真的位元組，但那不夠。

### ~~未決：編號的裝飾不是常數~~ —— **已結（v7）**

第三輪採樣到 `.uno:DefaultNumbering` 的**純文字**讀回是「    1. 」「    2. 」
逐行遞增，我因此問「要用有界樣式，還是編號乾脆不驗證」。
**那是個假岔路**：兩個選項都預設閘門必須跑在純文字上。第四輪測掉了——
html 的文字節點裡沒有標記數字（`native-round4/`，五臂三輪）。

> **應變條款保留，未啟動**：若哪一天量到 html 裡真的帶標記數字，
> 標記必須驗證成**一段連續遞增的整數**（起始值任意——起始值帶著選取之外的
> 清單脈絡，`set-list-none` 派在五項清單的第 3、4 項上不會從 1 開始），
> 每行最多剝一個**驗證過的**標記，任何結構違反就 cannot-verify 且什麼都不剝。
> **「`set-list-ordered` 乾脆不驗證」兩個世界裡都被否決**：
> 一個永遠不會成功的驗證每筆帶零資訊，是「不會失敗的檢查」的鏡像，
> 本專案的規矩用同一個理由否定兩者。

### 翻回 A 的條件（可檢查，由裁決者訂）

1. ~~跨段而第一段是部分的選取讀不回完整結構~~ ——**第三輪已測，不成立**；
2. ~~裝飾集合封不起來~~ ——**第四輪已測，不成立**（html 裡沒有裝飾要封）。
   ~~取代它的是 genuine 文字經 html 抽取無法逐位元往返~~ ——**第五輪已測，不成立**：
   反向對照（`outline-prose.odt`：選取裡真的以「1. 」開頭、含 `&` `<` `"`、
   行中間有「12.」，派送編號）**逐 block 文字前後逐字相同，三輪三臂全過**
   （`native-round5-misfire/`）。跳脫在兩側一致——閘門要的是**穩定**不是還原；
3. 原生十五格任一在 `940b7723` 上翻掉——**原生只答「核心會不會這樣」，
   wasm 一致性在 artifact 那一輪跑完之前是前提不是結論**；
4. wasm 的 B' 輪裡退路在**常見情形**上觸發 → **A**。

### A 這一側的帳，因為這些證據變差了不是變好

- 檢查三過（一次 undo、九次判在文件上）**移除了 A 最強的潛在論據**
  ——2.3 叫使用者 undo 的那句話對這一類是誠實的；
- 檢查一過移除了「沒有驗證基材」的論據；
- 而 A 原本的缺陷沒被碰到：**說謊的 barrier 仍然活在分類器後面**，
  而且 A 的分類器要吃的正是修好的 B' 拿來路由的**同一個**派送前 block 數。
  **同樣的基材，一個拿去拒絕一個量到正確的操作，一個拿去路由到驗證。**

### 退路，以及被丟掉的那條

**退路＝walk**：收合到存活選取自己的派送後起點，逐段 `SelectText` 走過去，
拿派送前擷取的文字當地圖（邊界行比對前後綴、中間行逐字相等）。
它繞開兩個斷點，代價是「下一段」這組原語沒量過、而且是 N 步延遲。

**丟掉：extend-to-boundaries。** 它同時需要沒量過的端點操作**又**仍然跨邊界、
因此仍然要正規化——被上面兩條同時支配。



## 9.10 第 7 節的執行結果（2026-08-15）

**產品 artifact `572035ac…`（profile `e2-editor-v2`），全部門檻達成。**

| 項目 | 結果 |
|---|---|
| 正向矩陣 | **132 個 run**（22 臂 × 3 輪 × 2 瀏覽器）。21 臂三輪全過，自我紅臂三輪全紅（那是它的通過）。**兩瀏覽器 66 格逐格相同**，連走的路由都相同 |
| negative matrix | **12 列**兩個判準（事前登記的碼 ＋ `<office:body>` 逐位元不變）兩瀏覽器全過 |
| no-op 方程式 | **成立且第一次被量到**：重複派送 revision 1 → 2，`<office:body>` 逐位元不變 |
| forbidden-field | 三個欄位**各送一次**全部 `INVALID_ARGUMENT` 且零 mutation |
| validator 突變 | `analyze_e2b_matrix.py --self-test` 18 項，並實測它自己會紅 |
| 四路清單 | header／manifest／worker／client **各 15 個動作，名稱與 id 全等** |
| 證據綁定 | 全部綁在 `572035ac…`，runner 自帶 attribution 檢查 |

**三個在預測裡明說「沒有依據」的格全部成立**，其中兩個關係到停止條件：
清單轉換與清單中段離開都沒有造成結構損失。
**在這一輪之前本專案從來沒有任何一輪從非基準狀態出發**，
所以「清單切換造成 silent ODT 結構損失」這個停止條件根本燒不起來；
現在燒得起來，而它沒有燒。

### 仍然沒有涵蓋的

- **`set-list-ordered` 沒有派送到「兩段都已經是編號清單」的跨段範圍上。**
  混合狀態那一格涵蓋的是「一段清單 ＋ 一段純段落」。
- H2–H6（縮限 2 不變）。
- **實體指標拖曳仍未量**：範圍是以座標進來的，不是 pointer event。

## 9.11 判定：`GO_TO_E2_C`（2026-08-15）

**產品 artifact `572035ac…`（`e2-editor-v2`），contract v2／abiVersion 2／
15 個動作／跨段處置 `verify-every-block`。**

判定由 `tools/validate_e2_b.py` **從證據重新推導**，不是寫下來的：
artifact 的 hash 從磁碟重算並與每份證據自己記的比對（finding 027）、
逐臂判定由分析器重跑而不是讀摘要、四路清單與 E1-C 的 bundle 一併重查。
**那支 validator 自己也驗過會說不**（改掉 manifest 的 hash、或從 manifest
拿掉一個動作，都會得到 `NOT_YET` 並指出原因）。

依 7.2，`GO_TO_E2_C` 成立。第 9 節的遷移條款也已完成：
`demo-structure` 改接 v2，舊的那支**原封改名保留**為 `demo-structure-discovery`。

### 這個 GO 明確**不**包含的

- **`set-list-ordered` 打在「兩段都已經是編號清單」的跨段範圍上**——沒量過；
- **H2–H6**（縮限 2 不變）；
- **實體指標拖曳**：範圍是以座標進來的，不是 pointer event；
- **標題的大綱參與**：`.uno:StyleApply` 套的是 `Heading_20_1` **樣式**，
  匯出仍是 `<text:p>`、沒有 `text:outline-level`。契約承諾的是樣式，
  從來沒有承諾它會進文件大綱。

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-15 | **v9。第 5 節十四項全部定案。** 上游送出擱置（使用者裁示）之後，把不重連結的項目一次做完：**5.7**（第 6＋10：manifest 從描述變成約束，方向是**交集、只能收窄**——反過來會讓被改過的 manifest 擴大 ABI）、**5.8**（第 11：獨立的 v2 builder 並在寫出 manifest 前 fail closed，export inventory 的檢查 `validate_e1_b.py:126` 已經存在不必發明）、**5.9**（第 14 的 v2 半）、**5.10**（第 7：negative matrix 十列，每列只動一件事，零 mutation 判在 `<office:body>` 逐位元上——那個判準 #50 用過且穩定）、**5.11**（第 2：v1 enum 一個字不動，另開 v2 enum，這樣釘住 v1 的 header test 逐字仍成立）、**5.12**（第 8：新建置變體＋掛既有的 `refuse_unasked_relink` 守衛＋補兩件欠著的 Makefile）。**第 12 項重做為 5.13**：全部視為 B、B 不前進 revision、B 的處置是 **rollback 到 checkpoint 而不是 undo**——而這條可以接受是因為 `_checkpointBeforeSelection()` 落在拖曳那一步，**所以 B 最多只損失那一個結果本來就未知的動作**。這是本規格第一次把損失算出來而不是含糊帶過；代價是第 9 節多一條：格式按鈕必須跟在選取手勢之後。順帶更正 2.3：「host 提示使用者 undo」在現行 shell **不可執行**（`undo()` 自己也走 `_enqueue()`，queue 一擋就被 `EDITOR_NOT_READY` 拒掉）。 |
| 2026-08-15 | **v8。反向對照過了，翻回 A 的條件只剩 wasm 一致性那一條。** `outline-prose.odt` 專門用來坑閘門：選取裡真的以「1. 」開頭、含 `&` `<` `"`、行中間有「12.」，再派送 `.uno:DefaultNumbering`。**逐 block 文字前後逐字相同，三輪三支跨段臂全過。** 真的裝飾形狀活下來（會剝裝飾的閘門會吃掉它），跳脫在兩側一致（閘門要的是穩定不是還原）。**另記一個我自己的錯**：這份 fixture 的第一版錨點在「1. 」**後面**，所以那串形狀根本不在選取裡——它一樣報 identical 3/3，**輸出裡沒有任何東西會透露**，是去讀抽出來的文字才發現的，和 G1 第一版 fixture 同一類。重建後核對 `wrapped-paragraph.odt` 逐位元不變，第二輪證據仍綁得住。 |
| 2026-08-15 | **v7。身分閘門從純文字換到 html 的逐 block 文字（9.9），編號那一格結掉。** 我拿第三輪的「編號裝飾逐行遞增、字串集合無界」去問裁決者要樣式還是要放棄驗證——**那是假岔路**，兩個選項都預設閘門跑在純文字上。推翻它的是我樹裡本來就有的證據：**A2 臂在 wasm artifact 上的 barrier readback，一個編號段落，html 文字內容裡沒有數字**，數字在 `<ol>` 結構裡。第四輪把探針改成留下完整 html 並實測跨段的情形，預測先寫：**五臂三輪，逐 block 文字前後逐字相同，十五比十五**。於是不需要任何裝飾集合、樣式或逐動作正規化表，而且**兩個清單動作驗法完全相同**。另外實測出**一定要逐 block**：整個 body 去標籤不會往返（`</li>\n<li>` 留下 tab），會在每一次成功的清單派送上誤報。**順帶記下我自己第一版數字檢查沒有判別力**——它比對到 body 屬性裡的 `#000080`，而且它找到的每一個數字其實都是 fixture 錨點 `E1-MULTI-START` 裡的 1；分析器現在會先跑四個抽取器對照並在失敗時非零退出。翻回 A 的條件第 2 條因此改寫成「genuine 文字經 html 抽取能不能逐位元往返」，那個反向對照**還沒做**。 |
| 2026-08-15 | **v6。三個否證檢查跑完（9.8），跨段處置維持 B' 但寫法改掉（9.9）。** 檢查一（基材）與三（undo，判在文件上、一次 `.uno:Undo` 復原、九次為九次）**過**；檢查二的相等閘門**被打斷**：跨段讀回會注入清單裝飾，所以逐位元相等會在每一次成功的跨段派送上失敗。我另外報了第二個斷點並**把它的範圍寫得太寬**——「部分選取就是偽陰性」——而推翻它的是同一輪的資料：跨段臂的第二段本來就是部分選到的，卻回 `blocks: 2, items: 2`。**偽陰性只限於不跨段落邊界的選取**，而那正是現行 barrier 已經處理得誠實的一格。第三輪把最後那格暗的關掉：**跨段而且第一段也是部分**（切在字中間）一樣帶完整結構，所以最常見的拖曳手勢上沒有結構性的洞。修好的寫法：**用派送前的 block 數路由**（1 走現行 barrier，>= 2 才走派送後驗證），身分閘門改成「行數＋block 數＋逐行文字相等且最多剝一個量過的裝飾前綴、兩側都正規化」，加逐 block 狀態檢查，並要求該輪自帶會紅的臂。**未決一項**：`.uno:DefaultNumbering` 的裝飾是「    1. 」「    2. 」逐行遞增，**不是常數**，所以「精確位元字串的封閉集合」對編號不成立；已送回裁決者。A 這一側因這些證據**變差**：檢查三過移除了「叫使用者 undo 不誠實」這個論據，而 A 的分類器要吃的正是修好的 B' 拿來路由的同一個 block 數。 |
| 2026-08-15 | **v5。跨段的處置定案為 B'，而且是明著偏離預先登記的那一條（9.7）。** 外部裁決（fable）抓到本規格的第三個假前提：**「派送前拒絕**或**驗證每一段」這個二選一從來沒有被預先登記過**——v2 的 3.7 與 `PREDICTION.md` 的處置段都只寫拒絕一條，「或驗證每一段」是我跑完之後寫 9.5 時加的，而且**引用 3.5 說那裡寫過，全文 grep 只出現在 9.5 自己**。更糟的是我拿「文件結果是對的」當偏離的理由，而 `PREDICTION.md` 在跑之前就預測了兩段都會變——**事前已知的事不能當事後改判準的新理由**，那正是 3.7 決策規則要防的。9.5 的假引用已刪並標註，偏離改為 9.7 明著寫。裁決同時否決了 B 的兩種寫法：**用座標重建範圍永遠不可能誠實**（reflow 接不回，而且鄰居本來就是清單，會假通過），**只逐 block 檢查 readback 會把 G3 的謊言在修法內部重建**（G3 六輪 `containment` 全部 `held: true`——只要讀到的東西含 restore point 就成立，最要緊的情形下不會失敗，依規矩必須降級為證據）。可用的寫法是驗「存活下來的原始選取」＋派送前後文字逐字相等，基材已在 G3 的六輪裡量到。另補三個**零 relink** 的否證檢查（基材／存活／undo），任一成立就退回 A，**且必須在 relink 之前跑完**——「選錯要付第二次 relink」是我的框架錯誤，那三件事現在就能量。A 的判準也修正為 `blockCount > 1 || itemCount > 1`。 |
| 2026-08-15 | **v4。兩件事：G1 那一格關掉了，第 5 節被逐項回到原始碼覆核。** G1 以新 fixture 重跑，兩瀏覽器各三輪通過，加上同一份文件裡的不換行對照臂——**第 3 節八臂現在只剩 G3 失敗，沒有 void**（9.6）。第 5 節原本是從對抗性審查的意見寫的、不是從原始碼重讀寫的，這次逐項覆核：**第 4 項（no-op 的 revision 語意）判為錯誤並撤回**——`SPEC-E1-B:82` 那句是規格原文，finding 022 之後引擎已不再讀前置狀態、成功一律 `+1`，v1 與路線 C 在 revision 上沒有差異；第 1、3 項改寫（worker 有**兩道** gate 而非一道；五個動作現在連結果驗證都到不了，在 `ACTION_SET` 就被擋掉）；並新增第 8–14 項，其中**第 8 項推翻了 3.9 節「那是一次 relink」的說法——產品 objects 沒有 `-DOXSDK_E2_FORMAT_BARRIER`，產品 build 根本沒有把路線 C 編進去**。新增 5.2 節列出唯一一次 relink 必須一起帶進去的東西。 |
| 2026-08-15 | **v1（草擬）。** 形狀由外部裁決訂定：先寫規格、把最小判別輪當第一個預先登錄的里程碑、凍結閘在其後。 |
| 2026-08-15 | **v3。第 3 節閘門已執行，結果記在 9.5。** 落在 3.7 的「只有 G3 失敗」分支：五個動作臂與反向臂兩瀏覽器各三輪全過（判準含「沒被選到的段落逐字未變」），**G3 如預測失敗但文件結果正確**，**G1 判 void——`第三段跨行 gamma` 其實是段落很高不是跨行，同段多矩形這一格仍然是暗的**。過程中三個比較器錯誤全是我的、全靠資料荒謬才抓到，其中一個特別要記：**事後寫的分析器把預先登記的判準悄悄換掉了**（給 G3 `allowed=2` 判成通過，而 `PREDICTION.md` 在 harness 存在之前就寫著那是失敗），**而且偏離的方向讓那一臂變綠**。已改回並在證據裡自陳。閘門的 harness 目前**沒有 Makefile target**，是手動複製進 `dist/` 的——finding 042：改 Makefile 會重連結，等於在閘門跑之前把受測 artifact 換掉；**留到下次刻意 relink 時補**。 |
| 2026-08-15 | **v2。經對抗性審查大幅改寫；被打掉的東西記在這裡，不隱藏。** **（一）G3（原 G2）的判準接錯機制**：v1 要求跨段範圍「以 typed `multiBlock` 拒絕」，但 `multiBlock` 算的是 **barrier 自己建立的**後置條件選取（`probe_engine.cpp:601`），而 barrier 用 `.uno:SelectText` **永遠只選一段**，且該判讀發生在派送**之後**（`:3320`）——跨段輸入**結構上走不到那個分支**。原判準等於在等一個不會發生的拒絕，該臂因此不可否證。已改寫為「會不會靜默地驗證不足」，並附四格判準表。**（二）正向臂證明不了範圍存在**：五個動作都是段落層級的，範圍若建立失敗而退回收合游標，存出的文件仍會完全符合後置條件——**把被測能力關掉，檢查照樣綠**。已補 3.4 的派送前四項與派送後三項，其中「相鄰未選取段落逐字未變」是 v1 完全沒有的。**（三）臂數不足**：v1 只具名測 `StyleApply`（heading）與 `DefaultBullet` 兩個指令，卻用「指令身分會造成差別」當理由——那個理由同樣適用於 `DefaultNumbering` 與 `RemoveBullets`（後者語意是離開清單）。另外 `dispatchSelectionRectangles == 1` 只描述視覺幾何、不等於單段，**同段跨視覺行是第五個未列的暗格**。四臂增為八臂、48 個 run。**（四）G1 的理由外推過頭**：v1 引用原生第三輪說「指令身分會造成差別」，但第三輪問的是「哪個指令毒化**後續選取**」，四個格式指令全部乾淨——那不能推出範圍派送會因指令而異。已改為「參數與期望 tag 都不同、24 筆未涵蓋」。**（五）候選 ABI 穿不過現行 worker 與 client**：worker 的 V1 閘門是 `endsWith("V1")` 字尾比對加寫死的 v1 capability／version、action map 只有 1–10、`internalAction()` 對 11–15 回 0，而**產品 client 要求 `changed === true` ＋ `uno-command-result`**，路線 C 回的是 `changed: null` ＋ `verified-format-readback`——五個動作即使 engine 完成也會被判成 malformed。新增第 5 節逐項列為凍結擋路條件。**（六）產品 worker 不轉發 `formatBarrier`**（診斷 profile 是 builder 另外 patch 的），所以第 3.9 節的產品重跑目前無法判 G3。**（七）typed failure 抄成自然語言**會讓 host 做錯 recovery：多數不是零 mutation 的拒絕，而是「已派送但驗不了」。2.3 已改為兩類並補上實際的 code 與 shape 名稱。**（八）workaround 只有移除條件沒有移除測試**——而且 workaround 還開著時第 3 節一樣會綠。2.4 已改為六步的移除測試，含「修復前必定變紅的對照」。**（九）失敗分支允許兩種互斥語意卻無決策規則**，等於失敗後可以事後挑一條看起來能動的路；3.7 已補決策規則，並要求 collapse-first 另跑一輪。**（十）第 7 節的門檻未訂**，現文不同執行者能用不同測試得到同一個 GO，已明寫為凍結前必須補齊。**（十一）`demo-structure` 沒有遷移條款**，已補為第 9 節並列入 GO。 |

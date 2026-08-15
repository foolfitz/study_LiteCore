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
> host 的訊息必須叫使用者去看文件並在需要時 undo——引擎自己寫的字串就是這樣寫的。
> per-stage 期限只保「stage 不會無限等」，**不保「barrier 一定收場」**。

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
14. **公開型別與 header 測試已經落後現行 v1。** `editor-client.d.ts:7` 只列到
    `set-bold`／`set-italic`，沒有底線與刪除線；`setInlineFormat` 的型別同樣
    只允許 bold／italic（`:64`）；`tests/editor_abi_header_test.cpp:6` 只 assert
    動作 1–8。**現況已經表達不完整的十個 v1 動作**，v2 之前要先補齊。
    另外 `EditorSession` 只有 `setInlineFormat()`、沒有清單／段落的方法
    （`editor-session.js:426`），且固定實例化只接受 v1 的 `NarrowEditorClient`（`:125`）。

### 5.2 唯一一次 relink 要帶什麼進去

finding 042：改 `Makefile` 會重連結。所以下列**必須同一次做完**，
否則就是第二次 relink：

- `src/editor_api.h`／`src/editor_api.cpp`：ABI 版本、外部 ID 11–15 與對應。
- `src/probe_engine.cpp`：**跨段的處置**（3.5／9.5 的兩條路之一）、
  G1 結果導出的範圍限制、以及第 12 項的 revision 決策。
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

**`GO_TO_E2_C` 的具體門檻（含每個動作每個瀏覽器的次數、歸屬欄位、no-op 的 revision 方程式、
negative matrix、forbidden-field inventory、validator 的突變控制）尚未訂定，
必須在凍結之前補齊。** 現在寫「達門檻次數」而不寫門檻，等於不同執行者能用不同測試得到同一個 GO。

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
`verdict.json` 另記 `documentOutcomeCorrect: true`，因為它影響該怎麼修：
**拒絕一個結果正確的操作是有代價的**，而 3.5 已經寫著另一個選項是「驗證所有受影響段落」。

**因此依 3.7 的決策規則**：範圍派送可以進 ABI，但跨段範圍必須**派送前** typed 拒絕、
零 mutation、有自己的 shape 名稱，且該拒絕要另跑一輪；
**或**改成驗證範圍內每一段。**兩條都還沒做，凍結仍被擋著。**

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

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-15 | **v4。兩件事：G1 那一格關掉了，第 5 節被逐項回到原始碼覆核。** G1 以新 fixture 重跑，兩瀏覽器各三輪通過，加上同一份文件裡的不換行對照臂——**第 3 節八臂現在只剩 G3 失敗，沒有 void**（9.6）。第 5 節原本是從對抗性審查的意見寫的、不是從原始碼重讀寫的，這次逐項覆核：**第 4 項（no-op 的 revision 語意）判為錯誤並撤回**——`SPEC-E1-B:82` 那句是規格原文，finding 022 之後引擎已不再讀前置狀態、成功一律 `+1`，v1 與路線 C 在 revision 上沒有差異；第 1、3 項改寫（worker 有**兩道** gate 而非一道；五個動作現在連結果驗證都到不了，在 `ACTION_SET` 就被擋掉）；並新增第 8–14 項，其中**第 8 項推翻了 3.9 節「那是一次 relink」的說法——產品 objects 沒有 `-DOXSDK_E2_FORMAT_BARRIER`，產品 build 根本沒有把路線 C 編進去**。新增 5.2 節列出唯一一次 relink 必須一起帶進去的東西。 |
| 2026-08-15 | **v1（草擬）。** 形狀由外部裁決訂定：先寫規格、把最小判別輪當第一個預先登錄的里程碑、凍結閘在其後。 |
| 2026-08-15 | **v3。第 3 節閘門已執行，結果記在 9.5。** 落在 3.7 的「只有 G3 失敗」分支：五個動作臂與反向臂兩瀏覽器各三輪全過（判準含「沒被選到的段落逐字未變」），**G3 如預測失敗但文件結果正確**，**G1 判 void——`第三段跨行 gamma` 其實是段落很高不是跨行，同段多矩形這一格仍然是暗的**。過程中三個比較器錯誤全是我的、全靠資料荒謬才抓到，其中一個特別要記：**事後寫的分析器把預先登記的判準悄悄換掉了**（給 G3 `allowed=2` 判成通過，而 `PREDICTION.md` 在 harness 存在之前就寫著那是失敗），**而且偏離的方向讓那一臂變綠**。已改回並在證據裡自陳。閘門的 harness 目前**沒有 Makefile target**，是手動複製進 `dist/` 的——finding 042：改 Makefile 會重連結，等於在閘門跑之前把受測 artifact 換掉；**留到下次刻意 relink 時補**。 |
| 2026-08-15 | **v2。經對抗性審查大幅改寫；被打掉的東西記在這裡，不隱藏。** **（一）G3（原 G2）的判準接錯機制**：v1 要求跨段範圍「以 typed `multiBlock` 拒絕」，但 `multiBlock` 算的是 **barrier 自己建立的**後置條件選取（`probe_engine.cpp:601`），而 barrier 用 `.uno:SelectText` **永遠只選一段**，且該判讀發生在派送**之後**（`:3320`）——跨段輸入**結構上走不到那個分支**。原判準等於在等一個不會發生的拒絕，該臂因此不可否證。已改寫為「會不會靜默地驗證不足」，並附四格判準表。**（二）正向臂證明不了範圍存在**：五個動作都是段落層級的，範圍若建立失敗而退回收合游標，存出的文件仍會完全符合後置條件——**把被測能力關掉，檢查照樣綠**。已補 3.4 的派送前四項與派送後三項，其中「相鄰未選取段落逐字未變」是 v1 完全沒有的。**（三）臂數不足**：v1 只具名測 `StyleApply`（heading）與 `DefaultBullet` 兩個指令，卻用「指令身分會造成差別」當理由——那個理由同樣適用於 `DefaultNumbering` 與 `RemoveBullets`（後者語意是離開清單）。另外 `dispatchSelectionRectangles == 1` 只描述視覺幾何、不等於單段，**同段跨視覺行是第五個未列的暗格**。四臂增為八臂、48 個 run。**（四）G1 的理由外推過頭**：v1 引用原生第三輪說「指令身分會造成差別」，但第三輪問的是「哪個指令毒化**後續選取**」，四個格式指令全部乾淨——那不能推出範圍派送會因指令而異。已改為「參數與期望 tag 都不同、24 筆未涵蓋」。**（五）候選 ABI 穿不過現行 worker 與 client**：worker 的 V1 閘門是 `endsWith("V1")` 字尾比對加寫死的 v1 capability／version、action map 只有 1–10、`internalAction()` 對 11–15 回 0，而**產品 client 要求 `changed === true` ＋ `uno-command-result`**，路線 C 回的是 `changed: null` ＋ `verified-format-readback`——五個動作即使 engine 完成也會被判成 malformed。新增第 5 節逐項列為凍結擋路條件。**（六）產品 worker 不轉發 `formatBarrier`**（診斷 profile 是 builder 另外 patch 的），所以第 3.9 節的產品重跑目前無法判 G3。**（七）typed failure 抄成自然語言**會讓 host 做錯 recovery：多數不是零 mutation 的拒絕，而是「已派送但驗不了」。2.3 已改為兩類並補上實際的 code 與 shape 名稱。**（八）workaround 只有移除條件沒有移除測試**——而且 workaround 還開著時第 3 節一樣會綠。2.4 已改為六步的移除測試，含「修復前必定變紅的對照」。**（九）失敗分支允許兩種互斥語意卻無決策規則**，等於失敗後可以事後挑一條看起來能動的路；3.7 已補決策規則，並要求 collapse-first 另跑一輪。**（十）第 7 節的門檻未訂**，現文不同執行者能用不同測試得到同一個 GO，已明寫為凍結前必須補齊。**（十一）`demo-structure` 沒有遷移條款**，已補為第 9 節並列入 GO。 |

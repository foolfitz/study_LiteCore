# SPEC E2-C：段落格式產品驗證（E2 里程碑判定）

> **日期**：2026-08-15  
> **狀態**：**v7**；**第一輪判定＝`E2_STOP_OR_RESCOPE`**（D0 過、D1 23／28、D2～D5 未跑）  
> **前置閘門**：[E2-B](./SPEC-E2-B-paragraph-format-contract.md) 已判
> **`GO_TO_E2_C`**（2026-08-15），產品 artifact `572035ac…`（profile `e2-editor-v2`）  
> **上位規格**：[SPEC E2-000](./SPEC-E2-000-overview.md) 第 7 節——
> E2-C 的職責是「雙瀏覽器、ODT corpus、round-trip、recovery 與產品驗收」，
> 完成訊號是「形成 E2 GO／部分 GO／停止判定」

## 1. 目的

E2-C **不新增 Editor 動作**。它要證明凍結的窄版契約——**十五個動作、
一個 profile、一個 session**——在真實 host 輸入、代表性 ODT、故障復原與較長操作
序列裡仍然 exactly-once、可保存、可解釋，然後對整個 E2 里程碑作判定。

> **2026-08-15 修訂：原文寫「不再擴充 Editor ABI」，而第二輪要動 ABI 版本常數。**
> 兩者不衝突，但原文的措辭不夠精確，所以就地改成「不新增動作」——
> 那才是這條真正守的東西。第二輪把 `OXSDK_EDITOR_ABI_VERSION` 由 2 改成 3，
> **動作列舉一個字不動**；改變的是 `enabled` 這個既有欄位的語意
> （[finding 045](../findings/045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)），
> 而語意也是 ABI 的一部分，所以版本必須動。見 11.1。

與 E1-C 的關係是**平行的一輪，不是追認**。`E1_GO_ODT_EDITOR` 綁在 artifact
`835b453d…`＋殼層 bundle `f9b1a52f…`；E2 的產品是**另一顆** artifact
`572035ac…`。E1-C 量過的 50 格**沒有一格是在 v2 上量的**，所以它們不能被引用成
「v2 也通過了」。這是 [finding 027](../findings/027-r8d-verdict-silently-outlived-its-release.md)
的教訓：判定綁在 artifact 上，不綁在名字上。

## 2. 進場基線

### 2.1 已觀察

- E2-B 交付產品 profile `e2-editor-v2`：contract v2、`abiVersion` 2、**十五個動作**
  （E1 的十個 ＋ E2 的五個）、跨段處置 `verify-every-block`、
  capability `narrow-editor-v2`。
- 132 個正向 run（22 臂 × 3 輪 × 2 瀏覽器）、12 列 negative matrix、no-op 方程式、
  forbidden-field 三欄，全部綁在 `572035ac…`，兩瀏覽器逐格相同。
- 判定由 [`tools/validate_e2_b.py`](../wasm_sdk_probe/tools/validate_e2_b.py)
  **從證據重推**，且該工具實測會說 `NOT_YET`。
- E1-C 的產品驗證跑在 `835b453d…` 上，**沒有任何一格跑在 `572035ac…` 上**。
- E1-C 的 C3 語料五份**完全沒有 `text:list`／`text:list-item`**
  （[SPEC E1-C](./SPEC-E1-C-editor-validation.md) 9.2 從位元組算出來的）。

### 2.2 進場阻擋：**出貨的 v2 profile 上，E1 的十個動作沒有任何殼層到得了**

**已觀察（2026-08-15 量到，host 側，不需要瀏覽器）**：

| profile | 殼層 | 十個 v1 動作到得了幾個 | 擋在哪 |
|---|---|---|---|
| `e2-editor-v2` | `editor-shell/editor-client.js` | **0／10** | `UNSUPPORTED_OPERATION`：它同時要求 capability `narrow-editor-v1` **與** `editorContract.version === 1`，v2 兩個都不是 |
| `e2-editor-v2` | `editor-shell-v2/paragraph-editor-client.js` | **0／10** | `EDITOR_ACTION_UNSUPPORTED`：它的 allowlist 只有五個段落動作 |
| `e1-editor-v1` | `editor-shell/editor-client.js` | **10／10** | —（**對照組**：沒有它，上面兩列證明不了任何事） |

引擎與協定兩層是**完整的**：worker 的 `editorActionV2` 吃十五個動作
（`EDITOR_V2_ACTION_IDS` 展開 v1 的十個再加五個，`sdk/sdk-worker.js:64`），
manifest 也宣告十五個。**洞只在殼層。**

> **E2-B 的四路清單檢查看不到這件事，而且它沒有壞。**
> [`check_e2_b_inventory.py`](../wasm_sdk_probe/tools/check_e2_b_inventory.py)
> 問的是「四份清單有沒有指同一組動作」，它的「client」那一份是**兩個殼層的聯集**。
> 聯集是對的——只是其中一個殼層**接不上這顆 profile**。
> **「四份清單一致」與「host 真的做得到這十五件事」是兩個宣稱，過去只檢查過第一個。**
> 檢查第二個的測試是
> [`editor-shell-v2/tests/manifest-reachability.test.mjs`](../wasm_sdk_probe/editor-shell-v2/tests/manifest-reachability.test.mjs)，
> 它自帶兩個對照（v1 殼層在 v1 profile 上必須到得了十個；沒有人宣告過的動作必須誰都到不了）。
> **它在寫出來的當下是紅的**，紅的內容逐字就是上表第一、二列。

#### 決定：**由 `editor-shell-v2/` 長出十五個動作的產品殼層**（進場工作，零 relink）

- **不動 `editor-shell/`**：它由 E1-C 的 bundle `f9b1a52f…` 逐檔 hash 綁定，
  改它或在它旁邊加檔案都會解除 `E1_GO_ODT_EDITOR`。
- **不改 manifest 去砍掉那十個**。那要重跑 builder → 新 manifest → 新 hash →
  E2-B 的 132 個 run 與 12 列全部斷綁。**manifest 已經承諾了十五個，
  讓殼層追上它，比讓承諾縮回去便宜一個數量級，而且不會丟掉已經量到的東西。**
- **不出兩顆 profile**。一份文件只能開在一個引擎裡；「格式用這顆、粗體用那顆」
  在產品上不成立。
- 新殼層**組合**而不是複製 `ParagraphEditorClient`：五個段落動作原封委派給它
  （路線 C 的 `changed: null` ＋ `verified-format-readback` 規則只有一份），
  十個 v1 動作在新檔案裡自己驗，但**必須有差異測試**把它的接受／拒絕行為
  逐格對上 `editor-shell/editor-client.js`——這一族唯一發生過的漂移
  （underline／strikethrough 進了 `.js` 沒進 `.d.ts`）就是靠沒有人比對而活了兩顆 artifact。

> **這不是擴 surface。** 十五個動作已經在 manifest、worker 與 ABI 裡，
> 而且是 E2-B 判定涵蓋的那顆二進位檔。新增的只有一個 JS 檔案，
> 它不新增任何 `.uno:*`、key code、WASM pointer 或未分類 callback。

**第四條路，對抗性審查指出來的，記在這裡而不是省略掉**：把不可變的
`NarrowEditorClient` 包在一個 facade 後面——facade 對它報 v1 的 manifest 形狀，
再把 `editorActionV1` 轉成 `editorActionV2`。這條路**不必**改凍結檔、不必 relink、
不出第二顆 profile，也**不必有第二份驗證規則**。

**沒有採用，理由是它要對閘門說謊。** v1 客戶端那個
`capabilities.includes("narrow-editor-v1") && version === 1` 的檢查，
存在的目的就是「不要讓一個客戶端跑在沒有量過它的 profile 上」。
facade 讓它以為自己在 v1 上，等於把那個閘門關掉——今天無害（兩邊的十個動作
走同一段引擎程式碼），但**它會在兩邊哪天真的分岔時無聲地繼續通過**，
而那正是這個閘門要抓的一天。複本＋行為差異測試把同一個風險換成
「兩份規則必須逐格同意」，那是會紅的，說謊的 facade 不會。

> **這條路仍然開著。** 如果差異測試的維護成本變得比它擋下的風險高，
> 換回 facade 是一個有理由的決定——但要連同「閘門被關掉了」一起寫進記錄。

#### 但是：**一個殼層不是一個產品**

上面那個決定只解決「有沒有一個客戶端能送出這十五個動作」。
對抗性審查指出，**它本身不構成產品修好了**，還差兩件（2.3、2.4），
在那兩件完成之前，`narrow-editor-v2-client.js` 只是一個**測試用的原始碼模組**。

### 2.3 進場阻擋二：**出貨的 session 在 v2 profile 上根本開不起來**

**已觀察（2026-08-15，host 側）**：`EditorSession`（`editor-session.js`）在
`_openFresh()` 裡建 `NarrowEditorClient`（`:125`），然後 `await this.editor.getState()`
（`:140`）。v2 profile 上那個客戶端拒絕，於是**`open()` 直接失敗**，
session 停在 `recoverable-error`、輸入被封鎖。

| profile | `EditorSession.open()` | |
|---|---|---|
| `e2-editor-v2` | **失敗**，`UNSUPPORTED_OPERATION`，狀態 `recoverable-error` | |
| `e1-editor-v1` | 成功，狀態 `ready` | **對照組** |

`ParagraphEditorSession` **沒有補上這個洞**：它包著一個 `EditorSession`、
讀 `session.document`（`paragraph-editor-session.js:74`），
繞過 `_enqueue`，只在錯誤上加一個 `recovery` 標籤（`:87`）；
它不更新 dirty／content stamp，也不從 checkpoint bytes 重開。

> **所以 D1／D2 承諾的每一件事——一個 session、FIFO queue、選取手勢前的
> checkpoint、rollback、三代上限——在 v2 上目前沒有任何實作。**
> 這比 2.2 嚴重：2.2 是「宣告的東西沒有殼層」，這是
> **「規格要驗的東西沒有實作」**。

**進場工作（列入 3. 的「不重連結」範圍內，純殼層）**：`editor-shell-v2/` 要有一個
**產品 v2 session**，它必須

1. 用 `NarrowEditorV2Client`，兩族動作**走同一個 FIFO queue**；
2. 在選取手勢前寫 checkpoint（E2-B 5.13 的損失計算就建立在這一步上）；
3. 對**每一個派送後失敗**擋下 queue，並以 fresh worker 從 checkpoint bytes 重開；
4. 執行三代上限，達上限回 typed `WORKER_GENERATION_LIMIT` ＋ `requiresPageReload`。

**這四件要有自己的單元測試，而且測的是實作、不是 runner 裡另寫一份復原邏輯。**
runner 自帶復原邏輯而產品沒有，是驗收會通過而產品仍然壞掉的標準作法。

### 2.4 進場阻擋三：**沒有任何產品頁面在用它**

`web/demo-structure-app.js` 仍然 import `ParagraphEditorClient`（`:30`），
工具列只有五個段落動作（`:249`），插入與復原走 Document SDK；
`Makefile` 的 `demo-structure-assets` 原本沒有把新客戶端複製進 `dist/`
（**已補**）。而且那一頁**唯一的指標處理是 `pointerdown` → 放游標**（`:265`），
**沒有拖曳選取**。

> 後果直接打在 D5 上：**「用真實指標拖曳選一段再按格式鈕」在現行產品頁面上
> 做不到**，因為那一頁沒有拖曳。D5 若在別的 harness 頁面上做，量到的就不是
> 產品，而是 harness。

**進場工作**：一個**從 `dist/` 服務**的產品頁面，import 合併後的客戶端與 2.3 的
session，工具列有十五個動作，並且**指標拖曳走的是產品自己的處理器**。
D0 與 D5 都必須跑在那一頁上。

**已完成（2026-08-15）**：`web/e2-editor.html`／`-app.js`，
`tools/run_e2_c_page_smoke.py` 兩瀏覽器 `ok: true`
——開到 `ready`、用頁面自己的指標處理器放游標（各 4 ms）、
用頁面自己的工具列按「標題」（47 ms）、revision 0 → 1。
**合成事件足以證明接線，不足以當 D5 的證據**；D5 那一格要真的 pointer event。

> **順帶抓到一個已經出貨的缺陷**：`demo-structure-app.js` 遷到產品 v2 之後
> 仍然呼叫 `client.placeCaretByClick`，那個方法只在**診斷用**的
> `e2/demo-structure-client.js` 上。所以從那次遷移起，那一頁**每一次點擊都丟
> TypeError**——上一輪檢查過「開得起來」，而開不起來正是它前一次壞掉的方式。
> 已修，並補了通用檢查 `product-page-calls.test.mjs`：把頁面裡
> `client.foo(`／`session.foo(` 的名字抽出來問那個類別有沒有。
> **`node --check` 看不到這種錯**，因為 `client.foo()` 不管 `client` 是什麼
> 都是合法語法。

### 2.5 第二個「宣告了但沒有人執行」的東西：十個繼承動作的 gesture

**已觀察（原始碼層級，2026-08-15）**：v2 manifest 給十個繼承動作的宣告是
`gestures: ["collapsed"]`。builder 這樣寫是**刻意而且誠實的**——
`build_e2_b_profile.py:82` 的註解：範圍派送只對段落動作做過特徵量測，
「宣告一個沒有人量過的手勢，就是 manifest 在宣稱證據沒有的涵蓋」。

worker 在 init 時把十五個動作的 mask 全部推進引擎
（`sdk-worker.js:837`，外部 id 由 `editor_api.cpp:149` 映射成內部 id，
E2-B 的 negative matrix 第 11 列證明這條路是通的）。**但引擎只有一個地方讀
這個 mask**：`routeFormatBarrier()`（`probe_engine.cpp:3298`），
而那是**五個段落動作專用的**路徑。

> **所以十個繼承動作的 gesture 宣告，推進去了、存下來了、從來沒有被讀過。**
> 這與 2.2 是同一類缺陷的第二個實例：**一個沒有人執行的宣告。**
> 5.7 訂 manifest「從描述變成約束」時處理的正是這件事，
> 當時只做到了段落那五個。

**E2-C 的處置——不強制執行，具名記錄，並在 D1 量它**：

- **不在客戶端補強制**。要在客戶端判手勢，客戶端就得在每一個粗體／刪除之前
  先讀一次選取狀態，那是**新增一個 `getSelection` 呼叫點**——而 finding 037／038
  講的正是這種呼叫在某些選取上不會返回。**為了讓一個沒有人量過的宣告成真，
  去新增一個已知會卡死引擎的呼叫點，是拿確定的風險換未知的整齊。**
- **不改 manifest**（要 relink）。
- **D1 必須實測十個動作在範圍選取上的行為**，結果只當**特徵量測**記錄，
  **不當通過條件**——這一版契約宣告的是 collapsed，量到什麼都不改變宣告。
- 產品 host **要用 `gesturesFor()` 做呈現**（停用或標註按鈕），
  不要靠派送失敗來告訴使用者。
- 想讓宣告真的被執行，得等下一次 relink：把 mask 檢查移到十個動作也會經過的
  地方。**列入 E2-C 之後的契約版本，不在本輪。**

### 2.6 已修的殼層缺陷：**沒送出去的失敗會叫 host 回滾文件**

**已觀察並已修（2026-08-15）**：`formatFailureDisposition()` 對任何**沒有帶
barrier 欄位**的錯誤回 `unknown-rollback`，`recoveryFor()` 把它變成 `rollback`。
但客戶端自己丟的 `INVALID_ARGUMENT`（參數寫錯）、`EDITOR_ACTION_UNSUPPORTED`、
以及 capability 閘門的 `UNSUPPORTED_OPERATION`，**都沒有 barrier，也都從來沒有
離開過客戶端**。於是「呼叫端打錯一個參數」的處置變成
**從 checkpoint 重開、丟掉自那之後的所有編輯**。

fail closed 是對的——**但它適用的是「不知道有沒有派送」**。這三個是知道的：

- 客戶端的參數檢查在 `_request` 之前丟；
- worker 的 typed-argument 閘與 manifest 閘都在 `accept()` **之前** return
  （E2-B 9.10 在出貨 artifact 上量過 worker 那半：三個禁用欄位各一次，
  全部 `INVALID_ARGUMENT`，`<office:body>` 逐位元不變）。

**已修**：這三個碼落在 `refused-no-mutation`。**順序刻意排在 barrier 之後**
——若引擎哪天真的帶著 `dispatched: true` 配上這三個碼之一，barrier 贏。
測試同時測常數表與**客戶端真的丟出來的那些錯誤**，因為只測常數表的話，
客戶端改丟別的碼也會通過。

### 2.7 一併繼承的縮限

**從 E2-A 繼承六項**（[SPEC E2-B](./SPEC-E2-B-paragraph-format-contract.md) 2.2）：
`set-paragraph-body` 的後置條件是「不是 heading」；heading 只承諾第 1 級；
readback markup 不是有文件的契約；`changed` 永遠 `null`；不提供前置格式狀態讀取；
第 7 項（只從收合游標派送）已由 E2-B 第 3 節解除。

**從 E2-B 的 GO 繼承四項未涵蓋**（E2-B 9.11）：

| 未涵蓋的 | E2-C 的處置 |
|---|---|
| `set-list-ordered` 打在「兩段都已編號」的跨段範圍 | **列入 D1**，是新增的一格，零 relink |
| H2–H6 | **維持不承諾**（縮限 2 不變），不列入 |
| 實體指標拖曳 | **列入 D5**（人工），這是唯一能拿到真 pointer event 的相位 |
| 標題的大綱參與 | **維持不承諾**，並在第 4.2 節寫成產品語句；**不改 manifest 的 `limits`**（那要 relink） |

**從 E1-C 繼承一條內容軸收窄**（E1-C 9.1）：選取涵蓋某個註腳／尾註引用記號、
而該註腳本文裡有 `as-char` 的 `draw:frame` 時，引擎執行緒會停止回應。根因是
[finding 040](../findings/040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md)，
**上游缺陷、未修、送出擱置**。v2 用的是同一顆 core（`671c848b…`），
**沒有任何理由假設它在 v2 上不會發生**，所以這條收窄原樣繼承，見 9.2。

## 3. 不可退讓的邊界

- 不新增 raw UNO、unoembind、任意 `.uno:*`、任意 key code、WASM pointer 或
  未分類 LOK callback payload。新增能力一律 closed enum。
- ~~**不重連結、不重建任何 artifact。** E2-C 的全部工作在殼層、runner 與判定工具；
  `572035ac…` 與四顆凍結 profile 逐位元不變，每一相位結束後核對。~~
  **（2026-08-15 修訂，見 11.1）** 這一條**約束第一輪，第一輪已經結束**
  （判定 `E2_STOP_OR_RESCOPE`）。**第二輪以一次有計畫的 relink 開場**，
  因為第一輪量到的缺陷（finding 045）**只能靠改引擎修**。
  **仍然不變的**：四顆凍結 profile 與 `572035ac…` 逐位元不動——
  第二輪鑄的是**新的** artifact，不是覆寫舊的。
- 不改 `editor-shell/*.js`，不在它旁邊加檔案。
- **不改 E2-B 的檢查工具**（`check_e2_b_inventory.py`、`analyze_e2b_*.py`、
  `validate_e2_b.py`）。它們會重新產生 `e2-b-summary.json`，那是已發判定的證據；
  E2-C 要新的檢查就寫 E2-C 自己的。
- 不跑會重建凍結 artifact 的 make 目標（`test-e1-c-static` 會拉
  `e1-editor-validation-assets`，因而重建 `e1-editor-v1`——**回歸相位不得用它**）。
- timeout、abort、stale revision、boundary rejection、Worker crash 與 outcome unknown
  皆不自動 retry／replay。
- 瀏覽器結果必須再經 ODT ZIP／XML／anchor 與桌面 LibreOffice 重開驗證；
  canvas 畫面不能取代內容證據。
- 不修改 LibreOffice core。

## 4. 凍結產品範圍

### 4.1 必須成立

- **十五個動作在同一個 session、同一份文件上可用**：E1 的十個（字元左右移動、
  兩向刪除、兩種斷行、粗體／斜體／底線／刪除線）與 E2 的五個（清單三態、
  標題／內文）。
- 每個動作回傳 typed 後置條件，且**兩套後置條件規則不互相污染**：
  v1 的十個仍是 `uno-command-result`／`verified-selection-delete`／
  `documented-callback-*` ＋ `changed` 明確；v2 的五個是 `changed: null` ＋
  `verified-format-readback`（E2-B 5.6：放寬**逐動作**，不是整條）。
- 派送後驗不了時，host 的處置是**回到選取手勢前的 checkpoint**，不是叫使用者 undo
  （E2-B 5.13）；`formatFailureDisposition()` 的三個回答都要有量到的一格。
- 選取手勢（含真實指標拖曳）之後派送格式動作，跨段逐段驗證。
- Boundary rejection 後 `restart-required`、fresh Worker、舊 handle 失效、
  queued mutation 不重播。
- 每個 session 最多三個 Worker generation，達上限以 typed
  `WORKER_GENERATION_LIMIT` ＋ `requiresPageReload` 擋下。

### 4.2 明確不承諾

- **H2–H6。** 承諾範圍是 H1。
- **標題的大綱參與。** `.uno:StyleApply` 套的是 `Heading_20_1` **樣式**，
  匯出仍是 `<text:p>`、沒有 `text:outline-level`。**契約承諾的是樣式**；
  任何「套了標題就會進大綱／目錄」的期待都不在承諾內。
- 清單縮排／階層、自訂樣式、字型／字級／顏色、對齊與行距。
- Redo、line up/down/home/end、表格／圖片／shape 的結構編輯。
- DOCX 與其他格式（屬 E3）；markdown（屬 E4）。
- **註腳本文帶 as-char frame 的文件**（9.2）。
- **任何帶註腳／尾註的段落，段落格式動作一律不支援。**

> **這一條是對抗性審查逼出來的，而且它比我原本寫的寬。** 我原本只排除
> 「註腳本文裡有 as-char frame」那一格，但 E2-B 2.3 早就寫著：
> **段落上有註腳／尾註，收尾就會回 `MUTATION_OUTCOME_UNKNOWN`／
> `footnote-apparatus-readback`**——這與註腳裡有沒有 frame 無關。
> D2 甚至刻意拿一個「註腳沒有 frame」的段落去示範它必須回滾。
> **示範它會失敗、同時把它寫成支援，是自相矛盾的。**
>
> **未解的不一致，具名留著**：manifest 的
> `set-paragraph-heading`／`set-paragraph-body` 的 `limits` **沒有**宣告這一條
> （只有 `heading-level-1-only`、`no-precondition-state`），三個清單動作的
> `limits` 是空的。要讓 manifest 說出來就得 relink，而本規格禁止 relink。
> **處置**：這一條寫在規格與產品 UI 上，並列為下一次 relink 的必帶項目；
> **`E2_GO_PARAGRAPH_FORMAT` 的敘述必須明寫「契約宣告與實際縮限有這一處落差」**，
> 不得只寫在這裡就當成揭露過了。

## 5. 自動測試矩陣

**相位前綴用 `D`，不用 `C`**——E1-C 的相位就叫 C0～C4，兩輪的證據會並排在同一棵樹裡，
同名會讓「C3 過了」變成一句不知道在說哪一輪的話。

數量與項目以本節為準，**正式結果產生後不得放寬**。

### D0：進場與 surface inventory

- 保存 core HEAD／dirty baseline、v2 manifest／export／artifact hash、
  瀏覽器與桌面版本。
- **可達性，而且判準比 host 側那個測試嚴**：
  1. **單一客戶端**——`NarrowEditorV2Client` **一個人**要到得了十五個。
     host 側的 `manifest-reachability.test.mjs` 取三個殼層的**聯集**，
     那對「宣告有沒有人實作」是對的問題，對「產品能不能用」是錯的問題；
     **聯集正是 2.2 那個缺陷之所以躲了一輪的原因，不能拿它當 D0 的判準。**
  2. **跑在 `dist/` 服務出來的檔案上**，不是原始碼樹的檔案。
  3. **比對整個請求信封**：operation、action、`extendSelection`、`enabled`、
     `documentHandle`、`expectedRevision` 逐欄相符，
     不是「有沒有送出去」。
  4. **要拿到真 worker 回來的 typed 成功結果**，不是 stub 的回覆。
  對照組保留兩個（沒宣告過的動作誰都到不了；v1 殼層在 v1 profile 上十個全到）。
- **session 可達性**：2.3 的產品 session 必須在 v2 profile 上 `open()` 到 `ready`，
  對照組是它在 v1 profile 上的行為。
- 產品 profile 不得出現 diagnostic 操作；未知 action、`keyCode`、`unoCommand`、
  `command` 各送一次，全部 fail closed 且 `<office:body>` 逐位元不變。
- **D0 不通過就停止，不跑任何內容 mutation。**

### D1：整合序列（每瀏覽器 3 輪）

一輪 = **一個 session、一份文件**，把兩代動作交錯：

1. click → typed collapsed caret；真實 mutation 前不得重送 click；
2. 插入文字，字元左右移動，Shift 延伸選取；
3. 十個 v1 動作各至少一次，每次驗 revision 與 typed 後置條件，
   **而且每一個都要有自己的錨點與獨立的前後 XML 判準**；
   > **typed 後置條件不足以證明做對了事。** 四個 inline 格式動作回的都是
   > 同一個 `uno-command-result`：**一個把 bold 接到 italic 的映射錯誤，
   > 會回報你要求的 action 名稱、回報同一個 completion，然後改錯屬性。**
   > 所以四個格式各要一個**只有它會動到**的錨點，
   > `enabled: true` 與 `false` 各一次，判準是存出來的 XML 上那個屬性；
   > 兩個 delete 與兩種斷行判在**文字內容**上（少了哪個字、斷在哪裡）。
   > 一次混合序列跑完只存一次檔，**沒有辦法把結果歸屬到單一動作**。
4. 選取手勢（座標範圍）→ 五個 v2 動作各至少一次，收合／單段／跨段三條路由各至少一次；
5. **新增的一格**：兩段**都已經是編號清單**時，跨段派送 `set-list-ordered`
   （E2-B 9.11 的第一項未涵蓋）；
6. 交錯：v2 格式動作之後接 v1 的 delete／bold，驗證 v1 的後置條件**沒有**被
   路線 C 的放寬污染；
7. Undo（走 Document SDK）與 save。
8. **特徵量測，不是通過條件**（2.3）：十個繼承動作在**範圍選取**上派送
   ——至少 `set-bold` 與 `delete-backward` 各一次，單段與跨段各一次。
   記錄實際發生什麼（有沒有派送、revision 動了沒、文件變成什麼樣）。
   **這一項無論結果如何都不影響 D1 的通過與否**，因為這一版契約宣告的是
   collapsed；它的用途是讓下一次 relink 有東西可以依據。
   **不得**因為量到「看起來可以」就把它寫進承諾。

**門檻：兩瀏覽器各 3 輪全過，且兩瀏覽器逐格相同**（E2-B 的 132 個 run 是這樣判的，
不降低）。任何一格出現 silent mutation、重播或 outcome 不明，**立即停止 D2～D5**。

### D2：Recovery 與 no-replay（每瀏覽器）

- stale editor revision、stale document handle：零 mutation。
- structure boundary → `EDITOR_BOUNDARY_UNSUPPORTED`，session 進 `restart-required`
  並拒絕已排隊操作。
- 五個 crash barrier（沿用 E1-C v8）：composing、queued mutation、unsaved local edit、
  checkpointed edit、saved authority。
- **四個處置各要一格，不是只有一格**（4.1 要求三個回答都量到，D2 v1 只寫了一個）：

  | 格 | 怎麼造 | 必須成立 |
  |---|---|---|
  | `refused-no-mutation`（引擎判的） | 帶 as-char 圖的段落上派送 → 派送前路由拒絕 | `dispatched: false`、`<office:body>` 逐位元不變、session 仍 `ready` |
  | `refused-no-mutation`（客戶端判的，2.6） | 傳一個壞參數 | **沒有任何請求送出**、文件與 session 狀態皆不變 |
  | `unknown-rollback` | 人工把錯誤的 barrier 欄位拿掉 | 落在 rollback，**證明 fail-closed 還在**（2.6 的修法不得把它一起關掉） |
  | `dispatched-rollback` | 見下 | 下面那串斷言 |

- **`dispatched-rollback` 這一格的完整斷言**（缺一不可）：
  1. **先做一次會弄髒文件的編輯**，並**確認 checkpoint 真的建立了**
     （`hasCheckpoint`）——沒有 checkpoint 的回滾證明不了回滾；
  2. 選一個**明確涵蓋註腳引用記號**的範圍（不是只選段落的一部分）；
  3. 派送前路由必須是 `range-single`（記錄下來，不是假設）；
  4. 結果必須是 `dispatched: true` **且** `failureShape` **逐字**是
     `footnote-apparatus-readback`；
  5. session 以 fresh worker 從 checkpoint bytes 重開；
  6. **回滾後存出來的文件與 checkpoint bytes 逐位元相同**；
  7. queue 裡的操作沒有重播。

  > **不要拿 E1-C 的 8 ms 當這一格的依據。** 那個數字證明的是
  > 「全選之後引擎還活著」，不是「格式動作會回 `footnote-apparatus-readback`」；
  > 而且 E1-C 的 `note-partial`（**不**涵蓋引用記號）一樣是可用的，
  > 它很可能根本不會觸發註腳裝置那一條。**活著與失敗成某個特定形狀，
  > 是兩件事。**
  > **怎麼造這一格，答案在我自己的樹裡**：用**帶註腳、但註腳本文沒有 frame**
  > 的段落。E1-C 9.1 的四格量過，`footnote-no-frame-full` 是 8 ms 可用的，
  > `note-full`（註腳裡有 frame）才會卡死。**拿錯 fixture 這一格不會失敗，
  > 會讓引擎不回應**，然後這一輪什麼都證明不了。
  >
  > **具體是哪一份哪一個錨點**：`test-docs/e1/paragraph-content.odt` 的
  > `PC-FOOTNOTE`（`web/e1-note-frame-select-app.js:99` 的 case 表）。
  > 會卡死的那一份是 `frame-contexts.odt` 的 `FX-NOTE` 全選，**不要用它**。
  >
  > **為什麼它會落在「派送後」而不是被 B' 的派送前路由擋掉——原始碼層級的推論，
  > D2 必須實測確認**：`routeFormatBarrier()`（`probe_engine.cpp:3273`）在派送前
  > 只做兩件事——finding 037 的型態守衛與 gesture 判定——**它讀了 html 卻不看
  > 註腳裝置**（`footnoteApparatus` 只在 `:3494` 被判，那是收尾階段）。
  > 所以帶註腳的選取會**通過**派送前路由、被派送出去，再由收尾判成
  > `MUTATION_OUTCOME_UNKNOWN`／`footnote-apparatus-readback`。
  > **這正是這一格需要的形狀**（dispatched = true），但在 D2 實測到之前它是推論。
  > 若實測發現它其實在派送前就被擋掉（`dispatched: false`），
  > 那 D2 這一格要換機制，**不是把判準改成接受零 mutation**。
- 每個 session 最多三個 Worker generation，第四次以 typed 錯誤擋下。

### D3：ODT corpus（每瀏覽器每份至少一次）

**六份**——E1-C 的五份 ＋ `list-contexts.odt`：

| ID | 目的 | 允許編輯位置 |
|---|---|---|
| `l0-t1` | 純文字、CJK 與 grapheme | 指定普通段落 anchor |
| `l0-t2` | style／table／image／comment 保存 | 非結構普通段落 |
| `l0-t3` | 22 頁長文件 | 首／中／末 anchor |
| `l1-review-odt` | comment／tracked-change 保存 | 未修訂普通段落 anchor |
| `l4-stress-100` | 100 頁含圖片 | 固定頁面文字 anchor |
| **`list-contexts`** | **清單內容軸與清單目標格** | 見下面的 L1–L8 表，**不只是 `E1-LC-ISOLATED`** |
| **`list-split`（新，待建）** | **清單中段離開**（L7 需要三項的清單，現有語料沒有） | `E2-LS-MID` |

> **第六份不是本輪想加的，是三天前就寫下的義務。** E1-C 9.2 的原文：
> 「**清單動作要進出貨契約之前，必須先補語料或依 9.1 的形式具名排除**」。
> 清單動作**現在就在**出貨契約裡（v2 的 11、12、13）。語料已經補好了
> （`test-docs/e1/list-contexts.odt`，2026-08-13），E2-C 是它第一次真的被用到的地方。
每份驗證：原始 required anchors、新增／刪除後置條件、ZIP CRC、XML、禁止內容未出現、
桌面 LibreOffice 重開與 PDF 匯出。**不重生成或改寫任何既有 corpus source bytes。**

#### D3 的清單目標格：**必須打在清單上，不是打在清單旁邊**

對抗性審查抓到 v1 的 D3 有一個致命的空轉：唯一允許的編輯位置是
`E1-LC-ISOLATED`，而那**刻意是一個前後都不是清單的普通段落**；
`E1-LC-BETWEEN` 又被排除。於是「D3 驗過清單動作」實際上是
**在沒有清單的段落上跑清單動作**，而 8.1 那個 `list: present` 斷言
會因為 ZIP 裡別處有清單而照樣通過。

**所以 D3 的清單那一半改成預先登記的目標格，每一格要綁「錨點 ＋ 派送前狀態」**：

| 格 | 錨點 | 派送前狀態 | 動作 | 後置條件 |
|---|---|---|---|---|
| L1 | `E1-LC-ISOLATED` | 普通段落，前後都不是清單 | `set-list-unordered` | 該段成為 `<text:list-item>`，鄰居不變 |
| L2 | `E1-LC-END` | 普通段落 | `set-list-ordered` | 同上，編號串 |
| L3 | `E1-LC-BULLET-TWO` | **已在無序清單中** | `set-list-none` | 該項離開清單，同串其餘項不變 |
| L4 | `E1-LC-NUMBER-TWO` | **已在有序清單中** | `set-list-none` | 同上 |
| L5 | `E1-LC-BULLET-ONE` | **已在無序清單中** | `set-list-ordered` | 轉換，不是新開一串 |
| L6 | `E1-LC-NUMBER-ONE` | **已在有序清單中** | `set-list-ordered` | **重複派送**：結構不得改變 |
| L7 | `E2-LS-MID`（`list-split`） | **三項清單的中間那項** | `set-list-none` | 前後兩段仍各自成串，或依實測記錄成 typed 結果 |
| L8 | `E1-LC-BETWEEN` | **兩側都是清單的普通段落** | `set-list-unordered` | 合併與否**都可以接受**，但**必須是預先寫下的那一個**；量到什麼就是什麼，不得事後選 |

> **L7 需要一份新語料，因為現有的沒有一份能表達它。** `list-contexts.odt`
> 的兩串清單**各只有兩項**，兩項的清單拿掉一項不會分裂。所以新增
> `test-docs/e2/list-split.odt`（**新位元組，不改寫任何既有 corpus**，
> 與 E1-C 新增 `list-contexts` 時同一條規矩），一串三項，中間那項是 `E2-LS-MID`。
> **沒有這一份，L7 就是一格永遠跑不到的宣稱**——正是 034／035／037／038 那一類。

> L6 與 L7 是停止條款直接指著的兩格（E2-000 第 10 節：
> 「清單切換造成 ODT 結構 silent loss」）。**L8 不是通過條件**，
> 它是把「相鄰清單會不會併」這件事從印象變成量測；
> E1-C 之所以留著 `E1-LC-BETWEEN`，就是為了有地方量它。

**盤點要綁到動作的目標錨點與前狀態，不是只綁文件層級的「有沒有清單」。**

### D4：Bounded lifecycle 與回歸

- 每瀏覽器 10 個獨立 edit → save → reopen session；每頁不超過三個 generation，
  runner 自行 reload 新頁。
- 每次結束 Worker／handle 歸零；記錄 process tree、PSS／RSS、WASM heap、latency。

  > **「無連續成長」不是判準，這是對抗性審查點名的**：一次 GC 凹陷就能讓
  > 一條真的在漏的曲線變成「不連續」，而 PSS／RSS 的雜訊可以解釋任何結果。
  > 改成可否證的數字：
  >
  > | 量什麼 | 怎麼量 | 門檻 |
  > |---|---|---|
  > | 靜止點 | 每個 session `close()` 之後**等到沒有 in-flight 請求**再取樣，同一輪固定 3 秒後再取一次，取**較小值** | — |
  > | 殘留 Worker | 取樣時 `dispose()` 後的 worker 數 | **0**，第 10 輪也是 0 |
  > | 殘留 handle | session 自報 | **0** |
  > | WASM heap | 10 輪的線性回歸斜率 | **≤ 2 MB／session**，且第 10 輪絕對值 ≤ 首輪 ＋ 20 MB |
  > | 瀏覽器 PSS／RSS | 同上 | **≤ 8 MB／session**；R7 的單頁 50 代量到 +22.4 MB／block 且判為回收延遲，本輪 10 輪的門檻據此訂在同數量級 |
  >
  > **取不到記憶體數字時的處置也要先寫**：Firefox 拿不到 PSS 就記 `notValidated`
  > 並**只**以 worker／handle 歸零與 WASM heap 判定，**不得**因為量不到就當作通過。
- 回歸：R6 release、R7-B／C／D、R8-D、E1-A、E1-B、**E2-A、E2-B 的靜態目標**，
  before／after workspace preflight 必須通過。
  **不得跑 `test-e1-c-static`**（它會重建凍結的 `e1-editor-v1`）；E1-C 側改跑
  唯讀的 `check_e1_c_bundle_intact.py` 與 `test-e1-c-frozen-guard`。

### D5：人工驗收最小化（每瀏覽器一個集中 run）

只在 D0～D4 全過之後開始：

1. **真實指標拖曳**選取一段（跨段一次、單段一次），再按格式鈕
   ——這是 E2-B 9.11 第三項未涵蓋唯一能關掉的方式，自動化拿不到 `isTrusted` 的
   pointer event；
2. 既有 Fcitx5 Chewing 在 v2 profile 上 collapsed caret commit 一次，
   再以選取取代一次（E1-C 的 IME 證據綁在 `835b453d…`，**不能引用成 v2 也過了**）；
3. 真 Ctrl+C／Ctrl+V 一次；
4. save 之後由 machine validator 檢查 anchor 數與桌面重開。

人工無法取得時可判部分 GO，**不為湊 GO 反覆要求 operator 操作**。

## 6. Evidence contract

```text
findings/evidence/sdk-e2/e2-c-validation/
  baseline/preflight-before.json
  baseline/preflight-after.json
  inventory/profile.json
  inventory/reachability.json
  browser/<browser>/<round>/
  recovery/<browser>/
  corpus/<browser>/<fixture>/
  lifecycle/<browser>/
  manual/<browser>-pointer-drag.json
  manual/<browser>-chewing.json
  regression/summary.json
  summary.json
```

- 每一份證據自帶它跑在哪顆 artifact 上（`wasmSha256`／`loaderSha256`／`workerSha256`
  ＋**殼層 bundle digest**，見下），判定工具**重算磁碟上的 hash 再比對**，
  不採信寫下來的（finding 027）。

> **綁定必須有第四個雜湊，而 v1 的規格漏掉了它。** E2-C 要證明的東西
> **有一半在殼層**——2.2 的客戶端、2.3 的 session、2.4 的產品頁面。
> 只綁 wasm／loader／worker 三個雜湊，等於允許那三樣在判定發出之後被改掉，
> 而 `E2_GO_PARAGRAPH_FORMAT` 仍然是綠的。
> **E1-C 已經學過這一課**：它的現行綁定是**四個**雜湊，第四個就是
> 殼層 bundle `f9b1a52f…`。
>
> **所以 E2-C 要有自己的殼層 bundle**（`e2/editor-shell-v2-bundle-v1.json`），
> 涵蓋**產品入口點可傳遞到達的每一個 JS 模組**與它們在 `dist/` 的複本：
> `narrow-editor-v2-client.js`、產品 session、產品頁面的 app 模組、
> 以及它們 import 的 `sdk/`、`input/` 模組。
> 驗證方式沿用 E1-C：`available - included - excluded` 必須為空，
> **在旁邊加一個檔案也會讓它紅**。
> D1～D5 的每一份結果都要記這個 digest，`validate_e2_c.py` 要重算它。
- 每次失敗 attempt 獨立保存不覆寫；每筆結果標 `observed`／`inferred`／`reused`／
  `notValidated`。
- 判定由 `tools/validate_e2_c.py` **從證據重推**，且該工具必須實測會說 `NOT_YET`
  （改一個 hash、拿掉一格，都要指出原因）。

## 7. 執行順序與停止點

順序固定為 **進場工作（2.2 客戶端 ＋ 2.3 session ＋ 2.4 產品頁面）
→ 凍結 `e2/validation-matrix-v1.json` → D0 → D1 → D2 → D3 → D4 → D5**。

- **三件進場工作全部完成之前不跑任何 D 相位。** 只做完 2.2 就開跑，
  量到的是一個沒有 session、沒有頁面的客戶端，而 D1／D2 的每一條
  都需要那兩樣。
- **矩陣沒凍結之前不跑 D0**（9.1）。
- D0 不過就停止，不跑內容 mutation。
- D1／D2 觸發 silent mutation、重播或 outcome 不明時立即停止並建立編號 finding。
- D3 required ODT 有 silent 內容／結構損失時停止。
- D4 未通過不得要求人工驗收；人工不能推翻 machine stop。

## 8. 判定

**`E2_GO_PARAGRAPH_FORMAT`**：D0～D4 全部通過；D5 兩瀏覽器各一份 trusted 證據
（或有同 artifact 的明確 `reused` 說明）；七份 ODT 皆桌面 round-trip；recovery、
no-replay、generation 上限、回歸與 workspace 保護成立；**不需要任何禁止 surface**；
且判定敘述**明寫 4.2 那一處契約宣告與實際縮限的落差**。

**`E2_PARTIAL_GO_PARAGRAPH_FORMAT`**：**只有**下面 8.0 的表列出來的格才可能落在這裡。

**`E2_STOP_OR_RESCOPE`**：其餘全部。保存失敗 bytes／trace 並建立編號 finding。

### 8.0 判定表：**每一格失敗都指定一個判定，事前訂**

對抗性審查指出 v1 的三個判定**不是全函數**——D1 的普通功能失敗、桌面重開失敗、
回歸失敗、D4 資源失敗都不屬於任何一類，而「單一非必要 corpus」在跑之前
**沒有指定哪一份是非必要的**。留白等於把判定權交給跑完之後的自己。

| 失敗在哪 | 判定 |
|---|---|
| D0 任何一項（可達性、session 開不起來、diagnostic surface、forbidden field） | **STOP** |
| **manifest 宣告的任何動作或手勢**在 D1／D3 失敗 | **STOP**——見下 |
| D1 的兩瀏覽器逐格不一致 | **STOP** |
| D1 第 8 項（範圍派送特徵量測） | **不影響判定**（2.5，它本來就不是通過條件） |
| D2 四個處置格任何一個 | **STOP** |
| D2 的 crash barrier／generation 上限 | **STOP** |
| D3 的 L1–L7 任何一格 | **STOP** |
| D3 的 **L8**（兩側都是清單） | 量到什麼記什麼；**與預先寫下的不同才是 STOP** |
| D3 的桌面重開或 PDF 匯出 | **STOP** |
| D4 資源門檻 | **STOP**；取不到記憶體數字 → `notValidated` ＋ **PARTIAL** |
| D4 回歸任一項 | **STOP** |
| **D5 的真 IME 那一項**（單一瀏覽器） | **PARTIAL** |
| **D5 的實體拖曳那一項** | **PARTIAL**（它關的是 E2-B 已具名的未涵蓋格，不是契約承諾） |
| operator 完全不可得 | **PARTIAL** |

> **為什麼「宣告的動作失敗」不能是 PARTIAL。** PARTIAL 的定義是「安全縮限並
> 以 capability／manifest 明示」，而 E2-B 7.1 要求縮限落在 manifest 的
> `limits`／`gestures` 上、不是只有 UI。**本規格禁止改 manifest**（要 relink），
> 所以一個已宣告的路由失敗之後，**沒有任何合法的方式把它縮限掉**——
> 硬要縮就得動 manifest，而動 manifest 會把 E2-B 的綁定一起弄斷。
> 因此那一類只有 STOP，然後由下一版契約決定要不要縮。
>
> **PARTIAL 只保留給事前就宣告在承諾之外的東西**（D5 的人工項、
> 拿不到的量測），不保留給任何契約內的失敗。

### 8.1 判定前的必要輸入：語料內容軸盤點

**任何判定之前，必須跑
[`tools/inventory_corpus_axes.py --check`](../wasm_sdk_probe/tools/inventory_corpus_axes.py)，
並把該次語料的內容軸盤點與盲區清單一併寫進判定**（E1-C 9.2 訂的規矩，原樣適用）。

E2-C 的套件宣告放在**新的 `e2/content-axis-suites.json`**，**不是**加進
`e1/content-axis-suites.json`；跑的時候必須明寫 `--suites` 與 `--output`：

```
python3 tools/inventory_corpus_axes.py \
    --suites e2/content-axis-suites.json \
    --output ../findings/evidence/sdk-e2/e2-c-validation/baseline/content-axes.json \
    --check
```

> **為什麼不能用預設值**：這支工具的預設 `--output` 是
> `findings/evidence/sdk-e1/baseline/content-axes.json`，那是 **E1 的證據**；
> 而且 E1-C 判定證據 `editor-validation-v2/summary.json` 裡**逐字收著這支工具的
> stdout**（靜態相位的輸出）。E2-C 用預設值跑一次，就等於在 E1 的證據上寫字。
> **這正是本輪已經踩過一次的那個坑**（`validate_e1_c.py` 掛進靜態檢查改寫了
> 兩個證據檔），第二次要在規格裡就擋掉。

套件必須把本規格用文字寫的宣稱改寫成會失敗的斷言：`list` 與 `list-item`
**present**（否則清單動作又是在沒有清單的語料上驗收）、`footnote` 與 `endnote`
**absent**（否則 9.2 的收窄理由不成立，見下）。

**已先量過（2026-08-15，六份的 roll-up）**，六個斷言全部成立：
`list` 2、`list-item` 4、`footnote` 0、`endnote` 0、`heading` 126、
`frame-as-char-in-paragraph` 1。

> **但這幾個數字要照它們本來的大小讀。** 清單軸**只有 2 個 `text:list` 與
> 4 個 `text:list-item`，而且全部來自 `list-contexts.odt` 一份**。
> 「list present」聽起來像涵蓋，實際是六份裡有一份、共兩串。
> D3 因此只能支持「清單動作在**帶清單的真實文件**上不破壞結構」，
> **不能**支持「清單動作在各種清單構造上都成立」——巢狀清單、
> 混合編號、清單裡的表格這些格在這個語料裡是 0，
> 要收就得補語料，不能靠重跑。這一句是本規格對 D3 效力範圍的界定，
> 不是待辦。

> 理由不是流程潔癖。034、035、037、038 是同一種失敗：**不是矩陣有一格沒跑，
> 是矩陣沒有這條軸，而且沒有人看得出它不在。**

### 8.2 這個判定不會涵蓋的內容軸

**與 E1-C 9.1 同一條，原樣繼承**：選取涵蓋某個註腳／尾註的引用記號、而該註腳本文裡
有 `text:anchor-type="as-char"` 的 `draw:frame`——在這個組合上，選取之後的讀回
不會返回，只有重啟 worker 能復原。

根因是上游缺陷（[finding 040](../findings/040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md)：
`IdlesLockGuard` 等一個 Emscripten build 永遠不會設的條件），**上游送出擱置中**，
所以**這條收窄在上游修好之前是永久的**。

**D3 的六份語料裡 `footnote`／`endnote` 都是 absent**（8.1 的斷言會盯著），
所以這個組合在本輪語料裡不可能出現——**這是覆蓋範圍之外，不是被證偽的結果。**

## 9. 實作檔案

本輪新增（預定）：

- `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js`（2.2 的產品殼層）
- `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.d.ts`
- `wasm_sdk_probe/editor-shell-v2/tests/manifest-reachability.test.mjs`（**已建立**）
- `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-client.test.mjs`（**已建立**）
- `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js`（2.3 的產品 session，**已建立**）
- `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-session.test.mjs`（**已建立**）
- `wasm_sdk_probe/web/e2-editor.html`／`-app.js`（2.4 的產品頁面，**含拖曳選取**，**已建立**）
- `wasm_sdk_probe/editor-shell-v2/tests/product-page-calls.test.mjs`（**已建立**）
- `wasm_sdk_probe/tools/run_e2_c_page_smoke.py`（接線煙霧測試，**已建立且兩瀏覽器通過**）
- `wasm_sdk_probe/web/e2-c-validation.html`／`-app.js`（D0～D4 的 harness）
- `wasm_sdk_probe/e2/editor-shell-v2-bundle-v1.json`（第 6 節的殼層綁定）
- **`wasm_sdk_probe/e2/validation-matrix-v1.json`（凍結矩陣，見下）**
- `wasm_sdk_probe/test-docs/e2/list-split.odt`（L7 用，新位元組）
- `wasm_sdk_probe/tools/run_e2_c.py`、`tools/validate_e2_c.py`

### 9.1 凍結矩陣：判準要在檔案裡，不在散文裡

E1-C 有 `e1/validation-matrix-v2.json`，E2-B 有預先登記的門檻；
**v1 的本規格兩個都沒有**，於是「各至少一次」「兩瀏覽器逐格相同」
「無連續成長」「required ODT」這些話**要等跑完之後由判定器去解釋**
——而判定器是我跑完之後寫的。E2-B 已經因為這個順序踩過一次
（分析器悄悄換掉了預先登記的判準）。

**`e2/validation-matrix-v1.json` 要在 D0 之前寫好並凍結**，內容：
每一格的 id、重複次數、比較投影（哪些欄位參與「逐格相同」）、
artifact 與殼層 bundle 的雜湊、每一格的判準（oracle）、
以及**每一格失敗時對應 8.0 表的哪一列**。

**`validate_e2_c.py` 的自我測試不得只有「改一個雜湊」與「拿掉一格」**
（那是 v1 寫的，遠弱於判定本身）。**每一個會影響判定的述詞都要有突變測試**：
XML 錨點、回滾的位元組相等、兩瀏覽器相等、no-replay、語料軸、
資源門檻、L1–L8 的每一條後置條件。**改任何一條判準都必須看到它變紅。**

本輪修改（預定）：

- `wasm_sdk_probe/Makefile`（`test-e2-c-static`、dist 複製規則）
- `wasm_sdk_probe/e2/content-axis-suites.json`（**新檔**，`E2-C-D3` 套件；
  **不動 `e1/` 那一份**，理由見 8.1）
- `specs/SPEC-E2-000-overview.md`（第 7 節接上 C 的規格連結）

**不修改**：`editor-shell/*.js`、E2-B 的任何檢查工具、任何 profile 的位元組。

## 9.5 執行結果

### 9.5.1 D0（2026-08-15）

**兩瀏覽器各一輪，九格全過，而且兩邊的比較投影對十五個動作逐格相同。**
證據 `findings/evidence/sdk-e2/e2-c-validation/d0/`（README 是英文，依 AGENTS.md）。

| 格 | 結果 |
|---|---|
| `d0-inventory` | 四個 baseline 雜湊與磁碟一致，宣告動作集合與凍結矩陣一致 |
| `d0-reachability-single-client` | **15/15**，**一個客戶端**在真引擎上，逐欄比對整個請求信封 ＋ 逐類 typed 後置條件 |
| `d0-reachability-control-undeclared` | 拒絕，零派送 |
| `d0-session-opens` | `ready`，`clientReplacements: 1`（2.3 的接縫真的被用到了） |
| `d0-no-diagnostic-surface` | `editorActionV1` → `UNSUPPORTED_OPERATION` |
| `d0-forbidden-keycode`／`-unocommand`／`-command` | 三個各 `INVALID_ARGUMENT`，`<office:body>` 逐位元不變 |
| `d0-unknown-action` | `EDITOR_ACTION_UNSUPPORTED`，零派送，`<office:body>` 不變 |

**分析器自己也驗過會說不**：11 個突變全部變紅，其中兩個是方向相反的
——「delete 接受路線 C 的形狀」與「段落動作回 v1 的 completion」。

> **順帶修掉一個量錯東西的計數器**：第一版數「所有請求」，而中間夾著兩次存檔，
> 於是一個根本沒派送的動作報 `2`。**一個測量了別的東西的數字，比沒有數字更糟。**
> 改成只數 `editorActionV2`。

### 9.5.2 D1 前置探針：**收合游標上的 inline 格式，文件位元組不會動**（2026-08-15）

寫 D1 的 28 格之前先量一件事，因為對抗性審查要求的判準有可能根本不可能滿足。

**兩瀏覽器逐項相同：**

| | 量到什麼 |
|---|---|
| 收合游標上派送 `set-bold`／`set-italic` | `changed: true`、revision +1、`uno-command-result` |
| 同一次派送之後的 `<office:body>` | **與派送前逐位元相同** |
| 之後在該游標提交的文字 | 落在帶 `fo:font-weight="bold"`／`fo:font-style="italic"` 的 span 裡 |
| 同一個動作打在**範圍**上 | 文件會變（特徵量測，契約沒宣告這個手勢） |

**三件事因此定下來：**

1. **游標上的格式是真的**——它是待用的打字屬性，效果在「接下來打的字」上。
2. **這裡的 `changed: true` 不等於「存出來的文件變了」。** 引擎回報變更、revision
   前進，而 `<office:body>` 逐位元不變。**這不是 finding 022 的形狀**（022 是
   stale cache 對一個什麼都沒做的動作回報成功，這裡確實有事情發生），但兩者近到
   必須把差別寫下來：**inline 格式在收合游標上的 `changed: true`，意思是引擎接受了
   命令且自身狀態前進，不是文件位元組移動了。E1 的契約一直是這個意思，只是從來
   沒有寫出來。**
3. **D1 對四個 inline 格式的判準因此改成**：在游標上派送 → 提交一個該動作專屬的
   標記 → 該標記所在的 span 必須帶那個屬性（`-false` 的格則必須不帶）。
   這**留在契約宣告的手勢裡**，而且仍然逐動作可歸屬——那正是審查要的性質。

> **凍結矩陣已在 D1 執行之前修訂**，八個格各帶一個 `amended` 欄位指向這份證據。
> **矩陣可以在跑之前改，不能在跑之後改**；這一次是前者，而且理由是量出來的：
> 原本的判準在契約宣告的手勢下沒有任何一輪能滿足，凍著它等於凍了四個必敗的格。

### 9.5.3 D1 撞到一個出貨缺陷：[finding 045](../findings/045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)

**D1 的四個 `d1-set-*-false` 格在現行 artifact 上不可能通過，而理由不是判準寫錯。**

`set-bold`／`set-italic`／`set-underline`／`set-strikethrough` 的 `enabled` 布林值
**沒有被送到引擎之外**：`probe_engine.cpp:3034` 把它存進 `gEditorUnoOption`，
`:3036` 派送的是**不帶參數**的 `.uno:Bold`，而 core 的 slot 宣告是
`Toggle = TRUE`（`svx/sdi/svx.sdi:832,838`）。實測：全新引擎、全新文件、純文字
游標上派送 `set-bold(enabled: false)`，之後打的字**是粗體**，兩瀏覽器逐字相同。

**這是 [finding 030](../findings/030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)
缺陷一的同一個形狀**，030 修了兩個清單命令、四個 inline 格式沒跟著修。

**依 8.0 的判定表，這是 STOP 那一列**（manifest 宣告的動作失敗）。

**不得把那四格的判準改成「接受粗體」讓它變綠。** 判準沒有錯——
它問的正是契約承諾的東西。

#### 外部裁決（fable，2026-08-15）：**先判 STOP，量兩件，再一次 relink**

裁決推翻了我寫在這裡的兩個前提（兩個都已在
[finding 045](../findings/045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)
就地更正）：

- **~~「四個選項是平行的」~~**：D1 **已經跑完**，而 8.0 是**預先登記**的。
  所以每一個選項都**從 STOP 開始**——relink 不能把這一輪變回不是 STOP，
  因為矩陣的 baseline 綁著 `572035ac…`，換 artifact 重跑**定義上就是新的一輪**。
  真正還活著的決定只有「下一次 relink 帶什麼、什麼時候做」。
- **~~「縮限也要 relink」~~**：`build_e2_b_profile.py` 是**打包器不是連結器**，
  而且**沒有任何檢查釘住 manifest 的位元組**。所以那句話是錯的——
  但縮限仍然不該單獨做（理由見 045）。

**裁決的處置**：

1. **現在**：本輪依 8.0 判 `E2_STOP_OR_RESCOPE`；
   同時就地標註 `E1_GO_ODT_EDITOR` 的涵蓋範圍（這四個動作只驗過「開啟」方向）
   ——**標註，不是撤銷**。
2. **relink 之前先量兩件**：045 的原生探針（參數形狀已由原始碼推導出預測）、
   以及 `d1-body-collapsed` 的序列二分。
3. **一次有計畫的 relink**，帶完整佇列（四個參數字串、`d1-body-collapsed` 的修法
   若在引擎側、4.2 的註腳 `limits` 債、2.5 的 gesture mask 執行債），
   新契約版本 v3、新 builder 與新 profile 目錄。
4. `e1-editor-v1` 可分割，之後單獨決定。

**為什麼不現在 relink**：`d1-body-collapsed` 是同級的 STOP 而機制未明。
`PLAN-E2-B-relink-and-freeze.md` 自己寫過——**「P1 完成才能 relink。
漏一項就是第二次 relink」**，而在 `wasm-build-not-reproducible` 之下，
第二次 relink 是這棵樹裡最貴的東西。

> **順帶必須一起看的兩件事**（同一份 finding）：這四個動作的 `changed` 是
> `probe_engine.cpp:2085` **寫死的字面值**，而收合游標上的派送**根本不動
> `<office:body>`**。合起來的意思是：**`changed: true` 在這裡既不代表文件變了，
> 也沒有任何東西看過文件。** 出貨的 E1 契約走同一段程式碼，
> E1-C 之所以沒抓到，是因為它驗 revision 與 typed 後置條件、
> **沒有任何一格去存檔看那段文字變成什麼**。

### 9.5.4 D1 的執行結果（2026-08-15）：**23／28，五格系統性地紅**

三輪 × 兩瀏覽器跑完。**兩瀏覽器的比較投影 81 個項目逐項相同——連紅的那幾格都相同。**
所以這五格不是 flake，是兩個獨立瀏覽器各三次給出同一個答案。

| 紅的格 | 通過輪數 | 原因 |
|---|---|---|
| `d1-set-bold-false`／`-italic-`／`-underline-`／`-strikethrough-false` | 兩瀏覽器各 0/3 | **[finding 045](../findings/045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)**，見 9.5.3 |
| `d1-body-collapsed` | 兩瀏覽器各 0/3 | **未解**，見下 |

**通過的 23 格包含**：四個 inline 格式的「開啟」方向（各自的錨點、各自的標記）、
兩個 delete（段落恰好少一個字，而且是原文刪掉一個字得到的）、
兩種斷行（分段：block 數 +1 且全文文字守恆；換行：`<text:line-break/>` 在、block 數不變）、
三個清單動作與標題在收合游標上、標題在 range-single 與 range-cross 上（兩段都驗）、
**`set-list-ordered` 打在兩段都已編號的跨段範圍**（E2-B 9.11 四個未涵蓋裡的第一個，
**現在關掉了**）、以及交錯格（段落動作之後的 delete 與 bold 仍各自滿足 v1 的後置條件，
路線 C 的放寬沒有外洩）。

#### `d1-body-collapsed`：**派送前拒絕，零 mutation，原因未解**

`set-paragraph-body` 在 `E2-D1-BODY-TARGET`（一個標題段落）的收合游標上，
六次全部在派送前被 finding 037 的型態守衛擋下：

```json
{"failureShape": "routing-selection-not-readable", "dispatched": false,
 "route": "collapsed", "preBlocks": 0}
```

兩件事要講精確：

- **`dispatched: false`＝什麼都沒送出去**，這是乾淨的拒絕形狀，不是 outcome unknown。
- **那個 payload 裡的 `route: "collapsed"` 是預設值，不是觀測值。**
  這個 shape 只在「選取矩形非空」那條分支裡被設定，而那條分支**在指派 route 之前就
  return 了**。所以那個欄位講的是 struct 的初值。**不可以讀成「引擎把它判成收合」。**

### 9.5.6 `d1-body-collapsed` 已二分到底：**它量的是 harness，不是產品**（2026-08-15）

前綴二分（為此在 harness 加了 `?prefix=N`）把界線壓在 15 與 16 之間：
前 15 格通過、加上第 16 格失敗。第 16 格是 `d1-heading-collapsed`。
**兩格就能重現**：`d1-heading-collapsed` → `d1-body-collapsed`，其他都不跑。

這與稍早一個「兩格通過」的探針矛盾，而差別在**收合游標是怎麼形成的**：

| 派送前的游標怎麼來的 | 結果 |
|---|---|
| `selectRange(p, p)`（零寬範圍）——**這個 harness 一直以來的作法** | **`EDITOR_FORMAT_SELECTION_NOT_READABLE`**，`dispatched: false` |
| `click` 之後輪詢到引擎確認收合——**產品頁面的作法** | **通過**，`verified-format-readback` |

同 artifact、同錨點、同前置動作，各一輪。

**兩個後果，第二個比較難看：**

1. **這一格不擋 relink。** 它不是需要進下一顆 artifact 的引擎缺陷，
   而是 [finding 043](../findings/043-fn-select-para-leaves-the-shell-in-selection-mode-and-the-next-lok-range-selection-is-silently-dropped.md)／049
   那一族——barrier 收尾還原選取，下一個零寬 `selectRange` 繼承到那個狀態
   ——而**產品自己的游標路徑踩不到**。
2. **D1 第一輪整輪都是用產品不會用的手勢驅動的。** 27 格的游標是
   `selectRange` 形成的。這不會讓它們的結果變成假的（它們就是在講那個手勢），
   但這一輪**沒有量到產品自己的路徑**——**與 2.2 記的是同一個錯誤，低一層**。

**第一輪的紀錄照原樣留著。** 矩陣在 D0 之前凍結、而且它沒有規定游標怎麼形成；
現在改 harness 重跑就是**跑完之後改判準**，那正是凍結要防的那一件事。
「**游標要照產品的方式形成**」這條進第二輪的矩陣，
連同一格把這裡量到的差別釘住的新格。

### ~~9.5.6 未解~~ 以下是二分之前的紀錄，保留

**已經量過，而且是跟著序列走、不是跟著錨點走**（同日、同 artifact、同語料）：

| 探針 | 結果 |
|---|---|
| 這個錨點上單獨派送 `set-paragraph-body` | **成功**；派送前讀到的選取型態是 `none`、0 個矩形 |
| 隔壁錨點上單獨派送 `set-paragraph-heading` | 成功 |
| **隔壁先標題、再這裡內文**，同一份文件 | **成功**——兩格的序列重現不了 |

所以它只在 D1 那個**更長的**序列跑過之後才失敗（前面十九格，含 inline 格式、
清單動作、跨段範圍）。這同時排除了「這個錨點特別」與「前一個段落動作弄壞了它」。

~~**下一個該看的鄰居是 finding 043／049**……下一步是把 D1 的序列二分。~~
**已做，見上面 9.5.6**——鄰居猜對了，但「兩格重現不了」這個結論是錯的：
重現不了是因為那個探針用了**全掃描**、而 D1 用**局部掃描**，
兩者在派送前留下的選取狀態不同。**真正的變數是游標怎麼形成的。**

> **判定影響**：依 8.0，這一格也是 STOP（宣告過的動作失敗）。
> 但它與 045 不同——**045 已經知道機制、也知道兩條修法都要 relink；
> 這一格連機制都還沒查清楚**，所以它先是一個待查項，不是一個待裁決項。

### 9.5.5 第一輪判定：**`E2_STOP_OR_RESCOPE`**（2026-08-15）

**由 [`tools/validate_e2_c.py`](../wasm_sdk_probe/tools/validate_e2_c.py)
從證據重推，不是寫下來的**（finding 044 記的就是寫下來的判定怎麼與證據脫節）。
輸出在 `findings/evidence/sdk-e2/e2-c-summary.json`。

| | |
|---|---|
| 判定 | **`E2_STOP_OR_RESCOPE`** |
| 觸發的 STOP 格（5） | `d1-set-bold-false`／`-italic-`／`-underline-`／`-strikethrough-false`（finding 045）、`d1-body-collapsed`（機制未明） |
| 未跑的相位 | D2、D3、D4、D5 |
| baseline 四個雜湊 | 全部從磁碟重算並與凍結矩陣相符 |
| 兩瀏覽器逐格比對 | D0、D1 皆相同 |

**判定工具自己驗過會說別的**：它的自我測試把 8.0 的判定表逐格走過——
沒有失敗但還有相位沒跑 → `NOT_YET`（**不是 GO**）；全部跑完沒失敗 → GO；
只有 PARTIAL 格失敗 → PARTIAL；STOP 格失敗 → STOP；
矩陣沒宣告過的格 → STOP。**只到得了一個答案的判定器不是在判定。**

> **自我測試的第一版是我寫錯的**：它想用「把失敗的格從矩陣刪掉」來走到 GO 那條
> 分支，但那不等於那些格通過了——**矩陣沒宣告的格是 unknown，而 unknown 是 STOP**。
> 工具是對的、測試是錯的，這個方向的錯是好的那一種。

**這一輪不會因為之後修好而變成 GO。** 矩陣的 baseline 綁著 `572035ac…`，
換 artifact 重跑**定義上就是新的一輪**（新的凍結矩陣、新的 D0～D5）。

### 9.5.7 第一輪的一個判準與 harness 對不上（2026-08-15，對抗性審查抓到的）

矩陣的 `d1-characterisation-range-inherited` 寫著「單段與跨段各一次」
（規格第 5 節 D1 第 8 項也這樣寫），而 harness 的
`rangeAt(client, y)` **起訖用同一個 y**（`web/e2-c-d1-app.js`）——
**那一格從來沒有做過跨段的範圍。**

它量到的是：`set-bold` 在**單段**範圍上 6/6 成功、
`delete-backward` 在範圍上 6/6 回 `EDITOR_STATE_UNAVAILABLE`。**那兩件事是真的**，
只是覆蓋範圍比判準寫的窄。

**處置：**

- **第一輪的紀錄照原樣留著**，這一節就是它的更正——不改矩陣（跑完不改判準）。
- **繼承動作在第二輪維持 collapsed-only**：要放寬宣告得先有跨段的量測，
  而現在沒有。
- 第二輪的矩陣要**分成兩格**（單段一格、跨段一格，各自的錨點），
  而且**帶文件判準**——第一輪那格只記 typed 結果，沒有任何一格去看存出來的文件。

> **這一類錯誤在本輪出現兩次**（另一次是 9.5.6 的游標手勢），形狀相同：
> **判準寫的是一件事，harness 做的是另一件，而輸出裡沒有任何東西會透露。**
> 兩次都是別人看出來的，不是我。

### 9.5.8 D2 第一次跑就掉出四件事（2026-08-15）

D2 是打失敗路徑的相位，寫在 relink 之前是外部審查的要求。**第一次跑就證明那個
要求是對的**——四件，兩件是產品／契約的，兩件是我自己的。

| | |
|---|---|
| **`STALE_REVISION` 被判成 `unknown-rollback`** | **真缺陷，已修。** 它是 `requireRevision()`（`probe_engine.cpp:3857`）在動作 switch 之前發出的，**零 mutation**；叫 host 回滾等於為了「呼叫端傳錯 revision」丟掉自 checkpoint 以來的全部編輯。與 2.6 同一類。**殼層改動，不需要 relink** |
| **空段落不是派送前拒絕** | **與 E2-B 2.3 的表對不上。** 那張表寫「空段落 → 派送前拒絕 → 沒有發生」；出貨 v2 上實測是 **`EDITOR_FORMAT_POSTCONDITION_FAILED`、`dispatched: true`、`postcondition-not-met`、`preBlocks: 0`**——它派送了。**尚未追根因，也還沒開 finding**：先記在這裡，因為「文件寫的處置」與「實際的處置」不一致，host 會照文件做錯的 recovery |
| 我的 harness：`EditorSession.save()` 回的是 `{bytes,…}` 不是 ArrayBuffer | 每一次 snapshot 都靜靜產出空的 base64，零 mutation 那幾格會因為「沒有文件可比」而失敗 |
| 我的 harness：兩格拿錯 fixture | 在**標題**上 delete 不是結構邊界；在**沒有註腳的文件**上找不到註腳失敗。**兩格都回綠，而且什麼都沒量到**——正是規格自己警告過的那個陷阱 |

**另外記一件在挑 fixture 時量到的事**：帶 as-char frame 的段落**沒辦法用掃描定位**
——定位它需要的正是 finding 037 的守衛要擋掉的那次讀取。
**一個你navigate不到的拒絕，是一個你量不到的拒絕。**

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-15 | **v10。D2 harness 寫好並第一次執行（9.5.8）**：掉出四件，兩件是產品／契約的（`STALE_REVISION` 的處置——已修；**空段落不是派送前拒絕，與 E2-B 2.3 的表對不上**——未追根因），兩件是我自己的 harness 缺陷（`save()` 的回傳型別、兩格拿錯 fixture 而回綠）。**這證實了「D2 要在 relink 之前寫」那個要求是對的。** |
| 2026-08-15 | **v9。新增第 11 節：第二輪從一次有計畫的 relink 開場。** 第 3 節「不重連結」與第 1 節「不再擴充 ABI」**就地修訂**——前者約束第一輪（已結束），後者措辭改成「不新增動作」（ABI 版本要動，動作列舉不動）。**contract version 與 capability 刻意不動**：worker 對 `abiVersion` 的精確比對才是在跑的身分守衛，動那兩個字串會讓新 profile 沒有殼層到得了，那正是 2.2。第二輪綁**五個**雜湊（加 manifest 自己）。 |
| 2026-08-15 | **v8。`d1-body-collapsed` 二分到底（9.5.6）：它量的是 harness 不是產品。** 零寬 `selectRange` 形成的游標在格式 barrier 之後會被型態守衛拒絕，而產品頁面用的 `click`＋確認輪詢不會。**因此它不擋 relink**（fable 的 Premise E 據此解除），但也因此**D1 第一輪整輪都是用產品不會用的手勢驅動的**——第一輪紀錄照原樣留著（跑完不改判準），「游標照產品方式形成」進第二輪矩陣。 |
| 2026-08-15 | **v7。第一輪判定 `E2_STOP_OR_RESCOPE`（9.5.5），由 `validate_e2_c.py` 從證據重推。** 外部裁決（fable）推翻了 9.5.3 的兩個前提——「四個選項是平行的」（D1 已跑完，8.0 是預先登記的，所以每條路都從 STOP 開始）與「縮限也要 relink」（builder 是打包器，且沒有檢查釘住 manifest 位元組）；兩處已就地更正，處置定為「先判 STOP → 量兩件 → 一次 relink 帶完整佇列」。**relink 的時機由 `d1-body-collapsed` 決定，不是由 045 決定**——漏一項就是第二次 relink。 |
| 2026-08-15 | **v6。D1 三輪 × 兩瀏覽器執行完畢（9.5.4）：23／28 通過，兩瀏覽器投影 81 項逐項相同。** 五格系統性地紅——四格是 finding 045，一格（`d1-body-collapsed`）是派送前的型態守衛，機制未解。順帶把 D1 分析器的自我測試改成「突變必須改變判定」而不是「突變必須讓它變紅」——只能在綠證據上跑的自我測試，會在最需要它的時候失效。 |
| 2026-08-15 | **v5。D1 撞到 finding 045（9.5.3）**：四個 inline 格式動作把 `enabled` 丟掉、派送 toggle，所以 `d1-set-*-false` 四格在現行 artifact 上不可能通過。依 8.0 這是 STOP，而修與縮限兩條路都要 relink——**待使用者裁示**。同時修掉三個我自己的判準缺陷（編輯目標改用尾端 token 認段落、每一格用自己的 before 圖、before 圖要在建立手勢**之前**存）。 |
| 2026-08-15 | **v4。D1 前置探針（9.5.2）。** 收合游標上的 inline 格式**不會動到文件位元組**，效果在之後提交的文字上；`changed: true` 在這裡的意思是「引擎接受且狀態前進」，不是「文件變了」。凍結矩陣的八個 inline 格式格因此**在 D1 執行之前**改判準。順帶把 runner 參數化（`--page`／`--namespace`）並補上探針自己的 artifact 歸屬。 |
| 2026-08-15 | **v3。D0 執行完畢，兩瀏覽器全過（9.2）。** 進場三件工作在此之前已完成，凍結矩陣 `e2/validation-matrix-v1.json`（75 格）、殼層 bundle `b01d77da…`、以及 L7 需要的 `test-docs/e2/list-split.odt` 也都就位。D0 的分析器自我測試 11 個突變全紅並掛進 `make test-e2-c-static`。 |
| 2026-08-15 | **v2。對抗性審查（codex）提了 16 項，全部處理過：15 項改寫規格或程式碼，1 項（重用 v1 客戶端的 facade）判為可行但不採用，連同否決理由寫進 2.2。這一版與 v1 差很多。** 最重的三項都是同一種錯：**我把「有一個能送出動作的客戶端」當成了「產品修好了」。**（1）v1 說新客戶端是「產品殼層」，但**沒有任何產品頁面在用它**，asset 目標也沒複製它（已補），而且 `demo-structure` **沒有拖曳選取**，所以 D5 的「真實指標拖曳」在產品頁面上做不到——新增 2.4。（2）**出貨的 `EditorSession` 在 v2 profile 上根本開不起來**（`:125` 建 v1 客戶端、`:140` 等它的 `getState`），`ParagraphEditorSession` 也補不上，**於是 D1／D2 承諾的 session、queue、checkpoint、rollback、三代上限在 v2 上沒有任何實作**——新增 2.3，並列為進場工作。（3）**判定只綁三個雜湊**，而 E2-C 要證的東西有一半在殼層；E1-C 早就學過要綁第四個——第 6 節改成要有 E2 自己的殼層 bundle。其餘：**PARTIAL 的定義原本會逼我去改凍結的 manifest**（縮限必須落在 `limits`／`gestures` 上，而本規格禁止 relink），所以宣告過的動作或手勢失敗一律 STOP，新增 8.0 完整判定表；**D3 原本在「沒有清單的段落」上驗清單動作**（唯一錨點 `E1-LC-ISOLATED` 前後都不是清單），改成 L1–L8 八個綁前狀態的目標格，並發現 L7 需要三項清單而現有語料**一份都沒有**，新增 `list-split.odt`；**D1 原本用 typed completion 當判準**，但四個 inline 格式回同一個 `uno-command-result`，映射錯了也會綠，改成逐動作錨點＋XML 判準；**D2 的四個處置只寫了一格**，補齊並把 `dispatched-rollback` 的斷言逐條寫死（含「先弄髒、確認 checkpoint 真的存在」）；**D4 的「無連續成長」不可否證**，換成斜率與絕對值門檻；**沒有凍結矩陣**，新增 9.1；**4.2 漏掉「任何帶註腳的段落都不支援」**（E2-B 2.3 早就寫著），補上並具名 manifest 沒宣告這一條的落差。另修一個真缺陷（2.6）：客戶端自己丟的 `INVALID_ARGUMENT` 會被判成 `unknown-rollback`，**呼叫端打錯參數的處置變成丟掉自 checkpoint 以來的全部編輯**。並補記第四條被否決的路（facade 重用 v1 客戶端）與否決理由。上位規格 [E2-000](./SPEC-E2-000-overview.md) 第 6 節的 no-op 條文同日就地修訂——`changed: null` 與它牴觸，而在此之前沒有任何條文說過話。 |
| 2026-08-15 | **v1 草擬。** 進場前先量了一件沒有人量過的事：**出貨的 v2 profile 上，E1 的十個動作沒有任何殼層到得了**（v1 殼層被自己的 capability＋version 閘擋掉，v2 殼層的 allowlist 只有五個），而**四路清單檢查看不到它**——那個檢查的「client」是兩個殼層的**聯集**，聯集裡有一個接不上這顆 profile。測試連同兩個對照組已建立且**當下是紅的**。因此本規格把「補上十五個動作的產品殼層」訂為**進場工作**而不是 D 相位的一部分，並寫明否決的另外兩條路（改 manifest 砍動作＝重建 artifact＋斷掉 132 個 run 的綁定；出兩顆 profile＝一份文件開不在兩個引擎裡）。相位前綴改用 `D` 以免與 E1-C 的 C0～C4 在同一棵證據樹裡同名。D3 語料六份，第六份 `list-contexts` **是 E1-C 9.2 在 08-13 就寫下的義務**（「清單動作要進出貨契約之前，必須先補語料或具名排除」）現在到期。E2-B 9.11 的四項未涵蓋各自有處置：跨段全編號進 D1、實體拖曳進 D5、H2–H6 與大綱參與維持不承諾。 |

## 11. 第二輪：一次有計畫的 relink 之後重跑

### 11.1 為什麼第二輪必須從 relink 開場，而第一輪禁止它

第一輪的邊界（第 3 節）寫「不重連結」，而那是對的——**第一輪要證的是那顆已經存在
的 artifact**。第一輪跑完之後，情況變了：

- 第一輪判 **`E2_STOP_OR_RESCOPE`**（9.5.5），五個 STOP 格；
- 其中四個是 [finding 045](../findings/045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)
  ——**`enabled` 根本沒被送到 core**，而那只能改引擎；
- 第五個（`d1-body-collapsed`）已查明是 harness 的手勢，**不需要引擎修法**（9.5.6）。

**所以第二輪的第一個動作就是那次 relink。** 執行順序、佇列與風險在
[`PLAN-E2-C-relink-v3.md`](../handoff/PLAN-E2-C-relink-v3.md)，
**那份是計畫不是規格**；規格這一節定的是**範圍與身分**。

### 11.2 第二輪改變什麼、不改變什麼

| | |
|---|---|
| **新 artifact** | `e2-editor-v3`，新的 build 與 dist 目錄。**`572035ac…`（v2）與四顆凍結 profile 逐位元不動** |
| **ABI 版本** | `OXSDK_EDITOR_ABI_VERSION` 2 → **3**。**動作列舉一個字不動**；變的是 `enabled` 的語意 |
| **contract version 與 capability** | **不動**（維持 2 與 `narrow-editor-v2`）。真正在跑的身分守衛是 worker 在 init 時對 `abiVersion` 的**精確比對**（`sdk-worker.js:810-818`）——新舊兩顆 build 在 manifest 上分得開，而且**分不開就跑不起來**。動那兩個字串會讓 worker 與兩個客戶端都認不得新 profile，那正是 2.2 的缺陷 |
| **殼層** | **一個位元組不動**。`editor-shell-v2/` 與 `e2/editor-shell-v2-bundle-v1.json` 維持原樣，第一輪證據的身分因此仍然可重驗 |
| **第一輪的證據** | **原封保留**，不覆寫。第二輪寫到自己的命名空間（`e2-c-validation-v3/`） |
| **E2-B 對 v2 的判定** | **仍然為真**，但**不再描述產品**（finding 027 的形狀），所以要在 v3 上重新建立 |

### 11.3 第二輪的綁定是**五個**雜湊，不是四個

第一輪綁 wasm／loader／worker／殼層 bundle。**第二輪要加第五個：`sdk-manifest.json`
自己的 sha256。**

理由是這一輪改的東西恰好都在那個檔案裡：`abiVersion`、`limits`、`gestures`。
而 finding 045 已經記過**沒有任何檢查釘住 manifest 的位元組**——
第一輪那樣還可以說「manifest 只是描述」，第二輪不行，
**因為 manifest 現在會決定引擎執行什麼**（gesture mask 是 init 時從它推進去的）。

### 11.4 第二輪的矩陣要在它自己的 D0 之前凍結

`e2/validation-matrix-v2.json`，與 v1 的差異至少四處：

1. baseline 換成 v3 的**五個**雜湊；
2. **游標一律照產品的方式形成**（click ＋ 確認輪詢）——第一輪 27 格用了產品不會
   用的手勢，而矩陣沒規定過（9.5.6）；
3. 新增一格把 9.5.6 量到的 `selectRange` 差別釘住；
4. 新增**帶文件判準**的範圍格（單段與**真的跨段**）——第一輪的特徵量測格
   宣稱「單段與跨段各一次」，而 harness 起訖用同一個 y，**從來沒有跨段過**（9.5.7）。

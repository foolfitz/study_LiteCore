# SPEC E2-C：段落格式產品驗證（E2 里程碑判定）

> **日期**：2026-08-15  
> **狀態**：v1 草擬；**尚未執行**，判定尚未成立  
> **前置閘門**：[E2-B](./SPEC-E2-B-paragraph-format-contract.md) 已判
> **`GO_TO_E2_C`**（2026-08-15），產品 artifact `572035ac…`（profile `e2-editor-v2`）  
> **上位規格**：[SPEC E2-000](./SPEC-E2-000-overview.md) 第 7 節——
> E2-C 的職責是「雙瀏覽器、ODT corpus、round-trip、recovery 與產品驗收」，
> 完成訊號是「形成 E2 GO／部分 GO／停止判定」

## 1. 目的

E2-C **不再擴充 Editor ABI**。它要證明 E2-B 凍結的 v2 契約——**十五個動作、
一個 profile、一個 session**——在真實 host 輸入、代表性 ODT、故障復原與較長操作
序列裡仍然 exactly-once、可保存、可解釋，然後對整個 E2 里程碑作判定。

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

### 2.3 第二個「宣告了但沒有人執行」的東西：十個繼承動作的 gesture

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

### 2.4 一併繼承的縮限

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
- **不重連結、不重建任何 artifact。** E2-C 的全部工作在殼層、runner 與判定工具；
  `572035ac…` 與四顆凍結 profile 逐位元不變，每一相位結束後核對。
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

## 5. 自動測試矩陣

**相位前綴用 `D`，不用 `C`**——E1-C 的相位就叫 C0～C4，兩輪的證據會並排在同一棵樹裡，
同名會讓「C3 過了」變成一句不知道在說哪一輪的話。

數量與項目以本節為準，**正式結果產生後不得放寬**。

### D0：進場與 surface inventory

- 保存 core HEAD／dirty baseline、v2 manifest／export／artifact hash、
  瀏覽器與桌面版本。
- **可達性**：manifest 宣告的十五個動作，十五個都要有殼層到得了；
  自帶兩個對照（v1 殼層在 v1 profile 上十個全到；沒宣告過的動作誰都到不了）。
- 產品 profile 不得出現 diagnostic 操作；未知 action、`keyCode`、`unoCommand`、
  `command` 各送一次，全部 fail closed 且 `<office:body>` 逐位元不變。
- **D0 不通過就停止，不跑任何內容 mutation。**

### D1：整合序列（每瀏覽器 3 輪）

一輪 = **一個 session、一份文件**，把兩代動作交錯：

1. click → typed collapsed caret；真實 mutation 前不得重送 click；
2. 插入文字，字元左右移動，Shift 延伸選取；
3. 十個 v1 動作各至少一次，每次驗 revision 與 typed 後置條件；
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
- **第六個 barrier，本輪新增：`dispatched-rollback`。** 造一個「派送出去但驗不了」
  的格式動作，確認 `formatFailureDisposition()` 回 `dispatched-rollback`、
  host 依 5.13 回到 checkpoint，且**回滾後的文件與 checkpoint bytes 逐位元相同**。
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
| **`list-contexts`** | **清單內容軸與孤立的清單動作錨點** | `E1-LC-ISOLATED`（前後都不是清單） |

> **第六份不是本輪想加的，是三天前就寫下的義務。** E1-C 9.2 的原文：
> 「**清單動作要進出貨契約之前，必須先補語料或依 9.1 的形式具名排除**」。
> 清單動作**現在就在**出貨契約裡（v2 的 11、12、13）。語料已經補好了
> （`test-docs/e1/list-contexts.odt`，2026-08-13），E2-C 是它第一次真的被用到的地方。
> `E1-LC-BETWEEN`（兩側都是清單）**刻意不當作允許編輯位置**——那一格是留給
> 合併行為的量測，不是產品驗收。

每份驗證：原始 required anchors、新增／刪除後置條件、ZIP CRC、XML、禁止內容未出現、
桌面 LibreOffice 重開與 PDF 匯出。**不重生成或改寫任何既有 corpus source bytes。**

### D4：Bounded lifecycle 與回歸

- 每瀏覽器 10 個獨立 edit → save → reopen session；每頁不超過三個 generation，
  runner 自行 reload 新頁。
- 每次結束 Worker／handle 歸零；記錄 process tree、PSS／RSS、WASM heap、latency。
  只要求無連續成長與無 zombie。
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

- 每一份證據自帶它跑在哪顆 artifact 上（`wasmSha256`／`loaderSha256`／`workerSha256`），
  判定工具**重算磁碟上的 hash 再比對**，不採信寫下來的（finding 027）。
- 每次失敗 attempt 獨立保存不覆寫；每筆結果標 `observed`／`inferred`／`reused`／
  `notValidated`。
- 判定由 `tools/validate_e2_c.py` **從證據重推**，且該工具必須實測會說 `NOT_YET`
  （改一個 hash、拿掉一格，都要指出原因）。

## 7. 執行順序與停止點

順序固定為 **進場工作（2.2 的殼層）→ D0 → D1 → D2 → D3 → D4 → D5**。

- 進場工作沒完成前不跑 D0：可達性測試是紅的，D0 只會重複說一次同一件事。
- D0 不過就停止，不跑內容 mutation。
- D1／D2 觸發 silent mutation、重播或 outcome 不明時立即停止並建立編號 finding。
- D3 required ODT 有 silent 內容／結構損失時停止。
- D4 未通過不得要求人工驗收；人工不能推翻 machine stop。

## 8. 判定

**`E2_GO_PARAGRAPH_FORMAT`**：D0～D4 全部通過；D5 兩瀏覽器各一份 trusted 證據
（或有同 artifact 的明確 `reused` 說明）；六份 ODT 皆桌面 round-trip；recovery、
no-replay、generation 上限、回歸與 workspace 保護成立；且**不需要任何禁止 surface**。

**`E2_PARTIAL_GO_PARAGRAPH_FORMAT`**：十五個動作的核心成立，但單一瀏覽器的人工項、
單一非必要 corpus、或某一條路由只能安全縮限。限制以 capability／UI 明示。

**`E2_STOP_OR_RESCOPE`**：文字重複／漏失、格式動作造成 ODT 結構 silent loss、
cancel／denied／stale 之後仍 mutation、boundary 或 crash 後自動重播、
舊 generation 污染新文件、Worker 無界增長，或完成流程需要禁止 surface。
保存失敗 bytes／trace 並建立編號 finding。

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
- `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-client.test.mjs`
- `wasm_sdk_probe/web/e2-c-validation.html`／`-app.js`
- `wasm_sdk_probe/tools/run_e2_c.py`、`tools/validate_e2_c.py`

本輪修改（預定）：

- `wasm_sdk_probe/Makefile`（`test-e2-c-static`、dist 複製規則）
- `wasm_sdk_probe/e2/content-axis-suites.json`（**新檔**，`E2-C-D3` 套件；
  **不動 `e1/` 那一份**，理由見 8.1）
- `specs/SPEC-E2-000-overview.md`（第 7 節接上 C 的規格連結）

**不修改**：`editor-shell/*.js`、E2-B 的任何檢查工具、任何 profile 的位元組。

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-15 | **v1 草擬。** 進場前先量了一件沒有人量過的事：**出貨的 v2 profile 上，E1 的十個動作沒有任何殼層到得了**（v1 殼層被自己的 capability＋version 閘擋掉，v2 殼層的 allowlist 只有五個），而**四路清單檢查看不到它**——那個檢查的「client」是兩個殼層的**聯集**，聯集裡有一個接不上這顆 profile。測試連同兩個對照組已建立且**當下是紅的**。因此本規格把「補上十五個動作的產品殼層」訂為**進場工作**而不是 D 相位的一部分，並寫明否決的另外兩條路（改 manifest 砍動作＝重建 artifact＋斷掉 132 個 run 的綁定；出兩顆 profile＝一份文件開不在兩個引擎裡）。相位前綴改用 `D` 以免與 E1-C 的 C0～C4 在同一棵證據樹裡同名。D3 語料六份，第六份 `list-contexts` **是 E1-C 9.2 在 08-13 就寫下的義務**（「清單動作要進出貨契約之前，必須先補語料或具名排除」）現在到期。E2-B 9.11 的四項未涵蓋各自有處置：跨段全編號進 D1、實體拖曳進 D5、H2–H6 與大綱參與維持不承諾。 |

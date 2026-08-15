# E2-C 執行計畫：一次 relink 鑄出 v3，然後重跑

> **2026-08-15：對抗性審查（codex）判定「現在不要連結」，11 項，6 個 blocker。
> 全部接受，其中兩個 blocker 由一個比它建議更便宜的修正一起消掉。
> 本計畫已據此改寫；`## 審查之後的修正` 一節是差異。**

2026-08-15 訂。**這份是執行順序與風險，不是規格**——每一步的內容在
`SPEC-E2-C` 與 finding 045 裡。

前一份 [`PLAN-E2-B-relink-and-freeze.md`](PLAN-E2-B-relink-and-freeze.md)
的規矩原樣適用，尤其那一句：**「P1 完成才能 relink。漏一項就是第二次 relink。」**

## 為什麼現在可以排

裁決要求的兩件量測都做完了，而且**其中一件把佇列變短了**：

- **finding 045 的修法已原生確認**（`findings/evidence/045/native/`）：
  帶參數就是 setter，兩個方向都是；**帶 `false` 打在已套用的選取上會把屬性移除**，
  那是出貨產品今天做不到的事。七個預測六個成立。
- **`d1-body-collapsed` 二分到底**（SPEC E2-C 9.5.6）：它量的是 **harness 的手勢**，
  不是產品的。**不需要引擎修法，因此不進這次的佇列。**

## P0 — 動手前（零風險，先做）

- [ ] `build/archive/` 存一份現行 `e2-editor-v2` profile（改引擎前先 archive）。
- [ ] 核對四顆凍結 artifact 的 hash 未變：`835b453d`／`679def61`／`c89f069e`／`940b7723`。
- [ ] 記下 `e2-editor-v2 = 572035ac…`：E2-B 的判定與 E2-C 第一輪的全部證據綁在它上面，
      **這次連結之後它們仍然為真、但不再描述產品**（finding 027 的形狀）。
- [x] `dist/profiles/e2-editor-v2/` **未被碰到**（連結後仍是 `572035ac…`，與 archive 相同）。
- [ ] ~~`build/e2/editor-v2/` 不得被碰到~~ —— **我違反了這一條**：只編 object 的檢查
      直接跑了 `make build/e2/editor-v2/probe_engine.o`，把 v2 的 object 換成新原始碼
      編出來的。**artifact 沒事**（編 object 不連結，`dist/` 逐位元不變、與 archive 相同），
      守衛也仍然擋著 v2 的連結。但那個 build 目錄現在是混的：一個新 object ＋三個舊的。
      **v3 用自己的 build 目錄，所以不受影響；記在這裡是因為「沒事」不等於「沒發生」。**
      往後只編 object 的檢查要編到 scratch 目錄，不要編進任何 profile 的 build 目錄。

## P1 — 引擎與 Makefile：**唯一一次 relink**

| # | 檔案 | 內容 | 依據 |
|---|---|---|---|
| 1 | `src/probe_engine.cpp` | 四個 inline 格式各送參數：`{"Bold":{"type":"boolean","value":<enabled>}}`（Italic／Underline／Strikeout 同形，slot 名對應）。`gEditorUnoOption` 從「只拿來回報」變成**真的被送出去** | finding 045，**原生驗證** |
| 2 | `src/probe_engine.cpp` | **gesture mask 要對十個繼承動作也生效**——目前只有 `routeFormatBarrier()` 讀 mask，而那是五個段落動作專用路徑 | SPEC E2-C 2.5 |
| 3 | `src/probe_engine.cpp` | barrier payload 的 `route` **不得把預設值當觀測值**回報：型態守衛在指派 route 之前 return，於是證據裡出現「`route: collapsed` 但其實沒有分類過」 | 9.5.4 |
| 4 | `src/editor_api.h`／`.cpp` | ABI 版本常數 → **3**（flat、精確比對）。**動作列舉一個字不動**——這次改的是語意不是介面 | 「版本是身分」 |
| 5 | `Makefile` | **新的建置變體 `e2-editor-v3`**：新的 build 目錄與 dist 目錄，掛 `refuse_unasked_relink`；**`e2-editor-v2` 的 target 一個字不動** | 5.12 的作法 |
| 6 | `tools/build_e2_c_profile.py` | **新 builder**（不改 v2 的）：contract v3、`narrow-editor-v3`、`limits` 補兩筆（見 P2-1） | 5.8 的作法 |
| 7 | `tests/editor_abi_header_test.cpp` | 斷言 ABI 常數 = 3（`-fsyntax-only`，不影響 artifact） | — |

**`changed` 刻意不改**（fable 的建議，採納）：SPEC E2-C 9.5.2 已經把這四個動作的
`changed: true` 定義成「引擎接受且狀態前進」，而不是「文件位元組變了」。
把它改成觀測值會動到 v1 契約而換不到任何量到的好處。
**這一條寫在這裡，是為了讓「沒改」是一個決定而不是一個遺漏。**

**P1 完成才能 relink。漏一項就是第二次 relink。**

### 動手順序（既有規矩）

1. 先只編 object 不連結（`em++ -c`），證明改得過；
2. 再 archive；
3. 才連結，且**只連結 v3 的 target**。

### P1-2 的後果：**inline 格式在範圍上會開始被拒絕**（自己覆核時發現的）

把 mask 對十個動作生效之後，manifest 說 `collapsed` 就真的只有 collapsed 能用。
**今天在範圍上按粗體是會成功的**——D1 的特徵量測格（3 輪 × 2 瀏覽器，**6/6**）
記到 `set-bold` 在單段範圍上回 `uno-command-result`；原生 P6／P7 也量到選取上的
文件效果。所以這是一個**產品行為的改變**，必須是刻意的。

**決定：v3 的宣告維持 `collapsed`，也就是範圍上的 inline 格式會被派送前拒絕。**

- **不宣告沒量過的東西**——builder 自己的註解就是這樣寫的。
  WASM 那半只量到 typed 成功，**沒有任何一格去看存出來的文件**；
  原生量到了文件效果，但那是原生。兩半都不夠。
- 拒絕是**零 mutation 的 typed 拒絕**，而且 host 可以用 `gesturesFor()` 把按鈕
  灰掉——不是「按了才失敗」。
- **而且這個決定很便宜就能翻案**：mask 是 init 時從 manifest 推進引擎的，
  所以**放寬宣告不需要 relink**（fable 已經確認 builder 是打包器）。
  第二輪加一格**帶文件判準**去量範圍上的 inline 格式；量到了就放寬。

**順帶記一個對照**：同一格量到 `delete-backward` 在範圍上 6/6 回
`EDITOR_STATE_UNAVAILABLE`——引擎本來就拒絕，所以 delete 那兩個不受這次改動影響。

## P2 — JS／Python：不重連結，但必須在量測前定稿

| # | 檔案 | 內容 | 依據 |
|---|---|---|---|
| 1 | 新 builder 的 `limits` | 兩筆債：**帶註腳／尾註的段落不支援**（4.2）、十個繼承動作的手勢宣告要與 P1-2 真的執行的東西一致（2.5） | 4.2、2.5 |
| 2 | `editor-shell-v2/narrow-editor-v2-client.js` | 接受的 contract 版本改成 **3** | 見下面的〈唯一一個值得再看一眼的決定〉 |
| 3 | `e2/editor-shell-v2-bundle-v1.json` | 重算（客戶端改了，摘要就變） | 第 6 節 |
| 4 | `web/e2-editor-app.js` | 釘死的 hash 換成 v3 的 | 2.4 |
| 5 | **`e2/validation-matrix-v2.json`** | **第二輪的凍結矩陣**，在第二輪 D0 之前寫好。與 v1 的差異至少三處：baseline 換成 v3 的四個雜湊、**新增「游標一律照產品的方式形成（click ＋ 確認輪詢）」**、新增一格把 9.5.6 量到的 `selectRange` 差別釘住 | 9.1、9.5.6 |
| 6 | `tools/analyze_e2_c_d1.py` | 四個 `-false` 格的判準**不變**——它們現在應該會綠，而那正是修法的驗收 | — |
| 7 | `e2/validation-matrix-v2.json` | **新增一格：inline 格式打在單段範圍上，帶文件判準**。量到了才有資格在 v4 放寬宣告（放寬不需要 relink） | 見上 |

## P3 — 量測（v3 上，開始之後不得再編）

**這次連結作廢的東西要全部重跑**：

- [ ] **E2-B**：132 個正向 run ＋ 12 列 negative matrix ＋ no-op 方程式 ＋ 四路清單，
      全部在 v3 上重跑，`validate_e2_b.py` 重推判定。
      （E2-B 對 v2 的判定仍然為真，但不再描述產品。）
- [ ] **E2-C 第二輪**：D0 → D1 → D2 → D3 → D4 → D5，用 `validation-matrix-v2.json`。
      D2～D5 的 harness **還沒寫**。
- [ ] **E1-C**：**可分割，先不做**。等 v3 的參數化形式在產品上驗過再單獨決定
      （`e1-editor-v1` 有同一個缺陷，但它是另一顆 artifact、另一套人工輪）。

## P4 — 凍結與遷移

- [ ] `demo-structure` 與 `e2-editor` 的 pin 換成 v3。
- [ ] `e2-editor-v2` 進 `refuse_unasked_relink` 的守衛清單（它現在也是歷史 artifact）。
- [ ] 舊證據**原封保留**，不覆寫：`e2-c-validation/` 是第一輪的紀錄，
      第二輪寫到 `e2-c-validation-v3/`。

## 唯一一個值得再看一眼的決定

**客戶端要不要跟著改名成 v3？**

「版本是身分」在 ABI、builder、profile 上我照做了（新常數、新 builder、新目錄）。
**客戶端我沒有複製一份**，只把它接受的 contract 版本從 2 改成 3。理由：

- 客戶端的**規則**一個字沒變（同樣十五個動作、同樣的後置條件）。變的是它被量在哪顆
  artifact 上——而**那件事是由殼層 bundle 的摘要記錄的**，不是由檔名。
- 複製一份就會有**兩份規則**，那正是 2.2 明確拒絕過的事（而且當時是為了避免
  underline／strikethrough 那種漂移）。

**代價要說清楚**：`e2-editor-v2` 從此沒有任何客戶端接得上——就像 `e1-editor-v1`
現在的處境。v2 已經不是產品，所以我認為可以接受，**但這是這份計畫裡最該被質疑的
一條**。

## 三個風險

1. **佇列漏項 → 第二次 relink。** 這是最貴的失敗。目前佇列的來源有三個：
   finding 045、SPEC E2-C 的兩筆 manifest 債（4.2／2.5）、以及 9.5.4 的
   `route` 回報缺陷。**D2～D5 還沒跑過，所以它們可能再生出佇列項**——
   這就是為什麼 P3 的順序是「先 E2-B 再 E2-C」而不是反過來：
   E2-B 的矩陣已經寫好，能最快把新 artifact 的基本面掃一遍。
2. **改了 `Makefile` 就讓連結目標過期**（finding 042）。所以 Makefile 可以分次改，
   **要只做一次的是「跑 make 去連結」**。
3. **第二輪矩陣要在第二輪 D0 之前凍結**，而不是「等 D1 跑完再補上游標那條」。
   第一輪就是這樣被咬的——27 格用了產品不會用的手勢，而矩陣沒規定過。


---

## 審查之後的修正（2026-08-15，codex）

**判定：不要連結。** 11 項全部接受。以下是每一項的處置。

### 兩個 blocker 由同一個修正消掉：**不動 contract version 與 capability**

審查指出（#2）：v3 若宣告 `narrow-editor-v3`／contract 3，**worker 根本不認**
——`sdk-worker.js:40` 把 `editorActionV2` 綁在 `narrow-editor-v2`、`:143` 綁在
version 2，而 `ParagraphEditorClient:64` 又自己再檢查一次。
**那正是 2.2 那個缺陷被我原封重建一次。**

它建議做一整套 v3 operation family。**更便宜而且更誠實的作法是：不要動那兩個字串。**

- **真正在跑的身分守衛是 ABI 版本**：`sdk-worker.js:810-818` 在 init 時把
  `oxsdk_editor_abi_version()` 與 manifest 的 `abiVersion` **精確比對**，
  不合就 `INCOMPATIBLE_ABI` 直接失敗。
- 這次變的正是 ABI 語意（`enabled` 的意義），所以**該動的版本就是 ABI 版本**，
  而它已經動了（2 → 3）。manifest 的 `abiVersion` 跟著寫 3，
  新舊兩顆 build 因此在 manifest 上就分得開，而且**分不開就跑不起來**。
- contract version 與 capability 維持 2／`narrow-editor-v2`：
  客戶端規則一個字沒變，於是**不必新增客戶端、不必動殼層 bundle**
  ——連帶 blocker #6（改 v2 客戶端會毀掉第一輪證據的身分）也消失。

**因此下列項目從計畫中刪除**：P2-2（改客戶端接受版本）、P2-3（重算殼層 bundle）、
〈唯一一個值得再看一眼的決定〉整節。`editor-shell-v2/` 與
`e2/editor-shell-v2-bundle-v1.json` **一個位元組都不動**。

### 引擎的兩個真缺陷，已修

- **#3 `selectionObserved` 沒有被看**：空的矩形集合只有在 core 至少報過一次選取
  之後才代表「沒有選取」（欄位自己的註解就這樣寫）。原本的閘門把
  「還沒有人說」當成收合游標——**沒有觀測就分類**。已改成 fail closed。
  **既有的段落路由（`:3300`）有同一個缺陷**，一併修（它也是這次 relink 帶的東西）。
- **#4 未分類的範圍用 OR 遮罩配「任一位元」判準**：`editorGesturePermitted` 是
  交集判斷，傳 `single|cross` 會讓「只允許 single」的 manifest 也放行一個
  **可能是跨段**的範圍。已改成未分類的範圍**必須兩個位元都允許**。

### 其餘接受的項目

| # | 內容 | 處置 |
|---|---|---|
| 1 | P1 沒做完就不能連結（Makefile 變體與 builder 都還沒寫） | 接受，那是門檻不是缺陷 |
| 5 | **規格仍然禁止這次 relink**（`SPEC-E2-C` 第 3 節），而計畫不是規格 | **連結前必須先改規格**：第二輪的範圍、v3 契約、證據命名空間、哪些舊條文被取代、v2 判定如何保留 |
| 7 | E2-B 重跑的工具寫死 v2：證據路徑、預設覆寫 `e2-b-summary.json`、negative profile 產生器**拿 ABI 3 當不匹配值**（會等於 v3 的真值） | 接受。要一套版本化的重認證，輸出另開路徑，**不匹配值改成 4** |
| 8 | **D2～D5 沒寫，是連結前的佇列完整性問題，不是連結後的排程細節**——D2 專門打引擎的失敗路徑，正是最可能再長出佇列項的地方 | **接受，而且這是最大的排程改變**：D2～D5 的 harness、分析器、突變測試要先寫好，能在 v2 上跑的先跑 |
| 9 | manifest 自己沒有被綁——而這次改的正是 manifest 裡的語意 | 接受：**manifest 的 sha256 加成第五個綁定身分** |
| 10 | 「單段與跨段各一次」的特徵量測**從來沒有跨段過**——`rangeAt(client, y)` 起訖同一個 y | 接受。**第一輪矩陣的判準文字與 harness 實際做的事對不上，這件事要記進第一輪的證據**；繼承動作在 v3 維持 collapsed-only |
| 11 | P4 那條「把 v2 加進守衛」已經做過了（`Makefile:936`），而且**連結之後再改 Makefile 會讓 v3 的目標過期**（finding 042） | 接受：刪掉該項，所有守衛與靜態斷言進 P1 |

### 因此，連結之前還要做的事（新的 P1 完成條件）

1. 改規格（#5）——**沒有這一步，連結是違反自己寫的邊界**。
2. 第一輪證據補記「跨段特徵量測其實沒跨段」（#10）。
3. Makefile 的 v3 變體 ＋ `build_e2_c_profile.py`（abiVersion 3、兩筆 `limits`）。
4. manifest sha256 進矩陣與 D0 證據（#9）。
5. E2-B 重認證工具版本化，不匹配值改 4（#7）。
6. **D2～D5 全部寫好並在 v2 上跑過**（#8）。

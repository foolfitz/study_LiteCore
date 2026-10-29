# SPEC-M3-shell-v79-finding-173：新空白文件按項目符號不再鎖佇列（頁面修法、殼層 generation 79、宿主 0.2.41）

> 狀態：**釘死**（2026-10-29，任何實作與瀏覽器執行之前）。釘死之後只准追加（CLAUDE.md 第 10 節）。
> 依據：finding 173（`d14186167`）、工單 `handoff/WORKORDER-173-blank-document-bullet-page-fix.md`。
> 擁有者 2026-10-29 約 22:00：「A：修頁面，出 0.2.41」。

## 1. 為什麼要有

擁有者在宿主 0.2.40 上手測：Files「＋新增 → 新文件」開出來的空白文件，按工具列的項目符號，跳出「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來」。鏡像上用宿主自己的空白範本重現（`findings/evidence/173/run-02/`）〔實測〕：

| 產品 | failureShape | 頁面 |
|---|---|---|
| v22（0.2.38 的引擎） | `stage-deadline:awaiting-selection` | `ready`，083 那句提示 |
| v24、v25 | `select-text-returned-none` | `recoverable-error`，「引擎需要重新開啟」 |

成因〔讀碼，與實測一致〕：頁面的處置 `formatFailureDisposition` 只對兩種「已送出、檢查無法核對」的形狀讓佇列開著——`multi-block-readback`（046）與 `stage-deadline:awaiting-selection`＋`selectionResultSeen`（083）。v23 起的有序引擎把 083 的同一情況改叫 `select-text-returned-none`（`wasm_sdk_probe/src/ordered_format.inc:30-36`，同步讀到的選取類型是 `LOK_SELTYPE_NONE`），頁面不認得，落到 `dispatched-rollback`，新文件沒有檢查點，於是要求重開。

v25 的 run-02 頁面紀錄（`findings/evidence/173/run-02/report.json`）：v25 的錯誤帶 `route: "collapsed"`、`dispatched: true`、`selectionResultSeen: true`、`failureShape: "select-text-returned-none"`——083 那條規則的另外三個條件都成立，只差名字〔實測〕。有序路徑只在 `.uno:SelectText` 的結果有回來時才會走到 `finishOrderedFormatReadback`（`ordered_format.inc:124-136`：collapsed 路由沒看到選取結果就先以 `proof-absent-at-poll:…` 結束），所以 `selectionResultSeen` 在有序引擎上的意思與 083 相同：引擎有回答，回答是「什麼都沒選到」〔讀碼〕。

## 2. 範圍

**做**（頁面側，不改引擎、不重新連結；profile 仍是 `e2-editor-v25`，釘選 `44cb15ea8d36f0e0`，worker URL 不變）：

1. `wasm_sdk_probe/editor-shell-v2/paragraph-editor-client.js`：083 那條規則也接受 `select-text-returned-none`，三個條件不變（`dispatched === true`、`route === "collapsed"`、`selectionResultSeen === true`）。
2. `wasm_sdk_probe/web/e2-editor-app.js`：`review` 的提示，083 那句（「動作已送出，但這一段是空的…這是檢查的極限，不是文件壞了」）也給 `select-text-returned-none`。不改的話會落到「這一格的檢查涵蓋了不只一個段落」，對這份文件是假的（finding 061 的前例）。
3. 兩個檔都是 generation 78 的成員（不是 E1-C bundle 的成員：`e1/editor-shell-bundle-v2.json` 只綁 `editor-shell/*` 與 `input/*`）→ 兩處改完後凍 **generation 79**，頁面換新雜湊。
4. 宿主 0.2.41：只換頁面與 `paragraph-editor-client.js` 兩筆。

**不做**：

- 有序路徑其他已送出的失敗形狀（`selection-type-not-readable`、`footnote-apparatus-readback`、`unknown-structural-tag`、`malformed-readback-nesting`、`block-extraction-failed`、`postcondition-not-met`）。v22 在對應情況下是否讓佇列開著**沒有量**，不能比照 083 的理由加進來。
- Ctrl+A 全選（`handoff/WORKORDER-v26-select-all.md`）、K、`what_the_link_ships.py` 的兩個盲點。

## 3. 決定紀錄

| 題 | 決定 | 出處 |
|---|---|---|
| 修在哪 | 頁面（不重新連結） | 擁有者 2026-10-29 選 A |
| 規則寬度 | 只加一個名字，083 的三個條件照舊；其他有序形狀不加 | 工單；本規格 §2 |
| 提示句 | 用 083 那句，不新寫一句：兩個名字說的是同一個情況 | 本規格 §1 |
| 為什麼要凍 79 而不是覆寫 78 | 78 已被 v25 的 F3／F4 與宿主 0.2.40 綁住；改動之後就是下一個 generation | v25 規格 §15 第 2 點 |

## 4. 設計

### 4.1 `paragraph-editor-client.js`

083 那條 `if` 的 `failureShape` 條件，從等於一個字串改成屬於一個兩個名字的集合（`stage-deadline:awaiting-selection`、`select-text-returned-none`）。其餘三個條件、其他每一條規則、規則的順序都不動。註解寫明第二個名字是有序引擎的同一情況、出處是 finding 173。

### 4.2 `e2-editor-app.js`

`review` 提示裡 083 那個分支的條件，改成同一個兩個名字的集合。句子本身一個字都不改。其他分支（059 的 `LOK_COMMAND_FAILED`、046 的「不只一個段落」、rollback、restart）不動。

### 4.3 身分

- profile：不變（`e2-editor-v25`，archive `e2-editor-v25-44cb15ea-worker-75557b22`）。
- 殼層：generation 79＝generation 78 只差這兩個檔（頁面、`paragraph-editor-client.js`）。凍結用 `build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v79.json --write --frozen-date 2026-10-29`（或實際凍結日），排除清單逐字沿用 v78 的八筆。工具的預設 `MANIFEST` 依設計仍是 v76，不改。
- Makefile 的 bundle 行（`wasm_sdk_probe/Makefile`，目前 `--manifest e2/editor-shell-v2-bundle-v78.json`）改指 v79：改前紅、改後綠、指回 v78 紅。
- 凍結之後若還要改殼層，那是 generation 80，不覆寫 79。

## 5. 判準

證據目錄：`findings/evidence/shell-v79-173/`（宿主另放 `findings/evidence/host-0.2.41/`）。

### 5.1 U1：處置規則（單元，先紅）

在 `editor-shell-v2/tests/paragraph-editor-client.test.mjs` 083 那個測試旁邊加一個測試：

- `select-text-returned-none`＋三個條件 → `dispatched-unverified`。
- 各自只改一項、都必須維持現在的處置 `dispatched-rollback`：`selectionResultSeen` 為 `false`、為 `null`；`route` 為 `range-cross`；`selection-type-not-readable`（同為有序引擎的名字，但不在本次範圍）。
- `dispatched: false` → `refused-no-mutation`（不變）。
- 083 原本的形狀與 046 的形狀仍是 `dispatched-unverified`（這條規則沒有吃掉別的情況，也沒有被改掉）。

**紅案**：在**未修改**的 `paragraph-editor-client.js` 上先跑一次，新測試必須紅、而且紅在第一個斷言（`select-text-returned-none` 得到 `dispatched-rollback`）；輸出存成見證 `u1/red-before.txt`。修好之後 `node --test editor-shell-v2/tests/*.test.mjs` 全綠，存 `u1/green-after.txt`。
**預設**：沒跑或沒有紅的見證，U1 不成立。

### 5.2 U2：提示句（單元，先紅）

新測試檔 `editor-shell-v2/tests/page-review-sentence.test.mjs`，照 `page-boundary-noop.test.mjs` 的作法，從頁面原始碼切出 `run()`、把協作者換成記錄用的替身，丟一個 `recovery: "review"`、`code: "MUTATION_OUTCOME_UNKNOWN"` 的錯誤進去，讀它發出的提示：

- `failureShape: "select-text-returned-none"` → 提示含「這一段是空的」，不含「不只一個段落」、不含「回到檢查點」。
- `stage-deadline:awaiting-selection` → 同上（083 沒有被改掉）。
- `multi-block-readback` → 含「不只一個段落」、不含「這一段是空的」（046 沒有被吃掉）。
- `code: "LOK_COMMAND_FAILED"` → 059 那句（含「核心的回覆」），不含另外兩句的鑑別字。

判的是「選了哪一句」，用每句的鑑別片語，不比整句逐字（三句由不同片語分得開即可）。
**紅案**：未修改的頁面上第一條紅（拿到「不只一個段落」）；見證存 `u2/red-before.txt`。另外測試檔自帶一個變異：把頁面裡的集合改回只有 083 一個名字，第一條必須紅（防止測試切錯函式而空洞地綠）。
**預設**：沒跑或沒有紅的見證，U2 不成立。

### 5.3 B1：擁有者那條路（瀏覽器，鏡像，形式二）

新工具 `wasm_sdk_probe/tools/check_v79_blank_bullet.py`（由 `findings/evidence/173/blank_bullet.py` 衍生；產品建構另放 `tools/v79_f_products.py`）。**從擁有者的步驟出發，不從 product-path 的固定裝置出發**（交接 10-29h 的警告）：

- **文件**：宿主自己的空白範本 `/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt`（sha256 記進報告，必須等於 `7e6221b6…`，即 173 run-02 用的那一份），經頁面自己的開檔入口打開。
- **臂**：`noclick`（開好就按）與 `click`（先真的點進段落再按）。
- **輸入一律是真的**：點擊與按鍵走 Chrome 的 CDP `Input.dispatchMouseEvent`／`Input.dispatchKeyEvent`、Firefox 的 WebDriver actions（`tools/v21_input.py`）。工具列的項目符號按鈕用真的滑鼠點它的中心；接著**不補任何 focus**，直接用真的按鍵打一個小寫標記字串（使用者按完按鈕就打字）；然後按產品自己的「儲存」，從頁面交出去的 Blob 讀 ODT。
- **產品**（每個 mirror 用之前逐檔核對身分，身分不過就不跑）：
  - **before**：頁面與 `paragraph-editor-client.js` 取自 git `d14186167`，其餘為 `dist/`；殼層每個模組必須等於 generation 78 的 sha256，profile 必須等於 v25 archive。
  - **after**：`dist/` 原樣；殼層除這兩個檔之外每個模組等於 generation 78；這兩個檔必須等於樹上的原始碼而且**不等於** generation 78（封閉清單）；profile 等於 v25 archive；頁面指向 `profiles/e2-editor-v25/`。兩個檔送出的 sha256 記進報告，凍結 79 之後核對它們等於 generation 79 的紀錄（§5.6）。
- **頁面觀察器**：HTML 注入一個包 `Worker` 的觀察器（同 F2），記錄每個 request 與回覆、錯誤裡的 `formatBarrier`（處置實際讀的欄位），以及頁面交出去的 Blob。不改任何送出的位元組。
- **after 的一回 PASS**（全部成立）：
  1. 項目符號的回覆是 173 的形狀：`ok: false`、`failureShape: "select-text-returned-none"`、`dispatched: true`、`route: "collapsed"`、`selectionResultSeen: true`。不是這個形狀＝沒有走到 173 的路，該回判 **NE**（不是 PASS），因為它沒有量到修法。
  2. 按完之後：狀態燈 `ready`、`#notice` 沒有顯示、提示含「這一段是空的」而且不含「不只一個段落」「回到檢查點」。
  3. 佇列開著：真的按鍵打的標記，每一個 `insertText` 回覆 `ok: true`，修訂號前進，狀態燈仍是 `ready`。
  4. 存檔成功，`content.xml` 裡含標記的那個 `text:p` 有一個祖先是 `text:list`（項目符號真的套上了——「請看一下結果」這句提示是誠實的）。
- **before 的一回「為 173 而紅」**：項目符號的回覆是第 1 條的形狀，而且狀態燈 `recoverable-error`、`#notice` 顯示。before 紅在任何別的原因上，是工具自己的設定問題，判讀不成立。
- **次數**：兩個產品 × Chrome、Firefox × 兩臂 × N＝3，共 24 回。
- **判定 `B1_HOLDS`**：兩個身分都過；after 12 回全 PASS；before 12 回全「為 173 而紅」。
- **紅案**：(a) 修法之前，after 的身分必須被拒（兩個檔等於 generation 78）；before 必須跑出「為 173 而紅」——這兩條同時是工具的試跑，結果存 `b1/pre-fix/`。(b) `--self-test REPORT`：拿真的報告做變異，每一個都必須讓判定轉紅：after 一回的提示換成「不只一個段落」那句、`#notice` 改成顯示、標記移出 `text:list`、一個 `insertText` 改成 `ok: false`、項目符號回覆的 `failureShape` 改成別的（必須變 NE 而不是 PASS）、before 一回改成 `ready`（不再為 173 而紅）、刪掉一回（次數不足）、身分 `ok` 改成 false。
- **不是計時量測**：不需要桌面閘門。
- **預設**：沒跑、或任何一回是 NE，B1 不成立。

### 5.4 回歸：F3 與 F4

修法只碰一個處置分支與一句提示的條件，所以**任何其他格子移動都是 finding，不是雜訊**。

- **F3-79**：`tools/run_v79_f3.py`（由 `run_v25_f3.py` 衍生，差異是封閉清單：generation 78 → 79），Chrome、Firefox 各 1 回，頁面是 `dist/` 送的新頁面。兩條讀法都要成立：
  1. `tools/read_v25_f3.py --v25 <dir>`（不改，§16／16.1 的規則，基準 v24 T4 run-02）→ `F3_HOLDS`。
  2. 新讀取器 `tools/read_v79_f3_equal.py`：母數由 v25 F3 run-02（`findings/evidence/link-batch-v25/f3/run-02/{chrome,firefox}/report.json`）逐瀏覽器生成，**每一格的結果必須與 run-02 相同**；id 集合必須相同；不同的格子逐一點名、判紅；任一份報告沒有檢查判紅（非空洞性）。紅案先做：一格 PASS 改 FAIL、一格 NE 改 PASS（變好也算移動，要點名）、少一格、多一格、空報告，每個都紅。
  - 若有格子移動：停下來，先查清楚是產品、工具還是環境，再決定下一步；不靠重跑把它洗掉。
- **F4-79**：`tools/run_v79_four_arms.py`、`tools/judge_v79_product_four_arms.py`、`tools/v79_four_arms_identity.py`（由 v25 的三支衍生，差異是封閉清單：generation 78 → 79、頁面雜湊、殼層摘要）。兩瀏覽器四臂 24/24 PASS。預檢紅案：指 v78 的 manifest 被拒、不加覆寫被拒。
- **不改** v78 的工具（`run_v25_f3.py`、`run_v25_four_arms.py`、`judge_v25_product_four_arms.py`、`v25_four_arms_identity.py`、`v25_f_products.py`）：它們被已 commit 的證據綁住。
- **預設**：沒跑、NE、或任何一格移動而沒有查清，回歸不成立。

### 5.5 E1-C 與 V0′

- `check_e1_c_bundle_intact.py`：`intact: true`、bundle `187706b2dcb07d2b`。
- **V0′**（沿用的計數必須仍讀得出來）：v24 的兩支讀取器（`read_v24_remaining_cohort.py`、`judge_v24_product_four_arms.py`）與 v25 的 F4 判讀（`judge_v25_product_four_arms.py`）都綁活的殼層摘要，凍結 79 之後在活的樹上**依構造**是 NE。照 `findings/evidence/link-batch-v25/cutover/README.md` 的作法，但這次要把**兩個**宣告的檔都換回（原始碼與 `dist/`）：給 v24 的讀取器換回 generation 77 的兩個檔，給 v25 的判讀換回 generation 78 的兩個檔；三支的輸出都必須與已 commit 的結果逐位元組相同；放回之後核對雜湊。
- **預設**：沒做，沿用的計數視為讀不出來，宿主 0.2.41 不送裝。

### 5.6 generation 79

- 凍結前：§5.1–5.3 全過（U1、U2 綠，B1 `B1_HOLDS`）。
- 凍結：與 generation 78 只差這兩個檔（工具算出的差異＝封閉清單，多一個或少一個都停手）；B1 記下的 after 兩個 sha256 等於 79 的紀錄。
- Makefile bundle 行：改前紅、改後綠、指回 v78 紅（三個輸出都存）。`make test-e2-c-reachability` 整體仍會紅在 v21 以來既有的覆蓋稽核那一行；凍結以 bundle 那一行本身為見證，並核對問題清單與凍 78 時相同。
- **預設**：沒凍，F3-79／F4-79 不跑。

### 5.7 宿主 0.2.41

- 腳本由 `findings/evidence/host-0.2.40/` 衍生（不改那些檔）：父＝活的 `main` **ae1f9db**（0.2.40）；前身 archive `wasm_sdk_probe/build/archive/host-0.2.40-engine-a08bc6ecb7241448`，先核對活的引擎等於它；新 worktree 分支 `host-0.2.41`（只改 `info.xml`）。
- 套件判準：對 0.2.40 **恰好兩筆**紀錄改變（頁面、`paragraph-editor-client.js`），profile 檔不變；證據閘門在 0.2.40 那一份之外加 U1、U2、B1、F3-79、F4-79、V0′、E1-C。紅案比照 0.2.40（多一筆改變、少一筆、profile 改變，各自要紅）。
- 安裝要**新的擁有者時段**，而且要有明確的「不開站」回答（記進 `slot.json`）；fgp-nc 與 nc-bridge 照擁有者 2026-10-29 的選擇維持關閉。
- 裝完：Files 實流程（`run_calc_editor_host.py`）與 `capture-after.py`，比照 0.2.40。
- 請擁有者重做手測：Files「＋新增 → 新文件」→ 按項目符號 → 打字 → 存檔。**這一條是使用者那條路，B1 走的是鏡像的開檔入口**（§6 的 L-mirror-open-route）。
- **預設**：沒有時段就不裝；0.2.40 仍是日常未計數候選。

## 6. 具名限制

- **L-none-means-empty**：083 那句說「這一段是空的」。有序引擎的 `select-text-returned-none` 是 `.uno:SelectText` 之後選取類型為 `LOK_SELTYPE_NONE`；本規格依 083 的前例把它讀成「段落是空的」。在**不空**的段落上 `.uno:SelectText` 什麼都沒選到的情況（例如只有錨定物件的段落）沒有量；若存在，提示句的歸因會錯，但處置（佇列開著、可以復原）仍是 083 的論證。
- **L-other-ordered-shapes**：§2「不做」那六個形狀在 v25 上仍是 `dispatched-rollback`；v22 在對應情況下的處置沒有量。
- **L-mirror-open-route**：B1 經頁面的開檔入口開範本；擁有者經 Files 的「新文件」（宿主複製範本、經 WebDAV 開）。引擎拿到的位元組相同，路由不同；宿主那條由裝完後的手測補。
- **L-no-engine-record-in-b1**：B1 讀頁面拿到的錯誤欄位（worker 的投影），沒有讀引擎紀錄（173 的診斷工具只在 Chrome 做得到）。處置讀的正是這些欄位，所以判準量的是處置的實際輸入；引擎側在 v25 F1 已經量過 `dispatched` 的序列化。

## 7. 順序

1. 本規格 commit（釘死）。
2. B1 工具；修法之前跑 §5.3 紅案 (a)（before 為 173 而紅、after 身分被拒）。
3. U1、U2 先紅（見證）。
4. 實作（§4.1、§4.2）→ `node --check` 兩個檔 → `node --test editor-shell-v2/tests/*.test.mjs` 全綠。
5. `make -n e2-c-assets` 應該只印兩行 `cp`（頁面、`editor-shell-v2/paragraph-editor-client.js`）→ `make e2-c-assets` → 逐檔 `cmp`。
6. B1 → `B1_HOLDS`；`--self-test` 全紅。
7. 凍 generation 79、Makefile 改指 79（§5.6）。
8. F3-79、F4-79（§5.4）→ V0′、E1-C（§5.5）。
9. 宿主 0.2.41 套件（§5.7）→ 擁有者時段 → 安裝 → Files 實流程 → 事後讀取 → 請擁有者手測。

沒有任何一步要編譯；`make e2-c-assets` 只有 `cp`（短步驟，我自己跑）。

## 8. §34.4

本規格釘死之前：因執行而修 0；因審核而修 0。

## 9. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-29 | 初版，釘死（任何實作與瀏覽器執行之前） |

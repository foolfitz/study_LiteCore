# Milestone 草案：從 ODT 編輯器到 Nextcloud app

> **日期**：2026-08-20
> **文件性質**：**排序與理由，不是規格。**不凍結範圍、不給日期、不構成執行授權。
> 真正要執行時，每個 milestone 各自另立 spec。
> **依據**：[產品路線與競爭者盤點](./RESEARCH-2026-08-20-product-route-and-competitors.md)、
> [SPEC R6+ roadmap](../specs/SPEC-R6+-roadmap.md)、[SPEC R10-000](../specs/SPEC-R10-000-overview.md)
> **證據標記**：**已觀察**／**推論**／**待驗證**，沿用專案慣例。

---

## 0. 使用者提出的順序

1. 核心：能讀 ＋ 簡單寫 ODT
2. 壓縮體積
3. **建立 Nextcloud app**（2026-08-20 插入）
4. 能讀 ODS、ODP、ODG
5. 能簡單修改 ODS、ODP

**2026-08-20 追加**：a11y 從長期目標**提前到 Nextcloud app 之前**（使用者裁示）。本文再往前放一格，
放在 M2a 之前，理由見 §3.2。

本文把它展開，並處理一個**會導致重做的排序衝突**（第 1 節）。

---

## 1. 排序衝突：壓縮體積放在「多支援格式」之前

### 1.1 事實（已觀察）

目前是 `--with-wasm-module=writer`。要支援 ODS／ODP／ODG 就要動這個開關，而
`libreoffice-26-8/configure.ac:4371-4392` 的實際行為是：

| 想要的格式 | 開關值 | 實際會進來的 |
|---|---|---|
| ODS | `calc` | Calc |
| ODP | `impress` | **Basic ＋ Draw ＋ Math ＋ Impress，一次全部**（同一個 `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS`） |
| ODG | **沒有 `draw` 這個值** | 只能搭 `impress` 一起進來 |

接受值只有 `writer`／`calc`／`impress`，其餘 `AC_MSG_ERROR`（`:4388-4390`）。

上游自己在 `configure.ac:2327-2328` 留了這句：

> `# Don't include impress by default. Debug builds become too large for Chromium`
> `# with 'calc impress writer' enabled. (buffer source exceeds maximum size)`

**（2026-08-20 下修）**本文初版把這句讀成「三個模組一起編載不動」，那太強了。兩點更正：

1. 它寫的是 **debug** build。我們是 `-Oz`，不在它的射程內。
2. **外部證據顯示 release build 做得到。**ZetaOffice 出貨的 `soffice.wasm`（36.3 MB brotli）裡
   `swriter`／`scalc`／`simpress`／`sdraw` **四個都在**，而且它在瀏覽器裡跑得起來——見
   [產品路線與競爭者盤點](./RESEARCH-2026-08-20-product-route-and-competitors.md) §4.3.2。

⇒ 這句註解**不再是 M4 的風險理由**，只是「預設值為何不含 impress」的歷史說明。M4 閘門 0 仍然要
跑，但**預期結果是通過**（見 §6.1）。

**順帶一個有用的外部參考點**：四個 app ＋ 完整 Qt UI 可以塞進 36.3 MB（brotli）。我們現在
Writer-only headless 是 40.9 MB（gzip）。所以加模組**不必然**讓體積爆炸——但那顆 binary 是別人的
build，flags 與裁切策略都未知，**不能拿來當我們的預估**（該文第 7 節待驗證第 8 項）。

### 1.2 後果

**多支援格式不是「多加一個 filter」，是換掉整個體積基線。**先壓縮再擴格式，R10 的每一個裁切
決定都要重來一次——這正是 roadmap 第 8.1 節寫死的那句：

> 先裁切再補能力，等於保證要重編一次 corpus 與 A/B artifact。

**（2026-08-20）這一條不受 §1.1 的下修影響。**排序衝突講的是「**裁切決定會失效**」，不是「體積會
爆炸」。即使加模組之後體積只多一點，一個在 Writer-only binary 上做的 filter allowlist 或 library
移除決定，在四個 app 的 binary 上仍然要重新 inventory、重新 A/B、重新判定。

### 1.3 處方：把「壓縮體積」切成兩半

| | 範圍 | 位置 |
|---|---|---|
| **M2a** | 換模組也不會作廢的減量：工具鏈、資源分包、傳輸層 | **M3 之前** |
| **M2b** | core feature slicing：filter allowlist、component／library 移除、資源裁剪 | **M4 之後** |

這樣使用者的排序意圖（先能出貨再擴格式）保得住，代價是壓縮分兩次做。

**⇒ 建議順序：M1 → M2a → M3 → M4 → M2b → M5**

**（2026-08-20 修訂）**a11y 提前之後：**M1 → A11y → M2a → M3 → M4 → M2b → M5**（見 §3）。

---

## 2. M1 — 核心：能讀 ＋ 簡單寫 ODT

**現況：快到了。**（已觀察，2026-08-19 收工）驗收清單 13 done ／ 1 partial ／ 2 blocked，
`KNOWN_RED` 空的，佇列 45 項、0 項擋連結，產品路徑 34 條路徑中 20 條被驅動。

| | |
|---|---|
| **完成判準** | 清單全綠 ＋ 每個 `done` 的檢查綠 ＋ **沒有 `blocked`** ＋ D0 跑完、矩陣凍結 |
| **不需連結** | 剪下真的能刪（先**量**範圍刪除再宣告，不要先放寬 manifest）／14 條 uncovered 路徑接進回歸網／復原的第二個誘發器（解除對未修的 038 的依賴） |
| **需真人** | 剪貼簿的 OS 邊界輪（權限提示、真的 Ctrl+V）。**排在「剪下能刪」之後**，否則只量到半條路 |
| **需連結（要決定）** | redo ＋ 上下鍵。引擎做得到，但產品 wire id 已用滿 15 個 ⇒ **ABI 變更 ＋ 第三次連結**。動的是契約不是實作 |
| **風險** | 低。所有缺口都已具名 |

**⚠ 這是 M1 唯一的岔路**：ABI 變更做不做，決定 M1 是「再連結一次」還是「就這樣收」。

---

## 3. A11y — 無障礙（機構市場的採購門檻）

### 3.1 為什麼它從長期提前到這裡

2026-08-17 的裁示是「a11y／block identity 移到長期，**不要為它提議重編 core**」。
**2026-08-20 推翻**，因為那個裁示的前提變了：它成立於「短期目標＝能用的編輯器」，而買家確定是
**機構**之後，a11y 從「功能」變成**採購門檻**。

外部佐證：Collabora Online 26.04 把 **BITV 2.0 認證**（德國無障礙標準）放進發布公告的頭條功能。
他們花錢去拿那張證，正是因為歐洲機構採購會查。

**這是一次反轉，不是澄清。**舊裁示的技術理由（要改 `configure.ac` ＋ 重編 core）**仍然成立**，
只是不再是「不做」的理由。

### 3.2 為什麼放在 M2a 之前，而不只是 M3 之前

使用者的指示是「提前到 Nextcloud app 之前」。本文再往前放一格，兩個理由：

1. **先問風險最高的問題（強）。**「WASM 上的 LOK accessibility 到底能不能用」**完全沒有量過**
   ——finding 056 只證明了**今天**不能用，沒有證明**改好組態之後**能用。若答案是「改了還是
   不行」，那是產品層級的壞消息，會回頭影響 M3 該不該做、怎麼做。這種問題不該排在兩個
   milestone 之後。
2. **體積基線（弱）。**a11y 會把 `sw/source/core/access` 的 26 個物件編進來，也是動基線。但量級
   跟 M4 差很遠（26 個物件 vs 三個 app），所以這是判斷題不是規則。

### 3.3 閘門 0：核心那一半（不通過即停）

改 `configure.ac` ＋ 重編 core ＋ **只問一件事**。

**修法已定位**（finding 057）：`ENABLE_WASM_STRIP_ACCESSIBILITY` 有兩個獨立存在——Make 變數由
`--with-wasm-module` 決定（`configure.ac:4372/4379/4386`），C++ 巨集由 `--enable-wasm-strip`
決定（`:3498`），而後者在 Emscripten 上於 `:1280` **無條件 yes**。兩個方向：讓 `AC_DEFINE` 跟著
module 決策走，或把 `:1280` 改成「使用者沒指定才預設」。

**閘門的問句**：LOK 在 WASM 上**吐不吐得出 focused paragraph**？

- 吐得出來 → 進 §3.4。
- 吐不出來 → **停。**不要往殼層那一半投入，並把結果回報給 M3 的產品定位。

⚠ **不是修法**：把 `calc` 加回 `--with-wasm-module`。finding 057 已否決——那只會讓物件被編進去、
呼叫端仍被巨集拿掉，換來的是體積不是能力。

### 3.4 第二半：殼層的 ARIA 投影（**目前是零**）

**螢幕報讀軟體讀不到 canvas。**我們整份文件畫在一張 canvas 上，所以核心給的資料（焦點在哪一段、
游標在哪、文字是什麼）**必須被投影成報讀軟體讀得懂的 DOM**。

這條路現在**一行都沒有**，而且可能比核心那一半大。**閘門 0 沒過就不要開始。**

### 3.5 順手該修的一個謊

佇列項 `queue-engine-must-report-core-lacks-accessibility` 仍開著：**引擎目前謊報
`enabled: true`**，而核心根本沒提供。不管 a11y 做不做，那個謊都該修——它也是
`tools/check_core_build_provides.py` 現在紅著、而且**應該紅**的原因。

### 3.6 完成判準

**待定。**要等閘門 0 的結果，也要先確認台灣公部門實際適用的無障礙規範等級（使用者比本文清楚，
見 §10）。**不要先寫死一個沒有依據的判準。**

### 3.7 由誰做

core 重編是使用者的範圍（見 `user-handles-core-rebuilds`）。重編前先 archive、先解除唯讀防護。

---

## 4. M2a — 與格式範圍無關的減量

| | |
|---|---|
| **進場基線**（已觀察） | 首載 **64 MB gzip ／ 169 MB raw**（wasm 40.9 ＋ base 7.3 ＋ CJK 15.5，gzip） |
| **範圍** | 工具鏈（LTO、`wasm-split`、PGO）／資源重新分包與延遲載入／傳輸層（Brotli、streaming compile、SW 快取契約）／字型策略 |
| **明確不做** | filter allowlist、component／library 移除、core 資源裁剪 ⇒ 那些是 M2b |
| **完成判準** | 每個裁切單位走完 R10 的六道證據：inventory → 凍結矩陣 → A/B artifact → **全量** corpus → desktop round-trip → **演練過的** rollback。門檻在結果之前寫死 |
| **量什麼** | raw 與 gzip **分列**，且**必量瀏覽器 cold compile 與 runtime memory**——只量 bytes 不構成證據（R10 §4.3） |
| **已量到的天花板** | R5 實測：`writer-reader` 把 API 縮到剩五個呼叫，binary 只小 **1.6 KiB**。**削 API 沒用。**M2a 能拿到多少，不先給數字 |

---

## 5. M3 — 建立 Nextcloud app

### 5.1 閘門 0：COOP/COEP（**最先做，它決定 app 長什麼樣**）

**已觀察**：SharedArrayBuffer 是硬需求（`PTHREAD_POOL_SIZE=7`）；而 Nextcloud server 31.0.13 的
`lib/` 與 `apps/` 裡 **grep 不到任何一行 COOP/COEP**。

`COEP: require-corp` 掛上之後，該頁**每一個子資源**都要帶 CORP/CORS——大頭貼、預覽圖、主題 CSS、
其他 app 的資產。掛在標準 Nextcloud 介面上會壞掉一片。

三個候選繞法（**全部待驗證**）：

1. 專屬路由／iframe，只載自包含資產
2. 獨立 origin
3. `COEP: credentialless`（只有 Chrome）

**推論**：這個 app 多半不能長成「Files 側邊欄就地開啟」，比較像「另開一條乾淨的編輯路由」。
**閘門 0 不先過，後面全部白做。**

### 5.2 已確認不是問題（已觀察）

- **CSP**：`EmptyContentSecurityPolicy::allowEvalWasm()` 存在（`:122`），吐 `'wasm-unsafe-eval'`（`:466`）
- **Files 整合**：`registerFileAction(new FileAction({…}))`，NC 28 以後的標準做法

### 5.3 第二個坎：169 MB 靜態資產

必須 web server 直出、immutable 快取、**不穿過 PHP**。而且**這體積上不了 App Store tarball**
（推論，上限未查），得另想發布——安裝時下載，或分開散布。

### 5.4 還要接的

WebDAV 讀寫、檔案鎖、版本、衝突處理。Nextcloud 都有，但 app 得真的用，不能自己另做一套。

### 5.5 完成判準

在一台**乾淨的** Nextcloud 上：從 Files 點開一份 ODT → 編輯 → 存回 → 版本正確 → 鎖正確，
**且整個流程沒有任何伺服器端文件行程**。

### 5.6 定位對照（已觀察）

Euro-Office Docs 要一台 Document Server：**最低 4 GB RAM、建議 8 GB、10 GB 磁碟**、
HTTPS 雙向可達、還要能反向 POST 回 Nextcloud。**我們要 0 台。**

---

## 6. M4 — 能讀 ODS、ODP、ODG

### 6.1 閘門 0：載得動嗎（不通過即停）

`--with-wasm-module='calc impress writer'` **編得出來嗎、瀏覽器載得動嗎？**
**一次 core 重編 ＋ 一次開頁**就有決定性答案。

**（2026-08-20 下修）預期結果是通過。**初版把 `configure.ac:2327-2328` 那句註解當成風險理由，
但它講的是 debug build，而 ZetaOffice 已經在出貨一個含 `swriter`／`scalc`／`simpress`／`sdraw`
四個模組的 release build（36.3 MB brotli，瀏覽器裡跑得起來）。

**閘門仍然保留**，理由改成兩個：

1. **他們的 profile 不是我們的 profile**——flags、裁切策略、Qt UI vs headless 全都不同，
   外部證據不能替代我們自己的量測。
2. 這道閘門真正要防的是**組合失敗**（連結不過、載入失敗、啟動卡住），不是體積大小。

⇒ 它從「可能會擋下 M4 的高風險閘門」降級為**便宜的例行確認**。真正的風險移到閘門 1（記憶體）。

### 6.2 閘門 1：記憶體撐得住嗎

現況（已觀察）：單一 Writer 文件 `sbrk` 290.8 MB、PSS Chrome 440–446 MB／Firefox 670–751 MB，
而線性記憶體是**固定 1 GB、不可增長**。加三個模組之後**沒有人量過**（待驗證）。

**（2026-08-20）這裡才是 M4 真正的風險**，因為 §1.1 下修之後閘門 0 幾乎確定會過。而 ZetaOffice
那個外部參考點**幫不上忙**：他們的記憶體用量沒有公開，我們也沒量過（見產品路線文件 §6 表格
「使用者端記憶體」列）。

### 6.3 SDK 側前置（便宜，可提前做）

finding 013：公開 `open()` 目前**在 content detection 之前用副檔名拒絕**。改成 allowlisted
`format` 封閉列舉，讓驗證、實際 MEMFS path、manifest capability 三者一致——**不公開任意 path
或 raw filter 名稱**。

### 6.4 代價要先講清楚

**ODG 沒有自己的開關**，跟 **Basic ＋ Math ＋ Impress** 綁在同一個旗標上。
要不要把 Basic 腳本引擎放進 binary，**是產品決定不是技術決定**（攻擊面）。

**外部佐證**：ZetaOffice 的資源清單裡 `sdraw` 命中 101 次、`simpress` 155 次——**兩者確實是一起
出貨的**，與 `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS` 的讀法一致。

### 6.5 完成判準

比照 R7-C：逐檔 corpus 過 open／render／search／save／desktop round-trip ＋ fidelity 分類。
**不是「開得起來」就算。**

### 6.6 由誰做

core 重編是使用者的範圍（見 `user-handles-core-rebuilds`）。重編前先 archive、先解除唯讀防護。

---

## 7. M2b — core feature slicing

M4 把功能 corpus 換掉之後才動：filter allowlist、component／library 移除、UI／config／gallery
資源、scripting policy、LTO／`wasm-split`／PGO 的第二輪。

**這才是能大幅縮 code 的那一半**，也是 R5 唯一證明「只有它有用」的那一半。
證據要求同 M2a（R10 §4 六道），逐單位判定，**不並行多個未判定單位**。

---

## 8. M5 — 能簡單修改 ODS、ODP

**這是最大的一塊，不是最小的。**

| | |
|---|---|
| **為什麼大**（推論，但有強證據） | 現有 15 個 action、readback barrier、游標與選取模型，**全部是 Writer 文字模型形狀的**。Calc 是儲存格模型、Impress 是形狀模型，**沒有一項直接轉移** |
| **要重跑的** | 每個 app 各自走一次 discovery → 窄合約 → validation（E1／E2 那一整輪） |
| **建議範圍** | 各自先定義到「最小可用」——Calc：改儲存格內容 ＋ 基本格式；Impress：改文字框文字。**不要一開始就承諾形狀編輯** |
| **前置** | M4 全數通過 |
| **明確不做** | **ODG 只讀不寫** |

---

## 9. 移到長期、目前不排的

| | 理由 |
|---|---|
| ~~**a11y**~~ | **2026-08-20 移出長期，成為 §3。**買家確定是機構之後，它是**採購門檻**不是功能。原本的技術理由（26.8 的 Emscripten 上沒有任何旗標組合能開，要改 `configure.ac` ＋ 重編 core；finding 056／057）**仍然成立**，只是不再是「不做」的理由 |
| **block identity** | LOK 沒有段落序號，段落文字是指紋不是身分。設計已寫（把 `placeCaret` 變成有回傳值的呼叫），短期目標把它推遲了。**注意**：a11y 提前**不會**順帶把它拉上來——它們共用資料來源，但 §3 的閘門 0 只問 focused paragraph，不問 block identity |
| **Mobile app** | 不是工程問題，是未量測的問題。**先量一台真機能不能配置 1 GB SharedArrayBuffer**，結果是二元的 |
| **DOCX** | 明確低順位（2026-08-05 產品決定）。最小安全修法已在 finding 013 框定，但框定不等於排程 |
| **E4 Markdown** | G0（WASM reachability）很便宜，可在 M1 收尾期間順手跑掉。**但跑 G0 不等於授權 E4** |
| **上游送出** | 2026-08-15 起全線擱置。重啟時先重查重複單 |

---

## 10. 待決定（需使用者點頭）

1. **M1 的 ABI 變更**（redo ＋ 上下鍵）做不做。
2. **M2 拆成 M2a／M2b 接不接受。**不拆的話 M2 得整個移到 M4 之後，M3 就要背著 64 MB 出貨。
3. **台灣公部門實際適用的無障礙規範與等級**——決定 §3.6 的完成判準寫得出來沒有。**本文問不出來，
   使用者比本文清楚。**

---

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-20 | **a11y 從長期目標提前，成為新的第 3 節。**使用者裁示提前到 Nextcloud app 之前；本文再往前放一格到 M2a 之前，理由是「WASM 上的 LOK accessibility 能不能用」**完全沒量過**（056 只證明了今天不行，沒證明改組態之後行），這種高不確定性的問題應該早問。**這是一次反轉**——2026-08-17 的裁示是「a11y 移到長期、不要為它提議重編 core」，其前提是「短期目標＝能用的編輯器」；買家確定是機構之後，a11y 從功能變成**採購門檻**（外部佐證：Collabora Online 26.04 把 BITV 2.0 認證放進頭條）。新節寫了兩半：核心那一半有閘門 0（改 `configure.ac` ＋ 重編，只問「吐不吐得出 focused paragraph」，不過就停），殼層那一半是**目前為零的 ARIA 投影**（報讀軟體讀不到 canvas）。並記下「把 `calc` 加回 `--with-wasm-module` 不是修法」（057 已否決）。§9 把 a11y 那列劃掉並註明移出理由；§10 新增一項只有使用者答得出來的問題（台灣公部門的無障礙規範等級）。**第 3 節之後全部順延一號**：前一列修訂紀錄提到的 §5.1／§5.2／§5.4 現為 §6.1／§6.2／§6.4，§4.x（M3）現為 §5.x。 |
| 2026-08-20 | **下修 §1.1 與 §5.1 對 `configure.ac:2327-2328` 那句註解的引用。**初版把它讀成「三個模組一起編 Chromium 載不動」，據此把 M4 閘門 0 設為高風險。更正：那句寫的是 **debug** build，而 ZetaOffice 正在出貨一個含 `swriter`／`scalc`／`simpress`／`sdraw` 四個模組的 release build 且瀏覽器跑得起來（36.3 MB brotli，實測見產品路線文件 §4.3.2）。⇒ 閘門 0 從「可能擋下 M4」降級為**便宜的例行確認**，理由改成「他們的 profile 不是我們的 profile」與「要防的是組合失敗不是體積」；M4 的真正風險移到閘門 1（記憶體），而那一格外部參考點幫不上忙。同時在 §1.2 明確標註**排序衝突不受此次下修影響**——那一條講的是裁切決定會失效，不是體積會爆炸。§5.4 補上 `sdraw`／`simpress` 一起出貨的外部佐證。 |
| 2026-08-20 | 初版。依使用者提出的五項順序展開，插入 Nextcloud app 為 M3；查出 `--with-wasm-module` 的實際行為並據此指出「壓縮在擴格式之前會導致重做」，處方為把壓縮切成 M2a／M2b。 |

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

**規範已定（2026-08-23，使用者提供來源）：[網站無障礙規範（110.07）]
(https://accessibility.moda.gov.tw/Accessible/Guide/68)**，數位發展部無障礙網路空間服務網。

| | |
|---|---|
| 實施 | 2021-07-01（民國110年7月），取代舊的「網站無障礙規範 2.0 版」 |
| 基礎 | **WCAG 2.1** |
| 結構 | 4 原則、13 指引、**78 條成功準則**（規範自述） |
| 等級 | **A**（必須滿足，否則某些使用者「將不可能使用」）／**AA**（應該滿足，否則會「遇到困難」；滿足後「移除顯著障礙」）／**AAA** |
| 範圍 | 從桌機擴及**行動裝置** |

**⚠ 更正（2026-08-23）：本表原本寫「AA ＝ 須符合第1及第2優先等級，共 68 條檢測碼」，
那是錯的。**規範全文裡「68」出現 **0** 次、「優先」出現 **0** 次——「優先等級」是舊的
**2.0 版**用語，110.07 用的是「檢測等級 A／AA／AAA」。那個數字來自搜尋結果的 AI 摘要
（它把新舊兩版混在一起），而我把摘要當成規範原文寫了進來。**引用一份自己沒讀過的
文件，就是在引用別人的讀法。**

**規範原文取得後量到的**（`research/reference/`，2026-08-23 用 Playwright 取得，
使用者手動通過 Cloudflare 挑戰）：

- 抽出 **77／78** 條成功準則，等級分布 **A=30、AA=20、AAA=27** ⇒ **A+AA = 50**，
  與 WCAG 2.1 的 30+20 完全吻合，這是抽取正確的交叉驗證；
- 碼 **239 條相異**，其中 **30 條以 C 結尾**、**209 條以 E 結尾**。
  **沒有任何一個層級對得上 68**，所以那個數字不知從何而來。

  **⚠ 二次更正（2026-08-23）：上一行原本在括號裡寫「C＝檢測碼、E＝稽核評量碼」，
  那個對應是我推的，沒有依據，已撤下。**規範本文確實區分「檢測碼」（可由軟體自動
  檢測）與「稽核評量碼」（人工自我評量），但**沒有任何一句話把它們對到 C／E 這兩個
  尾字母**——定義在頁面「編碼規則及格式說明」那個分頁，而這次抓下來的全文沒有涵蓋
  那一節。**同一天的第二次「把自己的讀法當成文件的說法」，機制跟 68 那次一模一樣。**
  要結案就把那一節抓回來，一句話的事。詳見
  `research/DESIGN-2026-08-22-aria-projection.md` §7.4。

**仍未證實，不當事實用**：「政府機關網站一律須達 AA」沒有查到白紙黑字的法源。

#### 這個答案把 §3.4 的範圍推大了

WCAG 2.1 裡真正咬到一個 canvas 編輯器的，至少有：

- **1.3.1 Info and Relationships（A 級）**——文件的資訊與關係必須是**程式可判定**的。
  標題是標題、清單是清單、段落是段落。
- **1.1.1 Non-text Content（A 級）**——canvas 要有文字替代。
- **2.1.1 Keyboard（A 級）**——全功能鍵盤可達。
- **4.1.2 Name, Role, Value（A 級）**、**4.1.3 Status Messages（AA）**、
  **2.4.7 Focus Visible（AA）**、對比度那幾條（AA）。

2026-08-23 出貨的投影**只有焦點段落，而且不帶角色**。照 1.3.1 看，那不是「範圍邊界」
而是**缺口**：全文件結構投影是 A 級門檻，不是加分項。

✅ **1.3.1 的等級不再是判讀，是規範原文**：「成功準則1.3.1：資訊與關連性
**(檢測等級A)** 由呈現方式所傳達的資訊、結構與關連性要能以程式化的方式判讀，或者有
對應的文字。」它底下掛 18 條碼，第一條 `HM1130100C` 就是「網頁中的標頭組件必須要按照
正確的巢狀層次結構來配置」——正是投影在做的事。

⚠ 其餘各條仍是**依 WCAG 條文的判讀，尚未逐條對照檢測碼**。判準在那份對照做完之前
**仍然不寫死**——但現在不寫死的理由變了：不是沒有規範，是還沒把規範翻成這個產品的
動作清單。

已做的那一半在 [`DESIGN-2026-08-22-aria-projection.md` §7]
(DESIGN-2026-08-22-aria-projection.md)：咬到 canvas 編輯器的九條，逐條標了現況。
**沒做的那一半需要官方文件**，而 `accessibility.moda.gov.tw` 對自動抓取回 403、
NCC 鏡站解析不到 ⇒ **取得那份文件是使用者做得到而我做不到的事**，記在 §10。

### 3.7 由誰做

core 重編是使用者的範圍（見 `user-handles-core-rebuilds`）。重編前先 archive、先解除唯讀防護。

---

## 4. M2a — 與格式範圍無關的減量

| | |
|---|---|
| **進場基線** | **要重量，見下方「基線改綁 writer+calc」。**舊值 64 MB gzip ／ 169 MB raw（wasm 40.9 ＋ base 7.3 ＋ CJK 15.5，gzip）是在 **writer-only** 的 core 上量的，那顆不會出貨了 |
| **範圍** | 工具鏈（LTO、`wasm-split`、PGO）／資源重新分包與延遲載入／傳輸層（Brotli、streaming compile、SW 快取契約）／字型策略 |
| **明確不做** | filter allowlist、component／library 移除、core 資源裁剪 ⇒ 那些是 M2b |
| **完成判準** | 每個裁切單位走完 R10 的六道證據：inventory → 凍結矩陣 → A/B artifact → **全量** corpus → desktop round-trip → **演練過的** rollback。門檻在結果之前寫死 |
| **量什麼** | raw 與 gzip **分列**，且**必量瀏覽器 cold compile 與 runtime memory**——只量 bytes 不構成證據（R10 §4.3） |
| **已量到的天花板** | R5 實測：`writer-reader` 把 API 縮到剩五個呼叫，binary 只小 **1.6 KiB**。**削 API 沒用。**M2a 能拿到多少，不先給數字 |

### 4.1 基線改綁 writer+calc（2026-08-23 決定）

a11y 閘門 0 過了，產品 core 因此改成 `writer calc`（使用者裁示），
`probe.wasm` 實測 115,297,675 → 135,216,207（+19.9 MB），
`soffice.data` 102,765,226 → 108,527,803（+5.8 MB）。

**舊基線描述的是一顆不會出貨的 build，所以它作廢。**這棵樹已經為「釘在消失的
artifact 上的理由」付過一次代價（覆蓋率登記簿的過期理由，2026-08-22）。

三件事跟著定下來：

**一、要重量，不要用加法算。**64 MB gzip 不能加 19.9 MB raw 得到新值——gzip 不是
線性的，而且 M2a 的判準本來就寫著「raw 與 gzip 分列，且必量瀏覽器 cold compile 與
runtime memory」。**用算的那個數字是記憶不是量測。**

**二、量在會出貨的那顆上，也就是 `e2-editor-v5`，不是 `a11y-projection`。**後者是
開發用 artifact。在它上面重綁基線，等於再綁一次就要再作廢一次。⇒ **M2a 的進場量測
排在 v5 連結之後**，在那之前 M2a 沒有基線，這是誠實的狀態不是待辦。

**三、不要為了拿掉 calc 再重編一次 core。**calc 進來只是清掉
`ENABLE_WASM_STRIP_ACCESSIBILITY` 的槓桿，對 Writer 產品本身沒有用處，所以「writer
＋ a11y、不含 calc」看起來像 M2a 最便宜的一刀（三行 configure ＋ 一次重編）。

**但 §6（M4）要讀 ODS，那本來就需要 calc。**M2a／M2b 當初拆開的判準就是
「換模組會不會讓這項減量作廢」（§1.3），而拿掉 calc 正是**會被 M4 原樣還原**的那一種。
所以它不屬於 M2a，甚至不屬於 M2b——它根本不該做。

**這一項推翻 2026-08-22 我自己給的建議**（「先花一次重編量 writer 不含 calc 再決定」）。
當時的理由是「不要在不知道真正價碼的情況下把產品綁上 +19.9 MB」，那個理由**仍然成立**，
只是被一個更強的事實蓋過去：那 19.9 MB 裡屬於 calc 的部分，M4 會自己要回去。

---

## 5. M3 — 建立 Nextcloud app

### 5.1 閘門 0：COOP/COEP（**2026-09-28 已過；形狀＝E1h**）

**已觀察**：SharedArrayBuffer 是硬需求（`PTHREAD_POOL_SIZE=7`）；而 Nextcloud server 31.0.13、
33.0.8、34.0.2 裡 **grep 不到任何一行 COOP/COEP**。

**2026-09-28 更新——閘門 0 通過，推薦形狀 E1h**（已觀察）。計數執行
`findings/evidence/m3-gate-0/runs/2026-09-28T065153Z-apache-fpm.json`，判定是
`check_m3_gate0_report.py` 印出的那一行 `VERDICT E1h`；判準、fable 的裁決與全表見
`handoff/m3-gate-0/PREDICTION.md`、`RULING.md`、`findings/evidence/m3-gate-0/RESULT.md`。

能說的是：出貨的編輯器（七個 hash）在乾淨的 Nextcloud 34.0.2、Apache＋pretty URL 上，放在
**Nextcloud 頂欄底下的專屬路由**，所有引擎腳本（module JS、`sdk-worker.js`、`probe.js` 含
pthread）由 PHP 帶 COEP 送出、`.wasm` 靜態直出、資料檔走 PHP——Chrome 151 與 Firefox 156 各
3/3 開機、定位游標、做一個段落動作，全程 cross-origin isolated。沒有頂欄的 E3 也各 3/3。
負向對照（同一頁不帶 header）兩個瀏覽器都在開機時失敗、都沒有隔離也沒有 SharedArrayBuffer；
Chrome 的 log 把失敗歸因到隔離（`SharedArrayBuffer transfer requires self.crossOriginIsolated`），
Firefox 沒有能歸因的欄位（只記到 120 秒逾時），那一邊是相關不是歸因。

原本兩句要更正：

- ~~掛在標準 Nextcloud 介面上會壞掉一片~~——**在乾淨的實例上、在量到的範圍內不成立**：頂欄那一頁
  掛上 COOP＋COEP `require-corp` 之後，頁面載入加上點開一次 app 選單，Nextcloud 自己的失敗載入
  兩個瀏覽器都是零，頂欄指紋（167 個元素、id 的**數目** 22、8/8 張圖、app 選單 6 項）與不隔離時相同。
  偵測器的範圍要跟著講：Chrome 是 CDP 的 `loadingFailed`；Firefox 只看得到元素層級的失敗
  （`<img>` 全抓，`<script>`／`<link>` 只抓得到探針腳本執行之後的），被擋的字型、CSS 背景圖、
  `fetch`、iframe 在 Firefox 都看不到。
  有第三方 app 的機器沒量，而且有兩個方向：(1) **把 header 掛在別的 app 的頁面上，會弄壞那些 app**——
  這就是 nextcloud/richdocuments#4103：Nextcloud Office 在 Collabora 宣告支援 WASM 時，對每一個
  app framework 頁面加 COOP＋COEP（`v8.4.0` 起，2024-04），Maps 圖磚、Memories 預覽、Mail 內嵌 HTML
  被回報壞掉，2024-10-08 開單至今未關；(2) 在我們自己的隔離路由上，若有 app 往每一頁塞跨源、
  不帶 CORS 的子資源，會在我們這一頁被擋——A1 的 canary 就是它的模型，乾淨實例上沒有 app 這樣做。
  **(1) 是推薦形狀只隔離 app 自己路由的理由。**
- ~~`COEP: credentialless`（只有 Chrome）~~——**錯**：Firefox 156 也隔離，跨源 canary 照樣載得進來。

候選繞法的實測結果：

1. 專屬路由——**可行**（E1h／E3）。條件是**引擎的 worker 腳本本身要帶 COEP**：從 app 目錄直出的
   靜態 `sdk-worker.js` 不帶 COEP，兩個瀏覽器都在開機時死掉（E1，0/3）。Chrome 記下原因
   `coep-frame-resource-needs-coep-header`；Firefox 只記到產品的 `WORKER_CRASHED`，原因是從 Chrome
   加上瀏覽器規則**推論**的。
2. 獨立 origin——**沒量**（仍待驗證）；專屬路由已經夠用。
3. `COEP: credentialless`——兩個瀏覽器都隔離（見上）。
4. 在不隔離的頁面裡嵌 iframe——兩個瀏覽器都**不隔離**；`Document-Isolation-Policy` 只有 Chrome
   能讓它隔離。把 Files 整頁隔離，在乾淨實例上頁面載入時零新增失敗——但那正是 #4103 的形狀，
   **不當產品機制**；編輯器本身也從沒在 Files 裡跑過，所以「側邊欄就地開啟」既沒證明可行也沒證明
   不可行。⇒ 「只隔離自己的路由、另開一條編輯路由」是**依 #4103 做的選擇**（fable 裁決），不是量出來的
   不可能。

**已命名的限制**：nginx 沒量（header 是 PHP 設的，但 `.htaccess` 那條路與靜態白名單在 nginx 上
不同）、Safari 沒量、有第三方 app 的機器沒量、煙霧序列以外的互動沒量（COOP `same-origin` 會切斷
彈出視窗的 `window.opener`，這裡沒有東西走到）。

**帶進 M3 的工作項**：引擎腳本怎麼拿到 COEP。四條路——PHP（已量）、app `.htaccess`（只有 Apache）、
blob URL worker（要改產品，CSP 加 `worker-src blob:`）、COEP service worker——每一條都要先跑過
E1h 的序列、兩個瀏覽器各 3/3，才能取代 PHP。

### 5.2 已確認不是問題（已觀察）

- **CSP**：`EmptyContentSecurityPolicy::allowEvalWasm()` 存在（`:122`），吐 `'wasm-unsafe-eval'`（`:466`）
- **Files 整合**：`registerFileAction(new FileAction({…}))`，NC 28 以後的標準做法

### 5.3 第二個坎：169 MB 靜態資產

必須 web server 直出、immutable 快取、**不穿過 PHP**。~~而且**這體積上不了 App Store tarball**
（推論，上限未查），得另想發布——安裝時下載，或分開散布。~~

**2026-09-28 更正（已觀察）**：「上不了 App Store」**不成立為一般規則**。App Store 的原始碼預設下載上限是
`MAX_DOWNLOAD_SIZE = 30 MiB`（`nextcloud/appstore` `nextcloudappstore/settings/base.py:305`；文件範例寫 20 MiB），
但正式站在 2026-09-24 發佈了 `richdocumentscode` 26.4.402，套件是 **269 MB**（GitHub release asset；App Store API
`apps.json` 裡那個版本的 `download` 就指向它）。所以正式站沒有套用那個預設，或者對個別 app 有例外——**對我們的 app
適不適用未知**，要問或要試。體積仍是發布成本，但不再是「做不到」。

**2026-09-28 補充（已觀察，閘門 0 的 C7）**：「web server 直出」在 Apache 上只對一部分副檔名成立。
擋住其餘檔案的是 **Apache `.htaccess` 的副檔名白名單加上 pretty URL**（`nextcloud/.htaccess:207`；
裁決說官方映像也是如此，本樹未查），不是 Nextcloud 本身：白名單以外的一律改寫到 `index.php`。從 app 目錄實測：
`.js` 與 115 MB 的 `probe.wasm` 都是 200、位元組與磁碟相同；`sdk-manifest.json`、`.odt`，以及 v14
切分打包的 `.data`（40 MB）／`.metadata` 全部 404。⇒ v14 的 `.data`／`.metadata` 與所有 `.json`
要走 PHP 或另一條路由。nginx 的 `try_files` 會直出它們——**未量**，而且這個推論只讀了 DDEV 通用的
PHP 設定（`.ddev/nginx_full/nginx-site.conf:28`），沒讀 Nextcloud 文件裡的 nginx 設定。另外，直出的 `.js` 不帶 COEP，
worker 腳本就算能直出也不能直接用（§5.1）。

### 5.4 還要接的

WebDAV 讀寫、檔案鎖、版本、衝突處理。Nextcloud 都有，但 app 得真的用，不能自己另做一套。

**2026-09-28 補充（已觀察，M3 骨架）**：「從 Files 開檔」那一步走通了。`litecore` app
（`~/Projects/Nextcloud_Apps/litecore`）在 Files 點 ODT → 導到 E1h 形狀的編輯路由 → 瀏覽器經
WebDAV 取檔 → 出貨的編輯器開啟它並做一個段落動作，Chrome 151／Firefox 156 各 3/3，**產品位元組
一個都沒改**（`findings/evidence/m3-skeleton/RESULT.md`）。但接法是借道產品自己的「開啟檔案」輸入框，
因為產品頁**沒有給宿主用的入口**，代價有兩個：產品會先開自帶的範例文件（約占開檔時間一半），
而且**存回做不到**——產品的儲存是觸發下載，位元組到不了宿主。所以本節剩下的四件事（寫回、鎖、
版本、衝突）都先卡在同一個決定上：要不要給產品頁加一個宿主入口（收位元組、交位元組）。加了就是
換頁面身分，由擁有者決定。

**2026-09-28 再補充（已觀察）：擁有者選了加入口，已落地。**產品頁讀 `globalThis.liteCoreHost = { load, save }`
（`specs/SPEC-M3-host-entry.md`），殼層凍為 v53（`2e3a2021…`，只差頁面一個檔）。`litecore` app 用它開檔、存回、
處理衝突：存兩次、版本串接、Ctrl+S、衝突兩次都不覆寫且另存衝突副本、壞宿主被拒——Chrome／Firefox 各 3/3
（`findings/evidence/m3-host-entry/RESULT.md`）；沒有宿主時產品路徑回歸網 v8／v14 逐格與 v52 相同。開檔從
3.7–5.1 秒降到 2.5–3.1 秒。剩下的：**鎖**（423／唯讀 403 目前會把內容困在頁面裡）、**版本**（Nextcloud 自己會留，
還沒量）、以及「乾淨」在宿主收下之前就成立的殼層語意。

**2026-09-28 三補充（已觀察）：鎖與權限落地。**`litecore` app（`49cc4ab`）開檔時先取 WebDAV token 鎖、再讀版本，每 60 秒續約，離頁時解鎖；每一種被拒絕的存檔都有出路（423／412 走衝突副本、唯讀 403 另存到自己的資料夾、連副本都存不了就給下載）。12 臂 counted run `LOCKS LAND`，Chrome 151／Firefox 156 共 52 次全過，紅案 87 個全紅（`findings/evidence/m3-locks/RESULT.md`）；頁面、殼層、引擎都沒動。過程掉出三張上游 finding：100（OCS 上鎖端點該回 423 卻回 500）、101（token 鎖續約不會延長，宿主已繞過）、**102（token 鎖誰送都收——有寫入權的人拿持有者的 token 就寫得穿；我們靠 `If-Match` 不掉資料，但「開著時別人寫不進來」只對照規矩來的用戶端成立）**。關分頁**不會**釋放鎖（兩個瀏覽器都不會），鎖約 306 秒後自行失效。剩下的：**版本**（Nextcloud 自己的檔案版本在我們存檔後長什麼樣，還沒量）、頁面沒有唯讀模式、「乾淨」在宿主收下之前就成立的殼層語意。

**2026-09-28 四補充（已觀察）：版本正確。**`specs/SPEC-M3-versions.md`，宿主、頁面、殼層都沒動。HTTP 探針：我們的存檔在版本上跟一般用戶端沒有差別；上鎖、解鎖不產生版本；**從 Files 還原版本會穿過我們的 token 鎖**（files_lock 的儲存層不看 token 鎖），宿主下一次存檔 412、另存衝突副本。R1 經過真的頁面（開檔 → 存兩次 → 在頁面開著時還原 → 第三次存檔 → 離頁），計數執行 `VERSIONS CORRECT`，Chrome／Firefox 各 3/3，紅案 68 個全紅（`findings/evidence/m3-versions/RESULT.md`）：使用者做出的四個狀態（原檔、兩次存檔、第三次的副本）都逐位元拿得回來。過程掉出兩張上游 finding：**103（同一秒內別人的寫入不換 ETag，`If-Match` 擋不住，帶舊 ETag 的存檔會蓋掉它）**與 **104（同一秒內兩次寫入之後，任何還原都會讓第二次寫入永久遺失）**；鎖與權限、宿主入口規格與 101／102 的「帶 `If-Match` 所以不掉資料」已原地修訂。剩下的：頁面沒有唯讀模式、「乾淨」在宿主收下之前就成立的殼層語意（兩件都要換頁面身分），以及 §5.3 的資產派送。

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
3. ~~**台灣公部門實際適用的無障礙規範與等級**~~ —— **已答（2026-08-23）**：
   網站無障礙規範（110.07）／WCAG 2.1／AA ＝ 68 條檢測碼。見 §3.6。
   **接續的一項只有使用者做得到**：取得官方那 68 條檢測碼的文件（站台擋自動抓取），
   以便把「規範」翻成「這個產品要做什麼」的完整對照。
4. ~~**結構投影走哪條路**~~ —— **已裁決（2026-08-23，fable，使用者授權）：走 B，
   引擎給。**我提的「骨架走 A、用指紋接合」被駁回，理由量得出來：貼近真實的語料裡
   **42% 的文件有指紋碰撞、22% 的段落落在碰撞裡**（最糟一份 133 段塌成 28 個身分），
   而那還是樂觀值。加上「骨架變動時 shell 知道」是假的（autocorrect、follow-on
   style、沒有 wire id 的 redo），以及標題指紋塌縮本身是引擎缺陷、修它就要連結——
   A 躲不掉那次連結。處方見 `DESIGN-2026-08-22-aria-projection.md` §8。

---

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-09-28 | **§5.4 四補：版本正確**（`VERSIONS CORRECT`，R1 兩個瀏覽器各 3/3），掉出 finding 103、104。**§5.3 更正**：「169 MB 上不了 App Store」不是一般規則——原始碼預設上限 30 MiB，但正式站 09-24 發佈了 269 MB 的 `richdocumentscode`。 |
| 2026-09-28 | **§5.4 再補：宿主入口落地**（擁有者選 A）。頁面加 `liteCoreHost`、殼層 v53；開、存、衝突在兩個瀏覽器各 3/3；剩鎖、版本、「乾淨」的時機。 |
| 2026-09-28 | **§5.4 補 M3 骨架的結果**：從 Files 開 ODT 走通（`SKELETON WORKS`，兩個瀏覽器各 3/3，不改產品位元組），但存回、鎖、版本、衝突都卡在「產品頁沒有宿主入口」這個決定上。 |
| 2026-09-28 | **M3 閘門 0 通過，§5.1 改寫、§5.3 補 C7。**計數執行（`findings/evidence/m3-gate-0/runs/2026-09-28T065153Z-apache-fpm.json`）的判定是 `VERDICT E1h`：出貨編輯器放在 Nextcloud 頂欄底下的專屬路由，引擎腳本由 PHP 帶 COEP，Chrome 151／Firefox 156 各 3/3。**更正兩句**：「掛在標準 Nextcloud 介面上會壞掉一片」在乾淨實例上、在量到的範圍內（頁面載入＋一次選單，附偵測器範圍）不成立；有第三方 app 的機器沒量，而把 header 掛在別的 app 頁面上的代價有外部證據（nextcloud/richdocuments#4103），因此依裁決選擇只隔離 app 自己的路由（這是選擇，不是量出「就地開啟」不可能）；「`credentialless` 只有 Chrome」是錯的，Firefox 156 也隔離。§5.3 記下擋住 `.json`／`.data`／`.metadata` 的是 Apache `.htaccess` 白名單加 pretty URL，nginx 未量。引擎腳本如何拿到 COEP 的四條路列為 M3 工作項。 |
| 2026-08-20 | **a11y 從長期目標提前，成為新的第 3 節。**使用者裁示提前到 Nextcloud app 之前；本文再往前放一格到 M2a 之前，理由是「WASM 上的 LOK accessibility 能不能用」**完全沒量過**（056 只證明了今天不行，沒證明改組態之後行），這種高不確定性的問題應該早問。**這是一次反轉**——2026-08-17 的裁示是「a11y 移到長期、不要為它提議重編 core」，其前提是「短期目標＝能用的編輯器」；買家確定是機構之後，a11y 從功能變成**採購門檻**（外部佐證：Collabora Online 26.04 把 BITV 2.0 認證放進頭條）。新節寫了兩半：核心那一半有閘門 0（改 `configure.ac` ＋ 重編，只問「吐不吐得出 focused paragraph」，不過就停），殼層那一半是**目前為零的 ARIA 投影**（報讀軟體讀不到 canvas）。並記下「把 `calc` 加回 `--with-wasm-module` 不是修法」（057 已否決）。§9 把 a11y 那列劃掉並註明移出理由；§10 新增一項只有使用者答得出來的問題（台灣公部門的無障礙規範等級）。**第 3 節之後全部順延一號**：前一列修訂紀錄提到的 §5.1／§5.2／§5.4 現為 §6.1／§6.2／§6.4，§4.x（M3）現為 §5.x。 |
| 2026-08-20 | **下修 §1.1 與 §5.1 對 `configure.ac:2327-2328` 那句註解的引用。**初版把它讀成「三個模組一起編 Chromium 載不動」，據此把 M4 閘門 0 設為高風險。更正：那句寫的是 **debug** build，而 ZetaOffice 正在出貨一個含 `swriter`／`scalc`／`simpress`／`sdraw` 四個模組的 release build 且瀏覽器跑得起來（36.3 MB brotli，實測見產品路線文件 §4.3.2）。⇒ 閘門 0 從「可能擋下 M4」降級為**便宜的例行確認**，理由改成「他們的 profile 不是我們的 profile」與「要防的是組合失敗不是體積」；M4 的真正風險移到閘門 1（記憶體），而那一格外部參考點幫不上忙。同時在 §1.2 明確標註**排序衝突不受此次下修影響**——那一條講的是裁切決定會失效，不是體積會爆炸。§5.4 補上 `sdraw`／`simpress` 一起出貨的外部佐證。 |
| 2026-08-20 | 初版。依使用者提出的五項順序展開，插入 Nextcloud app 為 M3；查出 `--with-wasm-module` 的實際行為並據此指出「壓縮在擴格式之前會導致重做」，處方為把壓縮切成 M2a／M2b。 |

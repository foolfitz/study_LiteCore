# 產品路線與競爭者盤點

> **日期**：2026-08-20
> **文件性質**：討論紀錄與外部方案調查。**不是規格，不凍結任何範圍，也不構成執行授權。**
> **本地基線**：artifact `29ec627bf8a5588b…`（`e2-editor-v3`）、殼層 v25、LibreOffice 26.8
> **外部調查基線**：`cool-26-04` @ `c64a7343a5c6`、Nextcloud server 31.0.13、各家官方頁面（查訪日 2026-08-20）
> **相關**：[TDF Web 與行動版方向](./TDF-WEB-MOBILE-STRATEGY-2026.md)、[COWASM co-26.04 參考研究](./RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)

---

## 0. 文件定位

這份文件記錄 2026-08-19～20 的一輪討論：**這個研究能做成什麼產品，以及那個位置上已經站著誰。**

回答三個問題：

1. 已經量到的東西，把產品可能性限制成什麼形狀？
2. 兩個候選型態——mobile app 與獨立的 Nextcloud app——各自被什麼擋住？
3. 這個位置上的競爭者是誰，他們實際做到哪裡？

**本文刻意不做**：不排程、不承諾格式支援、不凍結 API、不對任何 milestone 給日期。排序另見
[milestone 文件](./ROADMAP-2026-08-20-milestones.md)。

沿用三種證據標記：

- **已觀察**：可由本機原始碼、建置產物、證據檔或官方頁面直接確認，並附位置。
- **推論**：由已觀察推導，尚未直接量到。
- **待驗證**：尚無證據，且已知怎麼取得。

---

## 1. 決定產品形狀的本地量測（全部為已觀察）

### 1.1 首載體積

R5 的 `-Oz` 產品連結 `writer-review`（`devlog/DEVLOG-2026-08-01-wasm-sdk-r5.md`）：

| 產物 | raw bytes | gzip -9 bytes | 首載 |
|---|---:|---:|---|
| `probe.wasm` | 115,265,157 | 40,861,878 | 是 |
| base pack | 34,178,400 | 7,312,172 | 是 |
| CJK pack | 19,484,784 | 15,503,708 | 是（zh-TW） |
| fallback fonts | 49,102,042 | 20,002,976 | **否** |
| **首載合計** | **169,071,606** | **63,713,911** | |

現行 `e2-editor-v3` 的 `probe.wasm` 是 110.0 MiB，同一個量級。

**R5 掉出來的、對減量最重要的一句**：`writer-reader` 把公開 API 縮到只剩 open／tile／search／
save／cancel，binary 只比 `writer-review` 小 **1.6 KiB**。LibreOffice core 佔絕大多數。
⇒ **削 API 不會讓它變小，只有可證明的 core feature slicing 會。**

### 1.2 記憶體

| | 值 | 位置 |
|---|---|---|
| 線性記憶體 | **固定 1 GB，`-sTOTAL_MEMORY=1GB`，無 `ALLOW_MEMORY_GROWTH`** | `wasm_sdk_probe/Makefile:418,782,833,851,1317` |
| `emscripten_get_heap_size()` | 常數 `1073741824`，384 個 stage 事件裡只有一個值 | `findings/evidence/sdk-e2/e2-c-validation/d4/heap/` |
| 真正會動的數字 | `sbrk`：單一文件 **290.8 MB**，同一引擎八份文件後 **338.7 MB** | 同上 |
| 行程 PSS（十輪） | Chrome **440–446 MB**、Firefox **670–751 MB** | `d4/summary.json` |

### 1.3 執行環境的硬需求

- `PTHREAD_POOL_SIZE=7`（主緒外七條）＋ SharedArrayBuffer
  ⇒ **cross-origin isolation 是硬需求**：`COOP: same-origin` ＋ `COEP: require-corp`
  （`wasm_sdk_probe/web/serve.py:15-16`）。

### 1.4 建置範圍

- 目前是 **`--with-wasm-module=writer`**——**Writer only**，Calc 與 Impress 都不在 binary 裡。
- 上游該開關的預設值其實是 `'calc writer'`（`libreoffice-26-8/configure.ac:2322-2326`）。

### 1.5 已知的能力天花板

- **a11y 在 26.8 的 Emscripten 上，沒有任何 configure 旗標組合能開起來。**
  `enable_wasm_strip` 於 `configure.ac:1280` 對 Emscripten **無條件 yes**，
  而 `ENABLE_WASM_STRIP_ACCESSIBILITY` 的 Make 變數與 C++ 巨集**接到不同輸入**
  （finding 056、057）。要動就得改 `configure.ac` ＋ 重編 core。
- **行動裝置、觸控 IME、瀏覽器外 virtual keyboard 從未進過範圍**
  （`specs/SPEC-R7-000-overview.md:100` 明列為範圍外）。

---

## 2. 候選型態一：Mobile app

### 2.1 判斷

**有潛力，但目前不是工程問題，是未量測的問題。**

擋住的不是下載量（64 MB 一次、可 immutable 快取，行動裝置上不算離譜），是這個組合：
**1 GB 不可增長的 SharedArrayBuffer ＋ 8 條執行緒 ＋ 440–750 MB 實際佔用。**

- iOS 上沒有選擇——WKWebView 就是 WebKit，包 Capacitor 也一樣。
  **一個 1 GB 的 shared `WebAssembly.Memory` 在 iPhone 上能不能配置成功，是這條路的生死題。**（待驗證）
- Android 旗艦大概撐得住 450 MB；中低階不會。Firefox 那組 670–751 MB 說明這個數字**跟引擎有關**，
  不是常數。（推論）

### 2.2 更根本的一層

產品的互動模型是「canvas ＋ pointer 事件 ＋ 用像素定位游標」：**沒有選取控制點、沒有捏合縮放、
沒有虛擬鍵盤協調**。其中選取控制點撞上已知未解的 block identity——LOK 沒有段落序號，段落文字是
指紋不是身分。

### 2.3 最便宜的下一步（待驗證）

把現行 artifact 用一台真手機開一次，量兩件事：**1 GB 配得起來嗎、PSS 多少。**
結果是二元的：配不起來，這條路現在就關；配得起來，它從「猜」變成「有前提的可行」。

---

## 3. 候選型態二：獨立的 Nextcloud app（**已選定**）

2026-08-20 使用者裁示：**走這條**（理由是路徑熟悉）。

### 3.1 它拿掉的東西

拿掉 richdocuments + Collabora Online 最貴的一塊：**伺服器上那個每使用者的 LibreOffice 行程**。
文件伺服器只負責發文件與協調，解析／排版／編輯留在使用者裝置——與 TDF 2026 的 Web/Mobile 策略
同向。

### 3.2 已查證的三件事（Nextcloud server 31.0.13 checkout）

| | 結論 | 位置 |
|---|---|---|
| **CSP** | **不是問題。**`EmptyContentSecurityPolicy::allowEvalWasm()` 存在，會吐出 `'wasm-unsafe-eval'` | `lib/public/AppFramework/Http/EmptyContentSecurityPolicy.php:122`、`:466` |
| **Files 整合** | 不是問題。`registerFileAction(new FileAction({…}))`，NC 28 以後的標準做法 | — |
| **COOP/COEP** | **這是真正的坎。**整個 `lib/` 與 `apps/` grep 不到任何一行 | 已 grep，`--include=*.php`，零命中 |

**為什麼 COEP 是坎**：`require-corp` 一旦掛上，該頁**每一個子資源**都要帶 CORP/CORS——大頭貼、
預覽圖、主題 CSS、其他 app 的資產。掛在標準 Nextcloud 介面上會壞掉一片。

三個候選繞法（**全部待驗證**）：專屬路由／iframe 只載自包含資產、獨立 origin、
`COEP: credentialless`（只有 Chrome）。

⇒ **推論**：這個 app 多半不能長成「Files 側邊欄就地開啟」，比較像「另開一條乾淨的編輯路由」。
**這件事會決定 app 長什麼樣子，所以要在最前面決定，不能拖到後面。**

### 3.3 第二個坎：169 MB 靜態資產

必須由 web server 直出、immutable 快取、不穿過 PHP。而且**這個體積上不了 App Store 的 tarball**，
得另想發布方式（安裝時下載，或分開散布）。（推論；未查 App Store 實際上限）

### 3.4 範圍要老實講

**Writer only、ODT only、15 個 closed action。**Calc 與 Impress 完全不在 binary 裡（見 1.4）。

---

## 4. 競爭者盤點

### 4.1 Collabora × allotropia：合併是真的，WASM 路線也是真的

**已觀察**：合併於 **2025-05-28** 完成。官方把 WebAssembly 明確列為併購理由：

> allotropia's expertise around Web Assembly combined with Collabora Online to, **in time**, enable
> customer use-cases such as office-as-component embedding scenarios in vertical applications as well
> as **off-line and end-to-end encrypted editing**.

注意 **in time** 是未來式。文中並提到併購前兩家就拿過德國內政部（BMI）的原型補助，做的正是
「讓 Collabora Online 能在瀏覽器裡離線使用」。

### 4.2 Collabora 的 WASM 實作：**是伺服器產品的離線備援，不是獨立產品**

**已觀察**，全部讀自本機 `cool-26-04` @ `c64a7343a5c6`：

| 證據 | 位置 |
|---|---|
| `--with-wasm-fallback`：「Build a COOL where the client can **fall back to a WASM implementation if the connection to the server fails**」 | `configure.ac:174` |
| 專案自稱 **COWASM**（Collabora Online as WASM） | `wasm/README.no-container.md:6` |
| 前端切換：`app.socket.sendMessage('switch_request offline')` | `browser/src/control/Control.UIManager.ts:561` |
| 部署開關 `window.wasmEnabled` | `browser/js/global.js:461` |
| **切回線上那半是被註解掉的 TODO** | `Control.UIManager.ts:562-565` |
| allotropia 的 zetajs 已接進建置系統 | `configure.ac:472-493`、`wasm/emscripten-zetajs-example.js`（註明改編自 allotropia 範例） |

**架構含意（推論）**：COWASM 不是「把編輯器搬到 client」，是**把 coolwsd 搬進瀏覽器**——前端仍講
同一套 COOL 協定。繼承 Collabora Online 的功能廣度（Writer/Calc/Impress 全套），也繼承整包架構。

**但他們不把它當產品賣**（已觀察）：Collabora Online 26.04 的發布公告裡，**WASM、離線瀏覽器編輯、
ZetaOffice、zetajs 一個字都沒提**。頭條是 AI 寫作助理、文件比對、BITV 2.0 無障礙認證、OOXML 互通。
COOL 的 WASM 從 FOSDEM 2023／2024 就在講，程式碼在樹裡，**不在行銷裡**。

### 4.3 ZetaOffice：**產品線已休眠**（併購後被吸收）

網站仍在，內容也還寫著 open beta，但**產品本身已經十五個月沒有動靜**。詳見 4.3.4——那一節是
本文最重要的更正之一。

**網站仍宣稱的**（zetaoffice.net，查訪日 2026-08-20）：

- Writer／Calc／Impress 瀏覽器版，**open beta**
- 桌面版（Linux／Windows）beta，行動版「coming soon」
- 開源，另賣 **CDN ＋ 商業支援**付費方案；可自架也可用其 CDN
- **沒有提到任何 Nextcloud 整合**
- 網站頁尾的著作權人已經是 **Collabora Productivity Germany GmbH**——併購在法人層面已完成

**一個容易搞混的**：allotropia 確有一個 Nextcloud app（`allotropia/nextcloud_files_libreoffice_edit`），
但那是**透過 WebDAV 叫起本機安裝的桌面 LibreOffice**，與 WASM 無關。**不是競品。**

#### 4.3.1 首載體積：沒有公開數字，所以直接量

他們沒有公布任何體積數字。取得路徑：demo 頁 → `pre_soffice.js` →
`assets/vendor/zetajs/zetaHelper.js` 裡的 CDN base `https://cdn.zetaoffice.net/zetaoffice_latest/`，
再對每個檔案發 HEAD（實測日 2026-08-20）。

| 檔案 | 線上實際位元組 | 編碼 |
|---|---:|---|
| `soffice.wasm` | 36,279,250 | **brotli 預壓** |
| `soffice.data` | 15,891,013 | brotli 預壓 |
| `soffice.data.js.metadata` | 215,180 | identity |
| `soffice.js` | 858,124 | identity |
| **合計** | **≈ 53.2 MB** | |

CDN 對 `.wasm`／`.data` **無視 `Accept-Encoding` 一律回 brotli**，所以上表就是實際傳輸位元組。

#### 4.3.2 他們的 binary 裡有四個 app

`soffice.data.js.metadata`（215 KB，可公開下載）逐項統計：`swriter` 302 次、`scalc` 245、
`simpress` 155、`sdraw` 101 ⇒ **Writer、Calc、Impress、Draw 全在裡面**，外加完整 Qt UI
（demo 走 `qtcanvas`，是 LO 自己的介面）。

**這否證了一個推論**：`libreoffice-26-8/configure.ac:2327-2328` 說 `calc impress writer` 撐爆
Chromium——那句寫的是 **debug build**，release build 顯然做得到，因為他們正在出貨。
（[milestone 文件](./ROADMAP-2026-08-20-milestones.md) §1.1 引用該註解時的語氣應據此下修。）

**同時是一個對我們不利的對照**：他們 36.3 MB（br）裝四個 app ＋ 完整 UI；我們 40.9 MB（gzip）
只有 Writer、headless、自畫殼。**我們的 binary 並不精實**，而 R10 從未啟動——這是第一個外部參考點。

#### 4.3.3 他們的資源包裡**沒有任何 CJK 字型**

同一份 metadata：`NotoSansCJK` 命中 **0**、`CJK` **0**、`.ttc` **0**。實際字型是 Liberation、
DejaVu、Caladea、Carlito、Amiri（阿拉伯）、DavidCLM／Alef（希伯來）等——**拉丁、阿拉伯、希伯來
都有，中日韓沒有。**

同基準對照（拿掉我們的 CJK pack）：

| | 無 CJK | 含 CJK |
|---|---:|---:|
| ZetaOffice | 53.2 MB（brotli） | 需另加約 15 MB |
| 本專案 | **48.2 MB**（gzip -9） | 63.7 MB |

而且比較還對我們不利——他們 brotli、我們 gzip。**⇒ 在 zh-TW 市場上，重量這個軸我們領先。**

**但這個領先只在我們持續拒絕做完整套件時存在**：milestone M4／M5（加 ODS／ODP／ODG）會把它吃掉。
做了之後就不能再喊輕，得換一個賣點。這一格的判讀見第 5 節。

#### 4.3.4 產品線已休眠：時間軸（全部實測，2026-08-20）

起因是使用者注意到 GitHub 自 2025-06 之後幾乎沒有更新。查下去發現 **GitHub 是最不重要的訊號**。

| 日期 | 事件 | 量到的方式 |
|---|---|---|
| 2024-11-08 | ZetaOffice 發表、open beta | 官方 blog |
| 2025-03-06 | **最後一篇產品文**（ZetaJS: Combining Writer & Calc） | blog RSS |
| **2025-05-13** | **CDN 上的 `soffice.wasm` 最後一次建置** | `last-modified` header |
| 2025-05-28 | 併購公告——**blog 到此為止，之後一篇都沒有** | blog RSS |
| 2025-05-30 | npm `zetajs@1.2.0`——**最後一個發布** | npm registry |
| 2025-11-20 | 官網最後一次更動 | `last-modified` |
| 2026-04-01 | zetajs 三個 commit（Stephan Bergmann，跟上游 embindtest 改版） | GitHub API |
| 2026-08-20 | **`business-cdn.zetaoffice.net` DNS 查不到** | `getent hosts` 無回應 |

三個最硬的證據：

1. **出貨的 binary 停在 2025-05-13**（`last-modified: Tue, 13 May 2025 15:18:14 GMT`）。十五個月沒有
   重新建置，而且那個日期**比併購早兩週**——併購之後那顆 WASM 一次都沒再編過。
2. **付費方案的 CDN 已不存在。**他們自己出貨的 `zetaHelper.js` 裡寫著 `cdn.zetaoffice.net`（免費）
   與 `business-cdn.zetaoffice.net`（商業），**後者現在連 DNS 都查不到**。
3. **2026-04 那三個 commit 不是產品開發**，是「Adapt smoketest to embindtest rework」——讓它還編得過
   上游，不是讓它變好。

**推論（使用者 2026-08-20 的判讀，本文採納）**：ZetaOffice 不是被關掉，是**被吸收**——那批人被抓去
推進 COWASM。這與第 4.2 節的觀察一致：`cool-26-04` 的建置系統裡有 `--with-wasm-zetajs`、
`--enable-wasm-embind-uno` 與一份改編自 allotropia 範例的 `wasm/emscripten-zetajs-example.js`。
**ZetaOffice 從一個產品，變成了 COWASM 的管線。**

**另一個解釋沒有被排除**：賣不動而停損。從外部無法分辨這兩者，而分辨結果會影響我們要不要投入
（見第 7 節待驗證第 11 項）。**不論是哪一個，都不改變一件事**：一支擁有世界最強 LibreOffice 專業
的團隊，做了正好這個東西、上線了，然後在六個月內安靜下來。

**一個救回我們論證的不對稱**（推論）：ZetaOffice 賣的是**給開發者嵌的橫向 SDK，而且沒有通路**。
本專案要做的是**給 Nextcloud 管理員的一個 app**——有通路（App Store、既有站台）、有具體買家、有具體
痛點（Euro-Office 要一台 4–8 GB 的伺服器）。所以 ZetaOffice 的失敗是「賣 SDK 給開發者」的失敗，
**不必然是「這個技術沒人要」的失敗**。

**威脅評估因此下修**：ZetaOffice 從「最接近的競爭者」變成**休眠中**。真正的風險改為
**Collabora 隨時可以喚醒它**——零件都還在。最可能的喚醒條件是一張歐洲主權的單子；他們本來就拿過
德國內政部（BMI）的離線瀏覽器編輯原型補助（見 4.1）。

### 4.4 Euro-Office：真正動到我們定位的那一個

**已觀察**：

- ONLYOFFICE 的分支，**2026-03-27 分叉，2026-06-09 首個穩定版**。
- 自 **Nextcloud Hub 26 Spring** 起成為 Nextcloud Office 的引擎；Collabora 與 OnlyOffice 降為
  「其他可選方案」。
- 聯盟：IONOS、Nextcloud、Proton、XWiki、OpenProject、EuroStack、Soverin、Abilian、BTactic、
  Open-Xchange、Tuta、**Office.EU**。
- 範圍：文書／試算表／簡報／PDF 四個網頁編輯器 ＋ **一台 Document Server**。
  ⇒ 它占的是原本 Collabora Online／ONLYOFFICE Docs 的那一格，**不是一整套辦公平台**。

**最關鍵的一點——它沒有拿掉伺服器**（已觀察，官方安裝文件）：

| Euro-Office Document Server | |
|---|---|
| 記憶體 | **最低 4 GB，多人部署建議 8 GB** |
| 磁碟 | 10 GB |
| 網路 | Nextcloud 與**所有終端使用者**都要能經 HTTPS 連到它；且它要能**反向 POST 回 Nextcloud** |

所以 `nextcloud.com/office` 上那句 "client-centric architecture / reducing server load" 指的是
ONLYOFFICE 那種架構——**編輯邏輯跑在瀏覽器 JS，但仍有一台 document server 做轉檔與共編協調**。
是「伺服器比較輕」，不是「沒有伺服器」。

### 4.5 命名澄清：Office EU **不是** Euro-Office 改名

一則中文報導寫「Office EU 先前名為 Euro-Office」。**查證後：錯的。**兩者是不同層。

| | **Euro-Office** | **Office EU**（office.eu） |
|---|---|---|
| 是什麼 | 開源專案／引擎 | **託管服務**（雲端訂閱） |
| 誰 | 上述聯盟 | 荷蘭公司 **EUfforic Europe B.V.**（海牙，KvK 98746243） |
| 關係 | — | **加入**該聯盟的成員之一 |
| 內容 | 四個編輯器 ＋ Document Server | EU Drive／Docs／Spreadsheet／Presentation／Calendar／Talk／Email |

Nextcloud 官方 blog 原句是「**Office EU joined the Euro-Office open source project**」——是加入不是
改名；Wikipedia 的 Euro-Office 條目亦明講它 *"isn't branded as Office.EU"*。

**為什麼會被寫成改名（推論）**：Office EU 把自家 app 取名 EU Docs／EU Spreadsheet／EU Presentation，
看起來像新品牌。但那份清單裡有 **Calendar、Talk、Email、Drive**——那是 **Nextcloud 的形狀**，不是
一套編輯器的形狀。Office EU 實際上是「把 Nextcloud ＋ Euro-Office 打包成歐洲託管服務來賣」的那一層。

### 4.6 生態剛洗過牌

**已觀察（二手，未經一手來源查證）**：ONLYOFFICE 於 2026-04 因這次分叉暫停與 Nextcloud 八年的
合作，授權爭議依 Wikipedia 於 2026-06 已解決。

⇒ **推論**：Nextcloud 的辦公引擎生態剛整個換過一輪——Collabora 還在但已非預設、OnlyOffice 退場、
Euro-Office 上位。這種時候多一個「架構上真的不一樣」的選項，比在穩定期插隊容易。

---

## 5. 字型：三個不同的問題，以及一次自我更正

§4.3.3 量到「ZetaOffice 沒有 CJK」之後，最初的判讀是「這是護城河」。**那句話太強，本節是更正。**

### 5.1 引擎不用瀏覽器的文字堆疊

**已觀察**：LibreOffice-in-WASM 自帶 VCL ＋ HarfBuzz ＋ FreeType，從 Emscripten MEMFS 讀**字型檔案**，
自己排版、自己柵格化，再把點陣圖 blit 到 canvas。整條路沒有 CSS、沒有 DOM 文字、沒有瀏覽器的
font matching。**使用者裝了什麼字型，WASM 模組看不到。**

本機佐證：`sdk/sdk-worker.js:452` 只接受 `/instdir/share/fonts/truetype/` 底下的路徑，R5 的分類器
就是照那個實際檔案路徑分包的。對這個引擎而言，字型是檔案，不是 family name。

### 5.2 缺 CJK 造成的其實是三件事，嚴重度差很多

| | 是什麼 | 有多硬 |
|---|---|---|
| **(a) 螢幕上看不看得到字** | 缺字型就是豆腐塊 | **不硬。**部署者配一份 CJK pack 就解決 |
| **(b) 排版與分頁** | 字型 metrics 決定斷行與分頁 → 分頁不同 → 匯出 PDF 不同 | **這一格才硬** |
| **(c) 他們的市場優先順序** | 阿拉伯、希伯來塞了，中日韓沒塞 | 時間問題，開個會就能改 |

**⇒ 更正**：先前「缺 CJK 比架構上零伺服器更硬」的說法，**(a) 的部分撤回**。真正耐用的論點見 5.5。

### 5.3 Local Font Access API：範圍太窄，而且解不掉 (b)

`window.queryLocalFonts()` 能用 `FontData.blob()` 拿到字型檔位元組，寫進 MEMFS 的管線我們現成
（resource pack 機制）。但：

| | |
|---|---|
| 支援 | **只有 Chromium 桌面版**（Chrome／Edge 103+） |
| Firefox | 未實作；Mozilla standards position **反對** |
| Safari | 未實作；方向是只暴露 OS 預設就有的字型 |
| 行動裝置 | **完全沒有**（Android／iOS 的 Chromium 亦無） |
| 其他 | 需權限提示；MDN 標 experimental、非 Baseline |

理由都是指紋辨識。⇒ 它成立的條件是「在 Chrome 桌面上、使用者按了同意之後」，當 fallback 可以，
當產品前提不行。**而且它解不掉 (b)**：它給的是「那台機器上有什麼」，不是「文件指定了什麼」。

### 5.4 第三方字型 CDN：技術可行，策略自傷

**已觀察（實測 2026-08-20）**：`fonts.gstatic.com` 回 `access-control-allow-origin: *` ＋
`cross-origin-resource-policy: cross-origin`，**滿足 `COEP: require-corp`**，不會被 cross-origin
isolation 擋掉。（多數 CDN 沒有這兩個 header，所以選 CDN 時這是硬條件，不是理所當然。）

**但 Google Fonts 唯一真正值錢的機制，我們取用不到**（實測）：

```
Noto Sans TC 的 CSS 有 105 條 unicode-range 切片
單一切片 content-length = 5,068 bytes
```

CJK web font 便宜，是因為**瀏覽器端**依 unicode-range 只抓用得到的切片。我們的引擎要的是一個字型
檔，所以只剩兩條路：抓完整一份（我們的 `NotoSansCJK-Regular.ttc` 是 19.5 MB raw／15.5 MB gzip，
跟自架完全一樣，只是換來源），或自己重做切片——那要先知道文件用到哪些字，而那要先解析文件，
文件又在引擎裡。**先有雞先有蛋。**

**格式（待驗證）**：Google Fonts 送 `font/woff2`。WOFF2 是網頁傳輸格式；`libreoffice-26-8/vcl/`
裡搜不到 WOFF2 loader，但那是「搜不到」不是「量過」。

**策略上的四個理由比技術理由更決定性**：

1. 定位是「數位主權、自架、資料不出機房」。每開一份文件打一次 Google，賣點當場破掉。
2. Nextcloud 社群正是最會擋外部 CDN 的一群；Nextcloud 自身 CSP 預設 `default-src 'none'`。
3. **德國有判決**：LG München 2022 年判網站嵌 Google Fonts 違反 GDPR、須賠償。目標客群（歐洲主權
   市場、公部門）法遵上不能打 Google。
4. Euro-Office 整個聯盟的存在理由就是「不受外國控制」。接 Google CDN 等於把對手的核心論述送給他們。

### 5.5 真正可守的是分包機制，不是字型資產

**已觀察**：R5 已把資源拆成 base ／ startup CJK ／ optional fallback fonts 三包，互斥、聯集完整、
逐包 SHA-256 驗證、可選擇性載入；那 116 個「其他字型」（阿拉伯、希伯來等，49 MB）**我們也有**，
只是不在首載。**ZetaOffice 是一包 15.9 MB 全下載，沒有分包機制。**

⇒ 可守的不是「我們有 CJK 而他們沒有」，是**「我們可以讓部署者決定要載哪些字型」**——台灣的部署只
載 CJK，歐洲的部署反過來。這比「他們缺 CJK」耐用得多：**他們補 CJK 只要開個會，補分包機制要改
架構。**而且這一招同時解掉 (a) 與一大半的 (b)——部署者能保證全組織用同一份字型，分頁就一致，而那
正是 5.3、5.4 兩條路都做不到的（每台機器裝的東西不一樣，分頁就不一樣）。

**誠實的技術債**：現行 pack 載入是 engine start 之前、manifest 驅動、雜湊驗證。要接受部署者提供的
字型是**契約改動**，不是現成功能；R5 DEVLOG 亦記著 optional pack 的觸發政策「尚未做文件 font
inventory 自動重啟」，所以按需載入今天需要重啟，不是熱插拔。

---

## 6. 定位結論

**我們設想的那一格沒有被占住。**

| | Euro-Office | Collabora CODE | ZetaOffice | 本專案 |
|---|---|---|---|---|
| 伺服器行程 | 要一台，**4–8 GB RAM** | 要一台，每使用者一個行程 | 無 | **0 台** |
| 產品狀態 | **2026-06 穩定版，活躍** | 活躍 | **休眠**（binary 停在 2025-05） | 研究中 |
| 使用者端首載 | 輕 | 很輕 | **53.2 MB**（br，四個 app，無 CJK；2025-05 的 build） | **48.2 MB 無 CJK ／ 63.7 MB 含 CJK**（gzip -9，Writer only） |
| 使用者端記憶體 | — | — | 未量 | 450–750 MB PSS |
| 字型 | — | — | **無 CJK**，一包全下載 | **有 CJK，三包可選擇性載入** |
| 引擎 | ONLYOFFICE 分支 | LibreOffice | LibreOffice | **LibreOffice** |
| 格式 | OOXML first（ODF 仍是開發目標） | 全 | 全 | **ODF 原生、ODT only** |
| 離線 | 否 | 否（COWASM 是斷線備胎） | 是 | **是** |
| Nextcloud 整合 | **預設引擎** | 有 | **無** | **無（機會所在）** |
| 對我們的威脅 | **最高（通路已被占）** | 中（架構方向相反） | **已下修：休眠，但可被喚醒** | — |

四句話：

1. **Collabora 沒有占住這一格**——他們的 WASM 是「有伺服器時的斷線備胎」，前提是你本來就有一台
   CODE；我們要的是「根本不要那台」。方向相反。
2. **ZetaOffice 最接近，但它休眠了**（4.3.4）——出貨的 binary 停在 2025-05，商業 CDN 的 DNS 已經
   消失。整合層本來就沒有人做（Files action、WebDAV 存取、COOP/COEP 那個坎），現在連引擎那一側也
   沒有人在推。**這個生態位目前是空的**——但空著的理由本身值得查清楚（第 7 節第 11 項）。
3. **差異化不能再喊「比較不吃伺服器」**——Euro-Office 已經在喊 client-centric 了。要喊的是
   **「引擎是 LibreOffice、格式是 ODF 原生、而且真的零伺服器行程」**。
4. **重量是可守的第二個軸，但有效期有限**——目前我們比 ZetaOffice 輕（48.2 對 53.2，且他們用較強的
   brotli），理由是我們只做一個 app。**M4／M5 一做，這個軸就消失。**字型那一格則見第 5 節：可守的是
   分包機制，不是「他們缺 CJK」。

---

## 7. 買家是機構：這條路線實際上賣給誰

第 6 節說明了「那一格沒被占住」。本節說明**那一格怎麼變成一筆生意**——以及它回頭對產品提出了
什麼要求。

### 7.1 機構不是一個使用者，是一條簽字鏈

賣給個人，要說服的是使用者。賣給機構，要通過的是**一串各自不想扛責任的人**：

| 誰 | 他要的 |
|---|---|
| 使用的人 | 能用、跟他習慣的差不多 |
| **資安** | 「這東西會不會做壞事」——要一張**表**，不是一句保證 |
| **採購／驗收** | 一份**驗收得完**的規格 |
| **維運** | 「誰要顧它」——編制、預算、值班 |
| 簽字的人 | 出事的時候，**他的決定站得住** |

功能只是入場券。**成交的是「這個決定辯護得了」。**

⇒ 這也是封閉 ABI（E1-B 的十五個具名動作、不外露 UNO）**第一次變現**的地方：它產出的正是可以放進
公文的東西。對**打字的人**它目前淨值是負的（redo／上下鍵／Ctrl+A／剪下都做不到），所以
**不要對使用者行銷封閉 ABI，要行銷它的結果**（不會靜悄悄壞掉、壞了不賠上整份文件、載得快）。
那張清單是講給資安與採購聽的。

### 7.2 三個關卡，跟一般使用者完全無關

**資安檢核**——機構會給一張表要填：會不會執行巨集？會不會連外？會不會讀本機檔案？資料到哪裡？

封閉界面填得完，而且填的是「**沒有那條路徑**」。開放的 UNO 界面在這張表上只能寫「視使用情境
而定」，那在資安審查裡等於不通過。

**採購驗收**——「LibreOffice 能做的都能做」是**無法驗收**的規格（驗收範圍無限）。十五個具名動作、
每個有後置條件，是**驗收得完**的。這是能不能寫進契約附件的差別。

**維運編制**——最實際的一關：**誰要顧那台 document server？**Euro-Office Docs 要一台最低 4 GB、
建議 8 GB、10 GB 磁碟、HTTPS 雙向可達的伺服器（§4.4）。對 IT 只有一個人、或根本沒有專職 IT 的
單位——學校、鄉鎮公所、小型機關——那不是「貴」，是**做不到**。

### 7.3 「零伺服器」對機構的真正意義

不是省錢，是**省掉一個要有人負責的東西**：沒有 CVE 要追、沒有容器要更新、沒有負載要規劃、
沒有機房要排。

**對維運合約的影響是反過來的**（**使用者 2026-08-20 提供的前提**：在台灣不會有機關把 Nextcloud
與雲端編輯器拆成兩個案子架設）：

| | 加進一份既有的 Nextcloud 導入案 |
|---|---|
| Collabora／Euro-Office | 多一台伺服器、多一組 CVE、多一個值班對象 → **成本進到合約裡** |
| 本專案 | 多一批靜態檔 → **合約範圍不變** |

⇒ 商業角色因此是**贏得那份導入案的差異化條件**，不是一個有自己損益的產品。

**本文先前提過的顧慮「沒有伺服器就沒有維運合約可賣」據此撤回**——它假設編輯器會被單獨賣，
而那個前提在台灣不成立。

### 7.4 台灣的具體形狀

**推論（依據是本 repo 的環境，若有誤請更正）**：`research/` 有 OxOffice WASM Document SDK 的
研究線，工作目錄另有 odfvalidator。那是**已經在賣 ODF 合規給機構**的組織。

⇒ 這條路線對本專案不是新市場，是**既有關係上的新產品**。

而 ODF 在台灣公部門是**政策不是偏好**（使用者的領域知識，本文不重述細節）。這讓下表變得銳利：

| | ODF | 伺服器 |
|---|---|---|
| Euro-Office | **OOXML first**，ODF 仍是開發目標 | 要一台 |
| Collabora CODE | 完整 | 要一台，每人一個行程 |
| **本專案** | **原生** | **0 台** |

**這個組合目前沒有第二家。**

### 7.5 通路的真相：Nextcloud app 是產品形態，不是通路

機構採購**不會從 App Store 來**。實際路徑是系統整合商、既有的 Nextcloud 導入案、以及既有的
ODF／OxOffice 關係。App Store 的作用是**被找到、被信任、降低導入摩擦**。

⇒ 這也補上了 §4.3.4 未排除的那個問題的一半解釋：**ZetaOffice 有產品、沒通路，而且賣給開發者**
——開發者沒有採購流程、沒有預算科目、沒有簽字鏈。**本專案有那條鏈。**

### 7.6 一個會直接擋死機構案的門檻：無障礙

台灣公部門對網站無障礙有法規要求（適用範圍由使用者判斷）。而本樹的實測是：

> **在 26.8 的 Emscripten 上，沒有任何 configure 旗標組合能讓 Writer 的 LOK accessibility 運作**
> （finding 056、057）。

**外部佐證這不是我們自己想像的重要性**：Collabora Online 26.04 把 **BITV 2.0 認證**（德國無障礙
標準）放進發布公告的頭條功能。他們花錢去拿那張證，正是因為歐洲機構採購會查。

⇒ **2026-08-20 決定：a11y 從長期目標提前**，見
[milestone 文件](./ROADMAP-2026-08-20-milestones.md) §3。這推翻了 2026-08-17 的裁示，而推翻的
理由是**前提變了**——舊裁示成立於「短期目標＝能用的編輯器」，買家確定是機構之後，a11y 從
「功能」變成「採購門檻」。

### 7.7 回推：有些東西從加分變成產品的一部分

| | 為什麼 |
|---|---|
| **部署者能決定字型包** | §5.5 的分包機制，在這裡是**機構功能**不是技術優勢 |
| **一張「能做什麼／不會做什麼」的清單** | 應該是**可交付物**，不是內部 manifest。它是資安檢核表的答案 |
| **離線可用** | 對網段封閉的單位是**硬需求**，不是加分 |
| **資料不離開瀏覽器** | 對個資與機敏文件是**硬需求** |

### 7.8 一個仍要準備好答案的反問

> **「沒有伺服器，怎麼管控？怎麼稽核誰改了什麼？」**

答案在 Nextcloud 那一側（版本、稽核記錄、檔案鎖），但**分工要講得清楚**。這一題還沒有寫好的
說法。（另一個反問「出事找誰」已由 §7.3 的前提解掉。）

---

## 8. 待驗證清單

| # | 項目 | 怎麼取得 |
|---|---|---|
| 1 | 手機真機能否配置 1 GB SharedArrayBuffer；實際 PSS | 一台真手機開現行 artifact，半天 |
| 2 | COEP 三個繞法哪一個在 Nextcloud 上可行 | 一個最小 app ＋ 一條路由 |
| 3 | App Store tarball 的實際體積上限 | 查 Nextcloud App Store 政策 |
| 4 | `--with-wasm-module='calc impress writer'` 在 `-Oz` 是否載得動 | 一次 core 重編 ＋ 一次開頁（見 milestone M4 閘門 0） |
| 5 | Office EU 的技術底層是不是 Nextcloud | 官網未寫；未查證 |
| 6 | 「ONLYOFFICE 2026-04 終止合作」的一手來源 | 目前只有二手報導 |
| 7 | LibreOffice 的字型堆疊收不收 **WOFF2** | 丟一個 `.woff2` 進 MEMFS 開一份文件；`vcl/` 裡搜不到 loader，但只是搜不到 |
| 8 | ZetaOffice 的 build 是不是 `-Oz`、raw 體積多少 | 未公開；brotli 解壓後可量，但要下載 36 MB |
| 9 | `business-cdn.zetaoffice.net` 是否送不同的 build | `zetaHelper.js` 裡有這個 base，未查 |
| 10 | 我們改用 **brotli** 之後的首載數字 | R8 當時環境沒有 brotli CLI；裝一個就能量 |
| 11 | **ZetaOffice 為什麼停**：資源重分配去做 COWASM，還是賣不動？ | COOL Days 2025（布達佩斯）／2026（漢堡）的議程與錄影；BMI 補助的離線專案有沒有產出。**這比再量三個數字更能決定要不要投入** |
| 12 | `cdn.zetaoffice.net` 上有沒有 `zetaoffice_latest` 以外的較新路徑 | 他們自己的 `zetaHelper.js` 只指向 `zetaoffice_latest`，但沒有窮舉過 |
| 13 | **台灣公部門實際適用的無障礙規範與等級** | 決定 §7.6 這道門檻有多高、milestone §3.6 的完成判準寫不寫得出來。**本文問不出來，使用者比本文清楚** |
| 14 | 「沒有伺服器怎麼稽核」的標準說法 | §7.8。答案在 Nextcloud 那一側，但還沒整理成可以拿去講的版本 |

**方法備註**：這輪搜尋掉出數個明顯是 AI 生成的 SEO 農場頁（例如自稱 "ZIZIYI Office" 的條目），
**全部未採用**。本文每一條結論的來源不是本機原始碼，就是 Collabora／allotropia／Nextcloud／
Euro-Office 的官方頁面或 Wikipedia。

---

## 9. 來源

**本機**
- `cool-26-04` @ `c64a7343a5c6`：`configure.ac:174-493`、`wasm/README.no-container.md`、
  `browser/src/control/Control.UIManager.ts:561`、`browser/js/global.js:461`
- Nextcloud server 31.0.13：`lib/public/AppFramework/Http/EmptyContentSecurityPolicy.php:122,466`
- `libreoffice-26-8/configure.ac:1280,2322-2328,4371-4392`
- `devlog/DEVLOG-2026-08-01-wasm-sdk-r5.md`、`findings/evidence/sdk-e2/e2-c-validation/d4/`

- `wasm_sdk_probe/sdk/sdk-worker.js:452,519-520`（字型 pack 路徑白名單與 startup 篩選）

**外部實測**（HEAD／GET，2026-08-20）
- `https://cdn.zetaoffice.net/zetaoffice_latest/`：`soffice.wasm`、`soffice.data`、
  `soffice.data.js.metadata`、`soffice.js` 的 content-length 與 content-encoding
- `https://fonts.googleapis.com/css2?family=Noto+Sans+TC`：105 條 unicode-range
- `https://fonts.gstatic.com/...`：`access-control-allow-origin`、`cross-origin-resource-policy`
- `cdn.zetaoffice.net` 三個 artifact 的 `last-modified`；`business-cdn.zetaoffice.net` 的 DNS 解析
- `api.github.com/repos/allotropia/zetajs`（commits／pushed_at）、`registry.npmjs.org/zetajs`、
  `blog.allotropia.de/feed/`

**外部**（查訪日 2026-08-20）
- <https://blog.allotropia.de/2025/05/28/collabora-and-allotropia-merge/>
- <https://www.collaboraonline.com/blog/collabora-allotropia-merge/>
- <https://www.collaboraonline.com/blog/cool-26-04-release/>
- <https://archive.fosdem.org/2024/schedule/event/fosdem-2024-2828-collabora-online-wasm/>
- <https://zetaoffice.net/>
- <https://github.com/allotropia/nextcloud_files_libreoffice_edit>
- <https://nextcloud.com/office/>
- <https://nextcloud.com/blog/euro-office-building-momentum/>
- <https://nextcloud.com/blog/how-to-install-euro-office/>
- <https://euro-office.github.io/documentation/installation/>
- <https://github.com/Euro-Office/DocumentServer>
- <https://office.eu/>
- <https://en.wikipedia.org/wiki/Euro-Office>
- <https://developer.mozilla.org/en-US/docs/Web/API/Local_Font_Access_API>
- <https://github.com/mozilla/standards-positions/issues/401>（Mozilla 對 Local Font Access 的立場）
- <https://developer.chrome.com/docs/capabilities/web-apis/local-fonts>
- <https://github.com/allotropia/zetajs>（MIT，僅 JS wrapper；WASM 來自 CDN）

---

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-20 | **新增第 7 節「買家是機構」**，把定位（第 6 節）接到「怎麼變成一筆生意」。內容：機構是一條簽字鏈不是一個使用者；三個關卡（資安檢核填得完／驗收得完的規格／維運編制）；**封閉 ABI 第一次變現的位置**，同時記下「不要對使用者行銷封閉 ABI，要行銷它的結果」。**撤回本文先前的顧慮「沒有伺服器就沒有維運合約可賣」**——依使用者提供的前提（台灣不會有機關把 Nextcloud 與編輯器拆成兩案），編輯器是既有導入案的差異化條件，加進去**不會讓那份合約變重**。另記通路的真相（App Store 是被找到的地方，不是銷售管道）並補上 ZetaOffice 休眠的一半解釋（有產品沒通路、賣給開發者）。**7.6 記下 a11y 已從長期提前**（milestone §3）及其外部佐證（Collabora 26.04 的 BITV 2.0 認證）。待驗證新增兩項：台灣公部門的無障礙規範等級、以及「沒有伺服器怎麼稽核」的標準說法。原第 7～9 節順延為 8～10。 |
| 2026-08-20 | **ZetaOffice 的產品線判定為休眠，威脅評估下修。**起因是使用者注意到 GitHub 自 2025-06 後幾乎沒更新；查下去發現 GitHub 是最不重要的訊號——CDN 上的 `soffice.wasm` 停在 **2025-05-13**（比併購早兩週，之後一次都沒再編），blog 最後一篇就是併購公告，npm 最後一版在併購後兩天，而**商業方案的 `business-cdn.zetaoffice.net` 現在連 DNS 都查不到**。2026-04 那三個 commit 是跟上游 embindtest 改版、讓它還編得過，不是產品開發。採納使用者的判讀：**不是被關掉，是被吸收去推 COWASM**（與 4.2 在 `cool-26-04` 建置系統裡找到的 zetajs 整合一致）。§4.3 改標題、新增 4.3.4，§6 表格加「產品狀態」與「對我們的威脅」兩列，第 2 句改寫。並列出一個沒被排除的替代解釋（賣不動）與查證方式（第 7 節第 11 項）。 |
| 2026-08-20 | 補入字型與體積的實測，並更正一次判讀。新增 §4.3.1～4.3.3：直接量 ZetaOffice 的 CDN——首載 53.2 MB（brotli），而且那顆 wasm 裡裝了 Writer／Calc／Impress／Draw 四個 app 加完整 Qt UI，比我們 Writer-only 的還小；其資源包**沒有任何 CJK 字型**。新增第 5 節：**撤回「缺 CJK 是護城河」的一部分**——缺字型造成的三件事裡，只有「排版與分頁」是硬的，而 Local Font Access（Chromium 桌面限定）與第三方字型 CDN（Google Fonts 的省錢機制在瀏覽器端，我們取用不到；且與數位主權定位相斥）都解不掉它。可守的其實是 R5 的**分包機制**，不是字型資產本身。同時記下 4.3.2 否證了 milestone 文件 §1.1 對 `configure.ac` 那句註解的引用語氣。 |
| 2026-08-20 | 初版。記錄產品型態的選定（Nextcloud app，mobile 待量測）、決定形狀的本地量測、四家競爭者的實測盤點，以及 Office EU／Euro-Office 的命名澄清。 |

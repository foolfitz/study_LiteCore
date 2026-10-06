# LiteCore WASM 體積（減肥）現況盤點

2026-10-06。來源：subagent 唯讀盤點樹上既有的紀錄（不估算、不新量）；主 session 抽查了 v8 wasm 大小、zstd 首開位元組、v14 gzip 超上限三筆，與原始檔一致。
每個數字都附出處；「未記錄」就是樹上找不到，不是零。MB＝10⁶ 位元組、MiB＝2²⁰，原文件混用的地方照原文件標。

## 一句話

出貨的仍是 `e2-editor-v8`（只有 writer 的核心）。真正落地的瘦身只有三件：R5 的 `-Oz` 連結與資源三切（08-01）、M3 的 gzip 預壓＋immutable 快取（09-29）、
zstd 優先＋gzip 退路（09-30）。**目前沒有在進行的瘦身工作線**；核心功能切分（路線圖 M2a／M2b、R10）從未開始。

## 1. 現在的數字

### v8（出貨）

- `probe.wasm` 115,297,503 B（`wasm_sdk_probe/dist/profiles/e2-editor-v8/`，已核對）→ gzip-9 40,878,530 → zstd-19 30,670,578
  （`specs/SPEC-M3-zstd.md` 30–38 行）。
- 資源包：base 34,178,400、cjk 19,484,784（開機載）、fallback 49,102,042（宣告 `loadAtStartup:false`，**從未被抓取**，finding 085）。
- **第一次開檔**（開機需要的 22 個檔）：原始 169.6 MB；gzip 約 63.9 MB（09-28，宿主 0.2.1）；**zstd 48.56 MB**（09-30，宿主 0.2.5，
  `findings/evidence/m3-zstd/RESULT.md` 33 行，已核對）。資產派送之前是**每次開檔** 169.6 MB。
- **之後再開**：約 17–18 KB（Chrome 2 個請求、Firefox 1 個）。
- 本機回環到 `done` 的時間 2.5–3.3 秒；**真實網路沒量過**。
- 記憶體（不是下載量）：固定 1 GB heap。

### 候選（a11y 核心，writer＋calc＋a11y，v12／v13／v14）

- v14 `probe.wasm` 135,237,060 B → **gzip-9 47,987,197**（**超過打包器 45,000,000 的上限**，今天的打包器會拒絕 v14；已核對
  `findings/evidence/m3-zstd/README.md` 21 行、`tools/package_m3_engine.py` 48 行）→ zstd-19 36,078,637（過）。
- 擁有者認可的代價：「可用之前要下載的原始量」v8 161.4 MiB → v12 186.0 MiB，**＋24.5 MiB（＋15.2%）**（未切分的 v11 是 ＋71.4 MiB，
  其中約 65% 是打包方式造成的，不是核心）。實質核心成本：loader＋wasm ＋19.0 MiB、Calc 設定 ＋5.5 MiB。
- **未記錄**：~~v14（或 v12）壓縮後的首開總量~~（第 7 節算出：約 **54.1 MB zstd**，比 v8 多 5.5 MB）；v15 的任何大小（還沒有 artifact）。
- cutover 尚未執行，頁面仍釘 v8。

### 發佈封包

- 0.2.5 的 App 封包 111,711,969 B（106.5 MiB），因為同時帶 `.gz` 與 `.zst`（0.2.1 時約 60.5 MiB）。App Store 原始碼預設上限 30 MiB，
  但商店上有 269 MB 的 `richdocumentscode`，是否適用未知（擁有者待決項 A）。

## 2. 已經做過的瘦身與實際省下的量

| 項目 | 日期 | 省下（紀錄值） | 出處 |
|---|---|---|---|
| 建置選項 strip（`--with-wasm-module=writer` 等） | 07-31 | 211 → 183 MB（表頭寫 MB、實為 MiB）；`--disable-symbols` 的 125 MB 版開機就崩（finding 001）；二十幾個 `--disable-*` 多數無效 | `devlog/DEVLOG-2026-07-31-wasm.md` 71–75、110 行 |
| 核外連結探針 vs Qt6 | 08-01 | 原始 −8.74%、gzip −5.96% | `devlog/DEVLOG-2026-08-01-wasm-sdk-probe.md` |
| R5 `-Oz` 產品連結 | 08-01 | wasm 169.3 → 115.3 MB（−54.0 MB 原始；gzip −4.7 MB） | `devlog/DEVLOG-2026-08-01-wasm-sdk-r5.md` 107–120 行 |
| R5 資源三切（base／cjk／fallback） | 08-01 | 首載原始 −37.9%、gzip −28.0%（但 fallback 包其實「從未送出」，不是「延後」，finding 085） | 同上 21–24、56–70 行 |
| API 收窄（writer-reader vs writer-review） | 08-01 | 只差 1.6 KiB——無效 | 同上 128 行 |
| a11y 候選重新切分（v11 → v12） | 08-29 | ＋71.4 → ＋24.5 MiB | `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` |
| 資產派送（gzip-9、immutable、ETag） | 09-29 | 首開 169.6 → 63.9 MB；再開 169.6 MB → 18 KB | `findings/evidence/m3-assets/RESULT.md` 28–34 行 |
| zstd（level 19；瀏覽器解碼器視窗上限 2²³） | 09-30 | 首開 63.9 → 48.56 MB（−24%） | `specs/SPEC-M3-zstd.md`、`m3-zstd/RESULT.md` |

## 3. 上限與誰超過

- **打包上限 45,000,000 B（每個 `.gz`、`.zst` 各自）**，依據是 Firefox 快取量到能留住的最大編碼大小。**v14 的 wasm gzip 超過**；zstd 沒超過。
  規格刻意不預先放寬：「a11y cutover 時 K0-5 要重判」。
- Firefox 快取的單筆上限在編碼後 45–60 MB 之間（115 MB 的原始 wasm 會被重抓）；Chrome 的上限跟著設定檔所在磁碟的剩餘空間走，小磁碟的位置沒量過。
- Firefox 使用者每次登出都清快取（`Clear-Site-Data`）→ 下一次又是完整的 48.56 MB；每次換引擎或派送政策，每個使用者每個瀏覽器也要重抓一次（經過 PHP）。

## 4. 還沒做、已計畫、或量過但沒做的

- 路線圖 M2a（工具鏈：LTO、`wasm-split`、PGO；傳輸：Brotli、串流編譯、Service Worker；字型策略）、M2b（filter 白名單、元件與函式庫移除、資源修剪）：
  **都沒跑過**。R10（深度瘦身）：只有方法，前提未滿足、不得開始（`specs/SPEC-R10-000-overview.md`）。
- LTO「從來沒真的跑過」。~~`wasm-opt` 是否是 `--disable-symbols` 崩潰的成因只是推論（finding 001）。~~ **更正（同日，第 7 節）**：出貨的
  `probe.wasm` **沒有任何 custom section**（0 位元組，已核對），headless 核心本來就沒開符號；finding 001 講的是 Qt 版 `soffice.wasm`，
  不約束出貨的 artifact。「去掉符號」不是手段。
- CJK 字型子集化（19.5 → 3–5 MB）：只有研究估計，從未建出或量過。`--without-fonts` 同樣沒試過。
- Brotli：~~機器上沒有 brotli 工具~~ **更正**：node v24（已在 PATH、本來就是專案依賴）內建 brotli 與 zstd（已核對）；第 7 節量了。
- Calc 設定進了資料映像（＋5.5 MiB）：只登錄，沒動。**補充（第 7 節）**：那 ＋5.5 MiB 原始量裡 183 個是 `.ui`，壓縮後只多 ＋119 KB；
  候選線首開多出來的成本是 wasm（＋5.4 MB zstd），不是資料。
- 阻礙：finding 085（SDK 沒有按需載入的路徑，任何「延後載入」的點子都沒有載入器可搭）；finding 036（wasm 不可重建，任何重連結都換雜湊、
  要重綁身分並重新計數）；finding 001（strip symbols 不可用）；核心重連結由擁有者執行。

## 5. 文件之間的矛盾（舊文件未更正的）

- 路線圖 §5.3 還寫「第一次開檔 63.9 MB、封包 60.5 MiB、換 zstd 也不會低於 30 MiB」——09-30 之後是 48.56 MB 與 106.5 MiB。
- `research/RESEARCH-2026-08-20-product-route-and-competitors.md` 153–156 行仍寫「169 MB 必須直出、不穿過 PHP」，已被資產派送規格撤回。
- `litecore-analysis.md` 58 行與 §8.6 把「拿掉 `--enable-symbols`」列為第一瘦身手段——finding 001 證明會崩，檔案沒有過時標註。
- 同一顆 wasm 有兩組壓縮數字（CLI 與打包器的參數不同），規格已註明。

## 6. 樹上找不到的（明確缺口）

v14／v12 的壓縮首開總量；v15 的大小；真實網路的首開時間與冷編譯時間；zstd 解碼的 CPU；我們的 wasm 的 Brotli 大小；Safari／Edge／nginx；
Chrome 在小磁碟上的上限；宿主 0.2.6／0.2.7 的封包大小；CJK 子集化、`--without-fonts`、LTO、`wasm-split` 實際能省多少（沒有任何量測）。

## 7. 方法分析（fable，2026-10-06）

唯讀分析，量測都在 scratchpad 的複本上做，沒有重編、沒有重連結。依據標記：**量**＝本次實測、**推**＝由磁碟上的檔案推導、**文**＝取自既有文件、
**估**＝估計或文獻。主 session 核對過三項（wasm 無 custom section、ICU 資料在 wasm 裡、node 有 brotli）。

### 7.1 首開 48.53 MB 的位元組去哪了（v8，zstd；宿主 `engine/MANIFEST.json`，10-06）

| 項目 | zstd | 佔比 | 內容 |
|---|---:|---:|---|
| `probe.wasm` | 30.67 MB | 63% | 原始 115.3 MB＝程式碼 61.5 MB＋資料段 53.3 MB（量）；**資料段裡約 32.1 MB 是完整、未篩選的 ICU 資料 `icudt78l.dat`**（量；單獨壓縮 zstd 9.23 MB，約佔首開的 19%） |
| CJK 包 | 12.17 MB | 25% | 一個 `NotoSansCJK-Regular.ttc`：10 個 face 共用同一張 65,535 字形的 CFF 表；只留繁中 face 只省 0.18 MB（量）——要省就得做**字形子集** |
| base 包 | 5.53 MB | 11% | Liberation 字型 1.69、圖示 zip 1.38、fontwork 圖庫 0.72、program 下的 rdb／PNG 0.56、766 個 `.ui` 只有 **0.41**（原始 15.0 MB）、registry 0.27、Android 範例文件 0.28（量） |
| 其他 19 個 JS／HTML／JSON | 0.16 MB | 0.3% | |

程式碼按模組（推，用同一個 core 的 profiling 版名稱段歸類）：sw 12.8%、svx 8.8%、vcl 5.5%、chart2 4.2%、oox 3.4%、sfx2 3.1%、runtime＋libc++ 8%。
**再次開檔約 18 KB——下載量不是再開的槓桿，約 2 秒的啟動運算才是**（回環量測；真實網路沒量過）。

### 7.2 各方法（預期省多少、依據、代價、會靜默壞掉什麼、能裁決它的最便宜量測）

| 方法 | 首開預期節省 | 依據 | 代價 | 靜默壞掉的方式 | 裁決用的量測 |
|---|---|---|---|---|---|
| **CJK 字形子集**（新 cjk 包，profile 重新打包，**不重連結**） | −7～−9 MB | 推（CFF charstring 推算：Big5＋HKSCS 約 5.8 MB 原始→約 4 MB zstd；全部 URO 約 7.3→5 MB） | 重新打包＋重新計數產品路徑；fontTools／hb-subset 是新依賴（要你同意） | 子集外的字變豆腐或空白——LOK 沒有缺字回呼、fallback 包從不抓（085），沒有東西會回報；簡中／日／韓字形變成繁中字形 | 實際做出子集、壓縮；語料 A/B 比 tile 雜湊；逐實例判準「語料∪Big5∪HKSCS 的每個字在子集的 cmap 裡」 |
| **Brotli** 當優先編碼（gzip 保留當最後退路） | 約 −3.5 MB（−7%） | 量（8 MiB 樣本：brotli／zstd＝程式碼 0.94、ICU 資料 0.84–0.88、字型 0.94）；總數是估 | 打包器＋宿主 PHP（派送政策雜湊變→每位使用者重抓一次）；發佈封包多一種編碼 | 內容上無；Firefox／Chrome 在 HTTPS 上都宣告 `br`；Safari 收 br 不收 zstd（未核對） | 用 node 對三個大檔做 brotli（約 4 分鐘 CPU，不重連結），再跑同一組 K/Z 條款 |
| **ICU 資料修剪**（`icupkg -r`，要重編 ICU 外部套件＋重連結） | **−4.7／−5.5／−5.7 MB**（三種修剪程度） | **量**（native 26.8 的 `icupkg` 在複本上做） | 核心重編（你，1–2 小時）＋重連結＋全部身分重綁（036） | 拿掉 `rbnf/` 會讓序數後綴靜靜回空字串——要留 `rbnf/{root,en,zh*}`；被拿掉的語系的非公曆曆法會靜靜變成公曆；中日文斷詞要留 `brkitr/cjdict` | 大小已量；行為：這顆 core 開了 `--enable-sal-log`，用 `SAL_LOG=+WARN.i18npool` 跑語料，加上 `icupkg` 自己的相依檢查 |
| base 包裡沒用到的檔（重新打包） | −1.3 MB（圖庫、intro／about 圖、Android 範例）；圖示 zip 若沒讀過再 −1.4 | 量（大小）／估（哪些沒讀） | 重新打包＋計數 | 缺 `.ui` 會讓 `VclBuilder` 在引擎裡丟例外；缺圖示→空白圖 | **`FS.open` 普查**：診斷用 worker 複本包住 `Module.FS.open`，跑完整回歸網，記下開過的路徑與 ENOENT；判準逐實例：每個被開的路徑都在包裡 |
| 元件移除（既有開關 `ENABLE_WASM_STRIP_CHART`／`_HUNSPELL`） | 約 −0.7 MB | 推 | 核心重編＋重連結 | 內嵌圖表的文件畫成空白 | 只為量測的連結（不出貨）＋語料 |
| 合約外的 filter（oox、WW8／DOCX／RTF、writerperfect、hwp、HTML、SQL parser、擴充部署、webdav／curl） | 約 −1.6～−2 MB（原始約 6.1 MB 程式碼） | 推／估 | 改元件清單（手列）、重編、重連結 | 產品本來就拒絕的格式（013）徹底消失；HTML 貼上路徑要查 | 只為量測的連結加 `-Wl,--Map`——這棵樹缺的逐物件大小歸因工具 |
| LTO（從沒跑過） | 估 −0.8～−1.6 MB | 估（文獻） | 全核心重編＋連結，又一個 036 型的不可重現來源 | 低 | 另一個 build 目錄做只為量測的連結 |
| wasm-split／延遲載入程式碼 | 程式碼方面潛力最大（大部分函式在產品路徑上從不執行——未量） | 估 | 實驗性；它的 JS 載入器只接在 JSPI 上，而這個專案沒有 JSPI；7 條 pthread 每條都要同步載入次模組 | 剖面不對＝第一次用到時同步卡住 | 先量剖面，不出貨 |
| `--without-fonts` | **0**：那些字型本來就在從不抓取的 fallback 包裡 | 量 | 白做一次重編 | — | 不需要 |
| 真正的按需載入器（085 選項三） | 需要一個觸發訊號，而 LOK 沒有缺字回呼 | 推 | SDK＋worker | 為了維持一個宣稱而造機械 | 先查 LOK 有沒有任何字形退路的訊號；沒有就不做 |

### 7.3 建議的順序

**出貨的 v8 線（不重連結；只有重新打包與宿主改動，每項重新計數一次）：**

1. **先量，不動東西**：用 CDP 限速（10／50／100 Mbps）量第一次開檔，加上診斷用 worker 複本的啟動階段時間線（抓取→instantiate→資源包掛上→
   引擎就緒→文件開啟→第一張 tile）。這一步決定「UX」指的是首開的位元組，還是再開時約 2 秒的運算——兩者今天都沒有量測。
2. CJK 字形子集（覆蓋範圍由你決定：Big5＋HKSCS，或全部 URO）——最大的槓桿，−7～−9 MB。
3. Brotli——−3.5 MB，同時解掉 v14 的 gzip 上限問題。
4. base 包普查後移除沒用到的檔——−1.3～−2.7 MB。

v8 做完 2–4 的首開估計：48.5 → **約 35–36 MB**（估）。

**a11y／cutover 線（v14／v15——反正已經欠一次核心重編與重連結）**：ICU 修剪（−5.5 MB）與 `STRIP_CHART`／`STRIP_HUNSPELL` 的決定併進那一次重編，
一次身分變更付清；LTO 之後另做只為量測的 A/B。v14 估計：54.1 − 5.5 − 8 − 3.5 ≈ **37 MB**，也就是 a11y 核心出貨時會比今天的 v8 還小。

**v14 與 45 MB 上限**：上限加在一個 Firefox 根本收不到的表示法上——Firefox 157 宣告 `br, zstd`（讀 snap 的 `greprefs.js`），收到的是 36.1 MB 的
zstd，不是 48.0 MB 的 gzip。判準應該改成「每一個有上限的瀏覽器實際會收到的編碼，都 ≤ 該瀏覽器量到的上限」，並用 48／50／52／56 MB 四點量
Firefox 真正的單筆上限（今天的 45,000,000 只是兩點夾出來的；Firefox 預設 pref 是 50 MiB——fable 憑記憶，未核對）。**不要為了削 3 MB 的 gzip 重連結。**

**不要做**：去掉符號（本來就沒有）、`--without-fonts`、為了位元組刪 `.ui`（只有 0.41 MB）、把 TTC 按 face 拆、API 收窄（R5：1.6 KiB）、
為了大小重連結 v8、現在就做 wasm-split。

### 7.4 前面幾節被更正的地方

已在原處更正：去掉符號不是手段（第 4 節）、機器上有 brotli（第 4 節）、Calc 設定的壓縮成本只有 ＋119 KB（第 4 節）、v14 首開約 54.1 MB（第 1 節）。另外：

- R5 的 169.3 → 115.3 MB 不全是 `-Oz`：同一次連結也拿掉了 `--profiling-funcs`（這顆 core 上是 14.8 MB 的 name section）、embind 與 assertion；
  只有 gzip 的 −4.7 MB 能算在 `-Oz` 頭上。
- 第 4 節的「CJK 子集化 19.5 → 3–5 MB」取自 08-01 研究文件裡講「繁中／拉丁退路子集」的段落，是另一個東西；本節的推算是 Big5 到全部 URO 的
  4.6–7.3 MB 原始。
- `ENABLE_WASM_STRIP_LOCALES`（`config_host.mk.in:268`）在 26.8 的整棵樹裡沒有任何使用者——上游死掉的設定開關，與 085 同型（可立 finding）。

## 修訂紀錄

- 2026-10-06：初版（第 1–6 節，subagent 盤點）；同日追加第 7 節（fable 方法分析），並依第 7 節原地更正第 1、4 節四處。

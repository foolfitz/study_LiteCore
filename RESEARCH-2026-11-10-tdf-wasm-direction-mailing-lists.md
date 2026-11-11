# TDF 的 WASM 開發方向：郵件清單與公開來源查得到什麼

> 2026-11-10 讀取。起因是 TDF blog〈New Web and Mobile Strategy for LibreOffice〉（2026-05-27）對 WASM 只有一句話。
> 證據標記：**已觀察**＝原文或 git 可直接確認；**推論**＝從已觀察的事實歸納，未直接驗證；**未讀**＝來源存在但這次沒讀到。

## 結論

1. **開發者清單上沒有 WASM 方向的討論。**`libreoffice@lists.freedesktop.org` 2026-01-01 到 11-09 共 875 則信，沒有任何一則的主旨是 WASM；內文提到 wasm／webassembly／emscripten 的只有 13 則，全是順帶提及（致謝信、ESC 的 patch 清單、Coverity 報表）。**已觀察**
2. **方向的本文不在郵件清單，在 blog 與論壇。**會議紀錄引用的提案，TDF 在 2026-05-30 另貼成一篇〈Web and Mobile Development Strategy Proposal〉，討論串開在 TDF 論壇（Discourse topic 13729）。論壇這次讀不到（見〈來源〉）。**已觀察**
3. **提案對 WASM 的承諾很少。**只說已有一個用 Qt 與 WebAssembly 的可運作原型、狀態粗糙、初期工作是「polish and packaging」做出最小可部署版。沒有時程、負責人、已知問題、也沒有排除哪些替代方案。文件自稱是策略提案，技術與規劃內容「should be considered speculative」。**已觀察**
4. **清單上看得到的實際動靜是 Qt6，不是 WASM。**2026 年 TDF 團隊在做的是把 qt6 VCL plugin 擴到 Windows 與 macOS、以及 Qt welding（tdf#130857）。這對得上提案裡「standardize on the Qt 6 VCL backend」。**已觀察**；兩者是同一條路線的前後段是**推論**。
5. **原始碼裡 WASM 有實質進展，只是清單上沒人談。**（2026-11-10 修正，擁有者指出）26.8 的原始碼帶著 2024-06 到 2026-03 累積的 WASM 工作：Embind 的 JS↔UNO binding、Wasm UNO bridge、把 Qt 事件迴圈移出 JS 主執行緒、實驗性的 Qt6 與 JSPI、複製貼上、Impress、LOKit 上的 JS UNO scripting、emsdk 5.x 相容。分量集中在 25.2 與 25.8 兩個週期，26.2→26.8 這一輪新增的 WASM 專屬能力較少。細節見〈原始碼裡的 WASM 進展〉。**已觀察**（commit 標題與 diff 內容；沒有建置或執行）
6. **做這些的人已經不在 TDF 這邊。**2026-04-01 Collabora 與 TDF 分家。四個週期裡碰到 WASM 相關程式行的 commit，Stephan Bergmann（Collabora）佔 105／172；他在 TDF 樹上最後一個是 2026-03-31。分家之後到 2026-10-11，用同一個方法找不到新增 WASM 能力的 commit，只有建置修正、清理、以及順帶碰到 Emscripten 分支的 Qt 重構。**已觀察**，方法的盲點見該節。

## 來源與讀取方式

| 來源 | 結果 |
| --- | --- |
| TDF blog 兩篇（05-27 會議紀錄、05-30 提案） | WebFetch 可讀 |
| `lists.freedesktop.org` 開發者清單官方封存 | WebFetch 回 403；不偽裝的無頭 Chrome（UA 帶 `HeadlessChrome`）放行。抓 2026 年 1–11 月的月封存（`.txt.gz`，11 個請求）後在本機全文搜尋 |
| `mail-archive.com` 鏡像（含 commit 通知信） | WebFetch 可讀，用它的全文搜尋交叉核對 |
| `community.documentfoundation.org`（TDF 論壇，board-discuss 也已併入這裡） | **未讀**。Anubis 對無頭 Chrome 直接回「拒絕存取」（不是出題）。要讀就得偽裝瀏覽器，沒有做 |
| 本機 `~/LibreOffice/lo-submit` 的 `origin/master`（`016fd5d04925`，2026-10-11） | `git log`／`git grep` |

官方封存的訊息網址是用「全域序號＋94137」算出來的，以信件內互相引用的 4 個網址與 3 個實際頁面（2 月、7 月、10 月）核對過。**已觀察**

## 提案說了什麼

出處：<https://blog.documentfoundation.org/blog/2026/05/30/web-and-mobile-development-strategy-proposal/>。署名是 Italo Vignoli，內文沒有出現 Jonathan Clark 的名字；把它歸給 Jonathan Clark 的是 05-27 那篇會議紀錄。**已觀察**

五個 initiative，各自獨立可用：responsive UI、WebAssembly 網頁版、行動版、document server、client-server 協作編輯。

**WASM 段（約 115 字）**

- 「We already have a working prototype of LibreOffice built for web browsers, which uses Qt and WebAssembly.」
- 「This prototype is still in a rough state」。
- 初期工作「mostly focus on polish and packaging」，目標是「minimally viable web-deployable version」。
- 理由：重用桌面版原始碼來驅動網頁版，不需要大規模重複投入，也不需要吃資源的 server 元件；「we should perform all expensive computations on the client side」。
- responsive UI 完成後會成為網頁版與行動版的預設組態。

**沒寫的**：Qt 版本、Emscripten 版本、用哪個 VCL plugin、demo 網址、下載大小、啟動時間、threading、檔案存取、字型、剪貼簿、瀏覽器支援。也完全沒提 LibreOfficeKit、tiled rendering、Collabora Online、LibreOffice Online、headless WASM、或「WASM 核心＋JavaScript UI」。**已觀察**（由 subagent 讀全文後回報，我沒有自己讀原頁）

**周邊**

- Document server：要做一個「easy-to-host LibreOffice first-party document server」，server 元件要輕、便宜、可換供應商。沒提 WOPI、認證、儲存後端，也沒說 WASM client 用什麼 API 連它。Nextcloud 只在「on-premises cloud software vendors such as Nextcloud」這個例子裡出現，不是整合對象。
- 協作編輯：先在**桌面版**做，開發期用 LibreOffice 實例之間的直接 TCP/IP 連線，之後由 document server 當協調者與 proxy；模型是「a client-server network architecture, with a single authoritative state」。P2P 延後。沒提 CRDT／OT。
- 行動版：建立在「standardize on the Qt 6 VCL backend」的研究上，第一個目標是 Android／iOS **模擬器**上的最小可運作桌面版建置。

## 開發者清單：提到 WASM 的 13 則

| 日期 | 誰 | 內容 |
| --- | --- | --- |
| 02-19 | ESC 紀錄 | Michael Weghorn 的 a11y 週報：Qt 上游的 reduce-motion 屬性，並建議上游在 KDE Plasma 與 WASM 回報它。[094276](https://lists.freedesktop.org/archives/libreoffice/2026-February/094276.html) |
| 04-01 | Stephan Bergmann | 致謝 Balázs：「Early Wasm work that got Calc running in a browser」。[094406](https://lists.freedesktop.org/archives/libreoffice/2026-April/094406.html) |
| 04-01 | Stephan Bergmann | 致謝 Sarper：寫了第一版用 Embind 的 JavaScript UNO binding。[094408](https://lists.freedesktop.org/archives/libreoffice/2026-April/094408.html) |
| 04-01 | Michael Stahl | 致謝 Stephan：接手 Jan-Marek 與 Thorsten 起頭的 Emscripten WASM 原型，「turned it into something that almost works, and is scriptable」。[094414](https://lists.freedesktop.org/archives/libreoffice/2026-April/094414.html) |
| 04-25 | Julien Nabet | 問 `tb linux wasm` 那台 tinderbox 能不能把 gcc 升到 13。 |
| 05-22、05-27、05-28 | ESC 議程／紀錄 | Gerrit patch 清單裡的「Add a resize-event hack for Qt5 Emscripten」（Stephan Bergmann，174040）。 |
| 06-03、06-04 | ESC 議程／紀錄 | 「Patches automatically abandoned」清單裡的「Emscripten: Adapt to internal emscripten/val.h change in Emscripten 4.0.11」（Stephan Bergmann，188465）。[094664](https://lists.freedesktop.org/archives/libreoffice/2026-June/094664.html) |
| 07-12 | Dan Williams | Qt6 on macOS 的 patch 串裡有一個 `__EMSCRIPTEN__` 巨集的修正。[094730](https://lists.freedesktop.org/archives/libreoffice/2026-July/094730.html) |
| 05-09、09-01 | Coverity 報表 | 程式碼片段裡出現 `EmscriptenLightweightRunInMainThread`、`__EMSCRIPTEN__`。 |

沒有任何一則談 WASM 的路線、負責人、目標版本、下載大小、demo 或 threading 決策。**已觀察**

## 開發者清單：看得到的實際方向

**Qt6 擴到三個桌面平台**

- 03-12／03-19／03-26 ESC：Michael Weghorn「looking into qt6 VCL plugin on Windows」，動機寫的是 UIA（Windows a11y）；Hossein 有一個基於 Jan-Marek 舊作的 WIP。[094332](https://lists.freedesktop.org/archives/libreoffice/2026-March/094332.html)
- 04-02 ESC：「initial qt6 vcl plugin support for Windows now merged to master」。[094440](https://lists.freedesktop.org/archives/libreoffice/2026-April/094440.html)
- 04-30 ESC：Dan Williams 在 macOS「Have Qt6 VCL plugin working」，在修 HighDPI、對話框沒有標題列、Mac 專屬選單。[094520](https://lists.freedesktop.org/archives/libreoffice/2026-April/094520.html)
- 06-18 到 07-13「Qt6 on macOS」討論串（Patrick Luby、Dan Williams、Michael Weghorn）：字型渲染目前 Cairo 路徑最成熟，另有實驗性的 QFont 路徑，Skia 是未來可能的選項。[094692](https://lists.freedesktop.org/archives/libreoffice/2026-June/094692.html)、[094703](https://lists.freedesktop.org/archives/libreoffice/2026-June/094703.html)
- 07-23 ESC：「Mac-specific parts of the Qt plugin merged last week」。[094762](https://lists.freedesktop.org/archives/libreoffice/2026-July/094762.html)
- 10-01 ESC：「Qt on macOS and Windows: prospects for offering an experimental option to turn it on?」結論是先把建置選項加進 CI；Windows 上 headless（fontconfig）的建置問題是 blocker；要把 Qt 放進 external bundle。[094919](https://lists.freedesktop.org/archives/libreoffice/2026-October/094919.html)

**Qt welding 是 UI 的主軸**

Michael Weghorn 07-23 回覆一個 VCL 版面提案時的表態，是整個清單上最接近「方向宣告」的一段。[094760](https://lists.freedesktop.org/archives/libreoffice/2026-July/094760.html)

- 「switching from using vcl widgets to using native Qt widgets is the best way forward」（指 qt6／kf6 plugin）。
- master 已有 qt6 plugin 在 Windows 與 macOS 的實驗性支援，「this *might* be a potential way forward on those platforms as well. (That is still to be decided and needs further investigation.)」
- 他自己不會再對 vcl 自繪元件投入大量工作，因為「it's unclear to what extent it will still be used in the future」。
- 工具列與 Notebookbar 還沒走 weld（tdf#163988）。

**與 Online 那條路脫鉤**

- 06-04 ESC：「Remove JSDialog (Xisco) — used on in Online version」。[094664](https://lists.freedesktop.org/archives/libreoffice/2026-June/094664.html)
- 05-28 ESC：Heiko「Remove wordcount-mobile dialog」。[094651](https://lists.freedesktop.org/archives/libreoffice/2026-May/094651.html)

**提案的主筆在週報裡沒有 web 項目**

2026 全年 ESC 紀錄裡，Jonathan Clark 的固定項目一直是「RTL/CTL/CJK update (Jonathan)」。4 月到 11 月的週報段落沒有出現 web、WASM 或 mobile 的固定項目。**已觀察**。04-23 那次他的項目下有一行「event loop stuff abandoned, instead...」，沒有上下文，所指不明。[094500](https://lists.freedesktop.org/archives/libreoffice/2026-April/094500.html)

## 背景：Collabora 分家

- 04-01 清單上一口氣出現 28 封「Thank you, …」，是 Collabora 員工互相致謝的告別信。
- 05-08 Julien Nabet 引 Collabora 論壇的〈TDF ejects its core developers〉：Collabora 停用 `gerrit.libreoffice.org`，改用自己的 `gerrit.collaboraoffice.com`。[094564](https://lists.freedesktop.org/archives/libreoffice/2026-May/094564.html)
- 同日 Michael Meeks 回覆：之後會「contribute at a lower level where it makes sense」，沒有改授權的計畫。[094566](https://lists.freedesktop.org/archives/libreoffice/2026-May/094566.html)
- Collabora 的 repo 把 core 放在 `online` repo 的 `engine/` 子目錄下；TDF 這邊用 `git cherry-pick -x` 撿回來（Xisco 在 09-10 的介紹裡把這列為自己的工作）。[094581](https://lists.freedesktop.org/archives/libreoffice/2026-May/094581.html)、[094880](https://lists.freedesktop.org/archives/libreoffice/2026-September/094880.html)

以上都是**已觀察**。

## 原始碼裡的 WASM 進展（不是郵件清單）

2026-11-10 補。初版只用 commit **訊息**裡有沒有 wasm／emscripten 去數，那是代理指標，而且只看 2026 年，所以把進展說少了。這一節改看 **diff 內容**，並按版本週期往回拉到 2024-06。

方法：`git log --no-merges -G'EMSCRIPTEN|[Ee]mscripten|WASM|[^a-zA-Z]wasm|JSPI|[Ee]mbind'`（commit 的 diff 有增刪到符合的行才算），以及 `static/`、`solenv/gbuild/platform/EMSCRIPTEN*`、`config_host/config_emscripten.h.in` 的 `git diff --shortstat`。週期邊界用各發行分支與 master 的 merge-base。

| 週期 | 區間 | commit 總數 | 碰到 WASM 相關行 | 其中 Stephan Bergmann | `static/` 等的 diff |
| --- | --- | ---: | ---: | ---: | --- |
| 25.2 | 2024-06-01 → 2024-12-04 | 5,831 | 63 | 54 | 21 檔 +1,638／−1,541 |
| 25.8 | 2024-12-04 → 2025-06-09 | 4,697 | 43 | 27 | 5 檔 +448／−25 |
| 26.2 | 2025-06-09 → 2025-12-03 | 5,064 | 26 | 12 | 4 檔 +21／−25 |
| 26.8 | 2025-12-03 → 2026-06-16 | 5,734 | 40 | 12 | 3 檔 +20／−24 |
| 26.8 分支出之後 | → 2026-10-10 | 460 | 3 | 0 | 1 檔 −1 |
| master 分支出之後 | 2026-06-16 → 2026-10-11 | 3,317 | 11 | 0 | 未量 |

25.2 那一列的起點 2024-06-01 是我取的（本機沒有 24-8 分支可算 merge-base）。

**各週期做了什麼**（依 commit 標題，沒有逐一讀 diff）

- **25.2**：Embind 的 JS↔UNO binding 成形（`Module.uno_init`、UNO attribute 變成 JS accessor property、polymorphic struct、例外捕捉）；「Fully implement the Wasm UNO bridge cpp2uno direction」；「Emscripten: Move the Qt event loop off the JS main thread」與瀏覽器主執行緒／LO 主執行緒之間的通道；啟用 start center 與 WebDAV UCP；`--with-package-format=emscripten`；支援 `--disable-gui`；實驗性的 `--enable-qt6` 與 JSPI（2024-11-04）。
- **25.8**：複製貼上（Qt5 與 Qt6）；`--with-main-module=`；Qt6 的 proxy-to-pthread 替代作法；`EmscriptenLightweightRunInMainThread`；`comphelper::emscriptenthreading` 重新設計；WASM 建置啟用 Impress（Moritz Duge）；WASM 專用的字型組態與快捷鍵設定（Balazs Varga）。
- **26.2**：「Emscripten: Call initJsUnoScripting also from LOKit」（2025-07-18）、「Skip dubious LOKit SolarMutex acquire for Emscripten」；`-gseparate-dwarf`；`--enable-embindtest-uno`；emsdk 升到 4.0.10。
- **26.8**：相容 emsdk 5.0.1（2026-02-22）；vcl 的 `Platform`／`DesktopType` 重構把 WASM 列為正式成員（Michael Weghorn，3 月）；`EMSCRIPTEN` 巨集統一成 `__EMSCRIPTEN__`；Tor Lillqvist 的 headless 相關改動（2025-02 寫的，2026-01 才進 master）；box2d、expat 等外部函式庫的 WASM 建置修正。40 個裡有十幾個其實是 PyUNO／QuickJS／Rust 的測試重用 `embindtest` 這份 IDL，不是 WASM 功能。
- **分家之後**（2026-04-01 起，26.8 分支與 master 到 10-11）：符合的 commit 是外部函式庫升級與建置修正（Xisco Fauli）、Qt 重構順帶碰到 Emscripten 分支（Michael Weghorn，如 09-09「qt: Simplify QtInstance::DoExecute」）、「vcl/qt: enable Qt6 plugin for Mac」（Dan Williams）。沒有看到新增 WASM 能力的。

**方法的盲點**：只抓得到 diff 裡出現那幾個字樣的 commit。不帶這些字樣、但 WASM 建置也會受益的工作（最大宗是 Qt welding 的一千四百多個 commit）不在計數內。我也沒有建置或執行任何東西，「有進展」指的是程式碼進了樹，不是量到它能跑。

**樹內現況**（`origin/master` 到 2026-10-11）：

- `static/README.wasm.md` 寫的仍是「We're using Qt 5.15.2 with Emscripten 4.0.10」，`distro-configs/LibreOfficeWASM32.conf` 是 `--enable-qt5`。文件最後一次實質修改是 2025-11-21（Stephan Bergmann 升 emsdk）。
- Qt6 的 WASM 路徑存在但標為實驗性：`--enable-emscripten-jspi`（「Experimentally enable use of the Emscripten -sJSPI feature」），程式裡有一組 `__EMSCRIPTEN__ && ENABLE_QT6 && HAVE_EMSCRIPTEN_JSPI` 的分支，其中一部分再排除 `HAVE_EMSCRIPTEN_PROXY_TO_PTHREAD`。
- 標題含 JSPI 或「Qt6＋Emscripten」的 commit 共 18 個，17 個是 Stephan Bergmann（2024-01 到 2025-03），1 個是 Michael Weghorn。
- configure 的 WASM 選項（`emscripten-jspi`、`emscripten-proxy-posix-sockets`、`emscripten-proxy-to-pthread`、`wasm-module`、`wasm-strip`）從 25.8 分支點到 26.8 沒有增減。
- README 的第二種用法「Building headless LibreOffice as WASM for use in another product」仍在。

以上是**已觀察**。「blog 說的 Qt 6＋WebAssembly 原型就是這條 `--enable-qt6`＋JSPI 路徑」是**推論**：提案與清單都沒有指名。

## 對本專案的意義

- TDF 的網頁路線是把**完整桌面 UI**（Qt6 元件）編進瀏覽器，本專案是 headless 引擎加自己的殼層。兩條路不同，提案沒有提到後者，也沒有排除它。**推論**
- 提案的網頁路線排在 Qt6 標準化與 Qt welding 之後，而這兩件在 10 月還停在「要不要給實驗性選項」。樹內已有的 WASM 能力是分家前累積的，分家後沒有量到新增。短期內看不到可部署的 TDF 網頁版。**推論**
- 26.2 週期有兩個 commit 直接碰 LOKit 在 Emscripten 上的行為（`initJsUnoScripting` 從 LOKit 呼叫、略過 LOKit 的 SolarMutex acquire）。本專案走的正是這條路，值得對照自己的 patch。**已觀察**（標題），是否與本專案的改動重疊未查。
- 若本專案有依賴 JSDialog 或其他 Online 專用的 core 程式碼，TDF 的 master 正在移除它們；Collabora 的 repo 才是那些程式碼之後的上游。**推論**，未查本專案實際用到哪些。

## 沒讀到的

- **Discourse topic 13729**：提案的官方討論串，最可能有實質的技術意見。網址 <https://community.documentfoundation.org/t/web-and-mobile-development-strategy-proposal/13729>。要用本人的瀏覽器讀。
- board-discuss 2026 年的討論（同一個論壇）。
- `wasm-test.libreoffice.org`：一篇俄文報導的讀者留言說那裡有 demo、載入很慢。未驗證。
- Gerrit 上是否有未合併的 Qt6 WASM change。
- 本機樹 2026-10-11 之後的 commit。
- 2025 年以前的清單（這次只讀 2026 年）。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-11-10 | 初版。 |
| 2026-11-10 | 擁有者指出 26.8 原始碼顯示 WASM 有進展。初版結論 4 的「WASM 本身在 2026-04 之後只剩修 WASM build」是用 commit 訊息數出來的，且只看 2026 年。改用 diff 內容、按版本週期重量：刪掉那句，新增結論 5、改寫結論 6、把〈本機 core 樹的佐證〉擴成〈原始碼裡的 WASM 進展〉。 |

## 重現

腳本與下載的月封存在這個 session 的暫存目錄，session 結束後不保證還在：

- `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/2744140d-da10-4f27-b2d5-07eff2517712/scratchpad/scripts/crawl_pipermail.cjs`：無頭 Chrome 抓月封存
- `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/2744140d-da10-4f27-b2d5-07eff2517712/scratchpad/scripts/scan_archive.py`：全文搜尋（`list`／`show`／`ctx`／`subj`）
- `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/2744140d-da10-4f27-b2d5-07eff2517712/scratchpad/crawl-out/lo-archive/`：11 個 `.txt.gz`

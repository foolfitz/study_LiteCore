# 產業方向：辦公套件的運算往 client 移，這件事有多少證據

> 2026-11-10 查。起因：前輩問「跟過去的 Online 比起來好在哪裡」，需要外部證據佐證 LiteCore 的存在價值。
> 要查證的說法：「歐盟政策朝輕 server、重 client 的去中心化方向走；Collabora 與 OnlyOffice 都在做 WASM。」
> 證據標記：**已觀察**＝subagent 讀了原頁並回報原文片段；**搜尋摘要**＝只看到搜尋引擎的摘要，沒讀原頁；**推論**＝我的歸納。
> 我自己沒有直接讀任何一個原頁，引用前請點連結核對。相關：`research/RESEARCH-2026-08-20-product-route-and-competitors.md`（8 月的競品實測）。

## 結論

1. **「輕 server、重 client」這句話有出處，但不是歐盟政策。**它是 TDF 自己 2026-05-30 提案裡的設計原則，理由是託管成本。歐盟層級查不到任何一份政策文件這樣要求辦公套件。
2. **歐盟真正存在的相關證據是「錢」不是「法規」。**歐盟的 NGI 計畫透過 NLnet 至少三次資助「LibreOffice 完全在瀏覽器端執行、不依賴伺服器」這個方向，另外資助了 CryptPad 把 OnlyOffice 的伺服器端元件換成 client 端。
3. **廠商確實都在把運算往 client 移，但程度差很多，而且沒有一家做到零伺服器。**Collabora 的 WASM 是斷線備援；OnlyOffice／Euro-Office 編輯在瀏覽器但仍要一台 Document Server；OnlyOffice 官方在做 WASM 這件事沒查到證據。
4. **對「比 Online 好在哪」最站得住的答案是伺服器負載**，而且有第三方與 TDF 自己的白紙黑字可引。
5. **有兩個論點不要用**：「歐盟政策要求」與「RGESN 支持重 client」。後者讀原文反而對我們不利。

## 1. 那句話的出處

### TDF 提案（已觀察）

<https://blog.documentfoundation.org/blog/2026/05/30/web-and-mobile-development-strategy-proposal/>

- 「we should perform all expensive computations on the client side」，出現在 Lessons 的〈On-premises hosting – no privileged cloud provider〉一節。
- 理由是成本，不是政策：「Application hosting costs have risen dramatically」；要「designed to respect the limited computational and bandwidth resources of small cloud operators」；要「design toward a world of many small clouds」。
- 對舊架構最直接的一句：「We can no longer expect users to host applications that perform unnecessary computation inside the datacenter」。
- 提案**沒有**出現 EU、Europe、sovereignty、GDPR 這些字；隱私、離線、可擴展性也都不是它給的理由。
- 唯一提到政策的地方是引法國的 RGESN，說它「mandates software eco-design principles and resource efficiency for certain types of public procurement」，並說「Many other jurisdictions are developing similar regulations, including Germany and the UK.」提案沒有把「運算放 client」歸因於 RGESN。

### heise 的第三方轉述（已觀察）

<https://www.heise.de/en/background/Three-free-office-suites-vs-Microsoft-365-technology-comparison-11330876.html>（2026-06-13，Moritz Förster）

- 把 TDF 的計畫描述成「The goal is a local-first architecture where the main work is done on the end device.」
- 你「依稀看過」的說法，最可能是這篇或它的轉載。

## 2. 政策面：查得到什麼、查不到什麼

### RGESN：不支持「重 client」，引用它有風險（已觀察）

<https://ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/>

- **是法國的，不是歐盟的。**它引用了幾份歐盟文件（DSA、資料中心行為準則等），但沒有指向任何歐盟層級的軟體生態設計法規。
- **它自稱是自願性的**：「Il s'agit d'abord de promouvoir une démarche volontaire」。這和 TDF 提案寫的「mandates … for certain types of public procurement」有出入，哪個對沒查。
- **沒有任何一條準則說運算該放 client 或 server。**它關心的是終端負擔、網路傳輸量、伺服器資源浪費。
- **反而有幾條對大型 WASM client 不利**：
  - 2.2：網頁服務要能在 CPU「mis sur le marché il y a dix ans ou plus」的裝置上用。
  - 6.1：每個畫面的重量與請求數要設上限，舉的例子是 2 MB 降到 1 MB。
  - 6.4：以「minimiser la consommation d'énergie du terminal」為目標，圖片縮放「doit être réalisé côté serveur」。
  - 8.6：把資料中心放近使用者「ne correspond pas à adopter les technologies Edge Computing」。
- 它贊成的 client 端工作是輕量的：表單先在 client 驗證（4.10）、client 快取與本地暫存（6.2）、減少往返（4.9）。

### 歐盟的 edge 政策：是基礎設施，不是瀏覽器（搜尋摘要）

<https://digital-strategy.ec.europa.eu/en/policies/cloud-computing>

- 執委會的雲端政策頁寫：到 2025 年，80% 的資料預期會在靠近使用者的智慧裝置上處理（edge computing）。
- Digital Decade 的目標是 2030 年前 10,000 個氣候中和、高度安全的 edge 節點。
- 這是歐盟確實存在的「去中心化」政策方向，但講的是邊緣節點與物聯網，不是「辦公軟體在瀏覽器裡跑」。拿來當背景可以，當依據太牽強。**推論**

### 歐盟的資助：這才是直接證據

| 專案 | 經費來源 | 頁面上怎麼說 | 標記 |
| --- | --- | --- | --- |
| [ZetaOffice](https://nlnet.nl/project/ZetaOffice/) | NGI0 Discovery，2020-08 至 2022-10，執委會 NGI 計畫，grant 825322 | 「run fully client-side inside a regular browser」；「remove the entire dependency on a server」；「no single-point of architectural failure exists」 | 已觀察 |
| [LibreOffice CRDT](https://nlnet.nl/project/LibreOffice-CRDT/) | NGI0 Entrust，2023-02 至 2026-01，allotropia，grant 101069594 | 多個分散的 LibreOffice 實例之間的即時協作；頁面沒寫 P2P 或無伺服器 | 已觀察 |
| [LibreOffice P2P](https://ngi.eu/funded_solution/libreofficep2p) | NGI Zero Discovery | 標語「Encrypted collaborative editing in the browser」，其餘內容很少 | 已觀察 |
| [CryptPad](https://blog.cryptpad.org/2025/01/28/CryptPad-Funding-Status-January-2025/) | NGI Assure，13.5 萬 | 經費「very much directed towards the integration APIs and the OnlyOffice integration」 | 搜尋摘要 |

ZetaOffice 那頁的動機寫得最完整：信任（能進伺服器的人「can read everything you have written」）、去中心（中央單位「more vulnerable to attack, misuse and censorship」）、端到端加密。

德國內政部（BMI）也給過 Collabora 與 allotropia 離線瀏覽器編輯的原型補助，見 8 月研究的 §4.1。那是國家層級。

## 3. 廠商面：誰把運算放在哪裡

| | 編輯引擎在哪 | 伺服器還要做什麼 | WASM |
| --- | --- | --- | --- |
| Collabora Online | 伺服器 | 全部：算文件狀態、算磚 | 有，但只是斷線備援 |
| Euro-Office／OnlyOffice | 瀏覽器（JS＋canvas） | 一台 Document Server：session、轉檔、儲存、共編 | 官方：沒查到 |
| CryptPad（用 OnlyOffice） | 瀏覽器 | 只存加密資料 | 有：把轉檔器編成 WASM |
| TDF 計畫 | 瀏覽器（Qt6＋WASM） | 送檔案、管權限、協調共編 | 原型，未出貨 |
| LiteCore | 瀏覽器（headless WASM） | 0 個行程，檔案由 Nextcloud 存 | 已可手測 |

### Collabora

- **Online 是伺服器端架構**（已觀察，heise）：「The actual office engine does not run in the browser but on the Collabora server.」「The server calculates the document state and sends back the rendered areas.」瀏覽器是「more of an interactive, remotely controlled LibreOffice」。
- **COWASM**（搜尋摘要，FOSDEM [2023](https://archive.fosdem.org/2023/schedule/event/lotech_coolwasm01/)／[2024](https://archive.fosdem.org/2024/schedule/event/fosdem-2024-2828-collabora-online-wasm/) 投影片）：斷線時，瀏覽器端啟動一個含 Collabora Online 伺服器功能的 WASM 程式接手。2024 年的投影片自己列的限制：連結要超過 25 GB RAM、只有 online→offline 單向。8 月我們讀 `cool-26-04` 原始碼的結論一致：它是伺服器產品的離線備援，不是獨立產品。
- **Collabora Office 桌面版**（搜尋摘要，[新聞稿](https://www.collaboraonline.com/blog/press-release-bringing-collabora-online-to-the-desktop/)，2025-11 首發）：把 Online 的 JavaScript／canvas 介面搬到本機執行，不需要伺服器。這不是 WASM，但方向相同：同一套網頁介面，運算在使用者的機器上。

### OnlyOffice 與 Euro-Office

- **架構**（已觀察，heise）：編輯器是瀏覽器裡的 JS＋canvas，但「The Document Server remains central nonetheless.」它「handles sessions, conversion, storage, and collaborative editing.」
- **伺服器需求**（搜尋摘要，[Nextcloud 安裝指南](https://nextcloud.com/blog/how-to-install-euro-office/)）：最低 4 GB RAM、多人建議 8 GB，另外要 PostgreSQL、Redis、RabbitMQ、nginx。與 8 月的實測一致。
- **「OnlyOffice 在做 WASM」沒有查到官方證據。**找到的是 CryptPad 的 [`onlyoffice-x2t-wasm`](https://github.com/cryptpad/onlyoffice-x2t-wasm)（2024-04 建立）與幾個社群專案，都是第三方把 OnlyOffice 的轉檔器編成 WASM 來取代伺服器。CryptPad 4.12.0 的[發行說明](https://github.com/cryptpad/cryptpad/releases/tag/4.12.0)說它用 OnlyOffice 的 client 端元件，而伺服器端元件「completely replaced」。（搜尋摘要）

### 套件之外的兩個訊號（搜尋摘要）

- **Microsoft 讓地端的網頁版 Office 退場。**Office Online Server 在 2025-10-21 宣布、**2026-12-31 終止支援**（[Microsoft 公告](https://techcommunity.microsoft.com/blog/officeeos/announcing-the-retirement-for-office-online-server/4462402)）。TDF 提案的註腳寫「discontinued in October 2025」，那是宣布日，不是終止日。
- **Google Sheets 的計算引擎一路往 client 搬。**最早全在伺服器算，2013 年搬進瀏覽器用 JavaScript，2024 年再改成 WasmGC，官方案例說比 JS 版快約兩倍（[web.dev](https://web.dev/case-studies/google-sheets-wasmgc)）。

## 4. 回答「比過去的 Online 好在哪」

**可以直接引用的三件事**

1. **Online 架構的代價是伺服器負載，這是第三方的評語，不是我們自己說的。**heise：「The price is the server load.」「biggest disadvantage remains the high server load.」而且它是有狀態的服務，「all connections to a document must land on the same server or pod」，橫向擴展因此困難。LiteCore 在伺服器上沒有任何行程。
2. **LibreOffice 的上游自己已經放棄那個模型。**TDF 提案：「We can no longer expect users to host applications that perform unnecessary computation inside the datacenter」。LiteCore 走的是 TDF 宣告要去的方向，而且已經能手測；TDF 那邊還是原型（heise：「not a short-term option but a bet on architecture」）。
3. **同方向的其他人都還留著一台伺服器。**Euro-Office 要 4–8 GB 的 Document Server；Collabora 的 WASM 只在斷線時接手。「引擎是 LibreOffice、格式是 ODF 原生、真的零伺服器行程」這個組合目前沒有別人在出貨。**推論**，依據是上表與 8 月的實測。

**對方一定會反問的，要先準備**

heise 同一篇也列了 client 端架構的代價：首次啟動慢；「Processor, RAM, browser functions, and battery life become more important」；多執行緒與 SharedArrayBuffer 需要特殊的 HTTP 標頭；套件大小、記憶體用量、共編都還是未解問題。這些我們都量過，答案在 8 月研究的 §1。

## 5. 不要用的論點

- **「歐盟政策要求輕 server、重 client」**：查不到這樣的政策。能說的是「歐盟的 NGI 計畫資助過這個方向」。
- **「RGESN 支持我們」**：它要求網頁服務在十年前的 CPU 上能用、每個畫面以 1–2 MB 為目標。幾十 MB 的 WASM 引擎拿它當依據，會被讀過原文的人反駁。
- **「OnlyOffice 也在做 WASM」**：做的是 CryptPad，不是 OnlyOffice 官方。
- **「歐洲主權的錢會流向我們這種架構」**：目前流向的是 Euro-Office 與 openDesk，兩者都是有伺服器的架構。受過 NGI 資助、最接近我們的 ZetaOffice 已經休眠（8 月研究 §4.3）。方向被資助過，不等於市場買單。

## 6. 沒查的

- RGESN 在法國公共採購裡到底有沒有強制力（TDF 的說法與它自述不一致）。
- 德國、英國「正在制定類似規範」是哪幾份文件（TDF 提案沒給連結）。
- OnlyOffice 的 sdkjs 裡有沒有官方的 WASM 元件（要讀它的 repo）。
- Collabora 26.04 的 COWASM 現況有沒有超出 2024 年投影片所述。
- TDF 論壇上提案討論串的內容（Anubis 擋）。

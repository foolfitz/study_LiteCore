# 把 LibreOffice 帶進瀏覽器：TDF 的 Web 與行動版方向

TDF 在 2026 年提出的 [Web and Mobile Development Strategy Proposal](https://blog.documentfoundation.org/blog/2026/05/30/web-and-mobile-development-strategy-proposal/)，不是一份已經排好日期的產品藍圖，而是重新選定技術路線：LibreOffice 不另寫一套 Web 辦公軟體，而要讓既有桌面版的核心直接走向瀏覽器與行動裝置。TDF 隨後公布的團隊與董事會會議紀錄，也把 Qt 6、WebAssembly 和 client-server 協作列為 2026 年的實際工作重點。

這項決定的出發點，是不想重演桌面版與 Web 版各自發展、最後功能和排版逐漸分岔的問題。Writer、Calc、Impress 累積多年的文件模型、排版引擎與格式轉換能力，才是 LibreOffice 最難取代的資產。把這些 C++ 程式編譯成 WebAssembly，雖然不像重新開發一套 JavaScript 編輯器那麼輕巧，卻能讓桌面、Web 和 Mobile 共用大部分程式碼，也比較有機會維持 ODF、OOXML 文件在不同平台上的一致性。

Qt 6 在這條路線中扮演共同的平台層。TDF 計畫繼續改善 Qt 6 的 VCL backend，讓同一套 LibreOffice 可以在瀏覽器、Android 與 iOS 上運作，再配上一套會隨視窗大小與觸控環境調整的介面。Web 版預設可以只呈現日常閱讀與簡單編輯所需的功能，複雜工作則交回桌面版；精簡的是操作入口，不是另外打造一個能力較弱的文件核心。

另一個關鍵選擇，是把昂貴的文件解析、排版與編輯盡量留在使用者裝置。未來的文件伺服器主要負責提供文件、串接儲存服務和協調共同編輯，而不是替每位使用者長時間執行完整 LibreOffice。TDF 希望藉此降低自架成本，形成許多學校、組織或服務商都能負擔的「小型雲端」，同時避免讓 LibreOffice 綁在單一官方雲端供應商上。

協作功能也採取循序漸進的作法。第一步會先讓 LibreOffice instance 透過直接 TCP/IP 連線，建立具有單一權威狀態的 client-server 模型；待同步、衝突和文件狀態的基本問題穩定後，再讓文件伺服器擔任協調者。P2P 仍是長期願景，但不會和最初的協作實作綁在一起。

LibreOffice 26.8 已能看出這些選擇並非只停留在簡報上。Qt 6 + WASM 已可啟動 Start Center 與 Writer，LibreOfficeKit 也具備文件載入、圖磚渲染、輸入、callback、多視圖與存檔等基礎 API；程式碼中甚至已有利用 yrs CRDT 同步 Writer 留言的實驗，不過仍限制文件本體為唯讀。這些成果比較像可行性證明，而不是成熟產品：WASM 的下載量、記憶體、輸入法、觸控介面與協作協定，仍需要相當多工程整理。

因此，TDF 的方向不是把桌面版原封不動塞進網頁，而是以同一個 LibreOffice 核心為中心，逐步補上適應不同螢幕的介面、低成本文件服務與跨平台協作。它押注的是程式碼共用、使用者端運算和可自行架設的開放生態；Web、Mobile 與桌面版最終將是同一套文件技術在不同場合下的呈現，而不是彼此相似卻互不相通的產品。這是一條務實，但仍需長期打磨的道路。

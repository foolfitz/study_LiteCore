# finding 002 白話說明：官方說明文件叫人跑的示範程式跑不起來，我們把它修好了

2026-11-11。對應的 Bugzilla 草稿是 `findings/drafts/002-bugzilla.txt`（英文，給上游看），要貼到 Bugzilla 的文字是 `findings/drafts/002-bugzilla-paste.txt`。這份是給你看的。

## 一句話

LibreOffice 的 WASM 建置說明（`static/README.wasm.md`）列了兩個「建完就能在瀏覽器跑」的東西：一個是 LibreOffice 本體（`qt_soffice.html`），一個是 VCL 繪圖示範程式（`qt_vcldemo.html`）。第二個**每次都跑不起來**，原因有兩個：

1. 連結時少了「把資料檔載入虛擬檔案系統」的那段程式碼；
2. 補上之後，它的主視窗一顯示就被銷毀了。

兩個都修好了：連結設定加 8 行、vcldemo.cxx 加 17 行。你也在自己的瀏覽器上看過它正常運作了。

## vcldemo 是什麼

- LibreOffice 畫面上的一切，最底層都由 **VCL** 這個程式庫負責畫。vcldemo 是 VCL 的**體檢表**：它把 VCL 會的基本動作（線、文字、多邊形、漸層、點陣圖、裁切等 14 項）各畫一格，點一格就放大成更完整的測試，按 Escape 回到格子。
- 名字裡的 `qt_` 是建置規則自動加的前綴，不代表任何性質。
- 它是給開發者的測試程式，不會被安裝。用途是移植到新平台時，不必開整個 office，就能先確認繪圖層正不正常。

## 先講背景：WASM 版怎麼拿到它的檔案

瀏覽器裡沒有硬碟。LibreOffice 啟動時要讀的設定檔、字型、`unorc` 這些，全部預先打包成一個大檔 `soffice.data`（約 87 MB）。另外有一小段 JavaScript（Emscripten 的 `file_packager` 產生的載入器）負責在程式啟動前把它下載下來、攤開成虛擬檔案系統。

這段載入器是在**連結時**以 `--pre-js` 的方式塞進每個程式的 `.js` 裡的。打個比方：`soffice.data` 是行李箱，載入器是打開行李箱的那個人。

## 第一個原因：沒人開行李箱（已觀察）

- 在**上游 master、沒有任何本地修改、照 README 建議的組態**下建置，然後照 README 跑 `qt_vcldemo.html`：
  - 畫面全白；
  - 主控台在 0.6 秒印出 `Bootstrap exception Cannot open uno ini file:///instdir/program/unorc`；
  - 網路請求裡**從頭到尾沒有去要 `soffice.data`**。
- **對照組**（同一份建置、同一種伺服方式）：`qt_soffice.html` 在 0.6 秒去要了 `soffice.data`，然後正常走到開始中心。
- 直接看產出的檔案：`vcldemo.js` 裡找不到 `soffice.data` 或 `loadPackage` 任何一個字，`soffice.js` 裡找得到。
- **行李箱其實有送到**。建置規則會把 `soffice.data` 複製到每個程式旁邊，vcldemo 旁邊也有，只是沒有人去開它。
- 原始碼裡，載入器只在 `desktop/Executable_soffice_bin.mk`（LibreOffice 本體）加上，`vcl/Executable_vcldemo.mk` 沒有。但 `vcl/Module_vcl.mk` 又在 WASM＋Qt5 時**特地**建 vcldemo，看起來上游是想讓它能跑的。
- 7/31 在 26.8 分支上第一次看到時也是一模一樣的錯。26.8.2.2、26.8.3.1 的相關檔案跟當時完全相同，這兩個只讀了原始碼，沒實際跑。

**為什麼會這樣**（推論，沒有實驗證明）：翻 git 歷史找到一個很可能的起點，`cf0b0f0dd04f`（2024-04-30，最早進 24.8）。

- 在那之前，載入器是加給**所有**程式的，vcldemo 應該也有。
- 那個 commit 為了修另一個問題，把載入器改成**只給 LibreOffice 本體**。那個問題是：在 node 底下跑的小工具 `uri-encode.js`，會因為載入器呼叫了瀏覽器才有的 `XMLHttpRequest` 而掛掉。
- 結果 vcldemo 被連帶拿掉了。README 那一行（2022 年寫的）沒跟著改，複製 `soffice.data` 的規則也沒拿掉。那個 commit 的訊息自己寫了「can probably be cleaned up further in a next step」，但那「下一步」一直沒有發生。

這段是**讀歷史推出來的**，我們沒有建一棵 2024 年 4 月以前的樹去證明 vcldemo 當時真的能跑。

## 第二個原因：視窗一顯示就被拆掉（已觀察）

補上載入器（修法 F1）之後，vcldemo 拿到了資料檔，`Cannot open uno ini` 也消失了，但畫面還是空的。追查的經過：

1. **SAL_LOG 開不了**：README 建議的發行組態把 log 在編譯時就拿掉了。所以改在 vcldemo.cxx 裡加幾行印出訊息的探針，只重編一個檔再重連結，每輪約 3 分鐘。
2. **它其實有畫**：探針顯示主視窗建出來了、大小 1165×670、也畫過一次。但程式一進事件迴圈，畫面就沒了；之後只要點一下，程式就中止。
3. **在視窗被銷毀時印一行**：結果那一行緊接在「進入事件迴圈」之後出現。主視窗是被拆掉的。

為什麼會被拆掉，用一個比方：

- 一般程式進入事件迴圈後會**停在那裡等**，手邊的東西（視窗、繪圖器）都還擺在桌上。
- 在瀏覽器裡，Qt 的事件迴圈不能這樣停著等，它的做法是**丟出一個例外，把整個呼叫堆疊拆掉**，之後改由瀏覽器定時回來叫它。
- LibreOffice 的 WASM 版用的例外機制（`-fwasm-exceptions`），在拆堆疊時會把堆疊上的物件**一個一個收掉**。vcldemo 把主視窗放在堆疊上，所以視窗剛顯示就被收走了。
- **soffice 早就踩過這個坑**：`desktop/source/app/sofficemain.cxx` 有一大段註解寫的就是這件事，它的解法是故意把 `Desktop` 物件放到堆疊外、永不回收。

**修法 F3** 就是照 soffice 的做法：在 WASM 上把 vcldemo 的繪圖器和視窗也放到堆疊外。

## 修好之後（已觀察）

- 最終修法是 **F1＋F3**，一個 commit：連結設定 +8 行、vcldemo.cxx +17 行。patch 在 `findings/evidence/002/fix-2a2335cf/fix-final.patch`。
- 用 11-10 同一支探針、同一棵樹跑：
  - 去要了 `soffice.data`，沒有 bootstrap 錯誤；
  - 1.0 秒開始畫，畫出 14 格繪圖測試；
  - 點一格會放大，按 Escape 會回到格子，全程沒有錯誤。
- 你在自己的瀏覽器上看過，點一格會放大。
- **中途還試過 F2**（把程式搬到瀏覽器的背景執行緒上跑，跟 soffice 一樣），事後證明**不需要**。我原本推論「F1 之後會卡在開執行緒」，這個推論是錯的。
- **縮圖和放大長得不一樣**是設計如此：14 項裡有 7 項放大時會畫另一套更完整的測試。
- **沒驗的**：`--widgets`、`--popup`、`--font`、`--threads` 這幾個模式；放大後每一格有沒有畫對（手邊沒有原生版的畫面可以對照）。

## 草稿說了什麼、刻意沒說什麼

**說了**：
- 重現步驟、網路與主控台紀錄、同一份建置的 `qt_soffice.html` 對照、原始碼的差別；
- 可能的起點，標明是讀歷史得來的；
- 一句話說明為什麼值得修：vcldemo 是在瀏覽器裡、不經過 framework 和文件，就能測 VCL 繪圖、排版和輸入的最小程式，可以用來判斷問題出在 VCL 以下還是以上（你 11-11 要求加的，不細談）；
- 測過的修法：兩個原因各自怎麼修，F2 不需要，只測了預設模式；
- 另一個選項：如果上游不打算讓 vcldemo 在瀏覽器跑，就從 README 拿掉那一行。

**沒說**：
- vcldemo 在 `cf0b0f0dd04f` 之前能不能跑：沒建過那麼舊的樹；
- 推論出來的 configure 回歸成因（見〈順帶發現〉）：草稿只寫了觀察到的錯誤訊息。

**結尾有一句「We can submit the patch to Gerrit.」**：等於向上游表示我們會送 patch。你說 Gerrit 之後再談，所以如果還不想給這個預期，送之前把這句刪掉就好。

## 跟我們的產品有沒有關係

**沒有。**我們的產品走 LOK 引擎，不用 Qt，也不用 vcldemo，這張是單純回饋上游。它的價值在於好送：兩個原因都有證據、修法很小、上游不必建置也能從原始碼看懂。依 findings 的送出順序，這類單應該最先送，可以先跟維護者建立信任。

## 欄位（2026-11-11 對 Bugzilla 實查後修正）

| 欄位 | 值 | 備註 |
|---|---|---|
| Product | LibreOffice | |
| Component | LibreOffice | finding 原本寫的「Build tooling」**在 TDF Bugzilla 不存在**；README.wasm.md 的錯字單 tdf#169649 也歸在 LibreOffice |
| Version | 27.2.0.0 alpha0+ master | 選單裡沒有 finding 原本寫的「26.8.0.1 rc」；乾淨的重現是在 master 上做的 |
| Hardware / OS | All / All | OS 選單沒有 WASM 這個值 |
| Severity | normal | |

## 查重複與送出

- 2026-11-11 早上用 Bugzilla 的 REST API 查留言全文：`qt_vcldemo`、`vcldemo.html`、`soffice.data`、`emscripten_fs_image` 都是 0 筆。提到 vcldemo 的 10 張全是原生版的問題（例如 Linux 上關視窗時 assert、macOS 上不開視窗），沒有 WASM 的。
- 下午送出前又重查一次，加查了第二個原因的關鍵字（`QApplication::exec`、`simulateInfiniteLoop`），還是沒有重複。最新 master（`13788461`）上相關檔案都沒變。收據放在 `findings/evidence/002/dup-search-2026-11-11.txt`。
- **送出**：2026-08-15 起擱置的上游送出，你在 11-11 下午指示「這個 finding 先回報」，只解除 002。你已經送出：**tdf#174440**。修法的 Gerrit commit 也準備好了（標題帶 `tdf#174440`），由你自己推。

## 順帶發現

- **今天的上游 master 連 WASM 的 configure 都過不了**（已觀察）：
  - `e42678e7` 用同樣的選項，configure 會同時選到 gtk3 和 qt5 兩個介面外掛，然後失敗。我們因此改用 11-10 的 `2a2335cf` 建置。
  - 推論（只讀了原始碼）：成因是 11-10 晚上合進去的 `d98a796946ff`。
  - 要不要另開一張 finding，之後再談。
- **vcldemo 的「圖示」那格縮圖是空的**：它應該畫出工具列的小圖示，在瀏覽器上沒畫出來。沒有查原因。
- finding 003 的草稿（`findings/drafts/003-bugzilla.txt`）的 Component 也寫「Build tooling」，同樣不存在。這次沒有改它，等要送 003 時再一起處理。

## 修訂紀錄

- 2026-11-11 上午：初版（只有第一個原因，修法未測）。
- 2026-11-11 下午：補上 vcldemo 是什麼、第二個原因、修好之後的結果、送出狀態，以及兩項順帶發現；標題改成「我們把它修好了」。
- 2026-11-11 下午：草稿加一句除錯價值。
- 2026-11-11 晚上：記上 tdf#174440 與 Gerrit 準備狀態。

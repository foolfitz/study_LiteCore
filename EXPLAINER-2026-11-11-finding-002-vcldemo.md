# finding 002 白話說明：官方說明文件叫人跑的示範程式，本來就跑不起來

2026-11-11。對應的 Bugzilla 草稿是 `findings/drafts/002-bugzilla.txt`（英文，給上游看），這份是給你看的。

## 一句話

LibreOffice 的 WASM 建置說明（`static/README.wasm.md`）列了兩個「建完就能在瀏覽器跑」的東西：一個是 LibreOffice 本體（`qt_soffice.html`），一個是 VCL 繪圖示範程式（`qt_vcldemo.html`）。第二個**每次都跑不起來**，因為它被連結時少了「把資料檔載入虛擬檔案系統」的那段程式碼。

## 先講背景：WASM 版怎麼拿到它的檔案

瀏覽器裡沒有硬碟。LibreOffice 啟動時要讀的設定檔、字型、`unorc` 這些，全部預先打包成一個大檔 `soffice.data`（約 87 MB）。另外有一小段 JavaScript（Emscripten 的 `file_packager` 產生的載入器）負責在程式啟動前把它下載下來、攤開成虛擬檔案系統。

這段載入器是在**連結時**以 `--pre-js` 的方式塞進每個程式的 `.js` 裡的。打個比方：`soffice.data` 是行李箱，載入器是打開行李箱的那個人。

## 我們看到什麼（已觀察）

- 在**上游 master、沒有任何本地修改、照 README 建議的組態**下建置，然後照 README 跑 `qt_vcldemo.html`：
  - 畫面全白；
  - 主控台在 0.6 秒印出 `Bootstrap exception Cannot open uno ini file:///instdir/program/unorc`；
  - 網路請求裡**從頭到尾沒有去要 `soffice.data`**。
- **對照組**（同一份建置、同一種伺服方式）：`qt_soffice.html` 在 0.6 秒去要了 `soffice.data`，然後正常走到開始中心。
- 直接看產出的檔案：`vcldemo.js` 裡找不到 `soffice.data` 或 `loadPackage` 任何一個字，`soffice.js` 裡找得到。
- 最荒謬的一點：**行李箱有送到**。建置規則會把 `soffice.data` 複製到每個程式旁邊，vcldemo 旁邊也有，只是沒有人去開它。
- 原始碼裡，載入器只在 `desktop/Executable_soffice_bin.mk`（LibreOffice 本體）加上，`vcl/Executable_vcldemo.mk` 沒有。但 `vcl/Module_vcl.mk` 又在 WASM＋Qt5 時**特地**建 vcldemo，看起來上游是想讓它能跑的。
- 7/31 在 26.8 分支上第一次看到時也是一模一樣的錯；26.8.2.2、26.8.3.1 的相關檔案跟當時完全相同（這兩個只讀了原始碼，沒實際跑）。

## 為什麼會這樣（推論，沒有實驗證明）

翻 git 歷史找到一個很可能的起點：`cf0b0f0dd04f`（2024-04-30，最早進 24.8）。

- 在那之前，載入器是加給**所有**程式的，vcldemo 應該也有。
- 那個 commit 為了修另一個問題（在 node 底下跑的小工具 `uri-encode.js` 因為載入器呼叫了瀏覽器才有的 `XMLHttpRequest` 而掛掉），把載入器改成**只給 LibreOffice 本體**。
- 結果 vcldemo 被連帶拿掉了，但 README 那一行（2022 年寫的）沒跟著改，複製 `soffice.data` 的規則也沒拿掉。該 commit 的訊息自己寫了「can probably be cleaned up further in a next step」，那「下一步」一直沒有發生。

這段是**讀歷史推出來的**：我們沒有建一棵 2024 年 4 月以前的樹去證明 vcldemo 當時真的能跑。草稿裡也明講了這一點，而且整段刪掉也不影響這張單成立。

## 草稿說了什麼、刻意沒說什麼

**說了**：重現步驟（照 README 建置、跑 `qt_vcldemo.html`）、網路與主控台紀錄、同一份建置的 `qt_soffice.html` 對照、原始碼的差別，以及可能的起點（標明是讀歷史得來的）。

**給上游選的兩個修法**（兩個都沒試過）：

- **(a)** vcldemo 還想在瀏覽器跑：把 `soffice_bin` 那段 EMSCRIPTEN 區塊照抄到 `vcl/Executable_vcldemo.mk`。這只影響 vcldemo，不會把 node 那個問題帶回來。
- **(b)** vcldemo 不需要在瀏覽器跑：從 README 拿掉那一行，或者乾脆不在 WASM 上建 vcldemo。

**沒說**：vcldemo 有了資料檔之後能不能真的正常畫出東西——這個我們不知道，草稿也沒有宣稱。

## 跟我們的產品有沒有關係

**沒有。**我們的產品走 LOK 引擎，不碰 vcldemo，這張是單純回饋上游。它的價值在於好送：根因確定、上游不必建置也能從原始碼看懂、修法很小。依 findings 的送出順序，這類「根因確定、修法很小」的單應該最先送，可以先跟維護者建立信任。

## 欄位（2026-11-11 對 Bugzilla 實查後修正）

| 欄位 | 值 | 備註 |
|---|---|---|
| Product | LibreOffice | |
| Component | LibreOffice | finding 原本寫的「Build tooling」**在 TDF Bugzilla 不存在**；README.wasm.md 的錯字單 tdf#169649 也歸在 LibreOffice |
| Version | 27.2.0.0 alpha0+ master | 選單裡沒有 finding 原本寫的「26.8.0.1 rc」；乾淨的重現是在 master 上做的 |
| Hardware / OS | All / All | OS 選單沒有 WASM 這個值 |
| Severity | normal | |

## 查重複（2026-11-11）

用 Bugzilla 的 REST API 查留言全文：`qt_vcldemo`、`vcldemo.html`、`soffice.data`、`emscripten_fs_image` 都是 0 筆。提到 vcldemo 的 10 張全是原生版的問題（例如 Linux 上關視窗時 assert、macOS 上不開視窗），沒有 WASM 的。收據放在 `findings/evidence/002/dup-search-2026-11-11.txt`。

**送出擱置中**（2026-08-15 起）。真要送時要重查一次，因為重複單隨時可能出現。

## 順帶發現

finding 003 的草稿（`findings/drafts/003-bugzilla.txt`）的 Component 也寫「Build tooling」，同樣不存在。這次沒有改它，等要送 003 時再一起處理。

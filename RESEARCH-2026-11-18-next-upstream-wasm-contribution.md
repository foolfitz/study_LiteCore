# 下一個 LibreOffice WASM 上游貢獻：候選排序

> 2026-11-18。基線是 [`RESEARCH-2026-11-10-upstream-reportable-findings-wasm-qt.md`](RESEARCH-2026-11-10-upstream-reportable-findings-wasm-qt.md)（185 份 finding 裡 WASM／Qt 範圍的盤點）。這份只補那之後一週的變化，並對現行 master 重驗。
> 上游 master：`ac53621f754f`（Gerrit 與 GitHub 鏡像今天相同）。
> 證據標記：**已觀察**＝今天直接查到；**依 finding**＝照既有檔案的記載，今天沒重驗；**推論**＝沒有直接量到。
> 今天沒有建置、沒有送出任何東西、沒有改動任何 finding 檔或上游工作樹的檔案（只有 `git fetch origin master` 更新了遠端追蹤分支）。

## 結論

1. **最該先送的 MR：修 master 的 WASM configure 回歸。**照 README 的 `--with-distro=LibreOfficeWASM32` 在 master 上連 configure 都過不了。成因確定、修法只有幾行、不必編譯就能驗；上游的 Christian Lohmaier 昨天（11-17）在 Gerrit 上點出同一個成因，但還沒有人送修正。**不必另開 issue。**這一則有時效，別人隨時會修掉。
2. **最該先開的 issue（附 MR）：finding 159。**上游的 WASM Calc 裡，Analysis／Date／Pricing add-in 的函數（EOMONTH、NETWORKDAYS、YEARFRAC、XIRR 這一整類）一律 `#VALUE!`。成因確定，今天在 stock master 的建置產物上靜態確認；修法是一個 `.mk` 檔的 6 行 patch，已隨我們的產品出貨（0.2.32 起）。只差在 stock 建置上執行期重現一次，不必重建就能做。
3. 第三順位是 003（gbuild 的 race，最便宜，但不是 WASM 專屬）；114 影響大但審查成本高，排在 159 之後。其餘順序見〈其餘候選〉。
4. tdf#174440 與它的 Gerrit change 214058 都在正常等待中，沒有要處理的事。

## 上一則的現況（已觀察）

| 項 | 狀態 |
| --- | --- |
| [tdf#174440](https://bugs.documentfoundation.org/show_bug.cgi?id=174440) | UNCONFIRMED，只有我們自己的第一則留言，11-11 之後沒有變動 |
| [Gerrit 214058](https://gerrit.libreoffice.org/c/core/+/214058) | NEW，Patch Set 1，Jenkins Verified+1（11-12），還沒有 reviewer 與 Code-Review |

擁有者 11-18 的說明：上游審查很慢，等兩週算正常。所以不催、不加 reviewer。

一個關聯：214058 的 commit message 寫的是在 `2a2335cf` 上測的。審查的人若想在現行 master 上建 WASM 來試，會先撞上第一優先那個 configure 失敗。

## 第一優先：master 的 WASM configure 回歸（只送 MR）

**現象**（已觀察，11-11 的 log：`findings/evidence/002/fix-2a2335cf/e42678e7-configure-fail.log`）：stock 的 `--with-distro=LibreOfficeWASM32` 加上與 VCL 無關的旗標，configure 停在

```
configure: VCLplugs to be built: gtk3 qt5
configure: error: Can't build --disable-dynamic-loading without --disable-gui and a single VCL plugin"
```

**成因**（已觀察，讀 diff）：`d98a796946ff`「tdf#146153 Enable building the GUI --without-x」（Gerrit 211916，11-10 合併）。

- 之前：Emscripten 的 wasm-strip 設 `with_x=no`，於是 `disable_x11_tests` 把 gtk3、gtk4、kf5、kf6、cups、dbus 等測試全關，再因為 `DISABLE_DYNLOADING` 把 qt5／qt6 開回來。
- 之後：gtk 那一組搬到新的 `disable_unix_desktop_tests`，只有 `--disable-gui` 才呼叫。`emscripten)` 區塊被標成 `using_unix_desktop=yes`，`test_gtk3` 跟著變 yes，而 gtk3 預設啟用。
- 所以只有 GUI 建置壞掉；`--disable-gui`（我們 headless 探針的路）仍會走到 `disable_unix_desktop_tests`，不受影響。**推論**（讀程式，沒跑）

**現行 master 仍在**（已觀察）：`e42678e7` 到 `ac53621f` 之間 `configure.ac` 只差一個 hunk（第 15630 行，捐款橫幅），失敗的那段邏輯逐位元組相同。今天沒有重跑 configure。

**上游已經知道，但沒人修**（已觀察）：

- Christian Lohmaier 11-17 在已合併的 [211916](https://gerrit.libreoffice.org/c/core/+/211916) 的 `configure.ac` 上留言：「having that set here will cause the vclplugins to get auto-tested but the emscripten variant implies disable-dynloading and that in turn only allows for a single VCL-plugin to be compiled in (the qt5 one), so when using it here, the test_gtk* should be explicitly set here as well.」
- Gerrit 上 11-08 之後碰 `configure.ac` 的 change 共 7 個，沒有一個是修這件事的。
- tdf#146153 已在 11-12 關成 FIXED。Bugzilla 上提到這個錯誤訊息的只有我們自己的 tdf#174440（重現步驟裡順帶寫了）。

**為什麼排第一**：

- 成因確定，維護者自己給了修法方向，審查成本最低。
- 影響面是「文件記載的 WASM 建置在 master 上完全不能用」。
- 驗證只要跑 configure（幾分鐘、不編譯）。
- 有時效：原作者或 Lohmaier 隨時可能自己修。

**修法方向**：在 `emscripten)` 區塊明確關掉不可能在 Emscripten 上建的 plugin 測試，至少 `test_gtk3=no`、`test_gtk4=no`。要不要連 kf5、kf6、cups、dbus、cpdb、gstreamer 一起還原成回歸前的值，由下面第 3 條判準決定。

**驗收判準**（先釘死；全部只跑 configure）：

1. 未修的 master：configure 以上面那句錯誤結束（先紅一次）。
2. 修好後：印出 `VCLplugs to be built: qt5`，configure 完成。
3. 修好後的 `config_host.mk` 與回歸前（`wasm-lite/upstream-master/build-nosym/config_host.mk`，`2a2335cf`）逐行比對，差異只剩可解釋的（新增的 `USING_UNIX_DESKTOP`、版本與路徑）。
4. 加 `--disable-gui` 的組態修前修後都能 configure。

**還缺的**：finding 檔（這件事 11-11 發現時沒開，建議開成 186）；上面四條；commit message。

**要不要開 issue**：

- **A（建議）**：只送 MR。commit message 寫明是 `d98a796946ff` 的回歸，推上去之後在 211916 那串留言回一句附上連結。回歸剛合併、維護者已在 Gerrit 上點名，這是上游處理這類事的常態。
- **B**：先開一張 Bugzilla 再送。多一個單號，但對這種幾行的建置修正沒有實質好處。

**如果永遠沒做**：上游自己會修，我們沒有損失，只是少一次低成本的往來。

## 第二優先：finding 159（issue＋MR）

**現象**（依 finding）：WASM 上 Calc 的 add-in 函數一律 `#VALUE!`，核心函數正常。探針檔 20 格裡 add-in 的 5 格全錯（SERIESSUM、MULTINOMIAL、COUPDAYS、ACCRINT、YEARFRAC）。

**成因**（依 finding，函式層級）：add-in 經 `XIdlMethod::invoke` 走 `gcc3_wasm` bridge，bridge 的呼叫簽章表在建置時由 `wasmbridgegen` 產生，輸入只有 udkapi 與 offapi；add-in 的介面在 scaddins 自己的 IDL 裡，簽章不在表內，bridge 丟 RuntimeException，Calc 吞掉後顯示 `#VALUE!`。

**今天在 stock master 建置上的靜態確認**（已觀察，`wasm-lite/upstream-master/build-nosym`，`--with-distro=LibreOfficeWASM32 --disable-symbols`，無本地修改）：

- `generated-cxx.cxx` 共 53 個簽章；`didddi`、`diiii`、`diiiii`、`diiiiii` 逐字比對各 0 個（正向對照：`dii` 是 1 個）。
- 三個 add-in 函式庫都有建（`libanalysislo`、`libdatelo`、`libpricinglo`），`scaddins_AnalysisAddIn` 在 `services_constructors.list` 與 `component_maps.cxx` 裡。
- master 的 `bridges/CustomTarget_gcc3_wasm.mk` 仍只餵 udkapi＋offapi；我們的 patch 仍可直接套上，反向套用失敗。

這是成因的輸入在 stock 建置上成立，**不是**症狀在 stock 建置上重現。

**修法**：`wasm-lite/patches/libreoffice-26.8-wasm-bridge-scaddins-signatures.patch`（一個 `.mk` 檔，＋10／−2）。離線跑產生器是 55 → 80 個簽章；我們的檢視引擎 v2 是在全新的樹上帶著它建的，0.2.32 起出貨，受影響的兩份語料與桌面版相同（依 handoff）。

**為什麼排在 issue 的第一位**：

- 使用者直接看得到的錯誤結果，而且是一整類常用函數。
- 與 Qt5／Qt6／headless 哪條路線無關，TDF 的路線一定會中。
- 修法小、已在產品上跑了近一個月。
- Bugzilla 沒有重複單：`wasmbridgegen`、`wasm add-in VALUE`、`wasm YEARFRAC`、留言全文「Wasm bridge cannot call virtual function」都是 0 筆（已觀察）。

**還缺的**：

1. 在 stock 建置上執行期重現。`build-nosym` 的 `qt_soffice.html` 能跑，不必重建：開一份 Calc、填 `=MULTINOMIAL(2;3)`、讀回結果（用頁面裡的 Embind UNO 或畫面皆可）。
2. 在同一棵樹套 patch、刪掉三個產物、重連結 `soffice`，再讀一次。這步是會編譯的 make，耗時未量。
3. Bugzilla 草稿與 commit message。

## 其餘候選

| 順位 | # | 內容 | 手上有的 | 卡在哪 |
| --- | --- | --- | --- | --- |
| 3 | [003](findings/003-unpackedtarball-dir-race.md) | gbuild 的 `.version` 目標少一個 order-only 相依，全新建置目錄 `-j` 下偶發失敗 | 狀態「可送出」；Bugzilla 草稿與 commit message 都寫好；一行修法；master 該段今天仍相同（已觀察） | 不是 WASM 專屬（但我們只在 WASM 的全新目錄撞到）；草稿是 08 月寫的，有硬斷行與表格，要照現行規則重排；11-11 的 master 建置沒撞到 |
| 4 | [114](findings/114-wasm-lays-out-cjk-lines-with-latin-metrics-where-native-with-the-same-fonts-does-not.md) | LO 把 `35-lang-normalize.conf` 打包進會生效的 conf.d，CJK 行高變成拉丁行高 | 草稿、codex 審過、原生完整重現、普查工具 | 解釋起來複雜，審查的人要懂 fontconfig 的語言比對；stock WASM 映像沒有 CJK 字型，在上游建置上重現要另外想辦法 |
| 5 | 無編號 | fs image 的 registry 寫死 en-US，`--with-lang` 的 WASM 建置拿不到語言包 | 三行 patch，我們的建置從 7 月用到現在 | 沒有 finding 檔也沒有證據；stock 重現要一次 `--with-lang` 的全量建置 |
| 6 | [006](findings/006-qt6-wasm-stale-eventlistener-export.md) | Qt 6.10 起最終連結失敗（匯出清單列著已移除的符號） | 兩行 patch；在 TDF 宣告的 Qt6 路線上 | 要一棵接近上游的 Qt6＋JSPI 建置；要決定是否保留舊 Qt6 相容 |
| 7 | [057](findings/057-one-build-switch-two-halves-that-answer-to-different-inputs.md) | `--with-wasm-module` 改得動物件、改不動 a11y 巨集 | patch | 會改變上游預設組態的行為，說明與審查成本高 |
| 8 | [004](findings/004-emscripten-install-partial-symbols.md) | 部分符號建置不產生 `.dwp`，封裝失敗 | patch | 修補後沒重驗過；小眾 |
| — | [040](findings/040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md) | 非主執行緒的 `IdlesLockGuard` 永不返回 | 草稿 | 會踩到的是從別的執行緒呼叫 LOK 的用法（Collabora 的 WASM），TDF 的 Qt 路線不會；先決定送誰 |
| — | [089](findings/089-a-13kb-spreadsheet-with-a-full-height-repeated-row-times-out-on-wasm-but-opens-in-269ms-natively.md) | 13 KB 試算表在 WASM 上逾時 | 開關找到了（64 KB pthread 堆疊） | 溢位的函式沒指認，「是否上游」未確認 |
| 不送 TDF | 005、007、008 的 qtbase 那半 | 根因在 Qt | — | 見 11-10 盤點 |

十份 `libreoffice-26.8-*.patch` 今天全部仍可套上 `ac53621f`，反向套用全部失敗（已觀察）。這只表示那些程式碼上游沒動過。

## 一個背景觀察

Bugzilla 上標題含「wasm」的單至今只有 3 張（169649、172679、174440），含「emscripten」的 0 張（已觀察）。上游的 WASM 工作幾乎都直接發生在 Gerrit。所以 WASM 這條線以 MR 為主、issue 為輔比較合乎對方的習慣；issue 留給使用者看得到的缺陷（159、114 這種）。

## 建議的順序

1. configure 回歸：開 finding 186 → 在 master 上跑四條判準 → commit → 擁有者推上 Gerrit、在 211916 回一句。
2. 159：在 `build-nosym` 上執行期重現 → 草稿 → 重連結驗證修法 → 擁有者開單、推 Gerrit。
3. 003：重排草稿、重查重複單後送。

1 與 2 互不相依，可以同時進行；不要併成一個 change。

## 2026-11-18 補：第一優先已執行

擁有者同意先做 configure 回歸。結果登錄在 [finding 186](findings/186-master-wasm-configure-fails-gtk3-qt5.md)，證據在 `findings/evidence/186/`。

- 四條判準都跑了，全部只跑 configure（每臂約 30 秒）。判準 1、2、4 成立。
- **判準 3 改變了修法。**上面〈修法方向〉寫的「至少 `test_gtk3=no`、`test_gtk4=no`」（下稱 M）讓 configure 過，但與回歸前的組態相比，`USING_UNIX_DESKTOP`、`ENABLE_OPENGL_TRANSITIONS`、`ENABLE_OPENGL_CANVAS` 都是 `TRUE`，`HAVE_FEATURE_OPENGL` 是 1。`d98a796946ff` 把十幾處建置條件從 `USING_X11` 換成 `USING_UNIX_DESKTOP`，M 會把其中只靠這個變數把關的部分在 WASM 建置裡打開。
- 改用 R：在 Emscripten 上清掉 `USING_UNIX_DESKTOP`。`config_host.mk` 與 52 個設定標頭和回歸前相同，只多一個空的 `USING_UNIX_DESKTOP`；`--disable-gui` 的組態修前修後完全相同。
- **判準 3 的原文有洞**：「新增的 `USING_UNIX_DESKTOP`」被列為可解釋的差異，沒有限定值，照字面會放行 M。更正寫在 finding 186。
- R 已 commit 在 `wasm-lite/upstream-master/submit` 的分支 `emscripten-configure-gtk`（現為 `b7f3bd7eb41c`），沒有推。codex 做過一輪對抗性審查：組態相同、不影響其他平台都成立；commit message 兩句說過頭，已改（細節在 finding 186〈審查〉）。上面〈修法方向〉一節以本節為準。
- ~~**沒有建置**，commit message 照實寫了。~~（同日稍後已建置，見下一節。）

## 2026-11-18 補：兩種修法都全量建置了

擁有者問「為什麼和 Lohmaier 的方向不同、建置會不會比較清楚」，並指示先建只關 gtk 的那一個。結果（細節在 finding 186〈全量建置〉）：

- 兩種修法都建得起來、都跑得到開始中心、都能開 Writer 打字。**只關 gtk 的修法不是壞的。**
- 差別在它順帶把 Unix 桌面的設定放進 WASM 版：設定資料庫多 686 行，包含約一百個快速鍵。實測按 F11，只關 gtk 的那一版會打開「樣式」側邊欄，我們的修法與回歸前的建置都沒有反應。
- commit message 已改寫（`b7f3bd7eb41c`，內容與建置過的 `4847e69dd326` 相同）：寫明兩種都建過、另一種也能用、差別是什麼。
- 白話說明：`EXPLAINER-2026-11-18-finding-186-wasm-configure.md`。

## 2026-11-18 補：第二優先（159）的執行期重現已做

結果登錄在 [finding 159](findings/159-functions-recalculated-at-load-give-value-errors-on-the-viewer-core.md)〈2026-11-18〉，證據在 `findings/evidence/159/stock-runtime/`。

- 在 `build-186-R`（stock master＋186 的 configure 修正）上重現了，三次執行全部照事先 commit 的預測。
- **上面〈結論〉第 2 條與〈第二優先〉的「一律 `#VALUE!`」是錯的。**簽章剛好在表內的 add-in 能算：113 個 add-in 函數裡 57 個受影響。EOMONTH 不受影響；NETWORKDAYS 打原名是核心函數。YEARFRAC、XIRR 受影響。
- bridge 的例外訊息原文從 JS 直接呼叫讀到了（`Wasm bridge cannot call virtual function with signature didd` 等）。
- 〈還缺的〉三條都完成：第 1 條如上；第 2 條同日在 `build-186-R` 增量重建（擁有者授權代跑，317 秒），三次執行修法全對；第 3 條 Bugzilla 草稿 `findings/drafts/159-bugzilla.txt` 只差 Gerrit 連結，commit 在 `submit` 的分支 `emscripten-bridge-scaddins`（`ab916909bf26`，未推）。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-11-18 | 初版。 |
| 2026-11-18 | 補〈第一優先已執行〉：修法由「關掉 gtk 測試」改為「清掉 `USING_UNIX_DESKTOP`」，判準 3 的容許條件更正。 |
| 2026-11-18 | 補〈兩種修法都全量建置了〉。 |
| 2026-11-18 | 第一優先已送出：Gerrit [214345](https://gerrit.libreoffice.org/c/core/+/214345)。 |
| 2026-11-19 | 214345 照上游維護者的偏好改成 Patch Set 2（只關 gtk／kf plugin 測試），見 finding 186。 |
| 2026-11-18 | 補〈第二優先（159）的執行期重現已做〉：「一律 `#VALUE!`」更正為 113 個裡 57 個。 |

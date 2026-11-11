# 可回報上游的 finding：WASM 與 Qt 範圍盤點

> 2026-11-10。範圍：`findings/` 185 份裡，屬於 LibreOffice 的 WASM／Emscripten 建置與執行期、以及 Qt5／Qt6 WASM（含 qtbase）的那些。
> 作法照 `upstream-findings` skill：讀每份的表頭與「還缺什麼才能送」，再對照上游現況。
> 上游送出自 2026-08-15 起擱置，這份只是盤點，沒有送出任何東西，也沒有改動任何 finding 檔。
> 證據標記：**已觀察**＝今天直接查到；**依 finding**＝照 finding 檔自己的記載，今天沒有重驗。

## 結論

1. **範圍內值得送的有 12 則，其中 4 則已經寫好 Bugzilla 草稿**（001、040、114、008），差的是送出前的例行三件事：在乾淨的現行 master 重現、重查重複單、確認元件。008 的「是否上游」還是未確認，是四則裡最弱的。
2. **另外 6 則成因確定、多數有現成 patch，但還沒有草稿，或還沒在接近上游的組態重現過**（002、057、006、159、004、多語系 registry）。
3. **2 則的根因在別的專案**（007 屬於 Qt；005 屬於已停止維護的 Qt5），要先決定送哪裡。008 另有一半修補在 qtbase，等於要拆成兩份報告。
4. **十份本地 patch 今天全部還能直接套上上游**（master `016fd5d04925`，2026-10-11；26.8 分支 `d2b3fd7f169b`，2026-10-10）。這表示那些程式碼上游沒動過，不等於缺陷在 master 上重現過。**已觀察**
5. **所有證據都停在 26.8 的 `671c848b`**，沒有一則在現行 master 上跑過。這是每一則共同的缺口。

## 今天對上游現況做的查核（已觀察）

本機 `~/LibreOffice/lo-submit`，沒有動它的工作目錄與索引（用暫存索引 `git read-tree` 後 `git apply --cached --check`）。

| 查核 | 結果 |
| --- | --- |
| 十份 `libreoffice-26.8-*.patch` 套 `origin/master` | 10／10 可套用 |
| 同上，套 `origin/libreoffice-26-8` | 10／10 可套用 |
| 反向對照：三份 patch 反向套用 | 3／3 失敗（上游確實沒有這些修改，檢查不是空的） |
| 040：`m_inExecuteCondtion` 的 `set()` | 仍只有 `vcl/source/app/svapp.cxx:365` 一處，`wait()` 在 `scheduler.cxx:297` |
| 114：`35-lang-normalize.conf` | 仍在 `external/fontconfig/ExternalPackage_fontconfig_data.mk:34` 的打包清單裡 |
| 002：README 與 pre-js | `static/README.wasm.md:24` 仍叫人跑 `qt_vcldemo.html`；fs image 的 pre-js 只加在 `soffice_bin` |
| 089：pthread 堆疊 | `EMSCRIPTEN_INTEL_GCC.mk:25` 是 `-sDEFAULT_PTHREAD_STACK_SIZE=65536`，正是 089 找到的開關值 |

## 2026-11-10 補：四則在 26.8.2、26.8.3 與 master 上的複查

擁有者要求確認 001、002、040、114 在新版上是否仍存在。比對點：發現時的 `671c848b`（2026-07-30）、26.8.2.2 `9dea406a`（10-22）、26.8.3.1 `861effc5`（11-09，目前最新的 26.8 標籤）、master `2a2335cf`（11-10）。作法是比對成因所在的檔案，**沒有重新建置或執行任何 WASM**；114 另外重跑了 finding 自己的普查工具。

| # | 26.8.2.2 | 26.8.3.1 | master | 判讀 |
| --- | --- | --- | --- | --- |
| 001 | 相關檔案全同 | 全同 | 連結規則全同；寫入執行緒多一段重寫迴圈 | 成因的輸入沒變；崩潰沒重現過 |
| 002 | 全同 | 全同 | 只多列一個 `.ui` | **仍存在**（成因是建置規則加文件，靜態可判） |
| 040 | 全同 | 全同 | 只拿掉一個沒用的參數、改名 | **成因仍在**；死結沒重跑 |
| 114 | fontconfig 升到 2.18.3 | 同左 | 同左，檔案搬家 | **仍存在**：普查仍是 66 個被改寫、`zh-tw`→`tw` |

- **001**：決定最終連結的四個 gbuild 檔在三個 ref 上都與發現時逐位元組相同，configure.ac 沒有碰到符號或 Emscripten 的改動，README 仍建議 emsdk 4.0.10。master 的 `configmgr/source/components.cxx`（Armin Le Grand 一個 SmartArt commit 順帶改的）在寫完檔後若又有新變更就再寫一次，`try`／`catch` 沒動。因為 001 的機制本來就是推論，「仍存在」只能靠重建一次確認。**已觀察**（程式碼）／**未驗證**（崩潰）
- **002**：三個 ref 上 README 都還叫人跑 `qt_vcldemo.html`，`vcl/Executable_vcldemo.mk` 都沒有 fs image 的 pre-js，只有 `soffice_bin` 有。**已觀察**
- **040**：`scheduler.cxx` 的等待沒變；`set()` 仍只在 `Application::Execute` 的退路迴圈裡；master 的 Emscripten `DoExecute()` 在 `emscripten_set_main_loop_arg(…, 1)` 之後是 `O3TL_UNREACHABLE`，回不到那個迴圈。**已觀察**（程式碼）／**未驗證**（死結）
- **114**：LO 仍把 `35-lang-normalize.conf` 打包進 conf.d、仍以字串加 `FC_LANG`。26.8.2 起自帶的 fontconfig 升到 2.18.3（`80b5857b`，08-18）：
  - 2.18.3 的 35 保留全部 258 條舊規則、新增 57 條，做子字串比對的 `src/fccfg.c` 完全相同。
  - 用 finding 的 `census.py`、同一個 2.18.2 函式庫，只把規則檔換成 2.18.3 的重跑：正向對照與已 commit 的 `census-abs.txt` 逐行相同；換規則後仍是 66 個被改寫，只有 `wae` 的改寫目標變了。**已觀察**
  - 沒用 2.18.3 的函式庫跑，也沒普查 2.18.3 新增的 57 個語言碼。

收據：`findings/evidence/{001,002,040}/upstream-recheck-2026-11-10.txt`、`findings/evidence/114/recheck-2026-11-10/`。

## 2026-11-10 再補：實際建置的結果（取代上一節對 001、002 的判讀）

擁有者要求代建。五棵 WASM 建置，全部無本地修改或只套 7/31 的兩個 fs image patch，用 7/31 同一支 `probe.js` 與同一版 Chromium 151 測：

| 原始碼 | 組態 | 001 | 002 |
| --- | --- | --- | --- |
| master `2a2335cf` | stock＋`--disable-symbols` | 不崩 | **重現** |
| master `2a2335cf` | 7/31 lite 旗標（en-US、無 patch） | 不崩 | — |
| 26.8.2.2 `9dea406a` | 同上 | 不崩 | — |
| 26.8.2.2 `9dea406a` | 7/31 原樣（zh-TW＋patch） | 不崩 | — |
| `671c848b`（7/31 的 commit） | 7/31 原樣 | 不崩 | — |

- **001 撤銷**。7/31 那棵樹最早用 `--enable-lto` configure，重新 configure 後殘留了四個語系資料函式庫的 LTO bitcode，連結時印出 10,262 條 signature mismatch；今天每一棵都沒有。7/31 的 t3 是全新目錄，所以「只差符號」的對照被混淆了。見 finding 001 的〈撤銷〉與 `findings/evidence/001/july-crash-build-stale-lto.txt`。**已觀察**（log）／**推論**（因果）
- **002 在 master 上執行期重現**，與 7/31 逐項相同。證據：`findings/evidence/002/master-2a2335cf/`。
- **003 順帶又出現兩次**：26.8.2.2 的兩個全新建置目錄，第一次 `make` 都停在 `dragonbox.version`。見 `findings/evidence/003/make-error-26.8.2.2.txt`。

因此第一級只剩 040、114、008 三則；002 升為「成因與執行期都在 master 上確認」，只差草稿。

## 第一級：草稿已寫好

| # | 缺陷 | 送哪裡 | 手上有的 | 還缺的 |
| --- | --- | --- | --- | --- |
| [001](findings/001-wasm-configmgrwriter-crash.md) | `--disable-symbols` 的 WASM 建置一啟動就崩潰（configmgrWriter 執行緒逸出例外） | TDF Bugzilla | Bugzilla 草稿；三組建置對照把變因隔離到單一旗標；100% 重現 | 重查重複單、確認元件。機制（postlink 破壞例外處理）是推論，草稿已標明 |
| [040](findings/040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md) | 非主執行緒建構的 `Scheduler::IdlesLockGuard` 在 Emscripten 上永遠不返回 | TDF Bugzilla（見下方註） | Bugzilla 草稿；具名堆疊兩個入口；012、037、038 都是它的症狀 | 在上游自己的 WASM 組態重現；重查重複單 |
| [114](findings/114-wasm-lays-out-cjk-lines-with-latin-metrics-where-native-with-the-same-fonts-does-not.md) | LO 把 `35-lang-normalize.conf` 裝進會生效的 conf.d，CJK 行用拉丁行高，每行約 0.79 倍 | TDF Bugzilla | Bugzilla 草稿；codex 審過一輪；原生加同一份 conf.d 完整重現；附件用專案自產的檔 | 在上游發佈的 WASM build 或 CODA-W 上重現；重查重複單（10-08 查過一次） |
| [008](findings/008-qt6-wasm-inputcontext-invalid-emval-value.md) | Qt6 WASM 的 input context 跨 pthread 用了失效的 DOM handle，開 Writer 就退出 | TDF Bugzilla（`vcl/qt5/QtFrame.cxx`） | Bugzilla 草稿；LO 端 patch；修補前 5／5、修補後 0／1 | 乾淨 master 上修補前後各至少 3 次；只套最小修補重驗 |

註：

- **001 在上游預設組態不重現**，要加 `--disable-symbols` 才會中。草稿要把「翻一個旗標就能重現」寫在最前面。
- **040 的入口都是從別的執行緒呼叫 LOK**。TDF 的 Qt WASM 路線不這樣用 LOK，會這樣用的是 Collabora 的 WASM。缺陷在 `vcl` 的排程器，兩邊都有這段程式碼，但誰會踩到要想清楚再決定送哪裡。
- **008 目前只在我們自訂的 Qt 6.10.2＋JSPI 組態重現**，表頭的「是否上游」還是未確認。

## 第二級：成因確定、patch 現成，還沒準備好送

| # | 缺陷 | patch | 還缺的 |
| --- | --- | --- | --- |
| [002](findings/002-vcldemo-missing-fs-image.md) | `qt_vcldemo.html` 沒連結 fs image，README 卻叫人跑它 | 無（修法是文件或連結規則二選一） | 草稿檔還沒寫；重查重複單。已在 stock 組態覆驗，是這一級裡最接近可送的 |
| [057](findings/057-one-build-switch-two-halves-that-answer-to-different-inputs.md) | `--with-wasm-module` 改得動物件、改不動 `ENABLE_WASM_STRIP_ACCESSIBILITY` 巨集 | `wasm-strip-accessibility-single-input` | 草稿；patch 會改變上游預設組態的行為，說明要寫清楚 |
| [006](findings/006-qt6-wasm-stale-eventlistener-export.md) | Qt 6.10 已移除 `qstdweb::EventListener`，LO 的匯出清單還列著它，最終連結失敗 | `emscripten-jspi-stale-eventlistener-export` | 用接近上游的 Qt6-WASM 組態重現；決定要不要保留舊 Qt6 的相容；草稿 |
| [159](findings/159-functions-recalculated-at-load-give-value-errors-on-the-viewer-core.md) | `wasmbridgegen` 只吃 udkapi＋offapi，Calc 的 add-in 函數在 WASM 上一律 `#VALUE!` | `wasm-bridge-scaddins-signatures` | 在上游 build 上重現；草稿 |
| [004](findings/004-emscripten-install-partial-symbols.md) | 部分符號建置不產生 `soffice.wasm.debug.wasm.dwp`，封裝失敗 | `emscripten-emdwp-partial-symbols` | 修補後還沒重新連結驗證過；stock 組態重現 |
| 無編號 | fs image 的 registry 寫死 en-US，`--with-lang` 的多語系建置拿不到語言包 | `emscripten-fs-image-multilang-registry` | **沒有 finding 檔也沒有證據**，要先補登錄 |

006 值得特別留意：它是決定性的連結錯誤、修法兩行，而且正好在 TDF 宣告的 Qt6＋WASM 路線上。上游 master 的匯出清單今天還列著那個符號。

## 第三級：根因在別的專案

| # | 缺陷 | 屬於誰 | 狀態 |
| --- | --- | --- | --- |
| [007](findings/007-qt6-wasm-pointerenter-null-dom-node.md) | Qt 6.10 WASM／JSPI 延遲的 pointer-enter 事件拿到 null DOM 節點，整個應用程式退出 | Qt（qtbase） | 有 qtbase patch，本地驗證過；缺 stock Qt 範例的最小重現。finding 自己寫明要送 Qt Bug Tracker，不送 LibreOffice |
| 008 的另一半 | qtbase 的 input context 修補 | Qt（qtbase） | 有 `qtbase-6.10.2-wasm-inputcontext-ecmastring.patch` |
| [005](findings/005-qt5-wasm-no-input-context.md) | Qt5 WASM 沒有 input context，CJK 完全無法輸入 | Qt5（已不公開維護） | 標為可送出，但還沒在 stock 組態覆驗。TDF 既然轉向 Qt6，它的價值是佐證「樹內預設的 Qt5 WASM 對 CJK 不可用」 |

這三則都是在 Qt 6.10.2 上量的。TDF 的人 6 月在清單上用的是 6.11.1，送之前要先看新版還在不在。

## 還不能送

| # | 內容 | 為什麼還不行 |
| --- | --- | --- |
| [009](findings/009-qt6-wasm-duplicate-english-key-input.md) | Qt6-WASM Writer 英文按鍵重複輸入 | 只觀察到一次，沒有事件時序 |
| [089](findings/089-a-13kb-spreadsheet-with-a-full-height-repeated-row-times-out-on-wasm-but-opens-in-269ms-natively.md) | 13 KB 的試算表在 WASM 上逾時，原生 269 ms | 開關找到了（64 KB 的 pthread 堆疊），而上游的預設值正是 64 KB；但溢位的函式沒指認，也沒在上游 build 上重現。**值得優先補做** |
| [158](findings/158-an-ods-with-form-controls-cannot-be-painted-on-the-wasm-core-forms-service-absent.md) | Emscripten 上 DB connectivity 被無條件關掉，含表單控制項的 ODS 畫不出來 | 比較像組態限制而不是缺陷；沒在上游 build 重現；三份 patch 改的是模組選擇 |
| [032](findings/032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md)、036 | 同源同旗標重編，目的檔不相同 | 屬於 Emscripten／LLVM，沒有定位到哪個階段 |
| 草稿「LOK status update under emscripten loop」 | unipoll＋Emscripten 系統事件迴圈下 LOK 狀態更新落後 | 來源 finding 021 已判為不是上游；草稿自己寫著送出條件一項都沒完成 |
| 024 | Firefox 的 pthread worker 回收 | 上游已在 Nightly 155 修掉，沒有東西要送 |

## 不在這次範圍

與 WASM／Qt 無關、但同樣是上游缺陷的，這份沒有列入：

- LibreOffice 核心與 LOK：003（gbuild 的 race，有 patch 與 commit message，是全部裡面最容易送的一則）、020、043、074、146–149、156、166、167、169、184、185。
- Nextcloud：100–104、163。

## 重啟送出時的順序建議

照 skill 的排序原則（證據強度 × 影響 ÷ 審查成本），不要一次全送：

1. **002**：成因確定、已在 master 的 stock 建置上執行期重現，只要補一份草稿。
2. **114**：影響大、隔離乾淨、草稿現成。（001 已撤銷，2026-11-10）
3. **006、057、159**：成因確定但小眾，patch 現成。
4. **040**：先決定送 TDF 還是 Collabora。
5. **007、008**：先在新版 Qt 上確認還在，再分別送 Qt 與 TDF。

每一則送之前都要先做同一件事：在乾淨的現行 master 上重現一次。需要 WASM 建置的那幾則是擁有者的 `make`。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-11-10 | 初版。 |
| 2026-11-10 | 補〈四則在 26.8.2、26.8.3 與 master 上的複查〉。本機 `lo-submit` 的遠端追蹤分支更新到 master `2a2335cf`，並抓了 26.8.2.2、26.8.3.1 標籤；上方「今天對上游現況做的查核」一節的 master 仍指 `016fd5d0`（10-11）。 |
| 2026-11-10 | 補〈實際建置的結果〉：001 撤銷（從原始碼重建 0／5 重現，7/31 樹殘留 LTO bitcode）、002 在 master 執行期重現、003 又出現兩次；送出順序拿掉 001。原本第一級表格裡 001 那一列保留不刪，以新節為準。 |

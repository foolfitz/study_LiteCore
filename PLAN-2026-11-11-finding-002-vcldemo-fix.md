# finding 002：把 vcldemo 修好、正式跑一次的規劃

2026-11-11。給擁有者看的。對應 `findings/002-vcldemo-missing-fs-image.md`、草稿 `findings/drafts/002-bugzilla.txt`、白話說明 `EXPLAINER-2026-11-11-finding-002-vcldemo.md`。

證據標記：**已觀察**＝這次直接讀原始碼或量；**推論**＝要實驗才能確認。行號都是 master `e42678e7`（2026-11-11 fetch）。

## 1. 先回答：`qt_vcldemo.html` 是不是「只是個 demo」

是，它是**給開發者用的測試程式**，不是使用者會碰到的功能。但名字裡的 `qt_` 跟這件事無關。

- **`qt_` 是建置規則自動加的前綴**（已觀察）：WASM＋Qt5 建置時，`solenv/gbuild/platform/unxgcc.mk:184-195` 會給**每一個** Executable 和 CppunitTest 套 Qt 的 `wasm_shell.html`，產生 `qt_<名字>.html`。LibreOffice 本體的 `qt_soffice.html` 也是這樣來的，所以這個前綴不代表任何性質。
- **`vcldemo` 才是程式名，它確實是測試程式**（已觀察）：
  - `--help` 第一行就是 `vcldemo - a VCL test app`（`vcl/workben/vcldemo.cxx:2099`）；
  - 原始碼放在 `vcl/workben/`，workbench 就是開發者的工作台；
  - `Repository.mk:26` 把它登錄在 `NONE`，意思是不安裝。所以任何 LibreOffice 安裝包裡都沒有它。
- **它做什麼**：開一個視窗，把 14 種繪圖測試排成格子畫出來（`vcldemo.cxx:1589-1605`）。這 14 種是線、文字、多邊形、橢圓、棋盤格、兩種點陣圖、漸層、多重多邊形、裁切、畫到虛擬裝置、XOR、圖示、取回點陣圖。點一格會放大。另外有 `--test`（跑效能數據）、`--widgets`、`--popup`、`--threads`、`--font` 幾個模式。
- **它的價值**：不必開整個 office，就能單獨驗「VCL 繪圖層＋Qt＋WASM」這一段有沒有問題，是移植時除錯用的最小程式。上游 `vcl/Module_vcl.mk:39-41` 也特地在 WASM＋Qt5 時建它。
- **跟我們的產品**：沒有直接關係。我們的產品走 LOK、不用 Qt，修它純粹是回饋上游。

## 2. 規劃前查到的三件事

1. **11-10 那棵 master 建置樹已經刪了**（已觀察）。當時磁碟 99% 滿，你要求刪除，紀錄在 `findings/evidence/001/rebuild-2026-11-10/README.txt`。要正式跑就得重建一棵：11-10 實測 48.5 分鐘。現在磁碟剩 207 GB，Qt5 工具鏈（`wasm-lite/tools/qt5-wasm`）、emsdk 和探針 `wasm-lite/tools/pw/probe.js` 都還在，探針的 sha 跟 11-10 一樣。
2. **vcldemo 缺的可能不只是資料檔的載入器**：
   - 已觀察：2024-08-12 的上游 commit `6e6451ce96f4`（「Move the Qt event loop off the JS main thread」）做了兩件事：
     - 把 soffice 改成 `-sPROXY_TO_PTHREAD`，讓 Qt 事件迴圈離開瀏覽器主執行緒；
     - 把全域的 `-sPTHREAD_POOL_SIZE=7`（預先開好 7 個 worker）改成只在關掉 proxy 時才加（`EMSCRIPTEN_INTEL_GCC.mk:20-22`）。
   - 已觀察：這發生在把載入器收窄的 `cf0b0f0dd04f`（2024-04）之後，所以 vcldemo 這兩樣都沒拿到。它的 Qt 還在主執行緒上，而且沒有預先開好的 worker。
   - 已觀察：`static/README.wasm.md` 自己寫了，在主執行緒模式下要開執行緒，得靠夠大的 `PTHREAD_POOL_SIZE`。
   - **推論**：補上資料檔之後，vcldemo 可能會卡在開執行緒，畫面還是出不來。
   - 草稿的修法 (a) 只說「抄 prejs 那段」。草稿沒有宣稱 (a) 會讓它跑起來，所以沒有寫錯；但真的要修好，得準備第二步。
3. **上游現況**（已觀察）：今天的 master `e42678e7` 比 11-10 的 `2a2335cf` 只多一個 commit（`d98a796946ff`，`--without-x`），沒動到相關檔案。Gerrit 上沒有 open 的 vcldemo change，Bugzilla 查重複是 11-11 做的。

## 3. 修法（照順序試）

**F1**＝草稿的 (a)：在 `vcl/Executable_vcldemo.mk` 加上 soffice 那段 EMSCRIPTEN 區塊（`desktop/Executable_soffice_bin.mk:31-37`）。

**F2**＝F1 不夠時，再加上 soffice 那組 proxy 連結旗標（`desktop/Executable_soffice_bin.mk:67-70`）。soffice 專屬的東西不抄：`EXPORTED_FUNCTIONS`、`unoembind`、`uno.js`、`script.js`。

```make
ifeq ($(OS),EMSCRIPTEN)
# F1
$(call gb_LinkTarget_get_target,$(call gb_Executable_get_linktarget,vcldemo)) : \
    $(gb_CustomTarget_workdir)/static/emscripten_fs_image/soffice.data.js.link
$(eval $(call gb_Executable_add_prejs,vcldemo,$(SRCDIR)/static/emscripten/environment.js))
$(eval $(call gb_Executable_add_prejs,vcldemo,\
    $(gb_CustomTarget_workdir)/static/emscripten_fs_image/soffice.data.js.link))
# F2
$(eval $(call gb_Executable_add_ldflags,vcldemo,\
    $(if $(ENABLE_EMSCRIPTEN_PROXY_TO_PTHREAD), \
        -sPROXY_TO_PTHREAD=1 \
        -sOFFSCREENCANVAS_SUPPORT=1 -sOFFSCREENCANVASES_TO_PTHREAD=\#qtcanvas) \
))
endif
```

F2 的前提已經查過（已觀察）：Qt5 的 `wasm_shell.html:33` 的畫布 id 是 `qtcanvas`，allotropia 的 `qtloader.js:424` 有處理 PROXY_TO_PTHREAD。

送上游時要照抄一段，還是抽成 soffice 和 vcldemo 共用的 gbuild 巨集，等跑起來再決定。先求能跑，再談形狀。

## 4. 步驟

| # | 做什麼 | 誰 | 時間 | 吃 CPU |
|---|---|---|---|---|
| 0 | 準備（見下） | 我 | 約 10 分 | 否 |
| 1 | 全量建置**未修版** master | **你** | 40–50 分（11-10 實測 48.5） | 是，10 核 |
| 2 | 對照組：同一棵樹跑 `qt_soffice.html` 與 `qt_vcldemo.html` | 我 | 約 5 分 | 輕 |
| 3 | 不重編的預演：F1 夠不夠 | 我 | 約 10 分 | 輕 |
| 4 | 套 F1（或 F1＋F2），只重連結 vcldemo | **你** | 估幾分鐘（沒量過） | 是 |
| 5 | 正式跑：我用探針跑，你用自己的瀏覽器看 | 我＋你 | 約 10 分 | 輕 |
| 6 | 收尾：證據、finding、草稿、白話說明 | 我 | 約 30 分 | 否 |

**0. 準備**（我做，不編譯）
- 重建 worktree `wasm-lite/upstream-master/src`，用 `origin/master`、完整 checkout。11-10 第一次用稀疏 checkout，找不到 `autogen.sh` 失敗過。
- 從 `findings/evidence/001/rebuild-2026-11-10/` 把 `build.sh`、`run_probe.sh` 複製回去。`autogen.input` 跟 11-10 的 `build-nosym` 相同：README 建議的 stock 組態加 `--disable-symbols`。用全新的建置目錄和 ccache，不碰任何舊樹（finding 001 就是被舊目的檔害的）。
- F1、F2 先寫成兩個 patch 檔放著，不進第 1 步的建置。
- 判準（第 5 節）和預測先 commit，再跑能推翻它的東西。

**1. 全量建置**（你）：準備好後我給你一行指令，跑完回報 exit code。不要跟 0.2.61 手測或任何計時量測同時跑。

**2. 對照組**（我）：
- `qt_vcldemo.html` 應重現 `Cannot open uno ini`，這是紅案，也確認今天的 master 仍有這個問題；
- `qt_soffice.html` 應走到開始中心，證明建置和伺服本身沒問題。

**3. 預演**（我，不重編）：
- 做法：把 `vcldemo.js` 複製到 scratchpad，在 `var Module = …` 那行後面貼上 `environment.js` 與 `soffice.data.js.link` 的內容，然後伺服、探測。Emscripten 的 `--pre-js` 本來就貼在這個位置（emsdk `src/shell.js:130-132`）。
- 結果：F1 夠的話，第 4 步只連 F1；不夠的話，第 4 步直接連 F1＋F2，省你一輪。
- **預演不是證據**。手工改出來的檔案只是對「等於連結結果」的宣稱，正式結論只看第 4 步真的連出來的東西。

**4. 重連結**（你）：
- 我把 patch 套進 worktree，做成本地 commit。
- 你跑 `make Executable_vcldemo.clean && make Executable_vcldemo`。要先 `.clean`，因為 gbuild 不追蹤 `.mk` 的變化：新加的 prejs 檔比既有的輸出舊，不清掉不會重連。
- F1 連出來不夠才連 F2，最多兩輪。

**5. 正式跑**：
- 我：用 11-10 同一支探針跑 `qt_vcldemo.html`。
- 你：我開好 emrun，給你網址，你用自己的瀏覽器開，點幾格看會不會放大。你是唯一不共用我判讀工具的觀測者。

**6. 收尾**（我）：
- 證據放 `findings/evidence/002/fix-<commit>/`。
- 更新 finding 002；草稿的修法 (a) 改成「測過」，寫清楚需要 F1 還是 F1＋F2，附上 patch。
- 白話說明補一段。
- patch 以本地 commit 留在 worktree 的分支上。**送出仍擱置**，要不要送 Gerrit 等解除擱置時再決定。

## 5. 判準（第 1 步之前先寫死）

**修好**＝下面全部成立：

1. **網路**：`qt_vcldemo.html` 請求了 `soffice.data.js.metadata` 與 `soffice.data`。
2. **主控台**：沒有 `Bootstrap exception`，而且至少有一行寬高都大於 0 的 `DemoWin::Paint(…)`。vcldemo 每次重畫都會印這行（`vcldemo.cxx:1758`），這是「真的畫了」的機器訊號，不用靠看圖判斷。
3. **截圖**：不是白畫面。11-10 的白畫面是 4,254 bytes 的 PNG，可以拿來當紅案比。
4. **對照**：同一棵樹、同一支探針，未修版的 `qt_vcldemo.html` 是紅的，`qt_soffice.html` 是綠的。
5. **人看**：你在自己的瀏覽器看到格子裡有圖，點一格會放大。

**如果一直沒做到**：finding 002 照現在的草稿送，不宣稱修法有效。草稿本來就成立。

## 6. 風險與停損

- **F2 之後可能還有第三關**（推論）：例如 Qt5 在 worker 上的游標或輸入事件。`6e6451ce96f4` 依賴的 allotropia qtbase 補丁自己留了 TODO。
  - **停損**：F2 仍不行就停，把卡在哪裡寫進 finding，修法 (a) 改寫成「需要 F1＋F2，還卡在 X」，不繼續往下挖，除非你要。
- **建置不可重現**：不影響這次。A／B 在同一棵樹，只差 vcldemo 的連結。
- **不碰產品**：這次不碰 ddev、宿主和出貨 profile，也不佔你的 Nextcloud 環境。
- **磁碟**：建置樹加 ccache 約 8–10 GB（估），現在剩 207 GB。

## 7. 要你決定

- **A（推薦）**：照第 4 節全部做：全量建置 → 對照 → 預演 → 重連結 → 正式跑。
- **B**：跳過預演，直接 F1＋F2 一起重連結。少一輪，但不知道 F2 是不是必要；送上游時 reviewer 很可能會問 proxy 旗標是不是必要的。
- **C**：只做到 F1，確認它拿得到資料檔為止，也就是驗證草稿 (a) 那一步，不追畫面。

預設用今天的 master（`e42678e7`）建，因為 Gerrit 的 patch 要以最新 master 為底。

**實際（2026-11-11 12:00 更正）**：擁有者選 A，並要我代跑建置。改用 `2a2335cf` 建，原因是 `e42678e7` 的 configure 直接失敗：

- 錯誤訊息：`VCLplugs to be built: gtk3 qt5` → `Can't build --disable-dynamic-loading without --disable-gui and a single VCL plugin`。
- 已觀察：同一份 `autogen.input` 在 11-10 的 `2a2335cf` 上 configure 只選了 qt5，沒有出錯。
- 推論（只讀了原始碼）：兩者之間唯一的 commit `d98a796946ff` 把 emscripten 標成 Unix 桌面，WASM 建置因此不再自動關掉 gtk3。這是上游今天剛出現的回歸，可能值得另開一張 finding。
- 這次修的檔案在兩個 commit 之間完全相同，兩個 patch 在兩邊都能乾淨套用。

預測與判準在 `findings/evidence/002/fix-2a2335cf/PREDICTIONS.txt`。

## 8. 結果（2026-11-11 13:15）

觸發了停損條件，F1 和 F1＋F2 都沒有畫出東西。

| 臂 | 要了 `soffice.data` | `Cannot open uno ini` | 建出視窗 | `DemoWin::Paint` | 畫面 |
|---|---|---|---|---|---|
| C0 未修版 vcldemo | 否 | 有（0.6 秒） | — | 0 | 白 |
| C1 未修版 soffice | 是 | — | 開始中心 | — | 開始中心 |
| R1 預演（不是證據） | 是 | 沒有 | 是 | 0 | 深灰 |
| F1 | 是 | 沒有 | 是 | 0 | 深灰 |
| F1＋F2 | 是 | 沒有 | 是（main 在 worker 上） | 0 | 深灰 |

- 判準 1、4 過；2、3 沒過；5（你本人看）還沒做。
- 預演和 F1 的結果逐行相同，所以預演方法本身是準的。
- 詳細數字在 `findings/evidence/002/fix-2a2335cf/README.txt`。草稿的修法 (a) 已經改寫成這個實測結果，finding 002 也補了一段。

## 9. 繼續追之後（2026-11-11 15:15，擁有者選 A）

**修好了。** vcldemo 不畫有第二個原因，而且不在連結，在 vcldemo.cxx 本身：

- 在 WASM 上，`Application::Execute()` 最後會呼叫 `QApplication::exec()`，它會丟出 JavaScript 例外拆掉整個堆疊；
- vcldemo 把主視窗放在堆疊上，所以視窗剛顯示就被銷毀了；
- soffice 為了同一個原因，故意洩漏它的 `Desktop` 物件。vcldemo 照做（F3）之後就正常了。

| 臂 | 結果 |
|---|---|
| F1＋F2＋F3 | 畫出格子，點擊放大，Escape 回格子 |
| F1＋F3（拿掉 F2） | 同上，視窗還更早出現（0.9 秒對 2.3 秒） |
| **最終：F1＋F3，不含任何探針** | 正式探針：判準 1–4 全過；點擊與按鍵正常 |

- **F2 不需要**。第 2 節「多半會卡在開執行緒」的推論是錯的。
- 最終 patch：`findings/evidence/002/fix-2a2335cf/fix-final.patch`，`.mk` +8 行、`.cxx` +17 行。
- 判準 5 等你看：伺服器開在 http://127.0.0.1:6970/qt_vcldemo.html 。
- 沒驗的：`--widgets`、`--popup`、`--font`、`--threads` 幾個模式。

## 修訂紀錄

- 2026-11-11：初版。
- 2026-11-11 12:05：擁有者選 A、要我代跑建置；`e42678e7` 的 configure 失敗，改用 `2a2335cf`（第 7 節）。
- 2026-11-11 13:15：第 8 節結果；停損。
- 2026-11-11 15:15：擁有者選 A 繼續追；第 9 節，修好了（F1＋F3）。

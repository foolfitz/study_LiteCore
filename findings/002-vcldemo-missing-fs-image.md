# 002 — qt_vcldemo.html 沒有連結 fs image，README.wasm.md 卻要人跑它

| | |
|---|---|
| **狀態** | 可送出（根因完全確定，不依賴精簡組態） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-07-31 |
| **嚴重度** | 一般（影響的是官方文件指定的測試路徑） |
| **可重現** | 100% |
| **是否上游** | **是** —— 缺的是連結期的 pre-js，與 configure 旗標無關 |

## 現象

`static/README.wasm.md` 明文要人跑這個當測試：

> You should be able to run either
>
>     $ emrun --hostname 127.0.0.1 --serve_after_close workdir/installation/LibreOffice/emscripten/qt_soffice.html
>     $ emrun --hostname 127.0.0.1 --serve_after_close workdir/LinkTarget/Executable/qt_vcldemo.html

但第二個必定失敗：白畫面，主控台是 `Bootstrap exception Cannot open uno ini file:///instdir/program/unorc`。

## 重現步驟

1. 依 `README.wasm.md` 建置 WASM 版本
2. `emrun --hostname 127.0.0.1 --port 6932 workdir/LinkTarget/Executable/qt_vcldemo.html`
3. 開新分頁載入

**預期**：vcldemo 的繪圖測試畫面
**實際**：白畫面，UNO bootstrap 失敗

## 證據

- `evidence/002/console.txt` — 完整主控台紀錄
- `evidence/002/loader-missing.txt` — 兩個 .js 的比對
- `evidence/002/screenshot-blank.png`

網路請求時序證明 **`soffice.data` 從頭到尾沒有被請求過**：

```
[0.0s] 200      3229B  qt_vcldemo.html
[0.0s] 200      3047B  qtlogo.svg
[0.0s] 200     22298B  qtloader.js
[0.1s] 200    281830B  vcldemo.js
[0.1s] 200 123498234B  vcldemo.wasm
                            ← 沒有 soffice.data，也沒有 soffice.data.js.metadata
[1.0s] LOG  Bootstrap exception Cannot open uno ini file:///instdir/program/unorc
```

直接比對兩個 .js：

```
$ grep -c 'soffice\.data\|loadPackage' vcldemo.js      →  0
$ grep -c 'soffice\.data\|loadPackage' soffice.js      → 11
```

## 分析

`file_packager` 產生的載入器（`soffice.data.js`）是在連結期以 pre-js 的形式併進去的。`soffice.js` 有（`loadPackage`、`REMOTE_PACKAGE_BASE` 都在），**`vcldemo.js` 完全沒有**。

所以 vcldemo 執行時虛擬檔案系統是空的，`/instdir/program/unorc` 不存在，UNO bootstrap 第一步就失敗。

值得注意的是 `solenv/gbuild/platform/unxgcc.mk:191-193` 會把 `soffice.data` 和 `soffice.data.js.metadata` **複製**到每個可執行檔旁邊 —— 檔案確實在 `workdir/LinkTarget/Executable/` 底下躺著，只是沒有任何程式碼去載入它們。複製了卻沒連結載入器，看起來是漏了一半。

修法有兩個方向，**由上游決定哪個才對**：

1. 讓 `vcldemo` 這類 Executable 也連結 `soffice.data.js.link` 這個 pre-js
2. 如果 vcldemo 本來就不該依賴 fs image，那就從 `README.wasm.md` 拿掉那一行，並停止複製 `soffice.data` 過去

### 可能的起點（2026-11-11 補充）

**推論**（只讀了歷史，沒有建置更舊的樹）：`cf0b0f0dd04f`（Stephan Bergmann，2024-04-30，「Emscripten: Only add the --pre-js code to the soffice executable」，最早進 24.8）之前，`solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk` 會把 `gb_EMSCRIPTEN_PRE_JS_FILES`（`environment.js`、`soffice.data.js.link`）加到**每一個** Executable 與 CppunitTest，所以 vcldemo 當時應該有載入器。那個 commit 為了讓 node 底下執行的 `uri-encode.js` 不再因 `XMLHttpRequest is not defined` 失敗，把 pre-js 收到只有 `soffice_bin`。它的 commit message 自己寫了 unxgcc.mk 的 `cp` 還留著、「can probably be cleaned up further in a next step」。README 的那一行更早（`12a6b57c74aa`，2022-01），之後一直沒動。

**已觀察**（master `2a2335cf`）：`vcl/Module_vcl.mk:40-41` 在 EMSCRIPTEN＋Qt5 時**特地**建 `Executable_vcldemo`；`unxgcc.mk:184-195` 對 EMSCRIPTEN 的每個 Executable／CppunitTest 產生 `qt_<名稱>.html` 並複製 `soffice.data`。

### 修法實測（2026-11-11）

證據：`evidence/002/fix-2a2335cf/README.txt`；判準與預測在第一次探測前已 commit（`293468b1b`）。

**已觀察**：在 master `2a2335cf` 上全新建置一棵樹，只重連結 vcldemo，結果如下。
- **F1**（草稿的修法 (a)，補上兩個 pre-js）：
  - vcldemo 會去要 `soffice.data`，`Cannot open uno ini` 消失，並且建出視窗；
  - 但 90 秒內一行 `DemoWin::Paint` 都沒有，畫面空白，也沒有任何錯誤。
- **F1＋F2**（再加上 soffice 的 `-sPROXY_TO_PTHREAD` 等旗標）：main 改到 worker 上跑，但結果相同。
- **對照**（同一棵樹）：未修版重現 `Cannot open uno ini`，`qt_soffice.html` 正常走到開始中心。

**結論**：
- F1 是必要的：它修掉了這張單回報的錯誤。
- F1 不足以讓 vcldemo 能用，加上 F2 也不夠。
- 為什麼建出視窗後不畫，**還不知道**。照規劃的停損條件，停在這裡。
- 我原本預測「F1 不畫，是因為沒有執行緒池」。前半句應驗了，理由卻不成立：拿掉那個條件的 F1＋F2 一樣不畫。

## 環境

同 001（見 `./env-snapshot.sh`）。

**已在三種組態上覆驗**（lite / stock / t3），`vcldemo.js` 一律沒有載入器。與 configure 旗標無關。

## 還缺什麼才能送

- [x] 在 `build-stock/` 與 `build-t3/` 上覆驗 → 兩者 `vcldemo.js` 的 `soffice.data`/`loadPackage` 出現次數皆為 **0**，`soffice.js` 為 13。確認與組態無關
- [x] 搜尋 Bugzilla 是否已有重複 → 2026-11-11 用 REST API 查，沒有重複。提到 vcldemo 的 10 張都是原生的（146478、169688 等），`qt_vcldemo`／`soffice.data`／`emscripten_fs_image` 全部 0 筆。收據：`evidence/002/dup-search-2026-11-11.txt`。**送出前要重查**
- [x] 確認 Component → TDF Bugzilla **沒有「Build tooling」這個 component**（2026-11-11 查欄位值）。改填 `LibreOffice`：README.wasm.md 的錯字單 tdf#169649 也歸在那裡
- [x] Bugzilla 草稿 → `drafts/002-bugzilla.txt`（2026-11-11）。送出仍擱置

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | LibreOffice（2026-11-11 修正：原本寫的 Build tooling 不存在） |
| Version | 27.2.0.0 alpha0+ master（2026-11-11 修正：選單裡沒有 26.8.0.1 rc；乾淨的執行期重現是在 master 上做的） |
| Hardware / OS | All / All（2026-11-11 修正：OS 選單沒有 WASM 這個值，而問題跟建置主機無關） |
| Summary | 以 `drafts/002-bugzilla.txt` 為準（2026-11-11） |

## 時間軸

- 2026-07-31 為了切開 001 的問題層次而跑 vcldemo，發現它以完全不同的原因失敗
- 2026-11-10 靜態複查：26.8.2.2（`9dea406a`）、26.8.3.1（`861effc5`）、master（`2a2335cf`）上，README 仍叫人跑 `qt_vcldemo.html`，`vcl/Executable_vcldemo.mk` 仍沒有 fs image 的 pre-js（只有 `soffice_bin` 有）。成因原樣存在。收據：`evidence/002/upstream-recheck-2026-11-10.txt`
- 2026-11-10 執行期在 master `2a2335cf` 上重現（stock 組態、無本地修改）：`qt_vcldemo.html` 從頭到尾沒請求 `soffice.data`，0.6 秒出現 `Bootstrap exception Cannot open uno ini file:///instdir/program/unorc`，白畫面；`vcldemo.js` 的 `soffice.data`／`loadPackage` 計數仍是 0。與 7/31 逐項相同。證據：`evidence/002/master-2a2335cf/`
- 2026-11-11 用 Bugzilla REST 查重複，沒有找到；查欄位值時發現 Component「Build tooling」不存在，改成 `LibreOffice`。讀歷史找到可能的起點 `cf0b0f0dd04f`（推論，沒有實際建置）。寫好 `drafts/002-bugzilla.txt`，送出仍擱置
- 2026-11-11 下午 擁有者要求真的修一次並代跑建置。`e42678e7` 的 configure 失敗（gtk3＋qt5，推論是 `d98a796946ff` 造成的，另案），改用 `2a2335cf`，建置 52 分 51 秒。F1 過了 bootstrap、建出視窗，但不畫；F1＋F2 也一樣。草稿的修法 (a) 改寫成實測結果。證據：`evidence/002/fix-2a2335cf/`

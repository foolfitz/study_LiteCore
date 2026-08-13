# 開發筆記 2026-07-31 — LibreOffice WASM

給下一個 session 快速進入狀況用。**先讀「一分鐘版」和「已定案的判斷」兩節就能接手。**

---

## 一分鐘版

目標是把 LibreOffice 編成跑在瀏覽器裡的精簡繁中 Writer。

今天做到：**編出來了、跑起來了、找到五個上游問題、並且發現原本的技術路線有一個致命缺口。**

三個必須知道的結論：

1. **`--disable-symbols` 在 WASM 上會讓程式啟動即死**（例外處理被破壞）。已用五個 build 隔離到單一變因。目前唯一可用的組合是 `--enable-symbols=Executable_soffice_bin`。
2. **Qt5 的 WASM 版本完全不能用輸入法**，中文一個字都打不進去。這是 Qt 5.15 wasm plugin 缺 input context 造成的，**Qt5 路線修不了**。
3. 因此 **Qt6 從「風險太高不值得賭」變成「唯一可能的選項」**，儘管 LO 的 Qt6-WASM 路徑已經 18 個月沒人維護。

目前有一份**能跑的建置**：`wasm-lite/build-t3/instdir/program/`。

---

## 專案脈絡

- 使用者是繁中母語，目標是「像 markdown editor 一樣精簡」的瀏覽器版 Writer
- 原始要求：noto 字型、LTO、英文+繁中、只要 Writer、用 LO 自己的 UI（不做前後端分離）
- **時間壓力已解除** —— 使用者說趕時間只是想快點看到成果，不是要結案，願意投入

---

## 檔案地圖

```
study_LiteCore/
├── DEVLOG-2026-07-31-wasm.md      ← 本檔
├── litecore-analysis.md           Collabora vs 上游 core 的比較研究（較早期）
├── QA-GUIDE.md                    怎麼參與上游 QA（welded widgets A/B 測試為主軸）
├── Skills/                        可重複使用的工作方法（symlink 到 .claude/skills/）
│   ├── README.md                  為何這樣擺 + 什麼該寫成 skill
│   ├── upstream-findings/         記錄與回報上游問題的紀律
│   ├── build-variable-bisect/     昂貴建置下的變因隔離方法論
│   └── emscripten-app-debug/      瀏覽器內 WASM app 的除錯手法
├── .claude/skills/                三個全是指向 Skills/ 的 symlink
├── findings/                      上游問題紀錄（見下）
│   ├── README.md                  索引 + 工作流程
│   ├── TEMPLATE.md
│   ├── env-snapshot.sh            產生可貼進 Bugzilla 的環境區塊
│   ├── 001..005-*.md
│   ├── drafts/                    已寫好的 Bugzilla 內容與 commit message
│   └── evidence/{001..003}/       主控台紀錄、截圖、makefile 片段
├── wasm-lite/
│   ├── README.md                  建置規劃。⚠️ 檔頭有警告：§3.5/§3.6/§5.4 已被實測推翻
│   ├── build-wasm-lite.sh         自動化腳本
│   ├── tools/emsdk/               emsdk 4.0.10
│   ├── tools/qt5-wasm/            編好的 Qt5（勿刪，重編要一小時）
│   ├── tools/extra-fonts/         NotoSansCJK-Regular.ttc
│   ├── tools/pw/probe.js          Playwright 探針（抓主控台/網路/截圖）
│   └── build*/                    五個 build 目錄
├── libreoffice-26-8/              ← 主要工作分支（worktree）
├── libreoffice-26-2/  libreoffice-25-2/  collabora-25.04/
```

worktree 共用同一個 git object store。

---

## 建置矩陣（今天的實驗結果）

| 目錄                 | 組態                                                                              | wasm   | 結果                         |
| ------------------ | ------------------------------------------------------------------------------- | ------ | -------------------------- |
| `build/`           | lite：32 旗標 + 2 個本地 patch，含 `--disable-symbols`                                  | 125 MB | ❌ 啟動即崩                     |
| ~~`build-stock/`~~ | `--with-distro=LibreOfficeWASM32 --enable-symbols`                              | 211 MB | ✅ 正常（**已刪除**，角色由 t1/t2 涵蓋） |
| `build-t1/`        | stock + `--with-wasm-module=writer`                                             | 183 MB | ✅                          |
| `build-t2/`        | t1 + `--enable-release-build`                                                   | 183 MB | ✅                          |
| `build-t3/`        | **lite 全套，只把 `--disable-symbols` 換成 `--enable-symbols=Executable_soffice_bin`** | 183 MB | ✅ **目前唯一能用的精簡建置**          |

磁碟：`build*` 合計約 40 GB，`/` 剩 141 GB。

> `build-stock/` 已於 2026-07-31 刪除（省 16 GB）。它的角色是「上游預設組態的已知正常參考點」，
> 已由 t1/t2 涵蓋，結論也記在 findings/001。真要重建就是再跑一次 stock configure。

**注意**：`build-t3/` 的 `workdir/installation/` 是**不完整的** —— 打包步驟在複製 `.dwp` 時失敗
（見 [findings/004](../findings/004-emscripten-install-partial-symbols.md)），`soffice.wasm` 之後的檔案沒複製到。
**要跑 t3 請用 `build-t3/instdir/program/`。**

**t3 是決定性的一輪**：跟崩潰的 lite 只差符號設定，且符號只開給一個 target，其餘 `.o` 逐位元組相同（ccache 全命中）。

---

## 已定案的判斷

### ✅ 分支用 26-8，不用 26-2

26.8 RC1 是 2026-07-13，正式版八月底。原生 Qt 對話框覆蓋率 26-2=221 / **26-8=463** / master=582，另外 26-8 多了 7 筆純 WASM build fix。已建 worktree。

### ✅ `--enable-noto-font` 不存在於上游

是 Collabora 專屬旗標。上游用 `--with-fonts`（預設開）無條件安裝 14 套 Noto。

### ✅ 上游沒有任何 CJK 字型

`external/more_fonts/` 一套中日韓都沒有，WASM 也抓不到系統字型。必須自己塞（腳本的 `fonts` + `patch` 步驟處理）。

### ✅ `soffice.data` 的語言清單寫死 en-US

`static/CustomTarget_emscripten_fs_image.mk` 有 3 處硬編碼。不改的話 `--with-lang=zh-TW` 會編出來、裝進 instdir，但**不會進 soffice.data**。腳本的 `patch` 步驟改用 `gb_Configuration_LANGS`。

### ⚠️ 我列的 20 幾個 `--disable-*` 幾乎全是白工

比對 `config_host.mk` 後發現它們在 Emscripten 上**本來就是預設關閉**（`--enable-wasm-strip` 自動處理）。真正有效果的只有 `--with-wasm-module`、`--enable-release-build`、`--disable-symbols`、語言相關那幾個。

（`wasm-lite/README.md` §3.6 的正文仍是舊說法，但已加上「已過時」警告框。）

### ⚠️ 體積的真正槓桿是字型，不是程式碼

`soffice.data` 分類統計：

```
69.8 MB  71.7%  字型（130 個檔）   ← 這裡
14.3 MB  14.7%  .ui 對話框（766 個）
 6.3 MB   6.5%  其他
 3.8 MB   3.9%  圖示等 config
 3.2 MB   3.2%  registry 設定
```

其中 `LinLibertine + LinBiolinum` 佔 19.3 MB、阿拉伯文/希伯來文字型約 4 MB，對 en+zh-TW 完全無用。

**機制已經現成**：`--without-fonts`（`configure.ac:14618`）會讓 `fs_image.mk:1776` 的整個 `ooo_fonts` 區塊跳過，而我們 patch 進去的 `LITE_EXTRA_FONTS_DIR` 區塊獨立運作不受影響。粗估 70 MB → 12 MB。**這是還沒做的最大優化。**

### ❌ LTO 從來沒有真的跑過

`LITE_LTO=0`（因為當時 swap 不足）。而 emscripten#13665 指出 wasm 例外處理在 LTO 下會失效 —— 若 001 的機制假設成立，LTO 很可能是同一類地雷。**使用者原本要求的 `--enable-lto` 目前仍是未驗證狀態。**

### 🔄 Qt5 → Qt6：路線需要重新評估

原本的判斷（README §5.4）是「Qt6 缺文件與驗證，不值得賭」，前提是兩條路線功能等價。

**發現 005 之後這個前提不成立了**：Qt5 完全無法輸入中文。對繁中編輯器來說這是硬性阻斷，其他優化都沒意義。

Qt6 那條路的現況（今天查證過）：

- Emscripten+Qt6 的專屬管線最後一次更新是 **2025-02-11**，至今無新 commit
- Qt6 的**預設模式是壞的**（`--enable-emscripten-proxy-to-pthread` 預設 yes，但 Qt6 需要「excessive and unrealistic」的 hack）
- 唯一可行模式：`--enable-qt6 --enable-emscripten-jspi --disable-emscripten-proxy-to-pthread`，作者自陳「known to occasionally hang and crash」
- **必須自己編 Qt 6.10+ 帶 `-feature-wasm-jspi`**，官方預編 binary 沒有
- `README.wasm.md` 完全沒寫 Qt6 怎麼建
- `unxgcc.mk:190` 用 `sed -z` 改 Qt 的 `wasm_shell.html`，依賴 `@APPNAME@` / `@APPEXPORTNAME@` / `@PRELOAD@`（Qt 6.6 才有），Qt 一改樣板會**靜默失效**
- 唯一利多：JSPI 從 **Chrome 137 / Firefox 139** 起已預設開啟（2025-04 W3C 標準化），當年的阻塞理由消失了

**這是下一個要做的決策，使用者說先擱置。**

---

## 上游脈絡（影響方向判斷）

- TDF 2026-05-27 的[新網頁與行動策略](https://blog.documentfoundation.org/blog/2026/05/27/new-web-and-mobile-strategy-for-libreoffice/)把「polishing our functional prototype based on **Qt 6 and WebAssembly**」列為 2026 年目標
- 背景是 TDF 決定重啟 LibreOffice Online，Collabora 反對，TDF 會員委員會投票移除所有 Collabora 員工與夥伴的會員資格
- allotropia（Qt5-WASM 與 ZetaOffice 的推手）2025-05 併入 Collabora
- `tdf#130857`（原生 Qt 對話框）1460 個 commit、最近 12 個月 784 個，幾乎全是 Michael Weghorn —— 他正是策略文件點名的成員。這條線是策略本體
- Weghorn 2026-03 有一筆 commit 修「WASM 上 Insert→Hyperlink 會 crash」，代表**有人真的在跑 WASM**
- Xisco Fauli（TDF 員工）2026 年多次修 WASM build，有 tinderbox 在顧 —— 但**只驗「編得過」，不驗「跑得起來」**

---

## findings（五張，全部可送出或近乎可送）

| #   | 標題                                                        | 狀態           | 嚴重度 |
| --- | --------------------------------------------------------- | ------------ | --- |
| 001 | WASM `--disable-symbols` 破壞 C++ 例外處理，啟動即崩潰                | 可送出          | 阻斷  |
| 002 | `qt_vcldemo.html` 沒連結 fs image，README 卻要人跑它               | 可送出          | 一般  |
| 003 | `UnpackedTarball.mk` 的 `.version` 缺 `.dir` 相依，`-j` 下 race | 可送出（附 patch） | 一般  |
| 004 | `emscripten-install` 用全域 `ENABLE_SYMBOLS_FOR` 判斷，部分符號建置失敗 | 可送出          | 一般  |
| 005 | Qt5 WASM 無 input context，CJK 輸入完全不可行                      | **暫緩**       | 嚴重  |

**建議送出順序**：003（練流程，一行修法）→ 001（影響最大）→ 002 → 004 → 005 暫緩。

`drafts/` 已有 **003 的 Bugzilla 內容 + gerrit commit message**、**001 的 Bugzilla 內容**。

005 暫緩的理由：根因在 Qt5 wasm plugin 不在 LO，報到 TDF 可能被打回；且可能是已知限制；且我們的實測只有「fcitx 打中文沒反應」，太粗。等 Qt6 評估完再決定定位。

每張都還缺同樣兩件：**搜 Bugzilla 確認沒重複**、**確認 Component**。

---

## 怎麼恢復現場

```bash
cd ~/LibreOffice/study_LiteCore/wasm-lite
source tools/emsdk/emsdk_env.sh          # 系統另有 apt 裝的 emscripten 3.1.69，別用到

# 跑目前唯一能用的建置
emrun --no_browser --hostname 127.0.0.1 --port 6937 \
      build-t3/instdir/program/qt_soffice.html

# 抓主控台/網路/截圖（15-20 秒就夠，崩潰在 1.0 秒發生）
cd tools/pw && node probe.js http://127.0.0.1:6937/qt_soffice.html 20 /tmp/shot.png

# 環境快照（送 bug 用）
cd ../../../findings && BUILDDIR=../wasm-lite/build-t3 ./env-snapshot.sh
```

今天開著的伺服器：6935(t1) 6936(t2) 6937(t3)。清掉：`pkill -f 'emrun\.py'`

---

## 踩過的坑，別再重踩

| 坑                                         | 說明                                                                                                                                                                 |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **系統有兩份 emscripten**                      | apt 裝的在 `/usr/share/emscripten`（3.1.69）。裸打 `emrun`/`emcc` 會抓到它。一定要先 `source tools/emsdk/emsdk_env.sh`                                                              |
| **`autogen.lastrun` 不能用 `$(cat ...)` 展開** | `--with-lang=en-US zh-TW` 行內有空白，shell 會拆成兩個 argv，`zh-TW` 被當成 build system type。**改用 `autogen.input`**（autogen.sh 不帶參數時自動讀，見 `autogen.sh:232`）                      |
| **全新 build 目錄會中 003 的 race**              | 開始前先 `mkdir -p <builddir>/workdir{,_for_build}/UnpackedTarball`                                                                                                    |
| **探針不要跑太久**                               | 崩潰在 1.0 秒發生，20 秒足夠。我一度設 90-150 秒，讓使用者等了十分鐘                                                                                                                         |
| **`Module.FS` 在 Qt5 build 沒匯出**           | `EMSCRIPTEN_INTEL_GCC.mk:30` 用 `$(if $(ENABLE_QT6),...)` 才加 `FS`/`callMain`/`specialHTMLTargets`。碰它會直接 abort 整個 module。要從 JS 塞檔案得先改那行（只需 relink）                   |
| **免重編就能做的實驗**                             | ① 改 `soffice.data.js.metadata` 的 `files` 陣列可讓某些檔案不進 VFS（blob 不用動）② 等長置換可直接改 blob 內的文字檔（如 `bootstraprc`）③ 複製 `qt_soffice.html` 加一行 `Module.arguments = [...]` 測啟動參數 |

---

## 待辦（依價值排序）

1. **決定 Qt5/Qt6 路線** ← 阻塞其他一切。若要繁中就得走 Qt6
2. 送出 003、001（drafts 已備好）
3. 字型精簡（`--without-fonts` + `LITE_EXTRA_FONTS_DIR`），70 MB → 12 MB
4. 改寫 `wasm-lite/README.md` 的 §3.5 / §3.6 / §5.4
   （**已加上「已過時」警告，不會誤導**，但正文還沒重寫。
   §5.4 怎麼寫取決於 Qt5/Qt6 決策，所以卡在第 1 項後面）
5. 驗證 LTO 是否可用（現在有 64 GB swap 了）
6. 檔案開啟方案（改 `FS` 匯出 or 把文件烤進 image）
7. QA：`SAL_VCL_QT_USE_WELDED_WIDGETS` 的 A/B 測試（見 `QA-GUIDE.md`），繁中對話框是無人區

---

## 環境

```
LibreOffice   26.8.0.1.0+   libreoffice-26-8 @ 671c848b1bb8 (2026-07-30)
Emscripten    4.0.10（tools/emsdk）
Qt            allotropia/qt5 5.15.2+wasm @ 3d440b7787f9 (2025-05-23)
OS            Ubuntu 26.04 LTS / kernel 7.0.0-28-generic / x86_64 / KDE
硬體          12 核 / RAM 31 GB / Swap 64 GB（今天加的）/ 剩餘磁碟 125 GB
瀏覽器         Chrome 150.0.7871.128、Firefox 152.0.6、Playwright Chromium 151.0.7922.34
MCP           playwright 已註冊（本專案 local scope）
```

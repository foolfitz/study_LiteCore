# COWASM co-26.04 參考研究筆記

> **日期**：2026-08-01
> **研究狀態**：唯讀參考研究；本筆記不改變任何既有原始碼樹
> **研究對象**：`cool-26-04/` — CollaboraOnline `online.mirror` 的 `distro/collabora/co-26.04` 分支
> **檢視 commit**：`c64a7343a5c6`（2026-07-31）
> **取得方式**：在既有 `/home/jiajun/LibreOffice/collabora_online` repo 加入 `mirror` remote
> （`https://github.com/CollaboraOnline/online.mirror.git`），fetch 該分支後以
> `git worktree add` 掛至 `study_LiteCore/cool-26-04`
> **相關研究**：[OxOffice WASM Document SDK](./RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)、
> [WASM 輕量協作編輯器](./RESEARCH-2026-08-01-wasm-collaboration-editor.md)

---

## 0. 文件定位

本筆記回答一個問題：**COWASM（Collabora Online as WASM）在 co-26.04 的實作，對
`wasm_sdk_probe` 與 Document SDK 研究線有哪些可直接取用的答案?**

引用政策與 OxOffice 相同：cool-26-04 是唯讀參考，只取架構與機制知識；不把 Collabora
的程式碼、品牌或 fork 決策搬進以 LibreOffice 26.8 為基線的實作。

沿用三種證據標記：**已觀察**/**推論**/**研究假設**。本筆記內容除特別標注者外均為
「已觀察」——直接來自 cool-26-04 與 libreoffice-26-8 的原始碼比對。

---

## 1. co-26.04 是 core+online monorepo

- 頂層是 COOL（`browser/`、`kit/`、`wsd/`、`net/`、`wasm/`），LibreOffice core
  （Collabora Office engine）整棵嵌在 `engine/` 子目錄，同一條 git 歷史。
- `wasm/README.no-container.md` 明載 POCO、zstd、libpng 已併入 core engine 一起建，
  舊的 poco emscripten patches 已自 `wasm/` 刪除。
- engine 的 WASM distro config 是 `engine/distro-configs/CPWASM-LOKit.conf`。

這代表 Collabora 的 WASM 參考實作與它配套的 core 版本鎖在同一棵樹，對照時不需再猜
「哪個 COOL 配哪個 core」。

## 2. 對 wasm_sdk_probe 最重要的機制：核外連結（out-of-tree link）

COWASM **不在 LibreOffice gbuild 內**建立自己的應用，而是核外連結。`wasm/Makefile.am`
的完整配方：

```text
core 建置產出(headless、--with-package-format=emscripten):
  instdir/program/soffice.js.linkdeps        ← 完整 -l 清單(link 時 tee 出)
  instdir/program/soffice.data(+ .js.metadata)← Emscripten fs image
  workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link ← pre-js
  workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports  ← export 清單
  static/emscripten/environment.js           ← pre-js 環境設定

COOL 端:
  自己的 main()(wasmapp.cpp)+ wsd/kit 原始碼
  LDADD   = POCO/zstd 靜態庫 + -L instdir/program + $(cat soffice.js.linkdeps)
  exports = core exports 檔 + 追加自己的 C 進入點(_handle_cool_message)
  LDFLAGS = --pre-js environment.js --pre-js soffice.data.js.link ...
```

**已觀察**：上述每一個 core 端配套在上游 LibreOffice 26.8 都存在——

- linkdeps 生成：`solenv/gbuild/platform/unxgcc.mk:162`（`DISABLE_DYNLOADING` 下
  link 命令把 `-l` 清單 `tee $@.linkdeps`）；Emscripten 平台把 `.linkdeps` 列入
  auxtargets（`solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk:92`）。
- `static/emscripten/environment.js`、`static/emscripten/uno.js` 上游都在。
- exports 檔：`desktop/util/Executable_soffice_bin-emscripten-exports` 已含
  `_libreofficekit_hook`、`_libreofficekit_hook_2`、`_lok_preinit`、`_lok_preinit_2`、
  `_malloc`、`_free`。
- fs image：`static/CustomTarget_emscripten_fs_image.mk` 同一機制。

**結論（推論）**：`wasm_sdk_probe` 可以完全不進 gbuild——建一次 headless 26.8，
然後用一個獨立的小 Emscripten 專案（自己的 `main()` + LOK C shim）連結 linkdeps。
這回答了 SDK 報告 §8.1 懸置的倉庫拓樸問題：探針階段不需要 submodule 或 gbuild 掛載。

## 3. 執行緒與 runtime 模型

`wasm/Makefile.am` 的連結旗標與 `wasmapp.cpp` 的行為：

- `-pthread`、`-fwasm-exceptions`；**沒有 JSPI、沒有 PROXY_TO_PTHREAD**。
- `-s MODULARIZE -s EXPORT_NAME=createOnlineModule`；COOL 的 `browser/src/main.js`
  在**瀏覽器主執行緒** instantiate 模組。
- `main()` 立即返回（`EXIT_RUNTIME=0`），COOLWSD 在 detached pthread 裡跑；
  LOK/文件運算全部發生在 pthreads（headless svp 不碰 DOM，所以可行）。
- `-s PTHREAD_POOL_SIZE_STRICT=0`（允許動態長出 pthread；因為 JS 主執行緒事件迴圈
  沒被佔住，隨時能 spawn worker——這正是 Qt6 線做不到的）。
- C++ → JS 用 `MAIN_THREAD_EM_ASM` 推送訊息（FakeWebSocket.onmessage）；
  JS → C++ 用 `ccall("handle_cool_message", ...)` 類介面。
- `-s TOTAL_MEMORY=1GB`、`FORCE_FILESYSTEM=1`、`FETCH=1`。

**對探針的含意（推論）**：R1 應複製這個組態（主執行緒 host 模組、運算在 pthreads、
無 JSPI），因為它是已在產品驗證過的路徑，而且與 Qt6 線的 JSPI/main-thread 修補完全
無關。「把模組整個放進 dedicated Worker」仍是 SDK 的目標隔離邊界，但可以留到 R2
runtime 階段再做——在 Worker 內 instantiate 同一個 MODULARIZE 模組，glue 介面不變。

## 4. 文件進出的實際作法

`wasmapp.cpp`（272 行）的 I/O 模式：

- 載入：`emscripten_fetch`（同步）抓文件 → `fwrite` 進 Emscripten FS（`/tempdoc`）
  → 以 `file:///tempdoc` URL 交給 documentLoad。
- 存檔：從 FS 讀回 buffer → `emscripten_fetch` POST 回伺服器。

**已觀察**：COWASM 沒有「ArrayBuffer 直通 LOK」的路徑，一律經過 MEMFS。這回答協作
報告研究問題 #3 的參考答案：探針第一版就走「JS 把 ArrayBuffer 寫入 FS → `file://` URL
→ documentLoad；saveAs 到 FS → JS 讀出 ArrayBuffer」，不必先發明記憶體直通 API。

## 5. embind UNO 在核外連結是可選的

- **已觀察**：26.8 core 自己的 `soffice_bin` 連結無條件 `--whole-archive` 掛入
  `unoembind`（`desktop/Executable_soffice_bin.mk:66`），configure 無開關。
- **已觀察**：但 COOL 的核外連結把它做成 `ENABLE_WASM_EMBIND_UNO` 條件項——
  `libunoembind.a` 與 `bindings_uno.js` 只在啟用時加入；另有 ZetaJS
  （`ENABLE_WASM_ZETAJS`）作為更上層的可選整合。

**修正 SDK 報告的一個推論**：「embind 無條件進產物」只適用於 core 內建的
`soffice_bin`；探針走核外連結時，embind 天然可省。`writer-reader` profile 的體積
量測應直接以「不含 embind 的核外連結產物」為基線，不需要先做 configure 開關 patch
（該 patch 仍可作為上游改善，但不再擋路）。

## 6. COKit：Collabora 已把 LOK 改名分岔

- **已觀察**：engine 的 `include/LibreOfficeKit/` 已不存在，取而代之是
  `include/COKit/`（`COKit.h` 603 行、`COKitEnums.h` 1341 行等，合計約 4300 行），
  API 仍是同一套 struct-of-function-pointers（documentLoad、paintTile、postKeyEvent、
  saveAs…），init 符號改為 `cokit_hook_2`/`cok_preinit_2`。
- COOL kit 端以 `COKit ABI` 稱呼這層（`kit/Kit.cpp:3189`），並有 `DummyCOKit`
  測試替身。

**含意（推論）**：LOK「unstable」不是紙上警語——最大的下游使用者已經把它整個改名
自管。這強化 SDK 報告兩個既有決策：（1） 我們的公開 ABI 必須是自己的窄 C ABI，
LOK 只是內部實作細節；（2） 基線鎖 26.8 的 `LibreOfficeKit` 命名與 headers，
不追 Collabora 的 COKit。同時注意：**COOL 的 wsd/kit 原始碼已綁 COKit 命名，
不能原樣拿來配上游 26.8 的 LOK**；可搬的是機制（§2–§4），不是程式碼。

## 7. CPWASM-LOKit.conf：已驗證的 headless 旗標集

Collabora 的 WASM distro config（節錄有資訊量者）：

```text
--host=wasm32-local-emscripten
--disable-gui
--disable-scripting          ← 無 Basic/腳本引擎;體積候選,探針可跟進
--enable-cairo-rgba          ← tile 像素格式 RGBA,直接餵 canvas;
                               上游 LOK paintTile 預設 BGRA,探針要選一邊
--without-help --without-templates --with-galleries=no
--disable-librelogo
```

**對探針的含意**：R1 的 autogen.input 以上游 README 的 headless 範例為底，
逐項比對此 conf 決定取捨。`--enable-cairo-rgba` 尤其重要——不開就要在 JS 端
swizzle BGRA→RGBA，或用 canvas 技巧；開了則與桌面 LOK 行為略有差異，QA 對照時要記錄。
`--disable-scripting` 對 reader/review profile 是明顯的體積與攻擊面收益，
但要先確認 Writer 功能路徑沒有隱性依賴（靜態 component 缺席問題，見 SDK 報告 §12）。

## 8. yrs：上游 26.8 已內建留言協作實驗

- **已觀察**：`README.yrs` 在上游 `libreoffice-26-8` 與 co-26.04 `engine/`
  **逐字相同**；26.8 configure.ac 已有 `--with-yrs` 與 `ENABLE_YRS`。
- 內容：以 yrs（Yjs 的 Rust CRDT，經 yffi C FFI）同步 **Writer 留言**的實驗功能。
  文件本體要求唯讀模式；留言的插入/刪除/內文編輯（含格式、超連結）可雙向同步，
  peer cursor 可顯示；明言超出留言範圍的並行編輯會 crash。通訊 transport 目前是
  hard-coded pipe（YRSACCEPT/YRSCONNECT 環境變數）。

**對協作研究線的含意（推論）**：

1. 上游自己也選擇「先協作留言、文件本體單一權威」——與本研究「sidecar 協作 +
   edit lease」的分層判斷一致，是路線的獨立佐證。
2. 差異在留言資料的位置：yrs 實驗把留言同步進文件模型（EditDoc 鏡射到 YDocument），
   本研究提案把留言放 sidecar 資料庫。兩者可長期收斂：若上游 yrs 路線成熟，
   sidecar 留言可考慮改走文件內 track，反之亦然。R6 設計時應保留這個轉換空間。
3. 探針與第一版 SDK **不應**啟用 `--with-yrs`（多一個 Rust toolchain 相依與
   實驗性 crash 面），但協作報告 §7.4 的「何時研究真 multi-writer」多了一個
   具體觀察對象：追蹤上游 yrs 實驗的演進即可，不必自己先養 CRDT。

## 9. 給 wasm_sdk_probe 的具體輪廓（綜合）

```text
前置:headless 26.8 build
  --disable-gui --with-wasm-module=writer --with-package-format=emscripten
  (+ 依 INVENTORY.md 套用兩線共用 patches;旗標細節參照 CPWASM-LOKit.conf 比對)

probe 專案(獨立目錄,不進 gbuild):
  probe_main.cpp   main() 立即返回;pthread 內 lok_preinit_2 / libreofficekit_hook_2
  probe_shim.c     窄 C API:probe_open / probe_paint_tile / probe_post_key /
                   probe_save,內部走 LOK function-pointer table
                   (此 shim 即未來版本化 C ABI 的種子)
  link:em++ + $(cat soffice.js.linkdeps) + exports(追加 _probe_*)
       --pre-js environment.js --pre-js soffice.data.js.link
       -pthread -sMODULARIZE -sEXPORT_NAME=createProbeModule -sEXIT_RUNTIME=0
       (無 JSPI、無 PROXY_TO_PTHREAD;embind 不連)

JS 端(先主執行緒 host,R2 再移入 Worker):
  ArrayBuffer → FS 寫檔 → probe_open("file:///doc.odt")
  → probe_paint_tile → canvas(RGBA/BGRA 依 configure 決定)
  → probe_post_key / ext text input(程式化插入中文字)
  → probe_save → FS 讀出 ArrayBuffer → 桌面 26.8 round-trip 驗證
```

R1 閘門措辭修訂（併入 SDK 報告）：「輸入一個中文字」指**以 LOK API 程式化插入**；
真 IME composition 屬 R2+ 的 JS UI 工程，不作為 R1 的 No-Go 判準。

## 10. 本機資料來源

- `cool-26-04/wasm/Makefile.am`、`wasm/wasmapp.cpp`、`wasm/emscripten-module.js.m4`
- `cool-26-04/wasm/README`、`wasm/README.no-container.md`
- `cool-26-04/browser/src/main.js`（模組 instantiate 位置）
- `cool-26-04/kit/Kit.cpp`、`kit/DummyCOKit.{cpp,hpp}`（COKit ABI 使用方式）
- `cool-26-04/engine/include/COKit/`、`engine/distro-configs/CPWASM-LOKit.conf`
- `cool-26-04/engine/README.yrs` ↔ `libreoffice-26-8/README.yrs`（diff 相同）
- `libreoffice-26-8/solenv/gbuild/platform/unxgcc.mk`（linkdeps 生成）
- `libreoffice-26-8/solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk`（auxtargets）
- `libreoffice-26-8/desktop/util/Executable_soffice_bin-emscripten-exports`
- `libreoffice-26-8/static/emscripten/environment.js`、`uno.js`
- [patch inventory](./wasm-lite/patches/INVENTORY.md)

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-01 | 初版。取得 co-26.04 worktree；確認 monorepo 結構、核外連結機制、執行緒模型、embind 可選性、COKit 分岔、CPWASM-LOKit 旗標、yrs 上游狀態；整理 wasm_sdk_probe 具體輪廓。 |

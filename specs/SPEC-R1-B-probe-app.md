# SPEC R1-B：wasm_sdk_probe 探針程式

> **日期**：2026-08-01/**狀態**：可執行 spec（v1）/**上層**：[SPEC-R1-000](./SPEC-R1-000-overview.md)
> **連結步驟依賴**：[SPEC-R1-A](./SPEC-R1-A-headless-build.md) 的交接物；原始碼可先寫

## 1. 目標

一個獨立的小 Emscripten 專案（不進 gbuild），直接對上游 LOK 完成
`open → paintTile → 插入中文字 → save`，並附網頁測試頁。
其中的窄 C API（`probe_api.h`）是未來 SDK 版本化 C ABI 的種子，命名與參數要當正式介面對待。

## 2. 專案結構

```text
wasm_sdk_probe/
  Makefile
  README.md            # 建置與執行方式(完成後補)
  src/
    probe_api.h        # 窄 C API 宣告 + 事件 JSON 格式註解(ABI 種子)
    probe_api.cpp      # 匯出函式:參數驗證、命令入佇列、事件送 JS
    probe_engine.cpp   # engine thread:命令迴圈、全部 LOK 呼叫、LOK callback 轉發
  web/
    index.html         # 測試頁
    probe.js           # 測試頁邏輯(非 SDK;僅驗證用)
    serve.py           # 帶 COOP/COEP header 的靜態伺服器
  dist/                # 連結產物(probe.js/probe.wasm/soffice.data*,gitignore 級)
  test-docs/           # R1-C 放測試文件
```

## 3. 執行緒與生命週期設計（必守）

1. `main()`：只記錄啟動、立即 `return 0`（`-sEXIT_RUNTIME=0` 保持 runtime 存活）。
2. **所有 LOK 呼叫都在單一 engine pthread** 上執行。exported 函式在瀏覽器主執行緒被
   `ccall` 呼叫，只做「把命令放進 queue」後立即返回，**絕不阻塞等待結果**
   （阻塞主執行緒會卡住 pthread 生成與事件迴圈，是已知死鎖模式）。
3. 結果與狀態一律以事件回 JS：engine thread 用
   `MAIN_THREAD_EM_ASM({ globalThis.__probe_on_event(UTF8ToString($0)); }, jsonCstr)`。
4. queue 用 `std::mutex` + `std::condition_variable` + `std::deque<Command>`，
   engine thread 在 `probe_start()` 時以 `std::thread(...).detach()` 啟動。

## 4. C API（`probe_api.h`）

```c
// 全部由 JS 經 ccall 呼叫;立即返回,結果走事件。字串皆 UTF-8。
void probe_start(void);                       // 啟動 engine thread,LOK init
void probe_open(const char* file_url);        // file:///tmp/in.odt
void probe_paint_tile(int x_twips, int y_twips, int w_twips, int h_twips,
                      int canvas_w_px, int canvas_h_px);
void probe_click(int x_twips, int y_twips);   // 定位游標(單擊:down+up)
void probe_insert_text(const char* utf8);     // 主路徑:LOK paste()
void probe_key(int type, int charcode, int keycode); // 備援路徑:postKeyEvent
void probe_save(const char* format);          // "odt";輸出至 file:///tmp/out.<fmt>
void probe_close(void);
void probe_free(void* p);                     // 釋放 tile 事件交付的 pixel buffer
```

事件（JSON，經 `globalThis.__probe_on_event(str)`；`tile` 另帶指標）：

```text
{"type":"ready"}                                  // LOK init 完成
{"type":"opened","parts":N,"width":W,"height":H}  // twips 尺寸(getDocumentSize)
{"type":"tile","ptr":P,"size":S,"w":W,"h":H}      // RGBA pixels 在 HEAPU8[P..P+S)
                                                  // JS 複製後必須呼叫 probe_free(P)
{"type":"saved","url":"file:///tmp/out.odt"}
{"type":"closed"}
{"type":"error","where":"open|tile|...","msg":"..."}
{"type":"lok","id":N,"payload":"..."}             // 轉發的 LOK callback(見 §5.4)
```

## 5. engine thread 實作要點

### 5.1 LOK 初始化（不用 dlopen）

靜態連結下不可走 `LibreOfficeKitInit.h` 的 dlopen 路徑，直接宣告 hook：

```cpp
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
extern "C" LibreOfficeKit* libreofficekit_hook_2(const char*, const char*);
// init:
LibreOfficeKit* kit = libreofficekit_hook_2("/instdir/program", "file:///tmp/user");
```

install path 是 `/instdir/program`（fs image 掛載於 `/instdir`，已由 metadata 驗證）。
`lok_preinit_2` 是 pre-fork 伺服器用的，探針不需要。

### 5.2 開檔與渲染序

```cpp
doc = kit->pClass->documentLoad(kit, url);                 // 失敗→ error 事件(getError)
doc->pClass->initializeForRendering(doc, "{}");
doc->pClass->registerCallback(doc, onLokCallback, this);
doc->pClass->getDocumentSize(doc, &w, &h);                 // → opened 事件
```

### 5.3 tile、輸入、存檔

- `paintTile(doc, buf, canvas_w, canvas_h, x, y, w, h)`；buf 為 `malloc(canvas_w*canvas_h*4)`，
  cairo-rgba 組態下內容為 RGBA，直接交付事件，由 JS `probe_free`。
- `probe_click`：`postMouseEvent(doc, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0)` +
  對應 `MOUSEBUTTONUP`（座標 twips）。
- `probe_insert_text` 主路徑：`paste(doc, "text/plain;charset=utf-8", utf8, strlen(utf8))`。
  若 paste 失敗，備援用 `postKeyEvent(doc, LOK_KEYEVENT_KEYINPUT, charcode, 0)` +
  `KEYUP` 逐字送 Unicode。兩條路徑的成敗都要記進 README（這是 R3 輸入設計的資料）。
- `probe_save`：`saveAs(doc, "file:///tmp/out.odt", "odt", nullptr)` → saved 事件；
  JS 端以 `Module.FS.readFile("/tmp/out.odt")` 取回。

### 5.4 LOK callback 轉發

`onLokCallback(int type, const char* payload, void* data)` 可能在任意 LO 執行緒被叫：
只做「打包成事件字串丟進一個 callback queue，由 engine loop 送出」或直接
`MAIN_THREAD_EM_ASM`（payload 複製後送）。R1 至少轉發：
`LOK_CALLBACK_INVALIDATE_TILES(0)`、`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR(1)`、
`LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`、`LOK_CALLBACK_ERROR`（值見
`include/LibreOfficeKit/LibreOfficeKitEnums.h`，以 header 為準）。

## 6. 建置（`Makefile`）

變數：`LOSRC ?= ../libreoffice-26-8`、`LOBUILD ?= ../wasm-lite/build-headless-probe`。

編譯（兩個 .cpp）：

```text
em++ -c -O1 -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm \
  -DLOK_USE_UNSTABLE_API -I$(LOSRC)/include src/*.cpp
```

exports 檔生成：

```text
cp $(LOBUILD)/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports dist/exports.txt
printf '_probe_start\n_probe_open\n_probe_paint_tile\n_probe_click\n_probe_insert_text\n_probe_key\n_probe_save\n_probe_close\n_probe_free\n' >> dist/exports.txt
```

連結（旗標對齊 core 平台層與 COWASM；不要增刪 -s 選項）：

```text
em++ probe_api.o probe_engine.o \
  -L$(LOBUILD)/instdir/program $$(cat $(LOBUILD)/instdir/program/soffice.js.linkdeps) \
  -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --bind \
  -sMODULARIZE -sEXPORT_NAME=createProbeModule \
  -sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
  -sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536 \
  -sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
  -sASSERTIONS=1 -sEXIT_RUNTIME=0 \
  -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,FS,UTF8ToString,stringToNewUTF8,HEAPU8,HEAPU16,HEAPU32,registerType,ClassHandle \
  -sEXPORTED_FUNCTIONS=@dist/exports.txt \
  --pre-js $(LOSRC)/static/emscripten/environment.js \
  --pre-js $(LOBUILD)/workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link \
  --profiling-funcs \
  -o dist/probe.js
cp $(LOBUILD)/instdir/program/soffice.data dist/
cp $(LOBUILD)/instdir/program/soffice.data.js.metadata dist/
cp web/index.html web/probe.js dist/
```

註：`--bind` 是 core 平台層旗標（部分 core 物件參照 embind runtime），保留；
但**不可**加入 `libunoembind.a` 或 `bindings_uno.js`（總覽 §4）。

## 7. 測試頁（`web/`）

- `serve.py`：`http.server` 子類，對所有回應加
  `Cross-Origin-Opener-Policy: same-origin` 與 `Cross-Origin-Embedder-Policy: require-corp`，
  port 8765，serve `dist/`。
- `index.html` + `probe.js`：
  1. `<input type="file">` 選 ODT → `FS.writeFile('/tmp/in.odt', new Uint8Array(...))`；
  2. 按鈕逐步：Start/Open/Paint/Click/Insert「測」/Save/Download；
  3. `Run All`：自動依序執行（等對應事件再進下一步），插入文字固定為「測」；
  4. tile 事件：`new ImageData(new Uint8ClampedArray(HEAPU8.buffer, ptr, size), w, h)`
     →（複製後）`putImageData` → `probe_free(ptr)`；預設畫文件左上 512×512px、
     對應 tile 區域取 `w_twips = 512 * 15`（1px≈15twips@96dpi）起步，可調；
  5. 每步以 `performance.now()` 打點，結果累積在 `globalThis.__probe_metrics`
     （格式見 R1-C §3），提供「Copy metrics JSON」按鈕；
  6. 所有事件原文列印在頁面 log 區（供 findings 附證據）。

## 8. 驗收清單

1. `make` 產出 `dist/probe.js`、`dist/probe.wasm`，無 undefined symbol。
2. Chromium 開 `http://localhost:8765/index.html`：`ready` 事件出現（LOK init 成功）。
3. 開啟 `test-docs/` 任一 ODT：`opened` 事件帶合理尺寸。
4. Paint：canvas 出現文件內容（不是全白/全黑/雜訊）。
5. Click + Insert「測」：收到 invalidate callback，重畫後可見「測」字。
6. Save + Download：`out.odt` 桌面版 LibreOffice 可開、含「測」、無修復對話框。
7. `Run All` 連續執行 3 次成功（重現性）。
8. README.md 寫明建置與執行步驟、paste/postKeyEvent 兩路徑的實測結果。

## 9. 風險與失敗處理

| 症狀 | 優先檢查 | 處理 |
|---|---|---|
| init 卡住/無 ready | pthread pool 耗盡（console 有 spawn 警告） | 提高 `-sPTHREAD_POOL_SIZE`（7→16）重連結；記錄數值 |
| documentLoad 回 NULL | `getError` 內容；fs image 是否含 registry/services | 開 finding，附 SAL_LOG（`ENV.SAL_LOG='+WARN'` 於 pre-js 設定）輸出 |
| tile 全白 | 尚未 initializeForRendering/尺寸為 0/字型缺失 | 逐項排除；字型問題對照 metadata 內字型清單 |
| 顏色錯亂 | RGBA/BGRA 假設 | 確認 A 組態確實 `--enable-cairo-rgba`；記錄實際 byte order |
| 例外只有 wasm-function[N] | — | 確認 `--profiling-funcs` 在；必要時載入 `emscripten-app-debug` skill 的 Playwright 探針法 |
| 需要改 core 才能過 | — | **停止並回報**（總覽 §3.1） |

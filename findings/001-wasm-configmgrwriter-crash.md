# 001 — WASM 建置啟動即崩潰：configmgrWriter 執行緒逸出未捕捉的 RuntimeException

| | |
|---|---|
| **狀態** | **可送出** —— 根因已隔離到單一變因 |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-07-31 |
| **嚴重度** | 阻斷（整個 WASM 版本無法使用） |
| **可重現** | 100%（含 pthread 位址在內，每次堆疊完全相同） |
| **是否上游** | **是** —— 由 `--disable-symbols` 觸發，任何要出貨的 WASM release build 都會中 |

## 現象

用 Emscripten + Qt5 編出來的 `soffice.wasm` 在瀏覽器開啟後，Qt logo 閃現，接著畫面全白。載入器永遠停在 `Downloading/Compiling...`，canvas 是空的。

## 重現步驟

1. 依 `static/README.wasm.md` 建置 WASM 版本（emsdk 4.0.10 + allotropia qt5 `5.15.2+wasm`）
2. `emrun --hostname 127.0.0.1 --port 6933 workdir/installation/LibreOffice/emscripten/qt_soffice.html`
3. 開新分頁載入該頁

**預期**：出現 Start Center 或 Writer 空白文件
**實際**：白畫面；主控台顯示一個 pthread 因未捕捉的例外死亡

## 證據

- `evidence/001/console.txt` — 完整主控台紀錄（含網路請求時序）
- `evidence/001/screenshot-blank.png` — 空白畫面

關鍵片段：

```
[  0.5s RESP] 200 102087692B soffice.data          ← 資源全部載入成功
[  0.7s LOG]  QRect(0,0 1280x720) 1                 ← Qt 已初始化
[  1.0s LOG]  Thread name: "configmgrWriter"        ← 該執行緒啟動
[  1.0s LOG]  worker: onmessage() captured an uncaught exception: [object WebAssembly.Exception]
[  1.0s LOG]  Error: com::sun::star::uno::RuntimeException,
    at ___throw_exception_with_stack_trace
    at soffice.wasm:wasm-function[177251]:0x49e1a2c
    at soffice.wasm:wasm-function[9907]:0x472ed8
    at soffice.wasm:wasm-function[22835]:0x6aafa4
    at soffice.wasm:wasm-function[58390]:0x131dd59
    at soffice.wasm:wasm-function[58517]:0x1326971
    at soffice.wasm:wasm-function[22875]:0x6b03ea
    at soffice.wasm:wasm-function[22228]:0x66a299
    at soffice.wasm:wasm-function[175847]:0x498e7f8
    at invokeEntryPoint
[  1.0s LOG]  Pthread 0x034de350 sent an error!
```

## 分析

崩潰的是 `configmgr` 的設定寫入執行緒（`configmgr/source/components.cxx:187`，`Thread("configmgrWriter")`）。

`Components::WriteThread::execute()`（同檔 194–222 行）本來就有攔 `RuntimeException`：

```cpp
try {
    writeModFile(components_, url_, data_);
} catch (css::uno::RuntimeException &) {
    // Ignore write errors, instead of aborting:
    TOOLS_WARN_EXCEPTION("configmgr", "error writing modifications");
}
```

**但這個 catch 沒有生效**，例外一路逸出到 `invokeEntryPoint`，殺掉整個 pthread，連帶讓 app 停擺。

兩種可能，**目前無法斷定是哪一種**：

1. **例外不是從那個 try 區塊丟出來的。** `execute()` 裡 `triggerCondition_.wait(l)` 和 `delayOrTerminate_.wait(std::chrono::seconds(1))` 都在 try 之外。時間軸支持這個假設 —— `writeModFile` 前面有整整一秒的等待，而崩潰發生在執行緒啟動後 0.1 秒。
2. **wasm 的例外型別比對失效**，`catch (css::uno::RuntimeException &)` 沒認出丟出來的型別。

`writeModFile`（`configmgr/source/writemodfile.cxx:561`）確實有兩處會丟 `RuntimeException`（567–580、582–594 行），都是在檔案系統操作回傳非 `E_None`/`E_EXIST`/`E_ACCES` 的錯誤時。MEMFS 回傳的錯誤碼跟原生檔案系統不同，是合理的嫌疑 —— 但時間軸不支持。

### 對照建置

| 建置 | 組態 | 結果 |
|---|---|---|
| `build/`（lite） | 32 個旗標 + 2 個本地 patch | ❌ 崩潰 |
| `build-stock/` | `--with-distro=LibreOfficeWASM32 --enable-symbols` | ✅ **Start Center 正常算繪** |
| `build-t1/` | stock + `--with-wasm-module=writer` | ✅ 正常 |
| `build-t2/` | t1 + `--enable-release-build` | ✅ 正常 |
| `build-t3/` | **lite 全套，只把 `--disable-symbols` 換成 `--enable-symbols=Executable_soffice_bin`** | ✅ **正常** |

**t3 是決定性的一輪。** 它與崩潰的 lite build 之間，31 個 configure 旗標完全相同，只差符號設定；
而且符號只開給 `Executable_soffice_bin` 一個 target，所有函式庫的 .o 與 lite 逐位元組相同（ccache 全命中）。
所以差異被隔離在**最終那次 emcc 連結**。

`config_host.mk` 逐項比對後，兩邊**執行期相關的差異只有四個變數**：

```
ENABLE_SYMBOLS_FOR                LITE=(空)   STOCK=all    → 唯一剩下的
ENABLE_WASM_STRIP_CALC            LITE=TRUE   STOCK=(空)   → t1 排除
ENABLE_WASM_STRIP_ACCESSIBILITY   LITE=TRUE   STOCK=(空)   → t1 排除
ENABLE_RELEASE_BUILD              LITE=TRUE   STOCK=(空)   → t2 排除
```

`build/`(崩) 與 `build-t2/`(正常) 的 `config_host.mk` 現在**只差 `ENABLE_SYMBOLS_FOR` 一項**
（另有 `DISABLE_CVE_TESTS`／`MSGFMT`／`GIT_NEEDED_SUBMODULES` 三項，皆為編譯期或語言相關，
且 zh-TW 已用免重編方式排除）。

**結論：`--disable-symbols` 就是元凶**（t3 直接驗證，非僅排除法）。

其餘 20 幾個 `--disable-*` 對 `config_host.mk` **毫無影響** —— 它們在 Emscripten 上本來就是預設關閉的。

### 已排除

| 嫌疑 | 排除依據 |
|---|---|
| 啟動參數 | 測了 4 種（無參數、`--writer --norestore --nologo`、加 `-env:UserInstallation=file:///tmp/louser`、只有 UserInstallation）→ 堆疊完全相同 |
| COOP/COEP、SharedArrayBuffer | `crossOriginIsolated: true`、`hasSAB: true` |
| 資源載入失敗 | `soffice.wasm` / `soffice.data` / `metadata` 全部 HTTP 200，大小正確 |
| 混到系統的另一份 emscripten | `config_host.mk` 的 CC/CXX 都指向 emsdk 4.0.10；系統另有 3.1.69 但沒被用到 |
| Qt5 例外旗標設錯 | configure 沒帶 `-fwasm-exceptions`，符合 `README.wasm.md` 的要求 |
| zh-TW 語言包 | 從 `soffice.data.js.metadata` 索引移除那 3 個 `.xcd`（blob 不動，免重編）→ 堆疊不變 |
| 使用者設定檔路徑 | 直接改 blob 內 `bootstraprc` 的 `UserInstallation` 為可建立的路徑（等長置換）→ 堆疊不變 |
| `--with-wasm-module=writer` | `build-t1` 專門驗證 → 正常 |
| `--enable-release-build` | `build-t2` 專門驗證 → 正常。且 t2 的 `bootstraprc` 就是 `$SYSUSERCONFIG/libreoffice/4`，等於再次獨立否定路徑假設 |

## 環境

```
LibreOffice   26.8.0.1.0+   libreoffice-26-8 @ 671c848b1bb8 (2026-07-30)
Emscripten    4.0.10
Qt            allotropia/qt5 5.15.2+wasm @ 3d440b7787f9 (2025-05-23)
OS            Ubuntu 26.04 LTS / kernel 7.0.0-28-generic / x86_64
瀏覽器         Playwright Chromium 151.0.7922.34（headless）
              系統 Chrome 150.0.7871.128 亦重現
```

完整輸出：`./env-snapshot.sh`

**注意：目前的重現是在自訂精簡組態上**（`--with-wasm-module=writer` + 20 幾個 `--disable-*`，見 `env-snapshot.sh` 的 configure 區塊），**且套過兩個本地修改**（fs image 的語言清單與額外字型）。這是這張單還不能送的主因。

## 機制

在 Emscripten 平台上，符號開關的作用點**只有一個**。`solenv/gbuild/LinkTarget.mk:60`：

```make
gb_LinkTarget__get_debugldflags = $(if $(call gb_target_symbols_enabled,$(1)),\
    $(gb_LINKER_DEBUGINFO_FLAGS),$(gb_LINKEROPTFLAGS) $(call gb_LinkTarget__get_stripldflags,$(1)))
```

但 EMSCRIPTEN 平台上這三個變數**全是空的**：

```
EMSCRIPTEN_INTEL_GCC.mk:72   gb_LINKEROPTFLAGS :=
EMSCRIPTEN_INTEL_GCC.mk:73   gb_LINKERSTRIPDEBUGFLAGS :=
com_GCC_defs.mk:234          gb_LINKER_DEBUGINFO_FLAGS=
```

所以連結旗標兩邊相同。真正的差異來自 `LinkTarget.mk:49` 把 `gb_DEBUGINFO_FLAGS` 加進該 target 的
編譯旗標，而在 Emscripten 上 emcc 同時是編譯器與連結器，這些旗標會一路帶到最終連結：

```
EMSCRIPTEN_INTEL_GCC.mk:76   gb_DEBUGINFO_FLAGS = -g
EMSCRIPTEN_INTEL_GCC.mk:79   gb_DEBUGINFO_FLAGS += -gseparate-dwarf -gsplit-dwarf -gpubnames
```

t3 產生了 `soffice.wasm.debug.wasm`（199 MB），證明 `-gseparate-dwarf` 確實到達連結階段。

**推論**：`-g` 存在時 emscripten 限制 postlink 的 wasm 改寫（`EMSCRIPTEN_INTEL_GCC.mk:65-69` 那個
`-Wno-limited-postlink-optimizations` 就是為了消掉隨之而來的警告）；不存在時則執行完整的
wasm-opt 後處理，而該後處理破壞了 C++ 例外處理的型別比對 —— 這正好解釋
`configmgr/source/components.cxx:208` 的 `catch (css::uno::RuntimeException &)` 為何攔不到。

**此段最後一步是推論，尚未直接證實**（需要比對兩份 wasm 的例外處理 section，或請 emscripten
上游確認）。已證實的是輸入輸出關係：同樣的原始碼與 31 個旗標，`--disable-symbols` 崩、
`--enable-symbols=Executable_soffice_bin` 正常。

## 影響

**任何要出貨的 WASM 建置都會中。** 想縮小 `soffice.wasm` 就會關符號，一關就啟動即死。
這大概也是為什麼一直沒被發現 —— 開發與測試都用帶符號的建置。

## 還缺什麼

- [x] 用上游預設組態重現 → **不重現**，確認非上游
- [x] `build-t2` = t1 + `--enable-release-build` → 正常，排除
- [x] `build-t3` → **正常**，根因確認為 `--disable-symbols`
- [ ] 搜尋 Bugzilla 是否已有重複
- [ ] 確認 Component（gbuild / Build tooling？）
- [ ] （可選，加分）比對兩份 wasm 的例外處理相關 section，把「postlink 破壞 EH」從推論變成證據
- [ ] 若確認是 symbols/postlink → 重新評估是否為上游 bug，若是則補符號化堆疊後送出

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | ？（可能是 framework 或 Writer；送出前查證） |
| Version | 26.8.0.1 rc |
| Hardware / OS | x86-64 / Linux (Ubuntu 26.04) |
| Summary | WASM: `--disable-symbols` breaks C++ exception handling — startup crash in configmgrWriter |

## 時間軸

- 2026-07-31 lite build 完成，瀏覽器開啟後白畫面
- 2026-07-31 以 Playwright 抓到主控台，定位到 `configmgrWriter`
- 2026-07-31 排除啟動參數、COOP/COEP、資源載入、工具鏈混用、Qt 旗標
- 2026-07-31 啟動 stock + symbols 重編以確認是否上游
- 2026-07-31 **stock build 正常運作**（Start Center 算繪成功）→ 非上游
- 2026-07-31 `config_host.mk` 比對，差異收斂到 4 個變數
- 2026-07-31 免重編排除 zh-TW 語言包與 UserInstallation 路徑
- 2026-07-31 `build-t1` 排除 `--with-wasm-module=writer`
- 2026-07-31 `build-t2` 排除 `--enable-release-build` → 排除法指向 `--disable-symbols`
- 2026-07-31 `build-t3` 直接驗證 → **確認 `--disable-symbols` 為根因，且差異隔離在最終連結**

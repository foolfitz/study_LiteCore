# wasm-lite patches — worktree patch inventory

> **建立日期**：2026-08-01
> **對應 worktree**：`libreoffice-26-8` @ `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
> **目的**：把 worktree 內的既有本地修改逐項落成具名 patch，標明「兩線共用/僅 Qt6 線」與上游狀態，
> 讓 Qt6-WASM QA 線與 headless `wasm_sdk_probe` 線可以各自組出乾淨、可重現的建置組態。
>
> **重要**：worktree 本身的修改是工作現場，不可 reset。本目錄的 patch 檔是它們的
> 可稽核快照；`git apply --check --reverse` 已驗證每份 patch 與 2026-08-01 的 worktree 狀態一致。

---

## LibreOffice 26.8 patches

| Patch | 檔案 | 分類 | Finding | 上游狀態 |
|---|---|---|---|---|
| `libreoffice-26.8-emscripten-emdwp-partial-symbols.patch` | `solenv/gbuild/platform/unxgcc.mk` | **兩線共用**（任何開 partial symbols 的 Emscripten build） | [004](../../findings/004-emscripten-install-partial-symbols.md) | 候選，未送 |
| `libreoffice-26.8-emscripten-fs-image-multilang-registry.patch` | `static/CustomTarget_emscripten_fs_image.mk`（hunk 1） | **兩線共用**（任何 `--with-lang` 多語系 WASM build；co-26.04 engine 仍硬編 en-US，確認上游未解） | — | 候選，未送 |
| `libreoffice-26.8-emscripten-fs-image-extra-fonts.patch` | `static/CustomTarget_emscripten_fs_image.mk`（hunk 2） | **兩線共用，但屬本地客製**（`LITE_EXTRA_FONTS_DIR` 環境變數注入 CJK 字型） | — | 不送（機制若通用化可再議） |
| `libreoffice-26.8-emscripten-jspi-stale-eventlistener-export.patch` | `desktop/CustomTarget_soffice_bin-emscripten-exports.mk` + `solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk` | **僅 Qt6+JSPI 線**（移除 Qt 6.10.2 已不存在的 `qstdweb::EventListener` 匯出；probe 不用 JSPI，不需要） | [006](../../findings/006-qt6-wasm-stale-eventlistener-export.md) | 候選，未送 |
| `libreoffice-26.8-wasm-strip-accessibility-single-input.patch` | `configure.ac` | **僅 headless probe 線的 a11y 閘門 0 建置**（套上之後才有東西可量；其他建置樹不受影響，見下方說明） | [057](../../findings/057-one-build-switch-two-halves-that-answer-to-different-inputs.md) | 候選，未送（送出暫緩中；重啟時這份就是要提的修法） |
| `libreoffice-26.8-qt-wasm-inputcontext-main-thread.patch` | `vcl/qt5/QtFrame.cxx` | **僅 Qt6 線**（input context 同步代理回瀏覽器主執行緒） | [008](../../findings/008-qt6-wasm-inputcontext-invalid-emval-value.md) | Bugzilla draft，依 008 驗證計畫送 master |
| `libreoffice-26.8-wasm-bridge-scaddins-signatures.patch` | `bridges/CustomTarget_gcc3_wasm.mk` | **含 Calc 的 WASM 建置**（`ENABLE_WASM_STRIP_CALC` 為空時把 scaddins 的 internal API 以 primary 餵給 `wasmbridgegen`；writer-only 的 `build-headless-probe` 條件不成立、產物不變） | [159](../../findings/159-functions-recalculated-at-load-give-value-errors-on-the-viewer-core.md) | 候選，未送（上游 master 的同一檔與 26.8 相同，2026-10-21 查） |
| `libreoffice-26.8-wasm-explicit-database-connectivity.patch` | `configure.ac`（兩處） | **只影響明確下 `--enable-database-connectivity` 的 Emscripten 建置**（現行兩棵樹都沒下，configure 結果不變） | [158](../../findings/158-an-ods-with-form-controls-cannot-be-painted-on-the-wasm-core-forms-service-absent.md) | 不送（本地組態選擇；上游 2021 年 `dc9ccf3d8f29` 為了 Linux 靜態建置一律關掉，iOS／Android 照開） |
| `libreoffice-26.8-wasm-reportdesign-follows-dbaccess-strip.patch` | `RepositoryModule_host.mk` | **只影響開了 DB connectivity 的 wasm 建置**（reportdesign 搬進 `ENABLE_WASM_STRIP_DBACCESS` 的同一個區塊；非 wasm 建置照舊建它，現行兩棵 wasm 樹本來就沒有它） | [158](../../findings/158-an-ods-with-form-controls-cannot-be-painted-on-the-wasm-core-forms-service-absent.md) | 候選，未送（上游組合 DBCONNECTIVITY＋WASM_STRIP_DBACCESS 本身不一致） |
| `libreoffice-26.8-wasm-dbaccess-core-with-explicit-dbconnectivity.patch` | `RepositoryModule_host.mk`、`dbaccess/Module_dbaccess.mk` | **只讓開了 DB connectivity 的 strip 組態補回 dba／dbahsql**（RowSet）；dbu／dbaxml／sdbt／UI configs 與 reportdesign 仍排除，原生與未開 DB connectivity 的兩棵出貨核心照舊 | [158-B](../../findings/158-an-ods-with-form-controls-cannot-be-painted-on-the-wasm-core-forms-service-absent.md) | 不送（本地組態選擇；SPEC-M4-viewer-v3，擁有者選 A） |

注意：兩份 fs-image patch 拆自同一檔案的同一份 diff。在乾淨樹上套用時先套
`multilang-registry` 再套 `extra-fonts`（hunk 行號以此順序計算；`git apply` 對位移有容忍度，
但依此順序最穩）。

### `wasm-strip-accessibility-single-input` 的行為範圍（2026-08-22 加入）

這份 patch 把 `ENABLE_WASM_STRIP_ACCESSIBILITY` 的**兩個獨立存在**接到同一個輸入上：
C++ 巨集（`configure.ac:3498`，原本由 `--enable-wasm-strip` 決定，而該值在 Emscripten 上
`:1280` 無條件為 yes）改成跟著 Make 變數走（`:4372/4379/4386`，由 `--with-wasm-module` 決定）。
`AC_DEFINE` 必須**移到 module 迴圈之後**，否則變數還沒有值——這是 finding 057 的修法，
細節與選這個方向的理由寫在 `handoff/a11y-gate-0/PATCH.md`。

套用後對各組態的影響：

- `--with-wasm-module` 用**上游預設**（`calc writer`）或任何含 `calc`／`impress` 的值：
  巨集**不再被定義**（值 0），a11y 呼叫端編進來，與「物件本來就被編進來」一致。
  **這是上游預設組態的行為改變**，也正是 057 說的缺陷被修好。
- `--with-wasm-module=writer`（本 repo 現行的 `build-headless-probe`）：變數是 `TRUE`，
  巨集照舊被定義成 1。**現行產品建置樹完全不受影響。**
- 非 Emscripten 但下 `--enable-wasm-strip` 的靜態建置：變數從未被設過（`:4372` 在
  `_os = Emscripten` 的區塊裡），所以巨集不再被定義。那個組態原本正是「物件編進來、
  呼叫端被拿掉」的同一個缺陷，修法讓兩半一致。

### 2026-10-21 加入的兩份（檢視引擎 v2 的核心批次）

**`wasm-bridge-scaddins-signatures`**：`wasmbridgegen` 只為 **primary** registry 產生 `callVirtualFunction_*` 呼叫簽章；上游只餵 udkapi＋offapi，
Calc 的 Analysis／Date／Pricing add-in 介面在 `scaddins/idl`（`InternalUnoApi_scaddins.mk`）裡，所以經 `XIdlMethod::invoke` 呼叫它們時
bridge 找不到簽章、丟 RuntimeException，Calc 顯示 `#VALUE!`（finding 159）。patch 在有建 scaddins 的組態下把
`$(WORKDIR)/UnoApiTarget/scaddins.rdb` 加成相依與 `+` 參數。離線用既有的 build-side 產生器實跑過：不加時輸出與核心現有的三個檔逐位元相同，
加了之後簽章 55 → 80 個（`findings/evidence/m4-ods/phase-e/159-diagnosis/bridgegen-offline/`）。

注意：在**已經建好**的樹上只套 patch 不會觸發重產——`scaddins.rdb` 比三個產物舊，gbuild 也不追蹤指令列的變化。要在既有樹上生效，
得先刪掉 `workdir/CustomTarget/bridges/gcc3_wasm/` 的三個檔。

**`wasm-explicit-database-connectivity`**：Emscripten 上 DB connectivity 被**兩處**無條件關掉（`enable_wasm_strip` 區塊、`DISABLE_DYNLOADING`
區塊），所以 `--enable-database-connectivity` 原本沒有作用。patch 把兩處都改成「沒有明確指定才關」。開了之後要自己再下
`--disable-firebird-sdbc --disable-mariadb-sdbc --disable-postgresql-sdbc`（`disable_database_connectivity_dependencies` 不會被呼叫，
三個驅動在 Emscripten 上的預設是開）。dbaccess 仍由 `ENABLE_WASM_STRIP_DBACCESS`（＝`ENABLE_WASM_STRIP`）拿掉，進來的是 `forms`、
connectivity 的 `dbtools` 等。

**`wasm-reportdesign-follows-dbaccess-strip`（2026-10-22 加入）**：`build-ods-viewer-v2` 第一次 `make`（finding 003 重試之後）停在
`LinkTarget.mk: *** used LinkTarget Library/libdbulo.a not defined`。reportdesign 在 DB connectivity 打開時被加進模組清單，而它的
`Library_rpt`／`Library_rptui` 連 dbaccess 的 `dbu`；dbaccess 卻被 `ENABLE_WASM_STRIP_DBACCESS` 拿掉了。普查：dbaccess 的五個函式庫
（dba、dbahsql、dbaxml、dbu、sdbt）在 dbaccess 以外只有 reportdesign 用到（另一處是只在動態連結時生效的序列化清單）。patch 讓 reportdesign
跟 dbaccess 同進退。擁有者 2026-10-22 選 A（補這一行再建），覆寫規格 §2.5 的 F-1 預設。

**兩份都改的是共用原始碼樹**，而 `Makefile.in` 讓 `config_host.mk` 相依於 `configure.ac`：之後在 `build-headless-probe` 或
`build-a11y-gate0` 跑任何 `make`，都會先自動重跑一次 autogen。兩棵樹都沒下 `--enable-database-connectivity`，結果應該不變；
重跑之後比一下 `config_host.mk` 與 `config_host/*.h` 再往下。

## Qt 6.10.2 patches（既有，列入盤點）

| Patch | 分類 | Finding |
|---|---|---|
| `qtbase-6.10.2-wasm-inputcontext-ecmastring.patch` | 僅 Qt6 線 | 008 相關 |
| `qtbase-6.10.2-wasm-pointerenter-null-dom-node.patch` | 僅 Qt6 線 | [007](../../findings/007-qt6-wasm-pointerenter-null-dom-node.md) |
| `qtbase-6.10.2-wasm-suspendresume-reentrant.patch` | 僅 Qt6 線 | 007/008 相關 |

## 兩條線的組態含意

- **headless `wasm_sdk_probe`**（`--disable-gui`，無 Qt、無 JSPI）：
  只需要 `emdwp-partial-symbols`（若開 symbols）、`fs-image-multilang-registry`、
  `fs-image-extra-fonts`（若要 CJK 字型）。
  檢視引擎 v2 的核心（`build-ods-viewer-v2`）另外需要 `wasm-strip-accessibility-single-input`、
  `wasm-bridge-scaddins-signatures`、`wasm-explicit-database-connectivity` 與 `wasm-reportdesign-follows-dbaccess-strip`。
  158-B／檢視引擎 v3 在同一棵 `build-ods-viewer-v2` 上另加 `wasm-dbaccess-core-with-explicit-dbconnectivity`；
  只改模組選擇，不改 configure，不需 autogen。`build-a11y-gate0` 與 `build-headless-probe` 沒有 DBCONNECTIVITY，新增分支不加入模組。
- **Qt6-WASM QA 線**：需要全部五份 LibreOffice patch 加三份 qtbase patch。

## worktree 未追蹤檔案

- `LibreOffice_VCL_Qt6_研究報告.md`（研究筆記，非建置必要；保留在 worktree，不屬於任何 patch）

## 驗證方式

```bash
cd libreoffice-26-8
for p in ../wasm-lite/patches/libreoffice-26.8-*.patch; do
  git apply --check --reverse "$p" && echo "OK $p"
done
```

全部 OK 表示 patch 集與 worktree 現狀一致；任何一份失敗代表 worktree 又有新修改，
需重新產生對應 patch 並更新本文件。

2026-10-21：加入兩份（bridge 簽章、DB connectivity），八份 LibreOffice patch 全部 `git apply --check --reverse` 通過。
2026-10-22：加入第九份（reportdesign 跟著 dbaccess strip），九份全部 `git apply --check --reverse` 通過。
2026-10-23：加入第十份（158-B 只補 dba／dbahsql）；與第九份各自 `git apply --check --reverse`，十份全過。規格先釘於 `specs/SPEC-M4-viewer-v3.md`；核心建置交擁有者執行。

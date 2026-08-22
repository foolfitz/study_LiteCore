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

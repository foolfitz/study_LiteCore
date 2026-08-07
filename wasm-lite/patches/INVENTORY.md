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
| `libreoffice-26.8-qt-wasm-inputcontext-main-thread.patch` | `vcl/qt5/QtFrame.cxx` | **僅 Qt6 線**（input context 同步代理回瀏覽器主執行緒） | [008](../../findings/008-qt6-wasm-inputcontext-invalid-emval-value.md) | Bugzilla draft，依 008 驗證計畫送 master |

注意：兩份 fs-image patch 拆自同一檔案的同一份 diff。在乾淨樹上套用時先套
`multilang-registry` 再套 `extra-fonts`（hunk 行號以此順序計算；`git apply` 對位移有容忍度，
但依此順序最穩）。

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

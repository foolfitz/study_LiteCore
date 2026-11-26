# 已刪除的三棵 wasm-lite 建置樹的紀錄

> **建立日期**：2026-10-12
> **原因**：擁有者的硬碟空間不足，問了暫存檔體積。逐樹核對後由擁有者決定刪除（選項 A：先存設定檔再刪）。

## 刪了什麼

| 樹 | 大小 | 它是什麼 |
|---|---|---|
| `wasm-lite/build-qt6-poc` | 6.4 GB | Qt6／JSPI 的 QA 建置（2026-08-01 之後沒再動）。findings 006–009 在這棵樹上驗證過本地修法；004 留著的「重連結看 `.dwp` 有沒有產生」也要靠它 |
| `wasm-lite/build-t3` | 6.1 GB | Qt5 參考建置，finding 001「會動」的那一半；finding 002 的 `vcldemo.wasm` |
| `wasm-lite/build` | 5.7 GB | 最早的 lite 建置（31／32 個旗標、`--disable-symbols`），finding 001「會崩」的那一半 |

## 刪之前核對過的事

- **沒有任何連結或打包的輸入來自這三棵樹**：
  - `wasm_sdk_probe/Makefile:2` 的預設核心是 `build-headless-probe`（出貨的 v8、v15–v19，以及下一次連結批次），`:127` 的 `E2_V5_CORE` 是 `build-a11y-gate0`（v5、v9–v14、之後的 writer+calc）。這兩棵**保留**。
  - `dist/profiles` 與 `build/archive` 底下的 `probe.js` 嵌著核心路徑：64 個是 `build-headless-probe`、19 個是 `build-a11y-gate0`，嵌著這三棵的是 0 個。
  - 工具、腳本、Makefile 裡沒有任何地方引用 `build-t3` 或 `build-qt6-poc`。`build/` 只出現在 `tools/build_base_no35_pack.py:48` 的註解（說明「不是這一棵」），以及舊的 `findings/env-snapshot.sh:17` 預設值。
- **沒有任何出貨、候選或封存的 profile 出自這三棵樹**：它們的 `soffice.data` 大小（102,087,692 與 81,956,525 bytes）在樹外找不到同大小的副本。
- 核對由 subagent 唯讀完成，主 session 抽查了上面的 Makefile 兩行與 `probe.js` 計數。

## 這裡留了什麼

- 每棵樹的設定紀錄：`autogen.input`／`autogen.lastrun`、`lite-configure-args.txt`、env 腳本，以及 configure 解出來的 `config_host.mk`。路徑是絕對路徑，照原樣保留。
- `OUTPUTS.sha256`：刪除前每棵樹主要輸出的 sha256 與大小（`soffice.{wasm,js,data}`、`.debug.wasm`、`vcldemo.*`）。`build-qt6-poc` 的 `soffice.wasm` 是 `601c9ab1…`，與 `devlog/DEVLOG-2026-08-01-qt6-wasm.md` 記的相同。

## 代價

- 位元組本身沒有留下來，只留了雜湊。Qt 線（findings 001、004、006–009）若要重驗，需要數小時重建。上游送出自 2026-08-15 起擱置。
- `findings/062-…md:288` 與 `findings/evidence/062/layer/ATTRIBUTION.md:14` 引用的 `wasm-lite/build/workdir/UnpackedTarball/cairo/src/cairo-image-surface.c:59` 路徑失效。同一行仍在 `wasm-lite/build-headless-probe/workdir/UnpackedTarball/cairo/src/cairo-image-surface.c`，原始 tarball 也在 `libreoffice-26-8/external/tarballs`。
- Qt 工具鏈（`wasm-lite/tools/` 底下的 `qt5-wasm`、`qt5-src`、`qt6-wasm-*`、`qtbase-everywhere-src-6.10.2`，約 2.8 GB）原本只有這三棵樹引用，現在沒有任何保留的樹引用它們。刪不刪是另一個決定，**尚未處理**。`emsdk` 與 `extra-fonts` 是保留的兩棵樹與每一次連結都要用的。

---

## 2026-11-26：專案凍結時刪除的建置樹

> **原因**：擁有者 2026-11-26 凍結 study_LiteCore、移往 study_COOL，同意刪 B 級（盤點見 `RESEARCH-2026-11-26-freeze-disk-cleanup.md`）。

| 樹 | 大小 | 它是什麼 |
|---|---|---|
| `wasm-lite/build-headless-probe` | 5.5 GB | 出貨核心（`wasm_sdk_probe/Makefile:2` 的 `LOBUILD`） |
| `wasm-lite/build-a11y-gate0` | 5.9 GB | `E2_V5_CORE`（writer+calc、a11y 閘門 0） |
| `wasm-lite/build-ods-viewer-v2` | 6.0 GB | `ODS_*_CORE`（Calc 線） |
| `build-native-26-8` | 6.6 GB | 原生 core，`build_*_native.py` 的 harness 連它 |
| `native-lok-26-8/build`＋`src` | 7.8 GB | 原生 LOK 建置；`src` 是 detached worktree（`git worktree remove --force`，只有乾淨的 `dictionaries` 子模組）。目錄裡的 Bugzilla 分類 md 留在原位 |

同一輪也移除了 `libreoffice-26-2`、`collabora-25.04` 兩個 worktree（分支 `libreoffice-26-2-5`、`distro/collabora/co-25.04` 仍在 `libreoffice-25-2/.git`）、`libreoffice-26-8/external/tarballs`、`wasm-lite/tools/qt5-src`。

**刻意保留**：`wasm-lite/tools/emsdk`、`qt5-wasm`、`pw`。`wasm-lite/upstream-master/` 的 `build-186-R`、`build-nosym` 的 `config_host.mk` 與 `build.sh`、`relink_vcldemo.sh`、`run_probe.sh` 都用到它們，而上游工作（002／186／159）沒有凍結。

## 這次留了什麼

- 設定紀錄：上表五棵樹的 `autogen.input`、`config_host.mk`，有 `env.sh` 的也存了。分別放在同名目錄；兩棵原生樹放在 `native-build-native-26-8/`、`native-lok-26-8-build/`。
- `OUTPUTS.sha256` 末段：刪除前的 `soffice.{wasm,js,data,data.js.metadata}`、emscripten `exports`、原生的 `libmergedlo.so`／`libsofficeapp.so`／`soffice.bin`。
- `libreoffice-26-2-worktree.diff`（＋`.HEAD`）：26-2 worktree 移除前的未提交修改。內容與 26.8 的兩份 fs-image patch 相同，只是套在 26.2 上。

## 代價

- 出貨的 profile 不受影響，都在 `wasm_sdk_probe/dist/profiles` 與 `build/archive`（已設唯讀）。
- 要恢復開發，三棵 wasm 核心與兩棵原生樹都得從 `libreoffice-26-8`＋`wasm-lite/patches/` 重建，每棵 1–2 小時（擁有者的 make）。重建出的 hash 不會與上面記的相同。

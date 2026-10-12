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

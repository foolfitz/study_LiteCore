# Markdown 貼上：LibreOffice 26.x 怎麼做、LiteCore 缺什麼（2026-10-14）

**緣起**：擁有者手測 0.2.19 時，把一段 Markdown 貼進新文件，結果沒有轉成對應的格式。擁有者說這是「libreoffice 26.x 原生的功能」，希望 LiteCore 也能相容。

**擁有者裁示（2026-10-14）**：**A：明確的「貼上為 Markdown」**。Ctrl+V 照舊貼純文字，另外提供一個「貼上為 Markdown」，不自動猜。要改引擎，排進下一批連結（和 `Language=`、finding 031 的修法一起）。

## LibreOffice 26.x 的原生行為（讀 `libreoffice-26-8` 原始碼與 git 紀錄）〔已讀原始碼〕

- **一般貼上不會自動轉 Markdown。**純文字（`SotClipboardFormatId::STRING`）走 `ReadAscii`；只有剪貼簿格式是 `MARKDOWN`（`text/markdown`）時，才走 `ReadMarkdown`（`sw/source/uibase/dochdl/swdtflvr.cxx:2214–2239`）。
- **使用者的入口是「選擇性貼上 → Markdown」。**演變如下：
  - `f8c2fbdbceac`（2025-07-19，tdf#162153）：剪貼簿開始支援 `text/markdown`。當時要用 xclip、wl-copy 這類工具手動標上 mimetype 才用得到。
  - `c75975d1ac46`：Markdown 的 DataFlavor 改成 `OUString`，處理方式和純文字相同，所以**一般純文字也能用「選擇性貼上 → Markdown」**。commit 說明的理由是：大多數系統的剪貼簿不會標出 `text/markdown`。
  - `a3eb70238396`、`04a253b3c71f`：Qt 與 macOS 後端也在選擇性貼上加了 Markdown。
  - `1f665988d0b5`（2026-03-31，tdf#171481）：**拿掉 Markdown 的啟發式自動偵測**，理由是「現在選擇性貼上已經有 Markdown 了」。
  - `d5509c16cafe`、`0c361202d0ee`（tdf#171121）：Markdown 在剪貼簿上的優先順序降到**比純文字還低**，因為幾乎沒有剪貼簿服務原生支援它。
  - `f12cc758a1a0`、`de87e5b0ae65`、`8f5d83abd4a0`（cool#15535，Collabora）：修正貼進既有段落的行為、沿用相符的編號規則與段落格式。**Collabora Online 也走這條路。**
  - `1b0c64be44c4`（tdf#172084）：貼 Markdown 時不偵測編碼。
- Calc 也有「選擇性貼上 → Markdown」（`6e28f612c22e`，tdf#171481）。

## LiteCore 的現況〔已讀原始碼〕

- **WASM 核心有 Markdown 解析器**：`wasm-lite/build-headless-probe` 的 `BUILD_TYPE` 含 `MD4C`，`workdir/CxxObject/sw/source/filter/md/` 下有 `swmd.o`、`mdtab.o`、`mdnum.o`、`mdcallbcks.o`、`wrtmd.o`。v19、v20 的 `probe.wasm` 都帶有 `text/markdown` 字串（sot 的格式表）。**解析器是否真的連結進 `probe.wasm` 沒有直接驗證過**（wasm 的函式名已最小化），要在實作前用一次 `paste("text/markdown", …)` 量出來。
- **引擎把貼上的 mimetype 寫死成純文字**：`handleInsertText` 呼叫 `paste(document, "text/plain;charset=utf-8", …)`（`wasm_sdk_probe/src/probe_engine.cpp:3239`）。所以就算使用者想轉 Markdown，引擎也不會轉。
- 頁面沒有自己的貼上處理器（`web/e2-editor-app.js:2392` 的註解說明了原因）：貼上是瀏覽器的 `beforeinput`（`insertFromPaste`），由輸入轉接器送出一次 `insertText`。

## 下一批連結要做的事（草稿，尚未成為規格）

1. 引擎：一個帶 mimetype 的貼上（或專門的 `paste-markdown` 指令），呼叫 `paste(document, "text/markdown", …)`；ABI 與 action 清單怎麼擴充由規格決定。
2. 頁面：「貼上為 Markdown」的入口（工具列按鈕或快捷鍵），讀剪貼簿文字，送給上面那個指令。讀剪貼簿要考慮瀏覽器權限（`navigator.clipboard.readText` 需要使用者手勢，Firefox 另有限制），要先量。
3. 判準至少要有：標題、粗體、斜體、清單、程式碼、表格各轉成對應的 Writer 格式；貼進既有段落的行為和桌面版 LibreOffice 26.8 逐項一致（原生先量）；Ctrl+V 的行為不變（紅案：一般貼上不轉換）。
4. 原生先量：同一段 Markdown 在 native 26.8 用 `paste("text/markdown")` 貼上的結果，作為參照。
EOF
cd /home/jiajun/LibreOffice/study_LiteCore && git add research/RESEARCH-2026-10-14-markdown-paste.md && git commit -q -m "Research: Markdown paste -- LibreOffice 26.x converts only via Paste Special > Markdown (heuristics removed in tdf#171481, Collabora follows cool#15535); our engine hard-codes text/plain at probe_engine.cpp:3239 though md4c and the sw markdown filter are in the WASM core; owner chose A (explicit 'paste as Markdown') for the next link batch

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- research/RESEARCH-2026-10-14-markdown-paste.md && git log --oneline -1
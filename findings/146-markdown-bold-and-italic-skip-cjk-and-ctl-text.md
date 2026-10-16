# 146 — Markdown 匯入的粗體與斜體不套用到中日韓與複雜文字

| | |
|---|---|
| **狀態** | 待驗證（原始碼與原生存檔一致；顯示未看；上游送出擱置中，只登錄） |
| **Bugzilla** | tdf#______（送出後回填） |
| **發現日** | 2026-10-16 |
| **嚴重度** | 一般 |
| **可重現** | 100%（原生 3/3，P1 與 P2 兩個位置） |
| **是否上游** | **未確認**：原始碼層面是上游的程式碼；重現用的是沒有本地修改的原生 LOK build，但還沒在官方釋出版的桌面 LibreOffice 上重現 |

## 現象

把 `**粗體中文**` 當成 Markdown 貼上（LOK `paste(doc, "text/markdown;charset=utf-8", …)`），存檔裡那段文字的自動樣式只有西文的字重：`fo:font-weight="bold"`，沒有 `style:font-weight-asian`（也沒有 `style:font-weight-complex`）。Writer 對中日韓字元用的是 Asian 那一組屬性，所以這些字預期**不會**顯示成粗體；斜體同理。

## 重現步驟

1. 原生 LibreOfficeKit（26.8，`671c848b`），空文件。
2. `paste(doc, "text/markdown;charset=utf-8", "**粗體中文**")`。
3. 存成 `.fodt`，看 `粗體中文` 那個 span 的樣式。

**預期**：粗體同時套到 Western／Asian／Complex 三組字重（桌面 Writer 的「粗體」按鈕就是三組一起設）。
**實際**：只有 Western（`fo:font-weight`）。

## 證據

- `evidence/146/M8-run1-bold-span.txt`：

  ```
  <style:style style:name="T1" style:family="text">
     <style:text-properties fo:font-weight="bold"/>
  </style:style>
  span T1 粗體中文
  ```

  取自 `evidence/link-batch-v21/native/markdown-paste/out/P1-M8/run1/after.fodt.gz`（sha256 `96b7cc8e…`）；三回一致（同目錄 `run2`、`run3`，以及 P2 的範本文件）。
- `evidence/146/mdcallbcks-671c848b-140-175.cxx.txt`：原始碼摘錄。
- `evidence/146/env.txt`：環境快照，讀的是 `libreoffice-26-8`（WASM 原始碼樹，有本地修改）。**注意**：重現用的是 `native-lok-26-8/src`（同一個 commit `671c848b`，`git status` 是乾淨的）。兩棵樹的 `sw/source/filter/md/` 都沒有本地修改。

## 分析

讀原始碼（`sw/source/filter/md/mdcallbcks.cxx`，`671c848b`，該檔最後一次改動 `5505d3bc`）：`SwMarkdownParser::enter_span_callback` 對 `MD_SPAN_STRONG` 只放 `SvxWeightItem(WEIGHT_BOLD, RES_CHRATR_WEIGHT)`，對 `MD_SPAN_EM` 只放 `SvxPostureItem(ITALIC_NORMAL, RES_CHRATR_POSTURE)`。整個 `sw/source/filter/md/` 沒有任何 `RES_CHRATR_CJK_WEIGHT`、`RES_CHRATR_CTL_WEIGHT`、`RES_CHRATR_CJK_POSTURE`、`RES_CHRATR_CTL_POSTURE`（grep 為空）。

修法推論（**NOT VERIFIED — treat as a hypothesis**）：比照 HTML 匯入對 `<b>`／`<i>` 的作法，三組屬性一起放。

## 對我們的影響

v21 的「貼上為 Markdown」會帶著這個限制出貨，具名 **L-md-cjk-bold**（`specs/SPEC-M3-link-batch-v21.md` 4.2）。這一批核心不換，修不到。

## 還缺什麼才能送

- [ ] 在官方釋出版的桌面 LibreOffice 26.8 上用「選擇性貼上 → Markdown」重現，並截圖確認中文確實沒變粗（目前只看了存檔屬性，沒看顯示）。
- [ ] 查 master 是否已經修了（我們只有 26-8 分支）。
- [ ] 搜尋 Bugzilla 有沒有重複。
- [ ] 確認 Component（Writer）。
- [ ] 上游送出擱置中（記憶 `upstream-submissions-on-hold`）；重啟時先重查重複單。

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | Writer（送出前查證） |
| Version | 26.8.0.1 rc |
| Hardware / OS | x86-64 / Linux (Ubuntu 26.04) |
| Summary | Markdown import: bold/italic not applied to CJK and CTL text (only the Western weight/posture is set) |

## 時間軸

- 2026-10-16：v21 計畫的原生 Markdown 量測（臂 M8）看到存檔只有西文字重；主 session 讀原始碼確認、登錄。

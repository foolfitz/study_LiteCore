# SPEC R1-000：wasm_sdk_probe 總覽與執行協調

> **日期**：2026-08-01
> **狀態**：可執行 spec（v1）
> **目標讀者**：執行本計畫的 agents 與工程師
> **背景研究**：[SDK 主報告](../research/RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)、[COWASM 參考筆記](../research/RESEARCH-2026-08-01-cowasm-co-26-04-reference.md)、[協作編輯器報告](../research/RESEARCH-2026-08-01-wasm-collaboration-editor.md)

---

## 1. 目標（R1 技術閘門）

證明以下垂直切片可由 JavaScript 重複完成，不靠 Qt、不靠人工操作 WASM 內部 UI：

```text
ArrayBuffer → open ODT → paintTile 上 canvas → 程式化插入一個中文字 → save 出新 ArrayBuffer
→ 桌面版 LibreOffice 開啟驗證
```

並產出第一組 headless 產物的體積、時間與記憶體量測。

## 2. 子 spec 與執行順序

| Spec | 內容 | 依賴 | 預估 |
|---|---|---|---|
| [R1-A](./SPEC-R1-A-headless-build.md) | headless LibreOffice 26.8 WASM 建置 | 無 | 建置數小時（機器時間） |
| [R1-B](./SPEC-R1-B-probe-app.md) | 探針程式（C++ shim + 網頁測試頁） | 連結步驟依賴 A 的產物；**原始碼可在 A 建置期間先寫** | 1–2 個工作段 |
| [R1-C](./SPEC-R1-C-measurement.md) | 量測、驗收、報告 | A + B 完成 | 1 個工作段 |

建議並行方式：先啟動 A 的建置，同時進行 B 的原始碼撰寫；A 完成後 B 連結、冒煙測試；最後跑 C。

## 3. 全域硬性約束（所有 agents 必須遵守）

1. **不可修改 `libreoffice-26-8` worktree 的任何 tracked 檔案**。worktree 現有 5 個本地修改是工作現場（見 [INVENTORY.md](../wasm-lite/patches/INVENTORY.md)），保持原樣。若建置或探針需要改動 core 原始碼：**停止並回報**，不要自行修改。
2. `cool-26-04/`、`collabora-25.04/`、`/home/jiajun/LibreOffice/OxOffice` 為唯讀參考，禁止寫入；禁止複製其原始碼進探針（機制可學，程式碼不搬；COOL 程式碼已綁 COKit 命名，與上游 LOK 不相容）。
3. Emscripten 必須是 **4.0.10**（`emcc --version` 驗證）。系統另裝有 3.1.69，誤用會失敗。
4. 不啟用 `--with-yrs`、不用 JSPI、不用 PROXY_TO_PTHREAD、不連結 unoembind。
5. 不動 `wasm-lite/build-qt6-poc/`（Qt6 QA 線的建置目錄）；新建置一律在新目錄。
6. 遇到疑似 bug：依 `findings/TEMPLATE.md` 開 finding 記錄，證據放 `findings/evidence/`；不要在未記錄的情況下反覆試錯。
7. 新增檔案位置：建置在 `wasm-lite/build-headless-probe/`，探針專案在 `wasm_sdk_probe/`，報告依工作區慣例（`DEVLOG-*.md`、`findings/`）。

## 4. 已定案決策（不要重新討論）

| 決策 | 值 | 理由 |
|---|---|---|
| 實作基線 | 上游 LibreOffice 26.8 worktree @ `671c848b` | 研究定案 |
| 連結方式 | 核外連結（linkdeps），不進 gbuild | COWASM 生產驗證；SDK 報告 §8.1 |
| 執行緒 | `-pthread`；模組主執行緒 host、LOK 全在單一 engine pthread；無 JSPI | COWASM 組態；避開 Qt6 線地雷 |
| tile 像素格式 | `--enable-cairo-rgba`（RGBA 直餵 canvas） | Collabora 生產路徑；上游 26.8 configure 有此選項。與桌面 BGRA 的行為差異記入 QA 註記 |
| scripting | 維持預設（不加 `--disable-scripting`） | 探針減少變因；R5 減肥時再 A/B |
| 除錯資訊 | core 不開 symbols；探針連結加 `--profiling-funcs` | 保留可讀堆疊、控制連結時間；完整 DWARF profile 留待需要時 |
| 文件 I/O | 一律經 MEMFS（`FS.writeFile` → `file://` URL） | COWASM 模式；不發明記憶體直通 |
| CJK 輸入定義 | LOK API 程式化插入即算通過；真 IME 屬 R2+ | R1 閘門措辭（SDK 報告） |

## 5. 交接物（handoff artifacts）

- A → B：`wasm-lite/build-headless-probe/instdir/program/` 下的 `soffice.js.linkdeps`、`soffice.data`、`soffice.data.js.metadata`；`workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports`；`workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link`；以及 `PROBE-BASELINE.md` 建置清單。
- B → C：`wasm_sdk_probe/dist/` 下的 `probe.js`、`probe.wasm`、`soffice.data`（複製）；可操作的測試頁與 `run all` 自動流程。
- C → 使用者：`DEVLOG-<日期>-wasm-sdk-probe.md` + `findings/evidence/probe-r1/metrics.json` + Go/No-Go 判定。

## 6. 與 COWASM 的關係（避免執行時抄錯層）

照抄：linkdeps 連結配方、執行緒組態、MEMFS I/O、COOP/COEP 部署。
**不要抄**：wsd/kit 中間層、FakeWebSocket/COOL 協定、COKit headers、COOL browser UI。探針直接對上游 LOK（`include/LibreOfficeKit/`）。

## 7. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-01 | v1。依 COWASM 對照研究定稿；決策點（cairo-rgba、scripting）依建議定案。 |

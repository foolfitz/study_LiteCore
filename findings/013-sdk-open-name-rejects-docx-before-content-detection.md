# 013 — Document SDK 在 content detection 前拒絕 `.docx` 名稱，DOCX import 邊界與 bytes 能力不一致

| | |
|---|---|
| **狀態** | 已確認（專案 SDK 邊界） |
| **Bugzilla** | — |
| **發現日** | 2026-08-02 |
| **嚴重度** | 嚴重 |
| **可重現** | 100%（Chrome／Firefox R7-A 各 4/4 對照案例） |
| **是否上游** | 否（專案 SDK／C ABI policy） |

## 現象

公開 `DocumentEngine.open(bytes, { name })` 接受 caller 提供的名稱，但 R5 `writer-review` C ABI 只允許
名稱以 `.odt` 結尾。相同的合法 DOCX bytes 以 `plain.docx` 開啟會在進 queue 前得到
`INVALID_ARGUMENT`；把名稱改成不實的 `plain.odt` 則能 open、render、找到既有 anchor 並正常 close。

這不構成已承諾 ODT 能力的回歸，但否證「只靠現有 `OpenOptions.name` 即可安全擴成 DOCX import」的架構假設。
應用不可用偽造 `.odt` 名稱假裝完成 `open-docx`。

## 重現步驟

1. 執行 `make -C wasm_sdk_probe r7-discovery-assets`。
2. 執行 `python3 tools/run_r7_discovery.py --browser chrome --lifecycle-cycles 10 --crash-cycles 3`。
3. 比對 `docx-name-docx` 與 `docx-name-odt`，輸入 bytes SHA-256 都是
   `3f8c5645cc1925a5273b9697eb155420a3263008c804c9eb808c8e3a701708ce`。
4. 另比對 ODT bytes 的 `odt-name-odt` 與 `odt-name-docx`。

**預期**：若 public name 是格式辨識的一部分，合法 allowlisted DOCX 應有明確的 supported／unsupported
typed 結果，且 SDK 不要求 caller 偽造格式。  
**實際**：`.docx` 一律在 C ABI 前置驗證得到 `INVALID_ARGUMENT`；相同 DOCX bytes 配 `.odt` 名稱可完整讀取。

## 證據

- `evidence/sdk-r7/discovery/formats/chrome.json`
- `evidence/sdk-r7/discovery/input/chrome.log.txt`
- `evidence/sdk-r7/corpus/manifest-validation.json`
- Corpus manifest：`../wasm_sdk_probe/test-docs/r7/manifest.json`

關鍵 runtime 對照：

```text
odt-name-odt    opened=true  anchorFound=true
odt-name-docx   opened=false code=INVALID_ARGUMENT workerHealthy=true
docx-name-docx  opened=false code=INVALID_ARGUMENT workerHealthy=true
docx-name-odt   opened=true  anchorFound=true workerHealthy=true
```

## 分析

### 已觀察

- `src/sdk_api.cpp:67-82` 收到 `name` 後，若最後四字元不是 `.odt` 就同步回
  `OXSDK_STATUS_INVALID_ARGUMENT`；request 尚未進 engine queue。
- `src/probe_engine.cpp:478-489` 的 SDK input path 固定為 `/tmp/oxsdk-input-<request>.odt`。
- 公開 manifest 只宣告 `open-odt`，沒有 `open-docx`；因此不能把「偽裝名稱可讀」升格為產品能力。
- 合法 ODT baseline、corrupt ODT/DOCX、unknown bytes 的 Worker health probe 均可恢復，沒有 silent content
  loss 或 Worker 不可復原。

### 推論

- LibreOffice content detection 能在固定 `.odt` path 下辨識這份最小 DOCX，但這不保證完整 DOCX corpus，
  也不能代表 extension/filter policy 已正確設計。
- 若 R7-C 要支援 DOCX，最小安全改動應是 allowlisted `format: "odt" | "docx"` 或等價 safe extension，
  讓 validation、實際 MEMFS path、manifest capability 三者一致；不能公開任意 path 或 raw filter 名稱。

### 待驗證

- ~~Firefox 是否得到相同 4-case classification。~~ 已確認與 Chrome 一致。
- 以窄 `format` surface 修正後，完整 R7-C DOCX corpus 是否能 open／render／search 且 DOCX → ODT save
  不發生 silent loss。
- 是否需要獨立 DOCX artifact/profile，或現有 `writer-review` filters 已足夠。

## 影響與目前決策

- R7-A 最多 **部分 GO**：ODT、host input、typed negative 可以成立；DOCX 保留 unsupported／finding。
- R7-A 不修改 SDK/core；若後續要改 surface，須另列精確範圍與驗證矩陣後再執行。
- 不新增 `open-docx` capability，不以 `name: "*.odt"` 包裝 DOCX bytes 對外宣稱相容。

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- writer-review loader：`35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566`
- writer-review WASM：`ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`
- Chrome：`150.0.7871.128`
- Desktop LibreOffice：`26.2.4.2`

## 還缺什麼才能關閉

- [x] Firefox 重現並保存 evidence。
- [ ] 決定 R7-C 是 ODT-first typed unsupported，或另授權窄 SDK `format` 修正。
- [ ] 若修正，驗證 public/C ABI/path/capability 一致與 R1～R6 回歸。

## 時間軸

- 2026-08-02：R7-A Chrome discovery 首次以相同 bytes／不同 name runtime 對照確認；建立 finding。
- 2026-08-03：Firefox 152.0.6 得到相同四案例結果，跨瀏覽器確認。

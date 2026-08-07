# 011 — Document SDK Worker 將 search-not-found 純文字 payload 當 JSON 解析

| | |
|---|---|
| **狀態** | 已修（Chrome／Firefox） |
| **Bugzilla** | — |
| **發現日** | 2026-08-02 |
| **嚴重度** | 嚴重 |
| **可重現** | 修補前 Chrome 1/1；修補後 Chrome／Firefox 2/2 通過 |
| **是否上游** | 否（我方 Document SDK Worker adapter） |

## 現象

以 R5 `writer-review` 呼叫公開 `DocumentHandle.search()` 搜尋不存在的文字時，應回傳
`{ found: false, selections: [] }`，實際卻得到 typed `RESULT_PARSE_ERROR`。這會讓 reader 無法區分正常的
零命中與 Worker／協定錯誤，也使 R6 無法安全產生 `ANCHOR_NOT_FOUND`。

## 重現步驟

1. 以 R5 `writer-review` Worker 開啟 `t1-plain-zh.odt`。
2. 呼叫 `documentHandle.search("R6-ANCHOR-DOES-NOT-EXIST")`。
3. 保存 public Promise rejection 與 browser log。

**預期**：`found=false`、`selections=[]`，revision 不變。  
**實際**：Worker 對純文字 `R6-ANCHOR-DOES-NOT-EXIST` 執行 `JSON.parse()`，回覆
`RESULT_PARSE_ERROR`。

## 證據

- `evidence/sdk-r6/discovery/chrome.json`
- `evidence/sdk-r6/discovery/chrome.log.txt`
- `evidence/sdk-r6/discovery/chrome.png`

關鍵錯誤：

```text
RESULT_PARSE_ERROR: search returned invalid JSON:
Unexpected token 'R', "R6-ANCHOR-"... is not valid JSON
```

## 分析

### 已觀察

- `probe_engine.cpp` 對 `LOK_CALLBACK_SEARCH_RESULT_SELECTION` 與
  `LOK_CALLBACK_SEARCH_NOT_FOUND` 都把 callback payload 放入 `resultPayload`。
- 成功 callback 的 payload 是含 `searchResultSelection` 的 JSON；not-found callback 的 payload 是搜尋字串。
- R5 `sdk-worker.js` 在 `search-result` 分支只判斷 `resultPayload` 是否存在，未先判斷 `event.found`。

### 推論

這是我方 Worker adapter 對兩種穩定 LOK callback 語意正規化不完整，不是 LibreOffice core bug。最窄修正
是在 `event.found === true` 時才解析 JSON；not-found 直接正規化為空 selections。

### 待驗證

- Chrome／Firefox 真實 R5 core artifact 都回傳 `found=false`、空 selections。
- 修正不改變成功搜尋、selection text、revision 或既有 R1～R5 flow。

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- R5 writer-review WASM：`ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`
- Chrome：`150.0.7871.128`
- SDK／Worker protocol／C ABI：`0.5.0-r5`／1／1.1

## 結案驗證

- [x] Chrome 修補後真實 search-not-found 通過
- [x] Firefox 修補後真實 search-not-found 通過
- [x] R1～R5 regression 通過（R6 最終回歸）

## 時間軸

- 2026-08-02：R6-A discovery 首次在真實 artifact 重現。
- 2026-08-02：加入 R6 專用 Worker 修正；不覆寫 R5 封存 profile。
- 2026-08-02：Chrome 150／Firefox 152 的 unique、not-found、ambiguous checkpoint 通過。
- 2026-08-02：R5 review／reader、Provider、R3、R2、R1 回歸全數通過；finding 結案。

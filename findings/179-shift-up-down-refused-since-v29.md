# 179 — v29 起 Shift＋上下／Home／End 全被 worker 拒絕

| | |
|---|---|
| **狀態** | 已確認（修法見 SPEC-P-demo-batch-3 第 2 節） |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-11-02（擁有者手測 0.2.49） |
| **嚴重度** | 嚴重：出貨功能整組失效，紅字 toast 是開發者句子 |
| **可重現** | 100%（Chrome 鏡像，每按必現） |
| **是否上游** | 否（我方 worker） |

## 現象

Writer 裡 Shift＋←→ 可以選取，Shift＋↑↓、Shift＋Home、Shift＋End 跳紅字：

> 下移一行：INVALID_ARGUMENT：editorActionV2 requires a closed action and typed options

游標不動，文件不變。

## 重現步驟

1. 開任何 Writer 文件，點進內文。
2. 按 Shift＋↓。

**預期**：選取延伸一行。
**實際**：紅字 toast。Worker 回 `INVALID_ARGUMENT`，請求沒有到引擎。

## 分析

`sdk/v28-last-block-worker.js:181`：

```js
function featureExtendPermitted(action) {
  return activeManifest?.profile === "e2-editor-v28"
    && activeManifest?.editorContract?.abiVersion === 6
    && EDITOR_V23_EXTEND_ACTIONS.has(action);
}
```

v23 到 v28 每一版都改這個名字（規格的 worker 差異清單第 1 項）。v29 只改引擎，Makefile 寫「v28's worker source, byte-identical: this batch changes no wire behaviour」，於是 worker 沒換，名字留在 v28。**「沒改 wire 行為」的前提是假的：worker 的行為取決於 manifest 的 profile 名字，而 manifest 換名了。**

頁面看的是 `offersSelectionMove`，client 看的是 manifest，兩者都說可以；只有 worker 拒絕。左右不受影響，因為它們也在 `EDITOR_V1_MOVE_ACTIONS` 裡。

普查：v29 worker 裡比對 profile 名字的閘門只有這一個，shell 與頁面沒有（`grep`，2026-11-02）。

## 為什麼這麼久沒人看到

- 0.2.44（v28）還是好的，0.2.45（v29）起壞掉（各版 `release.json`），所以名義出貨版 0.2.45 帶著它。K 成立，因為 K 不量 Shift＋上下。
- `v28_feature_worker_test.cjs` 有 `extendPermitted` 這一格，但它把 manifest 的 profile 改成 `e2-editor-v28` 再測，測的是名字對的情況。v29 沒有對應的測試，因為「worker 沒變」。
- S1–S5（v23）的判準在 v23 上量過，之後每一版沿用，沒有重量。這是第 1 節「手工枚舉」的形狀：閘門住在別處，換 profile 不會讓任何檢查變紅。

## 修法

SPEC-P-demo-batch-3 第 2 節：`e2-editor-v30`，引擎位元組等於 v29，閘門不再比對名字；加逐實例檢查 `tools/check_extend_gate_instances.py`，新 profile 自動被量到。

## 證據

- 重現與修復：`evidence/demo-batch-3/shift-lines/`。

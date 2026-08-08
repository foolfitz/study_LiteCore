# 026 — 「每頁 Worker generation 上限」在規格與產品裡是兩個不同的量；產品端從未實作「每頁」

| | |
|---|---|
| **狀態** | 已確認（程式碼 ＋ E1-C 既有證據 ＋ 2026-08-08 新量測三方一致） |
| **發現日** | 2026-08-08（準備把上限由 3 改成 16 時，清點實際生效點才發現） |
| **嚴重度** | 一般偏高：規格對外承諾的性質與產品實際保證的性質不同，而且前者無人執行 |
| **可重現** | 100 %（不需重現，是靜態事實＋既有證據） |
| **是否上游** | 否，我方 |

## 一句話

規格寫的是**「每頁 Worker generation 上限為 3」**，產品唯一實作的是
**「每個 `EditorSession` 最多回復 2 次」**。兩者在「一個頁面只有一個 session」時碰巧
重合，其餘情況完全不同——**而產品沒有任何東西在數「每頁」**。

## 兩個量（已觀察）

| | 意義 | 誰在數 | 越界會怎樣 |
|---|---|---|---|
| **A：每個 session 的回復次數** | 首次 `open()` 算第 1 代，之後每次 `restart()` ＋1。`restart()` 只能從 `restart-required`／`recoverable-error` 進入，也就是**崩潰或 boundary 之後** | `editor-shell/editor-session.js:32,85`（`options.maxWorkerGenerations ?? 3`） | 丟 typed `WORKER_GENERATION_LIMIT`、`details.requiresPageReload: true` |
| **B：每頁的引擎實例化次數** | 一個頁面裡總共建了幾個引擎 worker，**不分屬於哪個 session** | 只有 harness：`web/e1-editor-validation-app.js` 的 `metrics.workers.created`、`tools/run_r8_production.py:307-320`、`tools/run_r7_compatibility.py`、`tools/run_r7_longevity.py` | 只影響測試怎麼切批；**產品側沒有任何檢查** |

規格條文（`SPEC-E1-C` §C2／§105、`SPEC-E1-A` §4 等）寫的是 **B**。
產品程式碼實作的是 **A**。

`close()` 會把 session 轉到 `closed`，而 `open()` 要求狀態是 `idle`——**同一個 session
關掉就不能再開**。要開下一份文件就得 `new EditorSession(...)`，而
`editor-session.js:65` 的 `this._generation = 0` 讓計數器歸零。
所以**一個頁面連續開 10 份文件 ＝ 10 次引擎實例化，而每個 session 的計數器都是 1**，
A 完全不會擋。

## E1-C 既有證據自己就說明了這件事（已觀察）

把 48 個 case 的 `result.json` 全掃一遍，每個 scenario 取最大值：

| scenario | 每頁 worker 建立數 | 觀察到的最大 generation |
|---|---|---|
| `integration` | 1 | 0 |
| `lifecycle` | 1 | 1 |
| `corpus` | 2 | 0 |
| `crash-preedit`／`crash-queued`／`crash-saved`／`crash-unsaved` | 2 | **2** |
| `boundary-start`／`boundary-table` | 2 | **2** |

**generation 只在崩潰／boundary 回復時前進，而且從來沒有超過 2。**
上限 3 允許的是「一個 session 撐過 2 次回復」——**E1-C 從來沒有把它逼到過**，
連它自己設定的 3 都沒碰到。

而 `lifecycle` 那 10 個 case 是 `run_e1_c.py` 的 10 次 `session.navigate()`，
**一頁一代**，所以 B 也從來沒有被驗證過。

## 這使得下列說法失效

- 我在 2026-08-08 對使用者說過「上限 3 的痛點是**使用者編到第四份文件就會被要求整頁重載**」。
  **這是錯的。**上限 3 從不管開幾份文件；它管的是**一個 session 能從崩潰中回復幾次**。
- 因此「放寬到 16 讓使用者不會被踢出去」這個理由**不成立**：16 的實際意思是
  **「一個 session 可以連續崩潰 15 次而不要求重新載入」**，那多半是更差的產品行為，
  不是更好的。崩潰反覆發生時，要求重新載入正是安全的反應。
- [finding 014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) 撤回的是
  **B** 的理由（Firefox 每頁 worker 累積）。它對 **A**（回復深度該給幾次）**一句話都沒有說**。
  A 的取值是產品可靠性決定，與 014 無關，也不因 014 撤回而需要改變。

## 順帶量到的：產品 artifact 在 A 這條軸上撐得住 16（已觀察）

既然要判斷 A 能不能放寬，就在**出貨的 `e1-editor-v1`**（wasm `835b453d…`）上量了一次
——這是第一次有人在產品 artifact 上把世代數逼到 1 以上。新增 `scenario=generations`：
同一個頁面裡連續「故意讓 worker 崩潰 → `restart()`」，直到第 N 代，再多崩一次確認仍被擋。

| | Chrome 150 | Firefox 153.0.1 |
|---|---|---|
| 達到世代 | **16／16** | **16／16** |
| worker | 16 建 16 拆（16 次故意崩潰） | 16 建 16 拆 |
| `restart()` 耗時 | 918～1610 ms，**無上升趨勢** | 1846～2312 ms，**無上升趨勢** |
| 第 17 次回復 | `WORKER_GENERATION_LIMIT`、`requiresPageReload: true` | 同左 |
| 單頁總時間 | 20.3 s | 35.7 s |

**技術上 A 可以放寬到 16，且放寬後仍然 fail-closed。**能不能放寬是產品決定；
本檔只確認「技術上做得到」與「fail-closed 沒被拿掉」。
證據：`findings/evidence/sdk-e1/editor-validation/session-depth/generations/{chrome,firefox}/result.json`。

## 兩個假閘門（已確認，需修）

清點時另外發現兩個**永遠不可能失敗**的檢查——不是數字錯，是**根本沒在量**：

| 位置 | 內容 | 為什麼是假的 |
|---|---|---|
| `tools/run_r8_production.py:634,656` | `worker_generations = 4`，然後 `pass` 條件含 `worker_generations <= (4 if browser == "firefox" else 8)` | 拿字面值 `4` 去比 `4`。**恆真** |
| `tools/run_r8_production.py:640` ＋ `tools/validate_r8_d.py:87` | 寫入 `"maxWorkerGenerationsPerPage": 3`，validator 檢查 `<= 3` | 同上，**恆真** |

R8-D 的 `boundedWorkerGenerations`／`boundedWorkerGenerationsPerPage` 兩個性質因此
**從來沒有被驗證過**，不論上限訂多少。這與上限的取值無關，是獨立的證據完整性缺陷
（同型於 [finding 025](025-webdriver-script-injection-never-ran-on-firefox.md) 與
`run_r7_compatibility.py:232` 寫死 `workerBudget` 的問題：**不能印出不同值的探針不是探針**）。

`e1/validation-matrix-v1.json` 的 `maximumWorkerGenerationsPerPage: 3` 與
`requiredProperties` 裡的 `bounded-worker-generation` 則是**純宣告**——
`validate_e1_c.py` 只檢查矩陣的 `schemaVersion`／`release`，**沒有任何程式讀那個門檻**。

## 產品面該怎麼收（待決定，不在本檔擅自決定）

1. **A（回復深度）**：預設 3 沒有已知理由要改。若要改，理由必須是可靠性論證，不是 014。
2. **B（每頁引擎實例化）**：若規格要繼續承諾它，產品就得**真的去數**——目前是零實作。
   014 撤回後，B 也沒有已量測的記憶體或 worker 名額理由（見 014〈待驗證 10 結案〉：
   閒置 240 秒後回到 624.6 MB；單頁 100 代全過）。**最省的收法可能是把 B 從條文刪掉，
   而不是給它一個數字。**
3. 兩個假閘門要改成真的量測，**無論 1、2 怎麼決定**。

## 待驗證

1. B 若要保留，產品側計數器該掛在哪一層（engine factory？頁面層 registry？）尚未設計。
2. 本檔只量了 A＝16；A 的上界沒量（不需要，除非要訂更大的值）。

## 證據

- `findings/evidence/sdk-e1/editor-validation/session-depth/generations/chrome/result.json`
- `findings/evidence/sdk-e1/editor-validation/session-depth/generations/firefox/result.json`
- `findings/evidence/sdk-e1/editor-validation/`（48 case 的既有 `result.json`，掃描結果見上表）
- `editor-shell/editor-session.js:32,65,68-80,83-98,373-381,411-423`

## 修訂紀錄

- 2026-08-08：建檔。起因是準備執行「上限 3 → 16」時清點實際生效點，發現規格與產品
  在數不同的東西；連帶更正我自己先前對使用者說的「第四份文件會被踢出去」。

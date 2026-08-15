# 044 — 判定綁定的 `summary.json` 到今天還寫著「E2-A 仍無總判定」

| | |
|---|---|
| **狀態** | **已確認／未修**（修法要重跑 validator 覆寫判定綁定的檔案，需刻意為之） |
| **Bugzilla** | —（我方文件與工具，不是上游） |
| **發現日** | 2026-08-15（做任務 #49 的 v23 修訂時順帶撞到） |
| **嚴重度** | 中——**機器可讀的那一份與規格互相矛盾**，照它做決定的人會得到相反的答案 |
| **可重現** | 100%，讀檔即見 |
| **是否上游** | 否 |

## 摘要

`findings/evidence/sdk-e2/summary.json` 是 E2-A 判定綁定的那一份摘要。
它的 `notValidated` 欄位到 2026-08-15 為止仍然寫著：

```
"A6 secondary capabilities have not run."
"A7's round-trip slice has run …; A7's regression half … has not,
 so A7 as a whole is still unmet and there is still no E2-A verdict."
```

**兩句都是假的**：

| 那句話說 | 實際 |
|---|---|
| A6 沒跑過 | **2026-08-13 已執行**（兩項維持 unsupported，不列入判定），SPEC E2-A 第 5 節 A6 註記 |
| A7 的回歸半沒跑，**所以 E2-A 仍無總判定** | **A7 已完成**（round-trip 10.12、回歸 10.13），**總判定 2026-08-14 已發＝`PARTIAL_GO_TO_E2_B`** |

字串來源是 `wasm_sdk_probe/tools/validate_e2_a.py:445`–`452` 裡寫死的清單。

## 為什麼這不只是「文件過期」

規格是人讀的，`summary.json` 是**工具讀的**。
`validate_e2_a.py` 自己就把這一份當成「E2-A 目前的狀態」寫出來，
finding 027 的整套紀律也是建立在「判定綁定的檔案就是判定」這件事上。

所以現在的狀況是：**同一個專案裡，人讀的那份說判定已發，機器讀的那份說判定沒發。**
任何自動化的下游（例如 E2-B 的進場檢查）若去讀後者，會得到「不能往前走」。

## 為什麼還沒修

修法是**改 `validate_e2_a.py` 的字串並重跑一次**，讓它覆寫
`findings/evidence/sdk-e2/summary.json`。這有前例：v16 那次就是這樣做的
（規格修訂紀錄：「`validate_e2_a.py` 的 `notValidated` 與 `narrowings` 兩句已就地改寫並重跑，
三個判定逐位元不變」）。

**但那是覆寫一個判定綁定的檔案**，要當成刻意動作來做，不是順手：

- 重跑必須用**發判定時同一支**工具與同一棵證據樹（`c89f069e`），
  且三個 `decision` 必須逐位元不變——**不變才證明改的只有敘述**。
- 執行前後要記 `summary.json` 的 sha256。
- 這件事**與任務 #49 無關**，#49 期間對它的唯一互動是
  「確認它沒有被我動到」（前後 hash 都是 `1dfc3df3363f3f69…`）。

## 順帶

`narrowings` 欄位只有兩條（縮限 2 與 3），**沒有**縮限 4，
所以 2026-08-15 撤掉縮限 4 這件事**不需要動這個欄位**——這是查過的，不是假設的。

# 046 — 讀回什麼都沒有時，引擎回報的是「文件不是你要的狀態」

| | |
|---|---|
| **狀態** | **已確認（出貨 v2 實測 ＋ 原始碼對照）／未修，列入下一次 relink** |
| **Bugzilla** | —（**不是上游缺陷**） |
| **發現日** | 2026-08-15（E2-C D2 第一次執行） |
| **嚴重度** | **嚴重**——觸發手勢是「在空白行上按項目符號」，而後果是 host 回滾、丟掉自 checkpoint 以來的編輯 |
| **可重現** | 100%（Chrome，出貨 profile `e2-editor-v2`） |
| **是否上游** | **否——我方 barrier 的分類** |

## 摘要

在**空段落**上派送 `set-list-unordered`，出貨 v2 回：

```json
{"code": "EDITOR_FORMAT_POSTCONDITION_FAILED",
 "failureShape": "postcondition-not-met",
 "dispatched": true, "preBlocks": 0, "postBlocks": 0}
```

**`postBlocks: 0` 的意思是「這次讀回沒有描述任何一個段落」**，
而不是「文件處在錯的狀態」。引擎把前者回報成了後者。

barrier 自己的註解就寫著這個區別（`probe_engine.cpp:3488`）：

> 「前兩個說的是**讀回沒有描述一個已知的段落，所以關於後置條件根本沒有任何判斷
> 可用**；只有兩個都成立之後，『它在不在目標狀態』才是個問題。」

**零個 block 的讀回正是那個情形，但它掉進了後置條件的判決。**

## 為什麼這件事會咬到人

`EDITOR_FORMAT_POSTCONDITION_FAILED` 帶 `dispatched: true`，於是
`formatFailureDisposition()` 回 `dispatched-rollback`，
而 `recoveryFor()` 把它變成 **rollback**——host 會**從 checkpoint 重開，
丟掉自那之後的所有編輯**。

**觸發它的手勢是「在空白行上按項目符號」。** 那不是邊角情形。

而且訊息本身是錯的：「the document does not show the state this action asked for」
——**沒有人看過文件**。

## 機制（原始碼層級）

| 位置 | 做什麼 |
|---|---|
| `probe_engine.cpp:3562` | `if (!formatBarrierReadbackSatisfied())` → `postcondition-not-met` ＋ `EDITOR_FORMAT_POSTCONDITION_FAILED` |
| `:3408-3430` | `formatBarrierReadbackSatisfied()`：`expectedListTag` 是 `"ul"`，讀回的 `listTag` 是空的 → 觀察值 `"none"` ≠ `"ul"` → 回 false |
| `:3416-3419` | 它確實會擋掉 `unknownTag`／`malformedNesting`／`footnoteApparatus`／型態守衛——**但沒有擋 `blockCount == 0`** |

**所以「什麼都沒讀到」與「讀到了、而且是錯的狀態」走同一個出口。**

## 與 SPEC E2-B 2.3 的表對不上

那張表把**空段落**列在「**派送前拒絕**（零 mutation）」那一類，
`EDITOR_FORMAT_*`、「**沒有發生**」。

**出貨的引擎沒有任何空段落的派送前檢查**——三個 `EDITOR_FORMAT_*` 碼分別是
`POSTCONDITION_FAILED`（派送後）、`GESTURE_UNSUPPORTED`、`SELECTION_NOT_READABLE`
（兩個派送前，都與空段落無關）。那一列**繼承自 E2-A 的 discovery 流程**
（當時還會讀前置狀態），路線 C 之後就不成立了，而沒有人回頭改。

**兩件事因此都要修**：引擎的分類，以及那張表。

## 修法（列入下一次 relink）

讀回**解析成功但一個 block 都沒有**時，回
`MUTATION_OUTCOME_UNKNOWN`＋自己的 shape（`empty-readback`），
而不是 `POSTCONDITION_FAILED`。理由是那正是 barrier 自己寫下的規矩：
**沒有描述到一個已知段落，就沒有關於後置條件的判斷可用。**

處置也跟著對：`MUTATION_OUTCOME_UNKNOWN` 仍然是 rollback（fail closed，
因為確實派送了），但**訊息不再宣稱看過文件**，而 host 也不再被告知
「文件是錯的狀態」這個沒有根據的說法。

> **這一項是「D2 要在 relink 之前寫」那個要求的直接產物。** 對抗性審查說
> D2 是最可能再長出引擎佇列項的地方；它第一次跑就長出了這一個。

## 還缺什麼

- [ ] 修完之後在 v3 上重測，並補一格**空段落**進第二輪的矩陣。
- [ ] 空段落在**文件最後一段**的情形另有一條已知路徑
      （`.uno:SelectText` 不回選取回呼 → stage deadline，`:718-735`）——
      要確認修法之後那一格仍然落在 `stage-deadline:*` 而不是被新的 shape 蓋掉。
- [ ] 改 SPEC E2-B 2.3 的表（**既有草稿不回頭改**那條規矩管的是 Bugzilla 草稿，
      規格是活文件，就地修訂即可）。

## 證據

`findings/evidence/sdk-e2/e2-c-validation/d2-presweep/`（D2 的掃描輪），
`d2-refused-no-mutation-engine` 那一格。

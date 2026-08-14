# P2：**預先寫下的失敗分支 (i)**——它會返回，但**什麼都沒選到**

**日期**：2026-08-15
**artifact**：`e2-combination` ＝ **`ba1a5dd5…`**
（不是 `938b4ff3…`，原因見 [finding 042](../../../../../042-editing-the-makefile-relinks-every-artifact-that-depends-on-it.md)）
**控制**：`e2-format-discovery` ＝ `c89f069e…`（凍結、封存）
**預測**：[../PREDICTION.md](../PREDICTION.md)，寫在任何一次執行之前

## 判定：**縮限 4 留著。E2-B 的進場條件沒有滿足。**

P2 預先寫下三種結局，實際落在第二種：

| 預先寫的 | 實際 |
|---|---|
| 具名完成 ＋ 回報選取吻合 | — |
| **具名完成但回報的選取不吻合（空的、或別的範圍）** | **← 就是這個** |
| 超過已武裝的期限仍逾時 | — |

處置也是預先寫好的：「**功能性失敗：縮限 4 留著，改寫成『會返回但沒選到』**」。

## 量到的

同一顆 artifact、同一份 `list-contexts.odt`、同一個 `set-list-unordered`、同一組座標，
**只差哪一個進入點發出選取**：

| arm | range-2 的結果 | 事後回報的選取 |
|---|---|---|
| `arm8-discovery`（discovery ABI） | **逾時 10 000 ms** | — |
| `arm8-product`（產品 ABI） | 完成，`verified-selection-readback`，**251 ms** | **`none`，空字串** |

**而歸因控制就在同一輪裡**：

| arm | 結果 |
|---|---|
| `select-y2600-without-format`（同一個選取，**前面不做格式動作**） | 完成，`documented-callback-text-selection`，**20 ms**，選到 **`"moji 😀 graphe"`（14 字）** |

所以 y=2600 那一行有文字、座標是對的、選取本身做得到——
**是那個格式動作讓它選不到東西**。

**Firefox 逐格相同**（同一顆 artifact）：`arm8ProductSelectionType` 為 `none`、
控制臂選到同一串 `"moji 😀 graphe"`、標籤分區同樣是 callback／readback、
控制臂之外零逾時。**所以這不是 Chrome 特有的。**

> **這一格是我漏掉、事後補的。** 第一版沒有這個控制，只有「格式動作之後選到 `none`」。
> 那個讀數和「y=2600 是空行」**長得一模一樣**，我原本就要據此寫結論了。
> 補上之後結論沒變，但在補上之前它不成立。

## 所以 bounded readback 到底做了什麼

**把「掛住」換成「誠實地說沒選到」**，這是真的改善，但**不是修好**：

- 引擎不再卡：`repeat-composition` 三輪的 `state-N` 每次都完成（1 ms），
  `gEditorPending` 有清掉，沒有 BUSY 連鎖。
- 但那三輪的 `select-N` **全部是 251 ms 的 readback**——也就是**三次都沒選到東西**。
  `repeatAllCompleted: true` 量的是**存活**，不是**成功**，引用時不要當成後者。

**底下的缺陷原封不動**：一個格式動作之後，範圍選取選不到東西。
E2-B 若照現況出貨，使用者得到的是「格式化一次，選取路徑就死了」——
只是從**卡死**變成**大聲地失敗**。

## 判準用的是回報的狀態，不是「呼叫返回了」

這正是 `probe_engine.cpp:1556`–`1559` 對這個 completion 自己寫的話，
也是裁決訂的驗收判準。如果只看 `arm8ProductCompletes: true` 就會得到相反的結論。

## 這一輪成立的其他事

| | |
|---|---|
| **鑑別控制** | 工具**先在封存的 `c89f069e` 上重現了第 8 臂的逾時**，然後才在新 artifact 上跑。`arm8ReproducesOnDiscoveryPath` 在**兩顆 artifact 上都是 true**——combination 上 discovery 那條**照裁決仍然不 buffered**，這是設計，不是遺漏 |
| **標籤分區** | `changing` → callback 19 ms／`same-again` → readback 251 ms，而且那一輪事後選到 `"ASCII abc XYZ"`。**沒有格式動作時，選取是好的** |
| **v2 主手勢** | `click-gesture` 三輪全過（格式 → click＋輪詢 → 格式）。**這是第一次在編進 barrier 的情況下量它** |
| **harness 逾時** | 控制臂之外為 **0** |

## 這一輪不宣稱

- **不宣稱 039 被修好或沒被修好**——按裁決，discovery 那條本來就留著。
- **不宣稱 A3／A4／A5（P3）的結果**：還沒跑。
- **不宣稱這是產品 `835b453d` 的行為**：出貨編輯器**沒有編進 format barrier**，
  所以這個組合在今天的產品上不存在。

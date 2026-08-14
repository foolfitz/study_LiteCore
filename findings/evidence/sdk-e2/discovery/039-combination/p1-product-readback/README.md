# P1：**結局 A**——出貨 artifact 上的 bounded readback 真的會動，而且 251 ms

**日期**：2026-08-15　**artifact**：`e1-editor-v1` ＝ `835b453d…`（**凍結，沒有任何重建**）
**預測**：[../PREDICTION.md](../PREDICTION.md)，**寫在這一輪之前**
**瀏覽器**：Chrome 與 Firefox，**逐格相同**

## 為什麼要跑這一輪

Option C 的整個前提是一句**只讀過程式碼、沒有量過**的話：
「finding 039 要的機制早就實作好也出貨了，只有 discovery 那個進入點不去武裝它。」
（`editor_api.cpp:123` 傳 `boundedReadback=true`、`editor_discovery_api.cpp:58` 沒有、
`probe_engine.hpp:69`–`72` 說那是刻意的。）

**前提垮了，整條路就要重議**，所以裁決把這一輪排在任何原始碼改動之前。

## 結果

| arm | 步驟 | completion | 耗時 |
|---|---|---|---|
| `five-selects` | select-1 … select-5 | 全部 `documented-callback-text-selection` | 9／9／9／10／9 ms |
| **`identical-range-twice`** | select-R | `documented-callback-text-selection` | 9 ms |
| | **select-R-again（同一個範圍）** | **`verified-selection-readback`** | **251 ms** |
| `changing-range` | select-half → select-full | 兩次都 `documented-callback-text-selection` | 9／10 ms |

Firefox 逐格相同（9／10／10／10／10、9 → **251**、9／10）。

**`changing-range` 是讓上一列讀得懂的對照**：如果沒有它，「readback 有動作」也可能只是
「這顆 build 把每一次都標成 readback」。實測是**會變的選取走 callback、不會變的走 readback**
——判準本身變成可觀察的。

## 判準是回報的選取，不是「呼叫返回了」

`probe_engine.cpp:1556`–`1559` 自己就這樣寫，所以每一臂都讀回選取：

- `identical-range-twice`：第一次之後 `"ASCII abc XY"`（12 字），
  **第二次之後一模一樣**，之後再讀一次還是一樣（`stillUsable`）。
  **所以那個 bounded completion 沒有說謊，也沒有把 pending slot 卡住。**
- `changing-range`：`"ASCII abc XYZ 0123456789"`（24 字），選取確實變寬了。

## 251 ms 那個假說：**成立**

finding 039〈影響〉列的產品五次是 112／19／**251**／8／10 ms，我在 08-15 把
「251 很接近 250 ms 期限」記成**未證實的假說**。

**現在直接量到了**：`EditorSelectReadbackDeadlineMs` ＝ 250，而「同一範圍再選一次」
這一格在兩個瀏覽器上都是 **251 ms ＋ `verified-selection-readback`**。

> **但不要把這一輪當成那五個數字的補證。** 我跑的是不同的序列（不同 span、不同 arm），
> **原本那一串 112／19／251／8／10 仍然沒有證據檔**。
> 這一輪落地的是**機制**，以及 251 ms 這個時間確實出自那條路徑。

## 這一輪不宣稱

- **不宣稱 039 修好了**——什麼都沒改，這是量測。
- **不宣稱 discovery profile 會有同樣行為**——它刻意不武裝這條路，那正是 039。
- **不宣稱 P2／P3**：barrier 與這條 select 共存的組合**還不存在**，見 [../PREDICTION.md](../PREDICTION.md)。

## 過程中修掉的一個 harness 坑

第一次執行失敗在 `Chrome page did not finish loading`。原因不是頁面壞掉：
`ChromeSession.navigate()` 要等 `globalThis.__probe_metrics` 出現才算載入完成
（`tools/run_browser_probe.py:281`），而我只發佈了自己的名字。
**兩個名字都掛上**之後就通了；註解寫在 app 裡，免得下一個人再踩。

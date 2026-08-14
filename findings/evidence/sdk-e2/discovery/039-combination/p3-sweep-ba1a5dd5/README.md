# P3：A3／A4／A5 在組合 artifact 上**全部通過**

**日期**：2026-08-15（02:04 跑完，41 輪，每一輪 runner 都是 exit 0）
**artifact**：`e2-combination` ＝ **`ba1a5dd5…`**
**判定工具**：`tools/validate_e2_a.py`——**跟當初發判定用的是同一支**，
只多一個 `--profile` 讓它拿組合 artifact 的 hash 去比對綁定
**預測**：[../PREDICTION.md](../PREDICTION.md) 的 P3，寫在執行之前

## 結果

| | `c89f069e…`（凍結） | **`ba1a5dd5…`（組合）** |
|---|---|---|
| A3 | **A3_PASS** | **A3_PASS** |
| A4 | **A4_PASS** | **A4_PASS** |
| A5 | **A5_PASS** | **A5_PASS** |
| gaps | — | **`{}`（空）** |

六個 A3 格子（3 fixture × 2 瀏覽器）全部 `state: covered`、
`required 3 / found 3 / bound 3 / passing 3 / superseded 0`。
A4 六格同樣 3/3，A5 八格 1/1。

## 「原尺寸」要講清楚，不然這張表會被讀錯

| | 凍結 | 組合 |
|---|---|---|
| A3 | 25 runs／125 次派送 | **18 runs／90 次派送** |
| A4 | 18／270 | **18／270** |
| A5 | 8 | **8** |

**A3 的數字不同，不是覆蓋變少。** 凍結那棵樹每個格子的 `bound` 是 8／5／3／3／3／3
（合計 25），因為 chrome 的兩個 fixture 當初多跑了幾次；門檻本來就是 **3**，多的是**盈餘**。
我這一輪每個格子剛好跑 3，所以 18 runs、每輪 5 次派送 ＝ 90。

**每一輪的派送數兩邊都是 5，格子的判定兩邊都是 covered。**
要說「原尺寸通過」，指的是**要求的重複數在每一格都達成**——那成立；
直接拿 125 對 90 說「覆蓋掉了三成」是錯的讀法。

## 所以 P3 說了什麼、沒說什麼

**說了**：把產品的 select ABI 和 format barrier 編進同一顆 artifact，
**沒有改壞共用引擎**——A3／A4／A5 三套矩陣在它上面的行為與凍結 artifact 一致。

**沒說**：這不代表 E2-B 可以凍結 ABI。**P2 已經擋住**（格式動作之後的選取會返回但選不到東西，
見 [`../p2-composition-scan-ba1a5dd5/`](../p2-composition-scan-ba1a5dd5/README.md)）。
P3 的用途是排除「組合本身把別的東西弄壞了」這個可能，它排除掉了。

## 過程中的兩個坑，都記在別處

1. **第一次 sweep 寫進了判定綁定的證據樹**：`--evidence-root` 對 keyed 模式會
   `.parent.parent` 走回 `browser/chrome/styled-list/`，於是組合 artifact 的 run 變成
   那裡的 `attempt-28`。沒有覆寫任何東西，已搬到本目錄的
   `misrouted-attempt-28/`，而且 `--profile-override` 現在**沒有 `--evidence-dir` 就拒跑**。
2. **單輪的 `pass: false` 是常態**，凍結的 `attempt-27` 也是 false。
   A3 的判定來自 validator 對整棵樹的判讀，不是那個欄位。
   我差一點把 shakedown 的 `pass: false` 當成 P3 失敗報出去。

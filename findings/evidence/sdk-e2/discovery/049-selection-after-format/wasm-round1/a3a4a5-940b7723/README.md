# relink 後的 A3／A4／A5 重掃：**全部通過**

**日期**：2026-08-15　**artifact**：`e2-combination` ＝ **`940b7723…`**（含 #49 的修法）
**判定工具**：`tools/validate_e2_a.py`——**與發 E2-A 總判定用的是同一支**
**驅動**：[`../sweep.sh`](../sweep.sh)，44 輪
**為什麼要跑**：SPEC E2-A 10.14 的 E2-B 進場條件寫死了
「finding 039 修復**並於 relink 後重掃 A3／A4／A5 通過**」——**兩件都要**。

## 結果

| | |
|---|---|
| A3 | **`A3_PASS`**，六格（3 fixture × 2 瀏覽器）全部 `covered`，每格 `bound 3 / passing 3 / superseded 0` |
| A4 | **`A4_PASS`**，六格同上 |
| A5 | **`A5_PASS`**，八格（4 fixture × 2 瀏覽器）全部 `bound 1 / passing 1` |
| `gaps` | **`{}`（空）** |

**綁定檢查**（finding 027 的規則）：

```json
"currentProfileWasmSha256": "940b7723ca8df6c1dd3327b5950b67b23fe9a0ae28504900d07221fb0cd85217",
"evidenceWasmSha256":      ["940b7723ca8df6c1dd3327b5950b67b23fe9a0ae28504900d07221fb0cd85217"],
"allEvidenceIsCurrentBuild": true,
"verdictCountsOnlyCurrentBuild": true,
"staleBuilds": []
```

**判定綁定的 `findings/evidence/sdk-e2/summary.json` 沒有被動到**：
執行前後 sha256 都是 `1dfc3df3363f3f69…`。`--output` 有另外指定，這是刻意的。

## 這一輪說了什麼、沒說什麼

**說了**：把 `RESET`＋`START`＋`END` 的修法編進共用引擎，**沒有改壞 A3／A4／A5 三套矩陣**。
與 [P3 在 `ba1a5dd5` 上那一輪](../../../039-combination/p3-sweep-ba1a5dd5/README.md)一致
（那一輪也是三個 PASS、`gaps` 空）。

**沒說**：

- **這一輪不是縮限 4 的憑據。** A3／A4／A5 **全部從收合游標出發**（縮限 7），
  它們根本不走範圍選取那條路。真正量掉縮限 4 的是
  [同層的 composition scan](../README.md)——arm8 兩個進入點、兩瀏覽器、
  而且選取幾何與控制臂逐格相同。**兩份加起來才是進場條件，缺一不可。**
- **縮限 7 仍然開著。** 「在**範圍選取**上派送格式動作」從來沒有量過，
  這一輪也沒有量。那是 E2-B 要補的那一格。
- **不是 E2-B 的判定。** E2-B 還沒有規格（任務 #48）。

## 過程備註

**單輪 `exit 1` 是常態**，44 輪每一輪都是。凍結的 `attempt-27` 也是 `pass: false`；
判定來自 validator 對整棵樹的判讀，不是那個欄位。
**我第一次啟動這個掃描時就是看到 `exit 1` 而把它停掉的**——上一份交接文件早就記過這個坑，
這是第二次踩。`sweep.sh` 現在把這件事寫在註解裡，並且刻意不用 `set -e`。

# WASM 這一輪：**修法在 artifact 上成立**，兩瀏覽器逐格相同

**日期**：2026-08-15
**artifact**：`e2-combination` ＝ **`940b7723…`**（前一顆 `ba1a5dd5…` 已封存）
**對照**：`e2-format-discovery` ＝ `c89f069e…`（凍結、封存）
**工具**：`tools/run_f039_composition_scan.py`，**與 P2 同一支**，只換 `--profile` 與 `--output`
**預測**：[`../PREDICTION-wasm.md`](../PREDICTION-wasm.md)，commit `5b363d3`，**寫在執行之前**

## 判定：落在預先寫下的**結局 A**

## 對照先跑，而且它必須失敗

`--profile e2-format-discovery`（封存的 `c89f069e`）：
**`arm8ReproducesOnDiscoveryPath: True`**——第 8 臂在對照 artifact 上**仍然逾時**。
與 [P2 當初那一輪的對照](../../039-combination/p2-composition-scan-ba1a5dd5/README.md)逐格相同
（`arm8ProductCompletes: false`、`repeatAllCompleted: false`、`clickAllCompleted: true`）。
**所以這支工具仍然偵測得到它宣稱量掉的那個缺陷**，新 artifact 的讀數才有意義。

## 修之前對修之後

| 判準 | `ba1a5dd5`（修之前） | **`940b7723`（修之後）** |
|---|---|---|
| `arm8ReproducesOnDiscoveryPath` | **true**（discovery 那條逾時） | **false** |
| `arm8ProductCompletes` | true | true |
| `arm8ProductSelectionNonEmpty` | **false** | **true** |
| `arm8ProductSelectionType` | **`none`** | **`text`** |
| `sameSelectWithoutFormatSelectsText`（歸因控制） | true，`"moji 😀 graphe"` | **true，`"moji 😀 graphe"`** |
| `repeatAllCompleted` | true | true |
| `clickAllCompleted` | true | true |
| `harnessTimeoutsOutsideControl` | 0 | **0** |

**逐步的數字才是重點：**

| step | 修之前 | **修之後** |
|---|---|---|
| `arm8-discovery` range-2 | **逾時 10 001 ms** | **完成，`documented-callback-text-selection`，10 ms** |
| `arm8-product` range-2 | 完成，`verified-selection-readback`，**251 ms**，選取 `none` | **完成，`documented-callback-text-selection`，11 ms** |
| `repeat` select-1／2／3 | **251／250／250 ms** 的 readback（＝三次都沒選到） | **10／10／11 ms** 的 callback |
| `select-y2600-without-format` | 20 ms callback | **20 ms callback（不變）** |

**那個 251 ms 的 readback 整個消失了。** 它本來是 bounded readback 在 250 ms 期限上
誠實回報「沒選到」；現在選取真的成立，回呼在 10 ms 就到了。

## `arm8-discovery` 那一格是這一輪最有訊息量的

它**沒有** bounded readback（依裁決刻意保留不 buffered），所以它**只能**靠回呼完成。

它從**逾時 10 001 ms** 變成 **10 ms 完成**，等於量到：
[finding 039](../../../../039-the-discovery-selection-path-completes-at-most-once.md)
的「回呼不會來」，原因是**選取根本沒有成立**——不是回呼被 WASM 這一層弄丟。
原生四輪推出來的機制，在 artifact 上得到同一個答案。

## 兩瀏覽器

Chrome 與 Firefox **八個判準逐格相同**，包括控制臂選到的那串
`"moji 😀 graphe"`。所以這不是單一瀏覽器的行為。

## 這一輪**沒有**宣稱

- **沒有宣稱 A3／A4／A5 通過**——那是同目錄的 `a3a4a5-940b7723/`，另一輪。
  SPEC E2-A 10.14 的 E2-B 進場條件要求「修復**並於 relink 後重掃通過**」，
  **兩件都要**，這一輪只完成前半。
- **沒有宣稱縮限 4 可以撤。** 撤限要憑重掃，不憑修法看起來對——那是 10.14 寫死的。
- **沒有宣稱這是產品 `835b453d` 的行為。** 出貨編輯器沒有編進 format barrier，
  而[原生第三輪](../native-round3/README.md)量到引擎派送的其他二十個指令都不毒化，
  所以今天的出貨路徑上這個組合不存在。**這個修法是為 E2-B 準備的，不是在補產品的洞。**
- **沒有宣稱上游那一半有進展。** 那是另一份 finding 與另一次回報。

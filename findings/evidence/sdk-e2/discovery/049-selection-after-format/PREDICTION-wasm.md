# WASM 這一輪的預測：修法在 artifact 上到底成不成立

**寫在任何一次 WASM 執行之前。** 前四輪全在原生，
這一輪第一次把話說到 artifact 上。

## 受測的東西

| | |
|---|---|
| **改動** | `probe_engine.cpp` 的 `OXSDK_EDITOR_SELECTION_TEXT_HANDLES`：`RESET`＋`END` → **`RESET`＋`START`＋`END`** |
| **新 artifact** | `e2-combination` ＝ **`940b7723…`**（前一顆 `ba1a5dd5…` 已封存於 `build/archive/`） |
| **凍結的三顆** | `835b453d`／`679def61`／`c89f069e` 重連結前後都核對過，**未動** |
| **工具** | `tools/run_f039_composition_scan.py`，**與 P2 同一支**，只換 `--profile` 與 `--output` |

## 對照組是必要的，不是形式

先跑 **`--profile e2-format-discovery`（封存的 `c89f069e`）**：
第 8 臂**必須仍然逾時**。若它這次不逾時，這支工具就偵測不到它宣稱量掉的那個缺陷，
**新 artifact 的讀數一律不得引用**。P2 當初就是這樣做的。

## 預測

| arm | P2 在 `ba1a5dd5` 上的讀數 | **這一輪的預測** |
|---|---|---|
| `arm8-product`（產品 ABI） | 完成，`verified-selection-readback` **251 ms**，選取 **`none`**、空字串 | **完成，走 callback（數十 ms 等級），選到 `"moji 😀 graphe"`** |
| `arm8-discovery`（discovery ABI，照裁決仍不 buffered） | **逾時 10 000 ms** | **也完成**——選取這次真的成立，`LOK_CALLBACK_TEXT_SELECTION` 就會廣播，那條路等的就是它 |
| `select-y2600-without-format`（歸因控制） | 完成 20 ms，`"moji 😀 graphe"` | **不變** |
| `repeat-composition`（三輪） | 三輪的 `select-N` 全是 251 ms 的 readback（＝三次都沒選到） | **三輪都走 callback 並選到文字** |
| `click-gesture` | 三輪全過 | **不變** |
| 對照 artifact `c89f069e` 的第 8 臂 | 逾時 | **仍然逾時** |

**`arm8-discovery` 那一格是這一輪最有訊息量的。** 它沒有 bounded readback，
所以它**只能**靠回呼完成。它若從逾時變成完成，就等於量到
「回呼沒來」的原因確實是「選取沒有成立」，而不是回呼被 WASM 這一層弄丟了。

## 結局

**結局 A（預測命中）**：兩條 arm8 都完成且選到 `"moji 😀 graphe"`，控制臂不變，
對照 artifact 仍逾時。
→ 修法在 artifact 上成立。**下一步是 A3／A4／A5 重掃**（SPEC E2-A 10.14 的 E2-B 進場條件
要求「修復並於 relink 後重掃通過」），縮限 4 才談得上撤。

**結局 B：產品那條成立、discovery 那條仍逾時。**
→ 「選取真的成立了」與「回呼會廣播」被拆開，我對機制的說法在 WASM 上不完整。
**不得宣稱修好**，先查那條路的回呼去哪了。

**結局 C：產品那條仍回報 `none`。**
→ 原生成立、WASM 不成立。修法不足，或 WASM 這一層另有東西。
**回到原生與 WASM 的差異本身**，不再往 E2-B 推。

**結局 D：對照 artifact 這次不逾時。**
→ 工具或環境變了，**這一輪全部作廢**，先修工具。

**結局 E：控制臂 `select-y2600-without-format` 變了。**
→ 那個座標的內容或版面被改動過，兩輪不可比，**先確認 fixture 與座標**。

## 這一輪一樣不宣稱

- **不宣稱 A3／A4／A5 仍然通過**——那是另一輪，還沒跑。
- **不宣稱這是產品 `835b453d` 的行為**。出貨編輯器沒有編進 format barrier，
  而[第三輪](native-round3/README.md)量到引擎派送的其他二十個指令都不毒化，
  所以今天的出貨路徑上這個組合不存在。
- **不宣稱上游那一半有任何進展**——那是另一份 finding 與另一次回報。

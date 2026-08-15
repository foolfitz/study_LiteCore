# 第一輪（原生）：**落在預先寫下的結局 A**

**日期**：2026-08-15
**跑的是**：原生 LibreOffice，`build-native-26-8/instdir/program`，core `671c848b`
**探針**：`wasm_sdk_probe/tools/f049_native_select_after_format.cpp`
**執行**：`tools/run_f049_native.sh`，probe exit 0
**預測**：[`../PREDICTION.md`](../PREDICTION.md)，
`a272f74`（五臂）＋ `1331654`（執行前修正臂 E、新增臂 F）——**兩個 commit 都在這一輪之前**

## 結果

`{"summary":{... ,"matchesPredictedShape":true}}`

| 臂 | 範圍選取之前做什麼 | 預測 | **實測** | 選到 | 回呼 |
|---|---|---|---|---|---|
| **A** `control` | 什麼都不做 | 選得到 | **選得到** | `"C-ISOLA"`（7 B） | 2 |
| **B** `format-only` | `.uno:DefaultBullet` | 選得到 | **選得到** | `"E1-LC-"`（6 B） | 2 |
| **C** `select-text-only` | `.uno:SelectText` ＋ 還原 | 選不到 | **選不到** | `""` | **1** |
| **D** `full-barrier` | barrier 的完整形狀 | 選不到 | **選不到** | `""` | **1** |
| **E** `+ .uno:Escape` | 同 D 再加 Escape | 選不到（**已修正的預測**） | **選不到** | `""` | **1** |
| **F** `+ .uno:GoLeft` | 同 D 再加 GoLeft | 選得到 | **選得到** | `"E1-LC-"`（6 B） | 2 |

## 這一輪確定了三件事

**一、起因是 `.uno:SelectText`，不是格式指令。**
臂 **B 做了格式動作、之後選得到**；臂 **C 一次格式動作都沒做、卻選不到**。
這兩格單獨就把「格式指令弄壞了選取」排除掉了。

**二、失敗的形狀是「少一個回呼」，不是「回錯東西」。**
成功的臂有 **2 次** `LOK_CALLBACK_TEXT_SELECTION`（`RESET` 一次、`END` 一次），
失敗的臂只有 **1 次**——`END` 那一次**沒有廣播**，因為選取確實沒有改變。
這正好解釋了 [finding 039](../../../../039-the-discovery-selection-path-completes-at-most-once.md)：
discovery 那條在等一個永遠不會來的回呼，而產品那條的 bounded readback
在 250 ms 期限誠實回報「沒選到」。

**三、`.uno:Escape` 不能解，`.uno:GoLeft` 可以。**
兩者的差別在 `MoveCursor(false)`：`FN_CHAR_LEFT` 會走到它並呼叫 `EndSelect()`，
而 `FN_ESCAPE` 的 `EnterStdMode()` 在 `HasSelection()` 為假時根本到不了
（`sw/source/uibase/uiview/view2.cxx:1232`）——barrier 還原完剛好沒有選取。

## 每一臂都有的健全性檢查

每一臂在量完之後另外派送 `.uno:SelectAll`：
**六臂全部拿得到全文**（沒做格式的 207 B、做過的 215 B）。
所以「選不到」不是文件不可讀或引擎壞掉，**是那一個選取沒有成立**。

## 兩個順帶讀到的東西

**`after-select-text` → `selectionType: 1`（TEXT），`after-barrier-restore-2` → `0`（NONE）。**
所以 barrier 的還原**確實**把選取收掉了——**看得見的狀態是對的**，
壞掉的是看不見的那一格。任何只看 `selectionType` 的檢查都會說一切正常。

**A 選到 `"C-ISOLA"`、B／F 選到 `"E1-LC-"`。** 同一組 x 座標選到不同的字，
是項目符號把整段往右推了。這反過來證明**臂 B／D／E／F 的格式動作確實生效了**
（`selectAllBytes` 從 207 變 215 是同一件事的另一個讀數）。

## 這一輪**沒有**宣稱

- **沒有宣稱 WASM 上也是這樣。** 這一輪只描述原生。要把話說到 artifact 上，
  得回到 `e2-combination` 上量。
- **沒有量到 `m_bInSelect` 本身。** LOK 不暴露那個旗標，這一輪量到的是**形狀**：
  哪些前置動作會讓下一個選取失敗、哪一種收尾會救回來。
  「就是 `m_bInSelect` 的那個提前 return」目前仍是原始碼層的推論——
  第二輪的臂 G／H 就是為了把它變成可觀測的。
- **沒有宣稱 `.uno:GoLeft` 是要出貨的修法。** 它會把游標移一格，
  而且它救得回來不代表救回來的是同一個原因（`MoveCursor(false)` 同時做了
  `EndSelect()` 和 `m_fnKillSel`）。

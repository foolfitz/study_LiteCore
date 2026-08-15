# 第二輪的預測：把「是 `m_bInSelect` 的提前 return」變成可觀測的

**寫在第二輪任何一次執行之前。** 承 [`PREDICTION.md`](PREDICTION.md) 與
[第一輪的結果](native-round1/README.md)（結局 A，`matchesPredictedShape: true`）。

## 第一輪留下什麼沒解決

第一輪證明了**哪些前置動作會讓下一個選取失敗**（`.uno:SelectText` 會，格式指令不會），
以及**哪一種收尾救得回來**（`.uno:GoLeft` 會，`.uno:Escape` 不會）。

**但它沒有指認機制。** `.uno:GoLeft` 走 `MoveCursor(false)`，那一行同時做兩件事：

```cpp
EndSelect();                                       // 清掉 m_bInSelect
(this->*m_fnKillSel)(nullptr, false, …);           // 另一件事
```
（`sw/source/uibase/wrtsh/move.cxx:87`–`89`）

所以「F 救得回來」與「壞的是 `m_bInSelect`」之間還隔著一個沒被排除的可能。
LOK 不暴露那個旗標，量不到它本身——但它的**提前 return 有一個外部可見的後果**，
第二輪就量那個。

## 這一輪的推論（同樣還沒量到）

`SwEditWin::SetCursorTwipPosition`（`sw/source/uibase/docvw/edtwin.cxx:7102`–`7122`）：

```cpp
if (bClearMark) rShell.ClearMark();
else            bCreateSelection = !rShell.HasMark();
if (bCreateSelection) m_rView.GetWrtShell().SttSelect();     // 可能提前 return
…
if (bCreateSelection) m_rView.GetWrtShell().EndSelect();     // 一定會執行
```

關鍵在最後一行：**`EndSelect()` 是照 `bCreateSelection` 呼叫的，不是照 `SttSelect()`
有沒有真的做事。** 所以那個失敗的 `END`——`SttSelect()` 提前 return、`SetMark()` 沒執行——
**結尾仍然呼叫 `EndSelect()`，把 `m_bInSelect` 設回 false**。

**推論：那個旗標會被「失敗的那一次選取」自己燒掉。**
於是同一組座標**再選一次就會成功**，而且中間不需要派送任何東西。

同一段程式碼也給出第二個推論：**`START` 也會燒掉它**，
因為 `START` 走的是同一支（`bPoint=false, bClearMark=false`），
`bCreateSelection` 同樣為真、結尾同樣呼叫 `EndSelect()`。
所以 `RESET → START → END` 應該一次就成——**而且這是完全在我方引擎裡的修法**，
不必派送 `.uno:GoLeft`，也就不會有「游標被移走一格」的副作用。

## 臂與預測

前置一律是**臂 D 的完整 barrier**（格式 → 還原 → `.uno:SelectText` → html 讀回 → 還原），
除了臂 I。座標與第一輪相同。

| 臂 | 量測尾巴 | **預測** |
|---|---|---|
| **G** `barrier-then-twice` | `RESET`→`END`，**然後再一次** `RESET`→`END` | **第一次空、第二次選得到** |
| **H** `barrier-then-reset-start-end` | `RESET`→`START`→`END` | **一次就選得到** |
| **I** `control-reset-start-end` | **不做 barrier**，直接 `RESET`→`START`→`END` | **選得到**（H 的對照） |

**臂 I 是必要的，不是湊數的。** 沒有它，H 選得到也可能只是
「`START`＋`END` 這條路本來就永遠有效、跟 barrier 無關」，
那樣就證不出「H 是修法」。第一輪漏掉這種對照的教訓已經有過一次
（P2 的 `select-y2600-without-format`）。

## 結局，以及各自的處置

**結局 A（預測命中）：G 第一次空、第二次選得到；H 與 I 都選得到。**
→ **機制指認成立**：壞的就是那個提前 return，而且旗標由失敗的那一次自己清掉。
處置：產品修法取 **`RESET → START → END`**（改 `probe_engine.cpp` 的
`OXSDK_EDITOR_SELECTION_TEXT_HANDLES` 一處），重連結**組合** artifact 重測 P2 三臂，
不動任何凍結 artifact。上游那一半另開 finding。

**結局 B：G 第二次也選不到。**
→ `EndSelect()` 沒有把它清掉，或壞的根本不是這個旗標。
處置：**不改任何產品程式碼**，回頭把 `m_fnKillSel` 那一支也拆出來單獨試
（例如改用只呼叫 `EndSelect()`、不碰函式指標的路徑），先重新指認機制。

**結局 C：H 選得到但 I 選不到。**
→ 對照臂自己壞了，H 的成立無法歸因。處置：**先修探針**，在修好之前不得引用 H。

**結局 D：H 選不到但 G 第二次選得到。**
→ 旗標會被燒掉，但 `START` 不是燒掉它的路徑，我對 `bCreateSelection` 的讀法有錯。
處置：修法退回 `.uno:GoLeft` 那條，並把它的游標副作用寫進規格。

## 這一輪一樣不宣稱

- **不宣稱 WASM 上也是這樣。** 兩輪都是原生。要動 E2-B 的判定，
  還是得在 `e2-combination` 上重測 P2 那三臂。
- **不宣稱 `RESET → START → END` 是對的產品修法**——這一輪只問它在原生上成不成立。
  要出貨還得過 A3／A4／A5 重掃。

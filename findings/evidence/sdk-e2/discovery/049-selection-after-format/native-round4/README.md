# 第四輪（原生）：覆核要的兩個分離臂都命中，**但第一輪的形狀這次沒複驗過**

**日期**：2026-08-15　**core `671c848b`**
**預測**：[`../PREDICTION-round4.md`](../PREDICTION-round4.md)（臂由
[codex 對抗性覆核](../codex-review-round1-3.md)指名）
**這一輪把前三輪全部重跑**，共 35 臂，probe exit 0。

```
"matchesRound1PredictedShape":            false   ← 見下，臂 F 翻轉
"matchesRound2PredictedShape":            true
"round3ControlsDisagree":                 true
"round3Poisoned":                         ["K-poison-selecttext"]
"round4HealingSurvivesBothControls":      true
"round4EndpointsAgree":                   true
"round4ReverseAgrees":                    true
```

## 四個新臂，四個都落在預測上

| 臂 | 預測 | 實測 | 它排除了什麼 |
|---|---|---|---|
| **AE** `twice-no-readback` | 第一次 0 個回呼、第二次選得到 | **就是這樣** | 治好它的**不是** readback，**也不是**那 600 ms 等待——這一輪兩者都拿掉了 |
| **AF** `markless-reset-first` | 仍然選不到 | **仍然選不到**（然後第二次選得到） | 治好它的**不是**單純的 `SetCursor`／版面 priming——AF 先在 `END` 的座標做了一次 markless `RESET`，走的是同一個 `SwCursorShell::SetCursor`，**但不呼叫 `EndSelect()`**，而它救不回來 |
| **AG／AH／AI** 端點 | 三者逐字相同 | **三者都是 `"C-ISOLA"`** | `RESET(x0)`→`START(x1)`→`END(x2)` 錨在 **`x1`**，不是 `x0`；而且**壞狀態與正常狀態選到同一串** |
| **AJ／AK** 反向 | 兩者逐字相同 | **兩者都是 `"-LC-ISOLA"`** | `END` 在 `START` 左邊時也一致 |

**AE 與 AF 合起來才是重點。** 覆核指出第二輪的臂 G「中間什麼都沒發生」是假的
（還有 sleep、`getTextSelection`、`getSelectionType`、`SwTransferable`），
並點名兩個替代解釋。這一輪把兩個都試掉了：**拿掉讀取與等待，照樣治好；
換成不呼叫 `EndSelect()` 的同一個 `SetCursor`，治不好。**

**AI 是 AG／AH 的錨點參照**，沒有它，AG＝AH 也可能是兩邊一起錯。

## 三個臂在四輪之間翻轉

| 臂 | r1 | r2 | r3 | r4 |
|---|---|---|---|---|
| **F** `full-barrier + .uno:GoLeft` | 選得到 | 選得到 | 選得到 | **選不到** |
| **Y** `.uno:InsertPara` | — | — | 空／空 | **選得到／選得到** |
| **Z** `.uno:InsertLinebreak` | — | — | 空／空 | **選得到／選得到** |

（`.uno:InsertAnnotation` 也算一個：第三輪讓行程當掉，第四輪跑起來而且乾淨。）

**最可能的原因是探針用固定 sleep**：`post()` 派送 uno 指令後只等 400 ms，
指令有沒有在量測開始前跑完並不保證。**這三臂的共同點正是「結果取決於那個指令已經生效」。**
——這也正是覆核提醒過的：固定臂順序、共用同一 kit，沒有排除順序與時序效應。

**所以要收回一句話**：第一輪的 README 寫「`.uno:Escape` 不能解，**`.uno:GoLeft` 可以**」。
後半**四輪之中有一輪相反，不可重現**，已就地標註。
（`.uno:Escape` 不能解那半四輪一致，仍然成立。）

**沒有被這件事動搖的**（四輪全部一致）：

- **C／D／E 從來沒有選到**——`.uno:SelectText` 之後範圍選取失敗，這是最硬的一格。
- **G／K／AE／AF 一律是「第一次空、第二次選得到」**——兩次嘗試的簽名。
- **A／B／H／I／J、以及 L–X／AB／AC／AD／AA 一律選得到。**
- **毒化的只有 `.uno:SelectText` 一個。**

## 這一輪之後仍然沒有的

- **仍然沒有直接量到 `m_bInSelect`。** 覆核指出 `SwWrtShell::IsInSelect()` 是公開方法
  （`sw/source/uibase/inc/wrtsh.hxx:154`），但那是 `sw` 模組內部標頭，
  外部 LOK 探針拿不到；要直接量得寫成核心樹裡的 cppunit 測試並重編 `sw`——
  長時間編譯，**歸使用者**。
- **仍然沒有在 WASM 上量。** 四輪都是原生。E2-B 的判定要動，
  還是得在 `e2-combination` 上重測 P2 那三臂。
- **探針仍然用固定 sleep。** 上面三個翻轉臂就是它的代價；
  要讓那三格可引用，得改成等待實際完成而不是等計時器。

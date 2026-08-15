# 第二輪（原生）：**兩個形狀都命中**，而且第一輪有一句要更正

**日期**：2026-08-15
**跑的是**：原生 LibreOffice，`build-native-26-8/instdir/program`，core `671c848b`
**探針**：同一支 `f049_native_select_after_format.cpp`，加了三臂與兩種量測尾巴
**預測**：[`../PREDICTION-round2.md`](../PREDICTION-round2.md)，commit `394b41c`，**在這一輪之前**
**這一輪把 A～F 一起重跑**，所以它同時是第一輪的複驗

```
"matchesRound1PredictedShape": true
"matchesRound2PredictedShape": true
```

## 新的三臂

| 臂 | 量測尾巴 | 預測 | **實測** |
|---|---|---|---|
| **G** `barrier-then-twice` | `RESET`→`END`，**再一次** `RESET`→`END` | 第一次空、第二次選得到 | **第一次 `""`、第二次 `"E1-LC-"`** |
| **H** `barrier-reset-start-end` | `RESET`→`START`→`END` | 一次就選得到 | **`"E1-LC-"`** |
| **I** `control-reset-start-end` | 不做 barrier，同樣三步 | 選得到 | **`"C-ISOLA"`** |

## G 才是這一輪的重點

**中間什麼都沒有派送**——同一組座標、同一支呼叫、連續兩次，第一次空、第二次成功。

這是 `if (m_bInSelect) return;` 那個提前 return **獨有**的簽名：
`SwEditWin::SetCursorTwipPosition` 結尾的 `EndSelect()` 是照 `bCreateSelection`
呼叫的（`edtwin.cxx:7121`–`7122`），**不是照 `SttSelect()` 有沒有真的做事**。
於是那個失敗的 `END` 自己把旗標設回 false，下一次就正常。

第一輪的臂 F（`.uno:GoLeft`）救得回來，但 `MoveCursor(false)` 同時做了
`EndSelect()` 與 `m_fnKillSel`，所以 F **指認不了**是哪一個。
**G 不需要派送任何東西**，所以它把「是某個 uno 指令的副作用」整類排除掉。

## H 與 I 一起才有意義

H 單獨成立不能說「`RESET`→`START`→`END` 是修法」——也可能是
「`START`＋`END` 這條路本來就永遠有效，跟 barrier 無關」。
**I 是那個對照**：不做 barrier 時它也選得到，所以 H 的成功不是這條路徑天生特別。

> 這種對照第一輪有、P2 那次是事後才補的（`select-y2600-without-format`）。
> 這次是先寫進預測才跑的。

## **更正第一輪的一句話：回呼次數不能照抄**

第一輪的 README 寫「成功的臂有 **2 次** `LOK_CALLBACK_TEXT_SELECTION`、失敗的臂只有 **1 次**」。
**那兩個絕對數字不穩定。** 同樣六臂、同一支探針、同一段量測程式碼，兩輪的計數是：

| 臂 | 選到？（兩輪相同） | 第一輪計數 | 第二輪計數 |
|---|---|---|---|
| A `control` | ✅ ✅ | 2 | **1** |
| B `format-only` | ✅ ✅ | 2 | **1** |
| C `select-text-only` | ❌ ❌ | 1 | **0** |
| D `full-barrier` | ❌ ❌ | 1 | **0** |
| E `+escape` | ❌ ❌ | 1 | **0** |
| F `+goleft` | ✅ ✅ | 2 | **1** |

**六臂全部差 1，方向一致。** 我無法從手上的資料歸因那個差（多出來的那一次最可能是
量測開頭那個 `RESET` 自己的廣播，但這是猜的，沒有量到）。

**所以可以引用的是「同一輪之內的差」，不是絕對值**：

> **失敗的臂，比成功的臂少一次 `TEXT_SELECTION` 廣播——少的就是 `END` 那一次。**
> 兩輪都成立。

這仍然撐得起 [finding 039](../../../../039-the-discovery-selection-path-completes-at-most-once.md)
的機制（discovery 在等一個不會來的回呼），但**引用時要寫成差，不要寫成 2 對 1**。

**這個更正是複驗抓到的**，不是覆核抓到的——把 A～F 一起重跑不是多花時間，
它就是抓到這件事的那個動作。

## 這一輪仍然**沒有**宣稱

- **沒有宣稱 WASM 上也是這樣。** 兩輪都是原生。E2-B 的判定要動，
  還是得在 `e2-combination` 上重測 P2 那三臂。
- **沒有宣稱 `RESET`→`START`→`END` 就是要出貨的修法。**
  這一輪只說它在原生上一次就成立，而且對照臂證明那不是路徑天生的優勢。
  要出貨還得過 A3／A4／A5 重掃。
- **沒有量到 `m_bInSelect` 本身。** LOK 不暴露它。G 是它的可觀測後果，不是它。

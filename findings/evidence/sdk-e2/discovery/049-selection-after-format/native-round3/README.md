# 第三輪（原生）：**二十個 uno 指令裡只有 `.uno:SelectText` 毒化**——但這一輪當掉了

**日期**：2026-08-15　**core `671c848b`**　**預測**：[`../PREDICTION-round3.md`](../PREDICTION-round3.md)，commit `9bfbb2c`＋`a850a7d`

> **這一輪沒跑完。** 探針在 `.uno:InsertAnnotation` 那一臂以
> `Unspecified Application Error` 當掉（`sal.log` 末行），
> 後面四臂（`InsertAnnotation`／`TrackChanges`／`AcceptTrackedChanges`／`Escape`）沒有執行，
> 也沒有印出 summary 行。**26 臂跑到、4 臂沒跑到。**
> 那四臂由[第四輪](../native-round4/README.md)補完（並把當掉的那一臂排到最後），
> 四臂**全部乾淨**。

## 結果

| 判定 | 臂 |
|---|---|
| **毒化**（第一次空、第二次選得到） | **`.uno:SelectText`**（臂 K，正對照） |
| 乾淨 | `.uno:ExecuteSearch`、**`.uno:Undo`**、`.uno:Redo`、`.uno:Bold`、`.uno:Italic`、`.uno:Underline`、`.uno:Strikeout`、`.uno:DefaultBullet`、`.uno:DefaultNumbering`、`.uno:RemoveBullets`、`.uno:StyleApply`、`.uno:Delete`、`.uno:SwBackspace`，以及什麼都不派送的負對照（臂 J） |
| 兩次都空 | `.uno:InsertPara`、`.uno:InsertLinebreak`（臂 Y／Z）——**但這兩格第四輪翻轉了，見下** |

**負對照（J）與正對照（K）確實不一致**，所以這一輪的其他讀數有意義。

## 三件成立的事

**一、只有一個。** 引擎派送的指令裡，**只有 `.uno:SelectText` 會毒化下一個範圍選取**。
所以 finding 的範圍就是 format barrier 那一處，不是「引擎到處都在留狀態」。

**二、`.uno:Undo` 是乾淨的。** 這很重要，因為
[任務 #50 當天剛把復原鈕接上 `demo-structure`](../../demo-structure-undo/README.md)。
如果它會毒化，那顆按鈕就是自己裝上去的地雷。四輪之中它都乾淨。

**三、搜尋乾淨，而且原始碼說得出為什麼。**
`sw/source/uibase/uiview/viewsrch.cxx:773` 的 `SttSelect()` 對上 `:846` 的 `EndSelect()`——
**有配對**。`FN_SELECT_PARA` 是同一份程式碼裡的例外。

## 臂 Y／Z 的判定要收回一半

第三輪把 `.uno:InsertPara`／`.uno:InsertLinebreak` 讀成「兩次都空 ＝ 那個座標沒字了，不是毒化」。
**[第四輪](../native-round4/README.md)同樣兩臂變成兩次都選得到。**

- **「不是毒化」這個判定兩輪一致**（毒化的簽名是「空→選得到」，兩輪都不是這個形狀）。
- **但「因為那個座標沒字了」這個理由不可靠**——同一份文件、同一組座標、同一個指令，
  兩輪讀數相反。真正的原因很可能是**固定 sleep 下那個 uno 指令有時還沒執行完**
  （見[第四輪對可重現性的整理](../native-round4/README.md#三個臂在四輪之間翻轉)）。

## 當掉本身

`.uno:InsertAnnotation` 在無視窗的 LOK 探針裡會讓行程結束。
**這一輪沒有進一步追**，只把它排到臂序最後，讓它只能帶走自己。
第四輪它跑起來了而且乾淨——所以那次當掉**不是穩定重現的**，同樣列進不可重現的那一類。

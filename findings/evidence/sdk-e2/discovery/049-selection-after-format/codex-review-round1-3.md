# codex 對抗性覆核（第一～三輪之後，2026-08-15）

送出的是三個 Claim 與全部臂的讀數，指令是**去否證，不是去確認**，
並要求「無法從原始碼核實就說無法核實，不要附和」。
覆核跑在唯讀沙箱、`cwd` 為本 repo，可讀 `libreoffice-26-8`。

**我對每一條打掉我的話都自己重跑過核對**，結果記在每一段的末尾。

---

## 覆核的總評

> 結論先講：Claim 1 的原始碼路徑大致正確，而且在一般 Writer 文字游標狀態下，
> `m_bInSelect` 確實是目前最強的解釋；但既有 arm 沒直接觀測該旗標，
> 不能宣稱已排除所有替代機制。Claim 2 的「唯一鑑別特徵」明顯過度宣稱。
> Claim 3 在目前測到的 body-text、同座標 `RESET/START` 情況會成功，
> 但尚未證明是普遍正確、可直接出貨的修法。

---

## Claim 1（機制）：八個步驟逐一核對，**路徑成立，唯一性不成立**

覆核逐步核對並確認：`swriter.sdi:5649` 的對應、`textsh1.cxx:1975` 的分支、
`move.cxx:402`／`:55`–`60`／`:84`–`85` 的呼叫鏈、`ShellMoveCursor` 解構子沒有 `EndSelect()`、
`select.cxx:407` 的提前 return、`edtwin.cxx:7076` 的 `bClearMark` 分支。

**它另外補了三件我沒寫到的事：**

1. **`textsh1.cxx:1975` 有一個我省略的分支**：在段首時走 `EnterStdMode()` 而不是 `SttPara()`。
   不推翻機制（兩支最後都由 `EndPara(true)` 重新開啟 selection 狀態），但敘述漏了。

2. **「兩個 barrier RESET 都讓旗標 survive」時序上不精確**：
   第一個 RESET 發生在 `.uno:SelectText` **之前**，那時旗標還沒被設。
   真正保存壞狀態的是 `.uno:SelectText` **之後**那個 restore RESET，以及呼叫端的 RESET。
   → **我接受，PREDICTION.md 的表確實把兩個 RESET 並列成同一回事。**

3. **排除函式指標替代說最重要的證據**：`SetCursorTwipPosition` 故意把 shell 宣告為
   `SwEditShell&`，呼叫的是 `SwCursorShell::SetCursor(const Point&)`（`crsrsh.hxx:443`），
   **不經過 `m_fnSetCursor`**。這一點比我原本的論證強。

它同時逐一排除了 `m_fnKillSel`／`m_fnSetCursor`／`m_bSelWrd`／`m_bSelLn`／cursor stack／
`m_bExtMode`，其中 `m_bExtMode` 的排除很漂亮：若它為真，`select.cxx:449` 的
`EndSelect()` 反而**不會**清 `m_bInSelect`，那 G 的第二次應該繼續失敗——觀測不支持。

**它保留的空缺**：`ClearMark()` 不等同 `KillPams()`，add-mode／multi-cursor 沒有涵蓋。

---

## Claim 2（鑑別簽名）：**「沒有其他候選」這句要刪**

> 第一次和第二次之間其實有：600 ms `sleep_for`、`getTextSelection()`、
> `getSelectionType()`、transferable 建立與資料讀取。沒有證據顯示這些讀取會清
> `m_bInSelect`，但「什麼都沒發生」並不正確。

**我核對過，成立**：`measureResetEnd` 就是這樣寫的，而 `getSelection()` 會建立
`SwTransferable`（`unotxdoc.cxx:4075`–`4105`）。

它提出兩個替代機制：第一次的 `SetCursor`／`UpdateCursor` 讓版面或座標映射穩定；
或等待／回呼／transferable readback 完成了某個 pending 狀態。
並指名兩個分離臂——**就是第四輪的 AE 與 AF**。

它也獨立指出兩輪的回呼數不一致（A/B/F 是 2 對 1、C/D/E 是 1 對 0），
**與我自己複驗抓到的是同一件事**，結論一致：固定 sleep 下的回呼計數有時序雜訊。

---

## Claim 3（修法）：**結論對、理由錯**

覆核逐步走了兩種狀態。壞狀態那半與我寫的一致。**正常狀態那半我寫錯了**：

> 目前 H/I 使用 `R == S`。此時 START 結束時是 collapsed mark，
> `SttLeaveSelect()` 會把 mark 清掉。之後 END 才重新在 S 建 mark，再移到 E。

**我核對過，成立**：`select.cxx:661`–`667`，`HasSelection()` 為假就落到 `ClearMark()`。
所以「`START` 建的 mark 一直保留到 `END`」是錯的，**最終選取範圍仍然是 S→E**。

它列出 H/I 證不足的四點：只檢查非空、`R == S` 沒測到 `R != S`、
只測 body text、沒有跑真正的 WASM 路徑。→ **第四輪的 AG／AH／AI／AJ／AK。**

---

## 修法該放哪：**先是上游缺陷，但我方仍要加標註過的 workaround**

覆核找到一條我沒找到、而且很關鍵的證據：

> 上游自己的 tiled-rendering 測試明確宣稱 `RESET + END` 可以建立 selection，
> 見 `sw/qa/extras/tiledrendering/tiledrendering.cxx:151`。

**我逐字核對過，成立**：

```cpp
// Next: test that LOK_SETTEXTSELECTION_RESET + LOK_SETTEXTSELECTION_END can be used to create a selection.
pXTextDocument->setTextSelection(LOK_SETTEXTSELECTION_RESET, aStart.getX(), aStart.getY());
pXTextDocument->setTextSelection(LOK_SETTEXTSELECTION_END, aStart.getX() + 1000, aStart.getY());
CPPUNIT_ASSERT_EQUAL(u"Aaa b"_ustr, pShellCursor->GetText());
```

**所以我方用的序列正是上游測試保證的那一個**，這不是誤用 API。
它建議：引擎加**明確標註為版本相容 workaround** 的修法、同時送上游回報
**並附一支 regression test**（`.uno:SelectText → RESET → END` 必須成功），
等上游修好升級 core 之後再評估移除。

---

## 它列出的其他過度解讀（全部接受）

- 臂 B 固定座標選到的字從 `"C-ISOLA"` 變 `"E1-LC-"`，是**內容位移**，不能說「同一個有效範圍」。
- 臂 C 不是純 `.uno:SelectText`＋`RESET`，還含前置 RESET、html 讀回、後置 RESET。
- 臂 C 證明格式不是必要條件，**但不證明格式在 D 裡完全沒有交互作用**。
- 臂 F 同時做三件事，本身指認不了旗標。
- 臂 G 的程式碼註解「no other candidate does」**應刪**。
- H／I 證明的是「得到非空 selection」，不是「端點語意完全正確」。
- **`.uno:SelectAll` 發生在失敗嘗試之後**，而依 Claim 2 那一次已經治好狀態，
  所以它只證明事後可讀，**不證明失敗當下文件正常**；而且探針只記 byte count，沒存全文比對。
- 固定臂順序、共用同一 kit／profile；每臂雖重開文件，**未排除 kit／global order effect**。

## 它建議、但這一輪做不到的

直接讀 `SwWrtShell::IsInSelect()`（`sw/source/uibase/inc/wrtsh.hxx:154`，公開方法）。
**那是 `sw` 模組內部標頭，外部 LOK 探針拿不到**；要直接量就得寫成核心樹裡的
cppunit 測試並重編 `sw`——長時間編譯，歸使用者。

# 043 — `FN_SELECT_PARA` 讓 shell 停在選取模式，下一個 LOK 範圍選取被靜默丟掉

| | |
|---|---|
| **狀態** | **已確認（原生四輪＋WASM 一輪）／我方已加標註過的 workaround／上游未送** |
| **Bugzilla** | 未送。草稿：[`drafts/043-bugzilla.txt`](drafts/043-bugzilla.txt) |
| **發現日** | 2026-08-15（任務 #49） |
| **嚴重度** | 高——**上游自己的測試保證的 API 序列會靜默失效**，而且沒有任何錯誤 |
| **可重現** | 100%，原生四輪、Chrome 與 Firefox 各一輪 |
| **是否上游** | **是。** core `671c848b`（26.8）。**但見下方「樹的狀態」——尚未在乾淨樹上重現過** |
| **相關** | [039](039-the-discovery-selection-path-completes-at-most-once.md)（這是它的根因）、[040](040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md)（另一個上游缺陷，無關） |

## 摘要

派送 **`.uno:SelectText`** 之後，**下一個 `setTextSelection(RESET)` ＋ `setTextSelection(END)`
不會建立任何選取**，而且**不回報任何錯誤**：呼叫返回、游標移動了、
`LOK_CALLBACK_TEXT_SELECTION` **不廣播**、`getTextSelection` 回空字串。

**這不是誤用 API。** 上游自己的 tiled-rendering 測試就是這樣用的：

```cpp
// sw/qa/extras/tiledrendering/tiledrendering.cxx:151
// Next: test that LOK_SETTEXTSELECTION_RESET + LOK_SETTEXTSELECTION_END can be used to create a selection.
pXTextDocument->setTextSelection(LOK_SETTEXTSELECTION_RESET, aStart.getX(), aStart.getY());
pXTextDocument->setTextSelection(LOK_SETTEXTSELECTION_END, aStart.getX() + 1000, aStart.getY());
CPPUNIT_ASSERT_EQUAL(u"Aaa b"_ustr, pShellCursor->GetText());
```

## 機制

| # | 位置 | 做了什麼 |
|---|---|---|
| 1 | `sw/sdi/swriter.sdi:5649` | `.uno:SelectText` → `FN_SELECT_PARA` |
| 2 | `sw/source/uibase/shells/textsh1.cxx:1975` | 不在段首則 `SttPara()`，在段首則 `EnterStdMode()`；最後一律 **`EndPara(true)`** |
| 3 | `sw/source/uibase/wrtsh/move.cxx:402` | `EndPara(true)` → `ShellMoveCursor(this, true)` → `MoveCursor(true)` |
| 4 | `move.cxx:84` | `MoveCursor(true)` 呼叫 **`SttSelect()`** |
| 5 | `sw/source/uibase/wrtsh/select.cxx:421` | `SttSelect()` 設 **`m_bInSelect = true`** |
| — | — | **這條路徑上沒有任何地方呼叫 `EndSelect()`。** `ShellMoveCursor` 的解構子（`move.cxx:62`–`71`）只做 `StartAllAction`／`EndAllAction` |
| 6 | `sw/source/uibase/docvw/edtwin.cxx:7105` | 之後的 `setTextSelection(RESET)` 走 `bClearMark` 那一支：只 `ClearMark()`，**`bCreateSelection` 維持 false，`SttSelect`／`EndSelect` 都不呼叫** → 旗標存活 |
| 7 | `edtwin.cxx:7107`–`7111` | 呼叫端的 `END`：`HasMark()` 為 false → `bCreateSelection = true` → 呼叫 `SttSelect()` |
| 8 | `select.cxx:409` | **`if (m_bInSelect) return;`——提前返回，`SetMark()` 從未執行** |

沒有 mark 就沒有選取範圍；第 7 步的 `SetCursor()` 只是把游標移過去。
選取確實沒有改變，所以核心**也不會廣播** `LOK_CALLBACK_TEXT_SELECTION`——
呼叫端若在等那個回呼，就會一直等下去。

**同一份原始碼裡的搜尋是有配對的**：`sw/source/uibase/uiview/viewsrch.cxx:773`
的 `SttSelect()` 對上 `:846` 的 `EndSelect()`。**`FN_SELECT_PARA` 是例外。**

## 量到的

證據：[`evidence/sdk-e2/discovery/049-selection-after-format/`](evidence/sdk-e2/discovery/049-selection-after-format/)。
**每一輪的預測都在該輪執行之前 commit。**

### 原生（`build-native-26-8`，core `671c848b`，四輪）

| 臂 | 前置 | 結果（四輪一致） |
|---|---|---|
| 對照 | 無 | 選得到 |
| 只做格式指令 | `.uno:DefaultBullet` | 選得到 |
| **只做 `.uno:SelectText`** | 一次格式指令都沒有 | **選不到** |
| **完整 barrier** | 格式 → `.uno:SelectText` → 還原 | **選不到** |

**「只做 `.uno:SelectText`」那一格單獨就排除了格式指令**——起因是 `.uno:SelectText`。

### 旗標會被失敗的那一次自己燒掉

`edtwin.cxx:7121`–`7122` 的 `EndSelect()` 是照 `bCreateSelection` 呼叫的，
**不是照 `SttSelect()` 有沒有真的做事**。所以：

> **同一組座標連選兩次，中間不派送任何 uno 指令：第一次空、第二次選得到。**

這一格三輪一致，並且經過兩個分離對照（覆核指名的）：
**拿掉中間的讀取與等待，照樣治好**（所以不是 readback）；
**換成不呼叫 `EndSelect()` 的同一個 `SwCursorShell::SetCursor`，治不好**
（所以不是單純的游標移動或版面 priming）。

### 只有這一個指令

我方引擎會派送的 **20 個** uno 指令逐一測過（含 `.uno:Undo`／`.uno:Redo`／`.uno:ExecuteSearch`／
四個字元格式／四個段落與清單指令／`.uno:Delete`／`.uno:SwBackspace` 等）：
**只有 `.uno:SelectText` 毒化下一個範圍選取。**

### WASM（`e2-combination` ＝ `940b7723…`，Chrome 與 Firefox）

| step | 修之前 | 修之後 |
|---|---|---|
| 沒有 bounded readback 的那條路 | **逾時 10 001 ms** | **完成，回呼，10 ms** |
| 有 bounded readback 的那條路 | 完成 251 ms，選取 **`none`** | **完成，回呼，11 ms，選到文字** |

**沒有 bounded readback 的那一條只能靠回呼完成**，它從逾時變成 10 ms，
等於量到「回呼不會來」的原因是**選取沒有成立**，不是回呼在 WASM 這一層被弄丟。

## 我方的處置：**標註過的版本相容 workaround**

`wasm_sdk_probe/src/probe_engine.cpp` 的 `OXSDK_EDITOR_SELECTION_TEXT_HANDLES`
由 `RESET`＋`END` 改成 **`RESET`＋`START`＋`END`**。
`START` 走的是同一支 `SetCursorTwipPosition`，`bCreateSelection` 為真，
所以它結尾的 `EndSelect()` 會把旗標清掉，後面的 `END` 就能正常 `SetMark()`。

**語意經過量測，不是推的**：三個互異座標下，
`RESET(x0)`→`START(x1)`→`END(x2)` 在**壞狀態與正常狀態選到同一串字**，
而且**與正常狀態下 `RESET(x1)`＋`END(x2)` 選到的同一串**——所以它錨在 `START` 不是 `RESET`。
`END` 在 `START` 左邊的反向範圍也一致。

**上游修好之後應該拿掉。** 註解裡寫了拿掉的條件。

## 建議上游怎麼修（未經我方驗證）

1. **`FN_SELECT_PARA` 補上 `EndSelect()`**，與 `viewsrch.cxx` 的用法一致。最小、最貼近既有慣例。
2. **`SwWrtShell::SttSelect()` 的提前返回不要跳過 `SetMark()`**——把
   `if (!HasMark()) SetMark();` 移到 `if (m_bInSelect) return;` 之前。
   影響面比 (1) 大，但它修的是「呼叫者以為自己開了一個選取，實際上沒有」這個更廣的形狀。
3. **回歸測試**：在 `sw/qa/extras/tiledrendering/` 加一格——
   `.uno:SelectText` 之後，`RESET`＋`END` 必須建立選取。
   現有的 `testSetTextSelection`（`tiledrendering.cxx:151`）只在乾淨狀態下測過。

## 樹的狀態：**帶著五個本地修改**，而且要講清楚

`libreoffice-26-8` 在 `671c848b` 上有**五個未提交的修改**：

| 檔案 | 變動 | 對這件事的影響 |
|---|---|---|
| `desktop/CustomTarget_soffice_bin-emscripten-exports.mk` | −3 | Emscripten 專用 |
| `solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk` | 1 行 | Emscripten 專用 |
| `solenv/gbuild/platform/unxgcc.mk` | 1 行 | **整段包在 `$(if $(filter EMSCRIPTEN,$(OS)), …)` 裡**，改的是 `emdwp` 的觸發條件；原生 build 走不到 |
| `static/CustomTarget_emscripten_fs_image.mk` | +26／−3 | Emscripten 專用 |
| `vcl/qt5/QtFrame.cxx` | +2／−1 | Qt VCL plugin 的 IME input context；**原生重現跑的是 `svp`，不載入這個 plugin** |

**沒有一個在 `sw/` 底下。** 但這是「逐一檢查過」，**不是「在乾淨樹上重現過」**——
後者要一次完整重編，屬長時間編譯，**歸使用者**，已列在草稿的送出前清單裡。
報告草稿把這五個檔案**全部列出**，不是只寫一句「與本問題無關」。

## 送出前還缺什麼

- [ ] **重複單查詢七組都還沒跑**（草稿裡列著）。
- [ ] Component 欄位確認（`sw/uibase/{wrtsh,docvw}`，LOK 介面在 `sw/uibase/uno`）。
- [ ] **在乾淨樹上重現一次**（見上）。
- [ ] 把草稿裡那支 cppunit 測試實際編起來跑，確認它在修之前真的紅（要重編 `sw`）。
- [ ] 決定要不要一併送 patch——方向 (1) 是兩行。
- [ ] **送出本身要使用者按。**

## 這份**不宣稱**

- **不宣稱這是 WASM／Emscripten 特有的。** 原生一樣壞，四輪。
- **不宣稱直接量到了 `m_bInSelect`。** LOK 不暴露它（`SwWrtShell::IsInSelect()` 在
  `sw/source/uibase/inc/wrtsh.hxx:154`，是 `sw` 模組內部標頭）。
  量到的是它的**外部後果**：哪些前置會壞、失敗的那一次會自我修復、
  以及兩個把替代解釋排除掉的對照。要直接量得寫成核心樹裡的 cppunit 測試並重編 `sw`。
- **不宣稱其他呼叫 `SttSelect()` 而不配對的地方也存在。** 只掃過**我方引擎會派送的**指令。
- **不宣稱出貨的 `e1-editor-v1`（`835b453d`）受影響**——它沒有編進 format barrier，
  而其他二十個指令都不毒化，所以那條路上這個組合不存在。

# 計畫 2026-08-16g — block identity 的事前量測，以及三條 HIGH 產品路徑

依據 [`HANDOFF-2026-08-16f-e1c-requalified.md`](HANDOFF-2026-08-16f-e1c-requalified.md)
的「下一步」。**只收自主可執行的兩項**：relink 是你的決定（目前「等一等」），
不排進來。

## 為什麼是這兩項，而且是這個順序

交接列了四項。第 1 項（relink）不是我的。第 4 項六個佇列項裡有五個已經
withdrawn／characterised，`expectation: absent` 是「不要有人偷偷長出這個形狀」的
守衛，不是待辦。真正剩下的工作只有兩件：

| | 為什麼現在做 |
|---|---|
| **T1 block identity** | **時效性**：relink 還沒發生，現在寫下的預測才有事前性。而且它是 046（選過頭）、052（殘留）、同一行不同 x 三個模糊掛著的共同處方——但那句「一次關掉三個」**還沒被量過**，本身就是待驗的宣稱 |
| **T2 三條 HIGH 產品路徑** | 覆蓋率清單自己說了下一個 049 在哪裡；機器現在空著；不需要 relink，改的是 harness 不是 artifact |

## T1 — block identity：先量，再設計，最後才改引擎

### T1.0 先把預測寫下來（英文，證據命名空間）

`findings/evidence/queue-block-identity/native/PREDICTION.md`，在探針寫出來之前。

**已經從原始碼確定、不需要量的**（讀 core 26.8 得到，寫進預測當背景）：

- `getA11yFocusedParagraph()` 與 `LOK_CALLBACK_A11Y_FOCUS_CHANGED` 的酬載只有
  `content` / `position` / `start` / `end` / `listPrefixLength`
  （`sfx2/source/view/viewsh.cxx:862` `paragraphPropertiesToTree`）。
  **沒有任何段落序號。**
- `getCommandValues` 在 sw 只認 `TextFormFields`／`SetDocumentProperties`／
  `Bookmarks`／`Fields`／`Sections`／`ExtractDocumentStructure`／`Layout`
  （`sw/source/uibase/uno/loktxdoc.cxx:1186`）。`.uno:Layout` 只回每頁的
  `isInvalidContent`。**沒有一條能回答「caret 在第幾個 block」。**
- 通知是被文字差異擋住的（`if (m_sFocusedParagraph != sText)`，同檔 1204 行），
  但 `m_nCaretPosition` 每次都更新——所以**同步查詢**與**回呼**的資訊量不同。

**要量的四條，每條都寫成可以不成立**：

| | 預測 | 不成立的話代表 |
|---|---|---|
| P1 | 空段落選過頭那格：dispatch 當下 a11y `content` 是 `""`，而 readback 含有第二個 block 的文字 → **用內容比對抓得到 046** | 046 不能靠這個資料解，設計要另尋 |
| P2 | 點在文字下方，a11y 換到最後一段；**再點一次更下面，同步查詢回來的酬載一字不變** → **052 的殘留不會被 block identity 解掉** | 佇列項那句「一次關掉三個」成立 |
| P3 | 同一行不同 x：`content` 不變、`position` 變 → 這一格靠的是 **offset**，不是 block | 需要別的判別式 |
| P4 | 兩個**文字完全相同**的段落：兩次酬載 byte-for-byte 相同 → **a11y 給的是指紋，不是身分** | 內容就足以當身分，設計可以簡單很多 |

### T1.1 native 探針

`tools/queue_native_block_identity.cpp` ＋ `tools/run_queue_native_block_identity.sh`，
照 `f046_native_empty_readback.cpp` 的骨架（同一個 `build-native-26-8`、同一個
「一輪就是一筆紀錄、拒絕覆蓋」規矩、profile 目錄開在輸出底下）。
判讀離線：`tools/analyze_queue_block_identity.py`，自帶 self-test。

語料要有：一個空段落、**兩個文字相同的段落**、一段有文字的、以及文字結束後的空白區。
`test-docs/e1/empty-paragraph.odt` 只滿足第一項，需要新語料
（`create_*` 工具那一套，語料本身不進凍結集）。

**紀律**：native 量到的東西**不描述 WASM artifact**（048 的先例）；探針要能印出
不同值才算探針；不得指認肇因。

### T1.2 設計（zh-TW）＋ 佇列項改寫

量完才寫。可能的岔路已經看得到：

- **甲案**：引擎把 a11y 的 `content`／`position`／`listPrefixLength` 投影進
  `editorGetStateV2`（欄位現在只留長度，內容被丟掉）。不動 core、今天就能做，
  但在空段落與重複段落上是**指紋不是身分**。
- **乙案**：core патch 出真正的 node index。真的解得掉，但那是上游工作，而
  **上游送出目前擱置**。

**這一步若判不下來，我會先問你要不要叫 fable**，附上實測數字與我的傾向；
agent id 會記進交接。

### T1.3 引擎改動（只有在設計站得住時才做）

改 `src/probe_engine.cpp`，佇列項 `queue-verify-caret-by-block-identity` 從
`absent` 翻成 `present`——那正是佇列的用法：原始碼已進、等下一次 relink。

**動手前**：`make -n` 對三個 static target 各跑一次，證明沒有任何 artifact 會被
重連結（`make e1-editor-assets` 的教訓，以及 finding 041／042）。

## T2 — 三條 HIGH 產品路徑

進 `tools/run_e2_c_product_path.py`，每條各自帶一個會紅的突變：

| 路徑 | 檢查什麼 | 突變 |
|---|---|---|
| `action:undo` | 按產品自己的「復原」鈕，修訂號與文件內容都要退回 | 把 `session.undo()` 換成不做事／換成 rollback |
| `action:insert-text` | 把字打進 `#text` 再按鈕，字要出現在存出的 ODT 裡 | 讀錯欄位（049 的形狀） |
| `listener:click#notice-action` | **產品的復原路徑**：改一次文件後按「回到檢查點」，內容回到檢查點 | 把 `session.rollback()` 換成 `session.undo()` |

完成後把三條從 `uncovered` 移進 `driven`（各自寫 `by`／`how`），
`audit_product_path_coverage.py` 的 HIGH 清單應該歸零，7/28 → 10/28。

**注意**：這個 harness 的事件 `isTrusted` 是 false，**不是 D5、任何格子不得引用**。

## T3 — codex 對抗性審查

兩件事各送一次：T1 的設計（找「這個資料其實答不了那個問題」）、T2 的三條檢查
（找「這個檢查在缺陷還在的時候也會綠」）。回來的每一條我自己複驗，修的與記成
具名極限的分開寫——照 08-16e 那次的做法。

## T4 — 交接

規格修訂（SPEC E2-C 的產品路徑一節、佇列項的新措辭）、devlog、記憶。

## 不做的

- **relink**：你的決定。
- **上游送出**：擱置中。
- **改 core**：即使乙案勝出，也只寫設計，不動 `libreoffice-26-8`。
- **重編 WASM**：sweep 與判定之間絕不重編；T1.3 只改原始碼。

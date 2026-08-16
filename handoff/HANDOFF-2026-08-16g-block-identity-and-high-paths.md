# 交接 2026-08-16g — block identity 量完了；三條 HIGH 走完兩條，第三條掉出一個缺陷

上一份是 [`HANDOFF-2026-08-16f-e1c-requalified.md`](HANDOFF-2026-08-16f-e1c-requalified.md)。
計畫是 [`PLAN-2026-08-16g-block-identity-and-high-paths.md`](PLAN-2026-08-16g-block-identity-and-high-paths.md)。

## 一分鐘版

- **block identity 量完了，而那個佇列項的說法只對一半。** LOK 裡**沒有段落序號**；
  拿得到的段落文字是**指紋不是身分**。它解得掉 046（已量到的那些格）與「同一行
  不同 x」，**解不掉 052 的殘留**——而且原因量到了。
- **處方因此換了形狀**：不是「多回報一個欄位」，是**把 placeCaret 變成一個有回傳值
  的呼叫**。這一步是參考 MarkText 的 Muya 才看出來的：它的游標就是
  `{offset, block, path}`，**幾何只從模型往像素走，沒有一處從像素反推**。
- **三條 HIGH 產品路徑走完兩條**（`insert-text`、`undo`，各自被突變證明會紅），
  **第三條判 `NOT_ESTABLISHED`，並且第一次按下去就掉出
  [finding 053](../findings/053-the-product-prescribes-a-recovery-whose-button-it-does-not-show.md)**：
  產品開了一個它自己不提供的處方。
- **對抗性審查（codex）打在判準上收掉九條**，掉出 block identity 的 round 4。
- **relink 仍照你的決定等著**；佇列 26 項、9 項未做、**0 項擋連結**；三個 static 全綠。
- 本段四個 commit：`38c6a54` → `c9d0f6f`。

## 現在的狀態

| | |
|---|---|
| 分支 | `main` |
| E1 artifact／殼層 | `835b453d…`／v2 `187706b2…`，`E1_GO_ODT_EDITOR` |
| E2 artifact／殼層 | `572035ac…`／v8 `4daad6b4…` |
| 佇列 | **26 項、9 項未做、0 項擋連結** |
| 靜態 | `test-e1-c-static`／`test-e2-b-static`／`test-e2-c-static` 全部 exit 0 |
| relink | 未發生 |

## 一、block identity：三個模糊解得掉兩個

四輪 native（core 26.8），事前預測寫在
[`findings/evidence/queue-block-identity/native/PREDICTION.md`](../findings/evidence/queue-block-identity/native/PREDICTION.md)，
判讀離線、self-test **27 格**。

**讀 core 就確定、不需要量的**：focused-paragraph 酬載只有
`content`／`position`／`start`／`end`／`listPrefixLength`，**沒有段落序號**；
`getCommandValues` 也沒有一條回答得了「caret 在第幾個 block」。

**量到的**：

| | |
|---|---|
| 指紋還是身分 | **指紋**。兩個文字相同的段落，酬載**逐位元組相同**，而 caret y 從 2585 走到 2974（P-BI-4） |
| 046 | **解得開**：dispatch 當下 `'• '`，`.uno:SelectText` 讀回 `'    • \nBI-AFTER-EMPTY'`。引擎**已經收到**這份酬載，只是把 `content` 丟掉——連只留的 `contentLength`（2 對 14）都分得開（P-BI-7） |
| 同一行不同 x | **解得開**，但靠的是 `offset` 不是 block（13 → 45，P-BI-3） |
| 052 的殘留 | **解不開**。同一個 x 在行上讀 offset **4**、在文字下方讀 **7**（P-BI-6）——x 在行上帶入、在文字下方丟掉。**就算真有 block index 也沒用**：caret 確實就在最後一段裡，那個點擊沒有「應該去哪裡」可比 |

**指紋的極限正好打在 046 身上**：`empty-paragraph.odt`——046 量測用的那份語料——
結尾就是**兩個相鄰的空段落**，兩段 `content` 都是 `""`。所以這個處方**涵蓋 046 已量
到的那些格，不等於一般性地修好它**。

**設計與四條事前預測**：
[`research/DESIGN-2026-08-16-caret-by-block-and-offset.md`](../research/DESIGN-2026-08-16-caret-by-block-and-offset.md)。
`D-BI-1`（第二次點在文字外同一點要 200 ms 內回來）是這個設計的生死線；
`D-BI-2` 明說「短延遲下 a11y 的新鮮度沒有量過」。
**趁 relink 還沒發生寫的，所以它們有事前性。**

## 二、三條 HIGH 產品路徑

| 路徑 | 結果 | 突變 |
|---|---|---|
| `action:insert-text` | **PASS** | 讀 `el.text.placeholder` 而不是 `.value`（049 的形狀）→ 紅 |
| `action:undo` | **PASS** | `session.undo()` 換成 `Promise.resolve()` → 紅 |
| `listener:click#notice-action` | **`NOT_ESTABLISHED`** | `rollback` 突變宣告「預期抓不到」（那格跑不到）；**`toolbar-drops-the-list-action` 證明這格仍然會紅** |

**九個 arm 全部 `ok: true`**，證據在
[`findings/evidence/sdk-e2/e2-c-validation/product-path/round-2-high-paths/`](../findings/evidence/sdk-e2/e2-c-validation/product-path/round-2-high-paths/)。
**`NOT_ESTABLISHED` 不是藏身處**：那一格先要求 047 的順序**看得見地做了事**
（擋了 queue，或格式動作完成），否則判紅——
`toolbar-drops-the-list-action` 就是這道守衛的突變證明。

第三條為什麼跑不到：產品**只在** `recoverable-error`／`restart-required` 顯示那顆
按鈕，而那正是 `EditorSession.restart()` 接受的同一個集合。要走到那個狀態，唯一
有記錄的產品 UI 路線是 finding 047 的順序——**而它在現行殼層上跑不出來了**
（兩輪，三個動作在頁面內背靠背送出，28 ms 完成、狀態留在 `ready`）。
**這不足以判定 047 修好了**：047 是 08-15 在另一個 harness、048 修法之前的殼層上
量的，而 048 改掉的正是 `placeCaret` 等什麼。佇列項
`queue-047-may-have-closed-under-048`。

## 三、finding 053：產品開了一個它自己不提供的處方

`EDITOR_FORMAT_POSTCONDITION_FAILED` 的 `recovery` 是 `"rollback"`（D2 presweep
兩瀏覽器都記著），產品照 SPEC E2-B 5.13 把處方 toast 給使用者——**而那個錯誤不在
`RECOVERY_ERRORS` 裡**，所以 session 留在 `ready`、`#notice` 不顯示、按鈕不存在。

兩個集合的判準不一樣，而它們應該一樣：一個問「引擎還能不能用」，另一個問「文件
可能已經被改到了嗎」。**回到檢查點是為了後者存在的。**

**端到端重現還沒做**，路線寫在單子裡（在產品頁上把游標放到空段落再按項目符號）。
已量到的兩個半邊在 `findings/evidence/053/`。

**這是覆蓋率清單自己預測到的**：它把這條路標 HIGH，理由是「一條從來沒被走過的
復原路徑，就是一條沒有人知道會不會動的復原路徑」。第一次去按就掉出這個。

## 四、外部裁決（fable）：一個岔路我判錯了

兩個岔路送出去，**第二個把我推翻了，而且我核對之後同意**。
agent id `a71bfffebd6e98742`（要續談就用 SendMessage）。

### 岔路一：「瞄準 A 的突變毀掉 B 的見證」——結構成立，做法要改

裁決把耦合分成兩種，而處置不同：

- **可拆的耦合**（insert／undo 借了 IME 那三個字串當見證）→ **拆掉**。
  做法不是「再插一個自己的 marker」（那要多跑產品動作），而是**從這一輪自己前一次
  存檔推導見證集**：`{語料哨兵} ∪ {前一次存檔裡真的看得到的 IME 字串}`。
  **零額外動作，而且更寬**——見證是文件實際含有的東西。
  規則的正確形狀是：**檢查不得要求「別的檢查的主題」當見證，但可以要求它自己在
  前一次擷取裡驗證過的內容。**
- **產品拓樸造成的耦合**（存檔是頁面唯一的出口；undo 的主題**就是**「把 insert 收
  回去」）→ **申報**，而且要**機器驗證**：新增 `alsoNotEstablished`，
  跑完要核對那格真的是 `NOT_ESTABLISHED`，**若它其實跑了就報「申報過期」**。
  我原本以為只有存檔突變需要它——**錯了**，`insert-text` 用同一個機制毀掉 undo 的
  前置條件，所以它也要申報。
- 順帶：拆耦合會**失去**一件事——今天 ime 突變的連帶紅色，本來是「見證條款會紅」
  的意外證明。所以補一個 `undo-twice` 突變（undo 兩次，連上一個 IME commit 一起
  收回去）**故意**讓見證條款紅。

### 岔路二：053 該改哪一邊——**我判錯了，規格早就決定了**

我傾向改頁面。**規格 E2-B 5.13 第三條寫的是「host 進 `recoverable-error`」**——
不只是「處方是 rollback」。所以**頁面那一邊是對的**，殼層才是規格不符；改頁面等於
把對的接到壞的。

我另一個前提也是錯的：**修這件事不必動 E1-C 綁的檔案**。逐項核對：E1-C 的 bundle
只有 5 個檔案，**沒有一個在 `editor-shell-v2/`**；修法放在
`NarrowEditorV2Session.action()` 的 catch（算 `recoveryFor`，是 rollback 就
`_blockQueue(..., "recoverable-error", ...)` 再重新丟出）就到得了。

而我原本想的「讓 rollback 從 `ready` 也合法」被指出是**主動錯誤**：5.13 那條
「最多只損失那一個失敗的動作」是個**有界損失定理**，前提之一就是「queue 會擋」。
從 `ready` 放行 rollback 會刪掉那個前提，使用者繼續打的字會被靜靜丟掉，**損失無界**。

**仍然要付的代價**（裁決也同意）：`editor-shell-v2/` 在 **E2-C 殼層 bundle v8 裡**，
所以這個修法把殼層推到 **v9**，而今天的 D5 第七輪綁在 v8——**與今早 E1-C 同一個
形狀**。所以它是一次有計畫的動作，**今天沒有執行**。

裁決順帶指出第二個缺陷，我核對屬實 →
[finding 054](../findings/054-the-v2-page-reads-a-reload-flag-that-is-never-written.md)：
產品頁讀 `snapshot.requiresPageReload`，**沒有人寫那個名字**（寫的那一處在
`error.details` 底下，v1 的元件讀對了）。所以到達 Worker 世代上限時，
「重新開啟」仍然可按，而按了保證失敗。

## 五、053／054 的修法已執行：殼層 v8 → **v9**

裁決定案之後就做了。**artifact 未動、沒有 relink。**

| | |
|---|---|
| 殼層 | **v9 `eb76c5be…`**（`e2/editor-shell-v2-bundle-v9.json`；v8 原樣保留） |
| 改動 | `editor-shell-v2/narrow-editor-v2-session.js`（053）、`web/e2-editor-app.js`（054） |
| E1-C | **`E1_GO_ODT_EDITOR` 未受影響，`intact: true`、`failedProperties: []`**——實測，不是推論 |

- **053**：`action()` 排進佇列的那個操作**內部**攔一次，
  `recoveryFor(error) === "rollback"` 就 `_blockQueue(...)` 再重新丟出。
  **證據是接縫上的單元測試**：把修法拿掉，那一格會紅（14 → 13 pass、1 fail）。
  順帶記下：原本就有一格叫「a post-dispatch failure blocks the queue」，用的卻是
  **基底類別本來就處理的那個碼**——**名字宣稱通則、涵蓋只有一個實例**。
- **054**：改成同時看 `error.code` 與 `error.details`，而**檢查寫成通則**——
  「頁面讀的每個 `snapshot.<欄位>` 都要是狀態機真的會發布的欄位」，四個頁面一起查，
  還原修法會紅（5 → 4 pass）。
- **產品路徑補上一條真的路**：點行尾 → 分段 → 對新的空段落按項目符號（046 那一格）
  → 佇列被擋 → 按鈕出現 → 按下去回 `ready` → 還能存出真的 ODT。
  **HIGH 清空、11／28 已驅動**，而 `rollback` 突變**是 harness 自己報「宣告過期」**
  之後才變成真驗證的。

**但那一輪不是 053 修法的證據**：它掉出來的碼是 `MUTATION_OUTCOME_UNKNOWN`，
**本來就會擋佇列**。所以現在的狀態是：兩個集合對不上「已證明」、修法擋得住
「已證明」、**使用者按不按得到那個錯誤「仍未證明」**。

### 代價：D5 第七輪綁在 v8 上

那一輪的 attestation 記著 `4daad6b4…`（v8），而殼層現在是 v9。
**證據與判定原樣保留、也沒有被推翻，但它不再描述現行殼層**——與同日早上 E1-C 同一個
形狀，處方也一樣：**重新綁定要靠重跑**。D5 的主題是可信輸入，所以
**第八輪人工輪是欠著的**；在它跑完之前不得說「D5 在現行殼層上通過」。
已寫進 round-7 的 README 與 SPEC E2-C 9.5.15。

## 六、今天的三個教訓

1. **參考實作會改結論，不只是佐證。** 讀 Muya 之前，我判定 052 的殘留「多一個
   資料也救不了」；讀完之後看到的是**映射方向反了**——我們送出像素、再從矩形反推，
   而 Muya 從來不反推。處方因此從「多一個欄位」變成「換一種呼叫」。
2. **缺席型的判準要有見證，而見證不能借別的檢查的主題。** 「marker 不見了」對
   「undo 把文件清空」也成立。補見證是對的，但我借了 IME 那三個字串，於是瞄準
   IME 的突變一併弄紅了另外兩格。**借來的見證會被別人的突變打死。**
3. **對抗性審查要打判準，不要打結論。** codex 那輪 22 條裡有 18 條是「這個述詞說了
   它沒在測的話」，結論那側只被打到兩處措辭。指令要明寫「逐條構造一個
   『東西壞了但檢查仍然綠』的情境」。

## 下一步

1. **relink** —— 你的決定，目前「等一等」。門檻達成、blocking 空。
   **搭同一班車最值得的引擎工作仍然是 block identity**，而且現在有設計與事前預測了。
2. **D5 第八輪人工輪（欠著，需要 operator）** —— 殼層 v9 的重新綁定。
   四格的手勢與 round 7 相同，`tools/run_e2_c_d5.py` 已指向 v9。
3. **證明使用者按得到 `EDITOR_FORMAT_POSTCONDITION_FAILED`** —— 053 唯一還開著的
   那一列。目前只有 D2 那條直接驅動殼層的路產生過它；產品路徑走到的是
   `MUTATION_OUTCOME_UNKNOWN`。
4. **`queue-047-may-have-closed-under-048`** —— 兩個殼層代、兩個瀏覽器、四組對照
   照原樣重跑。
5. `findings/README.md` 的清單停在 048，**049–053 五筆沒有進去**（今天沒補，因為
   那張表一列就是一整段，補要補齊五筆）。

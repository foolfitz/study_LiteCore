# SPEC M3：有序指令（引擎 v23）——引擎改成 unipoll 單執行緒拓撲（候選 C）

狀態：**判準釘死（2026-10-20，含 fable 裁決 1 附錄 1 的答案；本檔「釘死」的第一個 commit）。**草稿是 `b943adb4`（檔頭寫明未釘死）。任何 v23 的執行——原生臂 N1、模型、實作、連結——都在本 commit 之後（CLAUDE.md「驗收判準的形式」§9.1「先於滿足」）。之後只准追加更正（同 §10）。

依據：

- **fable 裁決 1**（`findings/evidence/link-batch-v23/review/ruling-fable-1.md`，`cca06f7a`）與**附錄 1**（`ruling-fable-1-addendum-1.md`，`3b93c7e2`）。下文「裁決 §2.N」指裁決 1 的第 2 節，「附錄 §2.N」指附錄 1 的。兩者與本檔不同時以裁決為準。
- 計畫 `handoff/PLAN-2026-10-20-ordered-commands-v23.md`（普查 18 項，§2；裁決紀錄，§7）。
- 事實表：`handoff/link-batch-v23/facts-lok-command-ordering.md`（LOK 的佇列與跳數）、`handoff/link-batch-v23/facts-async-key-machinery.md`（`ee0f167e`，引擎裡為非同步鍵而蓋的機制與完成詞彙的消費者）。
- 原生量測：`findings/evidence/link-batch-v23/native/ordered-commands/`（`24c5b635`，**VERDICT C-HOLDS**）。
- finding 137（性質的反例）、156（unipoll 下 `runLoop` 不再跑 `Desktop::Main`）、040、096、129、142、151。
- `specs/SPEC-M3-link-batch.md` §13–§15（候選、固定三題、L-C-number-or-indent）。

證據標記：**已觀察**＝量過；**讀原始碼**＝沒量；**推論**＝從前兩者推出；**未量**＝沒有人量過，後面寫怎麼量。

## 1. 為什麼要有

**性質（一句）**：頁面要求的每一個文件指令，都照 Writer 自己會套用的順序套用。

今天不成立（finding 137）：在多執行緒 LOK 裡，方向鍵等加速鍵是兩跳的排隊事件（鍵本身一跳，`AsyncAccelExec` 再一跳），而引擎的貼字、`.uno:Delete`、`.uno:Bold`、`setTextSelection` 是當場同步執行，會插到還沒跑完的鍵前面：刪錯、字提早一格、格式套錯。鍵的跳數由 Writer 依文件狀態決定（編號段落開頭的 Backspace 一跳、文字中間兩跳），所以「把指令排進同一條佇列」或「在鍵後面放標記」都不保序（裁決 §2.2、§2.3）。〔已觀察：finding 142 原生臂 3/3；本批原生 q 模式 7 臂 × 5/5〕

候選 C（LOK 的 unipoll 單執行緒拓撲）之下沒有排隊中的鍵：排隊事件在呼叫裡直接執行、加速鍵同步派送、`postUnoCommand` 同步，所以指令照呼叫順序套用。〔讀原始碼：`lokhelper.cxx:1283-1288`、`acceleratorexecute.cxx:213-221`、`init.cxx:5316-5322`；已觀察：原生 unipoll 7 臂 × 5/5 照 Writer 的順序〕

Shift＋方向鍵（擁有者點名要的）與範圍上的方向鍵，只有在這個性質成立之後才安全（裁決 4、5），所以跟著這一批出。

## 2. 決定紀錄

| 項 | 決定 | 出處 |
|---|---|---|
| 範圍 | 計畫 §4 A：第 1、2 層；第 3 層只以「候選順便帶來的後果」進來 | 裁決 §2.1 |
| 候選 | **C**。原生量測 C-HOLDS（§3） | 裁決 §2.5、§2.6 |
| A′、原樣的 B | 撤回（兩跳鍵；跳數由文件狀態決定） | 裁決 §2.2、§2.3 |
| A | 不是本批的退路（復原證明只讓「完成」與跳數無關，「順序」仍有關） | 裁決 §2.4 |
| 退路 | B″（佇列非空時不送同步指令）；C 不可行時才量 | 裁決 §2.3 |
| 裁決 4「C 受 040 限制」 | 撤回 | 裁決 §2.5 |
| 096 的計數檢查 | **不改**；v23 上 B2 必須被執行到（§9.3） | 附錄 §2.1 |
| 柵欄 K1 | 撤回；游標處的刪除送使用者自己的鍵 | 附錄 §2.2 |
| 完成字串 | **全部留名字**，含 `verified-move-readback`；ABI 6 寫的是時間 | 附錄 §2.2 |
| 排空與完成 | 一次 poll 一個指令；回覆在下一次 poll；`anyInput` 算進待送的回覆；WASM 上 poll 不阻塞 | 附錄 §2.3 |
| 看門狗 | 不新增；沿用 SDK 的 30 秒逾時與復原路徑 | 附錄 §2.3 |
| `STACK_OVERFLOW_CHECK=2` | 搭診斷 profile；產品照舊不開 | 附錄 §2.4 |
| 0.2.28 | 不在本批；等擁有者的時段 | 裁決 §2.9 |

## 3. 原生量測的結果（已觀察，`24c5b635`）

`findings/evidence/link-batch-v23/native/ordered-commands/README.md`。三種模式：seq（多執行緒，每個指令穩定後才送下一個＝**實量的 Writer 順序**）、q（多執行緒，指令在觸發鍵的回呼裡排隊送出＝正向對照）、unipoll（候選 C，指令在 poll 回呼裡接連送出）。

- D1、D2、D2′、D3、D4、D5、D6：unipoll 的落點與 seq **5/5 相同**；q **5/5 排錯**。
- D8：unipoll 下鍵的效果在呼叫返回時就在（D5 的選取文字、D7 的復原紀錄），q 下不在。
- **D7（固定題第 2 題規定的內容）**，使用者自己的鍵，復原紀錄頂端（5/5）：

  | 位置 | 鍵 | unipoll 返回時 | 窗結束 |
  |---|---|---|---|
  | (i) P1 項目符號標籤前（文件開頭按一次未加 Shift 的 Left） | Delete | `Number On/Off` | `Number On/Off` |
  | (ii) 文件開頭，P1 有項目符號 | Backspace | `Number On/Off` | 同 |
  | (iii) 文件開頭，P1 有首行縮排 | Backspace | `Apply attributes` | 同 |
  | 一般 P1，文件開頭 | Backspace | 無 | 無 |

## 4. 範圍：普查 18 項逐項處置（裁決 §2.1：每一項一行，形式一）

| # | 項 | 處置 | 怎麼成立 |
|---|---|---|---|
| 1 | finding 137 的根治（刪錯、字提早、格式套錯） | **in** | 由構造；WASM 臂 W-D（§9.2） |
| 2 | L-142-readback-overtaken | **in** | 250 ms 讀回撤除（§5.3 A1）；WASM 臂「存檔後馬上移動再打字」N/N 正確（§9.3） |
| 3 | finding 151 的方向鍵那半 | **consequence**（由構造關閉；096 的檢查不改） | 成因是 250 ms 讀回帶舊游標，C 之下撤除；檢查點留著（附錄 §2.1） |
| 4 | L-md-137（Markdown 貼上屬 137 一類） | **consequence** | 貼上本來就同步；C 之下排在前面的鍵已跑完 |
| 5 | Shift＋方向鍵 | **in** | §6 |
| 6 | 範圍上的方向鍵（finding 129）＋ R1 | **in** | §6 |
| 7 | 延伸套件：格子（R1 的 42＋L-129 的 wrap、S1–S5、S2 的 16 格 v19 預紅、S-12）帶過來當臂與紅案；機制（resolver、規則 (a)、旗標、K1 柵欄、`AwaitingDeleteCompletion` 的等待、§12.5 的放寬）**不帶**，在 C 之下重新推導 | **in**（格子）／**out**（機制） | 裁決 §2.1 |
| 8 | v20 撤掉的三支產品路徑臂（insert 後 Shift、合併 Backspace 後 Shift、Shift+Right 按住 1 秒） | **in** | §6 |
| 9 | 偽造完成的殘留與 L-extend-prior-flush | **consequence**（由構造關閉，**前提是一次 poll 一個指令**） | 模型同步鍵模式印 0（§8）；完成＝返回＋下一次 poll（§5.2） |
| 10 | 邊界鍵的即時回答 | **consequence** | 返回時就知道；2.25 秒的窗撤除（§5.5） |
| 11 | 點擊的完成條件（finding 140 第二輪） | **consequence** | 滑鼠事件在呼叫裡執行（D6 5/5）；完成同 §5.2 |
| 12 | C 的 manifest 宣告 | **out** | 沒有讀者；v23 的讀者看 `editorContract.abiVersion ≥ 6`（附錄 §2.2） |
| 13 | L-C-number-or-indent | **consequence**（關閉） | 刪除改送使用者自己的鍵（§5.4）；D7 是 Writer 的答案 |
| 14 | 固定三題 | 必備內容 | §7 |
| 15 | 模型的粗體寬度限制 | 必備內容 | §8 |
| 16 | ABI 6 | 必備內容 | §5.8 |
| 17 | 096 那支計數檢查的 §34 裁決 | 必備內容，**已裁**：不改（附錄 §2.1） | §9.3 的 B2 讀法 |
| 18 | 「2.25 秒空窗期間打字」（工單 10-14m） | **consequence**（關閉） | 窗撤除 |

相鄰、不在本規格：第 1 項的 D6 臂（下一次在有入口的頁面跑第 1 項之前實作）。`STACK_OVERFLOW_CHECK=2` 搭診斷 profile（附錄 §2.4，§9.2）。

## 5. 設計（C）

### 5.1 拓撲與初始化

- WASM 引擎以 `SAL_LOK_OPTIONS=unipoll` 初始化 LOK；引擎執行緒成為 VCL 主執行緒。`runLoop` 註冊 poll 回呼；之後引擎自己呼叫 `Application::Execute()`（現行 `OXSDK_MAINLOOP_ENGINE` profile 的作法，finding 021）。引擎的阻塞式 `engineLoop` 退役，指令改由 poll 回呼排空。`#error`（`probe_engine.cpp:15-17`）由新的接線取代，不是刪掉。
- **finding 156 的後果（附錄 §2.5 第 6 項）**：今天的多執行緒產品**有**跑 `Desktop::Main`（`lo_startmain` → `soffice_main` → `ImplSVMain` → `ImplSVMainRun` → `mpApp->Main()`，`svmain.cxx:224-235`）；C 之下**不會跑**（`ImplSVMain` 早退，`svmain.cxx:196-197`；WASM 上洩漏的 Desktop 被裝成 `mpApp` 但沒有 `Main()`）。上游自己的 unipoll 用戶端各補一點：iOS 補 `SfxApplication::GetOrCreate()`（`init.cxx:8294`），Android 補擴充套件的註冊「讓字典能用」（`:8296-8300`）；Collabora 的 core 留著 `Main()`。SfxApplication 由 SfxModule 建立時的 `GetOrCreate()` 產生（`sfx2/source/appl/module.cxx:83`，讀原始碼）；WASM 上第一次開檔前由誰觸發，**未讀**。→ §9.2 的 S-init 臂逐項點名。具名限制 **L-no-desktop-main**（§11）。

### 5.2 完成的定義（取代 250 ms 讀回與第一個回呼規則）

- **一次 poll 只排空一個指令。**（現行 `mainLoopDrainCommands` 一路排空，`probe_engine.cpp:6688-6750`；**改掉**。）頁面的佇列本來就一次送一個（`editor-session.js:287-311`），實務上沒有代價。
- **poll 什麼時候被呼叫**（附錄 §2.3 更正了草稿）：`ImplYield` 一個 tick 先派一個使用者事件、有就返回（`svpinst.cxx:440-444`）；否則 `CheckTimeout()` 跑一個排程工作（`:446-447`）；然後 `if (!bMustSleep && !anyInput()) return`（`:453-455`）；之後才 poll（`:471-481`）。所以 poll 出現在**沒有使用者事件**、而且（**這個 tick 沒跑別的工作**，或**用戶端的 `anyInput` 為真**）的 tick。LOK 的回呼 flush 是排隊的使用者事件（`init.cxx:2577-2580`），所以指令 N 返回後的第一次 poll 之前，N 的 flush 已經派送。
- **硬規則（每個 tick，形式一）：`anyInput` ＝ 有指令排隊 ∨ 有回覆待送。**（今天的 `mainLoopAnyInputCallback` 只看指令，`probe_engine.cpp:6845-6851`；不改的話，長文件上每個回覆都要等版面整理的閒置工作做完。）
- **硬規則：WASM 上 poll 不阻塞。**一次 poll 最多排空一個指令或送一個回覆，然後立刻返回；節奏由 100 fps 的 tick 決定。（今天 mainloop 在 poll 裡最多等 1 秒，`:6795-6819`；改掉。重入保護 `:6822-6835` 留著。）
- **指令的完成＝它的 LOK 呼叫已返回，且之後的第一次 poll 已到；回覆在那次 poll 送出。**不再有 250 ms 讀回、不再以「第一個回呼」當證據、不再有等回呼的期限。
- **回覆的欄位不得取自走計時器的回呼**（`STATE_CHANGED`、尺規）的快取：那類回呼本來就晚到（附錄 §2.3；N1b 記錄）。格式狀態直接讀，或沿用 html 讀回（§5.3 A7）。具名限制 **L-timer-class-callbacks**（§11）。

### 5.3 既有機制逐項處置（裁決 §2.5：每一項寫它還守什麼，或撤回）

依 `facts-async-key-machinery.md` 的 A1–A13：

| # | 機制 | 處置 | 理由 |
|---|---|---|---|
| A1 | 250 ms 移動讀回（096 的修法） | **撤回等待**；名字 `verified-move-readback` 留給「沒有移動的鍵」（§5.8） | 前提（沒變的鍵不發回呼、等回呼會卡死）不在 |
| A2 | 第一個回呼就完成（規則 (a)） | **撤回**；有移動的鍵在 flush 的 tick 以 `documented-callback-visible-cursor` 回答（那個回呼確實到了，而且只可能是這個鍵的） | 效果在返回時就在 |
| A3 | 選取柵欄刪除（K1、`AwaitingDeleteCompletion`） | **撤回**，改送使用者自己的鍵（§5.4） | 前提（finding 016）不在；D2、D2′、D5、D7；附錄 §2.2 |
| A4 | C 的窗（2.25 秒） | **撤回窗**（§5.5）；名字 `verified-boundary-noop` 留著 | 返回時就知道 |
| A5 | 合併鍵的復原路徑（Esc、K2、柵欄、15 ms 輪詢、2000 ms `key-deadline`） | **撤回時間與柵欄**；`judgeAfterKey` 的整份比較**留下**當返回時的證明；`key-deadline` 不再出現 | Esc／K2／歸屬只因 K1 是排隊鍵而存在 |
| A6 | 各階段期限（七個常數、1 秒閒置上限） | **撤回**；**不新增看門狗**，沿用 SDK 的 30 秒（附錄 §2.3） | 等的東西在返回時就有；同步呼叫能跑多久是另一個量 |
| A7 | 格式柵欄 | staging 與 5 秒期限**撤回**；**事後讀回（html）留下**；059 的狀態檢查不得讀走計時器的回呼快取 | 讀回沒有非同步前提 |
| A8 | 定位游標（138 的雙條件、400 ms grace、250 ms 讀回） | 完成改 §5.2（`documented-callback-*`／`verified-caret-readback`）；**138 的「位置或選取與點擊前不同」條款留下** | D6 |
| A9 | `extend_completion.hpp`（規則 (a)、旗標） | **撤回**（沒有引擎檔案引用它；只剩模型）；L-extend-prior-flush 的關閉依賴一次 poll 一個指令 | 裁決 4 已撤旗標 |
| A10 | 打字退路（`paste()` 失敗時逐字送鍵） | **留下**，回覆改在 §5.2 的點 | C 之下回覆不再先於效果 |
| A11 | 引擎迴圈的等待（`values[0]` 1／2／3、三個讀回指令） | **撤回** | 只為喚醒等回呼的引擎 |
| A12 | 跨執行緒機械（`gMergeMutex`、「在回呼裡不動作、排一步」） | 互斥鎖**撤回**；「回呼裡不呼叫 LOK」**變成硬規則**（§5.7） | 跨執行緒前提不在；重入前提還在 |
| A13 | 037／040 的保護 | **留下**，直到連結後臂 040-W 過（§9.2） | 裁決 §2.8(e) |

096 的檢查點（`CHECKPOINTED_MOVES`，`narrow-editor-v2-session.js:124-127`）**留著**，理由改寫成「在髒文件第一次移動之前先存起來」（「按鍵可能弄死 session」的前提在 C 之下不成立，撤回的是那句宣稱，不是守衛；附錄 §2.1）。它在 C 之下唯一的代價是延遲，§9.2 記錄。

### 5.4 刪除

- 游標處的 Backspace／Delete：送**使用者自己的鍵**（KEYINPUT＋KEYUP，在呼叫裡執行）。證明：返回時的 `.uno:Undo` 整份與送出前比（`judgeAfterKey`）；變了＝`verified-key-undo`（`keyUndo.actionsAfter ≥ 1`，凍結的 client 要求，`narrow-editor-v2-client.js:161-166`）；沒變而且游標、選取都沒變＝`verified-boundary-noop`，`changed:false`，版本不變（client `:372-374`）。
- 範圍上的刪除：照今天送 `.uno:Delete`（同步）→ `uno-command-result`。
- **後果**（附錄 §2.2）：文字中間的游標刪除不再以 `verified-selection-delete` 完成；client 兩者都收（`DELETE_COMPLETION`）；綁 v21 的判讀工具（`run_v21_d2.py:111-121`）不在 v23 上重跑；v23 自己的判讀工具對每一次游標刪除期望 `verified-key-undo`。
- **L-C-number-or-indent 因此關閉**：(i)–(iii) 的答案是 Writer 自己的 `Number On/Off`／`Apply attributes`（§3 D7），在返回時讀到。

### 5.5 邊界鍵與「沒有作用的鍵」

- 返回時復原紀錄、選取、游標都與送出前相同 → 在下一次 poll 立即回答「沒有作用」（移動：`verified-move-readback`；刪除：`verified-boundary-noop`），`boundaryNoop.waitedMs`／`keyUndo.keyToUndoMs` 是實際的毫秒數（預期約一個 tick）。2.25 秒的窗撤除。
- 頁面的「保留按鍵」（finding 141／144 的 `holdsDelete`／`settleDelete`）的前提是窗；窗撤除後它守什麼，由殼層的判準在實作前寫（§9.3）。

### 5.6 卡死

不新增看門狗（附錄 §2.3）。一個同步 LOK 呼叫若真的不返回（例：finding 037），由 SDK 既有的 30 秒請求逾時（`document-sdk.js:160`、`:243`）與復原路徑接手。§9.2 記錄最慢的誠實指令要多久；要縮短這個界限是之後另一個裁決，帶著記下的數字。

### 5.7 硬規則（形式一：每一個指令、每一個回呼、每一個 tick）

1. **指令內不得 `Application::Yield`、`Scheduler::ProcessEventsToIdle`、`Application::Reschedule`**（裁決 §2.8(a)1）。紅案：一個在鍵與讀取之間排空另一個指令的測試 build，證明讀到的是另一個變更。
2. **回呼裡不得呼叫 LOK**：今天的 `probe_engine.cpp:2875-2880`（註解送 `.uno:Escape`）改成排到下一次 poll。紅案是引擎單元測試裡的源碼檢查（不是計數檢查，§34.8）。
3. **所有 LOK 呼叫都在引擎執行緒**（040 的前提）：正向對照見 §9.2 的 040-W。
4. **`anyInput` 算進待送的回覆；WASM 上 poll 不阻塞**（§5.2）。

### 5.8 ABI 與完成詞彙

- 編輯器 ABI **6**：新的動作（延伸、範圍上的移動）加在 `kMaxInternalEditorAction`（25，`probe_engine.cpp:7281`）之後，**加之前先讀界限**（CLAUDE.md「工作結論」）。
- **完成字串全部留名字**（附錄 §2.2）：`documented-callback-*`、`verified-move-readback`、`verified-caret-readback`、`verified-key-undo`、`verified-boundary-noop`、`uno-command-result` 都照字面意思用。理由：凍結的 E2-C client 只認這些（`MOVE_COMPLETIONS`，`narrow-editor-v2-client.js:146-148`）；換名字會讓回答被當成壞掉、進入復原、session 死掉——而 096 的檢查看不出來（「死了但有檢查點」那一支也算過）。`editor-shell/editor-client.js`、`editor-session.js` 綁著 E1-C 的判定，也不動。
- **ABI 6 寫的是時間**：每一個完成都在返回後一個 flush tick 之內，沒有偽造的情況。`key-deadline` 不再出現。
- **形式一**：每一個回覆的 `completion` 都是凍結 client 對該後置條件類別接受的字串之一——引擎單元測試裡的靜態表，不是計數檢查。
- **wasm 位元組偵測**（`run_merge_wasm_shakedown.py:208`，`check_m3_production_ui.py:653` 引用）**不改**（§34.1 凍結）：字串照字面意思還在 `probe.wasm` 裡，`declared: true`，R 臂被要求「無作用」——那正是 v23 的行為。v23 的讀者看 manifest 的 `editorContract.abiVersion ≥ 6`。若 v23 的 shakedown 報告被綁 v20 的條款誤判，那份報告就是 §34.1(b) 的證人：修判讀工具、不修 runner、重判，因執行而修 1。

## 6. 第 2 層：延伸與範圍上的移動

- 新動作：Shift＋Left／Right／Up／Down／Home／End（延伸），以及範圍起點的一般移動（finding 129：在範圍上按方向鍵收合）。都是使用者自己的鍵，在呼叫裡執行，完成同 §5.2。
- manifest 的 gestures：新動作要寫 `gestures`；**扣住的動作寫 `gestures: []`，不是省略**（CLAUDE.md「工作結論」）。
- 判準：R1（129 的 42 格＋L-129 的 wrap 格）、S1–S5、S2 的 16 格 v19 預紅、S-12（按住 Shift）、三支產品路徑臂（§4 第 8 項）——逐格的協定在實作前追加（§9.3）。

## 7. 固定三題（第一輪審核；`SPEC-M3-link-batch.md` §13.4）在 C 之下

1. **FIFO 鍵的復原證明能不能被另一個變更滿足**：C 之下引擎是唯一改文件的執行緒，指令之間不讓出（§5.7 規則 1）；證明在返回時讀，同一個呼叫裡沒有別的變更能插進來。紅案見 §5.7。
2. **一個什麼都沒做的鍵，頁面怎麼知道**：返回時復原與游標都沒變，在下一次 poll 回答，並確認沒有晚到的、回覆所依賴的回呼（N1a）。測試位置：§3 D7 的 (i)–(iii) 與一般 P1，附原生的 `.uno:Undo` 頂端。
3. **表格或行內物件裡，鍵的行為和今天的拒絕不同**：格子開頭／結尾的鍵、跨格的選取、as-char frame——臂在 §9.3 追加；「今天的拒絕」與「Writer 的順序」衝突時，**預設照 Writer**（裁決 §2.8(a)3）。

## 8. 模型（`wasm_sdk_probe/tests/extend_completion_model_test.cpp`）

在本規格釘死之後、實作之前，跑兩種模式（裁決 §2.7）：

- **多執行緒模式**（紅案，證明產生器還活著）：照舊印出條件 32／33 的母數——27,744、2,448、5,474、3,868（`findings/137-…md:40-43`）。印不出來就停。
- **同步鍵模式**（C）：每一種形狀（含條件 33 的兩種）印 **0** 個與 Writer 不同；完成定義為「返回＋下一次 poll」、一次 poll 一個指令時，偽造完成那一類為**空**。
- 模型一節要寫的兩個限制：條件 40 的（粗體不改模型裡的矩形寬度）；新的——**模型的鍵是單一事件、沒有跳數**（只對已撤回的 FIFO 類候選有關）。
- 形式：每一種形狀（形式一）。預設：模型沒跑 → 不寫引擎碼。

## 9. 判準總表

### 9.1 實作之前（原生，不連結；附錄 §2.3）

- **N1a（硬，形式一）**：原生 unipoll，對 §3 的每一支臂與每一種指令（鍵、`postUnoCommand`、`paste`、點擊），**回覆所依賴的回呼**——`INVALIDATE_VISIBLE_CURSOR`、`TEXT_SELECTION`（含 `_START`／`_END`）、`UNO_COMMAND_RESULT`、`INVALIDATE_TILES`——在指令返回後的**第一次 poll 之前**全部送達。N=5。紅案：一份把一個這類回呼挪到第一次 poll 之後的合成報告 → 紅。
- **N1b（記錄，不是判準）**：走計時器的回呼（`STATE_CHANGED`、尺規等）每一種相對第一次 poll 的延遲。**正向對照**：離開表格那一格必須記到非零的 `STATE_CHANGED` 延遲；為零代表 harness 看不到晚到的回呼，N1 整組不成立。
- **N1c（硬，形式一）**：`anyInput` 兩種模式（含／不含「有回覆待送」），在 200 段的文件上做一次合段之後，「不含」那種的第一次 poll 延遲必須比「含」長。延遲相同＝沒有版面整理的閒置工作跑起來＝這一臂沒量到東西（NE）。
- **M1／M2**：§8 的兩種模式。
- **預設**：N1 沒跑 → 不寫引擎碼；N1a 不過 → §5.2 的完成定義不成立，回到裁決。

### 9.2 第一次連結＝診斷 profile（擁有者的 make；裁決 §2.8(e)、附錄 §2.4、§2.5）

先只接線 §5.1–§5.3 與 §5.7，**不加任何功能**，帶 `-sSTACK_OVERFLOW_CHECK=2`（同時開著 `CHECK_NULL_WRITES`，記錄），連成診斷 profile。判準（兩個瀏覽器，N=3，除非另寫）：

- **S-open／S-type／S-move／S-save**：開檔、打字、移動、存檔的 smoke。
- **S-init（附錄 §2.5 第 6 項）**：點名產品用到、而依賴 `Desktop::Main` 層初始化的功能，逐項對 v22 比：內建字典／擴充套件（拼字、斷字——若產品有用到）、自動校正、`OpenClients` 做的復原掃描、依賴 `RequestHandler` 的路徑；或記下「產品一個都沒用到」。
- **W-D**：§3 的 D1–D6 經引擎的線上動作在 WASM 上跑，落點等於原生 seq 的落點，N=5。
- **040-W**：finding 040 的兩個入口（`doc_destroy`、在帶 frame 的 SwDoc 上 `doc_getTextSelection`）在 C 之下**返回**；正向對照：從 JS 側執行緒呼叫一個 LOK 入口**要卡住**（逾時之內）。
- **溢位**：任何一格若以無法歸因的中止失敗，先由擁有者連一份不帶旗標的診斷 profile 再下結論（附錄 §2.4）。
- **記錄、不當閘門**：
  - tick 間隔、回呼延遲、`keyToUndoMs`（對 v20 的 [30, 32, 33] ms）、finding 122 的延遲；
  - **最慢的誠實指令**：開最大的 fixture、64 KiB 的 Markdown 貼上、存 `long60`——形式一：每一個都在 SDK 的界限（30 秒）之內完成；紅案是一個永遠不返回的測試指令，必須在界限內進到復原路徑；
  - **S-move-dirty**：檢查點「第一次移動前先存」在 `long60` 上的延遲；
  - `STACK_OVERFLOW_CHECK=2` 的三個數字：`probe.wasm` 大小、開檔時間、C2 打字時間（對 v22 只是上界；乾淨的差值等 §9.3）。
- 預設：診斷 profile 的任何一格不過 → 不做功能接線。

### 9.3 第二次連結＝功能 profile

§6 的動作、§5.4 的刪除、殼層的對應改動。逐格的協定**在實作之前追加**（CLAUDE.md §9 的四個條件）：R1、S1–S5、S2 預紅、S-12、三支產品路徑臂、L-142 的「存檔後移動再打字」、L-C-number-or-indent 的三個位置經產品路徑、固定題 3 的表格／frame 臂、頁面「保留按鍵」的新判準。

**096 的讀法（附錄 §2.1 第 4 項；形式二，工具生成）**：v23 上每一次跑產品路徑 runner，`a-boundary-arrow-press-does-not-cost-the-work` 的報告 `clausesExercised` 必須含 **B2**。沒有 B2、或 B2 為假 → **產品紅**（C 退化成有排隊中的鍵），不是改檢查。檢查本身、它的突變、`check_soak_bank.py`、`tests/test_product_path_mutations.py` 都不改。截止：v23 第一次乾淨的計數執行。

### 9.4 計數

K：v22 累積的未計數改動（交接 10-20 的清單）加上 v23，在擁有者指定的時段、脫離 session、先問（記憶 `release-count-batched`）。

## 10. 連結順序

1. 釘死本規格（本 commit）。
2. N1a／N1b／N1c、模型兩種模式。
3. 兩席審核（opus＋`codex exec -s read-only < /dev/null`）：固定三題，加上附錄 §2.2 的詞彙表與 §2.3 的 `anyInput` 規則各一題。
4. 診斷 profile 的引擎碼（紅案先行），**擁有者連結**，§9.2。
5. 功能的引擎碼與殼層，**擁有者連結**，§9.3。
6. 宿主、綁定、K。

## 11. 具名限制

- **L-native-harness-init**：原生 harness 的初始化不是產品的（不呼叫 `runLoop`、自己做三個註冊、補 `SfxApplication::GetOrCreate()`；finding 156）。量的是派送拓撲，由原始碼看與 Application 物件無關；**未量**。
- **L-no-desktop-main**：C 之下 `Desktop::Main` 不跑（finding 156）；§9.2 S-init 點名受影響的功能。
- **L-timer-class-callbacks**：`STATE_CHANGED`、尺規等走計時器的回呼在第一次 poll 之後才到；回覆的欄位不得取自它們（§5.2）。
- **L-no-ime-arm**：IME／ext-text 在 unipoll 下沒有臂（今天打字走 `paste`）。
- **L-writer-only**：Calc、Impress 沒有跳數分析。
- **L-mouse-hops**：`MouseButtonUp` 之後的跳數沒讀（D6 的落點正確，但沒追到每一跳）。
- **L-flush-order**：同一次 flush 裡 `UNO_COMMAND_RESULT`、`TEXT_SELECTION`、游標的順序在 unipoll 下沒量；N1a 的紀錄順帶記下順序。

## 12. §34.4

- 原生工具（`oc_native.cpp`、`read_results.py`）是新增；判讀工具在第一次計數使用前做一次雙席審核（§34），併在 §10 第 3 步。
- 本批到目前：因執行而修 0（d7i 的位置是在任何計數執行之前改的，記在 smoke/NOTES.md），因審核而修 0。附錄 1 沒有改任何計數檢查。

## 13. 已裁的四題（附錄 1）

- Q1 → 附錄 §2.1：096 的檢查不改；B2 的讀法（§9.3）。
- Q2 → 附錄 §2.2：柵欄撤回；完成字串全部留名字（含 `verified-move-readback`）；位元組偵測不改；ABI 6 是宣告。
- Q3 → 附錄 §2.3：一次 poll 一個指令；`anyInput` 與不阻塞的 poll；不新增看門狗；N1 拆成 N1a／N1b／N1c。
- Q4 → 附錄 §2.4：`STACK_OVERFLOW_CHECK=2` 搭診斷 profile。

## 14. 模型兩種模式的結果（2026-10-20，只追加；§8 的判準沒有改）

證據：`findings/evidence/link-batch-v23/model/`（README、`test-output.txt`、`red-mutation.txt`）。測試檔 sha256 `6201a62d…`，跑一次 24 秒，exit 0，結尾 `ok`。

- **多執行緒模式（紅案）**：照舊印出 27,744、2,448、5,474、3,868。後兩個這次也釘成 `fail(...)`。SECTION D 以外的輸出，與改動前的測試逐位元組相同（兩者都是 `bf5a4064…`）。
- **同步鍵模式（C）**：每一種形狀都是 **0 個與 Writer 不同、0 個偽造回覆**。形狀是 v20 鍵與全部鍵，各四種：只有移動、Backspace、打字、行內格式；後兩種就是條件 33 的兩種。「與 Writer 不同」比的是整個結束狀態：文字、游標、mark。另外，八種先前操作在每一種形狀都出現；凍結 client 接受的六種回答也都出現。
- **C 的紅案**：拿掉 §5.2 的任一條規則，都印出偽造回覆。
  - 回覆在指令自己的 poll、flush 之前送出：偽造 2,969,934，與 Writer 不同 557,568。後者是 Backspace，快照過期，選了範圍形式，被 gate 拒絕。
  - poll 落在一次 flush 的兩個回呼之間：偽造 2,575,890，與 Writer 不同 0。這是模型的性質：快照只決定刪除的形式，而 gate 讀的是引擎自己的快取。這不是產品的宣稱。
- 新檢查自己先紅過一次：把 pin 改成 5475、把同 poll 回覆塞進主 C 模式，exit 1、18 個 FAIL。
- **限制**（§8 要寫的兩條，加一條）：
  - 鍵是單一事件，沒有跳數；
  - 粗體不改矩形寬度（條件 40）；
  - **頁面一次只送一個項目，所以「一次 poll 一個指令」在模型裡從來沒有被爭用，這個模型分辨不出它**。它由 §5.2 守，要在引擎上查（§9.2）。
- §8 的預設「模型沒跑 → 不寫引擎碼」解除。
- §34.4：模型的 C 模式與兩個 pin 是新增，因執行而修 0，因審核而修 0。

## 15. 兩席審核 1 與裁決 2（2026-10-20，只追加；更正寫在這裡，原文不動）

來源：
- 工單 `findings/evidence/link-batch-v23/review/REVIEW-BRIEF-two-seat-1.md`（`152949f5`）；
- 兩席原文 `codex-review-1.md`、`opus-review-1.md`（`ef673ecc`）；
- 主 session 的核對 `review/disposition-1/`；
- 裁決 2 `review/ruling-fable-2.md`（`18e961d0`，擁有者選 A 叫 fable 裁決），後面附主 session 的原始碼核對。

### 15.1 游標處的刪除（取代 §5.4 的證明方式、§5.5 的條件；裁決 2 §2.1）

- **已實測**（`review/disposition-1/grouping/`）：在 `uni1` 下，穿過 30 個底線連按 25 次 Backspace 或 Delete，第 20–25 次返回時 `.uno:Undo` 與前一次逐位元組相同，但每一次都刪了一個字。原因是 Writer 把同類字元的刪除併成一筆，說明文字被截短在 20 字。
  - 照 §5.4／§5.5 的寫法，Delete 會回答 `verified-boundary-noop`（意思錯），Backspace 則兩條都不符合。
  - 中文一句二十幾個字很平常，所以這是一般使用者路徑。
- **證人改成兩個一起看**：`.uno:Undo`，加上焦點段落的同步讀法 `getA11yFocusedParagraph`（內容與游標位置）。兩者都在按鍵之前與返回時、在同一次 poll 裡讀，中間不讓出。規則：
  - 復原變了，且新的 payload 解析得出 ≥ 1 筆 → `verified-key-undo`；
  - 復原沒變，**按鍵前游標嚴格在段落中間**（Backspace：position ≥ 1；Delete：position < 長度），而段落內容變了 → `verified-key-undo`、`changed:true`、版本 +1、`actionsAfter` 取新 payload 的筆數；
  - 其餘 → `verified-boundary-noop`。
- **§5.5 的「游標、選取都沒變」不再是條件**：它沒有同步來源，頁面要的也只是「文件有沒有變」。
- **前提**（主 session 的核對）：只有 a11y 可用時才用這個讀法。產品 core `build-a11y-gate0` 有把 a11y 編進去（`ENABLE_WASM_STRIP_ACCESSIBILITY 0`）。引擎記錄 a11y 不可用時，判定不得悄悄退化成只看復原。
- **沒量之前不寫 §5.4 的引擎碼。** 量測是：
  - g1／g2 加上 a11y 讀取，`uni1` 與 `seq`，N=5；
  - 三個對照：25 個中文字、表格後一段的段首 Backspace（Writer 原地不動）、文件末端的 Delete；
  - 只看復原的判法要在第 20–25 次判錯，這支臂本身就是紅案。
- **「意思」的三層測試**：
  - 原生：判成「刪了」的次數 ＝ 存檔少掉的字數；
  - 引擎單元：把原生錄下的輸入當 fixture，標籤由存檔推出（形式二）；
  - 產品路徑：真鍵盤 25 次 Backspace 刪一句中文，頁面版本每次 +1。這是 §9.3 的新判準，四個條件寫在裁決 2 §2.1，第一次乾淨的計數執行之後封閉。
- **預設（量不出來或不成立）**：游標刪除維持今天的柵欄路徑，L-C-number-or-indent **重新登錄為未關閉**（§4 第 13 列），附錄 1 §2.2 撤柵欄那句改成「以 §15.1 的量測成立為前提」。

### 15.2 撤回與更正

- **§1（`:22`）「`postUnoCommand` 同步」**改成：只有帶 listener，或非 `Asynchron` 的 slot，才同步。不帶 listener 的 `.uno:Escape`（`Asynchron`）在 unipoll 下仍會排隊，在下一次 poll 之前完成。
- **§5.2（`:94`）「沒有使用者事件的 tick」**改成「tick **開頭**沒有使用者事件」：那個 tick 裡的排程工作可能再 post 一個，在下一個 tick 送出。
  - 新增規則：回覆待送又有指令排隊時，**先送回覆**。
- **§5.8（`:149`）「每一個完成都在返回後一個 flush tick 之內」撤回**，改成「在返回後的第一次 poll；沒有固定的 tick 數」。`CheckTimeout()` 每個 tick 會在 poll 之前跑一個排程工作，而拼字、自動完成、字數統計不看 LOK 的 `anyInput`。
- **§5.2、§5.3 A7、§11「`STATE_CHANGED` 是計時器類」撤回**（附錄 1 的原句）。實量是逐項的：`.uno:Bold`、`.uno:ModifiedStatus` 5/5 在指令自己的 flush 裡到達，表格與剪貼簿的狀態晚到。
  - 回覆只准讀「準時清單」上的 `(指令種類, 狀態項)`。清單由 `read_n1.py` 從紀錄產生（形式二），引擎的讀取表用單元測試去對。
  - 收合游標上的行內格式，回覆讀這次 flush 裡的那一項狀態，059 的檢查保留。
  - 四種行內格式的狀態項加進 N1a 的「回覆依賴的回呼」，**下一次 N1 執行起算**。
  - L-timer-class-callbacks 改成列出晚到清單，同樣由工具產生。
- **§9.1 N1a 的 `INVALIDATE_TILES` 撤回**：沒有任何回覆讀 tile，而且原生 282 個 process 裡一個 tile 回呼都沒有，那是一支沒有正向對照的「沒發生」臂。
  - N1a 是**有界的觀測**：每個 op 第一次 poll 之後的 1500 ms，最後一個 op 則到量測步驟安靜為止。已 commit 的資料在界外為 0。
  - 剩下的盲點要寫明：落在 op N+1 開始與 N+1 第一次 poll 之間的回呼，會被當成 N+1 準時。
- **§9.1 N1c 的標籤「沒有版面整理的閒置工作跑起來」**改成「poll 之前有某個排程工作跑了，是哪一個沒有辨認」。
- **§14「0 個偽造回覆」**改成「沒有回覆的選取或游標矩形與 core 不同」。模型的完成字串由它自己的 oracle 選，測不到意思（opus 的 E6：174,672 筆標錯照樣 `ok`），模型不加新模式。
  - §14 與 `model/README.md` 說「一次 poll 一個指令在引擎上查（§9.2）」，但 §9.2 沒有那一格；見 15.4。
- **§4 第 11 列**縮成「**文字**點擊的完成條件」。
- **§4 第 13 列**：關閉以 §15.1 的量測成立為前提。

### 15.3 新的具名限制（§11 追加）

- **L-object-click-shell-switch**：點選框或繪圖物件之後，Writer 把換 shell 延後 120 ms（`view.cxx:567-574`、`:844`），在那之前送出的指令會在點擊前的 shell 上解析。
  - 基準是「穩定後的 Writer」（seq），點擊的完成**不等**這 120 ms。
  - 原生臂（§9.3）：點 as-char 圖，接 Bold／Delete／Backspace／Left，三種模式：seq、uni1、uni1 隔 150 ms。N=5，落點對 seq。
- **L-idle-content-after-reply**：欄位在閒置時更新，桌面 Writer 也這樣，不是 C 帶來的。§9.2 只記錄。
- **L-anyinput-starves-idle-layout**：`anyInput` 也把 `PaintTile`／`EditorGetState` 算進去，頁面持續繪製時，背景版面整理一直被打斷。§9.2 只記錄。

### 15.4 §9.2 追加的格與前提（CLAUDE.md §9 的四個條件：寫在任何診斷執行之前；被裁決 2 點名；形式寫在各條；第一次乾淨的診斷執行之後封閉）

- **一次 poll 一個指令**：
  - 引擎單元紅案必備：兩個指令排隊、一次 poll，只准排空一個；舊的「一路排空」要紅。
  - §9.2 一格：每次 poll 記錄進入時的佇列深度與排空數，判讀是「沒有一次 poll 排空超過一個」（形式一，資料由工具產生）。**要有一次 poll 進入時深度 ≥ 2 才算量到，否則 NE**；診斷 harness 要繞過頁面的序列佇列，同時送兩個指令。
- **tile 延遲記錄**：一次看得見的編輯之後，第一個 `INVALIDATE_TILES` 相對回覆的延遲。至少看到一個才算量到。
- **前提（形式二，讀建置紀錄）**：診斷 profile 不得定義 `OXSDK_FINDING_016_SCHEDULER_PROBE`，因為 `EditorDrainScheduler` 會呼叫 `ProcessEventsToIdle`，違反 §5.7 規則 1。
- **延遲記錄**（不釘數字）：
  - 開最大的 fixture 後、在 `long60` 合段後，第一個回覆等了多久；
  - 持續繪製與閒置時，背景版面整理要多久才穩定。

### 15.5 判讀工具（§34.3 的那一次審核）

`read_results.py`、`read_n1.py` 的修正都算**因審核而修**，每一項都帶紅案，並用修正後的工具重判已 commit 的資料，判定不得移動：
- F1：只做記錄的 D7 也要乾淨，D8 的觀測要齊，D7 要逐輪列印；
- F2：run-log 每一格恰一筆，exit 0；
- F3：不乾淨的格只能給 NE，不能給 FAIL；
- d4 加存在證人（這個 op 的步驟裡要有 `.uno:Bold=true`）；
- 裁決 1 §2.6 的紅案 (b)「輪次不一致」補上；
- 每一種回覆型別各一個晚到紅案；
- 印出 N，N < 5 不算計數的讀法；
- N1c 的標籤照 15.2 更正；
- `REPLY_TYPES` 拿掉 tile。

修完之後，這兩支的因審核而修必須是 0。

### 15.6 順序（裁決 2 §4）

1. 這一節（追加）；
2. 判讀工具修正與重判；
3. 三支原生臂（g1／g2＋a11y、N1 重跑、物件點擊），都是原生、不連結；
4. 全部過了才寫診斷 profile 的引擎碼，由擁有者連結。

### 15.7 游標刪除證人的原生計數：G-HOLDS（2026-10-20，只追加）

證據：`findings/evidence/link-batch-v23/native/caret-delete-witness/`。判準 `ARMS.md` 在執行前釘死（`e129ac42`），判讀工具 `read_g.py` 帶 7 個紅案。共 50 個 process，全部 exit 0。

- **uni1 每一格（N=5）**：配對判定器判成「刪了」的次數都等於存檔少掉的字數：底線 Backspace、底線 Delete、25 個不同的中文字都是 25；表格後段首、文件末端兩個對照都是 0。
  - 只看復原的判定器在兩支底線臂每輪都是 19，紅案每輪都成立。
  - **返回時讀到的焦點段落已經反映這一下按鍵**，每一輪每一下都是。裁決 2 §2.1 第 5 項要求實測的前提，現在是「已觀察」。§15.1 的引擎碼可以寫，附 a11y 可用的防護。
- **更正裁決 2 §1 與 §2.1**：中文那一臂只看復原也是 25/25。說明文字截短後保留前後幾個字，連續刪除不同的字時，前端每一下都會變。**只有一長串相同字元**才會讓 payload 不變，例如填空線 `____`、`……`、`－－－`、`0000`。
  - 所以破洞是「填空線」，不是「中文句子」。
  - §15.1 的產品路徑判準（裁決 2 §2.1 寫成「25 次 Backspace 刪 25 個中文字」）照原樣**到不了**這個洞，要加一段相同字元串，例如 25 個全形底線 `＿`。這條判準仍在任何產品路徑執行之前，所以這是追加，不是事後移動（CLAUDE.md §9）。

## 16. 裁決 3：診斷 profile 的引擎碼裝什麼（2026-10-20，只追加；更正寫在這裡，原文不動）

來源：工單 `findings/evidence/link-batch-v23/review/brief-fable-3-diagnostic-scope.md`（`b86c8277`，擁有者選「送 fable 裁決」）；裁決 `review/ruling-fable-3.md`（§§1–4 與 §5 補充，後附主 session 的原始碼核對）。下文「裁決 3 §N」指該檔。

### 16.1 診斷 profile 的游標刪除與 §9.3 的更正（裁決 3 §2.1，A）

- 選 A：診斷 profile 的游標刪除就是 v23 要出貨的路；不把選項 B 的期限與輪詢接進 poll 迴圈（那是為撤回的宣稱造機械，而且多一個沒有原生對照的變數）。
- **§9.3（`:202`）「§5.4 的刪除」更正為「§5.4 的殼層與判讀那半」**：client 的期望、§15.7 要求的相同字元串產品路徑臂、L-C-number-or-indent 三個位置經產品路徑。引擎那半屬 §9.2（§9.2 接 §5.3，A3 的替代就是 §5.4 的鍵路徑；「不加任何功能」讀作「不加新動作、不改殼層」）。
- **`#error`（`probe_engine.cpp:15-17`）的替代**：兩道靜態閘——(i) `OXSDK_E2_V23_LINK_BATCH` 必須搭 `OXSDK_MAINLOOP_ENGINE`，並遞移地要求 v21 的 define；(ii) `OXSDK_MAINLOOP_ENGINE` 配 `OXSDK_MERGE_KEY_UNDO` 仍是錯，除非定義 `OXSDK_E2_V23_LINK_BATCH`——v23 只 include `merge_key_undo.hpp` 的純函式（`classifyUnit`、`judgeBeforeKey`、`judgeAfterKey`、`summarizeUndoPayload`），不編選項 B 的階段、期限與輪詢。紅案（引擎單元測試）：v23 上沒有動作到得了 `startSelectionBarrierDelete` 的舊階段機或 `startMergeKeyUndo`；阻塞式 `engineLoop` 不編譯。

### 16.2 出貨 core 沒有 a11y：§15.1 的前提更正（裁決 3 §5）

- **事實（已觀察）**：出貨線 v8–v22 連 `wasm-lite/build-headless-probe`（`ENABLE_WASM_STRIP_ACCESSIBILITY 1`），不是 `build-a11y-gate0`（只有 v5 a11y 線用）。證據：v22 的連結紀錄、兩顆 core 的 `config_wasm_strip.h:5`、v22 `probe.wasm` 含 `core-built-without-accessibility` 而不含 `lok-lacks-*`、v22 Firefox shakedown 實量 `a11y.enabled:false`。
- **更正 §15.1（`:276`）的前提句**「產品 core `build-a11y-gate0` 有把 a11y 編進去」：那句描述的是 v5 a11y 線。裁決 2 檔尾的主 session 核對同錯，已在該檔追加更正。G-HOLDS 是原生量的，對出貨 core 什麼都沒說。
- **§15.1 的引擎碼只在有 a11y 的 core 上編譯**（`#if !ENABLE_WASM_STRIP_ACCESSIBILITY`），只隨「產品線換到 a11y core」那次連結出貨；診斷 profile 在現行 core 上不會跑到它。§15.7「§15.1 的引擎碼可以寫」限定在 a11y core。
- **現行 core 上的游標刪除＝柵欄的 C 形狀（§15.1 預設的 C 版本）**，一個指令做完、不分階段、沒有期限：K1（Shift＋方向鍵，呼叫裡跑完）→ 返回時 `readSelection()`：
  - NONE → `verified-boundary-noop`（`changed:false`，`boundaryNoop.waitedMs`＝K1 送出到回覆的 poll）；2.25 秒的窗不存在；
  - TEXT、非空、≤ 128 bytes、無分隔符 → `.uno:Delete`／`.uno:SwBackspace`（帶 listener，同步）→ 返回時 `readSelection()` 必須是 NONE，否則 `MUTATION_OUTCOME_UNKNOWN` → `verified-selection-delete`；結果回呼與收合回呼是 poll 時的證據，不是閘門；
  - TEXT 含分隔符（合併）→ 同步 `setTextSelection(RESET, caretBefore)` 還原、確認 NONE、P0、送使用者自己的鍵、返回時讀復原、`judgeAfterKey`：變了且 ≥ 1 筆 → `verified-key-undo`；沒變 → `verified-boundary-noop`；`key-deadline` 不再出現。不需要 a11y（段落邊界只看復原）。
  - 非 TEXT → `EDITOR_BOUNDARY_UNSUPPORTED`，照舊。
- **RESET 還原先原生量再寫**（CLAUDE.md §7）：N=5，P2 段首（一般、編號、首行縮排）K1 Shift+Left、RESET 回 K1 前的游標矩形、NONE、再 Backspace；復原頂端與存檔要等於該位置不經 K1 的使用者 Backspace（D7 的方法）；紅案：RESET 偏一行要讀到不同落點。**量不出來的預設**：在指令裡送 `.uno:Escape`（Asynchron，下一次 poll 之前完成），鍵在下一次 poll 當成一個無條件的步驟送出（前提：`readSelection()` NONE 且快取游標等於 `caretBefore`），沒有期限。
- **L-C-number-or-indent 在出貨 core 上重新登錄為未關閉**（§4 第 13 列改為「出貨 core 上未關閉；原生（§15.7）與 a11y core 上關閉」）。
- **A3（只給功能連結）**：K1 為 NONE 時改送使用者自己的鍵、只看復原，可不靠 a11y 關掉 L-C；先要原生臂（D7 四個位置、G 的 t1 對照、找「K1 為 NONE 但鍵會刪字」的位置），N=5。沒跑的預設：NONE 回答「沒作用」，限制維持未關閉。
- **產品線要不要換到 a11y core 是擁有者的裁示**，記憶裡 08-20 的「產品 core 定為 writer calc」與出貨線實際的 core 不一致，這裡只登錄、不裁。要換就是獨立一次連結、自己的判準。

### 16.3 「staging 撤回」＝一個指令（裁決 3 §2.2，(a)；更正 §5.3 A7）

- 格式柵欄在一個指令裡做完：派送（帶 listener）→ 還原到派送前 → `.uno:SelectText` → `readSelection()` → 046 指紋 → 037 型別防護 → html 讀回 → 還原 → **以 `readSelection()` 為 NONE 確認還原**。不排 `EditorFormatBarrierStep`、沒有 `stageDeadline`。
- **包含檢查撤回**（它讀回呼餵的矩形，一個指令裡沒有；前提「柵欄進行中有別的指令搬動游標」在一個指令裡不存在）。具名限制 **L-format-read-identity-by-content**（§11）。
- 034 的空末段：`.uno:SelectText` 返回後 NONE → 在回覆的 poll 以 `MUTATION_OUTCOME_UNKNOWN` 拒絕，不等 5 秒。
- 同一讀法管所有還活著的階段機。註解路徑：`.uno:Escape` 從指令裡、在 `InsertAnnotation` 返回後送出（不帶 listener，Asynchron，排在 `InsertAnnotation` post 的事件之後、下一次 poll 之前）；不再從回呼裡呼叫 LOK（§5.7 規則 2）。
- 紅案（引擎單元測試）：`.uno:SelectText` 什麼都沒選到 → 在那次 poll 拒絕；舊的等待式階段機要紅。

### 16.4 回覆在 poll 組；證明不在＝當場型別化拒絕（裁決 3 §2.3）

- **§5.7 規則 5（硬規則，形式一）：`onLokCallback` 不組回覆；每一個回覆都在指令返回後的第一次 poll 組出來送出。**回呼只更新快取、記證據（相符回呼的型別與序號、UNO 結果、搜尋與註解的 payload）。`editor-state` 事件與原始 `lok` 事件照舊從回呼送。紅案：一個「游標然後選取」的合成 flush，回覆要兩者都帶；舊的發法要紅。
- 移動／放游標／選取：有記到相符回呼 → `documented-callback-<型別>`；沒有 → `verified-*-readback`、`changed:false`。UNO 動作：在 poll 時對 flush 之後的快取跑 059 的檢查。
- **回覆依賴的證明在那次 poll 不在 → 在那次 poll 以型別化拒絕回答，寫明少了哪個證明；不等、不開計時器、不分指令種類。**編輯動作：`postUnoCommand` 返回時就失敗 → `LOK_COMMAND_FAILED`（文件未變）；派送了卻沒有結果 → `MUTATION_OUTCOME_UNKNOWN`，`failureShape: "proof-absent-at-poll:<回呼名>"`。SDK 操作（搜尋、加註解）用既有的不重送代碼。
- **更正工單**：`.uno:ExecuteSearch` 不是 Asynchron（`sfx.sdi:1181-1196`），unipoll 下不帶 listener 也同步，不會排到 poll 之後。

### 16.5 §9.2 追加的格與前提（CLAUDE.md §9 的四個條件：寫在任何診斷執行之前；被裁決 3 點名；形式寫在各條；第一次乾淨的診斷執行之後封閉）

- **證明不在的拒絕**（形式一，工具產生的計數）：診斷 profile 上零筆；**正向對照**：一個診斷專用、故意不給證明的測試指令要剛好算到 1，否則 NE。
- **a11y 狀態**（取代裁決 3 §2.1 第 3 項「零筆 undo-only」那格，該格連同 `witness:"undo-only"` 路徑撤回）：(i) 形式一，每次開檔：診斷 profile 的狀態回報 `a11y.unavailable == "core-built-without-accessibility"`；(ii) 形式二，位元組讀：`probe.wasm` 含 `core-built-without-accessibility`、不含 `lok-lacks-setAccessibilityState`，由 `tools/check_v23_diagnostic_build.py` 讀，紅案先行。
- **W-D 的出處（更正版）**：d2／d2′ 走柵欄的 C 形狀（K1＋`.uno:Delete`／`.uno:SwBackspace`），d5 是延伸移動＋`delete-selection`；另加兩格：P2 段首的合併（`verified-key-undo`）與 D7 的四個位置（立刻回答「沒作用」，限制已登錄）。N=5，形式一。
- **功能連結的建置前提**（形式二，同一支腳本）：診斷專用 define 不存在。
- 診斷專用的儀器（每次 poll 的深度與排空數、永不返回的測試指令、故意不給證明的測試指令、從 JS 端執行緒呼叫 LOK）全在一個診斷專用 define 之下，只能經診斷入口觸發，不在 SDK 的公開介面。

### 16.6 ABI（裁決 3 §2.4；附註 §5.8 與 §13）

- 診斷 profile 維持編輯器 ABI 5（ABI 跟動作清單走）；6 留給功能連結的新動作。附錄 §2.2「`abiVersion ≥ 6` 就是返回時語意」只對綁定的 profile 成立；§9.2 的判讀工具認 profile 身分（manifest 的 `profile`＋wasm 雜湊），不認 `abiVersion`，餵 v22 的 manifest 要拒絕（紅案）。

### 16.7 §11 追加的具名限制

- **L-format-read-identity-by-content**：v23 上格式讀回的段落身分只靠 046 的內容指紋；重排把派送前的游標移出段落、而鄰段文字完全相同時分不出；074 的放棄照舊。
- **L-barrier-unit-geometry-post-hoc**：柵欄的派送前單位檢查只剩型別、大小、分隔符；單一矩形的幾何檢查變成 poll 時的證據。它在 v20–v22 是否單獨擋過，可從那幾版的 shakedown 證據讀（形式三，一次性）；§9.3 的表格／frame 臂是它的測試。

### 16.8 §34.4

本節沒有動任何計數檢查或原生判讀工具：因執行而修 0，因審核而修 0。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-20 | 草稿（opus，主 session），依裁決 1 §4 第 3 步，`b943adb4`。未釘死。 |
| 2026-10-20 | 依附錄 1（`3b93c7e2`）改定並**釘死**：§2 決定紀錄、§4 第 3／9／12／17 列、§5.1（156 的後果）、§5.2（poll 的條件、`anyInput`、不阻塞、回覆不讀計時器類快取）、§5.3（A1／A2 的名字、A6 不新增看門狗、096 的檢查點留著）、§5.4（刪除完成字串的後果）、§5.6、§5.7 規則 2 與 4、§5.8（名字全部留著）、§9.1 N1a／b／c、§9.2 的 S-init、溢位、記錄、§9.3 的 B2 讀法、§11 兩條新限制。草稿 §5.8「`verified-move-readback` 在 v23 不再出現」是主 session 的錯（附錄 §2.2）。 |
| 2026-10-20 | §14（追加）：模型兩種模式的結果——多執行緒照舊印出四個母數（後兩個新釘）；C 在每一種形狀都是 0 與 0；兩個紅案都印出偽造回覆；新限制：一次 poll 一個指令在模型裡分辨不出。 |
| 2026-10-20 | §15（追加）：兩席審核 1 與裁決 2——游標刪除的證人改成復原＋焦點段落（先量才寫碼，預設柵欄）；撤回「`postUnoCommand` 同步」「一個 flush tick」「`STATE_CHANGED` 是計時器類」「N1a 的 tile」「0 個偽造回覆（意義）」；新限制三條；§9.2 新格與前提；判讀工具修正清單；順序。 |
| 2026-10-20 | §15.7（追加）：游標刪除證人原生計數 G-HOLDS（uni1 配對 25/25、只看復原 19、對照 0）；更正裁決 2「中文句子」的說法：破洞是相同字元串；產品路徑判準要加相同字元串。 |
| 2026-10-20 | §16（追加）：裁決 3 與其 §5 補充——診斷 profile 帶 v23 的刪除路徑、§9.3 更正、`#error` 的替代；**出貨 core 沒有 a11y**：§15.1 的前提更正，現行 core 上游標刪除是柵欄的 C 形狀（RESET 還原先原生量），L-C 在出貨 core 上重新登錄為未關閉，判定器只在 a11y core 編譯；staging 撤回＝一個指令、包含檢查撤回；§5.7 規則 5（回覆只在 poll 組）、證明不在當場拒絕；§9.2 新格與前提；ABI 5；兩條新限制。 |

## 17. 恢復 v23：K1 讀取大小界限的釐清（2026-10-25，只追加）

擁有者明確要求恢復 v23，並授權 Astra 代為裁示。裁決見 `findings/evidence/link-batch-v23/pre-link/astra-proof-and-k1-ruling.md`。本節補充 §16.2，不改原文；寫在診斷引擎接線、原生 RESET 計數及任何診斷瀏覽器執行之前。

**保留既有 v22 的 4096-byte 合併讀取上限**（`verifyAndDispatchSelectionBarrierDelete`），作為現行 headless 診斷版的支援界限。這不是新增原生或瀏覽器母體，也不以新的等待機制維持舊宣稱。K1 的同步讀取分類為：

- NONE：立即回答沒有作用，L-C 限制維持登錄。
- TEXT：必須有文字、非空、UTF-8 解碼成功且不超過 4096 bytes；不滿足就型別化拒絕，不派送刪除或無條件的使用者按鍵。
- 在上述可讀範圍內，先辨識分隔符；含分隔符才進入待原生 RESET 量測成立的合併還原分支，因此 129–4096 bytes 的分隔符選取不會被 128-byte 單位上限誤拒絕。
- 不含分隔符時，沿用安全文字單位的 128-byte 界限，tab／物件占位字元仍拒絕。

原本要求的合成 K1 三分支測試同時涵蓋 128、129、4096、4097 bytes；這是既定單元紅案的邊界輸入，不新增計數閘門。RESET 引擎還原碼仍必須等既定 N=5 的原生量測通過才能寫；若量測永遠未做，預設就是未成立，不能連結該分支。

## 18. 原 RESET 失敗與版本化還原測量（2026-10-25，只追加）

擁有者編譯原生 harness 後，原凍結九臂各 N＝5 共45個程序皆正常結束，但原reader判為 **RESET-FAILS**（`native/reset-restore/reader-result-01.json`）：15組restore的存檔形狀、游標矩形及undo頂端均等direct，後續Shift定位卻全部讀不到選取。這不是把幾何正確推成狀態正確；既有判準與失敗不改寫。原始碼的ClearMark未EndSelect、後續SttSelect因m_bInSelect提早返回，支持選取模式殘留的因果推論，內部旗標本身未直接量測。

Astra裁決先測同步Q候選：同一記錄點連續RESET→START→RESET，中間不讀取、不yield、不等待。以新版本`native/restore-v2/tool/oc_native.cpp`承載，保留原工具及雜湊可重讀。DELETE三種P2×direct／Q／錯點各N＝5，共45；FORMAT另依`format/ARMS.md`四種路徑×Shift／handles各N＝5，共40。兩者讀取器自可執行arms產生母體，核對provenance、存檔／undo、後續選取與反例；各自未做或失敗即未成立，不能互相代證。第五輪完成即封閉該讀取；不為等到喜歡的結果而續跑。兩者成立才准各自採用Q，不增加新產品動作。

同一新binary預備原§16.2的async Escape備案，**Q先行，備案不自動啟動**。F操作在同一poll做K1＋無listener的Escape，緊接G在下一poll先驗NONE及cache游標等原點才送使用者鍵；以pollIndex恰差1證明，F/G間不得有quiet window或固定睡眠。若Q足夠成立就不跑備案；若需啟動，先完成其已登錄45程序的獨立runner／reader與紅控制。若永遠未啟動，預設未成立，不得寫該引擎路徑。FORMAT不得假定Escape可修復，既有finding049限制保留。

此階段沒有改core、沒有重新連結WASM、沒有動宿主服務或使用者文件。下一個人類步驟只編譯已審查的新版本小型原生harness，單次供兩個Q測量與有條件備案使用；不是舊v23連結命令。

## 19. 診斷 W-D 的私有輸入路由（2026-10-25，只追加）

本節記錄擁有者授權 Astra 的路由裁示，來源為 `findings/evidence/link-batch-v23/pre-link/diagnostic-packaging/private-wd-routing.md`。原生 DELETE45 與 FORMAT40 已各自依凍結判準通過，且整批輸入雜湊未變；本次追加發生在那85筆封閉之後、任何候選 WASM 連結或 W-D 執行之前，不回頭改原生判準或結果。

實讀 v22 manifest 後發現：字元移動只允許 collapsed gesture，但既定 W-D 的 d4 要在 Shift+Right 後於範圍上按 Left，d5 要先延伸再刪除選取；原生 L 落點觀測也要 Shift+End、Shift+Home。ABI5 診斷版若完整保留原公開合約，無法從那些公開入口送出全部既定輸入。

裁示為保留 manifest、公開 gesture 檢查與 ABI5，僅由單一 `OXSDK_E2_V23_DIAGNOSTIC` 私有入口補足具名 W-D 測試輸入：種類4為有 TEXT 選取時的 Left，5／6為 Shift+Left／Right，7／8為 L 觀測用 Shift+End／Home。它們沿用公開移動的同一個指令佇列、`dispatchOrderedKey` 與首次 poll composer，不接受任意鍵碼或 UNO 名稱，也不新增公開動作或能力。實際來源檢查必須保留公開 gate 與私有前提；私有 worker 的封閉 whitelist 拒絕種類9。

W-D 報告逐步標示公開或私有來源，並獨立核對實際 worker requests；其結論只涵蓋同一組原生輸入在 C 拓撲的落點。**這不代表 ABI6 的公開 Shift／範圍移動功能已驗收。** 那一層仍依 §9.3 另做功能身分、公開手勢與產品路徑驗證。未執行 W-D 的預設仍是未成立。沒有擴增 §9.2 的母體；首次乾淨診斷計數後依既定截止封閉。

## 20. S-init 有限比較與040量測入口更正（2026-10-26，只追加）

本節依擁有者授權Astra裁示，完整協定見 `handoff/RULING-2026-10-26-v23-s-init-and-040.md`；寫在S-init行為計數及更正後040計數之前。原候選 `e2-editor-v23-diag` 與WASM `52cf9d23…` 保持凍結，不覆寫。

**S-init**：工具固定六格 `direct-load-reopen`、`input-teh`、`input-quotes`、`input-number`、`paragraph-break`、`linguistic-layout`，實際v22與後繼診斷候選、Chrome／Firefox、各N=3，共72格。逐格保存實際候選／資源包／儀器／fixture身分、wire輸入與回覆、存檔及必要畫面資料。前三種文字輸入比實際 `method` 與存檔結果；換段獨立比結構；語言格含相同文件的自動斷字開／關對照，比固定區域像素、頁面幾何、存檔語言／斷字設定。母體由工具表生成；缺格、重格、錯身分、不同輸入、缺輸出不得過，並先以因果紅案守住。實際v22功能在後繼失效是FAIL，不能改稱未使用。

通過後只關閉「具名產品路徑的有限S-init比較」。來源可處置的擴充套件編譯guard、headless復原掃描guard、直接LOK載入路徑與行為證據分開記錄。擁有者代理明確接受 `L-no-desktop-main` 下仍未成立的殘餘：沒有正向區辨觀測時的字典／服務可用性、未曝露的有效拼字／自動校正設定、沒有自然觸發時的paste失敗按鍵fallback，以及略過 `disableRecovery` 的長時間效果。這些不是PASS，也不另開無截止閘門；禁止據此宣稱沒有語言功能使用或完整初始化等價。未跑有限比較的預設仍是NE並擋功能接線。

**040更正有實際反例**：`post-link/attempt-01/bounded-01/report.json` 的Chrome第1輪kind3，在 `plain-grapheme.odt` 的NONE選取上約1.31ms返回 `DIAGNOSTIC_CONTROL_RETURNED`，session仍ready。原24格保留原始結果與失敗，不改判。這否證「任意JS側LOK入口一定卡住」；040決定性條件是非主執行緒解構含frame的SwDoc，空選取沒有建立該條件。此更正指名量測儀器前提不足，不宣稱產品已過。

只新增後繼 `e2-editor-v23-diag-r2`、ABI5、新build／dist／archive身分中的私有kind9：既有引擎佇列上對目前文件／選取直接呼叫 `getTextSelection(...,"text/html",...)`，記錄實際進入、返回HTML及正常首次poll回覆；不接受任意MIME／UNO／鍵碼，不移除公開037guard。本節只對後繼身分取代§19的「拒絕9」：後繼允許1–9、拒絕10，原候選仍拒絕9。這是擁有者執行的後繼診斷連結，不重建core，agent不得代跑建置。

更正040固定三格：含frame文件的公開close真正返回；kind9在引擎執行緒的HTML選取真正返回含image元素；kind3在相同實際選取的JS側呼叫達既有SDK預設30000ms TIMEOUT並走既有復原。fixture固定 `test-docs/e1/image-variants.odt`、SHA256 `b2869e0eb89bc5644e08e5d86c5d374615d1e641ec5ed8a7d7aca0198567c661`，HTML兩格依裁示由IV-ASCHAR實際搜尋矩形建立範圍，先讀到COMPLEX才可計數；不能用同名標籤、猜座標、空HTML或兄弟API替代。兩瀏覽器各N=3，共18格，wire與fixture結構由讀取器驗證，紅案先行。缺前提／缺入口／未跑為NE；前提齊備仍快速返回的負對照是真反例，不能再自動豁免。逾時門檻不變。

計數語意：原24格及舊候選準備資料不計入更正後繼；依新輸入前提及實際後繼身分重新計數，相同觀測被兩份報告引用不能重複算輪次。原生DELETE45／FORMAT40封閉結論不變。這是§9.2既有具名義務的有限落地與反例逼出的前提更正，不是公開ABI6功能。首次完整乾淨母體及產物讀取器通過即封閉；後來非回歸疑慮登錄後續工作，不繼續擴張閘門。

## 21. §9.3 功能實作前的有限逐格協定（2026-10-26，只追加）

§9.2五組硬性讀取已由 `handoff/RULING-2026-10-26-v23-diagnostic-closure.md` 依實際產物封閉；C2單一準備格沒有版本變動／fresh paint，仍為已登錄NE，不當成改善、引擎退化或新硬閘門。本節只開啟§9.3的來源實作階段。完整英文逐格裁決為 `handoff/PROTOCOL-2026-10-26-v23-abi6-feature.md`，採用已提交的R1來源索引、S表與產品readiness協定；沒有任何功能執行已因此被判通過。

**合約更正**：本節對§5.8「加在25之後」的句子明確更正為既有六動作的行為擴充，不配置新ID。external 1、2、16、17、18、19／internal 1–6使用既有extend布林及三種gesture，external最大23、internal最大25不變。功能身分固定 `e2-editor-v23`、ABI6、獨立build與以釘住v22為基底的新產品worker；診斷ABI5與Calc/shared worker不變。保留空gesture的select-all、document moves原限制及096檢查點；不給新Ctrl+Shift文件移動、私有診斷入口、宿主或K授權。詳細來源邊界依 `DESIGN-2026-10-26-v23-abi6-after-diagnostics.md`。

### 21.1 工具產生的母體與比較

R1使用 `collect_v23_r1_inputs.py` 由保留原生資料產生的72格：主表42、extras18、drag extras12，每格三筆原生觀測；emuend只是參照，不再加格。36格在相同文字／單行／硬換行／表格前提成立時比logical落點；36個版面相關格使用同瀏覽器fresh control，依原生三輪已證相等的emu規則；`m1e`、`s1d`、`m1d`的Down改用原生已證相等的emuend與實際 `TEXT_SELECTION_END`，不可用上一行末visible cursor替代。產品setup以實際公開搜尋／幾何／placement／drag／六鍵建立語意shape，先證選取文字、方向及visual affinity；不搬原生XY或不存在的公開Ctrl+Down。缺setup/control為NE，不能拿候選range結果自證。

`v23_feature_s_cases.py` 與 `feature-protocol/s-cases.json`／`S-CASES.md` 固定S1＝84、S2＝108、v19預紅＝16、S3＝10、S4＝9、S5＝588。**各宣告格每瀏覽器一次**；歷史原生三輪不是新瀏覽器N3。S1保持anchor，以同瀏覽器非Shift對照移動端；literal native比較限Left/Right及已證單行的Home/End。S2比較完成回覆與至少500ms後真正引擎state／selection type，記錄重複terminal與晚cursor；500ms不是產品完成等待。S3沿來源三輪皆無callback子集，要求合法readback完成、版本不變、changed:false及不復原；不恢復250ms waiter。S4維持原三種延伸後三種click／drag／handles互動與原結果。

S2預紅以真正v19 SDK/client跑更正後16格，排除兩個文件邊界靜默格；不能用舊頁丟掉Shift作紅案。第一次用S2讀取器驗收之前必須完成，任何非預期綠先查儀器／callback，不往下計數。它不要求先有功能artifact才能編寫ABI6來源。

S5逐個84來源格固定七序列：Shift→Backspace、Shift→Delete、Shift→`x`、Shift→Backspace→Backspace、Shift→Delete→Delete、Backspace→Shift→Backspace、Delete→Shift→Delete，成員間不插等待。刪除採paragraph-merge§24的reduce_content，打字比段落文字。原生Left/Right及已證單行Home/End的exact continuation存檔尚未存在，不能把三輪Shift snapshots冒充；須有實際釘住的native save才可判該格。其餘依既有 `ruling-3.md` line55，以相同瀏覽器／feature／fixture／shape的fresh settled arm作oracle：只在Shift terminal與至少500ms穩態觀測後送後續，兩個delete仍連發，prefix delete→Shift仍連發。先前提議將全部browser端點重建進native版面不是既有規則，撤去該多餘機制。timed candidate final不能自證。continuation beforeinput的實際posted未terminal/cancel move/extend集合才算overlap；空overlap集合仍依舊規FAIL，未重疊格另判序列，不造產品延遲取得重疊。

### 21.2 真正產品輸入、held與保留鍵

採 `diagnostic/9.3-product-readiness-retained-keys-protocol.md` 的釘住fixture及輸入，並由本節取代其中建議標籤。預紅／計數之前另開readiness文件，必須有實際open/doc handle及fixture見證、啟用且聚焦的sink、真瀏覽器按鍵→wire→已存檔的已知修改，再fresh-open原fixture開始正式格。UI ready、抓到按鍵、canvas或正確下載bytes單獨都不足；實際UA browser family及不同page artifact須可核對。

三產品臂沿既有runner新增：`abcd`選b→打x→立即ShiftRight，期望axcd且選c；`plain3`第二段首Backspace→立即ShiftRight，期望前兩段接合且選原Bravo的B；`long200`第一文字caret按住ShiftRight一秒。另S-12是不同的兩秒臂。原文把N留待跑前填入，本次明定這四臂各瀏覽器N＝3，共24格，**不是宣稱原已有N3**。沿既有500ms delay／30ms repeat排程：一秒臂18 downs、計畫keyup995ms；兩秒臂52 downs、計畫keyup2015ms。保存實際時間／repeat旗標；這是輸入，不是新增延遲門檻。fixture第一段必須足夠長且未到邊界。S-12放開後增長上限嚴格是當下實際wire-pending延伸數，queued／held另列不能墊高上限；132 admitted outstanding深度2另行保留。缺實際repeat或release引擎state為NE，不是零增長PASS。

L-142另格採abcd末端→完成save→CtrlHome立即Z，存檔必為Zabcd；不以歷史2–9ms另設門檻。兩種刪字各自保留：cjk25末端25個真Backspace到空；underscores末端25個真Backspace留下 `Name: _____`。每成功刪除的版本與存檔損失須對得上，完成詞彙依當前headless路徑。這些未指定N的既有family各瀏覽器一次，不暗乘3。每次產品runner仍須由真正dirty-first-move取得原096讀取器的B2＝true；L-142先save不代證B2，原讀取器／突變不改。

保留鍵新判準是實際outstanding期間已admit輸入的保存及順序，不是2.25秒窗。由既有141／144／145與page-held-deletes／page-held-depth測試來源產生母體；單元以第一筆fake request尚未resolve明確建立重疊，測standing unchanged boundary noop、real change、state改變／缺失、拒絕、換文件及插入其他enqueue。保持18 unflagged presses、52 repeat、132深度2、144放開後最多2刪除及五種D8方向／click／其他鍵序列的原內容答案。只對真正在未完成request後保留的鍵判one-request；不把快速完成後的新按鍵誤判掉鍵。撤除舊2.5秒ready界限與fake66ms throughput要求，不改原使用者事件數。

### 21.3 具名限制、表格與frame的實際來源

L-C三格沿d7i／d7ii／d7iii與bullet／indent，每瀏覽器一次，記錄真正產品terminal、saved structure／caret及與native `Number On/Off`、`Number On/Off`、`Apply attributes`的差異。headless K1-NONE/noop限制維持，不宣布L-C關閉，也不授權a11y/core/A3 fallback。

表格start/end直接沿 `134/table/probe_table_refusal.py` 完整五格ARMS、table-boundary fixture及marks／排程，不新造start/end×兩刪除Cartesian。每瀏覽器各一次，`cell-start-hold`沿既有兩次，共12格。保留136接受的文件保存與marker落點；cell-start-hold依link-batch§10.7的C更正：刪完kjkjk後boundary不再nothing-selected拒絕／重開，wvy正好位於原A1之前。其餘保留真正內容／marker判準，typed terminal／generation按實測記錄，不要求舊toast猜stage或重造等待窗。

跨格來源為R1 s5，每瀏覽器一個fresh public Delete延續，只記錄實際terminal、版本、存檔cell結構及可讀性，native刪除parity缺oracle仍NE。**來源更正**：action20的range grant與 `.uno:Delete`直接派送確實存在；`not-characterised-in-tables-or-note-apparatus`是描述性限制，並不是runtime拒絕guard。因此不能釘「必拒絕且不變」、加新guard來保住假前提或稱此為新增grant。這不豁免S5對其source cell另有的硬性比較。

as-char frame沿原object-click八臂（Bold／Delete／Backspace／Left，各立即或150ms）及原fixture／實際object選取，每臂每瀏覽器一次，作既有具名限制記錄。保留native seq參照與實際公開permission/type處置；拒絕就記拒絕，不稱parity。150ms是原對照輸入而非新完成wait；缺setup／oracle為NE，未量預設仍text-click範圍，不新開frame grant，也不拿040 HTML證據替代。

### 21.4 前提、預設與截止

本節與來源生成表／因果紅控制完成後准寫既定功能來源；**未做的S5 native saves、fresh settled-WASM references及v19預紅是計數前義務，不是要求先有feature才能編寫feature的循環前提**。計數前須釘住真正feature五身分、儀器graph／fixture、readiness及各硬格oracle。需要編譯native harness時另備完整命令由擁有者跑，不假定舊binary能做新序列。此裁示不授權agent make、host／服務／活文件變更或K。

逐格缺輸入、身分、readiness或oracle為NE並擋該硬格；齊備而反例為FAIL。具名限制記錄維持各自預設，不暗升為Writer parity硬閘門。讀取器從工具真值源核對完整母體與因果紅案，保存原始wire及存檔，不許缺格／重格／錯browser／自造oracle轉綠。第一次完整乾淨母體及產物reader通過即關閉各組；之後不為疑慮追加輪數／門檻。candidate或clean定義變動使受影響feature計數失效；純文字／provenance更正不自動重設無關封閉組。歷史失敗／準備資料原樣保留，五組diagnostic與C2記錄不重開。

## 22. 實作來源逼出的三個窄澄清（2026-10-26，只追加）

**刪除選擇的時點**：實讀 `dispatchDelete` 在enqueue前從頁面snapshot選caret delete／delete-selection，而session直到既有queue operation開始才派送。S5的Shift→Backspace因此可能持pre-Shift collapsed送錯動作；C的引擎順序不會自動修正已選錯的client動作。本次只加ABI6用的窄 `session.deleteKey(direction)`，direction只收原Backspace／Delete兩名稱。於既有queue operation開始後一次 `editor.getState()`，必須有observed selection及合法collapsed boolean；collapsed派原方向，range且manifest確有action20才派delete-selection。未知shape用現成typed gesture refusal且不派送，讀取錯誤保留原code／recovery，缺grant不自行拓寬。共用既有mutation、唯讀、generation、錯誤及unchanged accounting；保留原方向與resolved action各自意義。舊profile沿舊路。這是對具體S5錯路重新推導的單次dequeue讀取，不帶回§4撤回的resolver旗標／waiter／K1柵欄，不造第二佇列、泛用resolver callback或公開options標記，096不改。因果紅案先保留Shift未完成時收到Backspace的舊錯路，再驗range／collapsed／雙delete／prefix-delete及未知state不派送；不放寬S5。

**held Shift release**：採頁面最多一個尚未派送的repeat，加一個outstanding＝既有132深度2；前者完成才釋出held，keyup丟棄同一hold尚未派送的repeat，已posted正常完成。其他操作真正enqueue前沿既有beforeEnqueue先釋出較早held，保留輸入順序及document generation。不加session cancellation或泛用queue；repeat:false初按不得丟棄。§21的wire release-bound只量已固定clean long200、沒有前序dirty checkpoint／typing的兩個held臂，並須見證初按已posted；缺此setup為NE。這不外推為所有混合操作／dirty checkpoint下的初按取消規則；其他路徑維持原輸入保序，不冒稱已量同一bound。三集合繼續分列，不把尚未posted當in-flight。

**state wire字面來源更正**：準備文件曾把窄client的getState寫成editorGetStateV1，是只看到base class的漏讀。實際current `narrow-editor-v2-client.js:514` 委派 `paragraph-editor-client.js:173–177`，真正wire是 `editorGetStateV2`；釘住v19 shell的同一public路亦為V2。本節取代 `S-CASES.md` 與產品readiness協定中這條路的V1敘述；工具依實際profile／shell及完整委派鏈釘V2，不能接受模糊state-like別名。V1只屬真正使用base client且另有來源綁定的其他路，不是本格的替代輸入。此更正不改SDK或凍結artifact，不新增case、threshold或runtime；尚無feature／預紅計數可重設，已封閉diagnostic保持原判。

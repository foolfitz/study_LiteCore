# SPEC M3：有序指令（引擎 v23）——引擎改成 unipoll 單執行緒拓撲（候選 C）

狀態：**草稿，判準未釘死。**本檔在 fable 裁決 1 附錄 1（§13 的四題）之後改定，**改定後的第一個 commit 才是釘死**；在那之前任何 v23 的執行（原生臂 N1、模型、實作、連結）都不得開始（CLAUDE.md「驗收判準的形式」§9.1「先於滿足」）。釘死之後只准追加（§10）。

依據：

- **fable 裁決 1**（`findings/evidence/link-batch-v23/review/ruling-fable-1.md`，`cca06f7a`；簡報 `9613bfea`）。下文「裁決 §2.N」指它的第 2 節。兩者不同時以裁決為準。
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

## 2. 決定紀錄（裁決 1 與原生結果）

| 項 | 決定 | 出處 |
|---|---|---|
| 範圍 | 計畫 §4 A：第 1、2 層；第 3 層只以「候選順便帶來的後果」進來 | 裁決 §2.1 |
| 候選 | **C**。原生量測 C-HOLDS（§3） | 裁決 §2.5、§2.6 |
| A′、原樣的 B | 撤回（兩跳鍵；跳數由文件狀態決定） | 裁決 §2.2、§2.3 |
| A | 不是本批的退路（復原證明只讓「完成」與跳數無關，「順序」仍有關） | 裁決 §2.4 |
| 退路 | B″（佇列非空時不送同步指令）；C 不可行時才量 | 裁決 §2.3 |
| 裁決 4「C 受 040 限制」 | 撤回（040 的等待只在非主執行緒；C 之下引擎就是主執行緒） | 裁決 §2.5 |
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

- 具名限制 **L-native-harness-init**：原生 harness 的初始化不是產品的（不呼叫 `runLoop`，自己做三個註冊，補 `SfxApplication::GetOrCreate()`；finding 156）。量的是派送拓撲，由原始碼看與 Application 物件無關；這一點**未量**。

## 4. 範圍：普查 18 項逐項處置（裁決 §2.1 的形式一：每一項一行）

| # | 項 | 處置 | 怎麼成立 |
|---|---|---|---|
| 1 | finding 137 的根治（刪錯、字提早、格式套錯） | **in** | 由構造；WASM 臂 W-D（§9.3） |
| 2 | L-142-readback-overtaken | **in** | 250 ms 讀回撤除（§5.3）；WASM 臂「存檔後馬上移動再打字」N/N 正確（§9.3） |
| 3 | finding 151 的方向鍵那半 | **in** | 需 096 的 §34 裁決（§13 Q1） |
| 4 | L-md-137（Markdown 貼上屬 137 一類） | **consequence** | 貼上本來就同步；C 之下排在前面的鍵已跑完 |
| 5 | Shift＋方向鍵 | **in** | §6 |
| 6 | 範圍上的方向鍵（finding 129）＋ R1 | **in** | §6 |
| 7 | 延伸套件：格子（R1 的 42＋L-129 的 wrap、S1–S5、S2 的 16 格 v19 預紅、S-12）帶過來當臂與紅案；機制（resolver、規則 (a)、旗標、K1 柵欄、`AwaitingDeleteCompletion` 的等待、§12.5 的放寬）**不帶**，在 C 之下重新推導 | **in**（格子）／**out**（機制） | 裁決 §2.1 |
| 8 | v20 撤掉的三支產品路徑臂（insert 後 Shift、合併 Backspace 後 Shift、Shift+Right 按住 1 秒） | **in** | §6 |
| 9 | 偽造完成的殘留與 L-extend-prior-flush | **consequence**（由構造關閉） | 模型同步鍵模式印 0（§8）；完成＝返回＋閒置 poll（§5.2），沒有「晚到的 flush」可以偽造 |
| 10 | 邊界鍵的即時回答 | **consequence** | 返回時就知道（復原與游標都沒變）；2.25 秒的窗撤除（§5.5） |
| 11 | 點擊的完成條件（finding 140 第二輪） | **consequence** | 滑鼠事件在呼叫裡執行（D6 5/5）；完成同 §5.2 |
| 12 | C 的 manifest 宣告 | **out** | 沒有讀者 |
| 13 | L-C-number-or-indent | **consequence**（關閉） | 刪除改送使用者自己的鍵（§5.4）；D7 是 Writer 的答案 |
| 14 | 固定三題 | 必備內容 | §7 |
| 15 | 模型的粗體寬度限制 | 必備內容 | §8 |
| 16 | ABI 6 | 必備內容 | §5.8 |
| 17 | 096 那支計數檢查的 §34 裁決 | 必備內容 | §13 Q1（裁決附錄 1，**在任何會滿足它的執行之前**） |
| 18 | 「2.25 秒空窗期間打字」（工單 10-14m） | **consequence**（關閉） | 窗撤除 |

相鄰、不在本規格：`STACK_OVERFLOW_CHECK` 第 2 級（v22 §3.3 登錄在「擁有者下一次診斷連結」，§13 Q4）；第 1 項的 D6 臂（下一次在有入口的頁面跑第 1 項之前實作）。

## 5. 設計（C）

### 5.1 拓撲與初始化

- WASM 引擎以 `SAL_LOK_OPTIONS=unipoll` 初始化 LOK；引擎執行緒成為 VCL 主執行緒。`runLoop` 註冊 poll 回呼；之後引擎自己呼叫 `Application::Execute()`（現行 `OXSDK_MAINLOOP_ENGINE` profile 的作法，finding 021）。
- **finding 156**：`runLoop` 在本 core 上不會跑 `Desktop::Main`（上游 `caa4036188ed`）。WASM 上 Desktop 被刻意洩漏所以不當，但 `Desktop::Main` 的初始化不會發生。SfxApplication 由 SfxModule 建立時的 `GetOrCreate()` 產生（`sfx2/source/appl/module.cxx:83`，讀原始碼）；**WASM 上它在第一次開檔前由誰觸發，未讀**——由診斷連結的 smoke（§9.2 S-open）驗。
- 引擎的阻塞式 `engineLoop` 退役；指令改由 poll 回呼排空。`#error`（`probe_engine.cpp:15-17`）由新的接線取代，不是刪掉。

### 5.2 完成的定義（取代 250 ms 讀回與第一個回呼規則）

- **一次 poll 只排空一個指令。**（現行 `mainLoopDrainCommands` 會一路排空，`probe_engine.cpp:6688-6750`；**改掉**——否則兩個排隊的指令之間沒有 flush，回覆會讀到前一個指令之前的狀態快取。）
- poll 回呼只在核心閒置時被呼叫：沒有待處理的使用者事件，也沒有到期的計時器（`vcl/headless/svpinst.cxx:442-455`，讀原始碼）。LOK 的回呼 flush 是排隊的使用者事件（`init.cxx:2578-2582`）。
- **所以：指令 N 的 LOK 呼叫返回之後的第一次 poll，N 產生的回呼都已送達。**這是推論；由原生臂 **N1**（§9.1）在實作之前量。
- **指令的完成＝它的 LOK 呼叫返回，且下一次 poll 已到；回覆在那次 poll 送出**，狀態取自那時的快取（已被 N 的 flush 更新）。不再有 250 ms 讀回、不再以「第一個回呼」當證據、不再有等回呼的期限。
- 「什麼都沒變」在同一點就知道：復原紀錄、選取、游標都與送出前相同 → 立即回答（§5.5）。

### 5.3 既有機制逐項處置（裁決 §2.5：每一項寫它還守什麼，或撤回）

依 `facts-async-key-machinery.md` 的 A1–A13：

| # | 機制 | 處置 | 理由 |
|---|---|---|---|
| A1 | 250 ms 移動讀回（096 的修法） | **撤回** | 前提（沒變的鍵不發回呼、等回呼會卡死）不在；返回＋閒置 poll 就知道 |
| A2 | 第一個回呼就完成（規則 (a)） | **撤回** | 效果在返回時就在；回呼只更新快取 |
| A3 | 選取柵欄刪除（K1、`AwaitingDeleteCompletion`） | **撤回**，改送使用者自己的鍵（§5.4） | 前提（finding 016：前刪沒有可歸屬的回呼）不在；D2、D2′、D5、D7 |
| A4 | C 的窗／`verified-boundary-noop` 的 2.25 秒 | **撤回窗**（§5.5）；完成名稱見 §5.8 | 返回時就知道；L-C-late-K1 在 K1 不存在時不會發生 |
| A5 | 合併鍵的復原路徑（Esc、K2、柵欄、15 ms 輪詢、2000 ms `key-deadline`） | **撤回時間與柵欄**；`judgeAfterKey` 的整份比較**留下**當返回時的證明 | Esc／K2／歸屬只因 K1 是排隊鍵而存在 |
| A6 | 各階段期限（七個常數、1 秒閒置上限） | **撤回**等回呼的期限；保留一個**卡死看門狗**（§5.6） | 等的東西在返回時就有 |
| A7 | 格式柵欄 | staging 與 5 秒期限**撤回**；**事後讀回（html）留下** | 讀回沒有非同步前提 |
| A8 | 定位游標（finding 138 的雙條件、400 ms grace、250 ms 讀回） | 完成改 §5.2；**138 的「位置或選取與點擊前不同」條款留下**（它判的是「核心有沒有接受點擊」，不是時間） | D6 |
| A9 | `extend_completion.hpp`（規則 (a)、旗標） | **撤回**（沒有引擎檔案引用它；只剩模型） | 裁決 4 已撤旗標 |
| A10 | 打字退路（`paste()` 失敗時逐字送鍵） | **留下**，回覆改在 §5.2 的點 | C 之下回覆不再先於效果 |
| A11 | 引擎迴圈的等待（`values[0]` 1／2／3、三個讀回指令） | **撤回** | 只為喚醒等回呼的引擎 |
| A12 | 跨執行緒機械（`gMergeMutex`、「在回呼裡不動作、排一步」） | 互斥鎖**撤回**；「回呼裡不呼叫 LOK」**變成硬規則**（§5.7） | 跨執行緒前提不在；重入前提還在 |
| A13 | 037／040 的保護 | **留下**，直到連結後臂 040-W 過（§9.2） | 裁決 §2.8(e) |

### 5.4 刪除

- 游標處的 Backspace／Delete：送**使用者自己的鍵**（KEYINPUT＋KEYUP，在呼叫裡執行）。證明：返回時的 `.uno:Undo` 整份與送出前比（`judgeAfterKey` 的比較）；變了＝`verified-key-undo`；沒變而且游標、選取都沒變＝邊界的無作用（§5.5）。
- 範圍上的刪除：照今天送 `.uno:Delete`（同步）；C 之下它前面不會有排隊中的鍵。
- **L-C-number-or-indent 因此關閉**：(i)–(iii) 的答案是 Writer 自己的 `Number On/Off`／`Apply attributes`（§3 D7），在返回時讀到。
- 柵欄（K1）在 C 之下守的東西：**主 session 找不到**。依裁決 §2.8(b) 的預設：撤回。（§13 Q2 請裁決確認。）

### 5.5 邊界鍵與「沒有作用的鍵」

- 返回時復原紀錄、選取、游標都與送出前相同 → 立即回答「沒有作用」，`waitedMs` 是實際的毫秒數（預期 < 一個 tick）。2.25 秒的窗撤除。
- 頁面的「保留按鍵」（finding 141／144 的 `holdsDelete`／`settleDelete`）的前提是窗；窗撤除後它守什麼，由殼層的判準在實作前寫（§9.3 的頁面臂）。

### 5.6 卡死看門狗

等回呼的期限都撤除之後，一個 LOK 呼叫若真的不返回（例：finding 037 的 as-char frame 卡死），poll 不會再被呼叫，引擎就停在那裡。保留一個**由 worker 側量的看門狗**：一個指令送出後 N 秒沒有回覆 → 照今天的「引擎沒有回應」路徑（新的 worker）。N 照今天最長的期限（5 秒）不變，不是新的數字。〔推論；§13 Q3〕

### 5.7 硬規則（形式一：每一個指令、每一個回呼）

1. **指令內不得 `Application::Yield`、`Scheduler::ProcessEventsToIdle`、`Application::Reschedule`**（裁決 §2.8(a)1）。紅案：一個在鍵與讀取之間排空另一個指令的測試 build，證明讀到的是另一個變更。
2. **回呼裡不得呼叫 LOK**：今天的 `probe_engine.cpp:2875-2880`（註解送 `.uno:Escape`）改成排到下一次 poll。紅案：源碼檢查 `onLokCallback` 的呼叫圖裡沒有 `pClass->` 呼叫（形式二：工具從原始碼生成清單）。
3. **所有 LOK 呼叫都在引擎執行緒**（040 的前提）：正向對照見 §9.2 的 040-W。

### 5.8 ABI 與完成詞彙

- 編輯器 ABI **6**：新的動作（延伸、範圍上的移動）加在 `kMaxInternalEditorAction`（25）之後，**加之前先讀界限**（CLAUDE.md「工作結論」：界限要跟著清單走）。
- **完成字串的名字留著，語意寫進 ABI 6**：`verified-key-undo`（返回時證明）、`verified-boundary-noop`（返回時知道；`waitedMs` 很小）。理由：消費者遍布 client、session、page、worker、tools，而 `editor-shell/editor-client.js:70-86` 與 `editor-session.js` 綁著 **E1-C 的判定**——改名就要動綁定的檔案。`key-deadline` 與 `verified-move-readback` 在 v23 profile 上不再出現。（§13 Q2 請裁決確認「留名字、改語意」與 wasm 位元組偵測 `run_merge_wasm_shakedown.py:208` 的處置。）

## 6. 第 2 層：延伸與範圍上的移動

- 新動作：Shift＋Left／Right／Up／Down／Home／End（延伸），以及範圍起點的一般移動（finding 129：在範圍上按方向鍵收合）。都是使用者自己的鍵，在呼叫裡執行，完成同 §5.2。
- manifest 的 gestures：新動作要寫 `gestures`；**扣住的動作寫 `gestures: []`，不是省略**（CLAUDE.md「工作結論」）。
- 判準：R1（129 的 42 格＋L-129 的 wrap 格）、S1–S5、S2 的 16 格 v19 預紅、S-12（按住 Shift）、三支產品路徑臂（§4 第 8 項）——逐格的協定在實作前追加（§9.3）。

## 7. 固定三題（第一輪審核；`SPEC-M3-link-batch.md` §13.4）在 C 之下

1. **FIFO 鍵的復原證明能不能被另一個變更滿足**：C 之下引擎是唯一改文件的執行緒，指令之間不讓出（§5.7 規則 1）；證明在返回時讀，同一個呼叫裡沒有別的變更能插進來。紅案見 §5.7。
2. **一個什麼都沒做的鍵，頁面怎麼知道**：返回時復原與游標都沒變，並由閒置 poll 確認沒有晚到的回呼。測試位置：§3 D7 的 (i)–(iii) 與一般 P1，附原生的 `.uno:Undo` 頂端。
3. **表格或行內物件裡，鍵的行為和今天的拒絕不同**：格子開頭／結尾的鍵、跨格的選取、as-char frame——臂在 §9.3 追加；「今天的拒絕」與「Writer 的順序」衝突時，**預設照 Writer**（裁決 §2.8(a)3），這就是性質本身。

## 8. 模型（`wasm_sdk_probe/tests/extend_completion_model_test.cpp`）

在本規格釘死之後、實作之前，跑兩種模式（裁決 §2.7）：

- **多執行緒模式**（紅案，證明產生器還活著）：照舊印出條件 32／33 的母數——27,744、2,448、5,474、3,868（`findings/137-…md:40-43`）。印不出來就停。
- **同步鍵模式**（C）：每一種形狀（含條件 33 的兩種）印 **0** 個與 Writer 不同；完成定義為「返回＋閒置 poll」時，偽造完成那一類為**空**。
- 模型一節要寫的兩個限制：條件 40 的（粗體不改模型裡的矩形寬度）；新的一個——**模型的鍵是單一事件、沒有跳數**（只對 FIFO 類候選有關，那些已撤回）。
- 形式：每一種形狀（形式一）。預設：模型沒跑 → 不寫引擎碼。

## 9. 判準總表

### 9.1 實作之前（原生，不連結）

- **N1（新，被 §5.2 的推論逼出）**：原生 unipoll，對 §3 的每一支臂與每一種指令（鍵、`postUnoCommand`、`paste`、點擊）：指令返回後的**第一次 poll** 時，該指令的回呼已全部送達——之後 2000 ms 的窗裡沒有屬於它的回呼。N=5。形式一。紅案：一份把一個回呼的時間挪到第一次 poll 之後的合成報告 → 紅。**預設**：N1 不過 → §5.2 的完成定義不成立，回到裁決（不寫引擎碼）。
- **M1／M2**：§8 的兩種模式。

### 9.2 第一次連結＝診斷 profile（擁有者的 make；裁決 §2.8(e)）

先只接線 §5.1–§5.3 與 §5.7，**不加任何功能**，連成診斷 profile。判準（兩個瀏覽器，N=3，除非另寫）：

- **S-open／S-type／S-move／S-save**：開檔、打字、移動、存檔的 smoke。
- **W-D**：§3 的 D1–D6 經引擎的線上動作在 WASM 上跑，落點等於原生 seq 的落點，N=5。
- **040-W**：finding 040 的兩個入口（`doc_destroy`、在帶 frame 的 SwDoc 上 `doc_getTextSelection`）在 C 之下**返回**；正向對照：從 JS 側執行緒呼叫一個 LOK 入口**要卡住**（逾時之內）。
- **記錄、不當閘門**：tick 間隔、回呼延遲、`keyToUndoMs`（對 v20 的 [30, 32, 33] ms）、finding 122 的延遲。
- 預設：診斷 profile 的任何一格不過 → 不做功能接線。

### 9.3 第二次連結＝功能 profile

§6 的動作、§5.4 的刪除、殼層的對應改動。逐格的協定**在實作之前追加**（§9 的四個條件）：R1、S1–S5、S2 預紅、S-12、三支產品路徑臂、L-142 的「存檔後移動再打字」、L-C-number-or-indent 的三個位置經產品路徑、固定題 3 的表格／frame 臂、頁面「保留按鍵」的新判準。

### 9.4 計數

K：v22 累積的未計數改動（交接 10-20 的清單）加上 v23，在擁有者指定的時段、脫離 session、先問（記憶 `release-count-batched`）。

## 10. 連結順序

1. 釘死本規格（§13 的附錄之後）。
2. N1、模型兩種模式。
3. 兩席審核（opus＋`codex exec -s read-only < /dev/null`），固定三題在內。
4. 診斷 profile 的引擎碼（紅案先行），**擁有者連結**，§9.2。
5. 功能的引擎碼與殼層，**擁有者連結**，§9.3。
6. 宿主、綁定、K。

## 11. 具名限制（現在就登錄）

- **L-native-harness-init**（§3）。
- **L-no-ime-arm**：IME／ext-text 在 unipoll 下沒有臂（今天打字走 `paste`）。
- **L-writer-only**：Calc、Impress 沒有跳數分析。
- **L-mouse-hops**：`MouseButtonUp` 之後的跳數沒讀（D6 的落點正確，但沒追到每一跳）。
- **L-flush-order**：同一次 flush 裡 `UNO_COMMAND_RESULT`、`STATE_CHANGED`、`TEXT_SELECTION`、游標的順序在 unipoll 下沒量（059 的狀態檢查與格式讀回依賴它）——N1 的紀錄順帶記下順序。

## 12. §34.4

- 本規格之前的原生工具（`oc_native.cpp`、`read_results.py`）是新增；判讀工具在第一次計數使用前要做一次雙席審核（§34），併在 §10 第 3 步。
- 因執行而修：本批到目前 0（d7i 的位置是在任何計數執行之前改的，記在 smoke/NOTES.md）。因審核而修：0。

## 13. 交給裁決的四題（fable 裁決 1 附錄 1；答案寫回本檔後才釘死）

- **Q1**：096 的計數檢查 `a-boundary-arrow-press-does-not-cost-the-work`（`run_e2_c_product_path.py:2205-2262`、`:9550-9575`）在 C 之下的 §34 裁決——它釘住的是「邊界方向鍵不建檢查點」與 2.25 秒窗下的行為；finding 151 的方向鍵那半要改它。
- **Q2**：§5.4 撤回柵欄、§5.8「完成字串留名字、改語意」與 wasm 位元組偵測的處置。
- **Q3**：§5.2「一次 poll 一個指令、回覆在下一次 poll」與 §5.6 的看門狗（5 秒沿用）——形式與預設對不對。
- **Q4**：`STACK_OVERFLOW_CHECK` 第 2 級要不要搭診斷 profile 的連結（v22 §3.3 登錄的「擁有者下一次診斷連結」）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-20 | 草稿（opus，主 session），依裁決 1 §4 第 3 步。未釘死。 |

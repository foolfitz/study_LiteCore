# SPEC M3：連結批次 v22——引擎執行緒的 pthread 預設堆疊改成 1 MiB（finding 153）

狀態：**判準釘死（2026-10-19，本檔第一個 commit）。**任何 v22 的執行——`make -n` 的 v22 目標、連結、瀏覽器——都在這個 commit 之後（CLAUDE.md「驗收判準的形式」§9.1「先於滿足」）。之後只准追加更正（同 §10）。

依據：

- **fable 裁決 4**（`findings/evidence/link-batch-v22/review/ruling-fable-4.md`，`ba41330a`；簡報 `brief-fable-4-stack.md`，`d7b7d392`）。下文「裁決第 N 項」都指它 §2 的編號，「裁決 §4.N」指它的第 4 節。兩者不同時以裁決為準。
- finding 153「下一批的判準」1–4（`findings/153-one-long-paragraph-overflows-the-engine-thread-stack.md`）。
- finding 089 的堆疊臂（`findings/089-…md`「堆疊臂：O-S」；`findings/evidence/089/stack-arms-2026-10-13/`）與 `specs/SPEC-M3-link-batch.md` §11、§12.6、§15.4。
- 不連結的量測 `findings/evidence/link-batch-v22/stack-size/`（`c56be2ed`）。
- 連結順序 C（v21 走完、v22 只改堆疊）：擁有者 2026-10-17 選定，交接 `HANDOFF-2026-10-17b`；擁有者 10-19 要求帶著走完 v22 的連結。

證據標記：**已觀察**＝量過或在產物上讀到；**讀原始碼**＝沒量；**推論**＝從前兩者推出；**未量**＝沒有人量過，後面寫怎麼量。

## 1. 為什麼要有

- **finding 153（已觀察）**：一段很長的單一段落，讓引擎執行緒 64 KiB 的 stack 溢位，worker 崩潰、卡死，或回答成功之後才中止。**0.2.24 與 0.2.26 的使用者不必貼上就碰得到**：開一份本來就有約 10 頁以上單段的文件，在那段開頭打一個字（0.2.24 失敗 4/4，v21 失敗 2/2）。
- **第 2 項（貼上為 Markdown）因此扣在 v21 之外**（`SPEC-M3-link-batch-v21` §12.3；發佈說明 §4.2）。C1 過了，第 2 項的入口才有可能在連結之後的殼層裡重開。
- 修法是一個連結旗標，只能重新連結；連結是擁有者的步驟。

## 2. 範圍

- **一個引擎變因**：連結行的 `-sDEFAULT_PTHREAD_STACK_SIZE=65536` 改成 `-sDEFAULT_PTHREAD_STACK_SIZE=1048576`。同一行其餘不動：`-sSTACK_SIZE=131072`、`-sPTHREAD_POOL_SIZE=7`、`-sPTHREAD_POOL_SIZE_STRICT=0`、`-sTOTAL_MEMORY=1GB`、`-sASSERTIONS=0`（所以 `STACK_OVERFLOW_CHECK` 仍是 0）。
- **其餘全部等於 v21**（已觀察，2026-10-19：v21 由 `5f5bf11c` 的樹連結；`git diff --stat 5f5bf11c..HEAD` 對 `wasm_sdk_probe/src`、`sdk/sdk-worker.js`、`sdk/v18-writer-review-manifest.json`、manifest 規則列的十個打包工具、`Makefile` 印出空白）：
  - 原始碼與 defines：v20 的 defines＋`-DOXSDK_E2_V21_LINK_BATCH`，md4c 的 `-I`。**不加 v22 的 define**：原始碼沒變，加 define 就是第二個變因。
  - 匯出表的作法、worker（`0d55bcfa…`）、資源包、v5 產生器與它的旗標（`--inline-range-gestures all --page-rectangles --paste-markdown`）。
  - 核心：連結輸入自 v21 連結以來沒有變新（`find … -newer build/e2/editor-v21/probe.wasm` 印 `0`，10-19 已觀察；連結當下再跑一次，見手冊）。
- **身分**：新 profile `e2-editor-v22`。編輯器 ABI 仍是 5。manifest 除了連結的兩個輸出雜湊與命名之外，每一個葉都等於 v21（I1-v22）。
- **連結之後、在殼層裡搭車的**（各自的判準在執行前另外追加，不在本檔）：第 2 項的入口重開、finding 152 的修法、finding 154 的頁面規則與 154 的宿主判準。之後凍殼層、宿主新版本、`BINDING`、計數鏈。
- **不在 v22**：任何等級的 `STACK_OVERFLOW_CHECK`（具名 **L-153-no-overflow-check**，§3.3）；任何其他連結旗標；核心；writer+calc（W8）。

## 3. 決定紀錄（裁決 4）

### 3.1 值：1,048,576，三條腿（裁決第 1–3 項）

finding 153 判準 2 要求「附理由」：量到的深度，或原生的設定。v22 三條都帶。

1. **Writer 的路徑（finding 153，已觀察，Chrome，N=1）**：需要 > 64 KiB、≤ 128 KiB，到 112 頁都沒有再長。65,536 在四個失敗輸入上全壞（崩潰／卡死／崩潰／回答後中止，是正向對照）；131,072 起全部正常；`insertText` 到約 112 頁、開 28／56／112 頁再在開頭打字，131,072 起全部正常，65,536 在 28 頁那格卡死（`stack-size/` 的三份報告，`identityOk: true`、`probeWasmUntouched: true`、`counted: false`）。1 MiB 是這個區間上限的 8 倍。
2. **第二條獨立的遞迴路徑（finding 089，2026-10-13，writer+calc 的 `e2-editor-v12`，同一個旗標，已觀察）**：Calc 開 ODS，64 KiB 壞；**256 KiB 是讓卡住的檔 3/3 打開的最低一階**；1 MiB、8 MiB 也 3/3；32 KiB 是紅案；**128 KiB 沒試**。所以 089 的需要在 (64 KiB, 256 KiB]。256 KiB 會踩在那條路徑的最低過關階上、沒有餘裕；1 MiB 有 4 倍，**現在選的值也蓋住 W8**，不必為堆疊再連結一次。089 不在今天的 writer-only 產品裡（`ScDocShell` 0 次），但旗標是**每一個產品連結共用的一個旗標**。
3. **原生的設定（讀原始碼）**：LibreOffice 自己在必須選數字的平台上設明確的 stack：macOS 1 MiB，註解說平台的 512 KB「不夠」（`libreoffice-26-8/sal/osl/unx/thread.cxx:283`）；OpenBSD 256 KiB（`:279`）；非最佳化的 Linux 12 MiB（`:281`）。Emscripten 不在那個 `#if` 裡（`:258-290`），所以**每一條** LibreOffice 的執行緒都拿連結的預設值，不只引擎執行緒。最佳化的 Linux 沿用 glibc 的預設（通常 8 MiB）。1 MiB 因此是 LibreOffice 自己在主流平台上「夠」的最小值、Linux 預設的 1/8，也是反事實實驗用的值——觀察最多的那一個（153 步驟 8／9 的 8/8 與 2/2；10-19 的 4＋3＋3；089 S2 在 v12 上 3 回）。

**從 v22 起，每一個產品連結都用 1,048,576**（裁決 §4.1）。

### 3.2 記憶體成本：算術加兩個既有量測，連結前不需要新量測（裁決第 4–7 項）

- 每條執行緒的 stack 在 `pthread_create` 時用 `emscripten_builtin_malloc` 從 wasm heap 配，不是在 pool 起 worker 時（讀原始碼，`wasm-lite/tools/emsdk/upstream/emscripten/system/lib/pthread/pthread_create.c:135-161`；emsdk `4.0.10`），執行緒結束時釋放。heap 是固定的：`-sTOTAL_MEMORY=1GB`，`ALLOW_MEMORY_GROWTH` 是預設的 `false`（`src/settings.js:217`）。所以是**每條活著的 pthread 1 MiB**。
- pool 7 條 → 名目 **7 MiB（1 GiB 的 0.68 %）**；pool 以外不能同步建立，所以 7 也是實際能同時跑的上限（推論）。
- 本專案唯一量過的數字（v12，已觀察）：**開 ODT 啟動 3 條、開 ODS 7 條**（10 回都一樣）；開檔時 heap 頂端 `sbrk` 290,066,432／1,073,741,824（約用 277 MiB）；8 MiB × 7（S3）沒有出現配置失敗。writer-only 開 ODT 的預期成本因此約 3 MiB（推論）。
- **v22 上的即時計數**：H1 的記錄項，只有在不碰任何綁定位元組的儀器存在時才做。**今天沒有這種儀器**：089 的回聲要改 loader，而 loader 是 profile 綁定的五個檔之一。預設：本檔引用 v12 的 3／7，寫「v22 上沒有計數」。heap 實際用量在出貨的 artifact 上量不到，除非加匯出；**不加**（那是第二個變因）。

### 3.3 `STACK_OVERFLOW_CHECK`：v22 不開，具名 L-153-no-overflow-check（裁決第 8–11 項）

- **不開的代價**：任何執行緒的 stack 溢位都沒有人發現；shadow stack 往下長進執行緒自己的 `struct pthread`（`pthread_create.c:141-152`），症狀是越界存取、停住不動、或晚到的 `std::terminate`——finding 153 的三種形狀，沒有任何診斷會點名它。0.2.24、0.2.26 出貨時就是這個狀態。
- **等級 1 在這裡幾乎買不到東西**：它在執行緒啟動時在 stack 底寫兩個 cookie，在 runtime 初始化、`run` 之後、`$handleException` 與**執行緒的進入函式回傳時**檢查（讀原始碼，`src/lib/libpthread.js:1004-1007`、`:1055-1058`；`src/preamble.js:154-155`；`src/postamble.js:227-228`；`src/lib/libcore.js:1991-1992`）。引擎執行緒是 `std::thread(engineLoop, …).detach()`（`wasm_sdk_probe/src/probe_engine.cpp:6956`，`OXSDK_MAINLOOP_ENGINE` 的 `#else`；v21 的編譯規則不定義它），一個永遠不回傳、也不走 JS tick 的迴圈，所以它活著的時候 cookie 從來不被檢查。等級 1 還會改 loader、多四個 `REQUIRED_EXPORTS`（`tools/link.py:1208-1222`）：沒有量到好處的第二個變因。
- **等級 2 能買到的**：wasm-emscripten-finalize 的 `--check-stack-overflow`（`tools/emscripten.py:508-509`）在每一次設定 stack pointer 的地方插檢查，溢位時呼叫 `__handle_stack_overflow`，帶著要求的 SP 與上下限中止（`libcore.js:1671-1680`；每條執行緒的上下限在 `libpthread.js:995-999`）。這會把一次 153 類的失敗變成一次確定、有位址的中止：可以診斷，對使用者仍然是引擎死掉。**代價沒量過**：115,314,060 位元組的 `probe.wasm` 會長多少、速度（settings.js:64-65 寫「small」）、以及跟著來的 `CHECK_NULL_WRITES`（settings.js:69-74）。上游 LibreOffice 自己的 wasm 只開等級 1（`ASSERTIONS=1`，`libreoffice-26-8/solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk:29-30`）。
- **若永遠不再討論**：之後每一個產品連結的 `STACK_OVERFLOW_CHECK` 都是 0；這個具名限制留在每一份發佈說明裡。
- **工作項（不是閘門）**：擁有者下一次本來就要連結一份**診斷用**（不出貨）的 artifact 時（前例 `build/e2/preguard-profiling`、`build/e2/wait-diagnostic`），在那份連結加 `-sSTACK_OVERFLOW_CHECK=2`，記下 `probe.wasm` 的大小、開檔時間與 C2 的打字時間，對照同一棵樹的產品連結；v23 以後要不要開，由這兩個數字在一份裁決裡決定。從來沒量：維持不開。

### 3.4 連結之前不再量什麼，以及為什麼（裁決第 12–16 項）

- **Firefox、N=3 都不是連結前的前提**：每層遞迴用多少 frame 是 wasm 程式碼與輸入的性質，不是瀏覽器的；153 步驟 7 已經看到 Firefox 在 64 KiB 上同樣失敗。兩個瀏覽器、N=3 是 C1，在連結後的真品上跑。
- **64 到 128 KiB 之間的值不需要**：只有在選的值靠近那個區間時才有意義；1 MiB 是它的 8 倍。
- **其他輸入**（表格、清單、區段、深層 XML）：不是前提。H1 只記錄 10-19 的六格，不在連結前發明新語料。
- 連結前唯一的前提是靜態的與文件上的：本檔先 commit；S3；S1 的紅案；finding 089 與 `SPEC-M3-link-batch` §11／§12.6 被引用並關閉（§3.5）。

### 3.5 撤回與關閉（裁決第 17、18、20 項；裁決 §4.1）

- **`SPEC-M3-link-batch.md` §11 登錄的問題**（「要不要調大 `-sDEFAULT_PTHREAD_STACK_SIZE`」，預設「不變；089 的修法跟著 W8」）：**由 v22 回答**——從 v22 起每一個產品連結都是 1,048,576。追加在那份規格的 §11（與本檔同一個 commit）。
- **§12.6 的 Writer 堆疊掃描（`SPEC-M3-link-batch.md:342`）與它的作法 §15.4**（裁決 3 條件 26、裁決 6 條件 52）：**撤回**，不跑（CLAUDE.md §4「撤回宣稱，不要造機械去維持它」）。它要找的 Writer 失敗就是 finding 153；它「沒有差異 → 登錄 L-writer-stack-64k」的那條分支已經不可能走到，**L-writer-stack-64k 不再能登錄**。撤回的說明追加在那兩節。
- **finding 089**：從它登錄出來的問題由這個決定關閉。它的修法（writer+calc 連結帶較大的 stack）是同一個旗標、同一個值，所以 W8 會繼承。G2 對 `tdf149752.ods` 的阻擋照舊成立，直到一個帶這個值的 writer+calc 連結落地並量過。追加在 089（同一個 commit）。
- **`stack-size/README.md` §3 被裁決更正的兩句不改**（那是證據）：「[source: the platform default, not this tree]」——樹裡有來源，`thread.cxx:258-290`（裁決第 20 項）；「pthreads alive not counted」——089 在 v12 上數過（裁決第 18 項）。以本節為準。
- **歸因（裁決第 17 項，只在連結之後、只在需要時）**：連結後若有一個紅需要分清是「stack 的值」還是「重新連結本身」（`wasm-build-not-reproducible`），那時在封存的 v21 上用 `v21stack1048576` 的鏡像 loader 跑產品路徑網。v21 一直封存著，這條路一直在。

## 4. 身分與連結的機械

### 4.1 Makefile 的 v22 區塊

接在 v21 的區塊之後：

- `E2_V22_BUILD := build/e2/editor-v22`、`E2_V22_DIST := dist/profiles/e2-editor-v22`、物件取自 `$(E2_C_SOURCES)`。
- **編譯規則**：v21 的規則逐字照抄（同樣的前置檔、同樣的 defines，含 `-DOXSDK_E2_V21_LINK_BATCH`、同樣的 md4c `-I`），只換成 v22 的路徑。
- **匯出表**：v21 的作法逐字照抄。
- **worker pin**：`E2_V22_WORKER_SHA256 := 0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`（等於 v21 的）。
- **連結**：從第一次連結就受守衛（`refuse_unasked_relink`）。呼叫一個**新的 macro** `link_product_stack_1m`：`link_r5_product` 的內容，只有那一個 token 是 `1048576`。
- **manifest**：v21 的規則，`--profile e2-editor-v22`。

**為什麼是新 macro 而不是替 `link_r5_product` 加參數（裁決 §4.3「由 S3 決定，不是品味」）**：兩種寫法給出的 v22 `make -n` 一模一樣，所以 S3 在 v22 的輸出上分不出兩者。分得出的是**對另外 22 個呼叫者要證明什麼**：`link_r5_product` 今天有 22 個呼叫點（`grep -c 'call link_r5_product' Makefile`）：六個是出貨過的 E2 profile（v4、v8、v15、v19、v20、v21，都已凍結），其餘是更早的里程碑與診斷用的規則。加參數會改動它們展開所依據的文字，它們的展開沒變就得另外做 22 個目標的證人；新 macro 讓 `link_r5_product` 一個位元組都不動（`git diff` 可驗），關於它們就沒有東西要證明。而新 macro 有沒有抄錯，正是 S3 量的東西：抄錯的任何一處都會成為第二個不同的 token。**從 v22 起的每一個產品連結都呼叫新 macro**；`link_r5_product` 留給已凍結與診斷用的規則。

### 4.2 連結前的其他兩處改動

- **`test-e2-c-static` 的 M1-1 那一行**加 `--carrier E2_V22=probe_engine,sdk_api,editor_api`。理由（讀原始碼＋推論）：M1-1 的母數是 Makefile 裡每一條 `$(X_BUILD)/%.o: src/%.cpp` 規則，v22 的物件帶著與 v21 相同的 defines，所以在 base `5d77dc84` 上會有同樣三個物件不同；沒列為載體就是紅的。**先紅**：區塊加進去、載體清單照舊時，M1-1 必須紅、而且點名 `E2_V22`（證人 commit）；加了之後綠。這是新規則的綁定（前例：v21 的區塊與 `--carrier E2_V21=…` 同一個 commit），不是修理。
- **`tools/what_the_link_ships.py`** 加 variant `link-batch-v22`：資料，v21 的 defines、`E2_V22_OBJECTS`、`E2_V22_MD4C_INCLUDE`。

### 4.3 v21 的封存直接沿用

`build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/`（10-16）：2026-10-19 `sha256sum -c SHA256SUMS` 5/5 OK，四個檔與 `dist/profiles/e2-editor-v21/` `cmp` 相同，`exports.txt` 與 `build/e2/editor-v21/exports.txt` 相同（已觀察）。再複製一份會逐位元相同，所以不做。連結前在手冊 §0 再驗一次。

### 4.4 連結前的凍結集合

`findings/evidence/link-batch-v22/pre-link/frozen-set-before.sha256`：`wasm_sdk_probe/dist/profiles/` 與 `wasm_sdk_probe/build/archive/` 底下每一個一般檔（`find -type f`；兩處都沒有 symlink，10-19 已觀察），在本檔 commit 之後、連結之前寫。

## 5. 判準總表

形式照 CLAUDE.md「驗收判準的形式」§1；每條附「若沒做或紅」的預設（§2）。

**通則**：

- **缺報、缺回、NE 一律等於「沒做」**，套用該條的預設。
- **證據的身分**：C1、H1 的每份報告都帶受測的 wasm、loader、worker、manifest、頁面的雜湊。與連結出來的 `dist/profiles/e2-editor-v22/` 不符就作廢，等於沒做。
- **C1 的讀法寫死在這裡**，讀的人用 `python3 -I` 讀報告，不另寫判讀工具（`checks-stop-rule`：不為判讀器寫判讀器）。

### 5.1 連結前

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| S3 | **(a)** 在 `wasm_sdk_probe/`、六個 `?=` 變數不設、`build/e2/editor-v22/` 還不存在時，`make -n dist/profiles/e2-editor-v22/sdk-manifest.json` 存成 `findings/evidence/link-batch-v22/pre-link/make-n-v22.txt`。把其中每一個 `editor-v22` 換成 `editor-v21` 之後，對 `findings/evidence/link-batch-v21/part-e-red/make-n-v21.txt` 做以空白分詞的 word diff（`git diff --no-index --word-diff=plain`），**恰好三行不同，而且每行只差下列那一處**（封閉清單，現在寫下）：① 連結行恰好一個 token：`-sDEFAULT_PTHREAD_STACK_SIZE=65536` → `-sDEFAULT_PTHREAD_STACK_SIZE=1048576`；② worker pin 那一行：`PENDING-PART-S-WORKER-SHA256` → `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`（v21 的證人是在 part S 釘 worker 之前取的；v21 的規則今天帶的就是這個值，`Makefile:1647`）；③ 守衛那一行 `it carries: ` 與 ` -- every link mints a new hash` 之間的說明文字（v21 的 → v22 的）。其他任何一行、任何一個 token 不同：S3 紅。**(b)** `python3 tools/what_the_link_ships.py --since 5f5bf11c --variant link-batch-v22 --shipped-profile dist/profiles/e2-editor-v21 --json`：`ok: true`、`configurationDrift: []`、四個單元都在 `identical`、`worker.identical: true` | 逐實例（這一對） | **連結不交給擁有者** |
| S1-red | S1 的檢查器 `tools/check_pthread_stack_literal.py` 先紅：對 v21 的 `dist/profiles/e2-editor-v21/probe.js` exit 1；對一份錨點出現兩次的副本 exit 1；正向對照——v21 的 `probe.js` 把 `,!ENVIRONMENT_IS_WEB,65536,false)` 換成 `,!ENVIRONMENT_IS_WEB,1048576,false)` 一次（診斷工具 `v21stack1048576` 的同一個轉換）——exit 0。三次輸出 commit | 逐實例 | S1 不得用來判 v22，v22 不綁定 |

### 5.2 連結之後（靜態，連結當天）

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| S1 | `python3 tools/check_pthread_stack_literal.py dist/profiles/e2-editor-v22/probe.js build/e2/editor-v22/probe.js` exit 0：每個檔都含 `,!ENVIRONMENT_IS_WEB,1048576,false)` 恰好一次、`,!ENVIRONMENT_IS_WEB,65536,false)` 零次。**送出的位元組**：C1、H1 每份報告的身分區塊記下鏡像送出的 `probe.js` 雜湊，必須等於 `dist/profiles/e2-editor-v22/probe.js` 的 | 逐實例 | v22 不綁定 |
| S2 | **記錄**：v22 的 `dist/…/probe.js` 把 S1 的字面量換回 65536 一次之後，與 v21 的 `dist/profiles/e2-editor-v21/probe.js` `cmp`。預期相同（0 個 token）。不同時：token diff（`git diff --no-index --word-diff=porcelain --word-diff-regex='[A-Za-z0-9_$]+\|[^[:space:]]'`）原樣追加到本檔，發佈說明「只改一個變因」那句換成實際的清單 | 記錄 | 發佈說明不得寫「loader 只差堆疊那個值」 |
| I1-v22 | **X1 的預設模式**（不帶任何宣告旗標）：`python3 tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v22 --reference dist/profiles/e2-editor-v21 --candidate-exports build/e2/editor-v22/exports.txt --reference-exports build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/exports.txt` 印 `VERDICT PASS`、exit 0。它說的是：manifest 每一個葉都相同，只有 `wasmSha256`、`loaderSha256`、`profile`、`sdkVersion` 例外（所以 `abiVersion` 5、動作、gestures、`pasteMarkdown`、`pageRectangles` 都不變）；wasm 與 v21 的不同；worker 逐位元相同（`0d55bcfa…`）；匯出表逐位元相同；檔名相同。**唯一事先寫下的例外**：X1 的 wasm 子句把「wasm 相同」當成「修法不在裡面」，而 v22 的修法只在 loader 裡——這個設定只出現在 emscripten 的 JS 模板（`src/lib/libpthread.js` 的 `{{{ DEFAULT_PTHREAD_STACK_SIZE }}}`），由 loader 交給 `_emscripten_thread_init`（讀原始碼）。所以若 X1 **只**因為 v22 的 `probe.wasm` 與 v21 的逐位元相同而 FAIL，I1-v22 讀成：其餘每個子句都成立＋S1 PASS，wasm 相同照實記錄（那也表示 S2 的預期更強）。任何其他子句失敗照樣是紅。**凍結集合**：`pre-link/frozen-set-before.sha256` 裡每一個檔連結後雜湊相同，而且 `dist/profiles/`、`build/archive/` 底下除了 `dist/profiles/e2-editor-v22/` 之外沒有新檔（在封存 v22 之前量）。`grep -a -o ScDocShell dist/profiles/e2-editor-v22/probe.wasm \| wc -l` 印 `0`。E1-C `intact: true` | 逐實例 | v22 不綁定 |

### 5.3 連結之後（瀏覽器）

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| C1 | finding 153 判準 1。診斷工具 `findings/evidence/link-batch-v21/shakedown/diag-long-paragraph/tool/diag_long_paragraph.py`，頁面族 `v22`（連結後加：`v21` 頁面族的鏡像，頁面指向 `e2-editor-v22`；身分區塊記下送出的 `probe.js` 雜湊），四格 `sdk-md:cjk:65536:v22`、`sdk-md:cjk:43520:v22`、`sdk-md:ascii:65536:v22`、`opentype:long14:0:v22`，`--odt long14=findings/evidence/link-batch-v21/shakedown/diag-long-paragraph/out/docs-chrome-s8-bigstack/001-sdk-md_cjk_65536_v21big.odt`（sha256 `150d28f5…`），`--repeat 3`，`--browser chrome` 與 `--browser firefox` 各一輪。**過**＝24/24 格 `outcome == "ok"`（工具的 `classify`：嘗試回答成功；Chrome 上沒有 `memory access out of bounds`、沒有 `probe.js` 的執行緒例外；頁面不在 `recoverable-error`；之後的存活詢問回答且 `ok`），而且每份報告的身分區塊都是 `e2-editor-v22`、雜湊等於 `dist/profiles/e2-editor-v22/`。**正向對照**（同一天、同一工具）：`sdk-md:cjk:65536:v21` 每個瀏覽器一次，必須**不是** `ok`（153 在兩個瀏覽器上都量到它失敗）；若是 `ok`，儀器沒有鑑別力，C1 為 NE，不是 PASS | 逐實例（輸入 × 瀏覽器 × 回） | 第 2 項繼續扣住；發佈說明 §4.1 那句留著；發佈說明不得說 153 已修。**1 MiB 上紅**：值的理由是錯的——停手，帶著報告重開裁決 4；沒有量測不得改成 2 MiB（裁決 §4.7） |
| H1 | **記錄**（Chrome，N=1）：`sdk-text:cjk:131072:v22`、`sdk-text:cjk:262144:v22`、`sdk-text:cjk:524288:v22`、`opentype:long28:0:v22`、`opentype:long56:0:v22`、`opentype:long112:0:v22`，`--odt` 用 `stack-size/docs-headroom1/010-`／`011-`／`012-…odt`（sha256 `d3d8a788…`、`285b9428…`、`a438d4dd…`）。記下結果與時間。pthread 即時計數：見 §3.2，今天沒有儀器 | 記錄 | 發佈說明只引 C1 的輸入與 10-19 在 `v21stack` 上的量測，不寫 v22 上的餘裕 |

### 5.4 計數

| # | 判準 | 若沒做或紅 |
|---|---|---|
| K | 計數鏈在最終位元組上成立（J-a.2 的讀法），照 `release-count-batched`：殼層項目、凍殼層、宿主新版本、`BINDING` 之後，排在擁有者的時段、脫離 session | v22 是未計數候選，名義出貨版本停在 0.2.26 |

## 6. 連結（擁有者的步驟）

`handoff/RUNBOOK-relink-v22.md`，照 `RUNBOOK-relink-v21.md` 的形狀。交給擁有者的是**一行短的連結指令**（長的一行貼上會被截斷）。`ALLOW_FROZEN_RELINK=1` 只給 v22 這一個目標；**v8、v15、v18、v19、v20、v21 永遠不給**。前提：S3 綠、S1-red 做過，兩者的證人都已 commit。

## 7. 連結之後的順序（裁決 §4.6）

1. **連結當天，靜態**：S1、S2、I1-v22；**立刻封存** v22 到 `build/archive/e2-editor-v22-<wasm sha8>-worker-0d55bcfa/`（`probe.wasm`、`probe.js`、`sdk-worker.js`、`sdk-manifest.json`、`exports.txt`、`SHA256SUMS`、`ATTRIBUTION.md`）。
2. 診斷工具加 `v22` 頁面族（追加，不是修理）；身分區塊的證人 commit 之後，跑 C1（兩個瀏覽器、N=3、正向對照）與 H1。
3. 殼層項目：第 2 項的入口重開、152、154 的頁面規則、154 的宿主判準——各自的判準在執行前追加。
4. 凍殼層。
5. 宿主新版本。
6. `BINDING`。
7. 計數鏈（K）。

## 8. 發佈說明的後果

- **只有 C1 PASS 之後**，出 v22 的那一版才能拿掉 §4.1 那句「開啟含超長單一段落的文件並在其中打字，可能讓編輯器停止回應」（`handoff/RELEASE-TEXT-0.2.25-0.2.26.md:55-58`）。
- 出 v22 的每一版都要加：**L-153-no-overflow-check**（stack 溢位沒有人檢查，症狀是崩潰、停住、或晚到的中止）；「引擎執行緒的 stack 是 1 MiB，每一條活著的執行緒從固定 1 GiB 的 heap 用掉約 1 MiB（pool 的 7 條是 7 MiB）」。
- S2 不是 0 時，「只改一個變因」換成實際清單（§5.2）。

## 9. §34.4

本批連結前的工具改動都是**新增**，不是修理（裁決 §4.4）：S1 檢查器、`what_the_link_ships` 的 variant（資料）、M1-1 的載體行、新的連結 macro；連結後的診斷工具 `v22` 頁面族同。因執行而修 0、因審核而修 0，除非之後有一份被誤判的已 commit 報告。

## 10. 連結之後的結果（2026-10-19，只追加）

擁有者 10:39–10:42 連結（手冊 §2；`wasm_sdk_probe/build/link-v22.log` 沒有錯誤）。主 session 當天照手冊 §3 的順序做完 §5.2，證人在 `findings/evidence/link-batch-v22/post-link/`（README 是總表）。

- **凍結集合**：1,370 個檔全部相同；新的一般檔只有 `dist/profiles/e2-editor-v22/` 的四個（已觀察，封存 v22 之前量）。
- **S1：PASS。** `dist/` 與 `build/` 的 `probe.js` 都是 `dc4c2c84…`，錨點 1／0。
- **S2：0。** 字面量換回 65536 之後與 v21 的 `probe.js` 逐位元相同（`0b6cf02a…`）。發佈說明「loader 只差堆疊那個值」可以寫。
- **I1-v22：PASS。** X1 預設模式 `VERDICT PASS`：動到的葉恰好是 `loaderSha256`、`wasmSha256`、`profile`、`sdkVersion`；wasm `f7a40bcc…`（v21 `db3408f5…`）；worker、匯出表逐位元相同。§5.2 事先寫好的「wasm 相同」讀法沒有用到。`ScDocShell` 0 次。E1-C `intact: true`。
- **封存**：`wasm_sdk_probe/build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/`，七個檔，四個 profile 檔與 `dist/` `cmp` 相同。
- **wasm 與 v21 差在哪（記錄，不是判準；已觀察）**：12 個 section 裡只有 code section 不同；149,474 個函式裡只有第 77040 號不同（25,122 → 25,123 位元組：兩個 local 編號 2→3、一個 `try` 區塊換了位置）；不同的位元組裡沒有 stack 的值。四個物件裡只有 `probe_engine.o` 與 v21 的不同——同一份原始碼、同一行編譯（S3）編了兩次，finding 036 的形狀。把那個函式歸給 `probe_engine.o` 是推論（它是唯一不同的物件；沒有 name section）。所以 §5.2 I1-v22 那句「這個設定只出現在 emscripten 的 JS 模板」在這次的位元組上成立。
- **推論**：v22 的 loader 就是 10-19 診斷工具以 `v21stack1048576` 送出的那一份（同為 `dc4c2c84…`），所以裁決第 17 項的歸因組態（封存的 v21＋那份 loader）與 v22 只差 wasm 的那一個函式。

下一步照 §7：第 2 步（診斷工具的 `v22` 頁面族，然後 C1 與 H1）。

### 10.1 C1 與 H1（2026-10-19，只追加）

證據 `findings/evidence/link-batch-v22/shakedown/`（README 是總表），10:52–11:06，主 session 用 `python3 -I` 照 §5.3 的讀法判。

- **頁面族 `v22`**（`7973c427`，新增）：本輪的頁面與殼層用 `pp.repointed_page` 指向 `e2-editor-v22`（切換時用的同一個轉換）。身分區塊比對 v22 封存的四個雜湊，並**從鏡像的伺服器抓** loader 算雜湊（S1 的送出條款）。證人格的六項身分檢查全為真，抓到的 loader 是 `dc4c2c84…`。紅案：期望值換成 v21 的 loader 雜湊時 `identityOk` 為假，只紅在那一項。
- **S1 的送出條款：成立。** 每份 C1、H1 報告抓到的 loader 都是 `dc4c2c84…`。
- **C1：PASS。**
  - Chrome 151 12/12、Firefox 157 12/12 都是 `ok`，四個輸入各 3 回，每份報告 `identityOk: true`。
  - 標籤底下：每格的編輯都回答 `ok`（貼上 30–112 ms，`opentype` 打字 0.103–0.110 s）；沒有例外；頁面停在 `ready`；存活詢問 `ok`。
  - 24 份存檔每份都把輸入整段存進一個段落，長度恰好等於輸入的 UTF-8 位元組數（`opentype` 是 `x`＋65,536）。
- **正向對照：有鑑別力。** 同一天、同一工具、同一輸入，`sdk-md:cjk:65536:v21` 在 Chrome 是 `crash`（`memory access out of bounds`＋`probe.js` 執行緒例外），在 Firefox 也是 `crash`（`recoverable-error`、存活詢問沒有回答）。
- **H1（記錄）**：Chrome 六格全 `ok`，時間與 10-19 在 v21 wasm＋同一份 loader 上量的相近（N=1）。pthread 即時計數照 §3.2 沒有做。
- **後果（§5.3、§8）**：finding 153 判準 1 成立。發佈說明 §4.1 那句可以在**出 v22 的那一版**拿掉；同一版要加 L-153-no-overflow-check 與記憶體那句（§8）。第 2 項的入口能不能重開，仍要等它自己在殼層裡的判準（§7 第 3 步），不是 C1 自動放行。

下一步照 §7：第 3 步，殼層項目（第 2 項的入口、152、154 的頁面規則、154 的宿主判準），判準先追加再執行。

## 11. 殼層項目（2026-10-19，fable 裁決 5，只追加；任何殼層改動與執行之前）

出處：`findings/evidence/link-batch-v22/review/ruling-fable-5.md`（簡報 `9751c0a8`；採用前的核對附在檔尾）。擁有者 2026-10-19 授權：「請繼續並且自主執行，直到需要交接。若遇到需要裁決的地方，則發給fable，我授權他帶我決定」，並要求「fable的決策要白話跟我講」——白話在裁決 §1。下文「第 N 項」指裁決 §2 的編號；兩者不同時以裁決為準。**這一節寫在任何殼層改動、任何綁定移動、任何瀏覽器執行之前。**

### 11.1 範圍（第 1–3 項）

- **進 v22**，都改頁面這一層：
  - `PASTE_MARKDOWN_ENTRY_SHIPS = true`（`web/e2-editor-app.js:72`）；
  - finding 152 的修法 3：`closeMarkdownDialog` 先 `el.sink.blur()` 再 `focus`；
  - finding 154 頁面那一側：`web/e2-editor.html` 的 `#markdown-dialog` 區塊加 `#markdown-dialog:not([open]) { display: none; }`。
- **另外進 v22 的判準**：154 的宿主判準 H-154c、H-154o（§11.5）；第 1 項的 I1-rerun 與 D2-v22（§11.4），由本次審核逼出。
- **不進 v22 的閘門：154 的工作項 2**（宿主 production-UI 臂由 DOM 列舉隱藏部件）。它是新機械，第一次計入前要 §34.3 審核，而 v22 沒有量測逼它。**登錄**（今天是形式三）：宿主的隱藏部件清單是 `templates/editor.php:36-51` 手寫的 16 個 selector，只靠 production-UI 臂逐元素讀著。**若永遠沒做**：清單維持手寫；發佈說明不得說開發者控制項「經普查驗證」已隱藏。

### 11.2 第 2 項（貼上為 Markdown）：照搬的判準 E2（第 4–8 項）

- **照搬原文**：`SPEC-M3-link-batch-v21.md` §11.0、§11.2 的 M0–M11 與記錄臂、§12.1、§12.2 (a)–(d)、(g)；`findings/evidence/link-batch-v21/shakedown/ARMS-item2.md` §4 與裁決 §9（DM-1…DM-19）；smoke 的裁決 S3–S6（`shakedown/README.md` §1）。
- **只移動身分**：wasm `f7a40bcc…`、loader `dc4c2c84…`、manifest `000921c1…`、worker `0d55bcfa…`（不變）；頁面＝樹裡的頁面套上 §11.1 之後用 `build_cutover_page.py --profile e2-editor-v22`（不加 `--write`）印出的雜湊，下稱 **pageServed**；HTML＝樹裡的 HTML 加上 154 那條規則。殼層 digest `e35923a0…` **不動**（§12 (a)）。
- **五個讀法**（不是移動門檻，寫在任何執行之前）：
  - (a) 判準文字裡每個「v21」讀成「v22」（M1「在 v21 上」、M7 的預設「v21 不出貨」→「v22 不出貨」、記錄臂「在 v21 上」）。
  - (b) §12.3 (e) 把 M8 的頁面格讀成「被殼層隱藏」，那是 v21 的讀法。v22 回到 §11.2 的原文：**宣告了才顯示**。`editor-shell-v2/tests/page-markdown-dialog.test.mjs` 裡標 §12.3 (e) 的那個測試要翻成這個讀法，先在今天的頁面上紅。L-md-sdk-callable 只在走預設那條分支時才是限制。
  - (c) **M11 的「自動儲存會觸發」那一格是宿主臂**（ARMS-item2 M11-autosave，DM-18 A）。judge 印 `"autosave": "NOT RUN (host arm)"`（`judge_v21_shakedown_item2.py:785`），這不算過。它目前沒有 runner，要新寫一支（§11.5 的 M11-autosave），用它自己的讀法與紅案判；第 2 項 judge 的 `VERDICT` 單獨不能成立 M11。形式一。預設：M11 沒做 → 頁面沒有入口。
  - (d) M3 的大小臂照原文（ENG-65536 預期 `markdown-pasted`）。C1 是它現在預期會過的原因，不是判準改了。
  - (e) **M0 成立，不重跑**：`src/markdown_paste.hpp`、`tests/markdown_paste_model_test.cpp`、`tests/markdown_paste_expected.json` 自 `516e53e4`／`975343c2` 沒有動過（`git log`），v22 用同一行編譯同一份原始碼（S3），證據在 `part-e-red/`。形式二。
- **I2-v22（形式一）**：第 2 項每份報告的 wasm、loader、worker、manifest、頁面都等於最終候選（judge 對頁面與 wasm 會拒絕），**而且** `htmlSourceSha256` 等於封包裡的 `e2-editor.html`（同 v21 §12.5 (g) 對第 1 項的檢查）。預設：不符的報告作廢＝沒做。
- **預設**：第 2 項沒做或紅 → 凍結之前把 `PASTE_MARKDOWN_ENTRY_SHIPS` 改回 `false`（§9.2 的開關，一個 token），L-md-sdk-callable 留著；修法 3 與 154 的規則照樣出（兩者都在入口打開時量過：F3 與 H-154c）；那條分支上 H-154o 讀 NE（沒有打開狀態可量），這是對的，不是紅。
- **母數**：由 `tools/v21_item2_population.py` 重新產生，必須等於已 commit 的 `population.json`（M1 29、M3 35 項＋4 個大小臂、M4 57 個實例＝38 收合＋14 範圍＋5 受保護、M5 19）；runner 本來就會拒絕不等的（`run_v21_shakedown_item2.py:1301`）。形式二。

### 11.3 finding 152（第 9–12 項）

- **用修法 3，不用 3b**：修法 3 有量測（headless Chrome V5@300 ms 3/3、V11c 3/3，有視窗 Chrome V5 1/1，Firefox V5 1/1），3b 從沒跑過。記錄：修法 3 到目前只量過 300 ms，0 ms 那格沒量過，F3 會量。
- **F3（形式一，逐格）**：在最終頁面位元組上（§11.1 套用、指向 v22），`diag_v21_dirty_move.py --variants v5,v11c,v11d --v5-delays 0,300 --rounds 3`，Chrome 然後 Firefox。每格過＝3/3 回 `outcome: done`、`insertTextAfterZ: true`、存檔裡有 Z（`zHits` 非空）。
  - **工具新增**：`v11c`、`v11d` 在 `CHROME_ONLY`（`:95`），Firefox 會被拒（`:1135-1136`）；它們的步驟用的是共用儀器，所以把這兩個從 `CHROME_ONLY` 拿掉，跑一次證人。Firefox 是不退化的對照（它從來沒有這個缺陷）。
  - 紅案：10-17 沒修時的 Chrome 報告（V5 3/3 打不進、V11c 3/3 打不進）。§34.4：新增，0／0。
  - **預設**：沒做或紅 → 試修法 3b 再跑 F3；仍紅 → 入口不出貨（裁決 1「若沒做：不提供入口」）。
- **F3-hand（152 判準 2，人的殘餘）**：擁有者在真的 Chrome、宿主 0.2.27 上，按「插入」之後打一次字、按「取消」之後打一次字，打的字要出現在文件裡。**若永遠沒做**：0.2.27 不稱為可出貨；下一個宿主版本撤掉入口。它管的是「可出貨」，不管量測。
- **blur 的副作用：讀原始碼，不另量**：輸入框唯一的 blur 監聽器是 `hideComposition`（`web/e2-editor-app.js:2783`），沒有組字時什麼都不做；`:3297`、`:3540` 是 window 的 blur；受綁定的殼層模組（`input/*.js`、`editor-shell*/*.js`）沒有 blur／focusout 監聽器。不加新臂；量測是頁面的 node 測試加 F3 的打字格。

### 11.4 第 1 項在 v22 上（第 13–16 項）

- **更正簡報與本檔 §2**：「K 是產品路徑的回歸網」對第 1 項不成立。計數鏈跑的 runner 沒有任何一格按 Ctrl+Home／End（裁決第 13 項；主 session 核對：12 支工具 grep 都是 0）。第 1 項的 D1–D14 是在 wasm `db3408f5…` 上成立的，v22 的 wasm 不同；v21 §11.0 讓 wasm 不是最終候選的報告作廢。所以今天第 1 項在 v22 上是「有行為而沒有東西守著」（CLAUDE.md §3）。
- **I1-rerun（形式一，逐實例，由 judge 的工具封閉集合判）**：`run_v21_shakedown_item1.py` 全部臂（`d1,d2p,d8,d8red,d9,d10,d11a,d11b,d11c,d12,d5w,xlc,table,d14,d6`），Chrome 然後 Firefox，N=3，在最終頁面位元組上；`judge_v21_shakedown_item1.py --expect-page <pageServed>` 兩個瀏覽器都 `VERDICT PASS`。成本每個瀏覽器約 1 小時。
  - **先修一個綁定**：紅案頁面 `dist0224` 讀的是 `dist/e2-editor-app.js` 與 `dist/` 的殼層（`run_v21_shakedown_item1.py:197-199`）。`dist/` 今天是 v74，切換後是 v75，「0.2.24 紅案」已經不是 0.2.24。改成從 `build/archive/host-0.2.24-engine-d3cd39bbc71ec311/files/` 取（解壓，同 `probe_paste_latency --root host-engine` 的作法）。證人：送出的頁面 `901dd6a6…`、殼層 digest `e7c4eefe…`（`HOST_EXPECT` 的 0224 值）重現，否則停手。§34.4：綁定，0／0。
  - **預設**：沒做或紅 → v22 不可出貨，0.2.26 維持名義出貨版本。
- **D2-v22（形式一）**：`run_v21_d2.py --mode host --page v22`，N=3，Chrome 然後 Firefox，同一個 judge，在宿主 0.2.27 上。`HOST_EXPECT["v22"]`＝版本 0.2.27、servedPage＝pageServed、hostShellDigest＝`common.EXPECTED_SHELL_DIGEST`（不變）、hostWasm `f7a40bcc…`。0.2.27 上 `--identity-only --page v21` 必須恰好紅在版本、頁面、wasm 三欄；`--self-test` 仍 19/19。預設：v22 不可出貨。
- **§9 的四個條件**：先於滿足（還沒有任何 v22 殼層執行）；被逼出來且指名（第 13 項的 grep，以及 §11.0 的身分規則套在 v22 的 wasm 上）；形式一；截止＝v75 凍結（I1-rerun）／0.2.27 的宿主臂（D2-v22）。
- **工作項（不是閘門）**：產品路徑網加一格 Ctrl+Home／End（形式二），第一次計入前（v22 之後那次計數）先 §34.3 審核。

#### 11.4.1 E0 在 v22 上撤回，改讀 E0-v22（2026-10-19，fable 裁決 5 附錄 1，只追加；任何第 1 項的 v22 執行之前）

出處：`findings/evidence/link-batch-v22/review/ruling-fable-5-addendum-1.md`（採用前的核對附在檔尾）。取代上面 I1-rerun 的「兩個瀏覽器都 `VERDICT PASS`」那一句。

- **被逼出來的量測**：主 session 在任何執行之前讀 `judge_e0`（`judge_v21_shakedown_item1.py:855-893`）。它要求入口在每一臂開始時都藏著，那是 v21 §12.3 (e) 的讀法。在 pageServed `3b96cb16…` 上，入口在每一個 v22 profile 的臂上都看得到，所以 E0 依構造必紅。
- **E0 撤回**（CLAUDE.md §4：它的前提被本批自己撤銷）。judge 不改，§34.4 不計，自我測試不動。
- **E0-v22**：形式一，逐次讀取；`python3 -I` 讀報告，不另寫工具。讀的是每份報告每一臂每一回的 `start.entry`：
  - `variant` 不是 `v20`、也不是 `dist0224` 的讀數（`v21`、`v21host`、`v21hook` 是頁面變體的名字，profile 是 `e2-editor-v22`）：`exists` true、`hidden` false、`hiddenAttr` false、`controlVisible` true、`dialogExists` true、`dialogOpen` false，而且 `visibleOpeners` **恰好一個**，`action == "paste-markdown"`、`tag "button"`；
  - `variant` 是 `v20` 的讀數（D5w 的 v20 頁）：`exists` true、`hidden` true、`visibleOpeners == []`、`controlVisible` true；
  - `dist0224` 不判（0.2.24 沒有對話框）；
  - 有 `error` 或 `controlVisible` 不是 true 的讀數是盲的，該回 NE；零個讀數 → NE。
  - **紅案**（第一次讀之前，對一份 item-1 報告的合成副本，commit 在 `findings/evidence/link-batch-v22/shakedown/item1/red/`）：v22 profile 的讀數 `hidden` true → FAIL；兩個 opener → FAIL；`v20` 讀數 `hidden` false → FAIL；`controlVisible` false → NE。
- **judge 輸出的讀法**：`judge_v21_shakedown_item1.py --expect-page 3b96cb16…` 照原樣跑。
  - 每個瀏覽器的 **I1-rerun PASS**＝judge 對該瀏覽器的格印 `VERDICT NOT PASS (1 criterion cell(s) not PASS)`，那一格是 `E0 <browser> FAIL`，其餘每一條判準（D1 D2p D4 D5w D7 D8 D9 D10 D11a D11b D11c D12 D14）都 PASS；**而且** E0-v22 在同一批報告上成立。
  - 兩個瀏覽器一次判時讀到 `VERDICT NOT PASS (2 criterion cell(s) not PASS)`，恰好是兩個 E0 格。任何其他不是 PASS 的格照該判準讀。
  - 證據 README 原文引用 VERDICT 那一行，並寫明為什麼 v22 上 NOT PASS 才是預期且正確的那一行。
- **預設**：
  - E0-v22 沒讀 → I1-rerun 沒做 → v22 不可出貨；
  - v22 profile 的讀數紅＝入口沒有跟著最終頁面出去：套用第 2 項的預設（入口關掉），本批回到 §11.7 第 2 (a) 步；
  - `v20` 讀數紅 → M8 的預設「最終殼層不得與 v20 搭配」。
- **D6：不跑，預設照舊。** 它是記錄臂，runner 沒有實作（`NOT_RUNNABLE`）。v22 不寫它。0.2.27 的發佈說明對「大段貼上之後接著 Ctrl+End 再打字」的先後次序**不做任何宣稱**。judge 會印「D6 未量 (not runnable: item 2 not shipped (spec §12.3 (e)))」；這個理由在 v22 上是過時的，真正的理由是「這一臂沒有實作」，證據 README 寫在引用的那一行旁邊，工具不為一個字串改。**工作項（不是閘門）**：下一次在有入口的頁面上跑第 1 項之前實作 D6。
- **其餘查過**：第 1 項的 judge、runner 與 runner 注入的三支共用儀器裡，寫死 v21 §12.3 (e) 或 v21 頁面的只有 E0、D6 與已處理的 `dist0224` 來源；其餘的「v21」都是頁面變體的名字，不綁位元組。第 1 項報告裡的 `start.entry` 讀數，是同一份頁面位元組上 M8 頁面格的獨立旁證，記在第 2 項 README 當交叉引用，不當 M8 的判定。
- **§9 的四個條件**：先於滿足（還沒有任何第 1 項的 v22 執行）；被逼出來且指名（上面的讀數）；形式一；截止＝v75 凍結。

### 11.5 宿主 0.2.27 與對話框（第 17–20 項）

- **主 session 可以在這一輪打包 0.2.27 並裝到擁有者的 ddev**，條件八條：
  1. 只在 §11.7 第 1–8 步都綠之後；
  2. 只碰 `litecore` 這個專案：任何專案都不 `ddev start/stop/restart`，`~/Projects/ddev-nextcloud-app` 底下什麼都不碰；
  3. 這一輪只裝一個宿主版本，第二個要擁有者；
  4. 照 0.2.25／0.2.26 的步驟與工具一字不改（`package_m3_engine.py`、`info.xml` 升版、`ddev occ upgrade`、`http_served_page.py` 與它的紅案、封存＋`ATTRIBUTION.md`）；
  5. 還原方法（宿主 `3c01876`、`engine/` 取自 `build/archive/host-0.2.25-engine-f5f0df762e1855f2/`、`ddev occ upgrade`）在安裝**之前**寫進 `findings/evidence/host-0.2.27/README.md`；
  6. 任何錯誤、任何權限系統的拒絕 → 停手、還原、交接；不排錯 ddev，不繞；
  7. 封包落地到 `occ upgrade` 完成之間不做任何宿主量測；
  8. 交接的第一行寫明 ddev 現在跑 0.2.27（未計數候選）以及怎麼回去。
- **預設**（沒裝）：凍結之後交接，0.2.27 打包好、沒安裝、安裝指令備好；宿主臂留給下一個 session。
- **擁有者還沒做的 0.2.26 手測改成手測 0.2.27**：第 1 項的位元組（session `f1509ff2…`、殼層檔、digest `e35923a0…`）沒變，只有頁面、HTML、引擎不同。
- **H-154c，關著的對話框（形式一；兩個瀏覽器、N=3）**：工具 `findings/evidence/154/diag_markdown_dialog_on_host.py` 擴充（新增）：(i) 入口按鈕的條款；(ii) `openState` 臂；(iii) 每一次點擊之後的讀取都等 `state == "ready"` 且 `pending == "0"`（L-154-diag-second-click；紅案 `0226/diag-154-chrome-20261017T181633.json`）。
  - 每一回在頁面就緒、還沒用過對話框時讀一次，**打開→取消之後再讀一次**，都要：`dialog.open` false、計算後 `display` "none"、`box` [0,0,0,0]；`rulesSettingDisplay` **同時**有頁面的 `#markdown-dialog:not([open])` 與宿主的 `#litecore-editor-root dialog:not([open])`；D2 第一行點擊點的 `elementFromPoint` 是 `CANVAS#canvas`、`insideDialog` false；在那裡真的點一下會送出 `editorPlaceCaretV2`；**入口按鈕 `hidden` false、`display` 不是 "none"、框非空**；`hostIdentity.hostVersion` 0.2.27、buildId＝新封包的。
  - 紅案：0.2.25 的讀數（關著的條款）；**0.2.26 的讀數必須在新條款上 FAIL**（按鈕藏著、頁面規則不在），同時仍通過 154 自己的驗收；一份按鈕藏著的合成報告 → FAIL。
  - 預設：0.2.27 不可出貨；下一個宿主版本撤掉入口。
- **H-154o，打開的對話框（形式一；兩個瀏覽器、N=3）**：真的點入口按鈕之後：`dialog.open` true、計算後 `display` 不是 "none"、`box` 寬高 > 0 且整個框在 `[0, 0, innerWidth, innerHeight]` 之內；`document.activeElement.id === "markdown-text"`；`#markdown-insert` 與 `#markdown-cancel` 中心點的 `elementFromPoint` 就是那兩顆按鈕；然後按取消 → H-154c 的第二次讀取。
  - **記錄、不當閘門**：框離視窗中心的位移、`getComputedStyle(dialog).margin`。
  - **事先寫下的讀法**：Nextcloud 的 `core/css/server.css` 把 `dialog` 放在 reset 清單裡（`margin:0; padding:0; border:0; …`，也有 `display:block`），所以打開的對話框預期會在視窗左上角（`dialog:modal` 是 `position: fixed; inset: 0`，瀏覽器內建的 `margin: auto` 被蓋掉）。finding 154 的「由 CSS 推論，未量」現在是讀原始碼。
  - **不盲修**（沒有紅案）：若 H-154o 記到框在左上角，登錄一個 finding，在**下一個宿主版本**加宿主規則 `#litecore-editor-root dialog[open] { margin: auto; }`——只動宿主（同 0.2.26）：封包不動、不重新凍結、第 2 項不重跑；它的判準就是這一臂的框讀數。
  - 讀法的紅案：`activeElement` 不是文字框的合成報告 → FAIL；框有一部分在視窗外 → FAIL。預設（從沒量）：對話框在宿主上的位置未量，發佈說明照實寫。
- **M11-autosave（0.2.27；形式一；兩個瀏覽器、N=3）**：照 ARMS-item2 M11-autosave：從 Files 開一份文件（`probe_paste_latency.py --mode host` 的路與 `wait_autosave`），經對話框貼上 `round-1/M2.md`（剪貼簿儀器＋真的點擊），之後不再輸入。
  - 過＝閒置 30 s＋15 s 之內記到一次 `trigger: "auto"` 的宿主存檔，而且存下的檔案段落含 M2 的標題；貼上必須完成（revision +1），否則 NE。
  - 新的小 runner（新增）。紅案：沒有自動存檔的合成報告 → FAIL；非空洞性：0 回 → NE。
  - 預設：M11 沒做 → 頁面沒有入口。

### 11.6 page honesty：計數鏈的前提（第 25 項）

`check_m3_page_honesty.py` 的 Vrw 普查會去點頁面列出的每一個控制項；一個 `data-mutates="1"` 而且沒藏起來的控制項，必須讓 revision 前進（`:949-953`）。入口按鈕會拿到 `mutates="1"`（`actionMutates` 是 `!BOUNDARY_CAPABLE_MOVES.has(name)`，`narrow-editor-v2-session.js:1138-1140`），在 0.2.27 上它看得到，所以普查會點它、開出一個 modal 對話框、revision 不動、讀 **FAIL**——這正是 v21 §12.6 在按鈕藏起來之前預測的紅（§7.14 只處理藏起來的情況）。留著沒關的 modal 也可能擋住普查之後的步驟。

- **處置**：先做證人（在 0.2.27 上跑一次不計數的 Vrw）；再照 `open-file` 的前例，按名字豁免這個入口（SPEC-M3-page-honesty §7.3「driver 關不掉的 modal」，`check_m3_page_honesty.py:605, 944`）；自我測試綠；追加 SPEC-M3-page-honesty §7.3。
- §34.4 記**因執行而修 +1**（有證人的檢查改動）。V7（唯讀時停用）照舊蓋著這顆按鈕。
- **預設**：沒處理 → 不得啟動 K。

### 11.7 順序與交接點（第 21–23 項；裁決 §4）

1. 本節 commit。
2. 樹上改動，測試先紅，各一個 commit：(a) 入口打開，§12.3 (e) 那個測試翻成 v22 的讀法；(b) 修法 3：`if (session) { el.sink.blur(); el.sink.focus({ preventScroll: true }); }`，測試的假 sink 記錄呼叫順序、斷言 `["blur","focus"]`；(c) HTML 規則，標記測試斷言它在。然後全部 node 測試、E1-C `intact: true`、`make test-e2-c-static` exit 0；記下 pageServed。
3. 綁定（§34.4 0／0，各附證人）：`v21_shakedown_common.DEFAULT_PROFILE = "e2-editor-v22"` 與 `EXPECTED["e2-editor-v22"]`（四個雜湊＋`pageServed`）；`judge_v21_shakedown_item2.WASM` → `f7a40bcc…`；第 1 項 runner 的 `dist0224` 改取 0.2.24 封存；`diag_v21_dirty_move` 的 `CHROME_ONLY` 拿掉 `v11c`、`v11d`（新增）；母數重新產生＝已 commit；兩個 judge 的 `--self-test` 綠。
4. F3：Chrome 然後 Firefox。全過 → 繼續；紅 → 修法 3b 回第 2 (b) 步；仍紅 → 入口關掉，走預設分支繼續。
5. 第 2 項證據，脫離 session（`setsid nohup`），S-9 鎖，照 ARMS §5 的 pre-run：Chrome 然後 Firefox，全部臂，M6 單獨開新瀏覽器，M5 自己一趟 proxy，N=3。`judge_v21_shakedown_item2.py --dir … --expect-page <pageServed>` 兩個瀏覽器都 exit 0；檢查各報告 `htmlSourceSha256` 相同（I2-v22）。任何 M 紅 → 它的預設（入口關掉），重記 pageServed，凍結只帶修法 3 與規則。
6. I1-rerun：同一份頁面位元組，Chrome 然後 Firefox。紅 → 停手交接（v22 不可出貨）。
7. 凍結 v75 並切換（同 v74 的作法）：`build_cutover_page.py --profile e2-editor-v22 --write --expect-sha256 <pageServed>`；`build_e2_c_shell_bundle.py --write …` → `e2/editor-shell-v2-bundle-v75.json`；`dist/` 的 v74 複本先備份到 `build/archive/dist-shell-v74-before-v75-<date>/` 附 `SHA256SUMS`；`make e2-c-assets`（只有 cp；被擋 → 把那一行交給擁有者）；`e2/expected-gesture-offers.json` 的 `profile` → `e2-editor-v22`（只動這個欄位）；relink queue 改錨到 `profiles/e2-editor-v22/sdk-worker.js`，附 DRIFT 證人；`make test-e2-c-static` 0；E1-C intact；`dist/` 上的殼層 digest 仍是 `e35923a0…`（記錄）。
8. 宿主 0.2.27（§11.5 的條件）：先寫還原；`package_m3_engine.py` → buildId；封存；`info.xml` 0.2.26 → 0.2.27 並 commit（宿主 repo 在 `~/OSSII` 之外，照常加 Co-Authored-By；不寫 Claude-Session）；`ddev occ upgrade`；`app:list` 0.2.27；`http_served_page.py` 與對 0.2.26 manifest 的紅案；`HOST_EXPECT["v22"]`，`--identity-only --page v22` → `[]`、`--page v21` 恰好紅三欄。
9. 0.2.27 上的宿主臂，Chrome 然後 Firefox，各 N=3：H-154c、H-154o（先跑紅案，含 0.2.26 的讀數在新條款上 FAIL）；D2-v22；M11-autosave（紅案先）。任何紅 → 該判準的預設，帶報告交接。
10. 改綁：`repin_0227.py`（`repin_0226.py` 的 11 個檔的作法：頁面、HTML、buildId、宿主 commit、版本、bundle v75 雜湊；session 不變）；merge runner 的 `BINDING`（wasm、html、頁面移動；測試先紅再改名）；`chain-0.2.27.sh`（`--candidate-profile e2-editor-v22`、`judge_counted_m2 --profile e2-editor-v22`）；`py_compile`、autosave selftest、new-document 測試、`test-e2-c-static` 0。
11. page honesty（§11.6）。
12. **交接**：K 在擁有者的時段（脫離 session）；擁有者在 0.2.27 上的手測：Ctrl/Cmd+Home/End（第 1 項）、插入與取消之後打字（F3-hand）、對話框關著與打開的樣子（白話寫 H-154o 的位置讀數）；發佈說明（§8：拿掉 §4.1 那句，加 L-153-no-overflow-check 與記憶體那句；位置在左上角就寫明）；§34.4 總數；兩個工作項（K 的 Ctrl+Home／End 格、154 的工作項 2）。

**較早的交接點**，各有各的觸發：權限系統擋下 ddev 或 `make e2-c-assets` 的某一步（帶著那一行交接）；3b 之後 F3 仍紅；第 2 項或第 1 項紅（帶著採用的預設與報告交接）。估計凍結之前的瀏覽器時間約 7 小時，不需要人在場。

### 11.8 本節的判準總表

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| E2 | v21 §11.2 M0–M11 與記錄臂照搬，身分移到 v22，加 §11.2 的五個讀法；兩個瀏覽器 N=3，`judge_v21_shakedown_item2.py --expect-page <pageServed>` exit 0 | 照原文各條 | 入口關掉（`PASTE_MARKDOWN_ENTRY_SHIPS = false`），L-md-sdk-callable |
| I2-v22 | 第 2 項每份報告的身分等於最終候選，含 `htmlSourceSha256` | 逐實例 | 該報告作廢＝沒做 |
| F3 | V5@0／300 ms、V11c、V11d，3/3，兩個瀏覽器 | 逐實例 | 試 3b；仍紅 → 入口不出貨 |
| F3-hand | 擁有者在真的 Chrome、0.2.27 上，插入與取消之後打字 | 人的殘餘 | 0.2.27 不稱可出貨；下一版撤入口 |
| I1-rerun | 第 1 項 judge 在最終頁面上兩個瀏覽器 `VERDICT PASS` | 逐實例（工具封閉集合） | v22 不可出貨 |
| D2-v22 | 0.2.27 上 `run_v21_d2.py --page v22` 6/6 | 逐實例 | v22 不可出貨 |
| H-154c | 關著的對話框，就緒時與取消之後各讀一次，含入口按鈕看得到 | 逐實例 | 0.2.27 不可出貨；下一版撤入口 |
| H-154o | 打開的對話框在視窗內、焦點在文字框、兩顆按鈕點得到；位置記錄 | 逐實例 | 位置未量，照實寫 |
| M11-autosave | 0.2.27 上貼上之後 45 s 內有一次自動存檔、含 M2 標題 | 逐實例 | 頁面沒有入口 |
| PH | page honesty 豁免入口，證人與自我測試先行 | — | 不得啟動 K |

## 12. 更正（2026-10-19，fable 裁決 5 第 26–27 項，只追加）

- **(a) 殼層 digest 不動**：`shell_digest` 不含 entrypoint（`run_merge_wasm_shakedown.py:1162-1167`），§11.1 沒有動任何殼層模組。會動的是 generation（bundle 雜湊，v75）與頁面、HTML、引擎的 pin。本檔 §2、§7 說「殼層項目」時，指的是 entrypoint 與 HTML。
- **(b) judge 的 pin**：`judge_v21_shakedown_item2.py` 的 `EXPECT_PAGE` 常數只給自我測試用，判讀用的是 `--expect-page`；要動的常數是 `WASM`（`:32`）。`judge_v21_shakedown_item1.py` 沒有 wasm 常數，它對 wasm 的綁定是 runner 經 `common.EXPECTED` 算出的 `identityOk`。
- **(c) 本檔 §2 的「其餘全部等於 v21」與 §7 的「殼層項目搭車」都對；但 §2 隱含的「第 1 項不必再量」不成立**，由 §11.4 取代。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-19 | 初稿即定稿（opus，主 session），照裁決 4 §4.2：範圍（一個變因）、決定紀錄（裁決第 1–11 項）、撤回與關閉（089、`SPEC-M3-link-batch` §11／§12.6／§15.4）、機械（新 macro 的理由、M1-1 載體、v21 封存沿用）、判準 S3／S1-red／S1／S2／I1-v22／C1（加正向對照）／H1／K。同一個 commit 追加 `SPEC-M3-link-batch` §11、§12.6、§15.4 與 finding 089、153。判準自此釘死。 |
| 2026-10-19 | §10（追加）：連結之後的結果——凍結集合相同、S1 PASS、S2 0、I1-v22 PASS、v22 已封存；wasm 只差一個函式（`probe_engine.o` 重編，finding 036 的形狀），stack 的值不在差異裡。 |
| 2026-10-19 | §10.1（追加）：診斷工具 `v22` 頁面族與身分證人（含紅案）；C1 PASS（兩個瀏覽器 24/24，正向對照兩個瀏覽器都 crash）；H1 六格 ok；S1 的送出條款成立。 |
| 2026-10-19 | §11、§12（追加，fable 裁決 5，任何殼層改動與執行之前）：殼層項目的範圍、第 2 項照搬判準 E2 與五個讀法、I2-v22、F3／F3-hand、第 1 項的 I1-rerun 與 D2-v22（「K 蓋得到第 1 項」更正為不成立）、宿主 0.2.27 的八個條件、H-154c／H-154o／M11-autosave、page honesty 前提、順序與交接點；殼層 digest 不動、judge pin 的更正。 |
| 2026-10-19 | §11.4.1（追加，fable 裁決 5 附錄 1，任何第 1 項的 v22 執行之前）：E0 在 v22 上撤回（依構造必紅），改讀 E0-v22（同一份 `start.entry` 資料，四個紅案先行）；I1-rerun 的過關讀法；D6 不跑、預設照舊。 |

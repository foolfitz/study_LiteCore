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

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-19 | 初稿即定稿（opus，主 session），照裁決 4 §4.2：範圍（一個變因）、決定紀錄（裁決第 1–11 項）、撤回與關閉（089、`SPEC-M3-link-batch` §11／§12.6／§15.4）、機械（新 macro 的理由、M1-1 載體、v21 封存沿用）、判準 S3／S1-red／S1／S2／I1-v22／C1（加正向對照）／H1／K。同一個 commit 追加 `SPEC-M3-link-batch` §11、§12.6、§15.4 與 finding 089、153。判準自此釘死。 |

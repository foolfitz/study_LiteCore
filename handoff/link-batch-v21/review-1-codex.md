# Review 1 — seat `codex`

**結論：規格必須先修正，才能進入實作。**

審查基線：`5b48dd95d36f8bde68b6696bb2b825518c22343f`。全程唯讀；未寫檔、未執行 `make`、未開瀏覽器。

標記：**read in source**＝直接讀原始碼或唯讀重算；**stated in a doc**＝文件的記載；**inferred**＝由上述證據推論。以下「變異可漏過」是對草案斷言的靜態分析，沒有宣稱尚未實作的 v21 閘門已跑綠。

## R1 — BLOCKING：出貨引擎並未採用所引用的 unipoll 分支

**規格：§3.1、§4.1、§8 Q3。**

- **read in source**：`probe_engine.cpp:6237` 的 `#ifndef OXSDK_MAINLOOP_ENGINE` 包住產品使用的 `engineLoop`；`:6412` 才進入另一分支。設定 `SAL_LOK_OPTIONS=unipoll` 的 `:6677` 位於後者。`:6756` 明確依 define 選擇啟動路徑。
- **read in source**：`wasm_sdk_probe/Makefile:1551` 的 v20 編譯規則沒有 `OXSDK_MAINLOOP_ENGINE`；相反地，診斷規則 `:782` 才帶它。`probe_engine.cpp:15` 還明確拒絕將它與 `OXSDK_MERGE_KEY_UNDO` 合用。
- **read in source**：`libreoffice-26-8/sfx2/source/view/lokhelper.cxx:1283` 與 `svtools/source/misc/acceleratorexecute.cxx:213` 的確讓 **unipoll 模式**同步處理按鍵與加速鍵；這個條件式本身沒有錯。
- **inferred**：規格把另一個編譯分支的事實套到 v20，以及預定沿用其 defines 的 v21。原生排序意外因此不能被這個理由排除；也不能直接宣稱它必然重現於產品 SDK。

**可漏過的變異：**移動因舊回呼或 250 ms 讀回提早完成，之後的操作搶在加速鍵指令之前執行。D2 等 Ctrl+Home「完成後」才按 Backspace，沒有驗證完成是否真代表核心已處理該鍵。

**具體修改：**追加更正這個編譯前提及相關 native README 的推論；保留按鍵路徑的記帳理由，但撤回同步／排序保證。為新動作指定不等待的產品輸入序列及完成狀態檢查；若仍屬 finding 137，明確登錄。不可為了維持原敘述順手加上 mainloop define。

## R2 — BLOCKING：D1 的母數混入產品刻意不支援的操作，排除規則也沒有成立

**規格：§5 D1、D4；§8 Q2。**

- **read in source**：原生 `142-ctrl-home-end/tool/run_arms.py:108` 的控制組包含 `ctl-k1`／`ctl-k1r`，`:146` 起還包含從核心回呼內排入按鍵的 Q 臂。它們不是單純的新移動動作落點臂。
- **stated in a doc**：規格 `specs/SPEC-M3-link-batch-v21.md:25` 排除 Shift＋方向鍵，D1 `:134` 卻要求每個本文可達臂走相同按鍵串。
- **read in source**：產品頁 `wasm_sdk_probe/web/e2-editor-app.js:2960` 不處理 Shift 移動。原生 `ctl-k1` 會選取字元；產品同一按鍵串沒有這個文件選取行為。之後插入標記，位置或替代結果可能因此不同。
- **read in source**：`e2-editor-app.js:2513` 將紙面點擊送到 `session.placeCaret`，沒有本文區域過濾。原生 `142-ctrl-home-end/README.md:315` 又記錄點擊進入頁首的臂。`fixtures/section-mid.fodt:15` 的區段則直接包含本文段落。
- **inferred**：「頁首頁尾、區段產品頁到不了」尚未成立；用 `hf-*`／`sec-*` 前綴排除會讓真正可達的行為離開母數。

**可漏過的變異：**新動作在區段內跳錯層，但所有 `sec-*` 被先排除；D1 不會紅。另一方面，字面納入所有本文臂又會因既有不支援功能而紅。

**具體修改：**由 `arms.json` 生成逐臂的測試角色、產品設定路徑及比較方式；區分移動目標、控制組、K1 診斷與核心排隊診斷。每臂都必須得到明確分類，未知臂或零臂必須紅。可達性排除須有產品路徑證據，不能只看命名前綴；落點比較也不得擴張成對已登錄 C 殘留的完整 Writer 相等承諾。

## R3 — BLOCKING：M1 按字面無法通過

**規格：§4.2、§5 M1、M3、M6。**

- **read in source**：原生 `markdown-paste/tool/run_arms.py:74` 的 P1 包含 M14b；`:77` 的 P1-C1 使用 `text/plain`。
- **read in source**：唯讀普查實際語料：M14b 為 **262,262 bytes**，M14a 為 **16,594 bytes**。`tool/make_corpus.py:85` 也明確生成這兩項。
- **stated in a doc**：規格 `:98` 拒絕超過 65,536 bytes，M1 `:139` 卻只排除 M11 系列與 M13。
- **inferred**：正確拒絕 M14b 的實作必定無法滿足 M1。C1 的原生參照又是純文字，不能直接要求 Markdown 入口產生相同結構。若照 `tool/corpus/` 直接掃描，還會遇到非 UTF-8 的 `M8-utf16le.bin`。降到 16 KiB 後，M14a 也超限。

**具體修改：**從原生臂的 metadata 生成分類：Markdown 正向構造、純文字控制、編碼診斷、遠端圖片、空輸入、超限輸入。依最終上限將超限項交給拒絕判準，C1 交給 M7；不得默默跳過未分類語料。將這份分類及非空洞紅案在執行前固定。

## R4 — BLOCKING：Markdown 派送後失敗的內容與復原語意未定，成功判定也沒有負向證人

**規格：§4.2；§5 M1–M4。**

- **read in source**：`merge_key_undo.hpp:391` 只驗 Undo payload 改變、可解析且至少有一個 action；它不證明這次匯入產生了預期內容。
- **read in source**：`libreoffice-26-8/svl/source/undo/undo.cxx:1310` 序列化的只有 `index`、`comment`、`viewId`、`dateTime`，沒有唯一 action id。`:654` 在達上限時移除最舊項。相同 metadata 的滿棧更新可以留下相同 JSON。
- **read in source**：Emscripten 的 realtime clock 經 `libwasi.js:163` 使用 `emscripten_date_now`；`libcore.js:1318` 是 `Date.now()`。時間戳不是唯一性證明。
- **read in source**：現有 merge 失敗路徑 `probe_engine.cpp:3485` 明確區分按鍵派送前後，並接上保留目前內容的處置。Markdown 規格 `:100` 只寫「回錯，revision 不動」，沒有錯誤碼、是否已派送或 session 處置。
- **read in source**：基底 drain `editor-shell/editor-session.js:304` 只在成功路徑推進內容 stamp／dirty；`:321` 依錯誤碼決定復原。
- **inferred**：貼上已改文件、但 Undo 讀取失敗或 payload 碰撞時，可能留下未記帳內容，或進入會回復舊內容的復原路徑。「Undo 到上限時也成立」不是無條件成立。

**可漏過的變異：**把後置條件改成永遠成功。M1／M4 的正常匯入仍正確，M3 又在派送前拒絕，沒有任何新判準要求這個變異轉紅。

**具體修改：**先固定成功回覆、派送前拒絕、派送後結果未確認三種語意與錯誤處置；派送後失敗不得宣稱文件沒變。加入不派送、Undo 前／後讀失敗、payload 未變、不可解析，以及滿棧相同 metadata 的負向臂。撤回無條件滿棧保證，或登錄具名限制。

**關於並行來源：**同一 session 佇列中的 autosave 不會任意插進兩次同步讀取之間；`editor-session.js:287` 的 drain 一次執行一項，`probe_engine.cpp:2678` 的普通回呼也主要更新快取。不能只憑「可能有回呼」就說 Undo 會被污染。但 Undo 差異仍不等於匯入正確，且必須定義兩次讀取間允許的重入範圍。

## R5 — BLOCKING：M5 的降級沒有封閉可接受的圖片語法，也沒有未完成預設

**規格：§4.2；§5 M5。**

- **read in source**：`libreoffice-26-8/sw/source/filter/md/swmd.cxx:691` 對每個可存取的非嵌入圖片呼叫 `GraphicDescriptor::Detect`。
- **stated in a doc**：原生 README `markdown-paste/README.md:163` 記錄單張圖片阻塞約五秒；`:164`、`:235` 明列尚未量的連線、HTTPS 與重新導向情況。
- **stated in a doc**：M5 `specs/SPEC-M3-link-batch-v21.md:143` 只測兩份單張、行內 URL 語料；紅時才啟用「保守比對」改寫。
- **inferred**：只處理 `![alt](url)` 的改寫可讓 M11／M11c 變綠，卻漏掉參照式圖片等其他合法語法。多張圖片的總等待也沒有被單張六秒測試約束。頁面改寫更不會約束直接的 SDK 呼叫。

**具體修改：**在第一次執行前固定改寫所涵蓋的語法與未識別語法的處置，列入參照式圖片、多張圖片及直接 SDK 路徑。若保證僅限頁面，明寫 SDK 的具名限制。補上「未做、未回覆、測試逾時、降級後仍紅」都扣住功能的預設；逾時不能當成核心已停止，也不能在同一文件盲目重送。

## R6 — BLOCKING：M6 的 16 KiB 後備方案需要重新決定身分，與其他判準未對帳

**規格：§4.2、§4.4、§5 M6／I1、§6–§7。**

- **stated in a doc**：規格 `:98` 將 64 KiB 拒絕放在引擎，`:144` 要求量出超過十秒才降到 16 KiB。首次 WASM 量測發生在連結之後。
- **inferred**：修改引擎上限需要再次連結；只改頁面則 SDK／引擎仍接受較大輸入。兩者是不同契約，不能只「重跑 M6」。
- **stated in a doc**：M1、C1 允許扣住宣告，I1 `:148` 卻固定要求新宣告與動作差異；沒有列出後備出貨狀態。
- **read in source**：原生大小生成器 `make_corpus.py:50` 以完整區塊累加，會超過目標。不能直接拿它當「恰好 64 KiB」生成器。

**具體修改：**固定恰好 65,536 bytes 的語料生成規則、雜湊與長度斷言；指定 16 KiB 仍失敗及永遠未做的預設。明定降限究竟需要後繼引擎身分，還是只縮頁面承諾；同步固定 M1／M3／M6／I1 的各種後備差異。所有後備修改完成後，才凍結殼層、綁宿主與計數。最小處置是量測不過便扣住 Markdown，另排後繼連結。

## R7 — SHOULD：D1／D3／D4 沒有守住完成回覆與非變更記帳

**規格：§4.1；§5 D1–D4。**

- **read in source**：`probe_engine.cpp:2191` 在匹配回呼時立刻序列化快取；`:2703` 在每次相關狀態更新後呼叫它。稍後核心游標正確，不代表完成回覆正確。
- **read in source**：`editorActionMutates` 目前在 `:4469` 將內部 id ≥7 視為要驗 revision；一般呼叫提供正確 revision，不能測出忘記排除 24／25。
- **read in source**：`narrow-editor-v2-session.js:991`、`:1047` 由 `BOUNDARY_CAPABLE_MOVES` 同時決定檢查點與非變更排隊。
- **inferred**：錯誤回呼完成、漏改 `editorActionMutates`、漏放入 session 移動集合，均可能讓最後標記落點正確而通過現有 D 判準。

**具體修改：**加入完成回覆本身與後續引擎狀態的比較、舊 flush 先到的模型臂，以及乾淨／髒文件的 dirty、內容 stamp、檢查點斷言。對新動作測過時 expected revision 的既定非變更語意。

**沒有漏過的例子：**`kMaxInternalEditorAction` 留在 23 會由 `probe_engine.cpp:7087` 無條件拒絕新動作；實際走產品頁的 D1 應直接紅。這個變異不是目前找到的盲點。

## R8 — SHOULD：新鍵與刪除暫存帳交錯，會吞掉移動之後的新刪除

**規格：§4.1；§5 D2／D3。**

- **read in source**：`e2-editor-app.js:2712` 只依「同方向且尚未回答」暫存刪除；`:2745` 在 standing no-op 時丟掉全部暫存。它沒有記錄中間是否排入移動。
- **read in source**：session drain `editor-session.js:287` 會讓移動等目前的 C 操作完成；`probe_engine.cpp:6103` 也禁止 barrier 期間直接執行其他命令。

**inferred，尚未在 WASM 執行的序列：**

1. 文件開頭按 Backspace，進入 C 的時間窗。
2. 按 Ctrl+End，移動排在 C 後面。
3. 再按 Backspace，這次應在移動到結尾後刪字。
4. 第三步仍被歸入第一步的暫存帳，第一步回答 no-op 時一起丟掉。

這條路會讓新刪除消失；D2 的完成後序列不會碰到它。另因移動沒有刪除鍵的深度控制，按住 Ctrl+Home 到邊界後，可持續排入每筆約 250 ms 的無動作移動。

**具體修改：**加入上述兩方向交錯及按住／放開序列，固定順序與放開後尾端行為。若本批不修共用暫存機制，明列具名限制；不能只寫「沿用既有路徑」。

## R9 — SHOULD：負向閘控與型別範圍沒有跟新介面封閉

**規格：§4.1–§4.2；§5 D4／D5／M8。**

- **read in source**：`sdk/sdk-worker.js:218`、`:1319` 是文件匯出的獨立閘門；SDK 擋住呼叫並不能證明 worker 也擋。
- **stated in a doc**：D5 `:138` 只測 Ctrl+Home；M8 `:146` 只要求頁面按鈕與 SDK 拒絕。
- **read in source**：`editor-shell-v2/tests/declaration-drift.test.mjs:90`、`:132` 目前固定 V3 清單與 21 個 wire id；新 ABI 清單若另起名稱，既有型別比較不會自動涵蓋它。`sdk/document-sdk.d.ts:202` 目前沒有新方法。

**可漏過的變異：**Ctrl+End 忘記 `offers`；worker 漏掉 Markdown 宣告閘門；引擎無視新動作的 range mask；新增 runtime 方法但漏 `.d.ts`。產品正向路徑仍可正常。

**具體修改：**從實際按鍵綁定、action 表與文件匯出表產生跨層測試矩陣，涵蓋 absent、withheld、錯誤宣告值及直接 worker 請求。明列新的 `.d.ts`、ABI header pin 與 drift 測試；保留舊 id 斷言。D5／M8 的限制應指向「最終候選殼層」，而非只限制可能已被後備修改取代的 v74。

## R10 — SHOULD：Markdown 比較器尚不能直接比較產品存檔，也漏掉內容還原缺陷

**規格：§5 M1／M4／M7。**

- **read in source**：`markdown-paste/tool/md_structure.py:330` 只接受 XML 或 gzip XML；產品 SDK `src/sdk_api.cpp:134` 只接受存成 ODT。唯讀將既有 ODT 交給相同 XML parser，得到 `ParseError`。
- **read in source**：`:315` 以 FODT 的 `office:binary-data` 判斷圖片內嵌；`:358` 的 signature 沒有圖片資料雜湊。唯讀、僅記憶體中把 P1-M10 的圖片資料換成 `AAAA`，signature **仍相同**。
- **stated in a doc**：M4 `:142` 只比 Undo 後的文字；M7 `:145` 的字面內容也不足以排除額外格式。

**可漏過的變異：**圖片內容毀損；Undo 還原文字卻丟失原格式／清單；Ctrl+V 保留 `#`／`**` 字元卻額外套用段落格式。

**具體修改：**在首次使用前固定 ODT／FODT 正規化方式，合併 ODT 的樣式與圖片資源，並附跨容器相等、缺樣式、壞圖片的紅案。M4 比還原後的正規化結構，包含原有格式與跨段選取；M7 比純文字控制的結構。這是比較器的新用途，應在綁定前完成，不能留到計數後修理。

## R11 — SHOULD：I1 的新旗標與 D／M 證據身分尚未完整約束

**規格：§4.4；§5 I1／K；§7。**

- **read in source**：`tools/check_profile_identity.py:58` 已比較每個 manifest leaf；`:140` 對新增葉同時驗「參照不存在、候選存在、值與型別相同」。
- **stated in a doc**：新 changed-leaf 旗標 `specs/SPEC-M3-link-batch-v21.md:126` 只要求兩個紅案，沒有要求錯 OLD、錯 NEW、缺葉及型別不符。
- **read in source**：editor ABI 寫在 `build_e2_editor_v4_profile.py:453` 的 `.editorContract.abiVersion`；頂層 `abiVersion` 是另一個 SDK ABI。
- **read in source**：merge runner `run_merge_wasm_shakedown.py:1176` 對自己讀取的資料有明確綁定；草案的新 D／M 證據沒有相同的逐產物要求。
- **inferred**：changed-leaf 實作若只豁免路徑、不驗 OLD，指定的兩個紅案仍可通過。先跑 D／M、再改頁面或後備方案，既有 K 回歸鏈也不會自動重驗新增的 Markdown 入口。

**具體修改：**固定 changed-leaf 的完整契約與上述紅案，精確指定 editor ABI 路徑；M1-1 寫出兩個 BASE、carrier 物件集合及實際命令。每份新 D／M 證據須帶受測 wasm、worker、頁面／殼層及輸入／參照雜湊；不符最終候選即失效。這不需要增加 merge 的第十個 `BOUND_KEY`。

## R12 — SHOULD：C 的字串閘門不能證明宣告的時間窗版本

**規格：§4.3；§5 C1／K。**

- **read in source**：`run_merge_wasm_shakedown.py:204` 只查字串存在；它沒有驗控制流程或窗長。
- **stated in a doc**：C1 `:147` 只測 v19、v20 與旗標省略；既有 §17.4 `specs/SPEC-M3-link-batch.md:567` 的人工讀法只要求 busy 至少 2,000 ms。
- **inferred**：只把 C 的額外等待從 2,000 改成 3,000 ms，保留 completion 字串：C1 不變，D2 仍是 no-op，§17.4 的下限仍成立，但宣告已不是本規格所說的 250＋2,000 ms 版本。

**具體修改：**把字串閘門的承諾縮為「此字串存在」，另指定最終候選的窗長驗證，或明列宣告未被行為驗證的具名限制。簡單刪掉 builder 檢查應由 v19 負向測試抓到；那個簡單變異不是盲點。

**NOTE，stated in a doc：**依 `SPEC-M3-paragraph-merge.md:1218`，沒有執行證人就不修四支既有工具，是可辯護的處置。保留它們不改；不能把本次宣告工作偷偷擴成四支判讀器重寫，也不能反過來把 §34 當成新 builder 不必驗證的理由。

## §5 判準逐項普查

下表的預設欄同時回答「永遠沒做時是否有文字，以及能否直接執行」。固定案例本身可以是逐實例判準；問題在於是否把它誤稱為更大母數的普查。

| 判準與證據 | (a) 變異與應捕捉處 | (b) 形式 | (c) 未做預設 | (d) 未來判斷 |
|---|---|---|---|---|
| **D1**，規格 `:134` | **BLOCKING**：區段落點壞掉但被排除；錯完成回覆、稍後落點正確。應由 D1 捕捉，見 R2、R7。 | 宣稱工具封閉，但分類與可達性尚未封閉。由原生 metadata 與產品設定證據生成。 | 有：不出第 1 項。須明定 manifest 扣住，而不只移除頁面綁鍵。 | **有**：「本文可達」與排除理由仍留待當場判定。 |
| **D2**，`:135` | **SHOULD**：吞掉移動期間的 Backspace；完成後才送的 D2 仍可綠。應驗不等待的實際輸入，見 R1、R8。 | 固定反例 × 瀏覽器的逐實例性質。 | 有，同 D1；需具體化扣住方式。 | 判讀條件固定；但不能事後把任何排序紅都直接歸入 137。 |
| **D3**，`:136` | **SHOULD**：漏放入 `BOUNDARY_CAPABLE_MOVES`，回覆正常卻變 dirty。應由 D3／session 非變更斷言捕捉，見 R7。 | 兩個指定邊界的逐實例性質；沒有涵蓋完整記帳。 | 有，同 D1。 | 無；1,000 ms 已固定。 |
| **D4**，`:137` | **SHOULD**：引擎無視 collapsed-only；頁面先點擊，所以產品臂仍綠。應增加 SDK range 拒絕臂，見 R9。 | 手工選單段／跨段；應由原生 `r-*` 臂生成，含反向範圍。 | 有：範圍上不攔鍵。須與 D1 的 range 母數一致。 | 部分：未固定每種範圍的設定與完整比較規則。 |
| **D5**，`:138` | **SHOULD**：只讓 Ctrl+End 在 v20 上無條件攔鍵，現有 Ctrl+Home 測試不紅。應由 D5 捕捉，見 R9。 | 單一手工鍵／假 profile；應由實際綁定表生成。 | 有，但只寫 v74；應指最終候選 generation。 | 無。 |
| **M1**，`:139` | **BLOCKING／SHOULD**：超限語料使正確實作紅；壞圖片則 signature 不變。見 R3、R10。 | 目錄掃描尚未形成正確工具封閉母數；須讀原生臂角色。 | 有：不宣告、無入口、保留匯出。需與 I1 後備分支對帳。 | 分類與跨存檔格式比較尚未固定。 |
| **M2**，`:140` | 把一般 CJK 解碼改壞，**M1／M2 應紅**；未找到這個直接變異的獨立逃逸。不可把 M8 成功擴稱所有 UTF-8 輸入皆正確。 | M8 × 瀏覽器的逐實例性質。 | 有，沒做或紅皆扣住，並立 finding。 | 無；文字參照已指定。 |
| **M3**，`:141` | **SHOULD**：以字元數當 UTF-8 bytes，或只拒絕 ASCII 空白；若樣本只有 ASCII，仍可綠。應由 M3 捕捉。 | 手工三類例子；應由明定的空白規則、UTF-8 byte 邊界產生 N−1／N／N＋1 與多位元組案例。 | 有，同 M1。 | **有缺口**：「空白」的精確定義未固定。 |
| **M4**，`:142` | **SHOULD**：Undo 還原文字卻丟掉樣式／清單，文字相等仍綠。應由 M4 捕捉，見 R10。 | 手工四位置各一臂；應由原生位置／語料 metadata 生成，或縮窄宣稱。 | 有，同 M1。 | **有**：「各一臂」沒有預先指定語料。 |
| **M5**，`:143` | **BLOCKING**：只改寫兩份測試使用的行內圖片，參照式／直接 SDK 仍可阻塞。見 R5。 | 手工兩個輸入，沒有封閉圖片語法或等待來源。 | **沒有**；只有「若紅」，缺未做與未完成。 | **有**：改寫邊界、超時後處置尚未固定；6,000 ms 本身是機械條件。 |
| **M6**，`:144` | **BLOCKING**：後備只縮頁面，上游引擎仍接受較大輸入；M6 單次成功無法辨識。見 R6。正確的恰好 65,536-byte 臂應抓到 `>=`／`>` 邊界錯誤。 | 單一逐實例測量；生成規則與實際 byte 長度尚未固定。 | **沒有**；16 KiB 仍失敗、拒絕或未回覆均未定。 | 10 秒分支是機械的；語料與第二次失敗處置仍留白。 |
| **M7**，`:145` | **SHOULD**：保留字面符號但額外套格式；標記數及文字仍可綠。應比較原生純文字結構，見 R10。 | 固定控制案例 × 瀏覽器的逐實例性質。 | 有：v21 不出貨。 | 無；但需要固定結構比較。 |
| **M8**，`:146` | **SHOULD**：worker 不檢查宣告，SDK 自己擋住，所以現有兩項仍綠。應由直接 worker 負向臂捕捉，見 R9。 | 手工 v20／假 manifest；應由宣告狀態與各層入口生成。 | 有，但 generation 限定需改為最終候選。 | 無。 |
| **C1**，`:147` | **SHOULD**：窗長改變卻保留字串，三個 builder 案仍綠，見 R12。直接完全移除檢查則應被 v19 案抓到。 | 三個指定 artifact 案的逐實例性質；不是行為版本的普查。 | 有：不宣告 C、工具照舊；須與 I1 對帳。 | 無。 |
| **I1**，`:148` | **SHOULD**：changed-leaf 忽略 OLD，現有兩個紅案仍可過；見 R11。單純新增未宣告 manifest leaf，既有 X1 應紅。 | X1／M1-1 為工具封閉；舊 profile 雜湊清單是指定樣本，不等於所有凍結 profile。 | 有：不綁定。後備出貨差異未固定。 | BASE、命令及允許差異的後備版本仍待指定。 |
| **K**，`:149` | **SHOULD**：D／M 跑完後改新增入口，再跑既有回歸鏈，缺少新證據身分規則時可能仍宣稱本批成立，見 R11。缺 `DONE` 等簡單缺漏由 J-a.2 捕捉。 | 引用的 J-a.2 對 chain 輸出是工具封閉；新增 D／M 尚未納入可查核的最終產物對帳。 | 有：未計數候選、出貨名義停 0.2.24。 | 既有 J-a.2 與 §17.4 數值規則不需新裁量；新證據如何接上尚未定。 |

## 其餘來源查核

- **read in source**：按鍵路徑的選擇合理。`probe_engine.cpp:5674` 的全選先例與 `:5709` 的非變更記帳，支持不走 UNO 變更包裝；它不提供 FIFO 保證。
- **read in source／stated in a doc**：collapsed-only 的理由成立。原生 README `142-ctrl-home-end/README.md:241` 記錄選取回呼先到；`probe_engine.cpp:2191` 會立刻用當時快取完成。`e2-editor-app.js:2973`、`:3057` 的確是既有點擊後移動路徑；不能由此擴稱所有表格／頁首範圍等同原生。
- **read in source**：兩個新動作屬於 `BOUNDARY_CAPABLE_MOVES` 是正確設計，但仍需要 R7 的斷言證明實作沒有漏接。
- **read in source**：保留 v4 builder、另建後繼 builder 符合 finding 042 的依賴問題；`Makefile:1588` 確實讓舊 builder 成為 manifest 前置檔。import 不應修改其全域清單，也不應呼叫會重建舊身分的流程。
- **stated in a doc／read in source**：殼層 generation、worker pin、E1-C、host packaging、merge `BINDING` 並未全被忘記：草案 §4.4、§7 已提及；`build_e2_c_shell_bundle.py:767` 也涵蓋 SDK 與 v2 shell。缺的是新型別／測試範圍、後備方案及最終證據的明確對帳。
- **inferred**：還應命名按住新移動鍵的佇列尾端、C 期間交錯刪除、Undo metadata 碰撞，以及頁面圖片降級未約束直接 SDK 的限制；目前不能將它們一併藏在「沿用既有路徑」之下。

## 十行摘要

1. BLOCKING：產品沒有編入所引用的 unipoll 分支，排序前提必須更正。
2. BLOCKING：D1 混入不支援操作，可達性排除也尚未成立。
3. BLOCKING：M1 包含超限 M14b 與不同 MIME 的控制語料。
4. BLOCKING：Markdown 派送後未確認結果的記帳與復原語意尚未定義。
5. BLOCKING：M5 的圖片改寫、直接 SDK 範圍及未完成預設未封閉。
6. BLOCKING：M6 降限會影響引擎身分、M1 母數與 I1 差異。
7. SHOULD：D 判準須驗完成回覆、revision 分類及 session 非變更記帳。
8. SHOULD：加入 C 期間移動後刪除，以及按住新移動鍵的序列。
9. SHOULD：補跨層負向閘控、型別、ODT 正規化與結構還原檢查。
10. 保留四支既有 C 工具的停止規則；全程未寫檔、未建置、未開瀏覽器。
# Findings — 上游問題紀錄

發現當下記完整，之後統一回報。

相關：[`../QA-GUIDE.md`](../QA-GUIDE.md)（怎麼參與 QA）、[`../wasm-lite/README.md`](../wasm-lite/README.md)（建置規劃）

---

## 清單

| # | 標題 | 狀態 | 嚴重度 | 上游？ | tdf# |
|---|---|---|---|---|---|
| [001](001-wasm-configmgrwriter-crash.md) | WASM `--disable-symbols` 破壞 C++ 例外處理，啟動即崩潰 | **可送出** | 阻斷 | 是 | — |
| [002](002-vcldemo-missing-fs-image.md) | qt_vcldemo.html 沒連結 fs image，README 卻要人跑它 | 可送出 | 一般 | 是 | — |
| [003](003-unpackedtarball-dir-race.md) | UnpackedTarball.mk 的 .version 缺 .dir 相依，-j 下 race | 可送出 | 一般 | 是 | — |
| [004](004-emscripten-install-partial-symbols.md) | Emscripten 部分符號建置未產生 soffice `.dwp`，封裝失敗 | 待驗證 | 一般 | 未確認 | — |
| [005](005-qt5-wasm-no-input-context.md) | Qt5 WASM 無 input context，CJK 輸入完全不可行 | 可送出 | 嚴重 | 是 | — |
| [006](006-qt6-wasm-stale-eventlistener-export.md) | Qt 6.10 WASM/JSPI 仍匯出已移除的 EventListener 符號 | 待驗證（連結通過） | 阻斷 | 未確認 | — |
| [007](007-qt6-wasm-pointerenter-null-dom-node.md) | Qt 6.10 WASM/JSPI 延遲 pointer-enter 以 null DOM 節點退出 | 本地修補已驗證 | 阻斷 | 未確認 | — |
| [008](008-qt6-wasm-inputcontext-invalid-emval-value.md) | Qt 6.10 WASM input context 跨 pthread 使用 DOM emval handle | 本地修補已驗證 | 阻斷 | 未確認 | — |
| [009](009-qt6-wasm-duplicate-english-key-input.md) | Qt6-WASM Writer 英文按鍵重複輸入 | 待驗證（首度觀察） | 嚴重 | 未確認 | — |
| [010](010-probe-export-list-requires-unoembind.md) | Core Emscripten exports 清單與「不連 unoembind」的外部 probe 規格衝突 | 已解決 | 阻斷 | 否（專案規格） | — |
| [011](011-sdk-worker-search-not-found-json-parse.md) | Document SDK Worker 將 search-not-found 純文字 payload 當 JSON 解析 | 已修（跨瀏覽器／R1～R5 回歸） | 嚴重 | 否（專案 Worker） | — |
| [012](012-r6-styled-document-close-timeout.md) | writer-review 對t2 image frame直接paragraph wrapper的open→close不回應 | **SDK bounded Worker recovery已修；core teardown根因保留** | 阻斷 | 未確認 | — |
| [013](013-sdk-open-name-rejects-docx-before-content-detection.md) | Document SDK 在 content detection 前拒絕 `.docx` 名稱，DOCX import 邊界與 bytes 能力不一致 | 已確認 | 嚴重 | 否（專案 SDK） | — |
| [014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) | ~~Firefox長壽程序反覆建立大型WASM Worker後init耗盡~~ | **已全數撤回（2026-08-08）：三組觀察沒有一組是Firefox缺陷。**R7-D `s2-fresh`/`s3`與R7-C→[023](023-sdk-init-wedges-at-fixed-session-depth.md)的unread `serve.py` pipe；R8-D 900秒→[025](025-webdriver-script-injection-never-ran-on-firefox.md)的注入腳本從未執行。重跑全過：R7-D正式九輪`summary.pass: true`、R7-C單頁19 Worker 19/19（原本要切7批）、R8-D compatibility 28/28＋soak 30.07分鐘。**「每頁Worker generation上限為3」前提被兩種工作量各自推翻**（單頁50代、單頁19 Worker）；引用處已就地標註，**條文一律未改**（放寬屬產品決定）。2026-08-08第二次：`dom.workers.maxPerDomain` 判別（正控制`=4`第1代即死、判別`=64`仍50/50）證明**頁內`dispose()`即時歸還worker名額**、50代之上沒有名額牆。2026-08-08第三次（對抗性複核，結論未被推翻）：成本模型補上「pipe起始存量」這個未申報參數並用`monotonicSeconds`重建invocation邊界，單頁那列（牆34）改判為初始條件不同；記憶體改正為約**1.9～2.6 MB／代**、外推**第207～281代**（原1.4／374出自錯分母），且兩輪四道門檻全過（不是靠`continuousThreeBlockGrowth`放行）、`maxPerDomain=64`末塊呈plateau，線性外推降級為推論；引用者由「八份規格」更正為**15個規格檔（11份帶現行條文）＋7個程式碼站點＋1份凍結矩陣**。2026-08-08第四次（待驗證9結案）：**位元組帳三列全部閉合**——獨立量到`s1`×3＋`s2-reuse`的serve.log前綴**10,033 B**（模型要求9,783 B，差250 B≈2.5行log），代回去牆落在cycle 34的85%處、實測牆就是34，**樣本外命中且模型不再有自由參數**；併同更正「12 s＝`time.sleep(12)`」（該sleep不在此路徑），改以實測session churn常數**12.8/12.5/12.4 s**認定invocation邊界 | ~~嚴重~~→**已撤回（我方harness）** | ~~是~~→**否** | — |
| [015](015-firefox-fetch-content-length-mismatch.md) | Firefox對部分Content-Length不符回應仍可能resolve fetch | **已確認／R8-A/B完整性契約已驗證** | 一般 | 否（browser相容性） | — |
| [016](016-lok-forward-delete-completion-gap.md) | forward delete已改文件，但SDK未建立可歸屬completion | **已修（selection barrier）；邊界拒絕後需fresh Worker** | 已解除阻斷 | **否** | — |
| [017](017-lok-collapsed-selection-readback.md) | selection reset後文字readback回unsupported UTF-16 flavor，SDK無法表示空selection | **已修（SDK側）／實測通過，不再阻斷** | 阻斷 | 未確認 | — |
| [018](018-lok-line-navigation-completion-nondeterministic.md) | Writer line navigation callback completion不具重複執行確定性 | **已確認；2026-08-06 已歸因**：移動沒壞，壞的是 visible-cursor completion 訊號需要活迴圈；Shift 模式兩 profile 皆 36/36 | 一般 | 未確認 | — |
| [019](019-e1a-paragraph-style-mapped-to-ui-alias.md) | E1-A段落樣式映射到UI別名，該名稱不是可派送命令 | **已確認／E2-A已定位修法** | 嚴重 | 否（專案SDK映射） | — |
| [020](020-lok-list-command-result-contradicts-document.md) | LOK清單命令的command result與文件實際結果矛盾 | **已確認（原生26.8＋WASM兩瀏覽器）／待搜重複單** | 嚴重 | 候選為是 | — |
| [021](021-wasm-format-state-not-refreshed-by-caret-movement.md) | WASM段落格式state不隨caret移動更新，barrier前置條件會讀到別段的值 | **已歸因到底：缺口在PEI語意；產品路線C＝不讀前置狀態，上游暫緩** | 嚴重 | **否** | — |
| [022](022-e1-release-set-bold-false-noop.md) | 已出貨的e1-editor-v1回報假`documented-state-noop`，按粗體／斜體／取消粗體都可能什麼都沒發生 | **已修並重新凍結**（WASM `94b38437…`→`97e605ee…`；兩瀏覽器驗證關閉、E1＋R6～R8全回歸） | 嚴重 | **否** | — |
| [023](023-sdk-init-wedges-at-fixed-session-depth.md) | 同一瀏覽器session反覆開檔到固定深度後SDK init永久卡住（Firefox 22／26、Chrome 30／34，逐次重現） | **已歸因（第二次）、已修**：機制是探針基礎設施的pipe阻塞（runner從不讀serve.py的stderr pipe，64 KiB塞滿後HTTP handler卡在`anon_pipe_write`）；`/proc`現場鐵證＋位元組對帳＋修復後牆全消失（full 45/45、30/30；minimal 120/120）；產品不受影響。**2026-08-08：善後那條「r7 longevity歷史無需作廢」已撤回**——它也是[014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)的成因（`s2-fresh` 50/50、`s3` 20/20重跑全過），影響範圍比原估大 | ~~高~~→harness（但作廢的歷史結論更多） | **否（我方harness）** | — |
| [024](024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md) | Firefox對導覽拆除的pthread池worker惰性回收：連續導覽~8次（1 GiB引擎、記憶體預算）或~65次（worker名額預算，`dom.workers.maxPerDomain`）後init靜默卡死 | **已確認、Nightly 155.0a1已修**（153仍中）：pref=64把牆從65移到9（歸因閉合）；nightly 1343/624次無牆；自包含重現`findings/repro/024-firefox-worker-reclaim/`；Chrome不受影響；產品對策＝pagehide明確dispose()。2026-08-08 **[014](014-firefox-long-lived-wasm-worker-init-exhaustion.md)的歸屬已撤回**（那是023的pipe），本finding自身證據不受影響 | 一般 | **是（FF 153；155已修）** | 未送（僅剩uplift價值，待使用者） |
| [025](025-webdriver-script-injection-never-ran-on-firefox.md) | 注入腳本在Firefox上從未執行：`evaluate()`包成`return`＋換行觸發ASI；WebDriver sandbox又不是頁面global | **已確認、已修**（我方harness）：三個缺陷疊套——(1)`wait_value`的`except: pass`讓「腳本沒跑」與「頁面沒好」都變成`timed out: None`；(2)ASI使整份注入腳本成死碼（實測`return⏎(IIFE)`→null且side effect未發生，Chrome走CDP無此問題）；(3)sandbox使`globalThis`寫入消失、且產品的`globalThis.fetch.bind(globalThis)`拋`'fetch' called on an object that does not implement interface Window`。修法＝`.strip()`＋新增`run_in_page()`。**R8-D Firefox compatibility 28/28通過**（原900秒零結果）。R8-C既有Firefox結果**不受影響**（走`webdriver-tabs`分支），而那條Firefox專用`webdriver-tabs`分支**確定**是當年為繞過本bug而寫的：保留的失敗嘗試`firefox-t0-full-iframe-client-timeout`死法為`runnerElapsedMs: 900531`，修好後強制Firefox走同一條共用路徑則**4,929 ms通過**（差182倍）。**該分支已退休（使用者指示）**：刪掉79行Firefox專用分支與臨時開關後重跑R8-C Firefox全套，t0 46/46、t1 37/37通過，multi-client走共用路徑5,192 ms。兩瀏覽器現在跑同一段程式碼 | 對產品零影響；對歷史結論破壞力大 | **否（我方harness）** | — |
| [026](026-generation-cap-means-two-different-things.md) | 「每頁Worker generation上限」在規格與產品裡是兩個量：規格承諾**每頁引擎實例化次數**，產品唯一實作的是**每個`EditorSession`的崩潰回復次數**（`maxWorkerGenerations ?? 3`）；**每頁那個產品端零實作** | 已確認（程式碼＋E1-C既有48 case證據＋新量測三方一致）：E1-C觀察到的最大generation是**2**、只出現在crash/boundary回復，`lifecycle`一頁一代，**連它自己的3都沒碰到**。連帶推翻「上限3＝第四份文件被踢出去」的說法（那是我對使用者的錯誤說明），因此「放寬到16讓使用者不被踢」不成立——16的實際意思是「一個session可連續崩潰15次」。另量到產品artifact（`835b453d…`）在回復軸上**兩瀏覽器各16/16**且第17次仍`WORKER_GENERATION_LIMIT`＋`requiresPageReload`。另發現`run_r8_production.py:634,656`與`:640`＋`validate_r8_d.py:87`是**兩個恆真的假閘門**（歷史soak summary一律`gen 4/maxPerPage 3`，**連`pass:false`那幾輪也是**）。**2026-08-08收尾（使用者決定）：A維持3、B承諾撤除**——11份帶現行條文的規格就地修訂＋補修訂紀錄，產品程式一行未改故不重發判定；兩個假閘門改成頁面自數的真量測（`window.__r8_worker_generations`），讀數**由1變3**才收下（那兩次1分別是WebDriver sandbox與`dist/`未重建） | 一般偏高 | 否（我方） | — |
| [027](027-r8d-verdict-silently-outlived-its-release.md) | R8-D的判定在release內容變更後靜靜過期四天；`make test-r8-d-static`會重鑄release id | 已確認（mtime＋確定性重建＋`make -n`三方一致）：R8 bundle含`profiles/writer-review-r6/sdk-worker.js`，該檔**08-07 11:19**被改，而compatibility證據是**08-04 15:38**錄的、綁在已不存在的`writer-review-5fa3ca0d…`。`activeCachedRelease`閘門沒壞，只是**要等有人跑make重建release set才有機會失敗**——判定新鮮度取決於「最近有沒有跑過make」而非「證據是否仍描述現況」。另兩個同族問題：(1)名為static的目標會改動建置產物；(2)**證據根分裂**——validator只讀`sdk-r8`，但023/025修好後的重跑與兩輪30分鐘soak都寫在`sdk-r8-post-023-fix`，**是真量測卻從未餵進判定**。已以單一campaign（中間不呼叫`make`）重跑四個相位進`sdk-r8`：**判定回到`PARTIAL_GO_LOCAL_DELIVERY`**，compatibility兩瀏覽器各28/28（6批次、12 worker、每頁最高3，與08-04歷史逐項相同），soak各30分鐘、`workerGenerations`實測**3**；**Firefox這次是自己過的、不再依賴`acceptedForPartialGo` fallback**，formal gap由6條降為3條（只剩T2／真quota／candidate adoption）。campaign後再跑一次`make test-r8-d-static`，release id逐字不變且判定仍pass。**2026-08-08補正：修復只完成一半**——R8-D吃六個證據家族，campaign只重跑了四個；`delivery`（R8-B，08-04 13:49）與`service-worker`（R8-C，08-04 15:56）仍綁`5fa3ca0d…`，而那些release目錄早被builder刪掉，bundle必要位元組差12,818 B。`safetyChecks.r8b`／`r8c`只看`pass`欄位、**那一側根本沒有release閘門**。已加`release_binding()`（`7e66554`）：六個家族全查，比對對象是**當下從`dist/`重算**的身分（release id本身就是bundle內容雜湊），沒記release者一律fail；**判定因此由`PARTIAL_GO_LOCAL_DELIVERY`變`STOP`**（bound 4、superseded 2），要救回只能重跑R8-B／R8-C，不能改門檻`sdk-r8` | 一般偏高 | 否（我方harness） | — |
| [028](028-cancel-during-manifest-body-read-reported-as-corrupt-manifest.md) | 取消若落在 manifest body 讀取階段，會被回報成`RELEASE_MANIFEST_INVALID`並要求 fallback | **已修（08-10）**：`delivery/verified-loader.js` 的 catch 不對稱——fetch 那層有 abort 檢查、body 讀取那層沒有，於是使用者取消被標成 manifest 損毀，`ERROR_POLICY` 對應到 `retryable:false`＋`select-known-good`（**會導致無謂的版本回退**）。08-04 同一 case 是正確的 `DELIVERY_ABORTED`，差別只在取消落點。**08-10 全檔審計後範圍加倍**：不對稱是**兩處**——`fetchJson` 的 `json()`（服務 manifest 與 compression-index 兩個呼叫點）與 `fetchArtifact` 的 `arrayBuffer()`，後者誤標成 `ARTIFACT_SIZE_MISMATCH`＝**`reject-release`**（比 `select-known-good` 更重）且**至今從未被觀測到**。既有 abort 測試只在 fetch promise 上 reject，**測試盲點正好落在缺陷所在**，因此兩個 catch 兩側都無覆蓋。修法為兩處各補 fetch 層已在用的判斷（未動 `ERROR_POLICY`，不是改契約），附三站點回歸測試＋正控制，並以突變（改成 `if (true)`）證明正控制能失敗。重跑 R8-B／R8-C 兩瀏覽器，release id 頭尾逐字不變：**R8-B `STOP`→`PARTIAL_GO`、R8-D `STOP`→`PARTIAL_GO_LOCAL_DELIVERY`**，未動任何門檻。**但瀏覽器重跑不證明 body 路徑**——修好後取消落在 fetch 或 body 輸出完全相同，證明來自 node 測試 | 一般偏高 | 否（我方產品） | — |
| [029](029-r8d-summary-transcribed-its-subject-identity-instead-of-measuring-it.md) | R8-D 判定摘要把「驗證對象的身分」抄成常數而非量測 | **已修（08-10）**：`validate_r8_d.py:18-20` 的 `CORE_COMMIT`／`LOADER_SHA256`／`WASM_SHA256` **全檔只有一個用途**——直接寫進判定摘要（`:424-425`），從未與任何東西比對。同一個 dict 相鄰三行、兩種認識論地位：`matrixSha256` 是算出來的，這三個是字面值，輸出裡沒有東西能讓讀者分辨。**只被寫出、從不被比對的常數不可能失敗，因此不帶資訊**（「連閘門都沒有的宣稱」）。失效形狀與 027 相同——判定的自我描述活得比它描述的東西久，且 `release_binding()` 守不到這三欄。發現當下數值**全部正確**（潛伏缺陷，非正在發生的錯報），但相符靠人工維護的巧合而非量測：同一個 core commit 在 repo 有 **15 份獨立寫死的副本、無交叉比對**，`dist/profiles/writer-review-r6/sdk-manifest.json` 只是 `cp` 手工來源檔。**修正 027 待處理第 3 項的描述**：那些欄位**有**被 release id 一起雜湊，所以缺口不是「宣稱改了 id 不變」，而是「宣稱從未被對照」。修法：新增 `shipped_identity()` 當下重算，原常數降級為 `EXPECTED_*` 期待值，加 `safetyChecks["shippedIdentity"]`——不符現在會 STOP。突變控制：改一個期待值後 `decision` 變 STOP、**逐欄區分**（只該欄 false）、摘要印實測值而非期待值。**三個待驗證同日結案**：逐檔審計另外 14 份副本，**沒有第二個「只寫出不比對」**（六處是比對實測 git HEAD 的真閘門，`validate_e1_c.py` 反而是做對的示範——artifact 雜湊實算後以 observed／expected 比對）；`capabilities` 查出**先前沒有任何閘門**（`validate_r7_preflight.EXPECTED_MANIFEST` 只涵蓋 `coreCommit`／`sdkVersion`），改以新增 `faithful_transcription()` 比對「抄本與它抄的來源檔」而非再加第 16 份寫死副本——這也堵住另一條 027 形狀的路（validator 直接讀磁碟上的 release manifest 而不重建，可能早於 profile manifest 的變更）；兩次針對不同欄位的突變各自證明能失敗（第一次沒真正考驗到 `capabilities`，因兩 profile 剛好同為 14 項，故補第二次）。**收斂 15 份副本改判為不做**：那是六個 release 各自的凍結基線，收斂會破壞凍結的意義。**殘留一已清（同日）**：E1 兩份矩陣的 `.baseline.coreCommit` 現在有人比對——`validate_e1_c` 加 `matrixCommitPass` 閘門，並在 `tests/test_e1_c.py` 加交叉檢查（`Makefile:1319` 讓它每次都跑，**這才是常態生效的那一個**；validator 那側只在 `--write-preflight` 時執行，既存 preflight 檔早於本改動，未為補一個欄位而重寫已凍結證據，改以乾跑確認今天重新擷取會通過）。比對**限制在同一 release 內**，理由同上：凍結基線本就允許各自不同。突變（`CORE_BASELINE_HEAD`→`0000dead…`）使測試 FAILED；還原後 15 測試全過、E1-C 仍 `E1_GO_ODT_EDITOR`／48 綁定。E2 那份未動（E2 無同 release 常數，要閘住得先寫明「E2 繼承 E1 基線」的契約，而 E2 尚未啟動）；corpus 只驗有無那項亦未動 | 中 | 否（我方 harness） | — |
| [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md) | 封閉清單動作派送的是 toggle 形式，第二次按下會反轉；而合法的 no-op 不會廣播任何狀態 | **已確認（原生實測＋原始碼對照）／缺陷一已修、缺陷二待產品決定**：2026-08-06 的產品路線 **C（不讀前置狀態）**靠一個從未量測的前提——`probe_engine.cpp:2688` 註解寫「dispatching unconditionally is idempotent for these commands」。原生 26.8 連按三次的實測**否證**它，並帶出第二個問題。**（一）不帶參數的 `.uno:DefaultBullet`／`.uno:DefaultNumbering` 是 toggle**：core 取 `!SelectionHasBullet()`，第二次按 `set-list-unordered` 會把段落踢出清單；`svx/sdi/svx.sdi:2251`／`:4985` 宣告 `SfxBoolItem On FN_PARAM_1`，`sw/.../txtnum.cxx:81-108` 有參數才是 explicit mode。**帶 `On=true` 則四案例全為 setter**，含有序→無序的跨種類轉換，所以三態封閉列舉做得到。**與 [019](019-e1a-paragraph-style-mapped-to-ui-alias.md) 同形狀**（派送形式錯，不是能力不存在），修法也相同。**先前是潛伏**：路線 B 的 fail-closed 只在「狀態已知且不等於目標」時派送，恰好是 toggle 會做對的情況——路線 C 一落地遮罩就消失。已改派參數化形式並重建 `e2-format-discovery`（`abf3598f…`）；隔離已驗（**改用前置處理後的翻譯單元比對**——原本用的目的檔逐位元比對有一半機率通過，見 [032](032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md)），三個凍結 artifact 未受影響；`tests/test_e2_profile.py` 加三項釘住，突變（拿掉 `On`）證明會失敗。**（二）值沒變就沒有 STATE_CHANGED**：已在目標狀態時再按一次，文件正確、command result 照常抵達且帶正確 `commandName`，但**九個案例的第二、三次全部零 watched payload**。E2-A 的 completion 需要「歸屬＋state 後置條件」同時成立，(b) 永遠不會到，於是逾時成 `MUTATION_OUTCOME_UNKNOWN`——**是低報不是誤報**，但 SPEC E2-A 第 8 節把「no-op 與遺失不可區分」列為 STOP，**所以只修（一）不會讓 A3 可判定**。四條出路（接受低報／路線 A 自行 pump／後置條件改讀文件／只用 command result）已列。**使用者 2026-08-11 選定第三條：後置條件改讀文件。**動手前先量可行性（同一條 A2 紀律）：`getCommandValues` 以讀原始碼排除，剩下的 selection transferable **實測可用**——`text/html` 下 heading→`<h1>`、無序→`<ul><li>`、有序→`<ol><li>`、離開清單→`<p>`，**五個 action 全可分、跟著 mutation 走、且與語系無關**（分辨用 HTML 結構不是 UI 名稱，順帶解掉 [031](031-styleapply-postcondition-compares-a-localized-ui-name.md) 在段落樣式那兩個動作的曝險）。**三項代價也是量出來的**：(1) 游標塌陷時讀不到（selType 0、0 bytes），必須先選起整段再讀、讀完還原，**而還原本身要被驗證**；(2) `Text body` 與預設樣式都是 `<p>`，分得出「是不是 heading」但分不出 Text body 與 Standard，`set-paragraph-body` 的宣稱因此變弱（兩態承諾剛好夠用，但是縮限，判定要明列）；(3) 這串 HTML 是序列化器輸出不是有文件的契約，整串比對＝把序列化器釘成 ABI，跨版本可能變（未驗證）。判定一律讀存檔 ODT，不讀 callback（[020](020-lok-list-command-result-contradicts-document.md) 是理由）。本輪自身缺陷一項：第一版分析器拿自動樣式的生成名稱（P1/L1 對 P2/L2）比對，誤報未被碰過的清單項變了；已改為解析到具名 parent，**沒有重跑量測，只重跑判讀** | 嚴重 | 否（我方派送形式；缺陷二是 core 既有語意，問題在我方判定設計） | — |
| [031](031-styleapply-postcondition-compares-a-localized-ui-name.md) | 段落樣式的後置條件比對的是**在地化 UI 名稱**，我方 build 已內含 zh-TW 譯文 | **已確認（原始碼追到底＋既有證據佐證＋譯文檔實查）／端到端未在非英文 UI 實測**：barrier 以整串比對 `.uno:StyleApply=Heading 1`／`=Body Text`，而那兩串是 **UI 顯示名稱**。`SID_STYLE_APPLY` 的狀態放 `UIName` 且**不放 ProgName**（`sw/.../docst.cxx:140,145,166`；對照 `SID_STYLE_FAMILY2`「兩個都放」），`StyleApplyPayload` 直接輸出它（`unoctitm.cxx:969-975`）；UIName 陣列**以 UI 語系為 key、由 `SwResId()` 建**（`DocumentStylePoolManager.cxx:2665-2676`），ProgName 陣列則寫死不翻譯（`SwStyleNameMapper.cxx:496-500`）。既有 A2 證據已佐證：**送出與回報不是同一個字串**（送 `Text body`→回 `Body Text`；送 `Standard`→回 `Default Paragraph Style`），所以回報值來自 core 的名稱表，不是輸入回音。**建置樹的 `instdir` 有 `zh_TW/LC_MESSAGES/sw.mo`**（5,354 筆；`Heading 1`→「標題 1」、`Body Text`→「內文」），**但出貨的 WASM 檔案系統映像沒有（本輪自我更正）**：`soffice.data.js.metadata` 的 1,358 個檔裡 `.mo` 是 **0**、`/resource/` 下只有一個字型檔，却有三個 zh-TW registry langpack XCD——**zh-TW 選得到但沒有東西可選，今天把 UI 設成 zh-TW 介面會是英文**。zh-TW UI 之下兩個段落樣式動作的 barrier 會逾時成 `MUTATION_OUTCOME_UNKNOWN`，**而文件其實已經改對了**。**派送側安全**（`Style` 參數送的是 ProgName）。**今天是潛伏的**：全樹沒有任何路徑選非英文 UI。**實測跑了，是假陰性，原因已查明**：新增隔離 profile `e2-locale-attribution`（＝scheduler-attribution 只改一件事，engine 走 `documentLoadWithOptions(…, "Language=zh-TW")`，以編譯期常數隔離、JS 選不了）。Chrome 兩臂比對：回報字串**完全沒變**（仍 `Heading 1`／`Body Text`）、五個 action 全 `verified-format-state`、ODT postcondition 5/5。**但那不是反證**——沒有譯文的 build 上這條路不可能印出不同值，我在上一版預測原生會有這個假陰性，然後在 WASM 上踩了同一個坑（看 `instdir` 而非出貨映像）。**因此最後一環仍是推論**，本輪也**沒有正控制**（無譯文時問不出「選項是否生效」）。唯一新增的正面觀察：帶 `Language=` 不會弄壞任何東西，路是通的。真要量到得先解決打包：把 `resource/` 打進 FS 映像（做 zh-TW 產品本來就得做，但動到凍結的 wasm-lite），或執行期把 `sw.mo` 寫進 MEMFS（便宜得多，需新增 discovery-only 注入通道，未實作）。修法四個候選（改比對 ODT 的 `Heading_20_1`／填 `StyleNameIdentifier`（要改 core）／依第 8 節縮到只承諾清單／把譯文編進來（不建議））**未選**。清單三個動作不受影響（payload 是布林值）。答完了 SPEC E2-A 2.5 節掛著的待驗證項 | 嚴重（潛伏） | 否（core 既有語意；問題在我方拿它當後置條件） | — |
| [032](032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md) | 用目的檔逐位元比對驗證 `#ifdef` 隔離是擲硬幣，不是檢查 | **已確認（同源同旗標 8 次重編：兩種輸出各 4 次，固定差 37 bytes、固定在 offset 23963，長度相同）**：差異是 WASM 指令位元組，不是字串／路徑／時間戳，像是最佳化階段在兩個等價分支形式間跳（**未定位到哪個 pass**）。那組旗標就是 `Makefile:420-422` 給 `$(E1_B_BUILD)/%.o` 的旗標，不是自拼的組合。**我本輪用這個方法下過三次「隔離乾淨」保證，全部要降級**（030 的派送修正、031 的 locale profile、readback barrier——第三次擲到另一面才因此發現）；SPEC E2-A 10.6 節更早的同方法保證同樣打折。**三次的結論本身仍成立**，改以**前置處理後的翻譯單元比對**（`-E -P`）重新驗證：E1-B 組態下 4,355,327 bytes 逐位元相同——那才是直接證明隔離、且不受 codegen 不確定性影響的檢查。**未驗證且不要據本單推論**：連結後的 profile 雜湊會不會也跳（沒量）、其他翻譯單元是否相同、是哪個 pass、是否為上游缺陷。紀律：**一個有一半機率通過的檢查比沒有檢查更糟**，它會產生「已驗證」的紀錄；最便宜的鑑別法是對已知不變的輸入跑兩次 | 一般偏高 | **未確認**（未定位、未回報） | — |
| [033](033-readback-barrier-read-wherever-the-caret-went.md) | readback barrier 讀的是「游標現在在哪」，不是「命令改了哪一段」 | **已確認（A5 實測）／已修並驗證**：路線 C 的 barrier 派送後選起游標所在段落再讀 `text/html` 判後置條件，但游標可能在派送與讀取之間被移走。A5 `state-crosstalk` 實測得 `EDITOR_FORMAT_POSTCONDITION_FAILED`——**fail-closed 方向對，但那是運氣**：若游標移到一段本來就已是目標狀態的段落，barrier 會回報成功，而實際被改的是另一段，**沒有任何訊號**。修法＝**選段落來讀之前先把游標移回派送當時記錄的位置**（該位置在派送前擷取，因為派送本身也可能移動游標）。修後同案例變 `verified-format-readback`，存檔 ODT 證實 heading 落在被派送的那一段。**殘留（推論，未實測）**：還原用文件座標，而派送會改變該段高度／縮排，極端重排仍可能落到別段；要真正關掉需要「段落身分」而非座標的定位，現有 LOK 介面沒有。**這條路 A3／A4 共 555 次派送一次也沒碰到**——這就是 A5 存在的理由 | 嚴重 | 否（我方 barrier 設計） | — |

**狀態**：`待驗證` → `可送出` → `已回報` → `已修` ／ `撤銷`

---

## 為什麼要這樣記

「先做完再一起回報」有兩個必然的損耗，這份結構就是在擋它們：

1. **細節會蒸發。** 版本號、確切的錯誤訊息、你當時排除過哪些可能 —— 三天後就模糊了，而這些正是 triager 判斷要不要收單的依據。所以**證據存檔案，不存腦袋**。
2. **會忘記自己還沒證明什麼。** 每張單都有「還缺什麼才能送」的核取清單。這是最重要的一段 —— 沒它的話很容易把還沒驗證的猜測當成結論送出去，被退一次之後，你之後的回報都會被當成低品質來源。

---

## 實驗型專案的留痕層級

不是每個觀察都是上游 bug，但值得影響後續判斷的資訊都不能只留在 console、聊天或記憶裡。依下表
選擇紀錄位置：

| 情況 | 紀錄位置 | 最低內容 |
|---|---|---|
| 當輪假設、嘗試、否證、取捨或已知限制 | 對應 `DEVLOG-<日期>-*.md` | 做了什麼、預期、實際、因此決定什麼 |
| 測試／量測原始輸出 | `findings/evidence/<finding 或 sdk-rN>/` | 環境、artifact hash、輸入、原始結果 |
| 可重現且會影響架構、SDK 邊界、相容性或排程的發現／阻礙 | 編號 finding | 最小重現、證據、事實／推測、影響、下一步 |
| 可送 LibreOffice／工具鏈上游的問題 | 編號 finding + Bugzilla 欄位 | 另補上游預設組態、重複單搜尋與 component |

編號 finding 可以是上游問題，也可以是「我方規格或架構假設被否證」。`是否上游` 欄位必須如實標記，
不能因為不準備送 Bugzilla 就不記錄。

### 何時應立即停下來寫

- 同一失敗已重現兩次，下一次嘗試沒有新增可區分原因的證據。
- 結果迫使我們改 API、協定、資料模型、建置 profile 或 Go／No-Go 條件。
- 不同瀏覽器、artifact 或 build 得到互相矛盾的結果。
- workaround 會擴大公開 surface、修改 LibreOffice core 或降低資料完整性保證。
- 一個「暫時限制」可能被後續工作誤認為已完成能力。

先保存當下環境與原始輸出，再整理文字。每則結論分成：

- **已觀察**：由原始輸出、hash、程式碼或可重現步驟直接支持。
- **推論**：目前最合理的解釋，但尚缺決定性實驗。
- **待驗證**：下一個能區分推論的最小測試。

里程碑結束時，machine summary 只負責回答閘門；DEVLOG／finding 必須保留失敗路徑與限制，不能用最後
一次 `pass: true` 覆蓋實驗歷程。

---

## 怎麼新增一張

```bash
cd findings
cp TEMPLATE.md 004-短描述.md
mkdir -p evidence/004
./env-snapshot.sh > evidence/004/env.txt     # ← 一定要在發現當下跑
```

然後把 `004` 加進上面的清單。

### 存證據的時機

**發現當下就存，不要等。** 重編、換分支、改旗標之後就重現不出來了。

| 要存的東西 | 怎麼取得 |
|---|---|
| 環境 | `./env-snapshot.sh > evidence/NNN/env.txt` |
| 瀏覽器主控台 | `wasm-lite/tools/pw/probe.js`（見下） |
| 建置錯誤 | 從 `wasm-lite/logs/*.log` 節錄，含前後文 |
| 原始碼片段 | 一定要附 commit hash，行號會漂 |
| 截圖 | probe.js 會自動存 |

---

## 工具

### `env-snapshot.sh`

產生環境區塊。會自動偵測原始碼樹**有沒有本地修改** —— 這點很關鍵：帶著本地 patch 重現出來的問題，不講清楚就送出去等於浪費雙方時間。

```bash
./env-snapshot.sh                              # 預設 wasm-lite/build
BUILDDIR=../wasm-lite/build-stock ./env-snapshot.sh
```

### `wasm-lite/tools/pw/probe.js`

用 Playwright 開一個無頭 Chromium，把主控台、網路請求、page error、worker 事件全部按時間軸記下來，最後印出頁面狀態並截圖。

```bash
cd wasm-lite/tools/pw
node probe.js <URL> [秒數] [截圖路徑]
```

001 和 002 的區別就是靠它的**網路請求時序**分辨出來的（vcldemo 從頭到尾沒請求 `soffice.data`）—— 人工看 DevTools 很容易漏掉「某個請求沒發生」這種負面證據。

首次使用需要 `npm i playwright` 與 `npx playwright install chromium`（已裝好）。

---

## 送出前的檢查

不管哪一張，送出前都要能回答：

1. **在上游預設組態上重現過了嗎？** 自訂旗標上的問題，上游有正當理由不收。
2. **搜過 Bugzilla 沒有重複嗎？** 重複單是 triager 最大的時間黑洞。
3. **哪些是事實、哪些是推測？** 推測要標明是推測。猜錯不丟臉，把猜測寫成結論才會傷信用。
4. **一張單只講一件事嗎？** 三個問題塞一張會整張卡住。

送出後把 `tdf#` 回填到單子和上面的清單。

---

## Bugzilla

- 送單：<https://bugs.documentfoundation.org>
- QA 入門：<https://wiki.documentfoundation.org/QA/GetInvolved>
- bibisect（定位是哪個 commit 造成的）：<https://wiki.documentfoundation.org/QA/Bibisect>

**Version 欄位填 `26.8.0.1 rc`。** 26.8 的時程：RC1 2026-07-13、正式版 2026 年 8 月底 —— 八月中之前送的還有機會進正式版，之後只能進 26.8.1。

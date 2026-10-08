指定報告檔寫入失敗：`Read-only file system`。以下是完整報告；repository 維持乾淨，HEAD 為 `daa5de61`。

## SUMMARY

- 審核範圍：題目列出的 1–6。**BLOCKING 8、SHOULD 3、NOTE 1**。
- B1：只讀 Chrome，漏掉必須量測的 Firefox，仍回計數 `VERDICT PASS`。
- B2：兩瀏覽器使用不同 runner、binding、候選頁面，合併判讀仍 PASS。
- B3：binding 完全缺少必要雜湊，只剩無關欄位，仍 PASS。
- B4：對照組 generation 轉換、執行順序或關窗狀態不同，仍 PASS。
- B5：續打 `Z` 才發生的重繪錯誤不進入 `noToast`，仍 PASS。
- B6：X1 忽略空容器；刪除 `select-all.gestures: []` 仍 PASS，卻使 worker 放行並略過 mask 設定。
- B7：X2 允許 carrier 的其他物件改變；v19 的 `sdk_api.o` 額外不同仍不列失敗。
- B8：兩個重複的重開結尾 toast 被當成重開流程自己的兩句，仍 PASS。
- 引擎輪詢修法沒有找到具體缺陷；頁面 `break` 的部分 strips 沒有重現成持續錯誤。
- 以下是檢查的反例，沒有宣稱真實 v19 已跑過或已壞。未連結、未開瀏覽器、未改 repository。

## BLOCKING

**B1 — 缺少第二個瀏覽器，仍宣告完整計數 PASS**

位置：`wasm_sdk_probe/tools/judge_counted_m2.py:522`、`:539`、`:547`；`specs/SPEC-M3-paragraph-merge.md:1011`、`:1077`。

**判準：** X7 必須為 Chrome 與 Firefox 各三輪，並各有 M2-1b、M2-4、紅案與對照。判讀器的 exit 0 應證明這個完整母體。

**反例：** 只讀 Chrome。Firefox 可以完全沒量，甚至已知失敗；`--browsers chrome` 不會把它列為 NOT DONE。

**證明：** 在記憶體建立與既有測試同源的完整合成綠案，呼叫 `judge(root, 'e2-editor-v19', ['chrome'], False)`，得到 `0`、`VERDICT PASS`。`judge` 只迭代傳入的 browsers；`main` 原樣回傳此 code。這不是 `--uncounted`。

**建議：** 只有瀏覽器集合恰為 Chrome＋Firefox 的完整判讀可回傳計數 PASS。單瀏覽器診斷可以保留，但結束碼與 VERDICT 必須明示不是完整 X7；拒絕空集合與重複集合。

**B2 — 身分一致性沒有跨瀏覽器核對**

位置：`wasm_sdk_probe/tools/judge_counted_m2.py:409`–`:425`、`:522`–`:529`；spec `:1010`–`:1011`、`:1062`、`:1077`。

**判準：** 一次綁定好的 runner、同一份候選頁面與同一個出貨身分，完成兩瀏覽器計數量測。

**反例：** Chrome 是候選 A；Firefox 是另一個 runner、另一個 session／wasm／頁面的候選 B。每個瀏覽器自己的五份報告彼此相符，所以 `Browser.together` 全過。全域 `judge` 沒有比較兩組身分。

**證明：** 合成綠案中，只改 Firefox 五份報告：runner 換成 `another-runner`；binding 的 `sessionSha256`、`wasmSha256`、`pageSha256` 換成另一組值；bound 與 `candidate.pageSha256` 相應變更，紅案保留其 profile 值的例外。兩瀏覽器一起判讀得到 `0`、`VERDICT PASS`。

**建議：** 對所有瀏覽器／所有模式建立同一個 runner 與 binding；非紅案候選頁面也跨瀏覽器相同。紅案只豁免 `PROFILE_BOUND` 的三個值，不豁免 runner、session、頁面原始碼。

**B3 — 綁定欄位與綁定權威沒有被建立**

位置：`wasm_sdk_probe/tools/judge_counted_m2.py:366`、`:411`–`:421`；`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:979`–`:987`、`:995`–`:1004`；spec `:1011`、`:1062`、`:1116`。

**判準：** 計數執行綁 wasm、worker、v56 session、候選頁面、頁面原始碼與 eshape 的 sha256，綁定值在量測前落地。

**反例：** 每份 JSON 的 `counted` 保持 true，但 binding 與 bound 都改成 `{'irrelevant': 1}`。六個必要欄位完全不存在；reader 仍只驗兩個自述 dict 相等。它也没有將 binding 核對到量測前凍結的權威值。當前樹的 `m.BINDING` 是 None，reader 仍能批准自稱已綁定的輸入。

**證明：** 此修改施於兩瀏覽器全部十份合成報告後，`judge` 回 `0`、`VERDICT PASS`。直接呼叫 `is_counted('counted', {'irrelevant': 1}, {'irrelevant': 1})` 與紅案模式，兩者也都回 True。正常 `bound_values` 會產生六欄，但 reader 沒有檢查收到的報告確實具有這個 schema。

**建議：** 必要鍵集合由 `bound_values` 的同一個 schema 產生並核對，雜湊必須是合法 sha256；另外核對明確指定、量測前凍結的 expected binding／runner 身分。不要讓兩個來自同份報告的宣稱互相作證。合成測試可注入明示的測試權威；歷史重判可指定其封存權威。

**B4 — 配對只比最後 generation，沒有比轉換、順序與完整關窗**

位置：`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:1032`–`:1049`；`wasm_sdk_probe/tools/judge_counted_m2.py:340`–`:346`、`:458`–`:481`；spec `:744`、`:752`、`:1011`。

**判準：** 對照參數與順序相同；逐 case×輪比 generation 的轉換、關窗後的 toast 序列與文件。對照不一致時，計數結果不得引用。

**反例：**

- 儀器版 C15 是 `['1', '2']`，對照版改為 `['2', '2']`，且 `toastWindow.closed=false`。最後值仍是 2，但對照沒有相同的重開轉換，也没有關窗。
- 將對照 cases 整份反轉，破壞同順序要求，保留全部 case×round。

`pair` 的 `seen()` 不辨識這些差異；reader 對對照只驗集合與 pair 結果。

**證明：** 以上兩案各自從基準重置、獨立施作，完整兩瀏覽器 `judge` 都回 `0`、`VERDICT PASS`。另只改對照起始 generation，或只把拒絕窗口 `closed` 改為 false，也各自 PASS。文件與 toast 內容不必修改。

**建議：** 配對比較完整起訖 generation／是否前進，核對兩側關窗成功，並直接比較有序的 `(case, round)` 清單。保留控制組 `INSTRUMENT_ONLY` 的 NE，但其他可觀察條款不能一起略過。pair CLI 的固定 `return 0`（`:1097`）也應避免被誤作「零差異」結束碼。

**B5 — noToast 的觀察窗在續打 Z 之前就結束**

位置：`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:826`–`:833`、`:967`–`:969`；`wasm_sdk_probe/tools/judge_counted_m2.py:203`、`:279`；spec `:729`、`:1007`、`:1009`、`:1044`。

**判準：** M2-1／M2-1b 的鍵後文件及續打 Z 都正確，而且沒有任何 toast；M2-4 亦保留 `noToast`。

**反例：** 併段正確、鍵後存檔正確，接著 Z 正確插入並存出正確 ODT，但該次重繪失敗，顯示 `TILE_NOT_PAINTED`。`out.toasts` 早在第一個 save 與 Z 之前取完，後面不重讀，所以案例仍綠。M2-4 的最終 save 也在最後一次 toast 讀取之後。

**證明：** 以 stub 做 `run_case` 的單元層執行，使用真實 C01 原生 key／follow 文件；在 `press('Z')` 時將「重繪失敗：TILE_NOT_PAINTED」加入模擬頁面 toast。結果 actual 是該錯誤、recorded 是 `[]`、`pass=True`，八條 `merge_clauses` 全 True。

另把同樣 toast 放進合成報告的 `keyTrace`、維持 `toasts=[]`，完整 reader 仍回 `0`、`VERDICT PASS`。正常把錯誤放入 `toasts`，reader 會 FAIL；問題是漏記與不讀 trace。

**建議：** 既有 `noToast` 觀察窗應涵蓋完整 case，包括續打及最終存檔／其重繪；在結束點取得完整 toast 記錄。使用現有 drained log 對帳窗口，不可讓可見錯誤被下一個 case 的 census 丟成只有計數。窗口終點要有可驗事件與逾時預設結論。

**B6 — X1 的空容器盲點會把 withheld 動作放出去**

位置：`wasm_sdk_probe/tools/check_profile_identity.py:38`–`:46`、`:62`–`:65`；`wasm_sdk_probe/dist/profiles/e2-editor-v18/sdk-worker.js:126`–`:129`、`:1175`–`:1181`；`wasm_sdk_probe/src/probe_engine.cpp:6825`–`:6830`；spec `:1097`–`:1098`。

**判準：** v19 manifest 與 v18 相同，只有四個指名葉子可變；worker、gestures 與能力繼承，沒有附帶授權變動。

**反例：** 刪掉 `editorContract.actions.select-all.gestures`，其原值是 `[]`。`leaves([])` 不 yield 任何東西，所以無法區分「present but empty」與「absent」。

對 worker 而言差異極大：原本 `manifestAllowsAction` 為 false、會送 id 21 的零 mask；欄位消失後變 true，mask 設定 loop 直接 continue。引擎第一次 mask 呼叫把全部 entry 初始化為全許可，這一格因未交集而保留全開。

**證明：** 用記憶體檔案映射重建 `test_profile_identity` 的合成 v19，未改參照 worker／exports。基準 check 為 PASS；刪除 `select-all.gestures` 後仍是 `0`、`VERDICT PASS`，兩側都報 148 leaves，moved 仍只有四個合法葉子。加入任意空 dict 新欄位也 PASS。

另用 Node VM 執行參照 worker 的實際 `manifestAllowsAction` 函式：

- 原案：`allowed=false`、`maskCall=true`。
- 刪欄後：`allowed=true`、`maskCall=false`、`id=21`。

引擎的全許可後交集是原始碼核對，未實跑 WASM。

**建議：** 做保留型別／結構的遞迴比較，空 list 與空 dict 也必須是可比較節點；缺欄、空陣列與空物件必须彼此不同。或先將四個合法差異正規化，再深度比較整個 JSON。紅案須包含刪除 withheld 空 gestures，以及 `[]` 改 `{}`。不要藉改 worker 規則掩蓋 X1 缺口。

**B7 — M1-1 的 carrier 豁免比 X2 的允許範圍大**

位置：`wasm_sdk_probe/tools/check_merge_key_undo_scope.py:162`–`:168`；spec `:1052`、`:1072`、`:1120`–`:1121`；`handoff/RUNBOOK-relink-v19.md:16`。

**判準：** 只有 v15、v19 的 `probe_engine` 物件與 BASE 不同，沒有其他物件差異。

**反例：** 在 `sdk_api.cpp` 另加一段 `OXSDK_MERGE_KEY_UNDO` 下的程式，改變 v15／v19 的 `sdk_api.o`。`probe_engine.o` 原本的差異與兩個非法組合守衛都仍存在。

工具只對 `rule not in carriers` 拒絕物件差異；carrier 僅需「有任何一個物件不同」，不限制是哪一個或是否多了別的。

**證明：** 讀既有 `pre-link/m1-1/green.json` 的 100 筆結果，將 E2_V19 的 `sdk_api.o` 成功前處理結果改為不同 token hash，其餘保持綠案。以 AST 取出工具原本 `:155`–`:168` 的判定分支執行，`failures=[]`；差異變成：

- v15／`probe_engine.o`
- v19／`sdk_api.o`
- v19／`probe_engine.o`

這是對實際判定程式的模擬前處理輸入；沒有宣稱編過修改後的完整 C++，也沒有執行 M1-1 CLI 的非 `-n` make。

**建議：** carrier 也逐物件核對：`probe_engine.o` 必須不同，其餘必須相同；每個 carrier 的 guard 個別必須有兩筆失敗。新增「carrier 的 sdk_api.o 額外變動」紅案。既有三個紅案不會碰到這個分支。

**B8 — 「重開自己的兩句」退化成兩次子字串命中**

位置：`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:699`、`:714`；`wasm_sdk_probe/tools/judge_counted_m2.py:239`、`:244`–`:245`；`wasm_sdk_probe/tests/test_merge_wasm_clauses.py:115`–`:121`；spec `:730`。

**判準：** 拒絕的正向關窗之後，只有重開流程自己的開始句與結尾句；不得出現多餘 toast。

**反例：** 兩句都變成「已重新載入。」：開始句遺失，結尾句重複。窗口可以因結尾句出現且 generation 前進而正常關閉，但 `len==2` 與 `all('重新載入' in t)` 都成立。兩句無關訊息只要含同一子字串，也能滿足 reader 的 `onlyTheReopenToasts`。

**證明：** 合成綠案的 Chrome 儀器版及對照版，所有 refusal `toastWindow.toasts` 改成 `['已重新載入。', '已重新載入。']`，完整 reader 回 `0`、`VERDICT PASS`。

另一個反例將兩句都改成「正在重新載入…」、維持 `closed=true`，同樣 PASS，表示 reader 也沒有從序列核對正向關窗的結尾證據。既有 duplicate 測試只做三句，會被長度抓到，沒有守住兩句重複。

**建議：** 核對有序的開始／完成兩階段、結尾事件與 generation，並確認兩句來源確為重開流程；`keyPosted=true` 的無變動宣稱禁令照保留。增加結尾重複、缺開始、缺結尾與無關 toast 紅案。僅測 `len==3` 不足。

## SHOULD

**S1 — shrink 診斷的 GREEN 比它宣稱的條件弱**

位置：`wasm_sdk_probe/tools/run_shrink_repaint.py:173`–`:184`；其 docstring `:17`–`:19`；`findings/evidence/v18/finding-118/PREDICTION.md` 的 P3。

它只問最後 rows 是否「不等於」舊的 `twoPageRows`，且只把 `TILE_NOT_PAINTED` 字串當錯誤。沒有驗新 rows 的幾何比例、最後 h／docH／changed、painted 比例，也沒有拒絕其他 toast。

以 AST 執行原始 `:170`–`:187` 的摘要／verdict：

- 成長 rows=2007，縮小最後 rows=9999：GREEN。
- 正確 rows=1012，但 painted=0：GREEN。
- 出現「重繪失敗：IO_ERROR」：GREEN。

三案都保持 `grewToTwoPages` 與 `shrankToOnePage` 已觀察為真。

建議用量到的尺寸／畫布 backing 比例核對終態，而非僅不等於舊值；要求終態 reply 尺寸與請求一致、已處理 size change、通過頁面自己的 painted 判定，並檢查全部 toast。

這支被明示為非 criterion run，X7 另有 noToast／文件條款，所以列 SHOULD；不能把單獨 GREEN 當成上述性質的證明。

**S2 — 負數延遲可以滿足兩個延遲閘門**

位置：`wasm_sdk_probe/tools/judge_counted_m2.py:173`–`:176`；`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:913`–`:915`、`:789`、`:957`。

只驗 `ms < 1000`，沒有驗非負與有限。把合成綠案的全部 runner／engine 延遲換成 -500，完整 reader 仍回 `0`、`VERDICT PASS`；runner 的 `fast` 也回 True。負 runner 時差可表示拿到起點之前的回覆，不能用來宣稱「該下刪除的回覆」很快。

建議驗 finite 且 `0 <= ms < 1000`，並核對回覆與該次刪除的世代／動作／請求關聯。`await_delete` 現在按 response n 與動作類別選回覆，未留下 requestId 供 reader 對帳（`:723`–`:743`、`:278`–`:283`）。既有 1000 邊界與 None 紅案有效，但不覆蓋這類。

**S3 — session.close 失敗會跳過其餘 finally 清理**

位置：`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:1064`–`:1065`、`:1253`–`:1258`；`wasm_sdk_probe/tests/test_merge_wasm_clauses.py:309`–`:347`。

`teardown` 修好了 observer 讀失敗仍呼叫 close，但 close 本身拋出時，外層 finally 的 `server.terminate`、`server.wait`、最後報告存檔都不執行。

以正常 observer 回覆、close 拋 RuntimeError 的 stub 執行實際 main finally AST，得到 `server calls=[]`；`completedAt` 已設好，但最後報告步驟未到。

建議將瀏覽器 close、server 回收與報告保存置於可獨立完成的 finally，清理錯誤記入報告並維持不成功判定；補 close 拋錯紅案。這不造成 reader 假 PASS，但會留下 server／失去完整失敗證據。

## NOTE

**N1 — 證明方式與驗證邊界**

Repository 全程唯讀，使用 `PYTHONDONTWRITEBYTECODE=1`。沒有瀏覽器、連結、`run_*.py` 腳本執行、build／dist 寫入或 commit。只允許的 `make -n` 已查看 v19 完整 recipe；它使用 v19 自己的 build/dist、v18 source manifest 與封存的 v15 worker。

`tests.test_merge_wasm_clauses`：**38 tests，OK**。reader 與 X1 的既有 unittest 曾嘗試啟動，但沙箱連 `/tmp` 都不能建立，停在 fixture setup；不能把這次說成兩套測試通過。

替代證明使用記憶體 VFS：既有檔案只讀，合成報告 JSON／ODT 全存在 Python dict，僅替換 Path 檔案操作；judge、check、文件比較與 pair 使用實際模組。合成基準為兩瀏覽器各 78 筆 counted records，符合既有測試的三輪資料建構，判讀 `0`、`VERDICT PASS`；不是另造回傳綠的判斷器。

五份指定 v18 M2-4 真實紅案各自放入記憶體綠案：全部 code=1，僅對應瀏覽器 M2-4 FAIL，slow=102；兩份 fixed-page 報告只紅 latency，其餘三份也紅 noToast。反向驗證：正常記錄的 toast、generation 改變、延遲等於 1000 都會 FAIL。因此漏洞不是基準沒有判，或測試總回綠。

JSON 反例均由合成基準重置後獨立施作；不把修改的 latency 當成實測。M1-1 與 cleanup 使用原始 AST 分支；頁面與 worker 使用 Node VM 的實際函式及 stub，没有 DOM／瀏覽器，也沒有實跑新 WASM 輪詢。

## No defect found

- **1／spec §§30–32 的判準文字本身：no defect found。** 母體、次數、嚴格延遲上界、紅案、未執行的預設結論與更正均已指名；沒有找到必然讓正確 v19 不能過的新文字矛盾。B1–B8 是守衛比文字弱。X3–X6 的工具實作不在本次列出的讀檔範圍內，沒有替它們補發有效性判定。

- **2／reader：有 B1–B5、B8、S2。** 指定五份真實 M2-4 紅案的 latency 判定、26×3 counted case／round 集合、typed 2×10、三個紅案母體、文件重算與正常欄位的負向測試：no defect found。沒有宣稱整支 reader 無缺陷。

- **3／runner：有 B4、B5、B8、S2、S3。** 現有 `mode_schedule` 模式與次數、criterion 模式拒絕 subset／frame／owner、`bound_values` 六個來源、紅案只豁免三個 profile 值的設計、105 下終態文件比較，以及 drained log 的序號 acknowledgment：no defect found。未讀到的尾端可下次讀，不會因 acknowledgment 把未讀事件一起刪掉；toast 資料未納入 verdict 是 B5。

- **4／引擎 fix：no defect found。**  
  (a) KEYINPUT 與 KEYUP 都在 `postMergeKeyEvents:3593`–`:3597` 排好，才進輪詢；完成提早送出不會把下一個 K1 排到原 KEYUP 前。KEYUP 走 `lokhelper.cxx:1232`–`:1235` 的 KeyUp 路徑，沒有找到此併段鍵的文件修改。  
  (b) `syntheticSelectionDeadline` 僅跳過 queue pop；`Command.sdk` 預設 false（`:217`–`:227`），不會誤擦 SDK pending／cancelled bookkeeping；正常 dispatch 仍進 serial／request／handle 守衛及 S2 catch（`:3954`–`:3983`）。  
  (c) `getCommandValues` 在 `init.cxx:6689` 取 SolarMutex；Writer key 路徑也在其下，未找到本次形狀中途讓出的具體反例。callback 同時排 step 時，poll 可能多一次讀，但 Pending 可重讀，完成清 ticket，舊 serial step 會被丟棄。  
  (d) poll 不重設 stageDeadline；到期送 `values[0]=2`，只有未到期的 `MergeAwaitingKey` 送 3；其他三階段仍走原 deadline。  
  這是原始碼／有界推論，未驗證 WASM 排程。15 ms 是空 queue 的等待週期，不是每 15 ms 必定取得 SolarMutex 的保證。

- **5／頁面 fix 本身：no defect found；診斷 verdict 有 S1。** 具名 partial strips 疑慮以真實 `renderDocument`／`paint`／`layoutCanvas` 模擬：舊畫布高 70000，第一或第二 strip 回 size change，重排後高 36000；兩案終態都是 `[32767 at y=0, 3233 at y=32767]`，沒有 toast。第二案確有先畫舊首 strip，但 `layoutCanvas:780`–`:786` 隨即清畫布與 lastTiles，`finally:899`–`:903` 排新輪；沒有留下永久半份快取。這個 stub 不是瀏覽器視覺驗收。

- **6／v19：X1 有 B6、M1-1 有 B7。** 實際 Makefile 與 runbook 的隔離目錄、四物件定義、export 配方、v18 packs／metadata 路徑、v15 archive worker、link guard，以及封存後才綁定的順序：no defect found。v19 不存在、`BINDING=None`、v56 尚未凍結都是文件明示待辦，沒有當成缺陷。
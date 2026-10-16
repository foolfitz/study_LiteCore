# 第二輪審查 — seat `codex`

**結論：先處置 B1–B3，再釘死判準。** 第一輪的大部分問題已有實質處置；最新設計仍留下復原資料來源、收合狀態判定與暫存刪除順序三個實作前必須決定的缺口。

基線：`1b0ccaeed80bb8aaf3c19f4e626b0e0d0ed431f2`。全程唯讀，未寫檔、未執行 `make`、未開瀏覽器。以下不是 v21 的執行結果。

路徑縮寫：

- `S`＝`specs/SPEC-M3-link-batch-v21.md`
- `wsp/`＝`wasm_sdk_probe/`
- `lo/`＝`libreoffice-26-8/`
- `N142/`＝`findings/evidence/link-batch-v21/native/142-ctrl-home-end/`
- `NMD/`＝`findings/evidence/link-batch-v21/native/markdown-paste/`

證據標記：**read in source**＝讀原始碼、產物或唯讀重算；**stated in a doc**＝文件記載；**inferred**＝由前述證據推論。

## 第一輪逐項處置

「resolved」表示規格已作出足夠明確的處置，不表示尚未開始的實作已通過驗收。

| 第一輪項目 | 嚴重度 | §9 處置與證據 | 判定 |
|---|---|---|---|
| codex R1：產品不是 unipoll | BLOCKING | §9.1、§9.13；`S:172`、`:175`、`:272` 撤回錯誤前提，加入不等待序列，擁有者接受 250 ms 與具名限制。 | **resolved** |
| codex R2：D1 母數 | BLOCKING | §9.5、§9.14；`S:206`、`:279`。文法分類、未知／零臂拒絕；頁首排除改成明確未量。唯讀重算為 38 IN／43 OUT。 | **resolved**，承諾已縮成明定母數。 |
| codex R3：M1 含不能通過的語料 | BLOCKING | §9.6；`S:212` 依 MIME、字串資格、大小與角色分類，未知／零項拒絕。 | **resolved** |
| codex R4：派送後失敗與負向證人 | BLOCKING | §9.4、§9.14；`S:197`、`:198`、`:291` 定義錯誤並找到 M9。 | **partially resolved**：錯誤碼會擋佇列，但未保護貼上前最新內容；見 B1。 |
| codex R5：圖片降級不封閉 | BLOCKING | §9.3、§9.14；`S:186`、`:189`、`:285` 改成引擎解析後拒絕，涵蓋參照式、多圖與直接 SDK。 | **resolved**；HTML 的產品證人另見 S1。 |
| codex R6：降限／後備身分 | BLOCKING | §9.2、§9.12；`S:180`、`:181`、`:262` 分開引擎硬上限與 SDK 生效上限。 | **partially resolved**：身分處置可執行；精確語料與降限後邊界仍缺，見 S3。 |
| codex R7：完成與非變更記帳 | SHOULD | §9.7；`S:217`、`:222`、`:223` 加逐按壓完成、集合對帳、唯讀／乾淨／髒文件及過時 revision 臂。 | **resolved** |
| codex R8：刪除暫存與新移動交錯 | SHOULD | §9.8；`S:227`、`:228` 加 D8 與重複鍵處置。 | **partially resolved**：只處理移動後的新按壓；移動前已扣住的按壓仍會錯序，見 B3。 |
| codex R9：跨層閘控與型別 | SHOULD | §9.7、§9.10；`S:221`、`:238`、`:242` 加遮罩、真 manifest、直接 worker 與型別清單。 | **resolved** |
| codex R10：Markdown 比較器 | SHOULD | §9.12；`S:261` 明定 ODT／FODT、樣式、圖片資料雜湊與紅案。 | **resolved**；D1 的另一支讀取器另見 S5。 |
| codex R11：身分旗標與證據綁定 | SHOULD | §9.10；`S:241`、`:243` 完整約束 changed-leaf 與逐報告雜湊。 | **partially resolved**：兩個 M1-1 base 與實際命令仍只是待辦，見 S6。 |
| codex R12：C 字串不能證明窗長 | SHOULD | §9.11、§9.13；`S:273` 撤出 C 宣告及 C1。 | **resolved**，以撤回處置。 |
| opus B1：unipoll 錯誤前提 | BLOCKING | §9.1、§9.13；`S:172`、`:176`、`:272`。 | **resolved** |
| opus B2：連結後不能撤宣告／改引擎上限 | BLOCKING | §9.2；`S:180` 至 `:182` 改成殼層開關並具名 SDK 仍可呼叫。 | **resolved** |
| opus B3：D1 母數錯誤 | BLOCKING | §9.5、§9.14；`S:206`、`:279` 至 `:283`。 | **resolved** |
| opus B4：M1 母數必紅 | BLOCKING | §9.6；`S:212`、`:213`。 | **resolved** |
| opus S1：錯誤完成回覆無人守 | SHOULD | §9.7 D7；`S:217` 至 `:220`。 | **resolved**；採樣時點仍須釘定，見 S4。 |
| opus S2：遮罩無證人 | SHOULD | §9.7；`S:221` 加初始化失敗與直接 SDK range 拒絕。 | **resolved** |
| opus S3：殼層清單未封閉 | SHOULD | §9.7；`S:222`、`:223` 加集合等式與未知分類拒絕。 | **resolved** |
| opus S4：Markdown 後置條件無紅案／處置 | SHOULD | §9.4、§9.14；`S:196` 至 `:202`、`:291`。 | **partially resolved**：M9 存在，但復原安全性尚未成立，見 B1。 |
| opus S5：M3 單位與邊界未釘 | SHOULD | §9.3、§9.12、§9.14；`S:262`、`:287`。 | **partially resolved**：解析器定義空輸入；大小語料的字面要求不可能成立，降限後也缺邊界，見 S3。 |
| opus S6：M5 語法與宿主差異 | SHOULD | §9.3；`S:186` 至 `:192` 改成派送前拒絕，加入 HTTPS 主機名與參照式。 | **resolved** |
| opus S7：按住移動造成長佇列 | SHOULD | §9.8；`S:228` 加丟棄 repeat、限制與 D9。 | **resolved** |
| opus S8：釘選清單與載體 | SHOULD | §9.10；`S:238`、`:239` 列出已知位置及 define 範圍。 | **partially resolved**：grep 產物與兩個 base 尚未固定，見 S6。 |
| opus S9：v5 如何 import v4 | SHOULD | §9.10；`S:240` 指定 globals、argv、重寫與前置檔。 | **resolved** |
| opus S10：C 欄位無讀者／缺裁決 | SHOULD | §9.11、§9.13；`S:273`，擁有者選撤出。 | **resolved** |
| opus S11：D4 預設重帶 142 | SHOULD | §9.9；`S:233` 改成攔鍵並提示。 | **resolved** |
| opus S12：長文件不跟隨游標 | SHOULD | §9.9 D10；`S:234`。 | **resolved** |
| opus S13：執行次數 | SHOULD | §9.12；`S:256`，每臂每瀏覽器 N=3、N/N。 | **resolved** |
| opus S14：未量位置 | SHOULD | §9.12、§9.14；`S:290`，原生已量，跨格改成拒絕。 | **resolved**，其餘未量仍須保留登錄。 |
| opus S15：入口未定 | SHOULD | §9.12、§9.13；`S:258`、`:271`，A 與取消臂定案。 | **resolved** |
| opus S16：貼上變更記帳 | SHOULD | §9.12；`S:259` 要求 dirty 與 autosave。 | **resolved** |
| opus S17：既有殘留變得容易到達 | SHOULD | §9.12；`S:260` 加記錄臂與發佈說明。 | **resolved** |

## 本輪發現

### B1 — BLOCKING：進入復原清單不代表已有最新檢查點

**規格：§9.4、§9.14 M9。**

- **read in source**：`wsp/editor-shell/editor-session.js:321` 對 `MUTATION_OUTCOME_UNKNOWN` 只呼叫 `_blockQueue`；沒有保存內容或立即重開。
- **read in source**：真正復原由 `wsp/web/e2-editor-app.js:2402` 的通知按鈕呼叫 `rollback()`；`wsp/editor-shell-v2/narrow-editor-v2-session.js:1318` 將它交給 `restart()`。
- **read in source**：重開在 `wsp/editor-shell/editor-session.js:163` 選「較新的 checkpoint，否則 authority」。`_checkpointBeforeSelection` 在 `:475` 對乾淨文件直接返回，而且 `:493` 的儲存失敗會被吞下並登錄。
- **stated in a doc**：`S:103` 只要求 Markdown 比照 insertText 以 mutation 排隊；`S:198`、`:291` 卻宣稱回到檢查點且不掉資料。
- **inferred**：一般位置先打字，再貼 Markdown；若後讀失敗或發生具名 Undo 碰撞，沒有新的選取／移動替它存檢查點。回復會丟掉貼上之前的未儲存文字。受保護區段的乾淨 M9 看不到這個問題。

唯讀重算復原選擇：

| authority stamp | checkpoint stamp | 貼上前 current stamp | 重開 stamp |
|---:|---:|---:|---:|
| 0 | 無 | 0 | 0，乾淨內容保留 |
| 0 | 無 | 1 | 0，先前編輯遺失 |
| 0 | 1 | 2 | 1，較新編輯遺失 |

**具體修改：**在 Markdown 的佇列操作內、派送之前，確保復原來源對應當時的內容 stamp。乾淨文件可使用 authority；髒文件必須成功保存最新 checkpoint。保存失敗或來源仍舊，就拒絕派送。不能只呼叫會吞失敗的 checkpoint 方法便繼續。M9 加入無 checkpoint、舊 checkpoint、checkpoint 儲存失敗，以及正常位置派送後讀失敗；實際驅動通知按鈕，驗證貼上前的文字、格式與 dirty 狀態。

### B2 — BLOCKING：collapsed-only 尚未指定可承載拒絕保證的讀取來源

**規格：§9.14「只在收合的游標上貼」。**

- **stated in a doc**：`S:290` 指定錯誤碼與頁面檢查，但沒有指定引擎怎麼取得 collapsed、未知狀態怎麼處理。
- **read in source**：`wsp/src/probe_engine.cpp:329` 明說空的 rectangle 清單在尚未觀察選取時不代表收合；`:2601` 顯示它是回呼更新的快取。
- **read in source**：`handleEditorAction` 的一般閘門在 `:5514` 驗 `selectionObserved`，再於 `:5521` 讀快取。刪除的實際派送前置條件則更強：`startSelectionBarrierDelete` 在 `:4189` 呼叫 `readSelection()`，並同時要求 typed readback 與回呼幾何都支持收合。
- **read in source**：`NMD/round-2/out/T1-P11-M8/run1/summary.json:42` 記錄跨格範圍具有文字選取；三回均發生來源文字與亂碼附加。
- **inferred**：照一般 action 閘門只抄快取，或只檢查頁面 snapshot，都不能支撐「跨格一定拒絕」。`selectionObserved=true` 也不證明那次觀察仍代表派送時狀態。

**具體修改：**明定引擎在實際派送階段使用的 typed readback、回呼確認及未知／矛盾狀態的拒絕規則；以既有刪除前置條件為比較基線，避免改用已知會卡住的 HTML readback。加入「快取說收合、typed readback 是範圍」、未觀察選取、反向範圍及產品 select-range 跨格臂。未能保證的非同步排序應具名，不能併入未說明的 collapsed 保證。

三個新派送前拒絕碼也應明定 `recovery: "none"`；現有 `wsp/editor-shell-v2/paragraph-editor-session.js:44` 並不認識它們，不能讓一般錯誤分類把拒絕解讀成 rollback。

### B3 — BLOCKING：只改 `holdsDelete` 仍會把早先按壓送到移動後的位置

**規格：§9.8。**

- **read in source**：`wsp/web/e2-editor-app.js:2782` 扣住按壓；`:2727` 等舊操作回答後才重新派送。因此已扣住的按壓尚未佔有 session 佇列中的順序。
- **read in source**：`:2761` 每次新派送都覆寫共用的 `heldDeletes.action`；`:2728` 釋放時讀的是這個可變欄位。
- **stated in a doc**：`S:227` 只改「之後的新按壓要不要扣住」，沒有處置先前已扣住的按壓。
- **inferred**：文字中依序按 `Backspace B1`、`Backspace B2`、`Ctrl+End`。B2 被扣住；移動先排入佇列；B1 真刪除完成後才釋放 B2，於是 B2 刪文件結尾的字。若移動後再送 Delete，B2 還可能被重送成 Delete。

依現有函式重算的序列：

```text
使用者順序：B1、B2、Ctrl+End、Delete D3
B1 回答時的待執行順序：Ctrl+End、D3、以 forward 重送的 B2
```

這不是 144 的深度失效：保留 `deletesInFlight + heldDeletes.count` 時，有標記 repeat 仍受深度 2 約束。也沒有證據顯示只改條件就必然重開 145 的漏減帳；`:2743` 的無條件結算仍正確。缺口是**暫存按壓跨越其他操作的順序與方向**，既有獨立重跑未必碰得到。

**具體修改：**規定任何後續操作越過刪除暫存之前，先把較早按壓依原方向安置到正確順序；暫存方向不能由後來派送覆寫。D8 加上移動前已有 held press 的序列、兩種方向、移動後換刪除方向，以及拒絕／換文件後帳歸零。保留 144 的深度規則與 145 的結算規則。

### S1 — SHOULD：HTML 拒絕缺少產品引擎派送路徑的負向證人

**規格：§9.3、§9.14；M1、M3、M5。**

- **stated in a doc**：`S:286` 新增 HTML 拒絕，但 `S:192` 的 M5 仍只有 Markdown 圖片與程式碼外觀；`S:212` 的角色分類沒有 HTML。
- **read in source**：`lo/sw/source/filter/md/mdcallbcks.cxx:272` 累積 HTML；`lo/sw/source/filter/md/swmd.cxx:591` 交給 HTML 匯入。`NMD/round-2/README.md:124`、`:127` 記錄 H4／H7 的真實抓取。
- **inferred**：保留純函式與模型測試正確，卻在引擎 handler 漏用 HTML 判定，明列的 WASM M1–M9 仍可能全部通過。

**具體修改：**將 round-2 語料按解析結果納入角色分類；產品／直接 SDK 都測 HTML block、inline HTML 後接 block、stylesheet，以及程式碼裡的 HTML 正向控制。拒絕須驗錯誤碼、revision／Undo／內容不變及零請求。對「helper 正確、handler 略過 HTML 判定」做紅案。

### S2 — SHOULD：同一個 md4c 不等於同一份解析輸入

**規格：§9.3、§9.14 預掃描。**

- **read in source**：旗標確實相同，見 `lo/sw/source/filter/md/swmd.cxx:951`。
- **read in source**：Writer 先在 `lo/vcl/source/treelist/transfer.cxx:1514` 移除所有尾端 NUL，再以 `osl_getThreadTextEncoding()` 解碼；`lo/sw/source/uibase/dochdl/swdtflvr.cxx:2216` 將 OUString 作為 UCS2 stream，最後由 `swmd.cxx:915` 轉回 UTF-8。
- **read in source**：md4c 原始位元組中的 NUL 會產生 `MD_TEXT_NULLCHAR`，見 `wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src/md4c.c:4412`。
- **inferred**：預掃描原始 UTF-8 與 Writer 的輸入不保證相同。最小反例是 `"\0"`：掃描器會看到內容，Writer 解析的是空位元組。非 UTF-8 thread encoding 也會使內容不同；M2 只驗最終環境的一項語料。
- **read in source**：`md4c.h:396` 定義解析失敗／回呼中止的非零結果；三條規則未明定其他失敗如何處置。

**具體修改：**固定兩次解析的輸入契約：驗證或建立 Writer 呼叫執行緒的 UTF-8 編碼，對尾端 NUL 等轉換採一致處置，或在派送前拒絕不能保真的輸入。預掃描解析失敗一律拒絕。模型加入 NUL、無效 UTF-8、非 UTF-8 codeset 與解析失敗；不要把既有原生掃描報告當成位元組保真的證明。

### S3 — SHOULD：精確大小語料的字面要求不成立，16 KiB 缺邊界證人

**規格：§9.2、§9.12；M3、M6。**

- **stated in a doc**：`S:262` 要求恰好 65,536／65,537 bytes，且由三位元組 CJK 字元組成。
- **read in source，唯讀算術**：兩者除以 3 的餘數分別為 1、2；全由三位元組字元無法構成。
- **stated in a doc**：`S:181` 允許 SDK 降到 16 KiB；`:262` 仍只釘 64 KiB 邊界。
- **inferred**：降限後，SDK 錯誤地繼續接受 16,385 bytes，既定 M3 的 65,537 拒絕與 M6 的 16 KiB 成功都可以綠。

**具體修改：**生成 `CJK 重複＋明定 ASCII 尾碼`，附長度與雜湊。SDK 測試從最終生效上限 `L` 生成 `L`、`L+1`；引擎硬上限另測 65,536／65,537，避免 SDK 先拒絕而遮住引擎缺陷。

### S4 — SHOULD：新增判準尚未補齊「永遠沒做」與固定判讀方式

**規格：§5、§9.7–§9.14。**

- **stated in a doc**：`S:217` 至 `:234` 的 D7–D10 沒有明寫未做預設；`S:291` 的 M9 只有「若紅」。
- **stated in a doc**：`S:176` 的 D6 是記錄臂；`:256` 又概括所有 D／M 為 N/N，應區分紀錄完整與產品正確。
- **stated in a doc**：`S:220` 只寫「≥500 ms 之後」，沒有固定採哪次讀取，容許實作者一直重讀到相等。
- **stated in a doc**：`S:261` 要求位置由原生臂產生；`:290` 又改回一份具名位置清單。
- **stated in a doc**：K 繼承 `specs/SPEC-M3-link-batch.md:567` 的人工抽取 busy 時段，終止證據仍由讀的人承載。

**具體修改：**在釘死前追加統一的缺報／缺 run／NE 預設，明確涵蓋 D7–D10、M9 及新增附帶臂；D6 保持診斷性質並登錄未量預設。D7 指定單次採樣時點與容許時間窗。M4 從 metadata 產生位置角色，或明確縮成固定個案並登錄其餘位置。K 的人工部分以讀既有產物的獨立讀取器承載，先做缺失／錯誤時段紅案。

第 1 項的未出貨預設也應說明 SDK 動作是否仍宣告；若只是移除頁面綁鍵，應像 Markdown 一樣具名其剩餘可呼叫範圍。

### S5 — SHOULD：D1 指定的標記讀取器尚不能讀產品 ODT

**規格：D1、§9.14。**

- **read in source**：`N142/d1-marker/tool/read_marker.py:74` 直接 `ET.fromstring`，`:184` 固定讀 `.fodt.gz`。
- **stated in a doc**：同檔 `:11` 宣稱這是 native／WASM 共用的 paragraph-order reader。
- **read in source**：`wsp/src/sdk_api.cpp:134` 的產品儲存只接受 ODT。唯讀把現有 ODT 交給 `paragraphs()`，得到 `ParseError: ... line 1, column 2`。
- **inferred**：§9.12 補的是 Markdown 結構比較器，沒有涵蓋 D1 的這支讀取器。

**具體修改：**D1 明定 ODT／FODT 共用的容器轉接，從 ODT 讀 `content.xml` 與需要的 master styles，保持相同段落順序與 offset。先做跨容器相等、標記位移、重複標記、缺 XML 的紅案，再用於 WASM 判讀。

### S6 — SHOULD：I1 的兩個基準仍未釘定

**規格：§9.10；I1。**

- **stated in a doc**：`S:239` 仍是「兩個 base……在實作前寫下」，沒有兩個實際 revision 或命令；`:238` 的 grep 清單也尚未有指令與輸出。
- **read in source**：`handoff/RUNBOOK-relink-v20.md:34`、`:35` 顯示 v20 的兩次檢查使用不同 base 與 carrier 集合；不能僅替舊命令追加 `E2_V21` 就推定涵蓋正確。
- **inferred**：等到實作後才挑 base，會改變 I1 真正證明的歷史範圍。

**具體修改：**釘判準前提交兩個確切 base、完整 carrier 命令及 grep 產物；分別說明它們證明本批與既有 profile 的哪個界線。新工具要有未宣告 carrier／舊 profile 漂移的紅案。

### N1 — NOTE：遮罩狀態檢查未顯示會破壞既有凍結 profile

**規格：§9.7、§9.10。**

- **read in source**：樹內執行 `oxsdk_editor_set_action_gestures` 的產品呼叫在 `wsp/sdk/sdk-worker.js:1253`；`:541` 目前確實只回傳數值。`wsp/src/editor_api.cpp:175`、`:183` 的拒絕會被新檢查揭露。
- **read in source**：產品頁在 `wsp/web/e2-editor-app.js:3305` 指向 profile 自己的 worker。唯讀盤點現有 profile，v20 的 worker 是 `478d0da1…`，其他舊 profile 亦各有固定副本。
- **read in source**：`wsp/Makefile:1590` 會拒絕以改過的樹內 worker 重鑄 v20；`:3298` 的 `writer-review-r6` 與 `:3313` 的根目錄副本會隨資產更新，但目前沒有 editor contract 可進遮罩迴圈。
- **inferred**：既有凍結 profile 不會因修改來源 worker 就自動開始嚴格初始化；未發現已出貨組合必然新失敗。

**具體修改：**照規格實作非 OK 即失敗；在 runbook 列出上述 worker 綁定，驗證 v21 的正常初始化與注入非 OK 的紅案。保留既有凍結副本。

### N2 — NOTE：`md_parse` 可解析連結；指定的其他 Markdown 連結構造未見抓取路徑

**規格：§9.3、§9.14。**

- **read in source**：`wsp/Makefile:842` 把引擎物件放在 `$(cat $(LINKDEPS))` 前面；實際 linkdeps 含核心 `libmd4c.a`。以既有 `llvm-nm --defined-only` 讀該 archive，得到全域定義 `T md_parse`。`md4c.h:29` 提供 C linkage。無須新增 JS 匯出。
- **read in source**：一般／自動／參照式超連結最終走 `lo/sw/source/filter/md/mdcallbcks.cxx:164` 的 `SwFormatINetFormat`；wiki link 在 `:219` 同樣只建立連結。Markdown 圖片才走 `:247` 的 `InsertCurImage`；原始 HTML 是另一條已被 §9.14 指名的路。
- **read in source**：依既有 scan.jsonl 重算三規則，H1–H7 都拒絕；N1、S14、S15、W3、W4 都允許，符合 §9.14 修正目的。
- **inferred**：針對 brief 指名的 wiki links、autolinks、link reference definitions，未找到另一個貼上時抓取路徑。這個結論仍以相同解析輸入為前提，見 S2。

**具體修改：**採用目前連結方式；將核心 header 的 include 路徑與依賴限於 v21，保留這些連結構造的無請求控制臂。

## 判準逐項普查

「漏網變異」是對文字判準的靜態分析；若由其他判準捕捉，另行註明。固定案例可以是逐實例性質，不能因此宣稱已普查案例以外的母數。

| 判準 | (a) 仍可綠的變異 | (b) 形式 | (c) 永遠未做的預設 | (d) 執行時判斷／形式問題 |
|---|---|---|---|---|
| **D1** `S:134`、`:206`、`:283` | 回覆 selection 錯、實際標記落點正確；D7 也只比 caret。 | **工具封閉**；38／43 可重算，虛構新臂自動分類，未知／零臂紅。 | 第 1 項不出貨、頁面不綁鍵；SDK 剩餘範圍待說明。 | 可達性的人判已撤除。ODT 讀取方式待補，見 S5。 |
| **D2** `S:135` | Ctrl+End 後的 Delete 壞掉，Home／Backspace 個案仍綠。 | **逐實例**，明定反例。 | 同 D1。 | 無主觀判斷；涵蓋範圍有限。 |
| **D2′** `S:175` | 文中已有 held press 的交錯錯序；單一下 Backspace 仍正常。 | **逐實例**，固定不等待序列 × 瀏覽器 × N。 | 紅或未做，第 1 項不出貨。 | 無；B3 是缺少的另一序列。 |
| **D3** `S:136` | 移動誤設 dirty；回覆及時間仍正確，§9.7 記帳臂應抓。 | **逐實例**，兩個明定邊界。 | 同 D1。 | 無。 |
| **D4** `S:137`、`:233` | 正常移動後回覆帶錯 selection，但最終標記正確。 | 以 `r-*` 來源產生可成 **工具封閉**；須確實納入反向臂。 | 未做仍有原預設；紅時改為攔鍵提示。 | 不必人判；缺報也應明確套用攔鍵預設。 |
| **D5** `S:138`、`:242` | 已宣告 profile 的正常按鍵被吃掉；v20 不攔鍵仍綠，D1 應抓。 | 跨層矩陣由真綁定表產生時是 **工具封閉**。 | 最終候選殼層不得與 v20 搭配出貨。 | 無；已改用真 manifest。 |
| **D6** `S:176` | 標記落錯仍可完成紀錄；這正是診斷用途。 | **逐實例的紀錄工作**，沒有產品通過條件。 | 未明寫；應為未量／不作排序宣稱。 | **需釐清**：不可把「記下了」混成 N/N 正確。 |
| **D7** `S:217` | caret 正確但 selection 回覆錯誤；或延後挑一次恰好相等的讀取。 | 對 D1 每次按壓為 **工具封閉**。 | **缺。** | **仍違反 §2**：缺未做預設；採樣時點未固定。 |
| **D8** `S:227` | 反方向交錯或移動前已有 held press，固定三鍵序列仍綠。 | **逐實例**；目前是一個明定序列。 | **缺。** | **仍違反 §2**；不能把這一臂稱為刪除交錯普查。 |
| **D9** `S:228` | 第一次 hold 正常，後續獨立按壓因旗標未清被吞掉。 | **逐實例**；應對兩個新動作各生成一臂。 | **缺。** | **仍違反 §2**；有標記／無標記 repeat 應寫明。 |
| **D10** `S:234` | 頁碼對此 fixture 寫死為 60；單一 fixture 仍綠。 | **逐實例**，固定長文件。 | **缺。** | 狀態判讀明確；**仍違反 §2** 的未做預設要求。 |
| **M1** `S:139`、`:212` | helper 正確但產品 handler 略過 HTML 拒絕；正向語料仍綠。 | 原生 metadata 分類為 **工具封閉**；round-2 新角色待納入。 | M1–M6 紅或未做，頁面無入口；SDK 仍可呼叫，已具名。 | 原本分類問題已修；新規則產品覆蓋見 S1。 |
| **M2** `S:140` | CJK 文字正確，其他格式轉換錯誤；M1 應抓，CJK 粗斜體另有具名限制。 | **逐實例**，M8。 | 頁面無入口，另立 finding。 | 無。 |
| **M3** `S:141`、`:262` | SDK 降到 16 KiB 後仍接受 16,385 bytes；64 KiB 拒絕臂仍綠。 | 邊界生成可成 **逐實例參數化性質**；目前語料描述不可能成立。 | 頁面無入口。 | 無主觀判斷；生成規則須先修，見 S3。 |
| **M4** `S:261`、`:290` | 未列位置的 Undo 丟格式；指定位置仍全部還原。 | **尚未封閉**：來源位置在 native metadata，最後又以手列 P1／P3／P4／P8–P10 鏡像。 | 頁面無入口。 | **仍有 §1 問題**，除非明確縮成固定個案，並登錄未涵蓋位置。 |
| **M5** `S:192`、`:286` | 只漏 HTML 拒絕；五類 Markdown 圖片／程式碼個案仍綠。 | 明列案例為 **逐實例**；圖片識別機制由 parser 定義。 | 頁面無入口。 | 原「保守比對」人判已移除；HTML 缺產品臂。 |
| **M6** `S:144`、`:181`、`:262` | 最終 16 KiB 成功，但 SDK 實際上限仍是 64 KiB。 | **逐實例**，生成大小與量測時間。 | 64 KiB 紅降 16 KiB；再紅或量不到，頁面無入口。 | 10 秒與計時範圍已固定；上限邊界見 S3。 |
| **M7** `S:145`、`:261` | Markdown 對話框取消時誤插入內容；Ctrl+V 控制仍綠，由 §9.13 取消臂抓。 | **逐實例**；純文字結構比較已補。 | v21 不出貨。 | 無。 |
| **M8** `S:146`、`:242` | 已宣告 profile 的入口錯誤；v20 的負向閘控仍綠，由 M1 抓。 | 實際匯出／閘控矩陣生成後為 **工具封閉**。 | 最終候選殼層不得與 v20 搭配出貨。 | 無。 |
| **M9** `S:291` | 乾淨文件回復正確，髒文件回復丟掉貼上前編輯。 | **逐實例**，受保護區段。 | 只寫「若紅無入口」，**缺未做預設**。 | **仍違反 §2**；也不足以支持「不掉資料」，見 B1。 |
| **I1** `S:148`、`:239`、`:241`、`:243` | 選錯 M1-1 base，X1 與所選兩次 scope 檢查仍可綠。 | manifest leaf／產物集合主要為 **工具封閉**。 | v21 不綁定。 | **尚未完成前置釘定**：base、carrier 命令與 grep 產物，見 S6。 |
| **K** `S:149`、`:157` | C 的邊界鍵根本沒送出，既有自動判分仍可綠；人工讀 busy 才區分。 | 自動鏈為 **工具封閉**；C 正向對照仍由人工擷取。 | 未計數候選，名義版本停在 0.2.24。 | **仍有 §8 問題**：終止證據未由可重跑讀取器承載；這是繼承的限制。 |

整體附帶臂也須進缺報檢查：§9.7 的記帳、§9.12 的 autosave、§9.13 的取消與 §9.14 的 range 拒絕，不能只出現在散文裡，缺一筆時仍把 D／M 報告判完整。

## 0.2.25 的未覆蓋使用者路徑

目前找到、且未被現有具名限制充分承載的路徑是：

- **先打字，再遇 Markdown 派送後未確認，按回復而遺失先前編輯**：B1。`L-md-undo-collision` 宣稱方向安全，並未登錄這種先前資料遺失。
- **文字中連按兩次刪除，立刻 Ctrl+End，第二次刪除跑到結尾**：B3；換刪除方向還會污染 held action。
- **尾端 NUL 等輸入在預掃描與 Writer 之間改變，導致原本應拒絕的輸入進入復原**：S2。
- **新 HTML predicate 在 helper 正確、產品 handler 漏接，仍通過既定產品判準**：S1。

finding 147 的輸入欄位、148 的跨格範圍、CJK 粗斜體、250 ms 提早完成、表格逐層移動與頁首未量，已有明確登錄；本輪不把它們重報成未揭露的新缺陷。

## 十行摘要

1. 第一輪 33 個 BLOCKING／SHOULD：26 個 resolved，7 個 partially resolved。
2. BLOCKING B1：Markdown 派送前未確保最新復原來源，rollback 可能丟掉先前未儲存內容。
3. BLOCKING B2：collapsed-only 未指定足夠的引擎讀取與未知狀態規則，跨格拒絕保證尚未成立。
4. BLOCKING B3：既有 held press 仍會跨過移動，並可能被後來的刪除方向覆寫。
5. SHOULD S1–S2：補 HTML 的產品派送紅案，固定預掃描與 Writer 的輸入轉換及解析失敗處置。
6. SHOULD S3：精確 CJK 大小需 ASCII 尾碼；SDK 生效上限與引擎硬上限各驗邊界。
7. SHOULD S4：補 D7–D10／M9 未做預設，固定 D7 採樣，分清 D6 記錄與產品通過。
8. SHOULD S5–S6：D1 讀取器補產品 ODT；I1 的兩個 base、命令與 grep 產物先釘定。
9. NOTE：md_parse 有全域定義且在產品 linkdeps；嚴格遮罩初始化未見必然破壞既有凍結 profile。
10. 唯讀驗證：D1 為 38 IN／43 OUT，38 臂加兩控制各三回通過；未寫檔、未 make、未開瀏覽器。
# M4：試算表儲存格編輯 v1

> 2026-10-25，任何本輪驗收執行之前建立；commit 後只追加。擁有者指定：雙擊格子原地編輯、上方寬輸入欄、沿用粗體／斜體／底線操作；離座期間自主規劃執行，簡單編譯／建置可代跑，直到必要人工介入才停。完整 K 繼續併批。

## 1. 範圍與設計

新增 **ods-editor-v1**，沿用 viewer v3 的已建 Calc／forms／dba 核心與資源，不重建核心、不改凍結 viewer profile 或 Writer profile。新增自己的 `spreadsheet-shell/` 與產品頁；現有唯讀檢視器保留。宿主可寫 ODS 才進編輯器，唯讀 ODS 保留唯讀行為。

雙擊進入覆在所選儲存格矩形上的瀏覽器文字框；上方寬公式欄與它共用同一份草稿。單擊選格並顯示 A1 位址與**引擎直接讀出的原始公式／內容**，不拿 tile 顯示值替代。Enter 提交，Escape 取消；IME 組字中的 Enter 不提交。換格、換表、存檔前先提交草稿，取消不發出寫入。Ctrl／Cmd＋S 存檔，B／I／U 套整格的文字格式，不宣稱支援格內部分文字格式。沒有新要求要接回 Writer v23，此輪優先做試算表編輯。

引擎操作採引擎執行緒上、SolarMutex 保護下的同步 UNO cell model：讀 `XCell.getFormula`／文字與格式、寫 `setFormula`／三種格式。這避免把 `CELL_FORMULA` 回呼快取當成直接讀值，也不送可能被超車的鍵。內部 model 入口另置一個以 `LIBO_INTERNAL_ONLY` 編的 bridge；普通 LOK translation unit 不變成內部 build。這是具名耦合 **L-calc-model-bridge**，只跟本樹核心版本綁定，不宣稱 LOK 公開 ABI 提供它。先做原生實驗；若取不到正確 model 或幾何，停在事實上，不換成猜測。

點選幾何由引擎自己的 row／column headers／cell cursor 提供，保留工作表與 cell 座標；每個寫入都帶明確 part／column／row 與預期 revision，不用瀏覽器當下焦點推定目標。輸入字數上限 32,767 UTF-16 code units，超過拒絕且原文不變。保護工作表的鎖定 cell、readonly host、錯誤型別與越界在 mutation 前拒絕。

存檔使用 ODS。鏡像下載 ODS；Nextcloud 沿既有鎖、ETag／條件 PUT、衝突副本與未存離開保護處理，不能借用只有 load 的 viewer host 冒充寫入。產品需要驗證真的存回再重開，而非只看目前引擎狀態。初版可採手動儲存並明示未存狀態；不把 Writer 的自動儲存驗收直接移植為已成立。

## 2. 執行前先釘的判準

| id | 判準與母體 | 形式 | 沒做／失敗的預設 |
| --- | --- | --- | --- |
| N-model | 原生同核心版本：每個 fixture case 直接讀出 cell 原始內容；修改後讀回與另存 ODS 重開相符，其他指名 cell／sheet 不變。case 包含文字、中文、數字、公式（公式欄讀公式而 tile 算結果）、空白清除、引號／換行、兩表不同值；N＝3 | 逐實例，case 由 fixture manifest 產生 | 不連結新編輯器 |
| N-format | 每種格式各自設為 true／false，三字族的屬性讀回；存檔 XML／重開一致，鄰格不變，N＝3 | 三個操作的工具封閉枚舉 | 不提供該按鈕，不冒稱 Writer handler 可直接套用 |
| N-geometry | 原生所選 cell 直接位址與幾何，點選測試涵蓋非等寬欄、非等高列、合併格與隱藏列／欄；正向 cell hit 與偏一格紅案 | fixture 逐實例 | 不接雙擊編輯 |
| S-old | 既有 viewer／Writer profile、出貨檔與 E1-C 綁定無變；新功能只能由新 profile 宣告，移除 capability 時 worker 不碰 symbol；舊 profile 的 save 禁止照舊 | 對既有綁定檔逐實例；manifest／exports 由產物讀 | 不切產品頁 |
| S-state | 草稿／提交／取消／IME／過期 revision／切表／排隊／儲存失敗／唯讀／保護格各路徑有可觀察結果；紅案先於綠案，核心拒絕時不可標示已存 | 路徑由新 API／session 操作與 fixture 產生，逐實例 | 不開放編輯 |
| W-edit | Chrome、Firefox，各 N＝3，在產品頁雙擊修改及公式欄修改，Enter／Escape、中文、公式重算、清空、B／I／U，下載 ODS 後由獨立 ZIP／XML 讀值與格式，再重開；另一表／鄰格不變 | fixture 逐實例 | 保留 viewer 頁；編輯器未成立 |
| H-write | 真 Nextcloud Files 路徑：可寫 ODS 用編輯 host，原檔條件寫回／重開、鎖正向、外部改檔衝突副本、readonly 拒絕；Writer 入口仍能開存。Chrome、Firefox，各一輪 | 已指定宿主路徑逐實例 | 不把新宿主當日常候選；採事前寫好的退路 |

N-model／N-format 的 fixture 與原生讀取產物落地後就封閉該次 N。W-edit 兩瀏覽器的第三筆成立後封閉；後續新顧慮另立 finding／工作項，不無限加跑。新增或更正判準必須在計入的執行之前 append，指名逼出它的實際結果；不得為了維持宣稱另造機制。

## 3. 順序、建置與環境

1. 本規格 commit。建立 fixture 與原生 bridge 實驗，先核對 model、幾何、保護與格式，保留原始失敗。
2. 新 API／bridge、worker／SDK、session、UI 分單位實作與 commit；有意義的拒絕與狀態測試先紅。新建 profile builder／Makefile，連結前保留現行身分／檔案雜湊，確認只用已建核心。
3. 每次編譯前讀 `uptime` 與 `pgrep -a make`；若有其他建置或長時間量測，先詢問並繼續不相依工作。簡單 C++ probe、SDK objects 與 SDK link 依本次明確授權執行。若需要重建 LibreOffice 核心或 root 操作，列出具體原因與指令後停給擁有者；不得 sudo／su／doas。
4. 鏡像定向測試與視覺檢查，先不動 ddev。通過後，在隔離宿主 worktree 準備封包、離線檢查、還原與安裝腳本，才碰 live host；宿主變更前再讀自己的規則。
5. 本次自主授權可準備並使用**空閒的**共享 ddev 測試時段：只啟動本任務 litecore，不停別人的專案。先記錄全部專案狀態，其他專案 running 則停在宿主執行前；完成或遇必要人工介入後恢復本次改動的專案狀態。這不是 K 的 P5 時段，也不啟動完整計數。

## 4. 計數與限制

各定向判準成立也仍是未計數候選；名義出貨保持 0.2.26。最後 K 等更多更新後一起做，pins／BINDING／chain 不在本輪提前重綁。既有 F3-hand／H7／V3-SEE 不重問。

不宣稱支援整片多格貼上、拖拉填滿、格內部分文字格式或所有 Calc 編輯功能。原有 ODS 限制（如 Basic UDF、E6 leak 登錄）保留。新編輯 UI 不顯示開發用協定／profile 判斷細節；診斷資料留給測試讀取。

本輪開始 §34.4 累計 47／27。新功能工具不是既有判讀修理；若真的改到既有判讀，依原規則留下證人並記帳。

## 5. 第一次原生執行逼出的兩項修正（2026-10-25，只追加）

`native/run-01/report.json` 159／171：寫入、重算、格式、保護與另存均成立；幾何在第 3／5 列各偏 25／38 twips，另外文字型 `'=B1*9` 的 UNO `getFormula()` 回傳 `=B1*9`（仍為 TEXT）。原始失敗保留，不用放寬幾何比較或把文字誤判成公式通過。

取代 §1 的幾何來源假設：UNO Position／Size 是邏輯毫米尺寸，不能代替 LOK 的像素對齊矩形。bridge 將以同步 `XSelectionSupplier` 選到明確 cell，再直接讀公開的 `.uno:CellCursor`，點選則讀 `.uno:ViewRowColumnHeaders`。本頁固定 scale＝1、每 CSS px 15 twips，明確設定 client zoom；不把一般 Writer 的鍵／回呼等待接回來。原生仍對比獨立 LOK GoToCell 後的 cursor，且保留偏一格紅案。若不能讀到相符 cell，就拒絕，不拿舊矩形繼續寫入。

`formula` 保留 UNO 原值，另回傳可安全送回的 `input`；TEXT 的 `=／+／-` 開頭補一個 apostrophe，數字／既有 apostrophe 則沿 UNO 本身的 escape。這是修正實作對 raw 值的解讀，原本「原始內容不得被改型」的判準不變。先讓上述紅案在新讀法成立，再執行新的 N＝3，舊三輪不挪來計數。§34.4 +0／+0（新功能實作／新原生工具，不是修理既有判讀）。

## 6. 定向實測與宿主衝突證人（2026-10-25，只追加）

原生最終 `findings/evidence/m4-cell-editing/native/run-03-final/report.json` **171／171**；兩瀏覽器各三輪的真實鍵鼠、下載到磁碟、獨立 ZIP／XML 與重開為 `browser-edit-03-download/report.json` **186／186**。W-edit 在該輪封閉；首次重開的 reader 誤以為存檔仍停在第 0 表，保留失敗並改成明確選第 0 表，沒有改產品判準。既有 static gate exit 0、E1-C intact，舊 Writer／viewer frozen 檔案保持相同。

新引擎凍結為 **ods-editor-v1／d5a081f8…／worker 39737ddb…**；沿用 viewer v3 核心，沒有重建 LibreOffice core。第一份 host 0.2.34 封包 **df7f6fe14e395638** 已封存，離線零問題、22／22 紅案；原 Writer／viewer 的 page records 相同。宿主快轉 **db5139c**，occ 0.2.34，測試時段只啟動 litecore。這是功能定向測試時段，不是 K／P5。

H-write `findings/evidence/host-0.2.34/host-write-02/report.json` 留下真實紅案：ODS 條件 PUT、鎖、重開、格式、外部改檔與衝突副本內容都正確，**副本已成功但 dirty 仍 true**。新 session 讀 `error.details.outcome`，既有宿主的 `failure()` 實際把 `outcome` 放在頂層。證人 commit **a25eedb0** 先於修法；新增 session 測試先紅，再由 **85ad4e33** 改讀真實契約，保留衝突提示、stranded 仍 dirty。

這不是放寬 §2 的儲存條件，H-write 尚未成立；接續只修正／重包新 session asset，留下第一份 immutable archive，再跑 H-write 全部指定路徑。新引擎不改、W-edit 不重置。第一次宿主工具本身的 DOM 序列化錯誤留在 host-write-01。§34.4 **+0／+0，累計 47／27**：這是新功能與新工具，沒有修理既有判讀。完整 K、既有 counted pins／BINDING／chain 仍未動。

## 7. 實際唯讀分享揭露的路由修正（2026-10-25，只追加）

修正 session 後封包 **d308e0cc58958d85**，45 檔中只改 `spreadsheet-shell/calc-editor-session.js`，前一包保留；離線零問題、22／22 紅案。host-write-03 的 Chrome 可寫路徑 **23 項全過**，包含 Writer 開存、存回副本後再存一次；最後卡在唯讀分享路由，因此不把整份報告說成 clean。

`host-readonly-04/report.json` 與 `entry-failed.png` 是實際證人：OCS 分享權限 1，新帳號由 Files 的 readonly.ods 進到 ods-editor；伺服器解析的 `writable=false` 已讓 UI 禁用編輯與儲存，但未照 §1 保留 viewer 路由。這表示 Files 的 UPDATE 提示不能代替實際檔案權限，不能把 contract unit mock 的 permissions=1 當成真分享驗收。

宿主 **2f3ef60** 在 page render 前，對 ods-editor 的實際 readonly target 導向原 viewer。使用同一次已讀取的 engine 身分建 URL；不改 manifest／引擎，也不改既有 viewer。`host-readonly-05` 的 Chrome 路由、無儲存與無鎖皆成立；該報告後半的 Firefox 未到產品頁（專用 profile 缺開發 CA）。`host-firefox-06` 為 snap Firefox 無法使用 /tmp 的外部 profile；專用 profile 移到本 repo ignored build 目錄、匯入既有開發 CA，失敗建構器自己的 geckodriver 已具名清理。這兩次不是產品紅、不算 Firefox H-write。

接續只完成 Firefox 的可寫／唯讀路徑，Chrome 已成立的路徑不重跑。H-write 全成立前仍不把 0.2.34 當日常候選。§34.4 **+0／+0，累計 47／27**；新功能實作修正，沒有修理既有判讀。

## 8. H-write 成立；候選已安裝，環境已還原（2026-10-25，只追加）

完成的 H-write 分別讀：Chrome 可寫／Writer `host-write-03/report.json` **23 項**，Chrome readonly `host-readonly-05/report.json` **2 項**，Firefox `host-firefox-07/report.json` **27／27**（含兩項 setup，其餘為 23＋2）。前兩份整體失敗維持原樣，只採已完成的具名臂；不把它們重新標成整份 clean。Firefox 確認為 157.0.1；Chrome 宿主臂未獨立記版本，不從另一輪推定。

實際 Files 的鎖正向與無 token PUT 423、ODS MIME／If-Match／帶 token 的原檔 PUT、伺服器 GET／ZIP／XML／重開、格式、外部改檔保留、`.ods` 副本與後續存同副本、readonly 分享 viewer 無寫入口／無鎖，以及 Writer 開存均成立。重讀工具 `python3 wasm_sdk_probe/tools/read_calc_editor_acceptance.py --red-cases` 讀既有產物：原生 171、W-edit 186、兩瀏覽器各 23＋2，零問題；空母體、缺 Firefox、真衝突 dirty 紅案三項都紅。H-write 成立，不新增人工項目。

**0.2.34／host 2f3ef60／package d308e0cc58958d85** 成為已安裝、未計數候選。35 個舊封包檔的完整 record 均相同，十個新路徑；離線 checksum 與 live／隔離 worktree 均對上 immutable archive。引擎 **ods-editor-v1／d5a081f8** 不改；第一次 package 仍獨立封存。沒有重建核心，也不需擁有者補跑本輪連結。

`pre-stop-verification.json` 實讀：所有本輪帳號／folder 已不存在、鎖 file-id 前後皆空、live source 乾淨、版本 0.2.34／package 相符。沒有清整張鎖表；早期 dirty 紅案只 UNLOCK 自己的測試檔。fileId 24920 的擁有者編輯 31,008 B／sha a8462965… 保持相同。停止 litecore 後 `cleanup.json` 比對全部專案狀態一致：litecore stopped，fgp-nc／nc-bridge paused，其餘 stopped。隔離 worktree 核對後移除，分支與全部 archive 留存。

整理見 `research/2026-10-25-cell-editor-v1.md`、英文證據 README 與最終 handoff。K 保持延後併批、名義出貨仍 **0.2.26**；§34.4 **+0／+0，累計 47／27**。本輪沒有剩餘必須人工介入的阻礙；後續由擁有者試用／提出下一批功能，不能自行把 v23 接回來或啟動完整 K。

## 9. 擁有者手測與格式後全白回歸（2026-10-25，只追加；新實測之前）

擁有者原話確認「輸入文字及公式功能符合預期」。另回報雙擊 cell、選取文字後按 B／I／U，編輯區全白、框線與內容消失；關閉重開後格式存在。這撤回先前定向驗收對這條路徑的畫面完整性信心，不撤回已讀到的存檔／模型結果。當時格式測試只驗模型和 XML，缺的是操作後繪圖證據。

本輪先調查本機 `cool-26-04`（HEAD c64a7343a5c6295623619c80aa7857c4e00e1ddd）之直接輸入、雙擊與格式分派，唯讀參考機制、不搬原始碼。新直接輸入、格內部分文字格式不是本次「研究做法」就自行納入實作；v1 仍整格 B／I／U。另依擁有者後續指示核對 Calc 是否自動儲存與 Writer 差異；沒有排程不能宣稱 autosave。

全白問題登錄 finding 165。先在未修的頁面走「單擊選格套格式」與「雙擊選取文字套格式」各個 B／I／U，保留直接 engine cell 值、revision、scheduler context／generation／metrics、畫布數與截圖；單看像素或模型變綠均不足。若臂在首個失敗停下，不把未跑的說成通過。

修正判準 **F165-view**（逐實例）：Chrome／Firefox，各三輪；每一個上列操作後 scheduler context revision 等於 document revision；drain 後同一輪實際送到 DOM 的每塊 tile，其 bytes 與引擎對應 region 直接 render 一致；可見區有 tile，沒有 tile error。並核對 cell 值／格式正確、存成 ODS／重開一致。先保留未修紅案；修後三輪成立就封閉。沒做／失敗：165 維持未修，不升宿主候選。不能把 v1 的舊六輪當作這條新路徑的畫面證據。

本輪先在隔離鏡像修正／定向驗證；不要重連結 frozen ods-editor-v1，不啟動 K。若發佈，沿用隔離宿主 worktree、不可覆寫 archive、先備退路再安裝與定向 Files 驗證；共享環境先實讀，保留擁有者目前測試狀態及全部原文件，不清鎖表、不重問已成立人工項目。§34.4 起點 47／27；新產品回歸工具不自動算既有判讀修理。

## 10. 165 的畫面證人、修法與六輪結果（2026-10-25，只追加）

未修 `165-calc-format-blank/red-01` 六個畫面檢查全紅：第一次 B／inline 為 28 塊 DOM tile、其中 1 塊與同 region 的引擎直接 render 不同；後五次 DOM tile 為 **0**。模型格式全正確，`tileErrors=0`，取消請求未被當成 error，符合擁有者「全白但重開格式存在」的觀察。紅案 commit **b3ccca5c** 先於產品修法。

產品 **4caa253e**：`setFormat` 先 `scheduler.invalidateRevision`，再 `_adopt` 同步 emit；不改共享 scheduler／UI／引擎。新增的 state observer 在未修程式見到 revision 0／1 不一致；修後第一次單元嘗試是在 close 時讀已釋放 scheduler，並非格式操作仍錯，保留 `session-green-attempt-01.txt`，限定 ready callback 後最終 **13／13**。初次 green 檔名不是通過證據，以最終輸出為準。

`green-01/report.json` Chrome／Firefox 各三輪，**90／90**，36 份格式後 snapshot／**936** 塊 DOM tile 逐位元組對比引擎同 region，全部一致；cell model、下載、重開也正確。另直接讀六份下載 ODS 的 B2 XML，文字及三格式關閉與預期相符（`saved-xml-read.json`）。`read_calc_format_view.py` 重讀綠案零問題，讀紅案會因真實 stale／empty 拒絕；不允許空集合通過。**F165-view 在第三筆成立後封閉**，不再為放心多跑。

接續 host **0.2.35／858a07c**、package **b007f950b2e18cd2**：45 個檔案 record 中 **44 個相同**，只改新 spreadsheet session；profile／worker／wasm、Writer 與唯讀 viewer 都不變。離線零問題、22／22 紅案、archive／checksum／rollback 先備；12:17:59–12:18:08 安裝成功，maintenance disabled，三路由未登入 401。這輪最初 litecore 已 running（擁有者手測後），測完應保留 running，其他專案不變。原有 fileId **24674** 的鎖列已先記錄，禁止清除；本輪只操作新建的測試資料。

自動儲存目前仍只做**差異核對**：Calc 沒有 Writer 的排程，不能因有未存提醒／共用 host 而宣稱已對齊。已提出可選範圍澄清，在沒有追加實作指示前不把新的 autosave 行為併入 165 修法。source 分析與差異表見 `research/2026-10-25-collabora-calc-input-format-autosave.md`。§34.4 **+0／+0，累計 47／27**，K 維持併批。

## 11. 165 宿主驗證成立；保留原先 running 狀態（2026-10-25，只追加）

`findings/evidence/host-0.2.35/format-host-01/report.json` **24／24**：Chrome／Firefox 各一輪實際 Files 開啟；B／I／U × inline／cell 共 12 份畫面、**336 塊 tile** 逐位元組對比同 region 的引擎 render；手動存回、伺服器 ODS XML、自己鎖的正常釋放皆成立。這是 165 的定向宿主驗證，沒有重跑 Writer／唯讀 viewer 的已成立觀察或完整 K。

自動儲存實際觀察：兩瀏覽器各完成一個修改後，**35,021 ms** 無操作，host saves 清單前後皆空，dirty 仍 true；接著 manual save 成功，伺服器 XML 含該修改。這只證明指定 35 秒內沒有自動存，不從等待推論永遠不存；「Calc 沒有排程」另由完整產品頁入口與 Writer 差異原始碼確立。本輪沒有新增 autosave，仍 manual only。

`python3 findings/evidence/host-0.2.35/read-result.py` 讀既有產物與 XML／snapshot／實際 ddev 狀態紀錄，全部成立；空 host checks 與 false check 兩個紅案均拒絕。`post-test-identity.json` 實讀 live source 乾淨、installed 0.2.35、package **b007f950b2e18cd2** 等於封存，原有 **24674** 鎖列前後相同、測試帳號／folder 已不存在。`cleanup.json` 全專案狀態前後一致，**litecore 保留 running**；沒有清鎖表或停止別的專案。隔離 worktree 核對 source／archive 後移除，分支與 archive 保留。

**finding 165 已修，0.2.35 成為已安裝未計數候選。**不需重連結 SDK／核心；ods-editor-v1 與全部舊 profile 身分不變。K 延後併批、名義出貨 0.2.26；§34.4 +0／+0，累計 47／27。擁有者本輪確認文字／公式符合預期已記錄；沒有把 0.2.35 的格式修法說成已由擁有者手測，也不新增人工閘門。

## 12. 擁有者人工結果與下一批輸入／選取需求（2026-10-25，只追加）

擁有者完成手測並明確回報：**「B／I／U 整格套用 => 測試通過」**、**「雙擊：保留原內容，進入文字編輯 => 測試通過」**；這兩項人類觀察成立，與先前文字／公式輸入的通過一起保留，不再重問。原話在 `findings/evidence/host-0.2.35/owner-test-2026-10-25/confirmation.md`。這是 0.2.35 安裝／研究之後的回覆；擁有者沒有另報 browser／版本／served 身分，不由本次離線 checkout 讀取替代當時的瀏覽器身分。

「選格後直接打字，F2 進入文字編輯 => 沒反應」符合本版尚未接線的事實。上一份說明是在描述 Collabora 的行為，不能把它當本版已提供；下一批須補上這兩個預期入口，不能把沒有實作只登錄成不需處理的回歸。新要求 **「區域選取」** 續入下一批，語境是試算表 cell range，與 textarea 內文字反白／部分文字格式分開。

本輪依指示只寫交接、記錄結果；沒有新增這些功能、凍結新功能判準或啟動建置／瀏覽器／ddev。下一輪先定義並事前記錄直接輸入、F2、矩形選區的語意與驗收，再實作。滑鼠拖拉、Shift 擴選、對選區套格式等細節是待具體化的實作規劃，不冒充本次已逐項指定的條件。既有 frozen ods-editor-v1 不覆寫；若 range mutation 要新增 API，另立後繼身分。

Calc 仍 manual only，沒有新增 autosave；先前可選範圍問題未獲追加實作回答，不把這則區域選取要求推定為 autosave 授權。K 繼續併批、名義出貨 0.2.26，§34.4 +0／+0，累計 47／27。

## 13. 直接輸入與 F2 的事前判準（2026-10-25，只追加）

依 §12 的未實作回報，本批先補入口：選格後打字建立空白的替換草稿（尚未 Enter 不改模型）；F2 與既有雙擊保留 cell.input，游標在尾端。Escape 還原並不增加 revision；Enter 提交。IME 組字中 Enter／Escape 不得提交或取消，組字結束後仍等一次明確 Enter。公式欄／位址欄維持自己的輸入，Ctrl／Meta／Alt 快捷鍵不當新內容；AltGraph 文字可經 beforeinput 輸入。純文字以既有 apostrophe-safe input 契約寫入；不新增格內 rich text、貼上多格或 autosave。

輸入焦點屬於同一個原地 textarea：未編輯時是貼近可見區的輸入接收點，beforeinput／compositionstart 才轉成原地編輯，避免第一字、IME 預編輯內容或焦點轉移遺失。唯讀／保護格拒絕新草稿。選格和切表提交既有草稿；失敗則保留原草稿與原選格，不帶著未提交內容改目標。此批不更動 frozen profile。

**I-entry**（逐實例）：新 session 狀態案例與 Chrome／Firefox 真實鍵盤路徑各 N＝3；每次涵蓋替換非空白格、F2 保留文字與公式、Escape 不寫、Enter 寫入、字首 apostrophe literal、組字期間不提交、公式／A1 欄的焦點隔離、唯讀／保護拒絕。每筆已提交修改下載 ODS 後獨立讀 XML 並重開；鄰格／別表不變。每份新 revision 後畫面須有可見 tile，DOM tile 與同 region 的直接 engine render bytes 一致。先保留目前未實作頁面的實際紅案；三筆全成立即封閉。未做／失敗：入口不列完成、不升宿主候選。自動送入的 composition 事件只算事件守衛，不冒稱實際 OS 輸入法；另記能實際驅動的預編輯路徑與限制。

區域選取的語意與判準將於該部分實作／驗收之前另行追加；Astra 已獲擁有者裁決授權，agent `/root/astra_calc_scope` 保留供續問。K／全域 pins／BINDING／chain 不動。既有人工已通過項目不重問。

## 14. Astra 裁決的矩形選取範圍（2026-10-25，只追加）

依擁有者明確授權，Astra `/root/astra_calc_scope` 作成 [裁決](../handoff/RULING-2026-10-25-calc-input-range.md)：本批以既有 v1 完成直接輸入／F2 與選取，不擴成 native 任意範圍格式。**多格選取時工具列、快捷鍵、session B／I／U 都拒絕且不寫入**，畫面說明原因；開始打字／F2 則收合至 active cell，僅編輯該格。不冒稱部分文字格式、原子範圍寫入或 autosave。

選區獨立保存 active／anchor／focus。單擊收合、滑鼠拖曳／Shift-click／Shift＋四方向擴縮，無 Shift 四方向從 focus 移到下一個可見格並收合；文字編輯中的方向鍵仍編輯文字。切表清選區並選新表 A1。範圍標籤顯示地址與 active cell。沒有拖曳自動捲動；拖出 viewport 保留最後有效點，可自行捲動再延伸。pointercancel／失焦終止拖曳，遲到結果不能復活舊手勢。

合併政策是**地址矩形**：端點依 engine snapshot 的 merged origin／endColumn／endRow 正規化，矩形含端點 merged extent，其他交界合併格不連鎖擴張。視覺包絡使用兩端真實 cursor twips；不宣稱 Calc 的完整 merge closure，未來範圍寫入必須另立契約。隱藏索引仍在地址矩形內但不捏造面積；導覽用 focus 邊緣外的 hitCell 找可見格，不逐一掃隱藏索引。幾何拒絕／越界時保留選取並提示。每次移動／延伸最多一次 readCell 或 hitCell，與面積無關；不可由被讀取操作改動的 engine cursor 推導寫入目標。

**R-select**（工具封閉枚舉）：新 runner 自 fixture case manifest 產生四向 mouse／Shift、縮回、Shift-click、普通方向收合、變寬高、merged endpoints／interior boundary、連續 hidden rows／columns、跨 sheet、取消及延遲反向操作；Chrome／Firefox 各 N＝3。每份報告記完整 case id 集合、selection/active 與 overlay twips 對照 engine endpoints，並量 SDK call count；多格每種格式的所有入口拒絕且 revision／原內容／鄰格／別表不變。session 測試另包含巨大地址矩形與延遲回覆，空 case／缺 case 的 reader 必須紅。先留下未實作的真實 mouse／Shift 紅案；第三筆成立後封閉。沒做／失敗：區域選取未成立、不升宿主候選。I-entry／R-select 皆成立後才打包並跑雙瀏覽器實際 Files 的新路徑／手動存回／正常釋放自有鎖，保留原專案狀態與既有 24674 鎖；K 不啟動。

## 15. 選格等待與可見性紅案逼出的補充（2026-10-25，只追加）

Astra 覆核指出 selection busy 會停用唯一接收器；`pending-entry-red` 已以 600 ms hit 回覆延遲重現點格後第一筆文字遺失。`pending-entry-green-01` 的 Chrome 又揭露暫存草稿過早交給 session：pointer pump 隨後提交它，未按 Enter 就改模型。兩個失敗原樣保留。故輸入意圖須等待該手勢的端點佇列完整結束，再建立新目標的 replacement／F2 草稿；期間同一 textarea 持續接收文字／組字，不可改投舊格或被 render 清除。Enter 排在輸入後、Escape 清除暫存且不寫；選格失敗／取消則保留未寫文字並提示取消。暫存輸入未處理完時的新選格／切表／位址跳轉以等待提示拒絕，不讓它換寫入目標。儲存先等選格、接回草稿再提交；換檔沿未存確認，明確捨棄才清掉暫存。

方向鍵須以 engine focus 幾何最小幅度捲動使其可見；開始編輯則顯示 active anchor。手動捲動重新定位 idle sink。繪圖在途的新 viewport 要補畫最新需求；不改共享 scheduler。手勢捕獲其 owner session，起點失敗不得從舊 anchor 擴選，pointerup 採最後有效座標，取消釋放 capture，換檔前取消舊手勢。上／左邊界的普通方向鍵收合到 focus，Shift 則不動。

上述均是 §13／14 的先前語意尚未被完整守住，新增固定的等待文字＋Enter／F2／F2 後文字／IME／Escape／再選格、鍵盤可見性與手勢生命週期案例，從 fixture manifest 讀母體，未測則未成立。本節先於可算入的新 N＝3；先前單輪 attempt 皆屬開發觀察，不挪作完成計數。沒有重設已封閉的 165／既有 cell 驗收，也不新增人工閘門。

## 16. 本批定向驗收與安裝成立（2026-10-25，只追加）

`calc-input-range/final-02/report.json` Chrome／Firefox 各三輪 **378／378**；每輪 63 項，十二份新輸入畫面／312 塊 DOM tile 比對直接 engine render 全相同，下載 ODS 的獨立 XML／重開、鄰格／別表均成立。reader 自可執行 check call sites 與 fixture 生成母體，核對來源／工具身分及確切集合；空 runs、缺瀏覽器、空 checks、缺項、false check、錯工具身分六個紅控制均拒絕。`pending-validation-05` 過長／保護／選格失敗後的拒絕、舊草稿前綴及拒絕 Save 後 Escape 每瀏覽器 **8／8**；session／SDK／host contract **22／22**，E1-C intact。

Astra `/root/astra_calc_scope` 在完整呼叫鏈覆核後裁決有限範圍可封閉；Claude 協定及片段審核原文與處置保留。一般 cell commit 等待時 textarea 停用所造成的按鍵接收限制屬既有、未量測的後續工作，不宣稱任意延遲下連續輸入已成立；不因片段審核的條件假設（save 不提交草稿／成功選格不清錯誤，兩者實際都做）重開本輪。Firefox 組字為合成生命週期守衛，Chrome 為 CDP 預編輯；均非 OS 輸入法證明。

宿主 **0.2.36／702bad6／package 2b17a0e790b24eb3** 已安裝，實際 Files 雙瀏覽器 **28／28**，兩份新輸入畫面／56 塊 tile 與引擎一致，手動存回、伺服器 XML 及自有鎖正常釋放成立。45 個封包檔的 42 筆完整前版紀錄相同，只改 Calc HTML／app／session。凍結 Calc v1、Writer v22、viewer v3 不改，不需重連結；離線零問題、22 個紅案全拒絕。原有 24674 鎖、24920 文件與所有專案狀態相同，litecore 留 running；測試資源與隔離 worktree 清完，分支／archive／rollback 保留。詳見[功能整理](../research/2026-10-25-calc-input-range.md)與[宿主證據](../findings/evidence/host-0.2.36/README.md)。I-entry／R-select 於本輪第三筆成立後封閉，無新增人工閘門。K／全域 pins／BINDING／chain 仍延後，名義出貨 0.2.26；§34.4 +0／+0，累計 47／27。

## 17. 多格格式與已確認修改的自動儲存（2026-10-25，只追加）

擁有者已回報前批人工驗收通過，並明確要求下一批「多格 B／I／U 與自動儲存」。由 Astra `/root/astra_calc_scope` 裁決，詳見 `handoff/RULING-2026-10-25-calc-range-autosave.md`。本節新增後繼能力，不撤銷 frozen v1 或前批人工通過紀錄；本批尚未量測的 native 能力不得宣稱交付。

範圍格式以明確 part、起訖索引、expectedRevision、format、enabled 呼叫一次 native `XMultiPropertySet`，三字族在同一個 pattern 套用。每次最多 65,536 個邏輯格，含隱藏／空白格；畫面仍可選更大的範圍，但操作拒絕。不用逐格 writes 冒充原子操作。跨越合併邊界的矩形整筆拒絕，不自動擴大目標；完整包含的合併格可套用。保護表僅接受 aggregate `CellProtection` 可證為一致且 unlocked，混合或 locked 整筆拒絕；這可能保守拒絕 IsLocked 皆 false 但其他保護欄位不同的範圍。已知拒絕不得改模型／revision；進入 native 寫入後的例外／無法驗回結果一律 uncertain，不宣稱 crash rollback，不自動重試。

多格格式狀態 true／false／null 分別是全開／全關／混合，混合按下設為全開，全開按下設為全關，三字族一起處理。成功後保留 active anchor 和範圍；先 invalidate 再 emit，並重新讀取兩端幾何。新 capability 為 `cell-range-formatting`，只在後繼 ods-editor-v2 出現；原 v1 不覆寫，仍拒絕多格格式。本節對多格選取增加一次固定的 range metadata read，取代 §14「每次至多一次 read/hit」對後繼的字面限制；原因是混合／保護／合併邊界不能由單格幾何證明。查詢與寫入呼叫次數均不隨面積增加。

自動儲存僅在 HOST 存在時啟用，存已確認進模型的修改：閒置 30 秒，dirty 上限 5 分鐘後仍需 3 秒 quiet，隱藏時符合條件可立即嘗試。不強制提交 active draft／IME；畫面標示「確認後自動儲存」。editing、composing、pendingEntry、selectionPending、drag、busy／saving、manual pending、uncertain、error 時延後。`committedDirty` 不含純草稿，automatic 呼叫 `save(...,{commitDraft:false})`，手動預設仍先提交草稿。匯出／host write 期間的新草稿不可被完成的儲存清掉。copy／stranded／其他失敗後停自動重試；成功手動存回 original 才恢復，sticky copy target 持續暫停。host 繼續負責版本／鎖／副本／stranded 與離開保護，不新增 unload 非同步完成保證。

**R-format**（工具封閉枚舉）：由新範圍 fixture 的 format 與 case manifest 產生所有 B／I／U × 成功／混合切換／冪等／保護拒絕／合併拒絕、隱藏包含、明確目標、stale revision、超限案例。Chrome／Firefox 各 N＝3，保存 profile／工具／fixture 身分與每個 case id；每種格式檢查 Latin／Asian／Complex（適用者），已知拒絕 revision 不變，成功最多一次模型 revision，鄰格／別表內容和格式不變。匯出 ODS 獨立讀 XML 並重開，實際 DOM tiles 對 direct engine bytes，不以模型綠燈替代畫面。SDK/session 突變紅案先證明 cap、v1 gate、回覆目標、一次明確 range 寫入與 uncertain 失敗路徑檢查會拒絕。未做／失敗：範圍格式未成立，不凍結或安裝 v2。

**A-save**（工具封閉枚舉）：clock tests 覆蓋 idle／cap+quiet／hidden／blocked／clean／readonly／single-flight／dispose、錯誤暫停與手動恢復，並用突變確認守衛有效；Chrome／Firefox 各 N＝3 使用真實 30 秒 idle 與既有輸入／engine／ODS 匯出，固定覆蓋 draft不強制、匯出中新打字、copy／stranded 暫停／手動 retry、XML／鄰格。host double 只證明頁面契約，不冒稱 WebDAV；完成 v2 建置後另跑實際 Files 雙瀏覽器的 auto trigger／原檔內容／自有鎖釋放，保持原有文件／鎖／服務狀態。各 reader 必須拒絕空集合、缺 case、false、錯工具／profile 身分；未做／失敗：對應層自動儲存驗收未成立。

每項 N＝3 的第三筆有效執行完成後封閉；之後的疑慮登錄為 finding／後續工作，不能無限加閘門。新 native 尚未建置時只完成可審閱來源與精確 build/runbook，不把舊 v1 實測算成 v2 證據。依本次 standing instruction，會編譯的命令交使用者，不援引舊 session 授權；不跑 root／K、不改全域 pins／BINDING／chain。安裝維持 0.2.36，待 combined v2 實測後才切換候選。

## 18. 位址欄輸入被狀態通知覆寫（2026-10-25，只追加）

`auto-final-03` Firefox 第三輪與等待公開 ready 後的 `auto-final-04` Chrome 第一輪，均在零個 autosave case 的 B2 定位前置停住，仍為 A1／revision 0／無 session error。因此撤回「只等 ready 就能解釋前次失敗」的推論，不改稱純工具問題。Astra 裁決以固定案例直接驗 render：聚焦位址欄、設入 B2、發送既有 session 狀態通知，內容必須保留；失焦後才依實際 active cell 正規化。Enter 沿既有選格流程，沒有新啟動架構。

本案在正式可計數執行前先留固定紅案，再修 focused render／blur；新增 `focused-address-keeps-input` 到既有 runner 的可執行 case 母體，reader 自動納入，未做／失敗則本案未成立。本輪尚無完整 N＝3 成立，修後重新開始雙瀏覽器各三輪，之前成功不拼湊計數。若固定紅案不成立或修後同症狀仍出現，停止沿此歸因擴張，改以明確 session 選格作 autosave fixture 前置，將起始互動另案登錄；這是有截止的裁決，不是「跑到看起來穩定」。

## 19. 自動儲存鏡像層成立，後繼引擎待使用者建置（2026-10-25，只追加）

`calc-range-autosave/auto-final-05` Chrome／Firefox 各 N＝3，18 案／輪，**108／108**。包含 focused address 回歸、真實 30 秒閒置、草稿不強制提交、匯出中新打字與焦點保留、copy／stranded 暫停及手動恢復，十八份 ODS 的獨立 XML／鄰格核對。artifact reader 自 runner 可執行 call sites 生成母體，核對工具與來源身分、ODS hash／XML；空 runs、缺瀏覽器、空 checks、缺項、false、錯工具六個紅控制全拒絕。先前失敗與未完成輪數均未拼入。

session／SDK／worker／host／autosave 單元 **45／45**；autosave 七個突變、range 六個突變、range reader 五個合成紅案與兩個 frozen profile 保護控制均拒絕，E1-C intact。Astra `/root/astra_calc_scope` 讀取 reader 結果後裁決鏡像層與來源準備可封閉，不再擴本輪閘門。Claude 03 完整審核與逐項處置、其餘逾時無 verdict 紀錄均保留。

以上使用真實凍結 v1 引擎與可控制的 HOST 替身，**不證明 native／v2 範圍格式、實際 Files 存回或新候選安裝**。這三層仍為 NOT_ESTABLISHED。來源、native 22 案及 browser 40 案／輪的續跑工具、精確 build／runbook 已完成，會編譯的命令依擁有者規則交使用者。未編譯、未重連結、未動 ddev／原文件／鎖、未凍結 v2、未打包安裝；現有宿主 0.2.36 與既有三顆 frozen profile 身分相同。K／全域 pins／BINDING／chain／計數不動，名義出貨 0.2.26，§34.4 累計 47／27。下一步是 [使用者建置](../handoff/RUNBOOK-build-calc-range-v2.md)，成功後由 agent 繼續實測及候選流程。

## 20. Combined 候選的實際 Files 有限驗收（2026-10-25，只追加）

擁有者已執行小型 native／後繼 SDK 建置；本節只釘實際 Files 層的新入口判準，不把鏡像 HOST 替身當成 WebDAV 證據，也不重跑既有完整衝突／stranded／Writer／K 閘門。使用 probe_calc_range_autosave_host.py，Chrome／Firefox 各一個管理者自有 fixture 加既有唯讀分享 route。case 母體由 driver 及實際繼承的 Harness run／readonly_round 可執行 check call sites 生成，reader 拒絕空／缺項／重複／false／缺 browser-route／錯工具／錯 package 身分。

每種 B／I／U 真工具列建立單格開啟＋鄰格關閉，再 Shift 擴選，驗 mixed → on → off，最後保留全開；作用目標仍為 B2:C2。確認新的模型 revision 與實際 tiles 對 direct render 一致。提交標記文字後等待 production 30 秒 idle，自動存回 original；driver 在 commit 完成後才取起始時間，因此 host 層採 29–55 秒完成窗，精確不少於 30 秒的排程性質仍由已封閉鏡像與 clock 層承載。實際 PUT 必須有 If-Match／自有 lock token／ODS MIME，host 紀錄 trigger=auto、outcome=saved、target=original。

獨立 GET 並保留伺服器 ODS bytes／hash，依 ODF cell、row／column defaults、named parent 及 family defaults 解析有效格式，核對 B2/C2 三字族格式、標記文字、範圍外 A2 與別表 A1 不變，不只相信 host success。active replacement draft 保持超過 30 秒不得新增保存或變模型；一次受控延後的真 native export 期間以 trusted input 打入新草稿，存回 XML 只能是先前已確認值，新草稿／焦點／dirty 必須保留。取消新草稿後回到已儲存，正常離開釋放自有 lock，再由 Files 重開讀回格式／內容並正常釋放。readonly 分享沿既有實際 viewer 路由，無 save API／按鈕且不持鎖；不要求另等 30 秒。

這個 driver 只建立與清除自己的 folder／user／share／lock token，不改服務狀態、不寫全域 lock table。呼叫方提供本次 fresh ddev-before/after.json、locks-before/after.txt 與 owner-document-before/after.json；reader 核對 service 狀態完全一致、既有 24674 lock 保留、24920 文件 bytes/hash 身分相同。正常成功不容許依賴 fallback UNLOCK；失敗仍由既有 Harness 清理自有 token，且失敗不算通過。未做／失敗：實際 Files 層未成立，不宣告 combined 交付；雙瀏覽器固定集合全部成立即封閉，後續新疑慮另案，不無限新增門檻。

## 21. 忙碌快捷鍵旁路與新候選重播（2026-10-25，只追加）

Claude successor review 05 的兩個原始 repro 以 selection 不經佇列為前提，完整 source chain 不支持該前提；但 Astra 追查實際 window Ctrl+B／I／U 路徑，發現它未遵守工具列 busy 限制，會先依舊格算 enabled，再在 queued selection 之後套用。source-chain 紅案 `shortcut-queued-selection-source-red.json` 使用實際 page toggleFormat 與 CalcEditorSession、fake engine／held host：A1 非粗體，排入 E5（已粗體）選取後按快捷鍵，結果 E5 被設 true。這是有明確來源的缺陷，不把它誤稱原 reviewer 的直接 typing 資料遺失已成立。

有限修正為工具列及快捷鍵共用 eligibility；ready／cell writable／非 readOnly／非 uncertain，且無 busy／selectionPending／pendingEntry／dragWork，範圍另需支援與 writable metadata。drag 完成／取消要刷新工具列。focused tests 必須執行實際來源函式，涵蓋這些條件的工具封閉案例、有效 mixed→on／on→off，以及 actual session 的 queued-selection 紅案修後不排入格式。移除共同入口守衛與各 predicate 的突變須被拒絕；未做或失敗不成立。

這是新 JS 候選，既有 range 240／autosave 108 的完成 cohorts 原樣保留，不能把新 hash 填回舊報告。修後對新候選各重播一次既有固定 Chrome／Firefox N＝3 母體（range 40／autosave 18，不新增案例），現有 reader 必須通過；native 22 未改不用重建。之後依既定 cell regression／freeze／package／guarded install／§20 host 54 繼續。新候選重播與 host reader 全過即封閉，不繼續擴 source audit；後續顧慮登錄 finding，除非另有具體資料遺失 blocker。

## 22. 多格格式與自動儲存交付成立（2026-10-25，只追加）

擁有者完成 native／WASM 建置，六份 v2 產物 hash 與回報逐一相同，capability bits 522291。native 22／22；§21 的新頁面候選 `range-browser-03` Chrome／Firefox 各 N＝3 **240／240**，六份畫面／156 塊實際 DOM tiles 對引擎相同，ODS 三字族 XML／重開成立；`auto-v2-02` 同母體各 N＝3 **108／108**、18 份 ODS；`cell-v2-02` **62／62**。新 cohort 原樣保存，不借用之前 hash／成功輪數。range 與 autosave reader 各六個紅控制全拒絕；range reader 也直接把匯出樣式改壞再拒絕。59 個來源單元、4 個獨立 XML 單元、格式入口 15 個工具衍生突變成立。XML 工具初次誤以為每格需 cell-local style-name 的六輪失敗保留，改正的是讀取 ODF 欄預設／parent 樣式的方法，沒有改格式期望。

`ods-editor-v2` 以使用者建置的完整六份 bytes 凍結一次，wasm **5bc53490**／worker **0bed22bd**；v1／Writer v22／viewer v3 不覆寫。宿主 **0.2.37／2f7a119／754ae8eafd15edda** 已於 20:06:22 安裝。46 個封包檔的 35 筆完整紀錄與前版相同；離線零問題、22 個紅案全拒絕，精確 archive／還原腳本先於 live mutation 準備並提交。代理只跑資產 cp target，未代編譯或重連結；沒有核心重建。

§20 實際 Files **54／54**，宿主 reader 七個紅控制全拒絕，四份獨立 GET 伺服器 ODS／兩份畫面 56 塊 tiles、production 自動存回、If-Match／自有 token／ODS MIME、31 秒不強制草稿、真匯出期間新輸入／焦點／dirty、正常離頁放鎖與 Files 重開、readonly 分享均成立。自有 folder／share／user 刪除完成且另查 folder 404／user absent，沒有 fallback UNLOCK。24674 lock 原樣保留；24920 文件仍 31,008 bytes／sha256 a8462965…；ddev 前後狀態相同，litecore 留 running。live engine／archive／隔離 worktree 逐檔相同，worktree 已清、branch／archive 保留。沒有全域 lock table 寫入或 root 指令。

Astra `/root/astra_calc_scope` 獨立讀取 release、host reader 與保留產物後裁決本輪正式封閉，不再新增測試／閘門。Claude successor review 05 引出的真實 shortcut 旁路、已修與不成立前提均保留完整處置。這批短期待辦完成，沒有剩餘人工／建置阻擋；普通 cell commit 等待期間的既有連續按鍵接收限制、OS IME 等仍不外推。K／全域 pins／BINDING／chain 延後，名義出貨 0.2.26；§34.4 +0／+0，累計 47／27。最新狀態見 [完成交接](../handoff/HANDOFF-2026-10-25-calc-range-autosave-complete.md)。

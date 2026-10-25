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

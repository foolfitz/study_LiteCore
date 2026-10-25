# 計數耗時、併批與後續工作（2026-10-25）

## 結論與這次的範圍

**完整計數 K 約需一個晚上，可以等更多更新完成後一起跑。**這符合 [v22 規格 §13](../specs/SPEC-M3-link-batch-v22.md#13-擁有者的兩個決定2026-10-19只追加) 已有的決定：K、最終 re-pin、merge `BINDING` 與 chain／reader 一起延後，避免在候選還會變動時重綁。

擁有者本次問：「再來好像要計數，會很久嗎？很久的話，能不能等更新多一點再一起跑計數？」本次沿用併批，沒有啟動 K 或建立計數時段。各項更新自己的定向驗收照原規格執行，完成後仍列為未計數候選；併批不會把尚未量的項目變成通過。

## 歷史耗時：讀既有日誌，沒有新跑量測

〔已觀察：既有產物〕最近成立的是 **0.2.26／editor v21** 的計數。原始日誌 [chain-20261018T160539Z.out](../findings/evidence/m3-production-ui/runs-0.2.26/chain-20261018T160539Z.out) 第 3 行 `START` 為 `2026-10-18T16:06:36Z`，第 133 行 `DONE` 為 `2026-10-18T23:55:16Z`，相差 **7 小時 48 分 40 秒**（台灣時間 10 月 19 日 00:06:36–07:55:16）。檔名的 16:05:39 是較早的啟動識別，不能拿來替代 `START`。該檔 sha256：`1bd79f7a9bf9b181e6d56f589e69ab6d67c0c5467607a15a416e8968a20dce78`。

下表是依日誌中相鄰階段起點相減的一次性統計；包含階段間的紀錄等開銷，不是 runner 的硬性時間門檻。最後一段到 `DONE`，總和等於上述時間。

| 階段 | UTC 起點／日誌行 | 到下一階段 |
| --- | --- | --- |
| START、shakedown | 16:06:36／3 | 1:16:49 |
| production UI | 17:23:25／30 | 0:27:33 |
| 六支 M3 counted runner | 17:50:58／37 | 2:21:27 |
| autosave | 20:12:25／55 | 1:18:28 |
| new-document | 21:30:53／58 | 0:02:43 |
| product-path | 21:33:36／60 | 1:17:27 |
| merge | 22:51:03／85 | 0:51:02 |
| C2 三輪與收尾 | 23:42:05／122 | 0:13:11 |

〔估計〕舊 chain 檔頭估 **7.5–9.5 小時**，0.2.24 實跑約 8 小時，與本次重算相符。下一輪可先預留 **8–9.5 小時**；這不是新候選的實測，也不含後續判讀、修復紅項、未來功能自己的驗收或編譯／連結。v23 若合批，須在最終 chain 定案時重估，不能保證仍在此範圍。

## 目前身分與已完成的驗收

〔已觀察：本次離線讀檔〕宿主 repo 乾淨，HEAD `4f7f870bb44e703e101148f143f174c7facee5c9`；磁碟上 package `a67beefefebe57d6`，manifest sha256 `df00baa21ffb760f1f0fe30bd9e04592a11946ae3f8a73b0c787b8fe7ea9c291`。兩份頁面在 `web/`、`dist/`、宿主 gzip 解碼與封存 gzip 解碼四處逐一雜湊相同：

- editor：`3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2`。
- viewer：`6d75f25a8fa75115265b5bd19c6bc20a87af05df38aef47dc30bf6979c286c29`。

〔既有驗收〕[目前 release 狀態](../findings/evidence/host-0.2.33/release.json) 與 [擁有者驗收交接](../handoff/HANDOFF-2026-10-25-editor-owner-acceptance-holds-stopped.md) 記錄：

- 已安裝 **0.2.33**，editor **e2-editor-v22／f7a40bcc**、viewer **ods-viewer-v3／ebb7e0cb**；仍未計數，名義出貨版本仍 **0.2.26**。
- ODS Phase H 含 H7、V3-SEE，以及編輯器 F3-hand、Home／End 邊界、對話框外觀均已完成；不再要求擁有者重做。
- PH 前提已修並有證人、紅案及實際雙瀏覽器結果，不重做修法。完整 `test-e2-c-static` 並未由這些結果替代。
- 上次 slot 已停止 litecore；本次沒有呼叫 ddev，也沒有重新觀察容器狀態。保留 fileId 24920 的擁有者編輯，不用歷史原始 fixture 覆蓋。

## 留給下一輪 K 的變更帳

下列是截至本次整理、供紅項歸因的一次性變更帳，**不是宣稱封閉的影響面清單，也不是新增閘門**。新更新應依自己的產物續記；K 真正綁定時仍要讀最終候選與實際參與工具。

| 已累積的單位 | 候選中的內容／既有證據 |
| --- | --- |
| editor v22 | pthread 預設堆疊 64 KiB → 1 MiB；[v22 規格](../specs/SPEC-M3-link-batch-v22.md) §10／§10.1 的連結、C1、H1；不是指令保序修法 |
| 編輯器頁與殼層 v75 | Markdown 入口重新開啟、152 的 blur／focus 修法、154 的頁面規則；同規格 §11，最終人工結果 §16 |
| host 0.2.27／0.2.28 | v22 封包與對話框隱藏／置中處理；同規格 §13／§14，155 的宿主驗收 |
| ODS 入口與 host 0.2.29–0.2.31 | schema 3 的雙頁面封包、Files 檢視入口、161 的 module 路徑與 162 的 scopedStyle 修法；[0.2.29 證據](../findings/evidence/host-0.2.29/README.md) 含三版的實際安裝與 Phase H |
| viewer v2／host 0.2.32 | part-info／隱藏表處理、Calc add-in bridge、160 的未派送 SelectAll 重送與殼層整合；[v2 規格](../specs/SPEC-M4-viewer-v2.md)、[0.2.32 封包差異](../findings/evidence/host-0.2.32/README.md) |
| viewer v3／host 0.2.33 | dba／dbahsql 核心與表單控制項；[v3 規格](../specs/SPEC-M4-viewer-v3.md) 的 K3、Phase E 三趟、V3-SEE 與 Phase H；editor closure 與 0.2.32 相同 |
| 計數相關工具 | schema 3／資產檢查與 package buildId 的既有更新，以及 PH modal 普查修法 `e704efee`；完整舊 pins／merge BINDING 尚未改綁，見 [既有 snapshot](../findings/evidence/host-0.2.33/count-preparation-2026-10-25/binding-inventory.json)（該 snapshot 自己也明載不是完整普查） |

v23 目前只有前置研究、模型與未接線的工具，不列作已安裝行為。finding 164／`L-E6-leak-sbrk` 仍是限制；ODS 驗收不代表洩漏已排除。

## 併批期間與最後執行的分工

1. **現在**：繼續新增功能或修法，先有各自判準與定向驗收；記錄未計數帳。不因每個宿主版號增加而跑一次完整 K。
2. **候選定案時**：依最終頁面、HTML、profile、session／shell、宿主與 package 身分重綁；沿舊 `repin_0226.py` 查起，但不能把它的 11 檔視為永遠完整。更新 merge `BINDING`，另建當批 chain／reader 及 product-path 判讀輸入，不直接執行 0.2.26 舊鏈。
3. **排程時**：沿用 [J-a／J-b 裁決](../handoff/RULING-2026-10-15-pre-binding.md)。P5 的具名時段與期間不開站約定仍需成立；這次問題沒有給起訖時間。沿既有規則協調共享 ddev、計時環境與不編譯核心的時段，不替擁有者關閉桌面瀏覽器。
4. **啟動前**：保留 P0–P6、PH 與既有紅案要求。`make test-e2-c-static` 會編譯 C++ model（`Makefile` 的 `HOST_CXX` recipe），chain 和 runner 內部也會叫它；須交擁有者執行，或取得明講「幫我建置」的授權並先檢查負載／其他建置。不能把 `--preflight-only` 當成純讀取而直接代跑。
5. **完成後**：依 J-a.2／J-b.2 讀各 counted verdict、紅案、身分、product-path、R spans、C2 三輪與至多一次延伸。`DONE` 本身不等於 K 成立。若一直不跑，0.2.33 與後續合批版本就維持未計數候選，名義出貨不前移。

既有 runner 會清整張 app-lock 表；本次沒有執行它們。未來 P5 若讀到鎖列，應先保存實際明細與判讀，不沿用上次未留明細的 22 列作為可清除依據。

## 下一批建議：接回 v23 指令保序

ODS 的優先工作已完成，現有可接續的功能批次是 **v23：指令保序、Shift＋方向鍵、範圍上的方向鍵**。它直接處理 finding 137 等已登錄問題；把 v22／ODS 累積更新與 v23 最終候選一起 K，是既有 [v23 規格 §9.4](../specs/SPEC-M3-ordered-commands.md#94-計數) 的安排。

接續來源是 [v23 暫停交接](../handoff/HANDOFF-2026-10-20e-v23-paused-ruling-3-spreadsheets-first.md) 的「what remains when it resumes」，以 append-only 的規格 §16 為準：先補診斷工具的 wasm 字節檢查與 feature 模式紅案，再釘 native RESET 還原臂、N＝5；其餘紅案完成後才接引擎與診斷 Makefile，連結仍交擁有者。現行 editor 的 headless core 不因 viewer 換 core 而自動取得 a11y。

**這是後續功能建議，尚未由本次詢問推定為擁有者的新選擇。**本次只完成離線耗時核對、變更帳與併批接續整理，沒有重新開始 v23 實作或驗收。

## 本次驗證與帳目

本次以 Python 標準函式庫讀日誌、重算時間並核對磁碟頁面／manifest 身分；沒有新量測、編譯、重綁或服務操作。文件以 `git diff --check` 與本機相對連結檢查驗證。§34.4 **+0／+0，累計 47／27**。

## 2026-10-25 接續：優先完成 cell 編輯

擁有者後續明確指定：格內雙擊編輯、上方寬輸入欄與 B／I／U，離座期間自主執行，簡單建置可直接跑。這取代上面的「下一批建議」之執行優先順序；v23 沒有恢復。新功能與宿主 0.2.34 續列未計數帳，細節見[儲存格編輯整理](2026-10-25-cell-editor-v1.md)與 [M4 cell 規格](../specs/SPEC-M4-cell-editing-v1.md)。

未計數批次新增：新 `ods-editor-v1` cell model bridge／C ABI／worker、獨立 spreadsheet session／頁面、三頁封包母體、Files 可寫／唯讀分流、ODS MIME 與副本副檔名。舊 Writer／viewer 閉包原檔與編碼 metadata 相同；這是本輪逐檔比較的結果，不是未來固定的影響面宣稱。K 的全域 pins、merge BINDING、舊 chain 仍未改綁；這輪只在離線 package wrapper 綁新候選 buildId。

## 2026-10-25 手測後：格式畫面修法與研究

擁有者確認 cell 文字／公式輸入符合預期；另報告格式後全白。finding 165 修法只調整新 Calc session 的 invalidate／emit 順序，既有模型／存檔驗證不足以證明畫面完整。本輪新增 DOM tile 與引擎 render 對比，雙瀏覽器各三輪 90／90；宿主準備 **0.2.35**，引擎不重連結。這一項續列未計數帳，K 舊 pins／BINDING／chain 不改。

[Collabora 輸入／格式原始碼與 autosave 差異](2026-10-25-collabora-calc-input-format-autosave.md) 已整理；直接輸入與部分文字格式尚未新增，目前 Calc 的手動儲存與 Writer autosave 有差異。本輪沒有把「要求確認」當作已新增排程。§34.4 +0／+0，累計 47／27。

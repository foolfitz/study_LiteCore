# Calc 直接輸入、F2 與區域選取完成

已安裝 **0.2.36／2b17a0e790b24eb3**，宿主 commit `702bad6`。本批短期待辦已完成，沒有新增人工驗收閘門。完整 K 延後併批，名義出貨仍 0.2.26。

## 現在怎麼操作

- 選格後直接輸入：建立取代原內容的草稿，Enter 寫入、Escape 取消。
- F2／雙擊：保留原內容或公式，進入格內編輯；上方輸入列仍可使用。
- 拖曳、Shift-click、Shift＋方向鍵：選取矩形區域；一般方向鍵從選區焦點移動並收合。開始輸入／F2 時收合到標示的「作用中」儲存格，只改該格。
- 選區與作用格各有框線，狀態列顯示範圍及作用格。方向鍵會把焦點捲回可見區。
- 多格 B／I／U 目前停用，快捷鍵也拒絕。先選單一格即可沿用整格格式。儲存仍需手動按鈕或 Ctrl／⌘＋S。

重新由 Files 開啟試算表會載入新封包。既有已開啟頁面仍是當時版本；有未存內容時先儲存再關閉。

## 範圍與裁決

擁有者授權 Astra 代決；agent id **`/root/astra_calc_scope`** 已多次續問。[英文裁決與覆核](../handoff/RULING-2026-10-25-calc-input-range.md) 保留完整決定。

本批交付選取本身，沒有擴成 native 任意範圍格式。矩形包含兩端合併格的範圍；交界的其他合併格不連鎖擴張，不宣稱完整 Calc 合併閉包。隱藏索引在地址範圍內但沒有假造面積；每步利用引擎 hit／cursor 幾何，不猜格寬、不逐格掃描選區。沒有拖曳自動捲動、填滿、多格貼上、部分文字格式或 autosave。

慢速選格時第一筆輸入先留在同一個 textarea，最後端點回覆才接到正確目標。過長文字、保護格或選格失敗會保留未寫文字並拒絕儲存，Escape 可取消；暫存期間的新選格／切表提示稍候，避免改寫別格。

持續以本機 Collabora Online 為唯讀參考（`cool-26-04`，HEAD c64a7343…），本次核對 [MouseControl.ts](../cool-26-04/browser/src/canvas/sections/MouseControl.ts) 的 modifier／拖曳事件，以及 [CalcTileLayer.js](../cool-26-04/browser/src/layer/tile/CalcTileLayer.js) 分開 cell selection 與文字游標的邏輯。輸入模式來源見[前一份研究](2026-10-25-collabora-calc-input-format-autosave.md)。這是原始碼參考，沒有啟動 Collabora 實例或移植程式碼。

## 驗證與審核

| 項目 | 結果 |
| --- | --- |
| Chrome／Firefox 各三輪 | **378／378**，每輪 63 項；含真實輸入／拖曳／Shift、合併與隱藏格、等待與反向手勢、下載 XML／重開 |
| 新輸入後畫面 | 12 份 snapshot、**312** 塊 DOM tile，逐位元組對比引擎同區域繪圖 |
| 過長／保護／失敗選格／舊草稿拒絕路徑 | 每瀏覽器 **8／8** |
| Session／SDK／host contract | **22／22**，E1-C intact |
| 真實 Nextcloud Files | **28／28**，兩瀏覽器；兩份畫面 **56** 塊 tile、手動存回、伺服器 XML、自有鎖釋放 |
| 封包離線檢查 | 零問題、**22／22** 紅案；45 筆中 42 筆完整紀錄不變 |

原始失敗、修法與 reader 見[功能證據](../findings/evidence/calc-input-range/README.md)、[宿主證據](../findings/evidence/host-0.2.36/README.md)。reader 拒絕空集合、缺項與 false check，結論能由既有產物重讀。

Claude Code 以英文工單經 `claude -p` 審核；完成協定及程式片段兩份審核，另外三次沒有結論，未當作通過。Astra 指出並覆核暫存驗證順序、失效目標與舊草稿前綴等實際問題，最後裁決有限範圍可封閉。[審核處置](../findings/evidence/calc-input-range/review-outcomes.md) 保留續問識別碼。

Firefox IME 證據是合成組字生命週期加真實 Enter；Chrome 有可信任 CDP 預編輯，兩者均非作業系統輸入法驗收。另有既有、未量測的限制：一般 cell commit 等待時輸入框停用，該時段連續按鍵接收尚未成立。Astra 將它列為後續工作，沒有擴成本輪新閘門；已收到的 session 草稿仍受版本保護。

## 環境與後續

litecore 保持原先 running；fgp-nc／nc-bridge paused，其餘 stopped，前後一致。24674 鎖未清；24920 文件維持 31,008 bytes、sha256 a8462965…。新建測試帳號／資料夾／分享已清除，隔離工作樹移除，分支／archive／退路保留。沒有 root 指令、核心編譯或 frozen profile 重連結。

本批沒有剩餘必須人工介入的項目。未來若要求多格格式、完整合併選取或持續輸入佇列，另立契約與判準；不自行恢復 v23 或啟動 K。§34.4 **+0／+0，累計 47／27**。

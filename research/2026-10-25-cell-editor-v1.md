# 試算表儲存格編輯 v1（2026-10-25）

本輪依擁有者指定，完成 ODS 儲存格編輯頁，整合進 Nextcloud Files。可寫的 ODS 會開啟編輯頁；唯讀分享仍走原本的檢視頁。

已安裝 **0.2.35**，原生 **171／171**、Chrome／Firefox 各三輪 **186／186**，實際 Files 存回／衝突／唯讀及 Writer 回歸均通過。仍是未計數候選；完整 K 延後併批。

格式後全白的 finding 165 已修，另有雙瀏覽器 90／90 圖塊畫面驗證與實際 Files 24／24。這次手測後 litecore 原本已啟動，維持啟動狀態，其他專案不變。日後若需要啟動可使用：

```bash
cd /home/jiajun/Projects/Nextcloud_Apps/litecore
ddev start
```

接著從 Nextcloud Files 開啟可寫的 ODS 即可。這輪連結已完成，無須補跑。

## 使用方式

- 單擊儲存格：上方顯示 A1 位址與儲存格的原始內容／公式。
- 連按兩下儲存格：在格子原地編輯；也能直接使用上方寬輸入欄。
- Enter 提交、Escape 取消；Shift＋Enter 輸入換行。輸入法組字中的 Enter 不提交。
- B／I／U：對所選儲存格切換粗體、斜體、底線，包含中文字型；作用範圍是整格。
- 按「儲存」或 Ctrl／Cmd＋S：存回 ODS；尚未儲存時會顯示狀態並保護離開操作。

換格、換工作表或儲存前會先提交目前草稿。公式欄顯示公式，格子顯示計算結果。保護工作表中的鎖定格不能編輯；可編輯格仍可使用。儲存前檔案若被別處修改，沿用宿主的衝突副本機制，保留外部版本，將本機修改另存成 `.ods`，之後的儲存會繼續寫入該副本。

目前採**手動儲存**。格式是**整格**，沒有宣稱支援格內部分文字、整片多格貼上、拖拉填滿或完整 Calc 功能。單格輸入上限 32,767 個 UTF-16 code units。這輪 SDK 連結已完成，沿用現成 Calc 核心，沒有重建 LibreOffice 核心。

## 實作與驗證來源

新 profile 是 `ods-editor-v1`，底層透過 Calc 的 cell model 讀寫；B／I／U 保留既有工具列的操作方式，改接儲存格格式。Writer 與唯讀 ODS profile 保持原本身分。

- [事前規格與後續結果](../specs/SPEC-M4-cell-editing-v1.md)
- [原生、session 與雙瀏覽器下載證據](../findings/evidence/m4-cell-editing/README.md)
- [Nextcloud 封包與實際 Files 存回證據](../findings/evidence/host-0.2.34/README.md)

完整 K 維持併批，這輪沒有啟動。先前那次完整計數實跑 7 小時 48 分 40 秒；新批次仍應預留約一個晚上，詳見[計數耗時與變更帳](2026-10-25-count-batching-and-next-work.md)。

## 手測後補充

擁有者已確認文字與公式輸入符合預期。格內選取文字後按 B／I／U 的全白已在 0.2.35 修正；目前 B／I／U 仍作用於**整格**，部分文字格式沒有支援。Calc **沒有自動儲存**；兩瀏覽器各閒置 35 秒沒有存檔，手動儲存成功，與原始碼一致。[Collabora 做法與 Writer autosave 差異分析](2026-10-25-collabora-calc-input-format-autosave.md) 記錄下一輪設計依據。

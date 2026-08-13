# 存檔點的宿主面：實際跑過一次，不是看程式碼推的

**日期**：2026-08-13　**引擎**：`835b453dd85adebbfcc6ada30fd47cdd7d5679a6abaaff3f1faebf47b484979d`
（出貨中的 `e1-editor-v1`，本輪**未重連結**，跑前跑後 hash 相同）
**瀏覽器**：Chromium（Playwright 驅動）　**fixture**：`test-docs/e1/frame-contexts.odt`
**受測頁面**：`web/demo-editor.html`（`make demo-editor-assets` 後由 `web/serve.py` 提供）

任務 033 的宿主面在此之前**沒有任何介面**：session 握著搶救回來的位元組，
畫面從頭到尾沒提過它。這一輪把那半做完，並且**用真的手勢跑過整條鏈**。

## 跑法（全部經由 demo 自己的 UI，沒有繞過任何一層）

1. 開 `frame-contexts`，點文件放游標（`1938, 1418 twips`）。
2. 打字 `RESCUEMARK`（機器速度）。修訂到 **8**、未儲存＝是。
3. 在畫布上拖曳選取（跨 `FX-PLAIN`、表格與 `FX-NOTE`）。
4. 觀察狀態、橫幅、按「下載搶救檔」。
5. 按「重新啟動引擎」，再按「儲存 ODT」。

## 結果

| 觀察點 | 實得 |
|---|---|
| 手勢後的狀態 | `recoverable-error｜EDITOR_RESULT_INVALID` |
| 引擎訊息 | `a non-collapsed selection did not read back as text` |
| 橫幅文字 | 「引擎沒有回應，但你最後那段編輯**已經保住了**（存檔點在修訂 8）。按「重新啟動引擎」會從那份繼續，也可以先下載搶救檔留一份在本機。」 |
| 搶救檔 | `frame-contexts-rescued.odt`，11.7 KB，ZIP CRC 通過 |
| 重新啟動 | 1001 ms，回到 `ready`，世代 2，未儲存＝是（走了 checkpoint 分支） |
| 重啟後存出 | `frame-contexts-edited.odt`，ZIP CRC 通過 |

**內容比對（判準是文件，不是狀態列）：**

| 字串 | 原始 fixture | 搶救檔 | 重啟後存出 |
|---|---|---|---|
| `RESCUEMA` | 無 | **有** | **有** |
| `FX-PLAIN` | 有 | 無（打字插進這一段裡） | 無 |

`FX-PLAIN` 那一列是控制組：搶救檔若只是 fixture 的複本，這一列會是「有」。

## 兩件要照實說的事

**這次卡住的不是 finding 038 的 wedge。** 拖曳範圍蓋到表格，選取讀回不是 text，
走的是 `EDITOR_RESULT_INVALID`。它同樣在 `RECOVERY_ERRORS` 裡、同樣升到
`recoverable-error`，所以宿主面驗到了——但**這一輪沒有驗到 038 那條 TIMEOUT 路徑**，
那條的 session 行為是任務 035 在 `../session-wedge-recovery/` 量的。

**打了 10 個字，文件只收到 8 個。** 修訂停在 8，存檔點宣稱修訂 8，
搶救檔的內容也正好是修訂 8——三者一致，所以**存檔點沒有說謊**。
少掉的兩個字是機器速度合成打字與 commit 路徑之間的事，不在本輪範圍，
也不是真人 IME 輸入的量測（那是 E1-C 人工輪的事）。

## 第一次的檢查是壞的，換掉了

第一版用「套用粗體」製造未存編輯，然後在搶救檔裡數 `fo:font-weight="bold"`。
**原始 fixture 本來就有一個**，而收合游標上的粗體不一定會寫進 `content.xml`——
那個檢查兩種情況都會通過。改成打字＋字串比對＋原始 fixture 控制組之後才有分辨力。

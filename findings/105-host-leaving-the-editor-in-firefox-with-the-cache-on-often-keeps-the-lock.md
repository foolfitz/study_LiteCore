# 105 — 快取開著的 Firefox 離開編輯頁時，宿主的 UNLOCK 經常沒送到伺服器：之後五分鐘重開同一個檔只能另存副本

| | |
|---|---|
| **狀態** | 已確認、宿主已修並量過（修法前新宿主 6/13、舊宿主 9/10 解鎖；修法後 30/30）／Firefox 那一側**未歸因** |
| **所在** | 我們的宿主 `litecore`（`js/litecore-editor.js` 的離頁解鎖）；成因看起來在 Firefox 對 `pagehide` 裡 keepalive fetch 的處理，沒有做最小重現 |
| **發現日** | 2026-09-29（資產派送第一次 shakedown：`findings/evidence/m3-assets/shakedown/2026-09-28T161410+0000.json`） |
| **嚴重度** | 一般（**沒有資料遺失**：重開後的存檔另存衝突副本；但使用者看到「你在另一個視窗或裝置開著這個檔案」，別人也有約五分鐘寫不進去） |
| **可重現** | Firefox 156、HTTP 快取開著：修法前新宿主約一半、舊宿主約十分之一 |

## 現象

在 Files 開一份 ODT（宿主上 token 鎖、`LOCK` 200），回到 Files，再開同一份：第二次的 `LOCK` 是 423，頁面說
「你在另一個視窗或裝置開著這個檔案：這裡的存檔會另存副本。」第一次的鎖要到逾時（約 306 秒）才消失。

伺服器的 access log 在第一次離頁時**一個 UNLOCK 都沒有**。頁面上另掛的 `pagehide` 監聽器每次都記到事件觸發、`persisted:
false`（不是 bfcache），所以宿主的 `pagehide` 處理器有執行、有呼叫 `fetch(…, {keepalive: true})` 兩次——請求沒有到伺服器。

## 為什麼之前沒看到

鎖與權限、版本的計數執行全部是 `cold`（快取關）跑的；`findings/evidence/m3-locks/unload/README.md` 記的「Firefox 156 單發
4/4 送到」也是快取關著量的。第 0 步（舊宿主、快取開、沒有編輯）兩次都送到了。直到資產派送的 K2——它**必須**開著快取量，
才看得到第二次開檔有沒有重抓——才撞到。

## 量測（`wasm_sdk_probe/tools/probe_m3_leave_unlock.py`，證據 `findings/evidence/m3-assets/leave-unlock-*.json`）

每次：新的瀏覽器 profile → 從 Files 開 → 宿主 `done` →（有編輯的臂做一個段落動作）→ 導向 Files → 輪詢伺服器的鎖 10 秒。

| 宿主 | 臂 | 10 秒內解鎖 |
|---|---|---|
| 新（`7a11a4b`） | Firefox 快取開、有編輯 | 3/7（0/2、shakedown 0/1、3/4） |
| 新 | Firefox 快取開、無編輯 | 3/6（1/2、2/4） |
| 新 | Firefox 快取關、有編輯 | 2/2 |
| 新 | Chrome 快取開（有／無編輯） | 4/4 |
| 舊（`49cc4ab`） | Firefox 快取開、有編輯 | 3/4 |
| 舊 | Firefox 快取開、無編輯 | 4/4（加上第 0 步 2/2） |
| **新＋修法** | Firefox 快取開，有編輯／無編輯 | **6/6、6/6** |
| 新＋修法 | Firefox 快取關、有編輯 | 6/6 |
| 新＋修法 | Chrome 快取開，有編輯／無編輯 | 6/6、6/6 |

失敗的每一次，access log 裡都沒有任何 UNLOCK；成功的每一次都在離頁後 1.4–2.2 秒內看到鎖消失。

**讀法**：缺陷在舊宿主就有（1/10 掉），新宿主（引擎全部從快取來）讓它常見得多（7/13 掉）。新舊宿主的離頁程式碼相同；
差別最可能是時序，**但沒有量到機制**。「Firefox 在快取開著時比較快拆掉舊文件、keepalive 請求還沒送出就被取消」是假說。

## 修法（宿主）

離頁的 UNLOCK 改成在 `beforeunload` 就送（兩發），`pagehide` 再送一次（兩發）。`beforeunload` 發生在導航開始之前，文件還
完整活著。宿主要問使用者「確定離開嗎」的那一支（內容困在頁面上、或存檔還在路上）**不**解鎖，因為頁面可能留下來。

代價：`beforeunload` 之後頁面沒有被卸載（例如點到的連結其實是下載）時，鎖已經放掉、而且解鎖會換 ETag，下一次存檔會走衝突副本。
宿主 3 秒後偵測到自己還在，就把鎖的狀態改成 `lost` 並顯示「鎖已釋放」，不假裝還持有。

修法後的量測見上表；每次離頁 access log 有 2–4 個 UNLOCK（`pagehide` 那兩發仍然有時不見，`beforeunload` 那兩發每次都到）。

## 還沒做的

- Firefox 那一側的最小重現（一個不含我們產品的頁面，`pagehide` 裡送 keepalive fetch、快取開／關）。有了才能判斷是不是上游缺陷。
- 使用者真的點連結離開（renderer 發起的導航）與 WebDriver 的「Navigate To」是不是同一條路：這裡量的都是後者。
- 關分頁：`findings/evidence/m3-locks/unload/README.md` 已記 Firefox 關分頁什麼都不送；這個修法沒有改變它（關分頁不一定觸發
  `beforeunload` 的送出），鎖仍靠逾時。

## 時間軸

- 2026-09-29：資產派送 shakedown 撞到；分辨探針四批；宿主修法；修法後 30/30。

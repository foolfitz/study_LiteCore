# 108 — 存檔的 PUT 還在路上時鎖被 refresh 判失效，宿主丟例外，修改無聲消失

| | |
|---|---|
| **狀態** | **已修**（宿主 `litecore` 0.2.4，`369e6ed`；同一支探針修前 LOST、修後 KEPT）；**計數執行尚未在 0.2.4 上跑**（見「後續」） |
| **所在** | 我們的宿主 `~/Projects/Nextcloud_Apps/litecore` `js/litecore-editor.js`（0.2.0 起就在，0.2.3 `c740d2f` 量到）：`saveOnce` 在 412 之後呼叫 `tokenOnServer(token)`，而 `token` 可能已被 `loseLock()` 設成 `null`；`save()` 只有 `try`／`finally`，沒有 `catch` |
| **發現日** | 2026-09-29（opus 對頁面誠實化實作的對抗性審核，BLOCKING 1；同日讀原始碼確認、同日量到並修掉） |
| **嚴重度** | **高（資料遺失）**：使用者按了儲存、看到「存回 失敗」，但伺服器上沒有新內容、沒有副本、頁面也沒留住位元組，離頁不問 |
| **可重現** | 用探針是決定性的（Chrome 1/1，見「限制」）；自然發生需要 60 秒一次的 refresh 恰好落在存檔的 PUT 往返之內，且鎖在那之前已從伺服器消失 |
| **是否上游** | 否，我們的宿主 |

## 現象

宿主每 60 秒 refresh 一次鎖。若鎖已經從伺服器消失（過期、在 Files 被解鎖、或被刪掉），而 refresh 的回答剛好在存檔的 PUT
還沒回來時抵達：

1. `refreshLock()` 收到 `LOST` 裡的狀態碼 → `loseLock()` 把 `token` 設成 `null`；
2. PUT（送出時帶著那個 token，`withToken: true`）回來 412；
3. `saveOnce` 見到「帶 token 的 412」，去問伺服器 `tokenOnServer(token)`——這時 `token` 是 `null`，`held.replace` 丟 `TypeError`；
4. `save()` 沒有 `catch`：這次存檔既沒有寫進原檔，也沒有另存副本，也沒有把位元組留在頁面（stranded）；
5. 頁面把存檔當成已結束，而修改在送出時就不再算「未存」——離開時沒有人問。

頁面上看得到的只有 toast `存回：Cannot read properties of null (reading 'replace')` 與「存回 失敗」，沒有下載按鈕。

## 證據

`evidence/m3-page-honesty/save-throw/`（README 有逐欄說明），探針 `wasm_sdk_probe/tools/probe_m3_save_throw.py`：
CDP `Fetch` 扣住存檔的 PUT、刪掉 `oc_files_lock` 那一列、放行其他請求直到宿主自己的 refresh 把鎖記成 `lost`，再放行 PUT。
三步的預期都寫在 09-29g 交接文件裡、任何一次執行之前。

| 步 | 宿主 | 預期 | 實測 |
| --- | --- | --- | --- |
| 1 | 0.2.3 原樣（`c740d2f`） | LOST | **LOST**：原檔不變、沒有副本、沒有 stranded、離頁不問 |
| 2 | 只加 catch-all | KEPT（stranded＋離頁詢問） | **KEPT**：同一個 `TypeError` 仍然發生，但位元組被留住、出現下載按鈕、`beforeunload` 對話框出現 |
| 3 | 再加「問送出去的那個 token」＋0.2.4 | KEPT（原檔或副本） | **KEPT 在原檔**：412（帶 token）→ 伺服器上沒有這個 token → 不帶 token 重送 204 |

第 3 步在 commit 後的乾淨宿主（`369e6ed`）上重跑一次，結果相同；那一份才是綁定 0.2.4 的證據。

順帶量到：對一個已刪除的鎖列 refresh，伺服器回 **400**（不是 412）；400 在宿主的 `LOST` 清單裡。

## 分析

「每一次存檔都以三種方式之一結束：寫進原檔、另存副本、留在頁面並擋住離頁」這件事，頁面誠實化規格 §7.1 當成前提在用，
但宿主裡**沒有任何東西保證它**——它只是每一條已知的路都剛好這樣寫。任何一個沒被預料到的例外都能從三條路之間漏出去。
這一次漏出去的是一個真實的競態，§7.5 已登錄的 `tokenOnServer` 裡 `.text()` 丟例外是同一類。

修法因此分兩層（`host_fix_0_2_4.py` 的 `b` 與 `a`）：

- **b（catch-all，讓不變式由構造成立）**：`save()` 接住 `saveOnce` 丟出、而且還沒落在三種結局之一的任何例外，把位元組 strand
  起來，改丟 `HOST_SAVE_FAILED`。第 2 步單獨量過它。
- **a（修掉這一個例外）**：`put()` 記下實際送出的 token（`sentToken`），412 之後問的是它；`tokenOnServer()` 對空 token 回 false。
  這讓「鎖在路上死掉」回到本來就設計好的路：不帶 token 重送一次。

### 為什麼之前沒抓到

每一支 M3 runner 的存檔都在鎖好好的時候做；會讓鎖失效的臂（K9′／K10′、鎖被別人拿走）是在存檔**之前**讓它失效，refresh 與 PUT
從來沒有重疊過。這條路只在 60 秒的時間軸上存在，而沒有一支 harness 在那條時間軸上等。抓到它的是審核者問「§7.1 的前提由誰保證」。

## 限制

- 只量了 Chrome，每一步一次。觸發是決定性的，所以次數量的是宿主程式碼走哪條路，不是競態的發生率；**自然發生率沒有量**。
- 鎖是用刪列的方式讓它失效的（refresh 回 400）。過期或從 Files 解鎖可能回別的狀態碼（412／423）；宿主對 `LOST` 裡的碼一視同仁（讀原始碼）。
- 0.2.4 上這支探針走不到 catch-all（`a` 已經把這個例外拿掉了）；catch-all 只在第 2 步量過。它對 `.text()` 例外與 `saveCopy`
  裡的例外的覆蓋是由構造推得，未量。

## 後續

- 頁面誠實化、鎖、資產、版本、宿主入口、同秒存檔六支 runner 都要在 0.2.4 上重跑計數（交接文件 09-29g 第 3–6 步）；那之後本單
  的「已修」才有計數執行支撐。

## 時間軸

- 2026-09-29：opus 審核指出（BLOCKING 1）；讀原始碼確認；寫探針與修法腳本（未跑）。
- 2026-09-29（同日稍後）：三步量測照預測；宿主 0.2.4 commit（`369e6ed`）、`ddev occ upgrade`；乾淨宿主上重跑第 3 步。

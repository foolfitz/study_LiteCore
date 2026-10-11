# 112 — Chrome 開 Files 頁，頁面自己的程式包一個都沒請求，清單一列都沒畫出來（locks 計數因此紅一格）

> **2026-10-11 更正標題的意思**：「一個都沒請求」是**伺服器那一側**看到的樣子。10-11 再發生一次時瀏覽器那一側留下來了：那些請求有發出，在瀏覽器裡以 `net::ERR_CERT_VERIFIER_CHANGED` 失敗，所以沒有到達伺服器。成因與修法見「2026-10-11」一節。檔名不改（被引用）。

| | |
|---|---|
| **狀態** | **成因已確認、修法待驗證**（2026-10-11 更新）：Chrome 開機後頭 2.5 秒內的兩次憑證驗證器重設，收走來源的 HTTP/2 session，排隊中的請求全部失敗；**不在受測程式碼裡**。修法在 runner 的共用啟動器（`ChromeSession` 開機後等 5 秒，`7fb0ed08`），0.2.12 計數鏈重跑中。（2026-10-06 的原狀態：已確認一次、成因未明、重跑一次 `LOCKS LAND`、重跑額度已用完） |
| **所在** | Nextcloud 34.0.2 的 Files 頁在 Chrome 151 headless 上載入時；**推論**：在受測程式碼之外（理由見「分析」） |
| **發現日** | 2026-10-06（宿主 0.2.7 的 locks 計數執行，`check_m3_locks.py --label counted`） |
| **嚴重度** | 對計數：阻斷（R 列的 locks 一格因此不成立）。對使用者：小——重新整理頁面就好，推論 |
| **可重現** | 頁面層級偶發：所有 M3 報告裡 1,244 次「從 Files 點開檔」中 1 次（10-06；另一次逾時是 09-28 的路由器 404，成因不同），10-11 再 1 次。**重設本身每次開機都有**（第二輪 E1 20/20），打不打中看當下有沒有請求排在來源的 session 上 |
| **是否上游** | **不是缺陷**（2026-10-11 更新，推論）：fable 讀 Chromium 151 原始碼——驗證器換資料就通知，H2 session 上排隊中的串流以 `ERR_CERT_VERIFIER_CHANGED` 失敗，是設計如此。問題在 runner 一開機就發請求。不送上游 |

## 現象

locks 計數執行（`evidence/m3-locks/runs/2026-10-06T035016+0000.json`）的 `runs[13]`：K5 foreign-lock、Chrome、第 2 次，04:15:30–04:16:35 UTC。
登入成功（200，落在 dashboard）、導到 `/apps/files/files?dir=/`，之後 runner 等那一列（`M3 骨架 測試.odt`）等滿 60 秒，
選擇器一直是 `null`；每 0.3 秒一次的 `evaluate` 都成功（`lastError: null`）——渲染器活著、網址也對，就是沒有那一列。之後 runner
去點那個不存在的元素，丟 `TypeError: Cannot read properties of null (reading 'click')`，這一臂判 fatal，整份報告
`LOCKS DO NOT LAND`（51/52；`chrome:foreign-lock` 2/3）。前一次（04:15:18）與後一次（04:16:35）同一臂都過，開檔 2.52／2.86 秒。

## 證據

`evidence/112/`（README 是英文）：

- `apache-access-2026-10-06T0415-0418Z.log`：web 容器裡 Apache 的存取紀錄（`/var/log/apache2/access.log`，**時間是 +0800**），
  04:15:15–04:17:49 UTC。這是唯一記到 2xx 的紀錄：ddev 路由器的存取紀錄只記 300–510（`~/.ddev/traefik/.static_config.yaml`
  的 `accessLog.filters.statusCodes`），`docker logs ddev-litecore-web` 是空的，nginx 的紀錄 0 位元組。
- **已觀察**（Apache，主 session 重算）：失敗那次的 Files 頁在 12:15:33 +0800 一秒之內請求了 188 個資源（含宿主注入的
  `litecore-files.mjs`），之後**再也沒有請求**，直到下一臂的 Python 設定。前後兩次通過的同一臂請求了它請求的全部，另外還有
  123 個路徑它沒有請求，其中包括 Files 自己的 `/dist/files-init.js`、`/dist/files-main.js`、`/dist/files-reference-files.js`、
  `/dist/core-common.js`、`/dist/core-main.js`、`core` 與 `files`、`files_lock`、`files_sharing` 等共 16 份 `l10n/zh_TW.js`
  （另有 `user_status`、`profile`、`theming` 等 6 份 l10n 它有請求），以及每一筆 `PROPFIND`／`REPORT`（列清單的請求）。
  它請求了、而通過的沒請求的：**零個**。（通過那兩次的視窗含點開編輯器之後的請求，所以這裡的 123 比 fable 數的 99 多。）
- **已觀察**：路由器的請求計數器從這次登入（129299）到下一次登入（129523）之間是 223 筆；Apache 同一段 234 行，扣掉 1 行
  容器健康檢查（`curl /phpstatus`，不經路由器）與 10 行 408（Apache 收掉閒置連線，不是請求）＝ 223。**路由器與後端之間沒有
  請求遺失或卡在路上**；瀏覽器關掉時也沒有 499。
- **已觀察**：`nextcloud.log` 在 04:15:30–04:16:40 UTC 沒有任何一筆（前後兩臂各有預期的 LOCK 被拒＋PUT 被鎖）；產品頁
  `/apps/litecore/r/e2-editor.html` 沒有被請求。這一次受測的鎖程式碼一行都沒跑。
- **已觀察**：容器 00:03 UTC 建立、跑了 5 小時沒重啟；其他 ddev 專案從 10-02 起都是停止的。

## 分析

- **讀原始碼**：宿主 0.2.5→0.2.7（`7420418..0488586`）只改了 `info.xml`、`js/litecore-editor.js`、`EditorController.php`、
  `templates/editor.php`；Files 頁上的 `js/litecore-files.mjs`（`FilesScriptsListener` 以 `addInitScript` 注入）自 2026-09-28
  的 `a245b2c` 起沒變。
- **推論**（在受測程式碼之外）：`litecore-files.mjs` 是 `type=module` 的 init script，在解析之後才執行，擋不住解析器去請求
  頁面上的 `<script src>`；而這一次 Files 自己的程式包**根本沒被請求**。所以宿主那支腳本不在因果鏈上的可能性高，但這是推論，
  不是觀察——那支腳本確實在那一頁上。
- 剩下的候選（都沒有證據可以分辨）：Chrome 的載入器、HTTP/2 串流、某支頁面腳本讓解析停下。**從伺服器那一側看不到。**
- **儀器的缺口**：runner 的 `LockChrome` 本來就收 `Network.requestWillBeSent`／`loadingFailed`、`Log.entryAdded`、
  `Runtime.exceptionThrown`，但 `open_from_files` 在點擊之前呼叫 `session.drain()`（`wasm_sdk_probe/tools/check_m3_locks.py:332`）
  **把結果丟掉了**；逾時這條路也沒有截圖或 DOM 摘要。瀏覽器那一側的證據是有的，只是沒留。

### 先前那一次逾時不是同一件事

`evidence/m3-locks/shakedown/2026-09-28T121837+0000.json` 的 run 12（Chrome K7）也是 Files 列逾時，但那次 reset upload 與
登入都拿到路由器的 `404 page not found`——另一個 ddev 專案啟動時路由器重寫路由，宿主根本沒跑（`evidence/m3-locks/README.md`）。
這一次 reset 204、登入 200，所以**是第一次在實例可達時發生**。

## 裁決（2026-10-06，fable 受擁有者之託）

擁有者看了三個選項（A：加診斷再重跑；B：原樣重跑；C：紅就是紅、先查清楚）後交 fable 裁決。裁決是 **A，但有界限**：

- **為什麼可以重跑**：事前寫的規則說「其他的紅先當 finding 讀」——「先」是順序，要求 finding 先寫，不是禁止重跑。規則 1
  禁止的是取代或改寫報告；一份新的完整報告兩者都不是。規則沒說的是「什麼時候可以重跑」，現在在紅之後、重跑之前補寫一條，
  點名是 112 逼出來的、只給一次，符合 CLAUDE.md §9 的四個條件。判準本身（一輪完整執行 52/52）沒有移動。
- **為什麼不是 B**：盲目重跑，再發生一次還是什麼都學不到，連通過的那幾次 Files 列花了多久都沒記。
- **為什麼不是 C（先）**：沒有擷取就去追一個約千分之一的事件要花好幾個小時；把擷取放進計數 runner，每一輪計數本身就是 52 次
  開檔的探針。C 寫成重跑紅時的預設路線。
- **條件**（全文在 `evidence/m3-locks/README.md` 規則 5 與 `specs/SPEC-M3-production-ui.md` §12）：
  1. 先登錄本單（就是這份）。
  2. runner 只改儀器：逾時時存下 CDP 事件、截圖、DOM 摘要（`filesRowDiagnostic`）；每一臂都記 `filesRowSeconds`。判分不動，
     用新 runner 對既存報告跑 `--score`／`--red-cases` 證明輸出相同；用一次非計數、故意給錯列名的執行讓擷取自己紅一次；
     新的 runner sha256 追加進規格。
  3. 重跑：一輪完整的 locks 計數，綁定同 §11，不起別的 ddev 專案、不同時跑別的 M3 runner 或探針。過＝`LOCKS LAND`、
     `problems=[]`、新報告的紅案全紅、`runnerSha256` 是新 pin、52 臂都帶 `filesRowSeconds`。
  4. 結果對應現在就寫死：綠→R 的 locks 格在 0.2.7 成立，10-06 那份照舊是 `LOCKS DO NOT LAND` 並被引用；任何一臂紅→R 不成立、
     本單的重跑額度用完、不跑第三次，改走 C（帶同樣擷取的專用探針），交擁有者。擷取若顯示宿主的 `litecore-files.mjs` 在因果鏈上，
     就不再是「環境」，先修宿主＋新 pin 才能再計數。
  5. **重跑若永遠沒做**：R 不成立；0.2.7 對 locks 不算已計數；109／110 維持已確認／未修。
  6. 其他五份計數報告與產品路徑網、靜態測試的結果照舊有效，不為此重跑。

## 2026-10-11：再發生一次，這次瀏覽器那一側留下來了

**已觀察**（`evidence/m3-locks/shakedown/2026-10-11T110140+0000.json`，0.2.12 計數鏈的 locks shakedown，`runs[15]`，K9′ `chrome:readonly`）：登入 200、Files 頁 `readyState: complete` 而 `rows: 0`，等滿 60.29 秒後點不存在的列而 fatal；10-06 補上的擷取（`filesRowDiagnostic`）這次觸發了：`loadingFailed` **43 筆全是 `net::ERR_CERT_VERIFIER_CHANGED`**，例外是 `OC is not defined`。鏈照規則停下、沒有任何計數執行（`evidence/m3-production-ui/runs-0.2.12/stop-1/`）。這是 shakedown 的紅、不是計數執行的紅，所以 10-06 裁決「不跑第三次」那個額度不適用；擁有者選先診斷。

**已觀察（兩份證據對讀）**：10-06 Apache 紀錄裡「通過的有請求、失敗的沒請求」的那批——`/dist/files-init.js`、`files-main.js`、`files-reference-files.js`、`core-common.js`、`core-main.js`，`core`、`files`、`files_lock`、`files_sharing` 的 `l10n/zh_TW.js`——**全部**在 10-11 瀏覽器端的失敗清單裡。集合不完全相同（10-06 收到了 `profile`、`theming` 的 l10n，10-11 這兩份失敗）。**推論**：10-06 是同一件事，請求在瀏覽器裡就失敗了，所以伺服器看不到。

**第一輪診斷**（`evidence/112/cert-verifier/`，擁有者選 A）：假說「元件更新安裝憑證元件時重設驗證器」**不被支持**——安裝在開機後 62–65 秒，三趟都沒打中任何請求；唯一一次失敗在開機後 2.3 秒。

**第二輪診斷**（`evidence/112/cert-verifier/second-round/`，fable，64 趟，判定 D2）：直接讀 `--log-net-log`。**已觀察**：每次開機都有兩次重設——R_a 約 0.17 秒（網路校時推給驗證器；關 `CertVerificationNetworkTime` 就消失）、R_b 約 2.3 秒（最大 2.421 秒；跟著背景連線，`--disable-background-networking` 就消失）；兩者都會讓來源的 HTTP/2 session going away。單一旗標只除得掉一個，留下的那個仍會收走來源的 session；`--disable-component-update` 什麼都不改。**第一個請求延到開機後 5 秒：0／12 的重設落在它之後、0 次打中。**主 session 從每趟報告重算核對過（交接 10-11e 附錄）。

**為什麼 locks 撞得到**：`check_m3_locks.py` 每個 Chrome 臂都開一個全新的 Chrome、登入之後立刻開 Files 頁，那一陣請求正好落在開機後頭幾秒。**推論**——locks 報告的 `loadingFailed` 沒有時間戳，那一次失敗的確切時刻讀不到；對得上的是時間與形狀。

**修法**（擁有者選「A 採用」，`7fb0ed08`）：`wasm_sdk_probe/tools/run_browser_probe.py` 的 `ChromeSession.__init__` 在 CDP 就緒之後等 5 秒才交回控制權。只動 runner，不動產品、宿主、頁面。理由、帳目（§34.4 因執行而修 7）、重跑的預測與殘留風險在 `specs/SPEC-M3-production-ui.md` §17.23。

**殘留**（登錄）：R_b 的時刻跟著網路走，網路變慢可能晚過 5 秒；開機後約 62 秒的元件安裝重設不在暖機範圍內（四次觀察都沒打中，但它確實會讓來源的 session going away）。

## 限制

- 只有伺服器那一側的證據；瀏覽器那一側在這一次沒有留下（儀器缺口，條件 2 補）。
- 「1,244 次中 1 次」是所有 M3 報告的合計，各報告的瀏覽器版本、宿主版本不同；不是單一條件下的發生率。

## 時間軸

- 2026-10-06 04:15:30 UTC：locks 計數執行 run 13 發生。05:01 計數鏈結束。
- 2026-10-06：主 session 讀報告、nextcloud.log、路由器紀錄、宿主 diff，普查 1,244 次；擁有者交 fable 裁決；fable 找到 Apache
  紀錄與 runner 丟掉的 CDP 事件，裁 A（有界限）；主 session 重算 Apache 視窗與 223／223，登錄本單。
- 2026-10-06 05:30–06:17 UTC：儀器改動後（runner `1d3099a2…`）依規則 5 重跑一次完整 locks 計數：`LOCKS LAND`，52/52、紅案 99／0；
  Files 那一列在頁面載入回來後 Chrome 0.00–0.07 秒、Firefox 0.00–0.26 秒就在，擷取一次都沒觸發。所以那次 60 秒是**卡住**，不是慢。
  R 的 locks 格在 0.2.7 成立；本單照舊開著——成因沒找到，下次再發生時擷取會留下瀏覽器那一側。
- 2026-10-11 11:33 UTC：0.2.12 計數鏈的 locks shakedown K9′ Chrome 再發生，擷取第一次觸發（43 筆 `ERR_CERT_VERIFIER_CHANGED`）；鏈停下。
- 2026-10-11 12:06–12:37 UTC：第一輪診斷（元件安裝假說不被支持）。13:14–13:35 UTC：第二輪診斷（fable，D2）。擁有者選加 5 秒暖機。
- 2026-10-11 14:39 UTC：暖機（`7fb0ed08`）之後整條 0.2.12 計數鏈從頭重跑。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-06 | 初版：已確認一次、成因未明；裁決 A（有界限）；重跑一次 `LOCKS LAND` |
| 2026-10-11 | 再發生一次（locks shakedown），瀏覽器端證據；兩輪診斷；成因＝Chrome 開機頭幾秒的驗證器重設；修法＝啟動器 5 秒暖機（`7fb0ed08`），重跑驗證中；標題意思更正 |

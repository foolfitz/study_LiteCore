# SPEC-M3-own-stack：測試宿主搬離 ddev

> 狀態：**草稿，演練過，切換未做**（2026-11-01）。切換要擁有者點頭（§5）。
> 依據：擁有者 2026-11-01「本專案不要依賴ddev了，不然每次都互相卡住」。

## 1. 問題

ddev 是擁有者所有專案共用的，router 也是共用的。別的專案 `ddev start`／`stop` 會讓 router 短暫 404、量測壞掉，所以宿主量測或計數鏈一跑，他別的專案就不能動。

## 2. 被綁定的東西決定了做法

搬家最自然的做法是改 runner，但 runner 是被證據綁住的，不能改：

| 綁定 | 位置 | 含意 |
|---|---|---|
| `ddev describe／occ／exec／mysql／list` | 19 處真實呼叫，9 個檔，多數經 `check_m3_skeleton_open.Instance` | 不能改呼叫端 |
| 根目錄路徑 | `DEFAULT_DDEV`；`installed_app()` 拿它分辨「開發機」與「解開的 release」 | 宿主根目錄要留在 `~/Projects/Nextcloud_Apps/litecore` |
| `webserver == apache-fpm` | `check_m3_gate0_report.py`，FPM 行程鏈檢查 | 不能換成官方 `apache` 映像（mod_php） |
| Apache access log 的 `%O` | `LOG = /var/log/apache2/access.log`，K2 讀 | 路徑與格式不能動 |
| `.ddev/config.local.yaml` 的密碼 | `Instance.__init__` | 檔案留著 |

## 3. 設計

`wasm_sdk_probe/host-stack/`，自己的 Docker Compose 專案，沒有任何 ddev 行程、router、網路或 volume：

- **web**：映像就是 `ddev/ddev-webserver:v1.25.3-litecore-built`（**故意沿用位元組**）。PHP 8.4.27、Apache 2.4.67、FPM pool 都和 0.2.26 計數時相同，新計數才能和舊計數比；換映像等於另外開一個變數。映像只是一包檔案，互相卡住的是 ddev 的共用 router 與 `start`／`stop`，不是映像。
- **db**：官方 `mariadb:11.4`（11.4.13，ddev 是 11.4.12），和 ddev 無關。
- **router**：同一顆 traefik 3.6.13，自己一個容器，自己的埠。瀏覽器到 router 是 HTTP/2、router 到 Apache 是 HTTP/1.1，和 ddev 相同的路徑，所以 `%O` 的語意不變。
- **`bin/ddev`（介面卡，不是 ddev）**：放在 PATH 最前面，把被綁工具的五種呼叫轉給 compose，依 cwd 選 stack，其他指令（`start`、`stop`）一律拒絕。綁定的工具一個位元組都不改。沒設 PATH 時工具會叫到真的 ddev，而 litecore 已停，失敗關閉。
- **網址**：`https://litecore.localhost:18443`，mkcert 憑證（`.localhost` 不需要 DNS，`*.ddev.site` 需要網路）。

## 4. 演練結果（2026-11-01，`litecore-rehearsal`，全新安裝，沒有碰 ddev）

| 項 | 結果 |
|---|---|
| 映像離開 ddev 能跑 | 可以；`/start.sh` 起 Apache＋FPM，啟動約 5 秒 |
| `occ maintenance:install`、`status` | 34.0.2 |
| `https://…:18444/status.php` | 200，HTTP/2 |
| access log | 路徑、`combined`、`+0800` 都同 ddev |
| `Instance` 類別（未改）經 `bin/ddev` | `describe`、PUT 201、GET 200、DELETE 204、`occ`、`mysql`、`exec stat` 都通 |
| 介面卡的拒絕 | `ddev start`、cwd 不是 stack 根目錄都 exit 2 |

**還沒驗**：瀏覽器登入、產品頁、runner shakedown。這些要在真的根目錄上才算數（`installed_app()` 把別的路徑當 release）。

## 5. 切換（要擁有者點頭，約 10 分鐘）

1. 確認 ddev 上沒有別的工作在用 litecore；記錄受保護文件與鎖表（`install-*.py` 的 snapshot）。
2. 從 `ddev-litecore-db` 倒資料庫，**`ddev stop litecore`**（只停這個專案，別的專案不動）。
3. 匯入新 db，`config.php` 改 `overwrite.cli.url`、`trusted_domains`；`nc-link` 的等效步驟放進啟動。
4. `compose up`，根目錄就是 `~/Projects/Nextcloud_Apps/litecore`，`data/` 原地沿用。
5. 比對第 1 步的 snapshot；再跑 §6。

**回退**：`compose down`、`config.php` 還原、`ddev start litecore`。`.ddev` 全程不動；§6 全過才談移除，而且那是另一個決定。

## 6. 切換後的判準

| 代號 | 判準 | 沒做的預設 |
|---|---|---|
| ST1 | 第 1 步的文件 sha256、鎖表與切換後逐筆相同 | 回退 |
| ST2 | `check_m3_assets`、`host_entry`、`new_document`、`same_second`、`page_honesty`、`locks`、`versions`、`autosave`、production UI 各 shakedown 一輪，結果與 ddev 上的 shakedown 逐格相同；不同的每一格都要查清是環境還是真問題 | 宿主留在 ddev，不開 0.2.45 |
| ST3 | `run_calc_editor_host.py` Files 實流程 52/52 | 同上 |
| ST4 | 擁有者另一個 ddev 專案 `start`／`stop` 期間，對新 stack 的輪詢沒有錯誤（這是搬家的目的本身） | 目的未達成，回報 |

## 7. 不做

- 不改任何被綁的 runner。`check_m3_install_elsewhere.py` 的 `litecoreprobe`、`DEV_URL`、`WEB` 寫死 ddev，K 不走它，留給之後的 install-elsewhere 工作。
- 不換 PHP、Apache 版本，不做 HTTP/3。
- 不刪 `.ddev`。

## 8. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-11-01 | 草稿；演練一輪。 |
| 2026-11-01 | 切換完成，ST1–ST4 全過（§9）。 |

## 9. 追加（2026-11-01）：切換與 ST1–ST4 的結果

**取代**檔頭的「切換未做」。擁有者同意後切換完成，宿主在 `https://litecore.localhost:18443`，ddev 的 `litecore` 已停。

| 代號 | 結果 | 證據 |
|---|---|---|
| ST1 | 三份受保護文件、鎖表、7731 個檔、版本逐筆相同 | `findings/evidence/own-stack/cutover/` |
| ST2 | `ST2_ST3_HOLD`：九個 runner 逐格比對 ddev 基線，四格不同都查清，全部是綠在新 stack | `own-stack/st2/reading.json`、`read_st2.py`（紅案 13 個全紅） |
| ST3 | Files 實流程 52/52，檢查 id 與 0.2.44 相同 | 同上 |
| ST4 | `ST4_HOLDS`：ddev 起停期間新 stack 的 status 219/219、DAV 45/45，ddev 那側同時段斷線兩次又 404 | `own-stack/st4/`（紅案 9 個全紅） |

**ST2 的四格不同**：`same_second` 兩格是 runner 在基線之後改了按鍵相位（`FOREIGN_PHASE` 0.05 → 0.60，`3d78bd5c6`，錄下的按鍵相位確實從 .05 變 .60，也是這個修法第一次重跑）；`production_ui` 的 P 兩格是 runner 的保留清單在基線之後才補上 `paste-markdown`（`4c4e7b639`）。兩者都是儀器動了，不是 stack。

**`assets` 的紅**：runner 從樹上導出 closure 和 dist 雜湊，樹已是 v29、宿主還是 0.2.44。判讀工具只把樹上導出的欄位換回基線，用 runner 自己的 `score()` 重判就 clean，對照組（弄壞一個 `.gz`）維持紅。這是「切換時樹與宿主不同步」的產物，宿主裝上 0.2.45 之後不再成立。

**具名限制**：ST2 每個 runner 只跑一輪，只出現在重複裡的差異看不到；K 會重複。

**ST1 的方法註記**：第 1 步的 snapshot 是經 PATH 選 stack 的同一支工具，所以比的是同一種讀法。

## 追加（2026-11-03，第一次冷開機）

搬到自有 stack 之後第一次重開機，`docker compose up -d` 成功，但 `/status.php` 一直 502，web 容器永遠 `health: starting`。

- **成因**：`/start.sh:146` 只在 `/var/tmp/logpipe` 不存在時才建立 FIFO 並起讀取端。ddev 每次重建容器，所以碰不到；這個 stack 重用容器，FIFO 留著、沒有讀取端，supervisord 打開它當 php-fpm 的日誌就卡住（PID 1 的 `wchan` 是 `wait_for_partner`，沒有 apache、沒有 php-fpm）。〔已實測，已讀碼〕
- **修法**：`web-config/web-entrypoint.d/clear-stale-logpipe.sh`。`ddev_custom_init_scripts` 在那個檢查之前執行，移除舊 FIFO，`start.sh` 就會重建它和讀取端。不動映像、不重建容器。
- **驗證**：連續兩次 `docker restart`，第二次 FIFO 已經存在，正好是這個缺陷的情境：2–3 秒回 200，FIFO 時間戳每次都換，讀取端在。〔已實測〕
- **沒有改的**：三個服務仍是 `restart: "no"`，開機不會自動起來，要手動 `docker compose --env-file litecore.env up -d`。

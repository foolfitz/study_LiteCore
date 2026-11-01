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

# 162：宿主 0.2.30 的 `scopedStyle()` 因為 `:root` 規則前面有一段註解而拒絕檢視頁——檢視文件回 500，編輯器正常

| | |
|---|---|
| **狀態** | **宿主 0.2.31 已修**（`host-0.2.31` 分支；裝上與 H 的重跑見 `findings/evidence/host-0.2.29/README.md`） |
| **影響版本** | **宿主 0.2.29、0.2.30** 配 package `1b4d6a1fc905fb8a`。0.2.29 上被 finding 161 蓋住（那時每條路由都 500）；161 修掉之後它才露出來 |
| **所在** | `lib/Controller/EditorController.php` `scopedStyle()`：把頁面的 `:root {`／`body {` 改寫成 `:scope {` 的那條 `preg_replace`，錨在「字串開頭或 `}` 之後、中間只准空白」。檢視頁 `web/ods-viewer.html` 的 `<style>` 在唯一的 `:root` 規則上方放了一段說明註解（SPEC-M4 §5.1、審查 C2「只准一條 document-level 顏色規則」的那段說明），`*/` 之後才是 `:root {`，改寫數是 0 → 回 null → 500「the shipped page's style no longer has the shape this app scopes」 |
| **發現日** | 2026-10-21 00:15：Phase H 第二次跑（0.2.30），H6 讀到檢視文件 500、編輯器文件 200（`findings/evidence/m4-ods/phase-h/shakedown/2026-10-20T161522+0000.json`） |
| **嚴重度** | **功能**：Nextcloud 裡點 .ods 落在檢視路由之後是一頁 500。編輯器不受影響（H6 編輯器 200；0.2.30 的 `scopedStyle` 對編輯器頁的輸出與修法後逐位元相同） |
| **是否上游** | 否。我們自己的宿主 |

## 量測

- 把 `scopedStyle()` 對 package 裡兩份頁面的 `<style>` 重放（`php -r`，主機上）：
  - `ods-viewer.html`：0.2.30 → null（500）；修法 → 1,656 B、兩個 `:scope`。
  - `e2-editor.html`：0.2.30 與修法都 → 12,058 B，**逐位元相同**。
- 紅案（修法上）：兩條 `:root` → null；`:root {` 只出現在註解裡 → null（0.2.30 會把它算成一條）。
- 與 161 同類：宿主對出貨頁面的「形狀」檢查在 Phase H 之前**沒有對真的頁面跑過**。單元測試、打包工具 selftest、`check_m3_assets` 的 22 個紅案都不經過 `scopedStyle()`。

## 修法

- 宿主 0.2.31：計數用去掉註解的副本；改寫允許 `}`（或開頭）與選擇器之間夾註解。頁面不動、package 不動（buildId 不變）。
- 沒選「改頁面把註解搬走」：那會換 package 的 buildId，今晚要重封存、重跑離線閘門、重裝 340 MB；而規則本身（頁面能在規則旁寫說明）是對的，錯的是宿主的錨。
- 判準：H6（檢視文件 200、COOP／COEP／CSP 與編輯器相同）、H2、H3 在 0.2.31 上過；H4 證明編輯器那一半不變。

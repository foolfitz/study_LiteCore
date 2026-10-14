# 143 — 在宿主裡，頁碼擠在左下角最後一條、灰色小字，而且下緣被 Nextcloud 的內容框裁掉；擁有者捲動時沒看到

| | |
|---|---|
| **狀態** | **已登錄，未修**（2026-10-14）。修法在宿主，尚未裁決。 |
| **影響版本** | 宿主 0.2.20（頁碼只在 v20 上才有）。沒有宿主的頁面上同一行在可見的狀態列上方，沒被裁。 |
| **所在** | 宿主 `templates/editor.php:53` 的容器高度寫死 `calc(100vh - 50px)`，比 Nextcloud 的 `#content`（`100vh − 50 − 8`、`overflow: clip`、圓角 16 px）高 8 px；宿主又把 `.statusbar` 藏掉，於是 `#page-status` 變成最後 27 px 那一條，字的下緣 4 px 在裁切線下。頁面樣式 `web/e2-editor.html:205`：12 px、`#6b7c8a` 白底，對比 4.31:1（WCAG AA 對 12 px 要 4.5）。 |
| **發現日** | 2026-10-14。擁有者手測 0.2.20：「捲動時我沒有看到頁碼」。任務 10-14n（`findings/evidence/host-0.2.20-hand-test/README.md`）量到它其實有顯示、每一格滾輪都跟著更新、捲動期間 0 個引擎請求。 |
| **嚴重度** | 低到中：資料正確，但功能等於沒交付——要它的人看不到。 |
| **可重現** | 每次（Firefox、Chrome，宿主上）。擁有者的視窗大小與縮放未知。 |
| **是否上游** | 否 |

## 修法方向（提出，未裁決）

宿主：`#litecore-editor-root { height: 100% }`，並讓 `#page-status` 用宿主的文字色、≥ 13 px（或改放到標題列）。紅案：路由上量字的下緣 ≤ `#content` 下緣（今天 990 > 986）、對比 ≥ 4.5:1 且 ≥ 13 px（今天 4.31／12）。只改宿主就不必換殼層 generation。

## 裁決（2026-10-14，任務 10-14o；擁有者裁示「外觀照 Collabora」，細節 fable 代決）

**只改宿主的 `templates/editor.php`，頁面與殼層位元組不動。**兩件事：

1. **容器不再比 Nextcloud 的內容框高。**`#litecore-editor-root` 的 inline 高度由 `calc(100vh - 50px)` 改成 `100%`：`#content` 本來就是 `--body-height`（`100vh − 50 − 8`），根元素填滿它，最後一條不再有 8 px 躺在 `overflow: clip` 之下。
2. **`#page-status` 變成編輯器的狀態列。**宿主的 `<style>` 裡加 `#litecore-editor-root #page-status { display: flex; align-items: center; width: 100%; min-height: 32px; padding: 0 12px; font-size: 13px; color: var(--color-main-text); background: var(--color-main-background); border-top: 1px solid var(--color-border); }`，並補 `[hidden] { display: none; }`（頁面故意不寫 `display`，讓 `hidden` 生效；宿主寫了就要自己補回來）。兩個 id 的選擇器勝過頁面在 `@scope` 裡的 `#page-status`，Firefox 146 之前的 unscoped 後備同樣適用。結果：沿著編輯器底緣、全寬、32 px 高、宿主自己的字級與文字色（13 px、`--color-main-text` 襯 `--color-main-background`，淺色主題對比約 16:1）、頁碼是最左邊的文字——這就是 Collabora 狀態列的位置與樣子（`cool-26-04`：底部全寬、`StatePageNumber` 最左）。

**沒做、為什麼。**Collabora 把頁碼畫成一顆 badge（`ui-badge`），點了開「跳到頁」。badge 的圓角外框需要頁面標記裡多一個 span（純 CSS 只能給整條或整段文字上色，畫不出只框住數字的圓角），點擊需要一個動作或頁面端的捲動——兩者都不在這一版：依擁有者的指示，不把它混進 141 的頁面改動，列為之後的項目（頁面端 scroll-to-rectangle 不需要引擎）。

**判準（K4，寫在執行之前）。**現行宿主（0.2.20 位元組＋這個樣板）、Firefox 與 Chrome、60 頁固定文件的 `page-number` 臂：(d) 頁碼文字框的下緣 ≤ `#content` 下緣（今天 990 > 986，紅）；(e) 字級 ≥ 13 px、對比 ≥ 4.5:1（今天 12 px、4.31，紅）；(f) 文字跟著滾輪（10-14n 的 18 步）；(g) 擁有者加的：狀態列沿著根元素底緣橫跨全寬，頁碼是它最左邊的文字。判讀器 `findings/evidence/host-0.2.21/judge_k.py`，先在 10-14n 的報告上確認會紅。數字見 `findings/evidence/host-0.2.21/README.md`；K3（裝上 0.2.21 之後）由之後的任務跑。樣板的 diff 未提交，列在 README（0.2.21 的宿主 commit 是主 session 的）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-14 | 登錄 |
| 2026-10-14 | 裁決（任務 10-14o，擁有者裁示外觀照 Collabora）：宿主 `templates/editor.php` 根元素改 `height: 100%`、`#page-status` 變成全寬 32 px 底部狀態列（13 px、主文字色）；K4 兩個瀏覽器通過；badge 與點擊跳頁列為之後項目 |

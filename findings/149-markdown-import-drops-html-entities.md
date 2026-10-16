# 149 — Markdown 匯入把 HTML 實體整個丟掉（`AT&amp;T` → `ATT`）

| | |
|---|---|
| **狀態** | 待驗證（原生 1 回已觀察，與原始碼一致；上游送出擱置中，只登錄） |
| **Bugzilla** | tdf#______（送出後回填） |
| **發現日** | 2026-10-16 |
| **嚴重度** | 一般（默默少字） |
| **可重現** | 1/1（原生；尚未重跑 3 回） |
| **是否上游** | **未確認**：原始碼是上游的；重現用沒有本地修改的原生 LOK build（`671c848b`），還沒在桌面 LibreOffice 上試 |

## 現象

把含實體的 Markdown 當成 Markdown 貼上（LOK `paste(doc, "text/markdown;charset=utf-8", …)`），實體整個消失：`AT&amp;T and a &lt; b and &copy; and &#x4E2D; end` 存檔後是 `ATT and a  b and  and  end`。具名實體、數字實體都一樣。

## 證據

- `evidence/149/`：輸入、存檔、stdout、原始碼摘錄、README。

## 分析

讀原始碼（`sw/source/filter/md/mdcallbcks.cxx`，`671c848b`）：文字回呼對 `MD_TEXT_ENTITY` 只有 `break`，什麼都不插入。md4c 會把 `&amp;`、`&lt;`、`&nbsp;` 與數字參照都當成 `MD_TEXT_ENTITY` 交出來（審核 2 opus §4 D1 引 `md4c.c:4409`）。

修法推論（**NOT VERIFIED — treat as a hypothesis**）：把實體解碼成字元再插入，比照 md4c 的 HTML renderer 的作法。

## 對我們的影響

擁有者 2026-10-16 選 B：v21 的「貼上為 Markdown」照貼，不攔。具名 **L-md-entities**，寫進發佈說明（`specs/SPEC-M3-link-batch-v21.md` §10）。

## 還缺什麼才能送

- [ ] 原生重跑到 3/3；桌面 LibreOffice 26.8「選擇性貼上 → Markdown」重現
- [ ] 查 master 與 Bugzilla 有沒有重複
- [ ] 上游送出擱置中

## 時間軸

- 2026-10-16：v21 審核 2（opus §4 D1）從原始碼指出；主 session 原生跑一回確認。

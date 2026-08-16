# 055 — E1-C 的驗證器會改寫它正在驗證的那份證據（人工輪的 desktop PDF）

| | |
|---|---|
| **狀態** | **已確認並已修（2026-08-16）／被改寫的紀錄已還原** |
| **Bugzilla** | —（我方工具，不是 core） |
| **發現日** | 2026-08-16——**我自己踩到的**：只是想讀一次判定，就把 08-07 那一輪的證據改掉了 |
| **嚴重度** | **嚴重**——證據的用途就是「那一輪產出的東西」，被後來的執行覆蓋掉就不再是那一輪的紀錄 |
| **可重現** | 100%，每一次執行 |
| **是否上游** | **否** |

## 現象

`python3 tools/validate_e1_c.py`（不帶參數）會把
`findings/evidence/sdk-e1/editor-validation/manual/{chrome,firefox}-output.desktop.pdf`
**重新產生一次**。LibreOffice 每次匯出都會蓋新的 `CreationDate`，所以位元組必然不同
——**那一輪的紀錄每跑一次就被換掉一次**。

不是只發生過一次：`git log --follow` 顯示同一個檔案在 `3ff063c` 也被換過，
而那個 commit 的主題是 finding 048 的第六輪預測，跟 E1-C 的人工輪毫無關係。
**它是搭別的 commit 進去的。**

## 這件事的邊界，說清楚

被改寫的是 **`*.desktop.pdf`——驗證器自己的重新匯出**，不是 operator 的檔案。
operator 產出的是 `*-output.odt`，**那個沒有被動到**。所以這是「驗證器污染它自己
的紀錄」，不是「人的成果被覆蓋」。即使如此，round-trip 那一段的註解早就把同一件事
判成缺陷了（見下）。

## 分析：守衛在，只是加在隔壁那個函式

`validate_outputs()` 從 2026-08-14 起就有完整的重用守衛，註解寫得一清二楚：

> Re-running rewrites desktop.pdf, and LibreOffice stamps a fresh CreationDate
> into every export, so the run can never reproduce the recorded pdfSha256
> anyway — **validating was silently mutating the evidence it was validating,
> every single time.**

而 `manual_gate()` 的桌面重開**是同一天加的**（SPEC-E1-C 6.5「人工輸出也要用桌面版
重開一次」），**卻沒有拿到那個守衛**。同一個檔案裡，隔一個函式，同一個缺陷又活了
兩天。`--refresh-desktop` 這個旗標的說明甚至寫著「Off by default so validating does
not mutate the evidence it validates」——**它從來沒有管到人工那一段**。

## 修法

人工那一段**照樣重新匯出**（匯出成功本身就是 SPEC-E1-C 6.5 要的量測），
但**已經有紀錄時就匯出到暫存路徑**，讓那一輪留著它被判定時的那個檔案。
`--refresh-desktop` 仍然可以強制覆蓋。

不用「來源沒變就重用」那條規則，是因為這一段沒有記過來源的 sha，而且
**新的匯出永遠不會等於舊的位元組**，所以「有沒有變」在這裡本來就測不出來。

驗過：修法前後 `chrome-output.desktop.pdf` 的 sha256 相同（`5ca899ac…`），
而判定仍然是 `E1_GO_ODT_EDITOR`、`failedProperties: []`。

## 還缺什麼

- [ ] **`summary.json` 與 `inventory/profile.json` 也是每跑必改。** 那是驗證器的
      報告，本來就該由它寫——但**對著一個歷史命名空間跑，就會用今天的數字蓋掉那一輪
      的報告**。今天就是這樣蓋到 08-07 那一份（已還原）。
      處方大概是「對非當期命名空間執行時要明講」，還沒做。
- [ ] 想知道「綁定還在不在」用 `tools/check_e1_c_bundle_intact.py`——
      **那支是唯讀的**（全檔零次寫入）。今天關於 v9 沒有動到 E1-C 綁定的結論就是
      它給的。

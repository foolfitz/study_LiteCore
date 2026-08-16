# 操作手冊 — 一個時段做兩件事：E1-C 收復的人工輪 ＋ D5 四格重跑

**這一份取代兩份分開的手冊。** SPEC E1-C §11.8 解除條件 1 自己就寫了「時程允許就與
E2-C D5 的四格人工排同一個時段」——同一套設置(Fcitx5 新酷音、真剪貼簿、真實指標
事件),所以合併跑的邊際成本遠低於分兩次。

## 開始之前:機器那半邊已經做完了

| | |
|---|---|
| E1-C 四個自動相位 | **Chrome 全過、Firefox 執行中/已完成**(見下方「狀態」) |
| E1-C 殼層綁定 | **已收復**:`e1/editor-shell-bundle-v2.json` = `187706b2…`,`intact: true` |
| E2-C 殼層 | **v8 `4daad6b4…`**(D5 那四格上次跑在 v6) |
| artifact | E1 = `835b453d…`、E2 = `572035ac…`,**兩個都沒有重連結** |

**§6 的規矩**:人工只在四個自動相位全過之後才開始。所以先看一眼狀態,綠了再開始。

---

## A. E1-C 人工輪(兩個瀏覽器各一次,九項檢查)

### 起伺服器

```bash
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 tools/run_e1_c.py --manual-server --port 8765 \
  --evidence-root ../findings/evidence/sdk-e1/editor-validation-requal-2026-08-16
```

它會印出網址。**Chrome 開一次、Firefox 開一次**,各做完整一輪。

### 五個步驟(規格 §6),頁面會照順序帶你走

1. **收合游標處輸入固定繁中片語**——用新酷音打 `E1C人工第一筆中文輸入`
2. **用產品的 Shift-character 按鈕做出選取,再用真 IME 取代**——打 `E1C人工選取替換`
3. **移動游標後開始組字然後按 Esc 取消**——取消的字**不可以**進文件
   (頁面會自己驗:修訂號不動、存出來的 ODT 裡沒有取消字串)
4. **真的 Ctrl+C / Ctrl+V**,以及一次 Clipboard API 的讀寫
5. **按頁面的存檔**——之後由機器驗證器檢查 anchor 數量與桌面版重開

### 九項檢查(頁面自己記,你不用抄)

`operatorConfirmedChewing`、`trustedComposition`、`trustedNativeCopy`、
`trustedPaste`、`cancel`、`clipboardWrite`、`clipboardRead`、`artifact`、`output`

### 兩件事要留意(都是上次的教訓)

- **提交之後看一眼終端機有沒有印出 `saved`**。08-07 那次 Firefox 第一次提交
  沒送達伺服器(磁碟檔沒變),操作者重做才落地。**沒看到 `saved` 就是沒存到。**
- **不要用合成事件**。這一輪的全部意義就是 `isTrusted`。

---

## B. D5 四格重跑(只有 Firefox,一輪)

**為什麼只有 Firefox**:Chrome 的 `compositionend` 是 `isTrusted:false`(08-16 實測,
同一台機器同一個新酷音),D5 的 IME 那格在 Chrome 上拿不到——**那是量到的平台限制,
判準不放寬**。

**為什麼要重跑**:那四格上次跑在殼層 v6,之後 051／052 兩個修法把殼層帶到 v8。
四格的判定**沒有被推翻**(v7／v8 只動 placeCaret 的確認路徑,而那四格是拖曳),
這一輪要的是「四格與判定器同代」的證據。

### 起伺服器

```bash
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 tools/run_e2_c_d5.py --serve --port 8766
```

### 四格(每一格:按 begin → 做手勢 → 按 done)

1. `d5-pointer-drag-single` —— **同一段**文字上拖曳選取,放開,按工具列「項目符號」
2. `d5-pointer-drag-cross` —— **跨兩段**拖曳選取,放開,按「項目符號」
3. `d5-ime-commit` —— 游標處用新酷音輸入一次中文並確定;**再選取一段文字後輸入一次
   取代它**(兩次都要,判準指名兩次)
4. `d5-clipboard` —— 真的 Ctrl+C 複製一段,游標移到別處,真的 Ctrl+V 貼上

**一格一格做完再開下一格**——round 4 有一格開著沒關,事件被算到別格去了。

做完四格按 `finish`,再按 **匯出**,把那個 JSON 檔給我。

### 這一輪新的地方

- **游標現在看得見效果了**:051／052 修好之後,點擊 30 秒逾時的情形沒有了
  (點在文字上 34 ms、點在文字下方的空白處也會成立)。上一輪你回報的
  「游標沒辦法被放置」**就是那個缺陷**,不是你的操作。
- 存檔那一步**由 harness 自己按**,你不用管。

---

## 完成之後(我來做)

```bash
python3 tools/validate_e1_c.py \
  --evidence-root ../findings/evidence/sdk-e1/editor-validation-requal-2026-08-16 \
  --matrix validation-matrix-v2.json
python3 tools/analyze_e2_c_d5.py --criteria round-two <D5 那一輪的目錄>
```

E1-C 的新裁決寫進 SPEC E1-C §11.9;D5 的四格寫進 E2-C 的證據。

## 交還的東西

1. E1-C:兩個瀏覽器各一份,**伺服器自己收**(你只要確認看到 `saved`)
2. D5:**一個 JSON 檔**(匯出鈕),以及它下載的 ODT(如果有)

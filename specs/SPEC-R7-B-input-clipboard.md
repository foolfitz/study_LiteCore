# SPEC R7-B：真實 IME、Unicode 與純文字 clipboard

> **日期**：2026-08-02  
> **狀態**：完成（部分 GO；automatic與雙瀏覽器Chewing通過，Cangjie／Pinyin未驗證）  
> **上層規格**：[SPEC R7-000](./SPEC-R7-000-overview.md)  
> **前置閘門**：[SPEC R7-A](./SPEC-R7-A-discovery-corpus.md) GO 或部分 GO

## 1. 目標

建立 host-owned input adapter，讓真實 IME 與 clipboard 的「已提交純文字」經公開 `insertText()` 進入
Document Worker。驗證文字不重複、不漏失、不拆 surrogate／ZWJ、cancel 零 mutation、拒絕權限零 mutation，
並能 save 成 desktop 可讀 ODT。

R7-B 不把 OS key event 或 composition preedit 直接送進 Writer，也不建立 generic paste surface。

## 2. Input ownership 與狀態模型

host 使用具 label 的 input sink（textarea／contenteditable 其一），DOM 擁有 composition buffer，文件只接收
commit：

```text
idle
  ├─ compositionstart → composing
  ├─ beforeinput(insertText/paste) → commit-pending
  └─ disabled/read-only → blocked

composing
  ├─ compositionupdate / beforeinput(insertCompositionText) → composing
  ├─ compositionend(non-empty committed data) → commit-pending
  ├─ compositionend(empty) / Escape / explicit cancel → idle (zero mutation)
  └─ blur / document stale / Worker crash → cancelling → idle (zero late mutation)

commit-pending
  ├─ exactly one insertText succeeds → idle
  ├─ typed failure → recoverable-error
  └─ stale / abort / Worker crash → recoverable-error (no automatic replay)
```

規則：

- 每次 composition 有單調遞增 local ID；同一 ID 最多一個 SDK request。
- `compositionupdate`／preedit 只顯示在 host sink，不增加 SDK revision。
- `compositionend.data`、`beforeinput.data` 與 sink value 不一致時保存 trace 並拒絕猜測；依 R7-A 已驗證的
  browser-specific adapter rule處理。
- mutation queue 一次一筆；上一筆完成前的新 commit 排入有上限 queue。queue full 回 typed
  `INPUT_BACKPRESSURE`，不丟棄最舊輸入。
- stale、read-only、lease unavailable 或 Worker recovery 時 input sink 明確 disabled；已開始但未 commit 的
  composition cancel，不在 reload 後重送。
- host 可記錄 fixture code points 與 byte length，但正式 API 不暴露原始 key sequence、candidate list 或
  Fcitx internals。

## 3. 公開 SDK 邊界

- v1 只呼叫 `DocumentHandle.insertText(committedText, { signal, timeoutMs })`。
- SDK 回傳 `{ method: "paste" | "postKeyEvent", revision }`；UI 不依 method 改語意，但測試分開記錄 fallback。
- 空字串在 host 視為 cancel；若直接呼叫 SDK，維持 `INVALID_ARGUMENT`。
- R7-A 凍結單次 commit UTF-8 byte ceiling、queue depth 與 timeout。超限回 `INPUT_TOO_LARGE`，不得截斷。
- `insertText()` 尚無 `expectedRevision`；R7-B 以單 Worker序列 queue與 Reader state guard 保護。若實驗證明
  late commit 可跨 revision 落地，停止並提出窄 revision-guarded insert API，不以 UI timing 規避。
- 不能新增 `.uno:*`、raw keycode passthrough、IME callback passthrough 或 Emscripten memory access。

## 4. 真 IME matrix

### 4.1 必測 input methods

| Input method | 環境 | 最低案例 |
|---|---|---|
| Fcitx5 Chewing | 已安裝且目前啟用 | 候選選字、連續兩句、Escape cancel、全形標點 |
| Fcitx5 Cangjie | 已安裝；人工切換 | 候選選字、連續 commit、cancel |
| Fcitx5 Pinyin | 已安裝；人工切換 | 候選選字、中英切換、cancel |

每種方法不驗證鍵碼教學；operator 將規格給定的最終 fixture phrase 輸入，evidence 記錄實際 committed
Unicode scalar sequence。切換全域 input method 是人工 GUI 動作，不由 test runner 偷改使用者設定。

### 4.2 Unicode cases

- `臺灣文件測試` 與至少一段 20 字繁中句；
- `「全形標點」，。！？；：`；
- `𠀀`、`😀`、`👨‍👩‍👧‍👦`；
- `e\u0301` 與 `é` 各自保持預期 code points；
- 連續 composition、composition 中點選別處、Escape cancel、空 compositionend；
- commit 後立刻 save、commit 排隊時 abort、Worker crash 前未 commit。

每個成功 phrase 在最終 ODT XML 恰好出現規格次數；cancel fixture 為零次。search／selection 與 desktop
LibreOffice text extraction必須一致。

## 5. Clipboard contract

### 5.1 Copy

- 只從公開 `getSelection()` 取得 `text/plain;charset=utf-8`，由明確 user gesture 呼叫
  `navigator.clipboard.writeText()`。
- 沒有 selection、頁面非 secure context、權限拒絕或 clipboard API 不可用時顯示 typed
  `CLIPBOARD_UNAVAILABLE|CLIPBOARD_DENIED`；不得假裝已複製。
- clipboard event／audit 不記錄任意使用者內容；fixture run可記 hash、bytes與 code points。

### 5.2 Paste

- 由明確 user gesture／真 Ctrl+V 取得純文字，通過 byte／queue／state validator後呼叫一次 `insertText()`。
- clipboard 同時有 HTML、圖片或其他 MIME 時只取純文字；沒有純文字則 `UNSUPPORTED_CLIPBOARD_TYPE`。
- denied、cancel、空文字、stale document、read-only 或超限全部零 SDK mutation。
- 不使用 `document.execCommand("paste")`、不讀取任意 HTML、不轉為 UNO command。

### 5.3 權限 fixture

- Chrome 以獨立 profile／permission fixture 跑 granted 與 denied；Firefox 以獨立 profile preference／真 user
  gesture跑相同語意。測試 profile 不得污染 operator 日常 profile。
- Synthetic ClipboardEvent 只跑 adapter unit test並標記 synthetic；至少 Chrome／Firefox 各一條 headed
  真 clipboard流程。

## 6. UI 與復原

- 顯示 `idle／composing／committing／blocked／recoverable-error`，以及文件 version／SDK revision。
- composition preedit 在 DOM 可見且有 focus；canvas 不偽裝成具原生 caret 的輸入元件。
- commit 成功後清 host buffer；失敗時保留 fixture text供使用者複製，但不得自動重送。
- save 前後顯示 local bytes；下載與 Undo 沿用 R6 分流。Worker crash、stale reload 與 Undo 後 input queue 清空。
- 所有錯誤進畫面與 machine log，不只出現在 console。

## 7. 自動與人工測試

### 7.1 Unit／synthetic browser contract

- 各 browser 的 composition event ordering fixture；同一 composition exactly-once。
- update/preedit N 次仍零 SDK mutation；commit一次 revision +1；cancel revision +0。
- duplicate compositionend、late beforeinput、blur、stale、abort、queue full、Worker crash。
- Unicode scalar/UTF-8 length與不截斷；paste／postKeyEvent兩種 result。
- clipboard granted／denied／unsupported／HTML+plain／oversized／empty。

Chrome／Firefox 各 3 次完整 synthetic suite；evidence 必須含 `synthetic=true`。

### 7.2 Headed manual

Chrome／Firefox × Chewing／Cangjie／Pinyin，各至少 1 次：

1. 開啟固定 R7 input fixture並點選 insertion target。
2. 真實輸入 phrase、選 candidate、輸入全形標點與 Unicode case。
3. 執行 Escape cancel，確認 revision／ODT 不變。
4. 真 Ctrl+C／Ctrl+V fixture，另跑 permission denied。
5. save／下載 ODT；由 validator 與 desktop LibreOffice檢查，不只人工觀看。

若某 browser／IME 因環境限制無法取得 `isTrusted` evidence，標成 `manual-unverified`，不能用 sendKeys 補成
通過。

## 8. Evidence 與 metrics

每個 run至少記錄：

- OS/session、Fcitx版本與 method、browser/version、artifact hashes、fixture ID；
- event sequence、`isTrusted`、composition ID、commit count、code points／UTF-8 bytes；
- SDK request ID、method、revision before/after、duration、typed error；
- save ODT bytes／hash、XML anchor counts、desktop open/PDF結果；
- clipboard permission state與 MIME分類，不保存非 fixture clipboard內容。

證據路徑：

```text
findings/evidence/sdk-r7/browser/input/<browser>/
findings/evidence/sdk-r7/manual/input/<browser>-<ime>/
findings/evidence/sdk-r7/roundtrip/input/
findings/evidence/sdk-r7/input-summary.json
```

## 9. 驗收與判定

**GO**：Chrome／Firefox synthetic contract各 3/3；兩 browser 的 Chewing／Cangjie／Pinyin headed runs 都
證明 exactly-once、cancel零 mutation；Unicode與純文字 clipboard逐 code point round-trip；denied／stale／
crash皆零 mutation；無 raw command surface。

**部分 GO**：host state machine與 ODT round-trip成立，但一個 browser／IME只能 manual-only或 unavailable，
或 clipboard read受 browser policy限制。明確列出支援矩陣與人工需求，不宣稱缺項跨瀏覽器完整。

**停止回報**：任何可重現重複／漏字、surrogate／ZWJ拆壞、cancel／denied後 mutation、late composition跨
revision落地、未 save mutation在 recovery後自動重送，或完成輸入必須暴露 raw key／UNO／callback。保存
event trace與失敗 ODT，建立 finding。

## 10. 交付物

- host input adapter、input fixture UI與 unit/browser tests。
- 真 IME／clipboard headed checklist與原始 evidence。
- Unicode／ODT round-trip validator與 machine summary。
- SDK gap finding或窄 revision-guarded insert提案（只在 evidence需要時）。

## 11. 執行結果

- 2026-08-03 automatic contract完成：bounded queue、typed stale／blocked／backpressure、composition exactly-once、
  cancel零 mutation、plain-text clipboard與 Unicode ODT→desktop PDF在 Chrome／Firefox各 3/3通過。
- Firefox前兩次 caret policy失敗均保留；最終採文件末端附近的公開 `click()` placement後 exact phrase gate通過。
- 集中三輸入法矩陣未執行；為降低operator負擔，沿用R7-A已保存的Chrome／Firefox Fcitx5 Chewing真實
  composition／cancel、trusted paste、Clipboard API與輸出ODT evidence。Cangjie／Pinyin明確列為未驗證。
- `input-summary.json`的automatic兩瀏覽器各3/3與Chewing兩瀏覽器皆通過。
- **判定：部分 GO**。host input／plain-text clipboard與Chewing工作流成立；不得宣稱Cangjie／Pinyin已驗證，
  未來若擴大輸入法承諾再補人工matrix。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。定義 host-owned composition、三種 Fcitx5真 IME、Unicode與純文字 clipboard安全邊界。 |
| 2026-08-03 | v2。記錄 automatic 兩瀏覽器3/3通過、manual pending與因R7-D停止而省略人工驗收。 |
| 2026-08-04 | v3。remediation後以既有雙瀏覽器Chewing真實evidence形成部分GO；Cangjie／Pinyin維持未驗證。 |

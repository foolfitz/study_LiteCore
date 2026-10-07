# 114 — 同一組字型檔與 fontconfig，原生用 CJK 行高、WASM 用拉丁行高：擁有者文件在 WASM 上每一行約 0.79 倍高

> **2026-10-07 修正（標題保留以免斷掉引用）**：「同一組 fontconfig」不成立——原生重跑只換了字型檔，規則用的是系統的 `/etc/fonts/conf.d`。成因已找到且原生重現：profile 自帶的 `conf.d/35-lang-normalize.conf` 把 LibreOffice 以**字串**送出的語言 `zh-tw` 用子字串比對改寫成 `tw`（Twi 語），於是挑到拉丁字型。見下方「成因」。

| | |
|---|---|
| **狀態** | **已診斷**（2026-10-07 修正；原為「已確認、未診斷」）：成因是 profile 的 fontconfig 規則檔 × LibreOffice 以字串加語言，原生加上同一份 conf.d 完整重現；未修 |
| **所在** | base 包的 `/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`（fontconfig 2.18.2 原樣）——**啟用它的是上游 LibreOffice 的打包**（`external/fontconfig/ExternalPackage_fontconfig_data.mk:34`，2026-10-07 審核 B2 補）；觸發條件在 LibreOffice `PrintFontManager::Substitute` 以 `FcPatternAddString(FC_LANG, …)` 加語言（**已觀察**，原始碼與量測） |
| **發現日** | 2026-10-07（merge WASM shakedown 第 3 次：擁有者文件 11 格全部 `placement-mismatch`） |
| **嚴重度** | 一般：沒有東西消失，但擁有者這類台灣字型名的文件在 WASM 上整份比桌面版矮約兩成、分頁不同（WASM 文件總高 257,114 twips，原生在 275,530 還有內容） |
| **可重現** | 100%（決定性：原生兩種字型設定 11 格逐 twip 相同；WASM 兩次執行相同） |
| **是否上游** | **是，上游 LibreOffice**（2026-10-07 審核後修正）：上游 fontconfig 預設不啟用 35、Ubuntu 只放在 conf.avail，而 LO 的 `ExternalPackage_fontconfig_data.mk` 把它裝進會生效的 conf.d（EMSCRIPTEN、MACOSX、MSC 建置；commit 703466d7 說要照 Ubuntu 保留，卻留下了 35）。LO 能送出的 282 個語言碼有 66 個被改寫（`evidence/114/review/census-abs.txt`）。上游送出照例擱置 |

## 現象

擁有者的 `PMPC指南.odt` 在 WASM（v16）上，原生 R0c 記下的游標放不回去：同一個位置的行高原生 348／521 twips，WASM 276／414。
這組數字跟度量值的算術對得上：276＝12 pt × Liberation Sans 的行距 1.149，348＝12 pt × Noto Sans CJK 的 1.448；414／521 是 18 pt 的同一對
（**推算**，不是從引擎讀出來的）。也就是 WASM 用拉丁字型的行高排這些中文行，字形照常畫出（glyph fallback）。

這是 finding 113 末段留下的開放項目（「台灣字型名在 v8 就已經拿到拉丁行高，未診斷、未量成保真缺口」）第一次在擁有者的文件上有數字。

## 排除了什麼（判別實驗，預測先 commit：`findings/evidence/merge-native/r0c-wasmfonts/PREDICTION.md`）

- **不是字型集**：把 v16 profile 的 13 個字型檔與它自己的 fontconfig 抽出來（`tools/extract_wasm_fontset.py`），用 `FONTCONFIG_FILE` 讓原生只看得到它們，
  重跑原生 R0c——11 個游標與用系統字型那一輪**逐 twip 相同**（W2 沒中）。
  **2026-10-07 修正**：「它自己的 fontconfig」只有一半——抽出來的 `fonts.conf` 以相對路徑 `<include>conf.d</include>` 引入規則，fontconfig 對**預設設定目錄**解析，實際載入的是 `/etc/fonts/conf.d` 的 61 個檔，不是 profile 的 22 個；這台機器的系統規則沒有 `35-lang-normalize.conf`。所以這一輪排除的是字型檔，**沒有排除規則**。
- **設定確實生效**（正向對照）：同一個探針在 `strace` 下，帶設定只開了 7 個字型檔、全部屬於抽出來的那組；不帶設定開了 363 個系統字型檔。
  **2026-10-07 補充**：這個對照只看得到字型檔被限制，看不到規則檔從哪裡來——儀器只報告它被指向的那一半。
- **不是合併**：同一輪的合併判讀 11 格都是 `merge`、0 KILL（W1 命中）；WASM 上這 11 格根本沒按到鍵。
- 這份文件的字型名在兩種 fontconfig 設定下用 `fc-match` 解析的結果，只有 `Microsoft JhengHei`、`PMingLiU` 不同（這台機器裝了真的微軟正黑體、
  新細明體）；其餘（含主要的「思源黑體」）都解析成 Noto Sans CJK TC——而原生換了設定版面不變，所以那兩個名字不是這份文件版面的來源。

## 重現步驟

1. merge WASM runner 對擁有者文件（`run_merge_wasm_shakedown.py --cases E01`，需要 `build/` 底下的文件）：`place.engineCaret` 的高度對 `nativeCaret` 的高度。
2. 原生：`FONTCONFIG_FILE=…/build/wasm-fontset-v16/fonts.conf MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z tools/run_merge_native.sh <out> 1 <PMPC> test-docs/merge/r0-pmpc.cases.tsv 1`，
   看 `arms.jsonl` 的 `placed.cursor`。

**預期**：同一組字型、同一個 core，行高相同。**實際**：原生 348、WASM 276（E01 等七格）；521 對 414（E02）。

## 影響

- M2-1 在擁有者文件上無法用原生座標放置（規格 §25：退回 A）。
- 保真：凡是段落字型名不是剛好五個 Noto Sans CJK 家族名之一的中文文件，WASM 的版面都可能比桌面版矮（113 的機制在 v16 的五家族之外仍然存在）。
  量成語料層級的保真缺口，要等 20.3／21.2 的語料版面比對（那是 v16 對完整 TTC，不是對原生）或另立一個對原生的比較。

## 成因（2026-10-07 補充；證據 `evidence/114/fc-debug/`，RESULT.md 英文）

判別探針（`tools/probe_fc_debug.py`，預測先 commit 於 `58c512cf`）讓 WASM 引擎裡的 fontconfig 自己印出比對（只改 mirror 裡 `probe.js` 的 `preRun` 一行加 `FC_DEBUG`，`probe.wasm` 不動）：

- v8 與 v16 都一樣：設定檔與 22 個 conf.d 全部載入；每一次「思源黑體」的請求都到了 fontconfig，但請求裡的語言是 `"tw"`，沒有 `zh-tw`。六次請求兩次答 Liberation Sans、四次答 Noto Sans CJK KR（主字型與 glyph fallback；哪次是哪個這支探針沒記，行高說主字型是拉丁那個）。**已觀察**。
- 改寫的來源：`35-lang-normalize.conf` 對每個語言碼寫 `<test name="lang" compare="contains"><string>tw</string></test>` → assign `tw`。LibreOffice 的 `PrintFontManager::Substitute` 用 `FcPatternAddString` 加語言（字串），兩邊都是字串時 `contains` 是 `FcStrStrIgnoreCase` 子字串比對（`src/fccfg.c:1134`）；`zh-tw` 含 `tw`、而 `tw` 排在 `zh` 前面，所以先中。`tw` 是拉丁文字的語言，最佳比對就落到 Liberation，中文字形照常由 glyph fallback 畫出，只剩行高看得出來。**已觀察**（原始碼）。
- 原生單一變因重現（`native-repro/`）：同 13 個字型檔、只把 include 改成 profile conf.d 的絕對路徑，LibreOffice 自帶的 fontconfig 2.18.2 與系統 2.17.1 都把 `zh-tw` 改寫成 `tw` 並挑到拉丁字型；相對路徑（＝系統規則）時兩者都留著 `zh-tw` 挑到 Noto Sans CJK TC。**已觀察**。
- 同一機制也解釋 113 的開放項目：台灣字型名在 v8 就是拉丁行高（都標 zh-TW、名字都要靠替代），以及 v15 指名 SC／JP／KR 的段落為什麼沒落到唯一的 TC（引擎環境的預設語言是 zh-TW，`familylang` 讀到 `zh-TW`）——後者是**推論**，沒有逐格量。
- 不只中文：`zh-sg`→`sg`、`pt-br`→`br`、`fr-ca`→`ca` 在原生重現裡同樣被改寫（**已觀察**）；對版面的影響只量了 zh-TW。
  **2026-10-07 修正（對抗性審核，`evidence/114/review/`）**：`pt-br`、`fr-ca` 不是 LO 會以強綁定送出的值（LO 只送 `FcGetLangs()` 的成員，會送 `pt`、`fr`），只可能經由 fontconfig 從瀏覽器 locale 推出的弱綁定預設語言進來；LO 實際送得出的改寫集合是普查的 66 個（含閩南語 `nan`→`an`、客語 `hak`→`ak`）。另外「`tw` 排在 `zh` 前面」那句論證是錯的——35 根本沒有 `zh` 規則，`tw` 只是唯一一個是 `zh-tw` 子字串的語言碼。主字型那次查詢落到 Liberation、glyph fallback 給 Noto Sans CJK KR，審核以同一份 log 確認（**已觀察**）。

## 修法候選（未做，交擁有者）

- 打包層：profile 的 conf.d 拿掉 `35-lang-normalize.conf`，或在它之前加一條把字串 `zh-tw` 換成 langset 的規則（langset 的 `contains` 是語言包含，不是子字串）。不用連結，但改的是 profile 的位元組＝新身分。
  （2026-10-07 補：擁有者選「現在修、出 v17」；審核指出窄規則只修 3 個、留 63 個改寫，拿掉 35 則為 0；修法形式交 fable 裁決中。）
- 引擎層：`PrintFontManager::Substitute` 改用 langset 加語言。要連結。
- 不修：照現狀出貨，登錄為具名保真極限。

## 未做

- 哪些發行版的桌面 LibreOffice 會因啟用 `35-lang-normalize.conf` 而在原生也中。
- 修法本身與它對產品路徑網、merge、語料版面的影響。
- ~~讀 WASM 建置的字型替代路徑~~（2026-10-07 已做，見「成因」）。
- ~~v8 上同一份文件的行高~~：探針量的是 113 的合成 fixture，v8 與 v16 結果相同；擁有者文件本身在 v8 上仍未量。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-10-07 | 初版：已確認、未診斷 |
| 2026-10-07 | 修正「同一組 fontconfig」（原生重跑載入的是系統規則）；補成因與原生重現；狀態改為已診斷 |
| 2026-10-07 | 對抗性審核（opus）：機制成立；所在／是否上游改為上游 LO 的打包；改寫範圍改為普查的 66 個；更正排序論證 |

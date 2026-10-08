# 114 — 同一組字型檔與 fontconfig，原生用 CJK 行高、WASM 用拉丁行高：擁有者文件在 WASM 上每一行約 0.79 倍高

> **2026-10-07 修正（標題保留以免斷掉引用）**：「同一組 fontconfig」不成立——原生重跑只換了字型檔，規則用的是系統的 `/etc/fonts/conf.d`。成因已找到且原生重現：profile 自帶的 `conf.d/35-lang-normalize.conf` 把 LibreOffice 以**字串**送出的語言 `zh-tw` 用子字串比對改寫成 `tw`（Twi 語），於是挑到拉丁字型。見下方「成因」。

| | |
|---|---|
| **狀態** | **已診斷、修法已打包未出貨**（2026-10-07）：成因是 profile 的 fontconfig 規則檔 × LibreOffice 以字串加語言，原生加上同一份 conf.d 完整重現。修法＝v17（base 包拿掉 `35-lang-normalize.conf`，規格 §26）；V1–V3 過、V4 兩列 19（判準寫 20）、**V5 過**（擁有者文件 11 格游標高度與 x／y 逐 twip 等於原生，`evidence/v17/v5/`）；V6：產品路徑網過（§23 紅格 0／84）、merge shakedown 兩瀏覽器過，**語料計數比較紅一份**（`e1/paragraph-content.odt` 4 px，與 35 無關、是 CJK 子集的性質）＝V6 未過、v17 不 cutover。**2026-10-08 更新**：那一份紅已診斷為 finding 116（子集沒有 Mono 字族），擁有者選 A；**114 的修法改由 `e2-editor-v18` 帶出貨**（＝v17＋補 Mono 面的 CJK 包，規格 §28），v18 的 W1–W3、W5 已過，W4／W6 在跑。**同日稍後：v18 的 W4／W6 也過了**（§28.4 六條全過，`evidence/v18/RESULT.md`；擁有者文件 11 格游標高度與 x／y 逐 twip 等於原生），114 的修法隨 v18 等擁有者核可 cutover；上游草稿 `drafts/114-bugzilla.txt` 已寫、送出照例擱置 |
| **所在** | base 包的 `/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`（fontconfig 2.18.2 原樣）——**啟用它的是上游 LibreOffice 的打包**（`external/fontconfig/ExternalPackage_fontconfig_data.mk:34`，2026-10-07 審核 B2 補）；觸發條件在 LibreOffice `PrintFontManager::Substitute` 以 `FcPatternAddString(FC_LANG, …)` 加語言（**已觀察**，原始碼與量測） |
| **發現日** | 2026-10-07（merge WASM shakedown 第 3 次：擁有者文件 11 格全部 `placement-mismatch`） |
| **嚴重度** | 一般：沒有東西消失，但擁有者這類台灣字型名的文件在 WASM 上整份比桌面版矮約兩成、分頁不同（WASM 文件總高 257,114 twips，原生在 275,530 還有內容） |
| **可重現** | 100%（決定性：原生兩種字型設定 11 格逐 twip 相同；WASM 兩次執行相同） |
| **是否上游** | **是，上游 LibreOffice**（2026-10-07 審核後修正）：上游 fontconfig 預設不啟用 35、Ubuntu 只放在 conf.avail，而 LO 的 `ExternalPackage_fontconfig_data.mk` 把它裝進會生效的 conf.d（EMSCRIPTEN、MACOSX、MSC 建置；commit 703466d7 說要照 Ubuntu 保留，卻留下了 35）。LO 能送出的 282 個語言碼有 66 個被改寫（`evidence/114/review/census-abs.txt`）。上游送出照例擱置 |

## 給審核者（2026-10-08；先讀這一節）

標題與開頭的「同一組 fontconfig」是**舊的、已被推翻的說法**，保留只為了不斷掉引用。下面是目前的宣稱，每條標了證據等級。

### 目前的宣稱

1. **機制**：LibreOffice 的 `PrintFontManager::Substitute` 以**字串**加 `FC_LANG`；`35-lang-normalize.conf` 的 `compare="contains"` 遇到字串是子字串比對；`zh-tw` 含 `tw` → 語言被改成 `tw`（Twi，拉丁文字）→ 主字型挑到 Liberation → 行高是拉丁的。**已觀察**：WASM 引擎內的 `FC_DEBUG` log、原生單一變因重現、原始碼。
2. **啟用 35 的是上游 LibreOffice 的打包**，WASM 映像從 2021-11 起就帶著它。**已讀原始碼與 git 歷史**。
3. **範圍**：LO 送得出的 282 個語言碼有 66 個被改寫。**工具普查**（由建構得出）；版面影響**只量了 zh-TW**。
4. **修法（base 包拿掉 35＝v17）有效**：V2 普查 0、V3 引擎側、V4 版面（兩列 19 未解釋）、V5 擁有者文件 11 格逐 twip 等於原生。**已量測**。
5. **平台**：Windows／macOS 一般桌面版不會中，Linux 看發行版。**讀原始碼，未逐平台實測**（見「還缺什麼才能送」）。

### 關鍵 commit（本 repo，依時間）

| commit | 內容 | 審核時看什麼 |
| --- | --- | --- |
| `99d07c82` | 發現：merge shakedown 第 3 次，擁有者文件 11 格全部 `placement-mismatch` | 症狀的第一筆數字 |
| `b2b30f65`、`fa44c830` | 第一次判別：原生換成 WASM 的字型檔重跑，沒重現 → 當時下了「成因在 WASM 引擎那側」的**錯誤結論** | 錯在哪：抽出來的 `fonts.conf` 用相對路徑 `<include>conf.d</include>`，原生載入的其實是系統規則（下方「排除了什麼」的修正） |
| `58c512cf` | 判別探針：讓 WASM 裡的 fontconfig 自己印比對；預測與解析器紅案先 commit | 探針只改 mirror 的 `probe.js` 一行，`probe.wasm` 不動 |
| `14464496` | **診斷**：WASM 裡看到 `tw`；原生以絕對路徑引入同一份 conf.d 單一變因重現；撤回 `fa44c830` 的結論 | 主要證據 |
| `b7026d9a` | opus 對抗性審核：66 個、啟用者是上游打包、更正排序論證 | 前一位審核者挑過什麼 |
| `58602d90` | 規格 §26：修法形式（fable 裁決拿掉 35）與 V1–V6 判準，**寫在任何 v17 量測之前** | 判準有沒有事後移動 |
| `321f76fe` | v17 打包（不連結）＋V1 對帳、V2 普查 | |
| `c5d360da`、`a74b24c2` | V3（引擎側）、V4（版面；兩列 19 照實記落空） | |
| `5f22c21a`、`c7b8c5c0` | V5 預測與結果 | |
| `badb2193` | finding 115：E02 合併後的分頁差，判別實驗排除 v17 字型集 | 相關但**是另一件事** |
| `14498361`、`1191edc4` | 上游草稿；平台範圍與只看標題的查重 | |

### 上游的關鍵位置

- LibreOffice core（我們的樹 `libreoffice-26-8`＠`671c848b`）：
  - `b7313bc1`（2021-11-30）〈WASM add fontconfig data to FS image〉——35 第一次進入打包清單（`git log -S35-lang-normalize -- external/fontconfig`）
  - `a7411d59`（2025-11-22）Windows 也打包這批規則；`703466d7`（同日）說「照 Ubuntu 的 conf.d 留」卻留下 35；`e219153c`（2025-11-24）最近一次改清單
  - `vcl/unx/generic/fontmanager/fontconfig.cxx:1139`（在 `Substitute`）、`:1420`（在 `matchFont`，**不是** `Substitute`；codex 審核 6），兩處都是 `FcPatternAddString(…, FC_LANG, …)`；master `216d3914` 上檔案搬到 `vcl/unx/generic/font/fontconfig.cxx`（`:1125`、`:1406`，codex 讀的，我沒重查）；`:951` 起 `mapToFontConfigLangTag`（只回傳 `FcGetLangs()` 的成員）
  - `external/fontconfig/ExternalPackage_fontconfig_data.mk:34`（35 那一行）；`Module_fontconfig.mk`（MSC、EMSCRIPTEN、MACOSX 才打包）；`configure.ac` 的 `using_freetype_fontconfig`（Windows／macOS 只有 `--enable-headless` 才是 yes）
- fontconfig 2.18.2（LO 自帶版）：`src/fccfg.c` 的 `FcConfigCompareValue`（字串的 `FcOpContains` → `FcStrStrIgnoreCase`，約第 1134 行）；`conf.d/meson.build:51–72` 的 `conf_links` 不含 35

### 證據地圖

- `evidence/114/fc-debug/`：`PREDICTION.md`、`RESULT.md`（英文）、`run1/`（WASM 內的 fontconfig log）、`native-repro/`（`fc_string_lang.py`、`fonts-abs-include.conf`、絕對／相對路徑兩種輸出、載入的規則檔清單）
- `evidence/114/review/`：opus 審核 `README.md`、`census.py` 與三份普查輸出
- `evidence/merge-native/r0c-wasmfonts/`：第一次（被推翻的）判別實驗，留著當歷史
- `evidence/v17/v1-v2/`、`v3-v4/`、`v5/`（含 `e02-discriminator/`＝finding 115）；規格 §26、§27；`drafts/114-bugzilla.txt`

### 審核者自己能重跑的（都不需要擁有者文件）

- 普查（規則改寫幾個語言碼）：`python3 wasm_sdk_probe/tools/check_fontconfig_lang_rewrites.py --profile e2-editor-v16 --expect 66`；v17 用 `--expect 0`。工具自己會在規則檔不是全部來自包內時判失敗。
- 原生最小重現：先 `python3 wasm_sdk_probe/tools/extract_wasm_fontset.py --profile e2-editor-v16 --out <新目錄>`，把產生的 `fonts.conf` 裡 `<include ignore_missing="yes">conf.d</include>` 改成**絕對路徑**，再 `FONTCONFIG_FILE=<那份 fonts.conf> python3 -I findings/evidence/114/fc-debug/native-repro/fc_string_lang.py <libfontconfig> zh-tw zh-cn`。預期 `zh-tw` 被改成 `tw`、配到 Liberation（這個最小 pattern 沒帶粗細與通用家族，所以是 Liberation Mono；LO 實際的請求配到 Sans）。
- 引擎內（要瀏覽器）：`python3 wasm_sdk_probe/tools/probe_fc_debug.py --profiles e2-editor-v16 e2-editor-v17 --out <目錄>`。
- **不能給**：擁有者的 `PMPC指南.odt`（V5 只能看報告裡的高度與段落序號）。

### 獨立審核（codex，2026-10-08）

報告：`findings/114-review-2026-10-08-codex.md`。結論：修正後的診斷成立，是 LO 自帶 fontconfig 設定的整合缺陷，值得以一般嚴重度回報上游；不要說成台灣桌面版普遍的問題，也不要說成 WASM 特有的字型度量計算缺陷。
它另外做了**原生 LibreOffice 的單一變因重現**（同一顆原生 build、v16 的 13 個字型、規則只差 35）：思源黑體 12 pt 276→348、18 pt 414→521，Noto Sans CJK TC 與拉丁對照兩邊不動。主 session 讀過原始輸出、與表格一致，已收進 `evidence/114/codex-native/`（原本在 `/tmp`）。
它的七條更正已套用到上游草稿（`drafts/114-bugzilla.txt`）；其中 5（本地修改有 `vcl/qt5/QtFrame.cxx`）與 6（`:1420` 在 `matchFont`）是**我寫錯的事實**，已在本文與草稿更正。
它也從原始碼推論上游預設的 Qt 版 WASM 走同一條路（**推論，未在官方發佈的 artifact 上測**）。

### 請特別挑戰的地方（已知的弱點）

1. V4 有兩列（思源黑體、標楷體）修好後是 19 px 不是 20 px，原因未量。
2. 「276＝12 pt × Liberation 的 1.149、348＝12 pt × Noto Sans CJK 的 1.448」是**推算**，不是從引擎讀出的。
3. 「LO 只送 `FcGetLangs()` 的成員」靠讀 `mapToFontConfigLangTag`；另有一條弱綁定的預設語言從瀏覽器 locale 進來（審核 N2）。
4. 另外 65 個被改寫的語言碼只是**由建構**修好，沒有版面量測；閩南語、客語文件不在任何 fixture 裡。
5. 平台範圍是讀 `configure.ac` 得出，CODA-W 沒實測。
6. 修法取捨（拿掉 35 vs 窄規則 vs 引擎改用 langset）的理由在「裁決」與規格 §26.1。
7. finding 115 是 v17 上另一個、更小的差異；它的判別實驗有一條照字面落空的對照（原生多載入 LO 自己的 `fc_local.conf` 與 OpenSymbol）。

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
   **2026-10-08 更正：照這一步做不會重現。**那份 `fonts.conf` 以相對路徑引入 `conf.d`，原生載入的是系統規則（沒有 35），所以會得到正常的 348。
   要重現必須把 include 改成絕對路徑（見「給審核者」的原生最小重現），並記下實際載入的規則檔（`FC_DEBUG=1024`）。

**預期**：同一組字型、同一個 core，行高相同。**實際**：原生 348、WASM 276（E01 等七格）；521 對 414（E02）。

## 影響

- M2-1 在擁有者文件上無法用原生座標放置（規格 §25：退回 A）。**2026-10-08 補**：在 v17 上可以了（V5：11 格都由點擊直接放到原生座標）；要不要放回 M2-1 依 §26.3 另寫追加段決定。
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

## 修法候選（2026-10-07 當時的三個選項；已選第一個的「拿掉 35」＝v17，見「裁決」）

- 打包層：profile 的 conf.d 拿掉 `35-lang-normalize.conf`，或在它之前加一條把字串 `zh-tw` 換成 langset 的規則（langset 的 `contains` 是語言包含，不是子字串）。不用連結，但改的是 profile 的位元組＝新身分。
  （2026-10-07 補：擁有者選「現在修、出 v17」；審核指出窄規則只修 3 個、留 63 個改寫，拿掉 35 則為 0；修法形式交 fable 裁決。）
- 引擎層：`PrintFontManager::Substitute` 改用 langset 加語言。要連結。
- 不修：照現狀出貨，登錄為具名保真極限。

## 未做

- 哪些發行版的桌面 LibreOffice 會因啟用 `35-lang-normalize.conf` 而在原生也中。
- 修法本身與它對產品路徑網、merge、語料版面的影響。**2026-10-08**：V5 過；產品路徑網 v8 對 v17 §23 紅格 0／84（`evidence/v17/product-path/`）；merge shakedown Chrome／Firefox 各 56／56（`evidence/v17/merge/`）；語料計數比較 VERDICT RED 一份（`evidence/v17/layout-corpus/RESULT.md`；v17 量到的 48 份與 v16 空跑逐帶相同，所以不是拿掉 35 造成的）。
- ~~讀 WASM 建置的字型替代路徑~~（2026-10-07 已做，見「成因」）。
- ~~v8 上同一份文件的行高~~：探針量的是 113 的合成 fixture，v8 與 v16 結果相同；擁有者文件本身在 v8 上仍未量。

## 還缺什麼才能送（2026-10-07 補）

- [ ] 上游 Bugzilla 查重複單（REST API；送出重啟時要再查一次）。2026-10-08 codex 審核做了**留言全文**子字串搜尋：`35-lang-normalize`、`lang-normalize`、`FC_LANG` 都是 0 筆；zh-tw／fontconfig 與行高／fontconfig 組合查到的單（55469、43984、58324、137393、64509 等）成因都不同。2026-10-08 先做過一次**只看標題**的 quicksearch（`35-lang-normalize`、`lang-normalize`、`FC_LANG`、`fontconfig zh-tw`、`emscripten font`、`wasm font`、`Traditional Chinese line height` 等）：沒有相符的單；留言內文沒搜
- 平台範圍（2026-10-08 讀 `configure.ac`＠671c848b，**已讀原始碼、未逐平台實測**）：Windows／macOS 的一般桌面版 `using_freetype_fontconfig=no`（只有 `--enable-headless` 才是 yes），`PrintFontManager::Substitute` 根本沒編進去，不會中；Linux 桌面用系統 fontconfig，中不中看發行版有沒有啟用 35（上游預設不啟用、Ubuntu 不啟用，其他發行版未查）；LO 自己打包規則的是 MSC、EMSCRIPTEN、MACOSX（`Module_fontconfig.mk`），WASM 映像從 2021-11（`b7313bc1`）就帶著 35，Windows 打包從 2025-11（`a7411d59`）
- [ ] 在上游發佈的 WASM build 或 CODA-W 上重現（目前是：原生＋上游自己打包的 conf.d＋LO 自帶 fontconfig 2.18.2，以及我們自己建的 26.8 WASM。**2026-10-08 更正（codex 審核 5）**：本地修改不只建置系統，還有 `vcl/qt5/QtFrame.cxx`（輸入法 context）；正確說法是「fontconfig 比對程式（`vcl/unx/generic/fontmanager`）與 fontconfig 打包（`external/fontconfig`）沒有本地修改」）
- [ ] 確認 CODA-W 的字型替代真的走 `PrintFontManager::Substitute`（`vcl_headless_freetype_code`；草稿目前寫「推測，未測」）
- [ ] 決定元件（提議 graphics stack），以及「`Substitute` 改用 langset」要不要拆成另一張
- [x] 草稿：`drafts/114-bugzilla.txt`（英文、一段一行、無表格；附件只用專案產生的 `cjk-font-slots.odt` 與 `fc_string_lang.py`，擁有者文件不附）

## 裁決（2026-10-07）

擁有者選「現在修、出新身分 v17、在 v16 cutover 之前」，修法形式交 fable 裁決＝**拿掉 `35-lang-normalize.conf`**。白話理由：另加小包放規則在這棵樹上做不到（worker 只收字型路徑，要放寬就得換 worker）；這個檔對 LibreOffice 只會把正確的語言碼改錯，拿掉它改寫數是 0；上游 fontconfig 與 Ubuntu 本來就不啟用它，拿掉正是上游 LO 該有的修法；代價是 base 包換身分、使用者多下載一次約 5.5 MB。條件與判準見規格 §26。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-10-07 | 初版：已確認、未診斷 |
| 2026-10-07 | 修正「同一組 fontconfig」（原生重跑載入的是系統規則）；補成因與原生重現；狀態改為已診斷 |
| 2026-10-07 | 對抗性審核（opus）：機制成立；所在／是否上游改為上游 LO 的打包；改寫範圍改為普查的 66 個；更正排序論證 |
| 2026-10-07 | 補裁決（fable：拿掉 35）；狀態改為修法已打包未出貨（v17，V1–V4 量過） |
| 2026-10-07 | V5 過（擁有者文件 11 格游標與原生逐 twip 相同）；上游草稿寫好、補「還缺什麼才能送」 |
| 2026-10-08 | 補平台範圍（讀 configure.ac）與一次只看標題的 Bugzilla 查重（0 筆） |
| 2026-10-08 | 加「給審核者」（目前宣稱、關鍵 commit、上游位置、證據地圖、可重跑指令、已知弱點）；更正重現步驟 2（相對路徑不會重現）；影響、修法候選、未做補上 v17 現況 |
| 2026-10-08 | codex 獨立審核入帳：原生 LO 單一變因重現收進證據；更正本地修改的說法（有 QtFrame.cxx）與 `:1420` 屬於 `matchFont`；查重補留言全文搜尋；草稿依七條更正改寫 |
| 2026-10-08 | 狀態補 V6：產品路徑網與 merge 過、語料計數比較紅一份（與 35 無關）＝V6 未過 |
| 2026-10-08 | 狀態：語料紅＝finding 116、擁有者選 A；114 的修法改由 v18 帶出貨（v17 不出貨） |

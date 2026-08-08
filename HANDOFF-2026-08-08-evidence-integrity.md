# HANDOFF 2026-08-08 — 證據與它所描述的東西會靜靜脫鉤：三個待決事項

> 對象：接手評估並**做決定**的人（本輪指定 fable）。
> 相關：[finding 027](findings/027-r8d-verdict-silently-outlived-its-release.md)（主檔）、
> [finding 026](findings/026-generation-cap-means-two-different-things.md)、
> [finding 025](findings/025-webdriver-script-injection-never-ran-on-firefox.md)、
> [finding 023](findings/023-sdk-init-wedges-at-fixed-session-depth.md)

## 這份文件要什麼

finding 027 的〈待處理〉留了三件事，**我只記錄、沒動手**，因為它們會改動 Makefile 語意、
證據擺放慣例，或驗證器的判準——都是流程決定，不是量測結論。

**請評估並決定這三件要不要做、怎麼做。**不是要你實作（除非你判斷該順手做掉），
是要一個帶理由的決定，以及「決定之後怎麼驗證它真的成立」。

**也請對抗性地看待我的框架本身。**我今天在這條線上犯過數次錯（見末節），
其中一次讓使用者基於我的錯誤說明做了決定又推翻。如果你認為這三件事被我歸錯類、
或根本不值得做，請直說。

## 背景：今天冒出四個同一類的缺陷

它們表面上互不相干，但都是同一句話的實例——**證據與它所描述的東西可以無聲脫鉤，
而且脫鉤本身沒有人在看**：

| # | 實例 | 狀態 |
|---|---|---|
| 1 | `validate_e1_c.py` 每次驗證都重跑桌面 round-trip 並覆寫 `desktop.pdf`——**驗證會改動它正在驗證的證據** | **已修**（`41d27fa`）：輸入 ODT 位元組相同就沿用，16/16 沿用、0 個 pdf 被改、連跑兩次輸出位元組相同 |
| 2 | `run_r8_production.py` 把 `worker_generations = 4` 寫死，再拿它去比 `<= 4`；`maxWorkerGenerationsPerPage: 3` 比 `<= 3`——**兩個恆真的閘門** | **已修**（`beda6d1`）：改成頁面自數，實測是 **3** 不是 4 |
| 3 | R8 release bundle 的一個檔在 08-07 變更 → 所有 08-04 的瀏覽器證據當天過期，**但四天沒人發現**，因為要等有人跑 `make` 重建 release set 才會被比對出來 | **已修復該次**（`294436e`，四相位單一 campaign 重跑，判定回 `PARTIAL_GO_LOCAL_DELIVERY`）；**機制未改** |
| 4 | `validate_r8_d.py` 只讀 `evidence/sdk-r8/`，但 023／025 修好後的重跑與今天兩輪 30 分鐘 soak 都寫進 `evidence/sdk-r8-post-023-fix/`——**是真量測，validator 從未看過** | **未處理** |

1、2 已經修掉了，列在這裡是因為**它們是同一個病**：如果有一條通則能一次擋掉這四個，
那條通則比三個個別修補值錢。這是我希望你先回答的問題。

## 已確立的事實（請回去核對，不要採信本文轉述）

| 事實 | 級別 | 去哪裡看 |
|---|---|---|
| R8 release bundle 含 17 個 artifact，其一是 `profiles/writer-review-r6/sdk-worker.js` | 已觀察 | `dist/r8c/releases/*/release-manifest.json` 的 `artifacts[].url` |
| 該檔 mtime ＝ 2026-08-07 11:19；其餘 bundle 檔案 mtime ≤ 08-03 | 已觀察 | `stat` |
| compatibility 證據 mtime ＝ 08-04 15:38，記的 `releaseId` ＝ `writer-review-5fa3ca0d38f2b46d`（現行是 `d6bee07b960a942d`） | 已觀察 | git `c7b899e` 版的 `evidence/sdk-r8/production/compatibility/chrome/summary.json` |
| release id builder **是確定性的**：連跑兩次三個 id 逐字相同；`CREATED_AT` 是寫死常數 | 已觀察 | `tools/r8_bundle.py:31`；實測 |
| `make test-r8-d-static` 會執行 `build_r8_c_release_set.py` | 已觀察 | `make -n test-r8-d-static` |
| `run_r8_production.py:131` 的 `release_ids()` **只讀不寫** `dist/r8c/release-set.json` | 已觀察 | 原始碼 |
| `validate_r8_d.py:65` 的 `activeCachedRelease` 沒有壞，只是**沒機會執行到會失敗那一刻** | 推論（機制清楚，但沒有做「刻意讓它晚一步發現」的實驗） | finding 027〈為什麼四天沒人發現〉 |
| campaign 之後再跑 `make test-r8-d-static`，三個 id 逐字不變、判定仍 pass | 已觀察 | 實測 |

## 待決一：讓「證據過期」可被偵測，而不是等 `make`

**現況。**判定的新鮮度取決於「最近有沒有人跑過 `make`」，而不是「證據是否仍描述現況」。
`activeCachedRelease` 比的是「證據記的 id」對上「`dist/` 裡那個快取檔記的 id」——
**兩邊都可能是舊的**，於是可以一起舊、一起通過。

**我想到的作法（請當成待挑戰的草案，不是建議）：**

- **A. 證據記 bundle 內容雜湊，validator 重算比對。**不經過 `dist/release-set.json` 這個快取。
  代價：validator 要能自己算出 bundle 雜湊（等於複製一份 builder 的邏輯，或呼叫它但不落地）。
  **我沒把握的點**：這是不是只是把快取往上搬一層？bundle 的輸入自己也是 `dist/` 的產物。
- **B. 證據記錄「所有被 bundle 的來源檔的雜湊」**，validator 逐一重算。更直接，但清單會隨
  bundle 定義飄移，需要單一事實來源。
- **C. 什麼都不做，改成流程紀律**：「跑判定前先重建」。最便宜，但依賴人記得——
  而今天證明了四天沒人記得。

**真正的問題**：這件事該由 validator 承擔，還是該由「證據寫入時就把足以自我驗證的資訊記進去」
承擔？我傾向後者，但沒有想清楚邊界在哪裡。

## 待決二：叫 `static` 的測試目標會改動建置產物

**現況。**`make test-r8-d-static` 會鑄出新的 release id，把既有瀏覽器證據的綁定當場作廢。
同族前例：`make test-e1-c-static` 會重建凍結的 `e1-editor-v1`（記憶裡已有警語
「跑前先 `make -n` 看相依」）。

**選項：**

- **A. 拆開**：`*-static` 只做 py_compile／unittest，把建置相依移到另一個目標。
  風險：靜態測試可能本來就需要產物存在才能跑。
- **B. 改名**（例如 `*-check`），承認它會建置。誠實但不解決問題。
- **C. 接受現狀**，只在文件警告。

**我沒把握的點**：這個相依可能是刻意的——「測試永遠測當前建置」也是一種合理立場。
若是如此，真正該修的是**「重建會作廢證據」這件事本身**（待決一），而不是目標名稱。
請判斷這兩者的先後。

## 待決三：證據根分裂

**現況。**`evidence/sdk-r8/`（validator 讀）與 `evidence/sdk-r8-post-023-fix/`（修復後的重跑）
並存。後果是今天親眼看到的：**Firefox compatibility 28/28 早就修好並跑過，
但因為寫在 validator 讀不到的目錄，`formalGaps` 白白掛著三條 gap**，
直到我把四相位重跑進 `sdk-r8` 才消失（6 條 → 3 條）。

**選項：**

- **A. 統一到 `sdk-r8`**，歷史證據靠 git 保存（今天的 campaign 已經是這個作法）。
- **B. 保留分裂**，但讓 validator 明確知道要讀哪個根、並在輸出裡寫清楚。
- **C. 把「哪個根是權威」變成證據集自己的欄位**，而不是散在各個 runner 的預設值。

**我沒把握的點**：`-post-023-fix` 這種命名可能是刻意保留「修復前後對照」的價值。
統一會不會弄丟那個價值？如果會，該用什麼形式保住？

## 硬約束（不得破壞）

- **E1-C 是凍結矩陣**，現行判定 `E1_GO_ODT_EDITOR`、48/48 綁定、0 superseded。
  動到任何閘門就要重發判定（重跑 `validate_e1_c.py` ＋重綁）。
- **R8-D 現行判定 `PARTIAL_GO_LOCAL_DELIVERY`**，四相位剛於今天 15:54 全部綁到
  release `writer-review-d6bee07b960a942d`。不要在沒有重跑的情況下讓它脫鉤。
- **不得放寬 fail-closed。**「沒量到」必須是失敗，不能預設成通過
  （`validate_e1_c.py` 的 `--skip-desktop` 目前仍會把必要檢查變成 `pass`，
  **這是一個已知未修的 fail-open**，順手評估一下要不要一起收）。
- **產品程式碼（`editor-shell/`、`sdk/`、`probe_engine.cpp`）不在這三件的範圍內**——
  這三件都是 harness／流程。
- `libreoffice-26-8` worktree **不可 reset**。需要 root 的指令一律交給使用者執行。
- 探針紀律：**不能印出不同值的探針不是探針**。今天的 `worker_generations`
  就是靠「讀數由 1 變成 3」才被收下的。

## 任何提案要怎麼驗證

沿用今天實際生效的判準，請照做：

1. **改完之後，讓那個數字／判定「有機會變成不同的值」**，並實際看到它變。
   例：待決一若實作了，就刻意改一個被 bundle 的檔，確認 validator **當下**就失敗——
   而不是等下一次 `make`。
2. **正控制不可省。**今天 `dom.workers.maxPerDomain=4` 讓第 1 代就死，才證明 pref 真的生效；
   沒有它，「加了設定還是通過」與「設定根本沒生效」無法區分。
3. **改動後重跑受影響的判定**，並照實回報判定有沒有變。若變差，回報，不要調門檻去遷就。
4. 數字一律回核 `findings/evidence/` 下的原始 JSON，不要引用本文或 finding 正文的轉述。

## 我今天的錯誤（供你校準，也請一併檢查有沒有殘留影響）

1. **把「每頁 generation 上限」的語意講錯給使用者**——說成「編到第四份文件就會被踢」。
   實際上它數的是**一個 session 的崩潰回復次數**。使用者因此先同意改 16，說明更正後改為維持 3。
   已記在 finding 026。**請確認我在規格裡的更正沒有再犯同一個錯。**
2. **把舊的 `progress.json` 當成執行中那輪的進度**（顯示 30/30，其實是幾小時前的檔）。
   教訓：看內容前先看時間戳。
3. **`--evidence-root` 傳錯**，讓一輪 30 分鐘 soak 寫進 `production/production/`，白跑。
4. **兩次用 `pgrep -f` 判斷背景工作是否結束，比對到自己的指令列**，回報成「還在跑」，
   實際上早已完成。
5. 我在 finding 014 上的數字錯過兩次（分母錯、以及把一個視窗太短的假象當成線性趨勢），
   都是上一輪 fable 複核抓出來或後續量測推翻的。

---

## 給 fable 的 prompt

```
repo：/home/jiajun/LibreOffice/study_LiteCore（zh-TW 全形標點；證據分 已觀察／推論／待驗證）

請讀 HANDOFF-2026-08-08-evidence-integrity.md，然後**做出決定**（不是只做分析）。

主問題，請先回答這一個：
  該文件列了四個「證據與它所描述的東西無聲脫鉤」的實例（兩個已修、一個已修復但機制未
  改、一個未處理）。有沒有一條通則能一次擋掉這四個？如果有，它比三個個別修補值錢，
  請提出並說明它在每個實例上怎麼運作。如果沒有，說明為什麼它們其實不同類——
  我把它們歸成一類可能就是錯的。

然後對三個待決事項各給一個決定：做／不做／改成別的做法，附理由與代價。
  待決一：讓證據過期可被偵測，而不是等有人跑 make
  待決二：叫 static 的測試目標會改動建置產物
  待決三：證據根分裂（validator 只讀 sdk-r8，修好的證據卻在 sdk-r8-post-023-fix）
另外評估文件裡提到的 validate_e1_c.py --skip-desktop fail-open 要不要一起收。

要求：
- 目標是**推翻我的框架**，不是確認它。我今天在這條線上犯過五次錯（文件末節有列），
  其中一次讓使用者基於錯誤說明做了決定又推翻。若你認為某件事被歸錯類、或不值得做，
  請直說並給理由。
- 所有數字回核 findings/evidence/ 下的原始 JSON 與原始碼，**不要採信 HANDOFF 或
  finding 正文的轉述**。我的轉述已經被證實會出錯。
- 尊重「硬約束」那一節：E1-C 是凍結矩陣（現行 E1_GO_ODT_EDITOR、48/48）、
  R8-D 現行 PARTIAL_GO_LOCAL_DELIVERY 且四相位剛綁到 release d6bee07b…、
  不得放寬 fail-closed、產品程式碼不在範圍內。
- 每個決定都要附「怎麼驗證它真的成立」，且必須符合〈任何提案要怎麼驗證〉那一節的判準
  ——特別是「讓那個值有機會變成不同的值，並實際看到它變」與「正控制不可省」。
- 若你決定順手實作，請一次只動一件事，每件事各自重跑受影響的判定並照實回報結果；
  判定若變差就照實說，不要調門檻去遷就。

輸出：每項一段決定 ＋ 理由 ＋ 代價 ＋ 驗證方式；最後給一個實作順序（含為什麼是這個順序）。
```

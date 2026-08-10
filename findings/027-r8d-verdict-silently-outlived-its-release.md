# 027 — R8-D 的判定在 release 內容變更後靜靜過期四天；「static」測試目標會重鑄 release id

| | |
|---|---|
| **狀態** | 已確認（mtime ＋ 確定性重建 ＋ `make -n` 三方一致）；**修復只完成一半**——campaign 重跑了 R8-D 自己的四個相位，R8-B／R8-C 的證據仍是 08-04、仍綁已刪除的 release，**判定現為 `STOP`**（見〈修復不完整〉） |
| **發現日** | 2026-08-08（重跑 R8-D soak 後 `validate_r8_d.py` 由 `PARTIAL_GO_LOCAL_DELIVERY` 變成 `STOP`，追下去才發現） |
| **嚴重度** | 一般偏高：判定會在無人察覺的情況下描述一個不存在的 release |
| **可重現** | 100 %（靜態事實） |
| **是否上游** | 否，我方 harness |

## 一句話

R8-D 的瀏覽器證據綁在一個**由 bundle 內容算出來的 release id** 上。bundle 裡有一個檔案在
2026-08-07 被改動，於是所有 08-04 錄下的瀏覽器證據**當下就過期了**——但**沒有任何東西會發現**，
因為 release id 只在有人重建 `dist/r8c/release-set.json` 時才會重算，而那要等到某個
`make` 目標被執行。判定因此連續四天宣稱 `PARTIAL_GO_LOCAL_DELIVERY`，描述的卻是一個已經
不存在的 release。

## 證據鏈（已觀察）

| 事實 | 來源 |
|---|---|
| R8 release bundle 含 17 個 artifact，其中一個是 `profiles/writer-review-r6/sdk-worker.js` | `dist/r8c/releases/*/release-manifest.json` 的 `artifacts[].url` |
| 該檔 mtime ＝ **2026-08-07 11:19** | `stat` |
| compatibility 證據 mtime ＝ **2026-08-04 15:38**，記的 `releaseId` ＝ `writer-review-5fa3ca0d38f2b46d` | `evidence/sdk-r8/production/compatibility/chrome/summary.json` |
| 現行 release set ＝ `writer-review-d6bee07b960a942d`（A） | `dist/r8c/release-set.json` |
| 其餘 bundle 檔案 mtime 全部 ≤ 08-03，**內容沒變的不是它們** | `stat` |
| builder **是確定性的**：連續重建兩次三個 id 逐字相同；`CREATED_AT` 是寫死常數 `2026-08-04T00:00:00+08:00` | `tools/r8_bundle.py:31`；實測連跑兩次 |

所以 id 改變**不是重建噪音，是真的內容變更**，時間點是 08-07。

## 為什麼四天沒人發現

`validate_r8_d.py:65` 的 `activeCachedRelease`（`value.get("releaseId") == release_id`）**就是**
擋這件事的閘門，它沒有壞——它只是**沒有機會執行到會失敗的那一刻**：

- `release_id` 來自 `dist/r8c/release-set.json`（`run_r8_production.py:131` 只**讀**它）；
- 那個檔只有在 `make` 跑到 `build_r8_c_release_set.py` 時才重寫；
- 在那之前，舊的 set 檔還躺在 `dist/`，記的還是 `5fa3ca0d…`，於是比對照樣通過。

**過期的是證據，但察覺過期需要一次重建。**判定的新鮮度因此取決於「最近有沒有人跑過 make」，
而不是「證據是否仍描述現況」。

## 附帶兩個同族問題

1. **`make test-r8-d-static` 會改動建置產物。**`make -n test-r8-d-static` 明確跑
   `python3 tools/build_r8_c_release_set.py --output dist/r8c`。名字叫 static 的目標會鑄出新的
   release id，把既有瀏覽器證據的綁定當場作廢。（同族前例：`make test-e1-c-static` 會重建凍結的
   `e1-editor-v1`；`validate_e1_c.py` 會覆寫 `desktop.pdf`，已於 2026-08-08 修掉。）
2. **證據根分裂：修好之後的重跑餵不進判定。**`validate_r8_d.py` 讀
   `findings/evidence/sdk-r8/`，但 finding 023／025 修復後的重跑（Firefox compatibility 28/28）
   與 2026-08-08 的兩輪 30 分鐘 soak 都寫到了 `findings/evidence/sdk-r8-post-023-fix/`。
   **那些是真量測，但 validator 從來沒看過它們**；`formalGaps` 裡「Firefox 沒有以單一 campaign
   重跑」那幾條之所以還在，正是因為證據放在它讀不到的地方。

## 修復（2026-08-08）

四個相位以**單一 campaign** 重跑進 `findings/evidence/sdk-r8/`，中間**完全不呼叫 `make`**——
因為 `make` 會重鑄 id，把已錄好的相位當場作廢。這正是 SPEC-R8-D「必須是同一次 campaign」
的實際機制，先前只寫成文字、沒有寫成可執行的約束。

**結果（已觀察，2026-08-08 15:54 完成）：判定回到 `PARTIAL_GO_LOCAL_DELIVERY`，
四個相位全部綁在現行 release `writer-review-d6bee07b960a942d`，`safetyChecks` 無一失敗。**

| 相位 | Chrome 150 | Firefox 153.0.1 |
|---|---|---|
| compatibility | 28/28、6 批次、12 worker、每頁最高 3 | 同左 |
| soak | 30.04 分、30 cycles、`workerGenerations` **3**（≤8） | 30.07 分、30 cycles、**3**（≤4） |
| `maxWorkerGenerationsPerPage` | 3（≤3） | 3（≤3） |

compatibility 的每一項與 08-04 歷史紀錄**逐項相同**（28／6／12／3）＝忠實重跑，不是行為改變；
唯一的差別是 `releaseId` 現在綁現行 release。

**兩個額外收穫：**

1. **Firefox 這次是自己過的，不是靠 fallback。**先前 `compatibility.firefox.pass` 與
   `longevity.firefox.pass` 都是 `false`，靠 `validate_r8_d.py:188-197` 的
   `acceptedForPartialGo` ＋ finding 014 檔案存在這條路徑才被接受。現在兩者
   `checks` 全綠、直接為 `true`——**判定比先前更強，不再依賴那條 fallback**。
2. **三條 formal gap 消失**（6 → 3）：「28 份 corpus 未以單一 R8 active-cache campaign 在
   Firefox 重跑」、「Firefox 的 cache/update 與 30 分鐘 longevity 分開通過、未重啟合併 soak」、
   「Firefox worker-generation budget 需要有界 reuse 與完整重載指引」。
   剩下三條與本檔無關：T2、真 quota、candidate adoption 需明確 reload。

**重建不會再打掉它**（已觀察）：campaign 之後再跑一次 `make test-r8-d-static`
（該目標會重建 release set），三個 id **逐字不變**，`validate_r8_d.py` 仍 `pass: true`。
因為 bundle 內容自 campaign 起未再變動——這也再次確認 builder 的確定性。

## 修復不完整（2026-08-08 補，已觀察）

**上一節說的「四個相位」是 R8-D 自己的四個瀏覽器相位；R8-D 的判定實際吃六個證據家族。
另外兩個沒有重跑，而且到補寫這一節為止仍綁在那個已經不存在的 release 上。**

| 證據家族 | mtime | 記的 release | 現行 dist/ 應為 |
|---|---|---|---|
| `production/compatibility/{chrome,firefox}` | 08-08 14:52／14:53 | `d6bee07b…` | 相符 |
| `production/longevity/{chrome,firefox}` | 08-08 15:24／15:54 | `d6bee07b…`（A／B／C 全記） | 相符 |
| `delivery/summary.json`（R8-B） | **08-04 13:49** | `5fa3ca0d…`／`687bd4d8…` | `d6bee07b…`／`da9e9a18…` |
| `service-worker/summary.json`（R8-C） | **08-04 15:56** | `5fa3ca0d…`／`29680a2e…`／`07f2694e…` | `d6bee07b…`／`2a409589…`／`b8993a6e…` |

那兩份證據描述的 release 目錄**已經被 builder `rmtree` 掉了**（`build_r8_c_release_set.py:72-76`、
`r8_bundle.py:289-293` 刪除 `old_ids - current_ids`）：`dist/r8c/releases/` 現在只剩
`d6bee07b`／`2a409589`／`b8993a6e`。bundle 必要位元組由 169,355,716 變成 169,368,534
（**差 12,818 B**），來源就是 08-07 那次 `sdk-worker.js` 變更——不是空白調整。

**為什麼上一節沒發現：**`safetyChecks.r8b` 與 `r8c` 只看 `summary.json` 的 `pass` 欄位
（`validate_r8_d.py` 原 241-242 行），**完全沒有比對 release**。本檔開頭說
`activeCachedRelease`「沒有壞，只是沒機會執行到會失敗那一刻」——這句話對 compatibility 成立，
但對 R8-B／R8-C 不成立：**那裡根本沒有這道閘門**。三份證據各自記了
`releaseIds`／`bundles[].releaseId`／`releaseSet.index.releases[].releaseId`，
寫下來卻沒有人讀，等於沒記。

**已修（`7e66554`）：**`validate_r8_d.release_binding()` 六個家族全查，比對對象改成
**當下從 `dist/` 重算**的身分（`source_bytes()` ＋ `bundle_manifest()`，不落地、不讀
`dist/r8c/release-set.json`、0.7 秒）。release id 本身就是 bundle 內容的雜湊
（`r8_release.expected_release_id()` 對 manifest 取 SHA-256，而 manifest 的
`artifacts[].sha256` 由現場檔案重算），所以不需要另外再記一份 bundle 雜湊。
沒記 release 的證據與記錯的證據**一律 fail**。

**判定因此變差，這是它本來就該有的值：`PARTIAL_GO_LOCAL_DELIVERY` → `STOP`**
（bound 4、superseded 2）。要救回來只能重跑 R8-B 與 R8-C 的瀏覽器相位，不能改門檻。
兩者各 166 個 case、`runnerElapsedMs` 合計 4.3 分與 3.9 分（已觀察，由 08-04 證據加總）。

**正控制（已觀察）：**用 symlink 影子 `dist/`，對被 bundle 的 `r7.css` 加一個位元組，
四個身分全變（`d6bee07b…`→`922814f9…` 等），**全程不跑 `make`**；不擾動時則逐字重現現行 id。
同一次真實執行裡兩種極性都出現：四個相位 bound、兩個 superseded。

## 待處理（未做）——已寫成交接文件待決

三件都會改動 Makefile 語意、證據擺放慣例或驗證判準，屬流程決定，因此只記錄未動手。
交接文件：[`HANDOFF-2026-08-08-evidence-integrity.md`](../HANDOFF-2026-08-08-evidence-integrity.md)
（含硬約束、驗證判準，以及一個更上層的問題：本檔與 025／026 的四個缺陷是不是同一個病、
有沒有一條通則能一次擋掉）。

1. ~~**讓過期可被偵測，而不是等 make。**~~ **已做（`7e66554`）**，見〈修復不完整〉。
   原本寫的作法（另記一份 bundle 內容雜湊）是多餘的：**release id 本身就是那個雜湊**，
   validator 只要在判定當下重算一次即可，不必新增欄位、也不必動證據格式。
2. **`*-static` 目標不該改動建置產物**，或至少改名，讓「static」名副其實。
3. **證據根統一**：`sdk-r8` 與 `sdk-r8-post-023-fix` 並存會讓「修好了」與「判定看得到」脫節。
   **注意**：`sdk-r8-post-023-fix/service-worker/` 底下 08-08 03:05 的重跑**已經綁在
   `d6bee07b…`**（已觀察，見該處 `result.json` 的 `releaseSet`），也就是說 R8-C 那一半
   「修好的證據」其實已經存在，只是在 validator 讀不到的根裡。R8-B 則**沒有**任何重跑證據。

## 已知取捨：builder 會不可回復地刪掉舊 release 目錄（2026-08-10 記錄，明知不改）

**這不是缺陷，是明知的取捨。記在這裡，是為了不讓它下次以「意外」的樣子再出現一次。**

### 機制（已觀察）

兩處，各自在寫完新 index 之後刪掉不再被引用的 release 目錄：

- `tools/r8_bundle.py:288-293`——`previous_ids - current_ids`
- `tools/build_r8_c_release_set.py:71-76`——`old_ids - current_ids`

兩處都有守衛：`target.parent` 必須是 `releases_root`、必須是目錄、名稱須
`writer-review-` 開頭且長度恰為 30。**不會誤刪守衛外的東西**，但守衛內的刪除
**沒有備份、沒有回收桶、不可回復**。

### 代價（已觀察，2026-08-10 實測）

| | |
|---|---|
| 單一 release 目錄 | **289 MB**（`du -sh`；先前交接文件轉述的 254 MB 不準） |
| 現存 release 目錄 | 5 個（`dist/releases/` 2 個、`dist/r8c/releases/` 3 個），約 1.4 GB |
| 磁碟 | `/` 916 G，已用 775 G，**90 %**，剩 95 G |

### 已經咬過一次

本檔〈修復不完整〉記的就是它的後果：R8-B／R8-C 的 08-04 證據綁在
`5fa3ca0d…`，而**那個 release 目錄早已被 builder 刪掉**，因此無法重算綁定、
只能重跑。**證據還在，它描述的東西沒了。**

### 為什麼仍然不改

保留每一個歷史 release 會無上限成長——每次 bundle 輸入變動就多 289 MB，
而磁碟已在 90 %。fable 的建議是不改，本輪同意。

### 真的要處理時，最小的作法

不是「不要刪」，而是**刪之前先讓證據自足**：release id 本身就是 bundle 內容
雜湊（見待處理第 1 項），所以只要判定當下已經重算並記下綁定，
artifacts 被刪不影響**已經下過的判定**——受影響的只有「事後回頭重算」。
若要保留那個能力，成本最低的是保留 manifest 與 `compression-index.json`
（KB 級）而非整棵 289 MB 的樹。**本輪未實作。**

## 證據

- `wasm_sdk_probe/dist/r8c/release-set.json`、`dist/r8c/releases/*/release-manifest.json`
- `wasm_sdk_probe/tools/r8_bundle.py:31`（`CREATED_AT` 常數）
- `wasm_sdk_probe/tools/validate_r8_d.py:61-74`（`compatibility_check` 與 `activeCachedRelease`）
- `wasm_sdk_probe/tools/run_r8_production.py:131`（`release_ids()` 只讀不寫）
- `findings/evidence/sdk-r8/production/`（重跑後）

## 修訂紀錄

- 2026-08-08：建檔。起因是重跑 soak 後判定變 STOP；追查發現 `compatibility` 的
  `activeCachedRelease` 失敗，再回溯到 08-07 的 `sdk-worker.js` 變更。
  一併記錄「static 目標會重建」與「證據根分裂」兩個同族問題。
- 2026-08-08（第二次）：**〈修復〉一節高估了修復範圍，已補〈修復不完整〉更正。**
  R8-D 吃六個證據家族，campaign 只重跑了四個；R8-B／R8-C 的證據仍是 08-04、
  仍綁 `5fa3ca0d…`，而它們那一側**從來就沒有 release 閘門**——所以本檔開頭
  「閘門沒壞，只是沒機會失敗」這句話只對 compatibility 成立。
  待處理第 1 項同時完成（`7e66554`），判定由 `PARTIAL_GO_LOCAL_DELIVERY` 變 `STOP`。
- 2026-08-10：**證據根統一（待處理第 3 項）改為「原地退休、保留」，不刪除。**
  [finding 028](028-cancel-during-manifest-body-read-reported-as-corrupt-manifest.md)
  修好後 R8-B／R8-C 已重跑進 `sdk-r8/`，六家族全 bound，判定回到
  `PARTIAL_GO_LOCAL_DELIVERY`——「R8-C 只有舊根綁對 release」這個阻擋因素消失。
  但逐路徑查證發現**另一個先前未列出的阻擋因素**：`driver-stderr/`、
  `service-worker-firefox-injected-path/`、`service-worker-unified/`
  **只存在於舊根**，且分別是 [025](025-webdriver-script-injection-never-ran-on-firefox.md)
  與 [014](014-firefox-long-lived-wasm-worker-init-exhaustion.md) 的主要證據，
  `specs/SPEC-R8-D-production-validation.md:259` 亦整棵引用。
  已在 `findings/evidence/sdk-r8-post-023-fix/README.md` 標明退休狀態與不可刪除的理由；
  要真的刪除，得先把那三個路徑的引用遷走。
- 2026-08-10（第二則）：**「跑 make 會重鑄 release id」這句話要再精確一層。**
  已觀察：`dist/r8/release-manifest.json` 的前置 `r7-assets` 是 `.PHONY`，所以整條
  鑄 release 的鏈**無條件**重跑（`make -n test-r8-c-static` 現在就會列出
  `build_r8_c_release_set.py`；`test-r8-b-static` 則不會）。但
  `r8_bundle.py:170` 是 `manifest["releaseId"] = expected_release_id(manifest)`
  ——**id 由 bundle 內容衍生**，而 `build_r8_c_release_set.py:72-76` 的 `rmtree`
  只刪 `old_ids - current_ids`。所以正確的形式是：**重建一定發生，但只有 bundle
  輸入變了才會換 id、才會作廢綁定。** 本輪修的 `verified-loader.js` 不在那 17 個
  artifact 內，實測跑前跑後 id 逐字不變（R8-B 兩個、R8-C 三個）。
  「重跑期間不跑 `make`」的紀律仍然維持，但理由是避免中途改寫 artifact 擾動
  進行中的相位，不是每次都會換 id。
- 2026-08-10（第三則）：補〈已知取捨：builder 會不可回復地刪掉舊 release 目錄〉。
  交接文件把它列為「明知取捨，需記錄不要當沒發生」，本輪據實測數字記錄
  （289 MB／份、5 份約 1.4 GB、磁碟 90 %；交接文件轉述的 254 MB／89 % 不準）。
  維持不改，但寫下真要處理時的最小作法。

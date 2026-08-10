# HANDOFF 2026-08-08 — 本輪成果與未完成項（給新 session）

> 對象：接手的下一個 session。
> 另有一份針對特定決策的交接：[`HANDOFF-2026-08-08-evidence-integrity.md`](HANDOFF-2026-08-08-evidence-integrity.md)
> （fable 已回覆並執行，結論見下）。
> 起點 commit `c7b899e`（匯入現況）→ 現在 `bd8ffcd`，共 15 個 commit，**working tree 乾淨、無測試在跑**。

## 先看這裡：現在的判定狀態

| 判定 | 現況 | 說明 |
|---|---|---|
| **E1-C** | **`E1_GO_ODT_EDITOR`** | 48/48 綁定、0 superseded、`automaticPass: true`。本輪未動其閘門 |
| **R8-C** | `PARTIAL_GO` | 兩瀏覽器全過 |
| **R8-B** | **`STOP`** | **唯一失敗項是 [finding 028](findings/028-cancel-during-manifest-body-read-reported-as-corrupt-manifest.md)**（產品缺陷，未修，待你決定） |
| **R8-D** | **`STOP`** | 連帶自 R8-B。**release 綁定本身已修好：六家族全 bound／0 superseded** |
| R7-D | pass（Firefox 正式九輪） | 仍是部分 GO，卡在 accessibility，與本輪無關 |

**R8-D 從 `PARTIAL_GO_LOCAL_DELIVERY` 掉到 `STOP` 不是退步，是先前被兩層問題遮住的東西露出來了**
（先是 release 綁定沒閘門，修好後才看見 R8-B 的產品缺陷）。沒有調過任何門檻。

> **2026-08-10 追記：上表的 R8-B／R8-D 已不再是 `STOP`。** finding 028 已修、
> 兩者已重跑重發。以下 08-08 的內容全部保留原樣，最新狀態見文末
> [〈2026-08-10 追記〉](#2026-08-10-追記finding-028-已修判定全部重發)。

## 唯一擋路的事：finding 028，等你決定

> **2026-08-10 追記：已決定並執行——修了，而且範圍比本節寫的大一倍。**
> 本節說的「一處不對稱」實際是兩處，第二處更嚴重。詳見文末追記。

`delivery/verified-loader.js:188-201` 兩個 `catch` 不對稱——fetch 那層會把 `AbortError`
原樣拋出，`response.json()` 那層不會，於是**使用者取消**被標成
`RELEASE_MANIFEST_INVALID`。而 `ERROR_POLICY` 把它對應到 `retryable: false` ＋
`select-known-good`，等於**告訴呼叫端「這個 release 壞了、退回舊版」**。

- 修法：把第一個 catch 的那行 abort 判斷補到第二個 catch。**不是改契約**——
  `DELIVERY_ABORTED` 早就存在，只是這條分支到不了。
- 代價（已查證）：`verified-loader.js` **不在** release bundle 的 17 個 artifact 內，
  所以**改它不會鑄新 release id、不會作廢剛綁好的六個家族**；但要重跑 R8-B
  （R8-C 走同一支 loader，建議一併），約 4.3 ＋ 3.9 分鐘 runner 時間。
- **不要用重跑求綠**：取消落在 fetch 或 body 是競態，重跑很可能就過，
  但那只是把缺陷放回它從 08-04 起就待著的隱形狀態。

## 本輪做完的事

### finding 014 全數撤回並結案

三組觀察沒有一組是 Firefox 缺陷：`s2-fresh`／`s3`／R7-C 是 [023](findings/023-sdk-init-wedges-at-fixed-session-depth.md) 的
unread `serve.py` pipe，R8-D 900 秒是 [025](findings/025-webdriver-script-injection-never-ran-on-firefox.md) 的注入腳本從未執行。
兩個待驗證本輪結案：

- **待驗證 9（位元組帳閉合）**：獨立量到 `s1`×3＋`s2-reuse` 的 serve.log 前綴 **10,033 B**
  （模型要 9,783 B，差 250 B ≈ 2.5 行 log）。代回去牆落在 cycle 34 的 85 % 處，實測牆就是 34——
  **樣本外命中，模型不再有自由參數**。附帶推翻「那 12 s 是 `time.sleep(12)`」
  （該 sleep 不在此路徑），改以實測 churn 常數 12.8／12.5／12.4 s 認定 invocation 邊界。
- **待驗證 10（記憶體）**：**是回收延遲，不是殘留**。單頁 **100 代 100/100**，
  首末淨成長 **−23.8 MB**；閒置 240 秒後整棵樹落在 **624.6 MB**，比最後一個 block 中位數
  低 **763 MB** 並保持平坦。**所有「每代殘留 X MB」與由它外推的上限全部撤回**
  （我的 1.4～2.6／207～374、以及複核修正後的 1.9～2.6／207～281——複核修對了分母，
  但被除的量本身是視窗太短造成的假象）。單頁實測深度 50 → **100**。

### generation 上限：維持 3，「每頁」承諾撤除（[finding 026](findings/026-generation-cap-means-two-different-things.md)）

規格寫的是「每頁引擎實例化次數」，**產品從來沒實作過它**；唯一實作的是
`editor-shell/editor-session.js` 的 `maxWorkerGenerations ?? 3`＝**同一個 `EditorSession`
的崩潰／boundary 回復次數**。E1-C 既有 48 case 佐證：最大 generation ＝ **2**，
只出現在 crash/boundary，`lifecycle` 一頁一代——**連它自己的 3 都沒碰到**。

使用者決定：**A（回復深度）維持 3；B（每頁）承諾撤除。**9 份規格條文已就地修訂＋補修訂紀錄，
**產品程式一行未改，因此不需重發任何判定**。實測支持：自發性崩潰量到 **0 次**
（單頁 100 代／50 代 `crashes: 0`；E1-C 210 個非故意 case 只有 7 個重建引擎，
且**全是同一份 `l0-t2`**＝finding 012 的已知降級）。

順帶量到出貨 artifact `835b453d…` 在回復軸上兩瀏覽器各 **16/16**、第 17 次仍 fail-closed
（新增 `scenario=generations`）——技術上可以放寬，但沒有理由放寬。

### 三個「證據與現實脫鉤」的缺陷已修

1. `validate_e1_c.py` 每次驗證都覆寫 `desktop.pdf` → 改成輸入相同就沿用。
   **16/16 沿用、0 個 pdf 被改、連跑兩次輸出位元組相同**。
2. `run_r8_production.py` 拿寫死的 `4` 比 `<= 4`、`3` 比 `<= 3`（兩個恆真閘門）
   → 改成頁面自數 `window.__r8_worker_generations`，**實測是 3 不是 4**。
   收下的判準是「讀數由 1 變成 3」。
3. [finding 027](findings/027-r8d-verdict-silently-outlived-its-release.md)：R8-D 的判定在
   08-07 `sdk-worker.js` 變更後**靜靜過期四天**。已由 fable 加上真正的 release 閘門，
   並重跑六個家族全部綁到現行 release `writer-review-d6bee07b960a942d`。

### fable 的三個 commit（`7e66554`／`c0f3610`／`9cb39f4`）

- **修正我的錯誤**：我宣稱 finding 027「已修復該次」是錯的——R8-D 吃**六個**證據家族，
  我只重跑了它自己的四個瀏覽器相位，R8-B／R8-C 仍綁死掉的 release，而
  `safetyChecks.r8b`／`r8c` **那一側根本沒有 release 閘門**（不是「沒機會失敗」）。
- **通則是兩條不是一條**：（一）證據自帶內容衍生身分、validator 當下重算比對；
  （二）validator 對它驗證的證據唯讀。反例證明兩者不同類。
- **第三條紀律**（我沒列到、值得記住）：**每個 extractor 要有正控制，證明證據存在時真的讀得到**。
  fable 自己第一版把 `releaseSet.index.releases` 寫成 `releaseSet.releases`，閘門照樣 fail
  但理由是錯的。**永遠 fail 的閘門和恆真閘門一樣沒資訊。**
- `--skip-desktop` 的 fail-open 已收掉（同輸入同旗標：改前 GO／exit 0，改後 STOP／exit 1）。

## 未完成：依優先序

1. **finding 028**（擋住 R8-B／R8-D 的判定）——決定要不要修 ＋ 重跑 R8-B（＋R8-C）。
2. **finding 027 第 5 步：退休 `evidence/sdk-r8-post-023-fix/`。**
   **只能在 R8-B／R8-C 重跑完成之後**——在那之前它是 R8-C 唯一一份綁對 release 的證據，
   先刪會真的丟東西。（第 4 步已完成，R8-C 已在 `sdk-r8` 綁對，所以此項現在**已解鎖**，
   但建議等 028 收完一起做。）
3. **finding 027 待決一的殘留層（待驗證）**：`dist/r8/release-manifest.json` 的
   `coreCommit`／`sdkVersion`／`capabilities`／`url`／`mediaType` 仍來自該檔，
   `bundle_manifest` 只重算 `rawBytes` 與 `sha256`。
4. **明知取捨，需記錄不要當沒發生**：builder 會 `rmtree` 舊 release 目錄，不可回復
   （一份約 254 MB、磁碟 89 %）。fable 建議不改，但要記成取捨。
5. **T2**（user-approved HTTPS/CDN）——只能由使用者提供，spec §119 明寫不得為此要求
   臨時建雲端帳號。完整 GO 缺四項：Brotli 實際預壓縮、真 quota、public document font
   inventory、T2。使用者 2026-08-08 表示「再想想」。
6. **finding 024 是否送 Mozilla**——上游 Nightly 155 已修，只剩 uplift／webcompat 價值。
7. 更早以前延後的：heading dropdown／有序清單／無序清單（我建議先用最便宜的 discovery
   profile 實驗把關）、SPEC E1-D §5 剩項、Route C 的 E2-A 前置契約、A3 未啟動。

## 踩過的坑（新 session 請直接避開）

- **R8 的多相位重跑期間絕對不能跑 `make`**：`make` 會執行 `build_r8_c_release_set.py`
  鑄出新 release id，當場作廢已錄好的相位。腳本要在頭尾各印一次 id 自我驗證。
- **`--evidence-root` 傳錯會白跑**：`run_r8_production.py` 的根是
  `findings/evidence/sdk-r8`（工具自己會補 `production/…`）。我曾多傳一層 `/production`，
  寫成 `production/production/`，一輪 30 分鐘 soak 白費。
  `run_r8_delivery.py`／`run_r8_service_worker.py` 的預設值已經是對的，不要覆寫。
- **`pgrep -f "…"` 會比對到自己的指令列**。我兩次據此回報「還在跑」，實際早已完成。
  用 `pgrep -af` 看清楚，或比對更精確的字串。
- **看檔案內容前先看時間戳**。我把幾小時前的 `progress.json`（30/30）當成當前進度。
- **shell cwd 會漂**。一律用絕對路徑，或每個指令自己 `cd`。
- `make test-e1-c-static` 會重建凍結的 `e1-editor-v1`；`make test-r8-d-static` 會重建
  release set。跑之前先 `make -n` 看相依。
- `serve.py` 服務的是 `dist/`，改了 `web/` 要 `make dist/<檔名>` 才會生效
  （我改 `r8-update-app.js` 後讀數一直是 1，就是這個原因）。

## 本輪的量測紀律（沿用）

- **不能印出不同值的探針不是探針。**`worker_generations` 是靠「讀數由 1 變成 3」才收下的。
- **永遠 fail 的閘門和恆真閘門一樣沒資訊**（fable 補充）。
- **正控制不可省。**`dom.workers.maxPerDomain=4` 讓第 1 代就死，才證明 pref 真的生效；
  沒有它，「加了設定還是通過」與「設定根本沒生效」無法區分。
- **判定變差就照實報，不要調門檻去遷就。**本輪 R8-D 由 PARTIAL_GO 掉到 STOP 兩次，
  兩次都是照實記錄。
- **不要用重跑求綠。**競態失敗重跑會過，但那是把缺陷藏回去。

## 我在本輪犯的錯（供校準，已全部更正於文件中）

1. 把「每頁 generation 上限」的語意講錯給使用者（說成「編到第四份文件就被踢」），
   使用者因此先同意改 16、說明更正後改為維持 3。
2. 宣稱 finding 027「已修復該次」，實際只重跑了六個家族中的四個（fable 抓到）。
3. `--evidence-root` 多傳一層，白跑 30 分鐘 soak。
4. 兩次用 `pgrep` 誤判背景工作仍在跑。
5. 把舊的 `progress.json` 當成當前進度。
6. finding 014 的記憶體數字錯兩次（分母錯；把視窗太短的假象當線性趨勢）。

**這份文件的轉述同樣可能有錯——數字請一律回核 `findings/evidence/` 下的原始 JSON。**

---

# 2026-08-10 追記：finding 028 已修，判定全部重發

> 以上 08-08 的內容一律保留原樣，本節只做增補與更正。
> 起點 commit `f4afa75`。

## 判定現況（取代文件開頭那張表）

| 判定 | 08-08 | 現在 |
|---|---|---|
| **R8-B** | `STOP` | **`PARTIAL_GO`**（`safetyChecks.firefox` 恢復） |
| **R8-C** | `PARTIAL_GO` | `PARTIAL_GO`（改綁修復後的 loader） |
| **R8-D** | `STOP` | **`PARTIAL_GO_LOCAL_DELIVERY`**，六家族 bound／0 superseded／0 unattributable |
| E1-C | `E1_GO_ODT_EDITOR` | 未動 |

**沒有調整任何門檻。** R8-B 剩下的兩條 `partialGaps`（Brotli CLI、full-fidelity 圖
218,486,240 B 超過凍結的 200,000,000 B）是既有項，與 028 無關。

## 更正：028 的不對稱是兩處，不是一處

08-08 的〈唯一擋路的事〉只記了 `fetchJson` 那一處。全檔審計三個 fetch／body
邊界後：**三個 fetch 的 catch 都有 abort 檢查，兩個 body 讀取的 catch 都沒有。**

| body 讀取點 | 誤標成 | `ERROR_POLICY` | 對呼叫端的意思 |
|---|---|---|---|
| `fetchJson:197-201` | `RELEASE_MANIFEST_INVALID` | `[false, select-known-good]` | 退回舊版 |
| `fetchArtifact:276-282` | `ARTIFACT_SIZE_MISMATCH` | `[false, **reject-release**]` | 直接作廢 release |

兩件 08-08 漏掉的事：

1. **`fetchJson` 服務兩個呼叫點**（`:339` manifest、`:351` compression-index），
   所以受影響的呼叫點是**三個**。
2. **`fetchArtifact` 那處更嚴重且至今隱形。** 訊息會宣稱
   `${role} response body was incomplete`——把使用者按取消講成 release 內容不完整。
   08-04 之所以看到**正確**的 `DELIVERY_ABORTED` at `artifact-fetch`，是因為取消
   落在 `fetchImpl` 呼叫本身的 catch（`:238`，有檢查），**不是** body 那條。

## 修復不必靠競態重跑就能證明（方法上的收穫）

`verified-loader.test.mjs:255` 的既有 abort 測試只在 **fetch promise** 上 reject，
**測試盲點正好落在缺陷所在**。讓 `json()`／`arrayBuffer()` 以 `AbortError` 拒絕
即可確定性重現——修前三站點分別印：

```
manifest           RELEASE_MANIFEST_INVALID / false / select-known-good
compression-index  RELEASE_MANIFEST_INVALID / false / select-known-good
entry-html         ARTIFACT_SIZE_MISMATCH   / false / reject-release
```

manifest 那筆的訊息與 Firefox 實測證據同形。修後三站點皆為
`DELIVERY_ABORTED / true / retry-release`。

**兩個被改的 catch 先前兩側都沒有任何測試覆蓋**——看似相關的
`ARTIFACT_SIZE_MISMATCH` 案例（`:174-193`）其實打在 `:270-274` 的 Content-Length
檢查，根本到不了 `arrayBuffer()`。所以正控制是新補的，並用**突變控制**
（把兩處判斷暫時改成 `if (true)`）證明它能失敗：正控制紅、abort 測試仍綠。

## 重要：這輪瀏覽器重跑**不能**當成 body 路徑的證明

四個 `negative-cancel`（兩瀏覽器 × t0／t1）都回到 `DELIVERY_ABORTED`，
但訊息全是 `release verification aborted`／stage `artifact-fetch`——那是外層
catch（`:400-408`）轉出來的。**修好之後，取消落在 fetch 或 body 輸出完全相同**，
從外部無法分辨走了哪條。這正是修好的定義，卻也表示
**body 路徑修好的證明是 node 測試，不是這輪重跑。**

## 未完成清單的狀態變更

- **第 1 項（finding 028）：完成。**
- **第 2 項（退休 `evidence/sdk-r8-post-023-fix/`）：改為原地退休、不刪除。**
  08-08 寫的解鎖條件（R8-C 已在 `sdk-r8` 綁對）確實滿足了，但逐路徑查證發現
  **另一個當時沒列到的阻擋因素**：`driver-stderr/`、
  `service-worker-firefox-injected-path/`、`service-worker-unified/`
  **只存在於舊根**，分別是 [025](findings/025-webdriver-script-injection-never-ran-on-firefox.md)
  與 [014](findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md) 的主要證據，
  `specs/SPEC-R8-D-production-validation.md:259` 還整棵引用。
  刪了會讓三份已結案文件失去證據。已加
  `findings/evidence/sdk-r8-post-023-fix/README.md` 標明退休狀態與不可刪除的理由
  （全樹 14 MB）。要真的刪，得先把那三個路徑的引用遷走。
- **第 3～7 項：未動。**

## 更正〈踩過的坑〉：「絕對不能跑 `make`」要再精確一層

**已觀察**：`dist/r8/release-manifest.json` 的前置 `r7-assets` 是 `.PHONY`，
所以鑄 release 的鏈**無條件**重跑——`make -n test-r8-c-static` 現在就會列出
`build_r8_c_release_set.py`（`test-r8-b-static` 則**不會**，實測 grep 計數 0）。
但 `r8_bundle.py:170` 是 `manifest["releaseId"] = expected_release_id(manifest)`
——**id 由 bundle 內容衍生**，而 `build_r8_c_release_set.py:72-76` 的 `rmtree`
只刪 `old_ids - current_ids`。

**正確的形式：重建一定發生，但只有 bundle 輸入變了才會換 id、才會作廢綁定。**
本輪修的 `verified-loader.js` 不在那 17 個 artifact 內，實測跑前跑後 id 逐字不變
（R8-B 兩個、R8-C 三個，由重跑腳本頭尾各印一次自我驗證）。

**紀律仍然維持「重跑期間不跑 `make`」**，但理由改成：避免中途改寫 artifact
擾動進行中的相位，而不是每次都會換 id。

## 本輪新增的量測紀律

- **改一個 catch 之前，先確認它兩側都有測試。** 本輪兩個 catch 兩側都沒有，
  看似相關的既有案例其實打在更前面的閘門上、根本到不了。
- **正控制自己也要證明能失敗。** 用突變（把判斷改成 `if (true)`）跑一次，
  看它是否變紅；不變紅就跟恆真閘門一樣沒資訊。
- **「修好」有時會讓兩條路徑從外部無法分辨。** 這時要明說判定綠燈證明的是什麼、
  不證明什麼，不能拿無法分辨的觀測回頭宣稱某條路徑被驗證過。

## 本輪我犯的錯（供校準）

1. `pgrep`／cwd 那兩個坑沒踩到，但 **cwd 還是漂了一次**——`cd` 寫在
   `&&` 複合指令裡不會持續到下一次呼叫，害一次 grep 找不到 `tools/*.py`。
   一律用絕對路徑仍然是對的。

## 尚未處理

08-08 未完成清單的第 3～7 項原樣保留：release-manifest 殘留層、builder `rmtree`
取捨的記錄、T2、finding 024 是否送 Mozilla、以及更早延後的
heading dropdown／清單／SPEC E1-D §5／Route C／A3。

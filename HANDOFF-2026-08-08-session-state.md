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
>
> **2026-08-11 追記：現在擋路的換成另一件事**——E2-A 的 no-op 沒有後置條件可等，
> 四條出路待你選。見文末〈2026-08-11 追記〉。

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

---

# 2026-08-11 追記：功能線開工，卡在一個產品決定

使用者指示「開始功能線，自主執行」。功能線＝heading dropdown／有序清單／無序清單，
交接文件建議先用最便宜的 discovery profile 把關——也就是 **E2-A**。

## 先做了「Route C 的 E2-A 前置契約」，因為那是 A3 的擋路者

08-06 的產品決定（路線 C：不讀前置狀態）當時只寫進 SPEC E2-A 的 2.6 節敘述，
**條文沒改**：第 4 節的 barrier 流程圖仍以前置狀態讀取開頭、A4 仍寫
`documented-state-noop`。規格已修訂為 **v11**，作廢原文以引用區保留不刪。

## 但實測先否證了路線 C 的一個前提（finding 030）

路線 C 允許同一個 action 被連續派送，這使兩件先前被 `alreadyAtTarget` 遮住的事顯露。
原生 26.8、同一段落、先置入相反狀態再連按三次，每次派送後存 ODT，**判定讀存檔不讀 callback**：

1. **不帶參數的 `.uno:DefaultBullet`／`.uno:DefaultNumbering` 是 toggle。**
   第二次按 `set-list-unordered` 會把段落踢出清單。`svx/sdi/svx.sdi:2251`／`:4985`
   宣告 `SfxBoolItem On FN_PARAM_1`，`sw/.../txtnum.cxx:81-108` 有參數才是 explicit mode。
   **帶 `On=true` 則四個案例全是 setter**，含有序→無序的跨種類轉換。
   與 finding 019 同形狀（派送形式錯，不是能力不存在），修法也相同。**已修。**
2. **值沒變就沒有 STATE_CHANGED。** 已在目標狀態時再按一次，文件正確、command result
   照常抵達且帶正確 `commandName`，但九個案例的第二、三次**全部零 watched payload**。
   E2-A 的 completion 需要「歸屬＋state 後置條件」同時成立，(b) 永遠不會到，
   於是逾時成 `MUTATION_OUTCOME_UNKNOWN`。**是低報不是誤報**，但 SPEC E2-A 第 8 節把
   「no-op 與遺失不可區分」列為 STOP。**未修，需要決定。**

## 唯一擋路的事：第 2 項要走哪條路（使用者決定）

規格第 4 節新增〈路線 C 未決事項〉列四條，**不預設**：

1. **接受低報**——零新機制；但「不知道」變成常態讀數，而且這個選擇本身就落在第 8 節的 STOP 條款上。
2. **路線 A（產品自行推進 scheduler）**——`Scheduler::ProcessEventsToIdle()` 是公開 API，
   v10 已更正「沒有受支援入口」不成立；代價是進共用路徑要跑完整回歸（finding 012 相鄰風險）。
3. **後置條件改讀文件**——最誠實，但需要目前不存在的 readback 能力，自成一輪 discovery。
4. **只用 command result**——歸屬有真值無，是第 4 節當初明確拒絕的做法。**不建議。**

**在這個決定之前跑 A3 沒有意義**：會得到「跨狀態轉換全過、重複派送全 UNKNOWN」，
而那個 UNKNOWN 是設計未定，不是量測結果。第 7 節已把這條寫成 A3 的前置。

## 本輪已完成、與出路選擇無關的部分

- engine 改派參數化 explicit mode（`OXSDK_E2_FORMAT_BARRIER` 內）。
- `e2-format-discovery` 重建為 `abf3598f…`、`e2-scheduler-attribution` 為 `38d15ed4…`。
- **凍結 artifact 未受影響**：關掉旗標重編 E1-B 組態的 `probe_engine.o`
  與既有 `build/e1/editor-v1/probe_engine.o` **逐位元相同**；`e1-editor-v1` 仍 `835b453d…`。
- `tests/test_e2_profile.py` 新增三項釘住派送形式；突變（拿掉 `On`）證明會失敗。
- `make test-e2-a-static` 納入新增的三個檔案（先前只檢查 caret 那組）。
- 兩瀏覽器各重跑一輪 `scheduler-attribution`：5/5 `verified-format-state`、
  postcondition 5/5，與最後一版 sound build 逐項相同。

## 這輪重跑**不能**當成「`On` 參數在 WASM 生效」的證明

那五個派送每一個都是**跨狀態轉換**，而 toggle 與 setter 在跨狀態轉換上結果相同——
`On` 就算在序列化中被丟掉也會照樣 5/5。要證明它生效必須**重複派送**，
而那正是路線 B 的 `alreadyAtTarget` 擋住的。與 finding 028 的
「瀏覽器重跑不能當成 body 路徑的證明」是同一種侷限，留給 A4。

## 本輪新增的量測紀律

- **「連按兩次會怎樣」是移除前置條件讀取之後才存在的問題面。** 原本的正向矩陣全是
  跨狀態轉換，那種矩陣**驗不到**冪等性——toggle 與 setter 在它上面讀數相同。
- **判定用的比較基準要挑對。** 本輪分析器第一版拿 LibreOffice 每次存檔重新編號的
  自動樣式名（P1/L1 對 P2/L2）比對，於是宣稱沒被碰過的段落變了。基準改為
  **同一次 run 的第一份快照**（已過存檔正規化）＋解析到具名 parent 之後才正確。
  拿手寫 fixture 當基準也會有同樣的假陽性。
- **沒重跑量測，只重跑判讀。** 分析器修好後是對同一批已保存的 ODT 重新判讀的，
  不是重跑探針求綠。

## 我在本輪犯的錯

1. 分析器第一版用生成的自動樣式名做比對，得到「未被碰過的清單項變了」的假陽性。
2. 又一次 shell cwd 漂移（在 `study_LiteCore` 下跑 `tools/run_...sh`）。
   交接文件已經寫過這條，我還是踩了；一律用絕對路徑。

## 同一輪另外挖出來的：finding 031（與路線選擇無關，但更早該發現）

barrier 用整串比對判定段落樣式的後置條件（`Heading 1`／`Body Text`）。那兩串是
**UI 顯示名稱**：`SID_STYLE_APPLY` 的狀態放 `UIName` 且**不放 ProgName**，
而 UIName 陣列以 UI 語系為 key、由 `SwResId()` 建。**我方 WASM build 的 `instdir`
已經含 `zh_TW/LC_MESSAGES/sw.mo`**，裡面 `Heading 1`→「標題 1」、`Body Text`→「內文」。

zh-TW UI 之下，那兩個動作的 barrier 會逾時成 `MUTATION_OUTCOME_UNKNOWN`，
**而文件其實已經改對了**。派送那一側安全（送的是 ProgName）。清單三個動作不受影響
（payload 是布林值）。

**今天是潛伏的**：全樹沒有任何路徑會選非英文 UI。但這個專案的產品對象就是 zh-TW。

**未實測，而且說明了為什麼不能就地測**：原生 build 是 `--with-lang=en-US`、`resource/`
下只有 `common`，設 `LANG` 會回退英文——量到「字串沒變」是量測環境的結論，不是產品的
（保證假陰性）。WASM build 有譯文，但 engine 走 `documentLoad(kit, url)` 沒有選項。
最小實測改動已定位未實作：discovery-only 改走
`documentLoadWithOptions(…, "Language=zh-TW")`。

這一項答完了 SPEC E2-A 2.5 節掛了六天的待驗證條目，該節已就地劃掉並填上答案。

## 使用者已回覆兩個決定（2026-08-11）

1. **no-op 缺口走出路 3：後置條件改讀文件。**
2. **finding 031 先做實測**（做了，是假陰性，見下）。

### finding 031 實測：跑了，假陰性，而且更正了我自己的錯

新增隔離 profile `e2-locale-attribution`＝`e2-scheduler-attribution` 只改一件事，
engine 走 `documentLoadWithOptions(…, "Language=zh-TW")`（`OXSDK_E2_UI_LANGUAGE`
編譯期常數，JS 選不了）。Chrome 一輪：**回報字串完全沒變**（仍 `Heading 1`／`Body Text`）、
五個 action 全 `verified-format-state`、postcondition 5/5。

**那不是反證，是我先前寫錯的直接後果。** 我寫「WASM build 已內含 zh-TW 譯文」——
我看的是建置主機的 `instdir/`，但 WASM 出貨的是 emscripten 檔案系統映像。
`soffice.data` 的 1,358 個檔裡 **`.mo` 是 0**、`/instdir/program/resource/` 下只有一個字型，
却有三個 zh-TW registry langpack XCD。**zh-TW 選得到但沒有東西可選**，
`SwResId()` 只能回英文 msgid，所以這條路上不可能印出不同值。
我上一版還預測原生 build 會有這個假陰性（並查了 `resource/`），
然後在 WASM 上踩了同一個坑——差別只在我查錯了樹。

因此 031 的最後一環仍是推論。本輪也**沒有正控制**（沒有譯文時，
問不出「選項到底有沒有生效」）。唯一新增的正面觀察：帶 `Language=` 不會弄壞東西，路是通的。

**留了一個 tripwire 而不是一句備註**：`TestFinding031Tripwire` 在出貨映像出現任何 `.mo`
的當下就會失敗——那既是做 zh-TW 產品的必要步驟，也正是整串比對悄悄失效的那一刻，
而那一刻不會有人想到要回頭重驗 format barrier。突變控制：指向一個含單一 `.mo` 的假 metadata，
它會失敗並印出 finding 編號。

順帶修掉 harness 一個缺陷：dispatch 失敗時不記錄 `formatAfter`——
**因狀態內容而失敗的 barrier ，正好丟掉唯一能解釋它的那個讀數**。

### 出路 3 動手前先量了可行性（SPEC E2-A 2.8 節）

`getCommandValues` 以讀原始碼排除。selection transferable **實測可用**：
`text/html` 下 heading→`<h1>`、無序→`<ul><li>`、有序→`<ol><li>`、離開清單→`<p>`，
五個 action 全可分、跟著 mutation 走、**且與語系無關**（順帶解掉 031 在段落樣式的曝險）。

**三項代價是量出來的**：

1. **游標塌陷時讀不到**（selType 0、0 bytes）。要先 `.uno:GoToStartOfPara` →
   `.uno:EndOfParaSel` 選起整段才讀得到，讀完要還原選取，**還原本身要被驗證**。A5 要加案例。
2. **`Text body` 與預設樣式都是 `<p>`**。分得出「是不是 heading」，分不出 Text body 與 Standard。
   `set-paragraph-body` 的宣稱因此變弱；兩態承諾剛好夠用，但**是縮限，判定要明列**。
3. **這串 HTML 是序列化器輸出，不是有文件的契約。** 整串比對＝把序列化器釘成 ABI，
   跨版本可能變。**未驗證**，屬 A7 回歸該涵蓋。

### 下一步（未動工）

實作 readback barrier：engine 派送後選段→讀 `text/html`→以封閉集合比對→還原選取並驗證。
**規格的契約與三項代價都已寫定（2.8 節），可以直接照著做。**
之後才是 A3～A7。

## readback barrier 已實作並實測（2026-08-11 後半）

engine 的 `OXSDK_E2_FORMAT_BARRIER` 改成路線 C ＋ 文件後置條件，完成事件更名
`verified-format-readback`（證據來源換了，名字就得換）。流程與三項代價寫在
SPEC E2-A 2.9 節。

`e2-format-discovery` WASM `7665308a…`，9 個派送含 **4 次重複派送**，
Chrome 150.0.7871.128 與 Firefox 153.0.1 **逐項相同**：
`verified-format-readback` 9/9、`restoreConfirmed` 9/9、存檔 ODT postcondition 9/9。

正控制是同一個 profile 的前後對照：它先前對五個動作一律回
`EDITOR_FORMAT_STATE_UNAVAILABLE`、文件零變動，現在 9/9 完成且文件如實改變。

**重複派送同時答完兩題**：冪等成立（所以 `On` 參數確實通過我方 worker／engine 路徑——
這正是上午那輪 scheduler-attribution 重跑答不出來的問題），以及無聲 no-op 不再逾時。

實作被實測逼出一項設計：`heading-on-repeat` 讀到 `listTag="ul"` 且 `blockTag="h1"`
（清單裡的 heading）。**只取第一個標籤會讀成 `ul`**，段落樣式後置條件在清單裡就永遠不成立，
所以解析必須把清單種類與區塊標籤分開答。

## 兩個我犯的錯，都已更正並釘住

1. **「目的檔逐位元相同」不是隔離檢查，是擲硬幣**（[finding 032](findings/032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md)）。
   同源同旗標連編 8 次得到兩種目的檔各 4 次，固定差 37 bytes。
   我本輪用它下過三次保證，全部降級；SPEC E2-A 10.6 節更早的同方法保證同樣打折。
   **改用前置處理後的翻譯單元比對**（`-E -P`），E1-B 組態下與 `HEAD` 4,355,327 bytes 逐位元相同——
   那才是直接證明隔離、且不受 codegen 不確定性影響的檢查。
   **未量**：連結後的 profile 雜湊會不會也跳。不要據此推論。
2. **同一個缺陷修了一處、漏了另一處**：`run_e2_discovery.py` 的 postcondition 比對原始
   `text:style-name`，但清單裡的 heading 是自動樣式 `P2`（parent 才是 `Heading_20_1`），
   於是把正確的 barrier 判成失敗。我當天稍早才在 `analyze_e2_a_native_reissue.py` 修掉同一件事。
   **沒有重跑求綠**——先用修好的判定重新判讀同一批已存 ODT 得到 9/9，之後才重跑留乾淨證據。

## 下一步

A3～A7 尚未執行。A3 的兩項前置（路線 C 契約、no-op 可判定性）都已解除，
可以開始跑正式矩陣。第 8 節判定要記得明列 2.8 節的縮限（`set-paragraph-body`
只承諾「不是 heading」）與未驗證項（HTML 是序列化器輸出，跨版本穩定性屬 A7）。


## A3 已完成：`A3_PASS`（2026-08-11）

2 瀏覽器 × 3 fixture × 3 次 = **18 run × 5 派送 = 90 次**，每次同時滿足四項：
completion 為 `verified-format-readback`、`changed` 未宣稱（null）、
`restoreConfirmed` 為 true、存檔 ODT 後置條件相符。每一步各自判定。

新增 `tools/validate_e2_a.py`：**以矩陣展開必要格，不是列舉找得到的 run**——
沒跑過的 fixture 標 `missing` 而不是消失。突變（把 ordered 的期望改成 bullet）
使 18 次 run 全數失敗並逐格指名。

### 又一個「檢查會說謊」的坑（第三個）

`python3 -m py_compile tools/x.py` 會留下 `__pycache__/*.pyc`。若之後在**同一秒內**
改回原檔，Python 會認為快取仍有效而**繼續用舊的 .pyc**——我因此看到「已還原但驗證仍失敗」，
差點把它當成真的失敗。`rm -rf tools/__pycache__` 後恢復正常。
**跑突變控制前後，先清 `__pycache__`。**

### 清單種類要逐層讀

`styled-list` 的 `L1` 是混合定義（level 1 bullet、level 2／3 number）。
第一版 validator 問「這個樣式含不含 numbered level」，把正確的 bullet 清單讀成 number。
同一個順序錯誤在原生分析器也有，一併修掉；以修好的判讀重跑原生已存證據，
**九個案例判定完全不變**（先確認再說不變，不是假設）。

## A4 也完成：`A4_PASS`

每個 action 先驅動到目標，再在**已在目標狀態的段落上**連按兩次。
2 瀏覽器 × 3 fixture × 3 次 × 15 派送＝**270 次**全過（四項條件同前）。
冪等與無聲 no-op 兩題同時關閉，且是矩陣證據不是單點示範。
突變（把 repeat-1 的期望改成 toggle 的行為）使 19 次 run 全紅。

### 下一步

A5 負向與邊界（`state-crosstalk`／`stale-revision`／`timeout-after-dispatch`／
`table-boundary`／`unsupported-action`／`list-teardown`）、A6 次要能力、
A7 round-trip 與回歸。A5 的 `table-boundary` 就是那份還沒用到的 fixture。

## A5：六個案例都跑起來了，其中兩件要處理

| 案例 | 實測 |
|---|---|
| `unsupported-action` | `EDITOR_ACTION_UNSUPPORTED`，派送前擋掉 |
| `stale-revision` | `STALE_REVISION`，帶實際新舊值 |
| `state-crosstalk` | 見 [finding 033](findings/033-readback-barrier-read-wherever-the-caret-went.md)——抓到真缺陷並已修 |
| `table-boundary` | **`verified-format-readback`（完成，不是拒絕）** |
| `list-teardown` | 清單三態循環後 close **11～14 ms**，無 finding 012 類阻塞 |
| `timeout-after-dispatch` | 呼叫端 `TIMEOUT` → 不重試 → 下一個動作 `BUSY` |

### 待處理一：`table-boundary` 的結果與凍結矩陣相反

矩陣寫「typed 拒絕，之後 fresh Worker」——那是**舊設計（選取 barrier）時代寫的期望**。
路線 C ＋ readback 之下，表格儲存格內的段落**照常套用並通過驗證**：
存檔 ODT 顯示 `E1-CELL-A1` 確實進了清單並套上 Heading 1，
而**相鄰儲存格與表格外的段落都沒被動到**。

**這是實測推翻預設，不是缺陷**，但矩陣不能默默跟著改——要照 2026-08-11 那次的做法
補一筆 `revisions`，保留舊期望。**尚未做。**

### 待處理二：`state-crosstalk` 在 table-boundary fixture 仍失敗

其他 fixture 修好後會通過，這份仍回 `EDITOR_FORMAT_POSTCONDITION_FAILED`。
crosstalk 錨點在表格外、派送錨點在儲存格內，finding 033 的座標式還原跨表格邊界時
可能落不回原處——**與 finding 033 記的殘留是同一條**，未歸因。

### 我在 A5 犯的錯

`table-boundary` 第一次跑回 `STALE_REVISION`，看起來像產品結果，**其實是我的 harness**：
`timeout-after-dispatch` 讓一個動作在呼叫端逾時後才完成並推進 revision，
排在它後面的案例就全都拿著過期的 revision 被擋下。試過在案例前後重新同步——
**`getState` 根本不回傳 revision，那個同步是靜默的 no-op**。
真正的修法是把會去同步化的案例排到最後。

## 尚未執行

**A6（次要能力）與 A7（round-trip ＋ 桌面 reopen／PDF ＋ R6～R8／E1 回歸）完全沒動。**
A5 的六個案例只在 Chrome × table-boundary 跑過完整一輪，
其他 fixture 與 Firefox 尚未補齊，也還沒寫進 validator 判定。

## 2026-08-11 覆核（fable）：三個卡點的結論，以及我一個要更正的說法

### 更正：table-boundary 的證據被我歸錯案例

我寫「存檔 ODT 顯示 `E1-CELL-A1` 確實進了清單並套上 Heading 1」。**兩半都歸錯了**：

- **Heading 1 是 `state-crosstalk` 案例做的**，不是 table-boundary 做的。crosstalk 在同一個錨點
  （`E1-CELL-A1`）派送 `set-paragraph-heading`，**mutation 成功、只有讀取失敗**。
  table-boundary 案例只派送 `set-list-unordered`，判定也只看 `listTag`。
- **最終 ODT 的清單狀態是 `timeout-after-dispatch` 留下的**（它最後派送 `set-list-ordered` 並完成）。
  我拿「所有案例跑完的最終存檔」去驗一個中間案例——那份檔案描述的不是它。

**結論本身不變**（表格儲存格內是完成不是拒絕），但**站得住的證據是該案例自己的 readback**
（`listTag='ul'`），不是最終 ODT。這反過來也證明 crosstalk 的 **mutation 是對的、錯的只有讀取**——
是偽陰性。

### 卡點一：殘留是真的，但我把量級寫反了

`restorePoint` 在派送**前**擷取、還原在 mutation **後**執行，座標跨越一次 reflow——**這是結構性的**。
**縮高類**（heading→body、離開清單）平常就會踩到；**增高／縮排類**不會，這解釋了為何
555 次正向派送一次都沒碰到。finding 033 寫「極端重排」是低估。

我 2970 行的註解推理也有瑕疵：「派送可能移動游標所以要在派送前擷取」——這五個封閉動作
**不會**把游標移出目標段落，真正需要的不變量是「還原回同一段」，派送前擷取反而保證幾何過期。

**LOK 並非沒有身分錨點**：`.uno:InsertBookmark`／`.uno:JumpToMark`／`.uno:DeleteBookmark` 都是可派送 slot，
`getCommandValues(".uno:Bookmarks")` 已實作。代價是多一筆 model mutation。

**更便宜的修法（不需新 API）**：barrier in-flight 時 `search`／`placeCaret`／`select` **目前不被 BUSY 擋**，
這正是 crosstalk 能存在的原因。把移動游標類命令也納入 BUSY 閘之後，
`restorePoint` 就可以改在**命令結果返回後、選段落前**擷取——capture 與 restore 之間不再有 reflow，
座標殘留整個消失。

### 卡點二：我的座標假說站不住，而且證據被 harness 丟掉了

**引擎失敗時已經送出完整 readback（含 2048 bytes 的原始 HTML），但 `sdk-worker.js` 的
`case "error"` 只轉發五個固定欄位，`formatBarrier` 整包被丟掉。**
這同時違反矩陣自己的 `postconditionFailure`（明寫「carries the observed tags and the raw markup」）
與 engine 註解自陳的理由。**程式碼知道，管線把它弄丟了。**

最便宜的判別實驗因此不是新實驗：**改 `sdk-worker.js` 一處（純 JS、不重編 wasm）**，重跑一次，
用 `readback.html` 直接分辨三個假說（讀到 crosstalk 段＝時序劫持／空 markup＝選取被塌掉／
儲存格段但 tag 不符＝才輪到座標假說）。

更強的對手假說：barrier 狀態機靠**無歸屬的** `TEXT_SELECTION` 回呼推進，
crosstalk 的 search 會產生選取，**可以替 barrier「按下一步」**。

### 卡點三：方向同意，但範圍比我寫的窄，且漂移已逾期

- 已證的只有**收合游標、單一儲存格、Chrome**。`negative/` 底下**沒有 firefox**，
  矩陣門檻 `negativeRepetitionsPerBrowser: 1 × 兩瀏覽器`**尚未滿足**。
- 凍結預期的正文在 **SPEC E2-A 的 A5 表格**，不只矩陣的 `negativeCases` 名單——兩處都要補。
- **harness 已經先行實作了新預期**（app 的 expects 寫「typed outcome, and the document agrees」，
  註解自承與矩陣相反）。凍結文件與執行中的 harness **今天就是分歧的**——補修訂不是選項，是逾期。
- `requiredProperties`／`decisionPolicy` 不用動。

### 我沒問、但更嚴重：styled-list 的 crosstalk PASS 不健全

`A5_CROSSTALK_ANCHORS["styled-list"] = "E1-STYLED-HEADING"`，而那段**本來就是 `Heading_20_1`**，
crosstalk 派送的又是 `set-paragraph-heading`。**我把 finding 033 警告的那個陷阱直接蓋進了測試裡**：
styled-list 的 PASS 無法區分「還原成功讀對段」與「劫持讀到 crosstalk 段（也是 h1）」。
multi-paragraph／plain-grapheme 的 PASS 才是健全的（錨點是 body，劫持會失敗）。

便宜修法：換一個非 heading 的 crosstalk 錨點，或在 readback 加**文字回聲檢查**
（比對派送段的已知文字——fixture 文字唯一，這本身就是零 API 的段落身分代理，也能反哺卡點一）。

### 建議動作順序（fable）

修 `sdk-worker.js` 的 error 轉發 → 重跑 table-boundary 拿 `readback.html` 歸因卡點二 →
依歸因決定卡點一走「原子化＋結果後擷取」或書籤 → 補 firefox 負向輪 → 才寫卡點三的修訂條目。

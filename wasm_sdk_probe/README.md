# wasm_sdk_probe

LibreOffice 26.8 headless WASM Document SDK 實驗。R1 證明 Writer 的
open／render／insert／save 垂直切片可行；R2 在同一個 core artifact 外建立版本化 C ABI、
Dedicated Worker 與 TypeScript-first public API，使應用層不必接觸 Emscripten、MEMFS、
WASM pointer、UNO 或原始 LibreOfficeKit callback；R3 再加入帶 revision guard 的 search、
selection、replace、undo、comment 與 tracked-change 語意操作；R4 則建立 Provider contract 1.0、
operation validator、Web／desktop adapters 與獨立 Provider Worker；R5 再加入 `full-qa`、
`writer-review`、`writer-reader` profile、字型資源分包、content hash 與 immutable cache contract。
R6完成雙client review-first reference application；R7完成真實輸入、ODT-first相容性與longevity corpus；
R8已完成並判定`PARTIAL_GO_LOCAL_DELIVERY`；E1-A經verified-selection barrier解除Finding 016停止條件後完成，
E1-B也已交付隔離的窄版Editor Contract與host shell；E1-C矩陣跑完並曾判定`E1_GO_ODT_EDITOR`，
但2026-08-07兩次重連結使證據脫離出貨artifact，現行裁決`E1_STOP_OR_RESCOPE`（待重取證據，能力邊界不變）。

## 前置條件與建置

- `../wasm-lite/build-headless-probe/` 已依 R1 spec 建置完成。
- 使用 `../wasm-lite/tools/emsdk/` 的 Emscripten 4.0.10。
- 瀏覽器必須支援 SharedArrayBuffer，並透過 `web/serve.py` 的 COOP／COEP headers 載入。

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
make -C wasm_sdk_probe r5
```

Makefile 會直接選用專案內的 Emscripten 4.0.10，避免誤用系統的 3.1.69；仍不要 source
`qt6-poc-env.sh`，因為該腳本會切換目前目錄，而且本 probe 不依賴 Qt6 build。
`LOSRC` 與 `LOBUILD` 可在 `make` 命令列覆寫。建置採核外 linkdeps，不修改
LibreOffice core、不連 unoembind，也不使用 JSPI 或 `PROXY_TO_PTHREAD`。

## R5 profiles

- `full-qa`：保留 R1～R4 assertions、profiling 與 legacy harness，作診斷／回歸基線。
- `writer-review`：`-Oz` product link，保留 R4 review 與 Provider 能力。
- `writer-reader`：只輸出 open／render／search／save／cancel C ABI；edit、comment、redline 會得到
  typed `UNSUPPORTED_OPERATION`。
- `writer-automation`：本輪明確標示 `not-shippable`，不以 raw UNO／unoembind 冒充產品 API。

`soffice.data` 會拆成 34.18 MB base、19.48 MB startup CJK 與 49.10 MB optional fallback-font
pack。Profile manifest 將 Emscripten logical filename 映射到 SHA-256 content-hashed artifacts；測試
server 只對 hash artifact 發 `immutable`，HTML、Worker entry 與 manifest 維持 `no-cache`。

## Document／Provider SDK

Document SDK 位於 `sdk/`：

- `document-sdk.js`：無相依 ES module，提供 Promise、AbortSignal、timeout 與 typed errors。
- `document-sdk.d.ts`：完整 TypeScript public surface。
- `sdk-worker.js`：唯一載入 `probe.js`、持有 FS／heap 並呼叫 C ABI 的 Dedicated Worker。
- `manifest.json`：SDK、Worker protocol、C ABI、core commit 與 capability metadata。

Provider SDK 位於 `provider-sdk/` 與 `providers/`：

- `provider-sdk.js`／`.d.ts`：contract 1.0、registry、host、validators 與 adapters。
- `fixtures/text-translate.json`：Web／desktop binding 共用的 canonical domain fixture。
- `text-translate-descriptor.js`：主執行緒可發現的 immutable provider metadata。
- `text-translate-worker.js`：不載入 Document SDK 的 Dedicated Worker entry。

最小使用方式：

```js
import { createDocumentEngine } from "./document-sdk.js";

const engine = await createDocumentEngine({
  workerUrl: "./sdk-worker.js",
  timeoutMs: 30_000,
});
const doc = await engine.open(odtArrayBuffer, {
  name: "input.odt",
  transfer: true,
});
const tile = await doc.render({ canvasWidthPx: 512, canvasHeightPx: 512 });
await doc.click(1200, 1200);
await doc.insertText("測");

const match = await doc.search("LibreOfficeKit");
const selection = await doc.getSelection();
await doc.replaceSelection("LOK-R3", {
  expectedRevision: selection.revision,
});
await doc.undo({ expectedRevision: doc.revision });

await doc.addComment("R3 review note", {
  author: "OxOffice SDK",
  expectedRevision: doc.revision,
});
await doc.setTrackChanges(true, { expectedRevision: doc.revision });
const comments = await doc.listComments();
const changes = await doc.listTrackedChanges();

const output = await doc.save({ format: "odt" });
await doc.close();
engine.dispose();
```

Provider 使用方式：

```js
import {
  ProviderHost,
  ProviderRegistry,
  WorkerProviderAdapter,
  createWebDocumentAdapter,
} from "./provider-sdk/provider-sdk.js";
import { descriptor } from "./providers/text-translate-descriptor.js";

const registry = new ProviderRegistry();
registry.register(descriptor, new WorkerProviderAdapter({
  workerUrl: new URL("./providers/text-translate-worker.js", import.meta.url),
  providerId: descriptor.id,
}));
const host = new ProviderHost({ registry });

await doc.search("English words");
await host.invokeSelection({
  providerId: descriptor.id,
  endpointId: "translate-selection",
  documentAdapter: createWebDocumentAdapter(doc),
  parameters: { "target-language": "zh-TW" },
});
```

Provider 只收到 immutable selection snapshot、`AbortSignal` 與 progress callback。它回傳的
`replaceSelection` operation 必須先通過 capability、schema、UTF-8 size 與 snapshot revision
驗證，之後才由 Host 呼叫 Document SDK；Provider 本身拿不到 document／UNO／Emscripten runtime。

`transfer: true` 會把輸入 ArrayBuffer ownership 移給 Worker，caller 不可再使用；預設
`false` 會先複製。render 與 save 的輸出則由 Worker 從 WASM-owned buffer 複製後，以
transferable ArrayBuffer 交給應用層。close 後的 document、或 `engine.restart()` 前取得的
document 都不能再操作。

目前 core 同時只允許一份 Writer ODT。所有 mutation 都要求 `expectedRevision`；不相符會得到含
expected/current details 的 `StaleRevisionError`，且不修改文件。Cancel 只保證能取消尚在 C
queue 的 request；已進入同步 LOK call 的工作不會被 thread kill。timeout／AbortSignal 會立即拒絕 public Promise，並送出
best-effort cancel。

## 執行與驗證

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 web/serve.py
```

- R4 Provider SDK harness：<http://127.0.0.1:8765/r4.html>
- R5 reader product harness：<http://127.0.0.1:8765/r5-reader.html?profile=writer-reader>
- R5 review product harness：<http://127.0.0.1:8765/r4.html?profile=writer-review>
- R3 semantic review harness：<http://127.0.0.1:8765/r3.html>
- R2 相容／conformance harness：<http://127.0.0.1:8765/r2.html>
- R1 相容 harness：<http://127.0.0.1:8765/index.html>

R4 頁面的 **Run R4 Provider Flow** 驗證 selection snapshot、Provider Worker progress、concurrent
edit stale rejection、undo、validated replace 與 save；**R4 Provider Conformance** 驗證 contract
discovery、Worker 隔離、越權 operation 阻擋與取消不落地。R3 頁面的 **Run R3 Review Flow** 執行
search／selection／replace／stale guard／undo／comment／
tracked changes／save；**R3 ABI Conformance** 驗證 1.0 client 相容、1.2／2.0 拒絕、capabilities
與無 generic UNO surface。R2 頁面的 **R2 Conformance** 仍可驗證
Abort／timeout cancel、stale／invalid handle、double-close、ABI mismatch、零 request ID、
invalid argument、input／output ownership、10 輪 open/render/close，以及實際 Worker error 後
restart recovery。自動化命令：

```bash
make test-r4
make test-r5

python3 tools/run_browser_probe.py \
  --browser chrome \
  --doc test-docs/t1-plain-zh.odt \
  --cache cold \
  --samples 3 \
  --url 'http://127.0.0.1:8765/r4.html?memory=skip' \
  --evidence-dir ../findings/evidence/sdk-r4/browser-raw

python3 tools/run_r4_conformance.py \
  --browser firefox \
  --evidence-dir ../findings/evidence/sdk-r4/conformance

python3 tools/validate_r4_roundtrip.py \
  --raw-dir ../findings/evidence/sdk-r4/browser-raw \
  --output ../findings/evidence/sdk-r4/roundtrip.json

python3 tools/validate_r5_artifacts.py \
  --base-url http://127.0.0.1:8765
```

`memory=skip` 只略過成本較高的瀏覽器記憶體 API，不影響功能或時間量測。Runner 直接使用
Chrome DevTools Protocol 或 Firefox WebDriver；不需新增 Python package。

## C ABI 與執行緒

`src/sdk_api.h` 定義 ABI 1.1（`0x00010001`）、固定寬度 request／document handle、穩定
status code、capability bits，以及唯一公開的 buffer alloc／free 邊界。C exports 只驗證參數、
同步複製 borrowed input 並 enqueue；所有 LibreOfficeKit 操作由單一 engine pthread 依序執行。
相容規則接受同 major 且 client minor 不高於 runtime 的版本，所以 1.1 runtime 可服務 1.0
client。公開 entry points 只接受固定語意操作，呼叫端不能傳任意 `.uno:*` command。

Worker protocol v1 以非零 request ID 對應每個結果。公開事件只包含 `view-ready`、
`document-invalidated` 等語意，不把 LOK callback id 70 的 payload 當成應用契約。

Core exports 尾端包含只能由 `libunoembind.a` 供應的 bridge RTTI；本 probe 排除該批 exports，
只補回 `documentLoad` catch 所需的 UCB exception RTTI，並 wrap 未使用的 JavaScript UNO
scripting 初始化。證據見
[`../findings/010-probe-export-list-requires-unoembind.md`](../findings/010-probe-export-list-requires-unoembind.md)。

## R6 協作 Reference Application

R6 沿用 R5 `writer-review` loader／WASM／resources，只用 R6 專用 Worker entry 修正正常
search-not-found response。建置前端資產、跑 contract 與完整 release gate：

```bash
make r6-assets
make test-r6-c
node tools/run_r6_contract.mjs --evidence-dir ../findings/evidence/sdk-r6/contract
python3 tools/validate_r6_roundtrip.py
python3 tools/validate_r6_release.py
```

啟動只綁 loopback 的 reference service：

```bash
node tools/serve_r6_reference.mjs --port 8765
```

人工驗收請用兩個獨立 browser context（最簡單是 Chrome 與 Firefox 各一個），分別開啟：

- Alice：<http://127.0.0.1:8765/r6-reference.html?role=alice>
- Bob：<http://127.0.0.1:8765/r6-reference.html?role=bob>

兩頁 ready 後可依序驗收：

1. 兩端按 Heartbeat／刷新，確認 presence 顯示 Alice、Bob 與各自 viewed version。
2. Bob 建 comment；Alice 刷新後回覆並 resolve。兩頁仍顯示 v1、SDK revision 不變。
3. Bob 搜尋 `LibreOfficeKit`，按 Provider suggestion；原文件不變，只增加一筆 sidecar suggestion。
4. Alice 刷新、Acquire、接受第一筆 open suggestion；畫面應明確前進 v2。
5. Bob 按重連 events 後顯示 stale；按明確重新載入，再搜尋 `R4 Provider：LibreOfficeKit`。
6. 可先在搜尋欄放入目前版本中存在的文字，再按「本機 edit + save」保留未提交 bytes；accept／edit 後
   搜尋欄會同步成 replacement。若另一端先提交，舊 ETag 會顯示權威／本機 base，不覆蓋 v2。下載權威
   版本與下載未提交 bytes 是兩個分開的動作。
7. Provider／Document Worker crash、anchor failure 與 event retention 的完整 deterministic 負向情境由
   `tools/run_r6_reference.py` 自動執行；人工 UI 只作輔助，不取代 machine evidence。

R6 最終判定 **GO**：reader Chrome／Firefox 6/6、contract domain／HTTP 24/24、同瀏覽器完整雙 context
6 runs、mixed-browser 1 run、7 份 ODT/PDF round-trip 與 R1～R5 回歸全數通過。總結見
[`../findings/evidence/sdk-r6/summary.json`](../findings/evidence/sdk-r6/summary.json)。finding 012 的 styled
fixture 特定 close timeout 仍待最小化，不影響規格必要 t1／t3 corpus。

## R7-A input／format discovery

R7-A 沿用 R5 `writer-review` artifact，不修改 core。建立 frozen ODT／DOCX／corrupt／unknown corpus、host
composition adapter、Unicode／plain-text clipboard probe、10-cycle lifecycle、3-crash recovery 與 process
RSS/PSS baseline：

```bash
python3 tools/validate_r7_preflight.py --phase before
python3 tools/create_r7_corpus.py --output test-docs/r7
python3 tools/validate_r7_corpus.py --manifest test-docs/r7/manifest.json
make r7-discovery-assets test-r7-a-static
python3 tools/run_r7_discovery.py --browser chrome --lifecycle-cycles 10 --crash-cycles 3
python3 tools/run_r7_discovery.py --browser firefox --lifecycle-cycles 10 --crash-cycles 3
python3 tools/validate_r7_a.py
python3 tools/validate_r7_preflight.py --phase after
```

R7-A 最終為 **PARTIAL GO**：兩 browser 的 composition/Unicode/clipboard adapter、ODT XML→desktop
PDF、typed corrupt recovery 與 lifecycle 全通過；合法 DOCX 使用 `.docx` 名稱會被 C ABI 前置驗證拒絕，
故 `open-docx` 保持 unsupported，詳見 finding 013。Chrome／Firefox 的 Fcitx5 Chewing commit/cancel 與
user-gesture plain-text clipboard headed evidence 已通過；Firefox read 需逐次確認 Paste prompt。人工頁為
<http://127.0.0.1:8766/r7-discovery.html?manual=1>。

## R7-B～D 最終結果

R7-B bounded input／plain-text clipboard、R7-C 28份相容性corpus，以及R7-D usability／longevity harness均可由
同一批資產建立與跑靜態檢查：

```bash
make r7-assets test-r7-d-static
python3 tools/run_r7_input.py --browser chrome
python3 tools/run_r7_input.py --browser firefox
python3 tools/run_r7_usability.py --browser chrome
python3 tools/run_r7_usability.py --browser firefox
```

R7-B automatic在Chrome／Firefox各3/3通過，並沿用R7-A雙瀏覽器Fcitx5 Chewing／clipboard真實evidence；
Cangjie／Pinyin保持未驗證。R7-C正式matrix與R7-D正式longevity已在Finding 012 remediation後完成：

```bash
python3 tools/run_r7_longevity.py --browser chrome --scenario s5-normal --s5-variant open
python3 tools/run_r7_longevity.py --browser firefox --scenario s5-normal --s5-variant open
```

Document SDK會在10秒bounded close timeout後回收該Worker並啟動新generation；原始t2在Chrome／Firefox各3/3
recovery close，S5 normal／known通過。C的28份corpus與兩瀏覽器正式矩陣全部通過，判定ODT-first部分GO。

Chrome完整50-cycle fresh/reuse、20-crash、30-minute soak通過。Firefox一般／reuse／30-minute與S5通過，
但fresh 35/50及crash recovery 19/20後出現新Worker init timeout，詳見finding 014。因此R7整體為
**部分 GO（ODT-first）**；不承諾DOCX、未測輸入法、完整accessibility或Firefox無限Worker generation。

## R8 delivery

R8不重做R5 artifact或R7 corpus，先從host delivery層建立release identity、防混版、Service Worker、offline、
rollback與production-shaped驗證。R8-A discovery可重現命令：

```bash
python3 tools/validate_r8_preflight.py --phase before
make r8-discovery-assets test-r8-a-static
python3 tools/run_r8_discovery.py --browser chrome
python3 tools/run_r8_discovery.py --browser firefox
python3 tools/validate_r8_preflight.py --phase after
python3 tools/validate_r8_a.py
```

R8-A為**PARTIAL GO**：17-role closed graph、Chrome／Firefox T0/T1、COOP／COEP／CORS／CORP、gzip、
deterministic faults與115 MB WASM cache跨重啟驗證皆通過。Brotli CLI、真quota、public document font
inventory與T2 HTTPS環境是明列缺項；Finding 015要求後續loader以decoded bytes＋SHA-256驗證完整性，不能只靠
`fetch()` rejection。正式結果見
[`../findings/evidence/sdk-r8/discovery/summary.json`](../findings/evidence/sdk-r8/discovery/summary.json)。

R8-B versioned direct delivery可重現命令：

```bash
python3 tools/validate_r8_b_preflight.py --phase before
make r8-delivery-assets test-r8-b-static
python3 tools/run_r8_delivery.py --browser chrome
python3 tools/run_r8_delivery.py --browser firefox
python3 tools/validate_r8_b_roundtrip.py
python3 tools/validate_r8_b_preflight.py --phase after
python3 tools/validate_r8_b.py
```

R8-B為**PARTIAL GO**：standard/full-fidelity bundles、Chrome／Firefox各T0 44＋T1 39 cases、identity/gzip
3 cold＋3 warm、88 negative、known-good recovery及8份desktop roundtrip全部通過。Brotli CLI缺席與
full-fidelity 218,473,422 bytes超過凍結200,000,000-byte門檻仍是明列缺口；最終bundle也已封閉
`locateFile()`未知logical path。正式結果見
[`../findings/evidence/sdk-r8/delivery/summary.json`](../findings/evidence/sdk-r8/delivery/summary.json)。

R8-C／D可重現的主要命令：

```bash
make r8-service-worker-assets test-r8-c-static
python3 tools/run_r8_service_worker.py --browser chrome --suite full
python3 tools/run_r8_service_worker.py --browser firefox --suite full
python3 tools/validate_r8_c_preflight.py --phase after
python3 tools/validate_r8_c.py
make test-r8-d-static
python3 tools/run_r8_production.py --phase compatibility --browser chrome
python3 tools/run_r8_production.py --phase soak --browser chrome --minutes 30 --interval-ms 60000
python3 tools/run_r8_production.py --phase regression
python3 tools/validate_r8_d.py
```

R8-C為`PARTIAL_GO`：Chrome／Firefox T0/T1的atomic stage／activate、client pin、offline、repair、rollback、
interrupt及deterministic storage failure全部通過。R8-D最終為`PARTIAL_GO_LOCAL_DELIVERY`：13項safety checks
全為true；Chrome同一active cached release完成28/28份corpus及30.038分鐘soak。Firefox在R8-C後觸發Finding 014，
兩次combined campaign均在第一批前timeout，故其summary保持`pass:false`，只以R7完整corpus／30分鐘soak加
R8-C active-release矩陣形成明列的部分GO組合證據。沒有T2、真quota且candidate仍需顯式reload，因此不宣稱
production CDN SLA。總結見
[`../findings/evidence/sdk-r8/summary.json`](../findings/evidence/sdk-r8/summary.json)。

R8規格入口：

- [`SPEC-R8-000`](../specs/SPEC-R8-000-overview.md)：整體範圍、邊界、topology與GO／部分GO／停止條件。
- [`SPEC-R8-A`](../specs/SPEC-R8-A-delivery-discovery.md)：release graph、browser/origin、manifest、font與fault discovery。
- [`SPEC-R8-B`](../specs/SPEC-R8-B-versioned-artifact-delivery.md)：versioned bundle、預壓縮、headers與verified loader。
- [`SPEC-R8-C`](../specs/SPEC-R8-C-offline-update-recovery.md)：Service Worker原子更新、offline、rollback與eviction。
- [`SPEC-R8-D`](../specs/SPEC-R8-D-production-validation.md)：T0/T1自動矩陣、可選T2 HTTPS拓樸與R6/R7正式回歸。

基本編輯器不塞進R8；它延後到R8完成後另立spec，並在R10深層裁切前完成或至少凍結功能corpus。R9
Automation維持需求驅動的獨立backlog。完整後續順序見
[`SPEC-R6+ roadmap`](../specs/SPEC-R6+-roadmap.md)。

## E1 ODT-first基本編輯器

E1不以legacy raw key、raw LOK callback、任意UNO或canvas假caret交付編輯器。第一階段只做editing discovery，
驗證文件化caret／selection geometry、closed keyboard action、delete／paragraph／line break、Undo／Redo與最低
bold／italic／heading／list語意能否形成typed、revision-guarded、exactly-once contract。

規劃入口：

- [`SPEC-E1-000`](../specs/SPEC-E1-000-overview.md)：產品範圍、A→B→C路由與GO／部分GO／停止條件。
- [`SPEC-E1-A`](../specs/SPEC-E1-A-editing-discovery.md)：A0～A6 discovery、fixture、門檻與evidence。
- [`SPEC-E1-B`](../specs/SPEC-E1-B-narrow-editor-contract.md)：八個產品action、typed state、session與host shell。
- [`SPEC-E1-C`](../specs/SPEC-E1-C-editor-validation.md)：input／clipboard、ODT corpus、recovery、lifecycle與最終E1 gate。
- [`e1/discovery-matrix-v1.json`](e1/discovery-matrix-v1.json)：凍結的browser、operation、negative與threshold matrix。
- [`e1/validation-matrix-v1.json`](e1/validation-matrix-v1.json)：E1-C凍結的整合、corpus、recovery與人工最小矩陣。

E1-A可重現命令：

```bash
python3 tools/validate_e1_preflight.py --phase before
make e1-discovery-assets test-e1-a-static
python3 tools/run_e1_discovery.py --browser chrome
python3 tools/run_e1_discovery.py --browser firefox
python3 tools/validate_e1_roundtrip.py
python3 tools/validate_e1_preflight.py --phase after
python3 tools/validate_e1_a.py
```

結果為`STOP_OR_RESCOPE`：兩瀏覽器的backward delete各3/3可由visible-cursor callback完成；forward delete則
已刪除`A`並save成合法ODT，卻沒有任何可歸屬的documented completion callback，request只能timeout且不得retry。
Machine summary為`complete:true`、`stoppedEarly:true`；依spec省略停止後的Firefox其餘fixture與E1-B／C。

後續[Finding 017](../findings/017-lok-collapsed-selection-readback.md)已修正空selection readback並完成artifact重建、
SDK測試與headed驗證。Finding 016最終不採用`StateWordCount`：隔離profile以closed unit selection、typed callback、
public readback與固定Delete／Backspace形成verified-selection barrier。Chrome／Firefox各24/24正向案例及4/4邊界
拒絕通過，十份ODT再通過desktop LibreOffice reopen／PDF export，decision為
`SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART`。

Finding 016已解除阻斷；段落／table cell邊界拒絕後需fresh Worker且不得retry。其後E1-A已完成Chrome／Firefox各
五個fixture與10份desktop ODT／PDF round-trip，最終判定 **`PARTIAL_GO_TO_E1_B`**。成立能力為character
caret／selection、雙向delete、paragraph／line break、public Undo及bold／italic；line navigation、Redo、drag
handles、paragraph/list與structural boundary editing保持unsupported。Line callback的不確定性另記
[Finding 018](../findings/018-lok-line-navigation-completion-nondeterministic.md)。

E1-B建立獨立`e1-editor-v1`產品profile，只開放字元左右移動／延伸selection、雙向delete、paragraph／line break、
explicit bold／italic；文字commit、click、Undo與save沿用Document SDK。Line navigation、Redo、drag／handles、
paragraph/list、structural boundary editing、任意key code與UNO command維持unsupported。

建置與完整自動驗證：

```bash
make e1-editor-assets test-e1-b-static
python3 tools/run_e1_b.py --browser chrome
python3 tools/run_e1_b.py --browser firefox
python3 tools/validate_e1_b.py
```

人工查看非必要；若要檢視shell，可啟動既有本機server後開啟`http://127.0.0.1:4173/e1-editor.html`。最終Chrome／
Firefox各27筆操作、兩份ODT desktop round-trip及R6～R8／E1-A regression全部通過，machine decision為
**`GO_TO_E1_C`**。證據見
[`editor-contract summary`](../findings/evidence/sdk-e1/editor-contract/summary.json)。

E1-C不新增Editor ABI，將E1-B產品shell與host-owned IME／plain-text clipboard整合。可重現命令：

```bash
make e1-editor-validation-assets test-e1-c-static
python3 tools/run_e1_c.py --browser chrome
python3 tools/run_e1_c.py --browser firefox
python3 tools/validate_e1_c.py --run-regression
```

Chrome 150／Firefox 153共48個cases、48份ODT內容驗證、16份desktop reopen／PDF及每browser 10個bounded
lifecycle session全部通過；兩browser各一份集中Fcitx5 Chewing／clipboard人工evidence也通過。Final summary為
`automaticPass:true`、`complete:true`、`decision:E1_GO_ODT_EDITOR`。此GO只承諾縮限的ODT-first editor；
Cangjie／Pinyin、line navigation、Redo、drag／handles、paragraph／list、structural editing、DOCX與rich clipboard仍
不在E1 v1承諾。證據見
[`editor-validation summary`](../findings/evidence/sdk-e1/editor-validation/summary.json)。

**上述數字描述的是當時的artifact。** 2026-08-07的E1-D與底線／刪除線兩次重連結之後，48個case與人工輪
記錄的hash都不再等於`dist/profiles/e1-editor-v1/`的現況。`validate_e1_c.py`現在對**每個**自動case做這項
比對（`artifactBinding`，見`inventory/artifact-binding.json`），因此現行裁決為`E1_STOP_OR_RESCOPE`。
回到GO需雙瀏覽器重跑四個自動相位與各一輪人工Chewing，全部對`835b453d…`。

Finding 016隔離實驗可重現命令：

```bash
make finding-016-selection-barrier-assets test-finding-016-selection-barrier-static
python3 tools/run_finding_016_selection_barrier.py --browser chrome --timeout 600
python3 tools/run_finding_016_selection_barrier.py --browser firefox --timeout 600
python3 tools/validate_finding_016_selection_barrier.py --desktop-roundtrip
```

詳見[`Finding 016`](../findings/016-lok-forward-delete-completion-gap.md)、
[`selection-barrier summary`](../findings/evidence/016/selection-barrier-wasm/summary.json)與
[`E1 A6 summary`](../findings/evidence/sdk-e1/discovery/summary.json)、
[`E1 DEVLOG`](../devlog/DEVLOG-2026-08-05-wasm-sdk-e1.md)。

### Finding 012 native／WASM 歸因

以下target建立隔離的native LOK probe與diagnostic WASM profile；不覆蓋R5 `writer-review`：

```bash
make finding-012-attribution-assets
python3 tools/run_finding_012_attribution.py --layer native \
  --evidence-root ../findings/evidence/012/r7-attribution
python3 tools/run_finding_012_attribution.py --layer wasm --browser chrome \
  --evidence-root ../findings/evidence/012/r7-attribution
python3 tools/run_finding_012_attribution.py --layer wasm --browser firefox \
  --evidence-root ../findings/evidence/012/r7-attribution
python3 tools/validate_finding_012_attribution.py \
  --evidence-root ../findings/evidence/012/r7-attribution
```

diagnostic profile只在`LibreOfficeKitDocument::destroy()`前後發出`stage`。正式結果確認兩個瀏覽器都已進入
destroy，原始t2不返回而unwrapped返回；系統native LibreOffice 26.2.4則兩者都正常。這排除Worker queue未派送，
但仍需same-commit native build才能區分core版本與Emscripten特有行為。

Same-commit native 26.8完成後，以既有runner與最終validator執行：

```bash
python3 tools/run_finding_012_attribution.py --layer native \
  --native-install-path ../native-lok-26-8/build/instdir/program \
  --native-source ../native-lok-26-8/src \
  --evidence-root ../findings/evidence/012/native-26-8-attribution
python3 tools/validate_finding_012_native_26_8.py \
  --evidence-root ../findings/evidence/012/native-26-8-attribution \
  --wasm-evidence-root ../findings/evidence/012/r7-attribution \
  --build-dir ../native-lok-26-8/build
```

原始t2與unwrapped在same-commit native各3/3正常，最終判定為
`EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY`，下一步是R7 `wasm-fix`，不再新增歸因階段。

## 結果

R5 技術閘門判定 **GO**。`writer-review` WASM raw 從 169.26 MB 降為 115.27 MB，gzip -9
從 45.59 MB 降為 40.86 MB；base+CJK 首載資源從 102.77 MB 降為 53.66 MB。Chrome 150／
Firefox 152 的 review 6/6、reader cold 6/6、reader warm-cache 6/6 全部通過，18 份產品 profile
輸出 ODT 都通過桌面 round-trip。完整資料見
[`../DEVLOG-2026-08-01-wasm-sdk-r5.md`](../devlog/DEVLOG-2026-08-01-wasm-sdk-r5.md)與
[`../findings/evidence/sdk-r5/summary.json`](../findings/evidence/sdk-r5/summary.json)。

### R4 基線

R4 技術閘門判定 **GO**。Chrome 150 與 Firefox 152 各 3 次 Provider flow，6/6 完成 discovery、
selection snapshot、progress、stale rejection、undo、validated replace 與 save。6 份 ODT 都含預期
Provider 文字、不含 concurrent edit／raw UNO 文字，且桌面 LibreOffice 26.2.4.2 全數可轉成 PDF。
Provider conformance、R3 完整 review flow、R2 conformance 與 R1 legacy flow 也都跨兩個瀏覽器
通過；Provider Worker 與主執行緒都沒有 Emscripten runtime surface。

Core runtime 維持 raw 259.78 MiB、gzip -9 84.60 MiB，與 R3 byte-for-byte 相同。R4 browser
Provider layer 新增 raw 45,229 bytes、各檔 gzip -9 合計 12,028 bytes。依研究決策只記錄體積；
optimization、scripting、字型、registry、filter、cache 與分包 A/B 全部延後到 R5。

完整結果見
[`../DEVLOG-2026-08-01-wasm-sdk-r4.md`](../devlog/DEVLOG-2026-08-01-wasm-sdk-r4.md)、
[`../specs/SPEC-R4-000-overview.md`](../specs/SPEC-R4-000-overview.md)與
[`../findings/evidence/sdk-r4/summary.json`](../findings/evidence/sdk-r4/summary.json)。

R1 的完整 24 份文件結果仍保留於
[`../DEVLOG-2026-08-01-wasm-sdk-probe.md`](../devlog/DEVLOG-2026-08-01-wasm-sdk-probe.md)。

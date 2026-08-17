# 046 — 讀回什麼都沒有時，引擎回報的是「文件不是你要的狀態」

| | |
|---|---|
| **狀態** | **已確認（出貨 v2 實測 ＋ 原始碼對照）／未修**——**2026-08-15 更正：修法並沒有被寫進原始碼樹**，佇列項仍在 |
| **Bugzilla** | —（**不是上游缺陷**） |
| **發現日** | 2026-08-15（E2-C D2 第一次執行） |
| **嚴重度** | **嚴重**——觸發手勢是「在空白行上按項目符號」，而後果是 host 回滾、丟掉自 checkpoint 以來的編輯 |
| **可重現** | 100%（Chrome，出貨 profile `e2-editor-v2`） |
| **是否上游** | **否——我方 barrier 的分類** |

## 摘要

在**空段落**上派送 `set-list-unordered`，出貨 v2 回：

```json
{"code": "EDITOR_FORMAT_POSTCONDITION_FAILED",
 "failureShape": "postcondition-not-met",
 "dispatched": true, "preBlocks": 0, "postBlocks": 0}
```

**`postBlocks: 0` 的意思是「這次讀回沒有描述任何一個段落」**，
而不是「文件處在錯的狀態」。引擎把前者回報成了後者。

barrier 自己的註解就寫著這個區別（`probe_engine.cpp:3488`）：

> 「前兩個說的是**讀回沒有描述一個已知的段落，所以關於後置條件根本沒有任何判斷
> 可用**；只有兩個都成立之後，『它在不在目標狀態』才是個問題。」

**零個 block 的讀回正是那個情形，但它掉進了後置條件的判決。**

## 為什麼這件事會咬到人

`EDITOR_FORMAT_POSTCONDITION_FAILED` 帶 `dispatched: true`，於是
`formatFailureDisposition()` 回 `dispatched-rollback`，
而 `recoveryFor()` 把它變成 **rollback**——host 會**從 checkpoint 重開，
丟掉自那之後的所有編輯**。

**觸發它的手勢是「在空白行上按項目符號」。** 那不是邊角情形。

而且訊息本身是錯的：「the document does not show the state this action asked for」
——**沒有人看過文件**。

## 機制（原始碼層級）

| 位置 | 做什麼 |
|---|---|
| `probe_engine.cpp:3562` | `if (!formatBarrierReadbackSatisfied())` → `postcondition-not-met` ＋ `EDITOR_FORMAT_POSTCONDITION_FAILED` |
| `:3408-3430` | `formatBarrierReadbackSatisfied()`：`expectedListTag` 是 `"ul"`，讀回的 `listTag` 是空的 → 觀察值 `"none"` ≠ `"ul"` → 回 false |
| `:3416-3419` | 它確實會擋掉 `unknownTag`／`malformedNesting`／`footnoteApparatus`／型態守衛——**但沒有擋 `blockCount == 0`** |

**所以「什麼都沒讀到」與「讀到了、而且是錯的狀態」走同一個出口。**

## 與 SPEC E2-B 2.3 的表對不上

那張表把**空段落**列在「**派送前拒絕**（零 mutation）」那一類，
`EDITOR_FORMAT_*`、「**沒有發生**」。

**出貨的引擎沒有任何空段落的派送前檢查**——三個 `EDITOR_FORMAT_*` 碼分別是
`POSTCONDITION_FAILED`（派送後）、`GESTURE_UNSUPPORTED`、`SELECTION_NOT_READABLE`
（兩個派送前，都與空段落無關）。那一列**繼承自 E2-A 的 discovery 流程**
（當時還會讀前置狀態），路線 C 之後就不成立了，而沒有人回頭改。

**兩件事因此都要修**：引擎的分類，以及那張表。

## 修法（列入下一次 relink）

讀回**解析成功但一個 block 都沒有**時，回
`MUTATION_OUTCOME_UNKNOWN`＋自己的 shape（`empty-readback`），
而不是 `POSTCONDITION_FAILED`。理由是那正是 barrier 自己寫下的規矩：
**沒有描述到一個已知段落，就沒有關於後置條件的判斷可用。**

處置也跟著對：`MUTATION_OUTCOME_UNKNOWN` 仍然是 rollback（fail closed，
因為確實派送了），但**訊息不再宣稱看過文件**，而 host 也不再被告知
「文件是錯的狀態」這個沒有根據的說法。

> **這一項是「D2 要在 relink 之前寫」那個要求的直接產物。** 對抗性審查說
> D2 是最可能再長出引擎佇列項的地方；它第一次跑就長出了這一個。

## 2026-08-16 原生量測：**讀回描述的是上一段，而且動作其實成功了**

3b 的判準本來卡在「產品看不到 `itemCount`」。原生可以看，而且看到的東西比預期的
更根本。證據 `findings/evidence/046/native/`（三輪，預測先寫，分類由
`tools/test_format_readback_parser.py` **把引擎自己的 scanner 從 `probe_engine.cpp`
切出來編譯**後施加，不是第二份實作）。

**量到的：在空段落上，barrier 自己的選取對（`.uno:GoToStartOfPara` ＋
`.uno:EndOfParaSel`）會把游標往上帶一段，然後選中上一段。**

| 臂 | 游標 y | 選取型態 | 讀回 |
|---|---|---|---|
| `click-empty-bare` | **1807**（空段落上） | 0（無） | **空字串** |
| `click-empty-pair` | **1418** | 1 | **`E1-EMPTY-BEFORE`**（上一段） |
| `select-empty-pair` | **1418** | 1 | 同上——**兩個手勢在原生上完全相同** |
| `after-bullet-pair` | **1418** | 1 | 同上（動作之後也一樣） |
| `last-empty-pair` | 2585 → **2196** | 1 | `E1-EMPTY-AFTER`（上一段） |

**而動作是成功的**：存出來的文件裡那個空段落確實變成了
`<text:list><text:list-item><text:p/></text:list-item></text:list>`。
所以**不是「bullet 沒生效」，是「檢查看了別的地方」**。

**引擎自己的 parser 對幾種標記的分類**（量出來的，不是推的）：

| 標記 | parsed | blockCount | itemCount | multiBlock |
|---|---|---|---|---|
| 上面那些成對讀回 | 1 | **1** | 0 | 0 |
| 空字串／只有空白／`<html><body></body></html>` | **0** | 0 | 0 | 0 |
| `<ul><li></li></ul>` | 1 | **0** | 1 | 0 |
| `<ul><li></li><li></li></ul>` | 1 | **0** | 2 | **1** |

兩件因此定案：**空的讀回是 `parsed = false`**（不是「parsed 但零個 block」——
任何寫成後者的判準都會漏掉它）；而**「零個 block ＋ itemCount ≥ 1」在 parser 裡
是真的存在的**，兩個 item 就會變成「沒有任何 block 的 multiBlock」，正是本檔
推論過的那個矛盾組合。

**對 3b 的影響：不撤回，也還不能寫。** 卡住的問題換了一個，而且更尖銳了——
**core 對空段落的讀回是「上一段、一個 block」，而出貨的 build 對同一個手勢回報
「零個 block」。兩者不一致，在解釋清楚之前，`empty-readback` 這個名字會取在一個
機制未明的症狀上。**

**而且浮出一件比 046 的分類 bug 更大的事**：**barrier 驗的是動作沒有碰到的那一段。**
空段落上選取對往上走一段，於是後置條件比對的是錯的文字——與
[048](048-place-caret-confirms-before-the-click-takes-effect.md) 同一個家族
（產品確認了一次還沒落地的點擊）。**046 原本的修法（改個名字）碰不到這一件。**

## 2026-08-16 瀏覽器對照：**不一致消失了——瀏覽器那個數字從來不是讀回**

原生說「上一段、一個 block」，出貨 build 說「零個 block」。本檔把這兩個並排當成
矛盾，而 3b 就卡在這個矛盾上。**它們從來不可比。**

`preBlocks` 與 `postBlocks` 在這些格走的那條路徑上根本沒有被寫入：

- `preBlockCount` 全樹只有一處指派（`probe_engine.cpp:3329`），在「選取矩形不為空」
  的分支裡——也就是兩條 **range** 路徑。`collapsed` 上永遠不會被寫。
- `postBlockCount` 全樹只有一處指派（`:3368`），在 `checkFormatBarrierCrossParagraph()`
  裡——只有 **cross** 路徑。

而這場爭論的每一格，兩邊都是 `route: "collapsed"`。

不是靠讀原始碼定案的，是靠控制格：**一個成功的 barrier，打在有文字的段落上，
回報 `preBlocks: 0`**（`A3-text-click`，`verified-format-readback`）。零不可能是
「讀了而且什麼都沒有」，因為那個讀明明成功了。而 `A5-text-range` 在 range-single
上回 `preBlocks: 1`——欄位不是壞掉，是只在某些路徑上被寫。兩瀏覽器、兩輪，完全一樣。

證據：`findings/evidence/046/browser-vs-native/`（四輪，凍結的 e2-editor-v2，
一個檔案都沒改）。

**順帶量到兩件**：

- **兩個手勢現在一致了。** D2 記到「點擊 → `postcondition-not-met`、
  零寬 selectRange → `multi-block-readback`」；帶 048 修好之後的確認點擊，
  **兩者都是 `multi-block-readback`**。那個差別是「點擊還沒落地」的性質。
- **文件最後一段的空段落不一樣**：同一份文件同一個手勢，barrier 連讀回都沒走到
  （`stage-deadline:awaiting-selection`，兩瀏覽器一致）——與本檔「還缺什麼」
  第二項是同一條路徑。

## 2026-08-16 診斷輪：**在凍結的引擎上讀出 barrier 自己的紀錄**

外部裁決指出「這些問題需要 relink 才量得到」是錯的：診斷 profile 是一個
**Python 打包步驟**（`build_e2_discovery_profile.py` 是 `shutil.copy2(wasm)`，
`--wasm` 是輸入），引擎位元一個都不動。核對過：`probe.wasm` 與
`dist/profiles/e2-editor-v2/probe.wasm` **逐位元相同**。

方法的自我控制先成立（P-046D-5）：**同一頁、同一批 arm、兩個 profile 的結果完全
相同**——換掉投影改變的是看得到什麼，不是發生了什麼。

**讀出來的東西**（兩瀏覽器一致）：

| arm | parsed | blockCount | itemCount | containment | 結果 |
|---|---|---|---|---|---|
| 有文字的段落（控制） | true | **1** | 1 | checked, **held** | **成功** |
| 空段落（點擊／零寬 selectRange） | true | **2** | 1 | checked, **held** | `multi-block-readback` |
| 最後一個空段落 | **false** | 0 | 0 | 未檢查 | `stage-deadline` |

**原始 markup 就是答案**：

```html
空段落那一格：<ul><li><p></p></li></ul><p>E1-EMPTY-AFTER</p>
```

**項目符號套用了**——空段落確實變成帶空 `<p>` 的 list item——**而讀回把下面那一段
也吞進來了**。所以 barrier 看到兩個 block，然後拒絕了一個其實成功的變更。

### 兩個 blocker 都有答案了，而且都不是我預期的方向

- **3b 撤銷**：我登記的是「`parsed:true, blockCount:0, itemCount≥2`」，量到的是
  `blockCount:2`。**沒有任何一格產生「parsed 但零 block」的讀回。** 3b 要命名的
  那個案例在這份語料上不存在，而它賴以成立的「零個 block」是 `postBlocks: 0`
  ——那個在 collapsed 路徑上從來沒被寫入的欄位。`multiBlock` 不是誤報：
  讀回真的涵蓋了兩段。
- **containment 重排不進這次連結**：我登記的是 `checked:true, held:false`，
  量到的是 **`held: true`**（選取 1807–2471，restore centre 1945，在裡面）。
  重排**不會改變任何一格**。這個撤退條件是裁決在資料出現之前就指名的。

### 真正的缺陷，現在精確了

**空段落上 `.uno:SelectText` 會選過頭，把下一段也選進來。** 動作成功、驗證讀多了
一段、barrier 回報 `MUTATION_OUTCOME_UNKNOWN`。

而 containment **依構造抓不到它**：它問的是「選取有沒有涵蓋游標」，不是「有沒有
只涵蓋游標那一段」——**一個單向的檢查**，只抓得到選少了，抓不到選多了。
選多了是被 `multiBlock` 順便抓到的,這也解釋了為什麼 `multiBlock` 先判、
以及為什麼重排沒有用。

### 選過頭的範圍量過了：**只發生在空段落**（2026-08-16）

一個位置不是刻畫，所以八格 × 兩瀏覽器又量了一輪（凍結的引擎，
`findings/evidence/046/overshoot/`）。關鍵格是 **`text-end`**——finding 034 說舊的
選取對是因為**游標在段落邊界**才逃到鄰段的，而空段落正是兩個邊界同時成立。

| 格 | 游標 | blocks | 結果 |
|---|---|---|---|
| 有文字、中間（控制） | mid | 1 | 成功 |
| 有文字、最左 | start | 1 | 成功 |
| **有文字、最後一個字之後** | **past text** | **1** | **成功** |
| **空段落** | — | **2** | `multi-block-readback` |
| 非清單鄰居的段落（中間／末尾） | | 1 | 成功 |
| 兩個清單之間的段落 | | 1 | 成功 |
| 既有 list item 內 | | 1 | 成功 |

六條預測全部成立，**包含 P-OV-3 的前提**（那兩格的游標確實落在文字之後）。
所以「點在行尾按項目符號」這個日常手勢是好的——**只有空白行會中**。

因此這一項維持**不擋連結**。而 containment 在每一個選過頭的格上都是 `held: true`，
所以修法必須拿讀回去比**動作派送的那一段**，不是比游標。

### 原生那一輪的更正

`findings/evidence/046/native/README.md` 把 `.uno:GoToStartOfPara` ＋
`.uno:EndOfParaSel` 說成「barrier 自己的選取對」。**那不是引擎的手勢**：barrier
送的是單一 `.uno:SelectText`（`probe_engine.cpp:804`），而它上面的註解記著那個
「對」正是因為**游標在段落邊界時會逃到鄰段**（finding 034）才被取代的。
原生那一輪等於重量了一個已被取代的手勢——而且量到的正是取代它的那個缺陷。
已在該檔加註日期更正。

## 這對 3b 的意思

**卡住的東西沒了，但問題換了位置。** 沒有 native／WASM 矛盾要解釋。3b 真正還缺的是：
host 要怎麼分辨「什麼都沒讀到」與「只讀到清單項」。引擎自己的紀錄有這個資訊
（`readback.parsed`／`blockCount`／`itemCount`），而**產品投影前兩個都沒有**——
`itemCount` 進 v3，`parsed` 與 `blockCount` 沒有。這是一個投影決定，要進這次 relink。

**而且掉出一個與第 3 項同族的新佇列項**：第 3 項存在，是因為 barrier 會回報一條
它沒有分類過的 route——把預設值當觀測值。`preBlocks`／`postBlocks` 又做了兩次，
而這份證據已經被當成量測讀了兩輪。處方二選一：每條路徑都寫，或改名到不會被誤讀。

## 還缺什麼

- [ ] 修完之後在 v3 上重測，並補一格**空段落**進第二輪的矩陣。
- [ ] 空段落在**文件最後一段**的情形另有一條已知路徑
      （`.uno:SelectText` 不回選取回呼 → stage deadline，`:718-735`）——
      要確認修法之後那一格仍然落在 `stage-deadline:*` 而不是被新的 shape 蓋掉。
- [ ] 改 SPEC E2-B 2.3 的表（**既有草稿不回頭改**那條規矩管的是 Bugzilla 草稿，
      規格是活文件，就地修訂即可）。

## 2026-08-15 更正兩件（D3 那一輪查證時發現的）

**一、修法沒有被寫進去。** 本檔原本寫「修法已寫、待 relink」，而
`grep -rn "empty-readback" src/` 是零筆——`probe_engine.cpp` 裡沒有這個 shape，
`blockCount == 0` 也沒有任何分支。P1 佇列的第 3b 項**仍然待做**，
`handoff/PLAN-E2-C-relink-v3.md` 已同步更正。P1 的其他四項（inline 參數、
gesture mask、route 不謊報、ABI → 3）確實在樹裡。

**二、同一個空段落有兩個出口，取決於游標是怎麼形成的。**

| 游標形成方式 | 回報 | session 狀態 |
|---|---|---|
| 產品的點擊（`placeCaret`，中間有一次存檔讓它落地） | `EDITOR_FORMAT_POSTCONDITION_FAILED`／`postcondition-not-met` | `ready` |
| 零寬 `selectRange` | `MUTATION_OUTCOME_UNKNOWN`／`multi-block-readback` | `recoverable-error` |

兩者的 `preBlocks`／`postBlocks` 都是 **0**。而 `multiBlock` 的定義是
`blockCount > 1 || itemCount > 1`（`probe_engine.cpp:605`），所以第二列必然是
**itemCount ≥ 2 而 blockCount == 0**——訊息卻寫「涵蓋了超過一個段落」，
而證據裡的段落數是 0。**操作者看到的紀錄自相矛盾。**

這正是 SPEC E2-C 9.5.6 那條「手勢會改變答案」的另一個實例，
也連到 [048](048-place-caret-confirms-before-the-click-takes-effect.md)。

**因此修法的判準還不能定案。** 引擎其實有 `itemCount`／`listTag`／`blockTag`／
`expectedListTag`，但那是**診斷** payload；產品 profile 的 `formatBarrier` 只投影
`failureShape`／`dispatched`／`route`／`preBlocks`／`postBlocks`／兩個 held 旗標，
**看不到 itemCount**。所以「零個 block」到底是「什麼都沒讀到」還是「只讀到清單項
而沒讀到 block」，在出貨 profile 上**分不出來**。

修法要嘛：

1. 先把 `itemCount` 補進產品投影（**它是判斷有沒有讀到東西的必要欄位**，
   而不是診斷用的額外資訊），再依量到的值決定 `empty-readback` 的判準；或
2. 直接把判準定成 `parsed && blockCount == 0 && itemCount == 0`——
   保守、只處理本 finding 原本記錄的那個情形，不對「只有清單項」那一類發明語意。

**兩條都要進同一次 relink**，而 (1) 多一個欄位、少一次猜。

順帶一個原始碼層級的觀察（**未驗證，當假說看**）：`listTag` 只在**第一個**結構
標籤是 `ul`／`ol` 時才會設。若讀回是從 `<li>` 開始的，`listTag` 會是空的，
於是 `formatBarrierReadbackSatisfied()` 拿 `"none"` 去比 `"ul"` 而回 false
——**明明讀到的就是一個清單項，卻被判成「文件不是你要的狀態」**。
這個假說能不能成立，同樣要等 `itemCount` 進投影才量得到。

## 證據

`findings/evidence/sdk-e2/e2-c-validation/d2-presweep/`（D2 的掃描輪），
`d2-refused-no-mutation-engine` 那一格。更正用的兩個出口在
`d2-narrow/run-2/`（零寬 selectRange）與 `d2-narrow/caret-click-arm/`（產品點擊）。

---

## 2026-08-17 —— 殘留的**處置**已修（殼層 v14),驗證仍然沒有恢復

**分清楚兩件事**:

| | 狀態 |
|---|---|
| barrier **拒絕給結論** | **沒有改,而且是對的**——讀回涵蓋兩段,它確實不知道描述的是哪一段 |
| 那個拒絕**被翻譯成「回檢查點」** | **已修** |

也就是說:修的是**處置**,不是判決。在空白行上按項目符號,現在 session 留在
`ready`、佇列不擋、復原可用,訊息說「已送出、無法單獨核對、請自行確認」。

### 為什麼 a11y 那條路死了也沒關係

原本的處方是用 accessibility 的段落指紋去比對「派送的那一段」與「讀回的那一段」。
[[056]]／[[057]] 之後那條路在這個平台上沒有輸入。**但那條路本來就修不好這一格**:
`multiBlock` 的檢查在**識別檢查之前**就 return 了(`probe_engine.cpp:3806` 對
`:3852`),所以這一格從來走不到識別比對。失去 a11y 對這個缺陷的代價,比看起來小。

### 判準之外的三件事,都記下來

1. **B 案（驗 block[0])被否決,不是延後。** 既有證據顯示目標在 block[0] 且已帶目標
   狀態,但那是**同一顆引擎跑兩次**——兩個瀏覽器不是這個宣稱的兩次獨立量測——而且
   只涵蓋 `empty-mid` 一種形狀。反例:向**上**溢出、而上面那段本來就已經是項目符號、
   動作其實失敗——「恰好一塊帶目標狀態」的護欄照樣放行,而且放行的正是它要擋的那格。
2. **文件最後一行的空段落不在涵蓋範圍。** 實測它**到不了 readback**
   （`stage-deadline:awaiting-selection`,另一條路)。**不要說「空白行按項目符號不會
   再叫你回檔」——對最常見的那種空白行,那句是假的。**
3. **代價已量到:回歸網失去了唯一進得了 `recoverable-error` 的路。**
   `notice-action-recovers-the-session` 現在報 `NOT_ESTABLISHED`;
   `review-disposition` 突變讓這一對同時反向移動。recovery 路徑**不是壞了,是沒被涵蓋**,
   欠一個新的誘發手段。

### 實作為什麼長這樣

「不要擋佇列」比想像難:基底類別是看**錯誤碼**擋的
（`editor-shell/editor-session.js:20` 的 `RECOVERY_ERRORS` 含
`MUTATION_OUTCOME_UNKNOWN`,在 `:325` 生效),而那個檔案**綁在 E1-C 的雜湊上,不能動**。
第一版只改了 `_blockQueueIfDispatched`,**訊息換了、session 照樣被擋**——量出來的。

做法是:讓那個操作以 sentinel **resolve**(基底的 catch 只在 reject 時才跑),
在 drain 外面再把原始錯誤丟出來。原始錯誤碼原封不動。

**而且它會自我撤銷**:sentinel 沒有帶 `state`,所以 drain 走成功路徑時會向引擎
要一次 `getState`。引擎若卡住,那一次會 TIMEOUT,而 TIMEOUT **在** `RECOVERY_ERRORS`
裡——佇列照樣會被擋。放寬只在引擎能證明自己活著的時候成立。

外部裁決:fable(2026-08-17)。**我原本的兩個候選都被否決**:直接 `_invalidateDrain()`
會讓 session 卡在 `busy`（drain 的 `finally` 只在 token 相符時才轉回 `ready`),
而換錯誤碼會讓 host 看到的碼和引擎送出的碼分岔。第三條路是 fable 提的。

契約變更寫在 SPEC E2-C **2.6b**,與殼層世代**同一次**出貨。

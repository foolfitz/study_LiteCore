# 038 的堆疊取到了——**它是 040 的第三個入口，預測結局 A**

**日期**：2026-08-14 23:59 ～ 2026-08-15 00:06（三次獨立執行）
**artifact**：`e2-preguard-profiling` ＝ `e05fd156…`（**本輪沒有任何連結動作**，
profile 是任務 #42 建好的。三個凍結 artifact 未變的核對**不在這三份 JSON 裡**
——JSON 只記診斷 wasm 自己的 SHA——讀數寫在 [`../ARTIFACT.sha256`](../ARTIFACT.sha256)）
**fixture**：`frame-contexts.odt`　**模式**：`wedge-split`　**選取法**：`mouse-drag`（預設）
**預測**：[../PREDICTION.md](../PREDICTION.md)，commit `90cc23d`，**寫在第一次執行之前**

## 結果：預測表的結局 A

```
 0 emscripten_futex_wait                      ← 停在這裡
 1 __timedwait_cp
 2 __pthread_cond_timedwait
 3 pthread_cond_wait
 4 std::__2::__libcpp_condvar_wait
 5 std::__2::condition_variable::wait
 6 osl_waitCondition
 7 Scheduler::IdlesLockGuard::IdlesLockGuard()          ← 040 的那一格
 8 sw::DocumentLayoutManager::DelLayoutFormat(SwFrameFormat*)
 9 SwTextNode::DestroyAttr
10 SwTextNode::EraseText
11 SwTextNode::DeleteAttribute
12 SwNodes::RemoveNode
13 SwNodes::DelNodes
14 SwDoc::~SwDoc
15 SwDoc::release
16 rtl::Reference<SwDoc>::~Reference                    ← 剪貼簿 SwDoc 的最後一個持有者
17 SwTransferable::~SwTransferable                      ← 解構子對（D1／D0）
18 SwTransferable::~SwTransferable_151845
19 cppu::OWeakObject::release
20 non-virtual thunk to cppu::WeakImplHelper<…>::release()_1486   ← 名字不可信，見下
21 doc_getSelectionTypeAndText                          ← 038 的入口
22 probe::(anonymous namespace)::readSelection()
23 probe::(anonymous namespace)::dispatch
24 probe::(anonymous namespace)::engineLoop
25 __thread_proxy
26 invokeEntryPoint
27 handleMessage
```

第 16～21 格就是整件事：`doc_getSelectionTypeAndText` 從 `pDoc->getSelection()`
拿到區域 UNO reference，函式返回時釋放，`SwTransferable` 解構
（`swdtflvr.cxx:295` 的 `m_pClpDocFac.reset()`），連同它自己那份剪貼簿 `SwDoc` 一起銷毀
——**同一條 `DelLayoutFormat` → `IdlesLockGuard`**。

## 與 037 的逐格比對（**本輪實測，不是引用 040 的敘述**）

拿 [`../../wait-primitive-names/chrome/f037-preguard-named.json`](../../wait-primitive-names/chrome/f037-preguard-named.json)
（同一顆 artifact 上取得的 037 堆疊，深度 27）對本輪的 28 格逐格比：

| 範圍 | 結果 |
|---|---|
| 第 0～**20** 格 | **逐格完全相同**（含第 20 格那個折疊後的 thunk 名） |
| 第 21 格 | 037 ＝ `doc_getTextSelection`／038 ＝ `doc_getSelectionTypeAndText` |
| 之後 | 038 多一格 `probe::readSelection()`，這就是深度 27 對 28 的全部差別 |

精確的說法是：**第 0～20 格相同；第 21 格是不同的 LOK API；038 另外多一格
`readSelection()`。** 不要說成「只差一個函式名」——那會漏掉多出來的那一格。
（初稿寫「第 7～19 格相同」，把範圍講小了；改寫後又寫成「只差一個函式名」，
把差異講小了。兩次都由外部覆核指出。）

> **精確一點：那個函式持有的是兩個區域 reference，不是一個。**
> `doc_getSelectionTypeAndText` 先取 `XTransferable`（`init.cxx:6004`），
> 再 query 出 `XTransferable2`（`init.cxx:6011`）。解構發生在兩個逆序釋放之後。
> `doc_getSelectionType` 是同樣的兩個（`init.cxx:5966`／`5973`）。
> （外部對抗性覆核指出，初稿寫成「一個區域 reference」。）

## 卡的是哪一步：同一份檔案自己說得出來

**這是本輪唯一一項需要另外做工的證據，而且第一版做錯了。**
`result.json`（run 1）**沒有**把堆疊綁到任何 anchor——它只有 callback 靜默與
`phase: "wedge-split"`，而 `wedge-split` 對 `frame-contexts` 會依序跑四個 anchor。
外部對抗性覆核就是以此把主張判為未成立，**判得對**。

`result-run3-with-step-log.json` 的 `pageSteps.stepLog` 是從頁面 `#log` 節點讀出來的，
逐步 append、不是事後補的。**時點要講清楚：它讀在偵測到 callback 靜默之後、
三輪 `Debugger.pause` 之前**，不是「暫停當下」（初稿這樣寫，錯了）：

| anchor | 步驟 | 結果 |
|---|---|---|
| FX-PLAIN | locate → select:mouse-drag → selection-rectangles → get-selection-text → selection-reset | **五步全過**，`selectionType: "text"`、2 ms |
| FX-CELL | 同上五步 | **五步全過**，`selectionType: "complex"`、0 ms |
| FX-NOTE | locate（18 ms）→ select:mouse-drag（完成，3864 ms） | **然後就沒有了**——下一步 `selection-rectangles` 送出去再也沒有回來 |

所以「引擎在 FX-NOTE 之前是活的」由**同一次執行**證明：前兩個 anchor 剛剛才各做了一次
同樣的讀選取。這不是拿別的 profile、別的 run 的數字來對。

**但最後一行本身不足以推到「下一步已經送出去了」，補上的是控制流：**
`step()` 只在 `await fn()` 成功或丟錯之後才 append，**沒有 started 紀錄**。
接得起來的是三件事：預設 `idleAfterSelect=0`，所以 select 之後緊接著就是
`selection-rectangles` 的 `client.getState()`；引擎那一側 get-state 的 handler
第一件事就是 `readSelection()`（`probe_engine.cpp:3787`）；而堆疊尾端正是
`dispatch → readSelection → doc_getSelectionTypeAndText`。
頁面的 event handler 只記錄事件、不另外送 request，所以沒有第二個候選來源。

> **第一次改版也是錯的，一併記著。** 我原本讀 `metrics.wedgeSplit`——
> 那個陣列頁面**要等整個相位返回才指派**，而整件事的前提就是它永遠不返回，
> 於是跑回來是一個空陣列，配上一個明明已經卡死的 run。
> 改讀 `#log` 節點才對：它是逐步 append 的，是**卡死期間唯一存在的逐步帳**
> （不是「唯一存在的帳」——`metrics.engineTrace` 一樣在，偵測靜默用的就是它；
> 但那是 callback 流水帳，不說步驟）。
> （`result-run2-with-page-steps.json` 保留了那個空陣列的版本，沒有刪。）

## 穩定度：三次執行 × 每次三輪 ＝ 九次逐格相同

| 檔案 | 時間 | 深度 | 與 run1 逐格相同 | 該次三輪彼此相同 |
|---|---|---|---|---|
| `result.json` | 08-14 23:59 | 28 | —（基準） | ✅ |
| `result-run2-with-page-steps.json` | 08-15 00:02 | 28 | ✅ | ✅ |
| `result-run3-with-step-log.json` | 08-15 00:06 | 28 | ✅ | ✅ |

輪與輪間隔 8 秒，所以每一次執行都橫跨 16 秒以上。

**但「橫跨 16 秒」不等於「永遠」，這裡要講清楚是誰在證明什麼：**

- **取樣證明的是**：至少 16 秒沒有可見進展，而且三次執行都一樣。
- **永久性由原始碼證明**，不是由取樣證明：`IdlesLockGuard` 呼叫無參數的
  `Condition::wait()`（`scheduler.cxx:297`），預設 timeout 為 null
  （`include/osl/conditn.hxx:121`），null 分支走的是無期限的 predicate wait
  （`sal/osl/unx/conditn.cxx:123`）；而全樹唯一設定該條件的地方在
  `Application::Execute()` 的 fallback loop 裡（`svapp.cxx:366`），
  Emscripten 的 `DoExecute()` 設好 main loop 之後不可返回（`svpinst.cxx:308`）。
- **第 1～2 格的 `__timedwait_cp`／`__pthread_cond_timedwait` 不表示這是有期限的等待**——
  那是 musl 的內部實作。上層是無參數 `wait()`。

## 第 20 格的名字不可信，物件的身分由第 17～18 格決定

外部覆核指出第 20 格的 `WeakImplHelper<XServiceInfo, XTerminateListener>`
**對不上 `SwTransferable` 的介面**——`SwTransferable` 繼承 `TransferableHelper`，
其 UNO base 是 `XTransferable2`／`XClipboardOwner`／`XDragSourceListener`
（`include/vcl/transfer.hxx:129`）。**這是對的，而且不能含糊帶過。**

順著查下去，那個符號指向的是一個**與這條路毫無關係的類別**：

- 覆核猜的是 `TransferableHelper` 裡巢狀的 `TerminateListener`。**不是它**——
  那個是 `WeakImplHelper<XTerminateListener, XServiceInfo>`（`transfer.hxx:136`），
  **模板參數順序相反**，是另一個實例化。
- 順序完全相符的只有一個：`RequestHandlerController`
  （`desktop/source/app/officeipcthread.hxx:137`），soffice 的 IPC 請求處理器，
  **跟剪貼簿、跟 Writer 都沒有任何關係**。

而 name section 裡整顆 artifact 只有四個
`non-virtual thunk to cppu::WeakImplHelper<…>::release()` 符號，其中三個是**同一個名字**
加上 `_1486`／`_1489` 後綴，**且 `WeakImplHelper<XTransferable2, …>::release()`
的 thunk 符號根本不存在**。

> **初稿在這裡下了一個錯的結論，而且是被反組譯直接推翻的。** 我原本寫
> ~~「同名加數字後綴是連結器把內容相同的函式折成一份的指紋」~~。
> 對這顆 artifact 跑 `wasm-dis` 之後，那三個同名 thunk 的函式體是：
>
> | 符號 | body |
> |---|---|
> | 無後綴 | `OWeakObject::release(this - 16)` |
> | `_1486` | `OWeakObject::release(this - 20)` |
> | `_1489` | `OWeakObject::release(this - 24)` |
>
> **偏移量不同，所以它們是三個不同的函式，不是一份折疊的副本。**
> `_NNNN` 是**名稱去重編號**：不同 secondary-base 偏移的 thunk 會 demangle 成
> 同一段可讀名稱，工具必須為撞名加唯一化 ID。（外部對抗性覆核先指出，我自己重跑
> `wasm-dis` 確認過才寫在這裡。）

**留下來的結論只有一句，但它就夠了：第 20 格的名字不能拿來認型別**
——已經證明這個名字本身就會撞，而且該出現的那個名字不在模組裡。
物件的身分由第 17～18 格認：`SwTransferable::~SwTransferable` 與
`SwTransferable::~SwTransferable_151845` 是同一個解構子的 D1／D0 對，**那是正面指認**。

**仍未解決**：`SwTransferable` 自己那個 release thunk 是被 ICF 併進了偏移 20 那一個、
還是以別的方式失去名字。這不影響任何結論，但也不要說成已經知道。

## 040 有一句要更正，不是補充

040 第六之二節寫：`doc_getSelectionType`（`init.cxx:5966`）「**很可能**是 038 的入口
——未取得堆疊，這是推論」。

**量到的是它的鄰居 `doc_getSelectionTypeAndText`。** 類別層級的推論成立
（一個從 `getSelection()` 取區域 reference 的讀取函式），**點名的那個函式錯了**。

> 初稿在這裡多寫了一句「我方引擎根本不呼叫 `doc_getSelectionType`」，**那也是錯的**：
> `readSelection()`（`probe_engine.cpp:2371`）優先用 combined API，
> **ABI 缺該欄位時會 fallback 到 `getSelectionType` ＋ `getTextSelection`**。
> 正確的說法是：**這顆 artifact 上實測走的是 combined API**。

## 037 的擋法在這個構造上是**觸發器**，不是防線——**但這是推論，不是本輪量到的**

`formatBarrierSelectionIsReadable()`（`probe_engine.cpp:3163`）第一件事就是
`readSelection()`——也就是第 22 格。**擋法要問的那個問題，走的就是被量到會卡死的那個呼叫。**

以前 038 檔案裡寫的是「037 的擋法涵蓋不到這條路」。涵蓋不到是輕的說法：
在這個構造上，擋法自己會踩下去。

> **這一格的證據強度要標清楚（外部覆核指出，初稿寫成「量到的」）。**
> 本輪三次執行跑的是 `selection-rectangles → getState`，
> **`formatBarrierSelectionIsReadable()` 一次都沒有被呼叫**。
> 量到的是 `readSelection()` 在這個構造上不返回；「所以呼叫 `readSelection()` 的擋法
> 也會不返回」是一步**原始碼層級的推論**。要把它變成量測，得在這顆 artifact 上
> 對 FX-NOTE 派送一次格式動作，讓 barrier 自己走過去。**沒有做。**

## 「文字已經取出來了」——這句話本輪**證不出來**

`doc_getSelectionTypeAndText` 確實在返回前才寫 out-parameter
（`init.cxx:6028` 的 `*pText = convertOString(aRet)`）。但**堆疊不告訴我們它走到哪裡**：
同一個函式在 `isComplex()`（`init.cxx:6011`）、傳輸失敗、長度超過 10000、
以及空字串這四個分支都會**提前 return**，而那些路徑一樣會釋放區域 reference、
一樣走到解構——**全部都在 `*pText` 之前**。

同一次執行裡 FX-CELL 的選取型態就是 `complex`，所以「FX-NOTE 走到了寫 out-param 那一行」
不是可以順帶假設的事。

**所以能說的只有：卡的是函式返回前釋放區域 reference 的那段清理。**
不能說文字已經取完，也不能說已經寫進呼叫端。（037 那一篇與 040 §六之二
也有同樣措辭，一併改了。）

## 這一輪不宣稱

- **不宣稱 `doc_getSelectionType` 也會卡。** 它與量到的那個結構相同
  （同樣兩個區域 reference、同樣在返回時釋放），但**沒有量過**。
- **不宣稱 `doc_getClipboard` 屬於這一族。** 它也持區域 `XTransferable`
  （`init.cxx:6074`），但**來源不同**（剪貼簿，不是 `pDoc->getSelection()`）。
- **不宣稱產品界定有變。** SPEC-E1-C §9.1 對 038 的具名收窄照舊。
- **不宣稱擋法要怎麼改。** 入口相同不等於防法相同。
- **不宣稱「註腳裡的 frame 是必要條件」。** 本輪證明的是那個停等堆疊屬於 FX-NOTE 這一格；
  必要性來自 038 早先的 2×2 矩陣（無 frame 的註腳、不涵蓋引用記號的選取），不是這三次執行。
- **這顆 artifact 不支持任何產品／出貨判定**（它自己就是診斷結論的載體，
  所以不能寫成「不支持任何判定」——初稿那樣寫是自相矛盾的）。

## 引用這三份檔案時，以下每一句都不成立

1. 「result.json 記錄了 FX-NOTE」——run 1 沒有，歸因在 run 3。
2. 「暫停與步驟帳是同一瞬間」——步驟帳讀在暫停之前。
3. 「`selection-rectangles` 在 DOM 留下了 started 紀錄」——`step()` 沒有 started。
4. 「擋法在這一輪被呼叫過」——沒有，那是推論。
5. 「out-parameter 已寫入／文字已取完」——四個提前 return 分支都沒被排除。
6. 「`_1486`／`_1489` 證明了 ICF」——反組譯顯示是三個不同偏移的函式。
7. 「十六秒取樣證明了永遠」——永久性來自條件設定路徑的原始碼分析。
8. 「診斷 artifact 的行為就是出貨 artifact 的行為」——不同的 build。

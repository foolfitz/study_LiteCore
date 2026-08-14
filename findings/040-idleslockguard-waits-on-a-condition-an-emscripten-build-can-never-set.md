# 040 — 非主執行緒建構的 `Scheduler::IdlesLockGuard` 在 Emscripten build 上永遠不返回

| | |
|---|---|
| **狀態** | **已確認並歸因到 core**；停等位置、等待對象與「為什麼永遠等不到」三者都有依據 |
| **Bugzilla** | —（尚未送出；本篇第 7 節就是報告草稿） |
| **發現日** | 2026-08-14 |
| **嚴重度** | **嚴重**——不是拒絕而是**永久停等**，只有殺掉 worker 重開能救 |
| **可重現** | [012](012-r6-styled-document-close-timeout.md) 100%；具名堆疊兩個入口各 1/1（`doc_destroy` 與 `doc_getTextSelection`） |
| **是否上游** | **是。** 死結完全在 core 裡，我方沒有任何一行參與 |

## 摘要

`Scheduler::IdlesLockGuard` 的建構子，在**非主執行緒**被建構時，會等一個
**只有 `Application::Execute()` 的 fallback 迴圈才會設定**的條件；而 Emscripten build 的
`SvpSalInstance::DoExecute()` 呼叫 `emscripten_set_main_loop_arg()` 之後標
`O3TL_UNREACHABLE`——**它永遠不返回**，那個迴圈因此結構上進不去。

**條件永遠不會被設定。** 於是任何在非主執行緒上走到
`DocumentLayoutManager::DelLayoutFormat()` 的程式碼就停在那裡不動了——而走到那裡的方式
不只一種，**已量到兩個入口，都是「銷毀一份含 frame 的 `SwDoc`」**：

- **`doc_destroy`**：關閉使用者的文件（[finding 012](012-r6-styled-document-close-timeout.md)，
  `close()` 180 秒不回應）。
- **`doc_getTextSelection`**：它內部造一份 `SwTransferable`（帶自己的 `SwDoc` 副本），
  函式返回時解構——**看起來是唯讀 API，卡的是返回前的清理**
  （[finding 037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)）。

## 一、停等的位置（量測，引擎 `ee185b3d…`）

`Debugger.pause` 對卡死當下的 worker **有效**——這是上一輪判定做不到的事，所以先記下來：
[wedge-thread-state](evidence/sdk-e2/discovery/wedge-thread-state/chrome/README.md) 用 CPU
profiler 判出「停等不是空轉」之後，下一步一直缺一個能對停等執行緒取得堆疊的工具。V8 的
inspector 可以中斷 `memory.atomic.wait32`，所以那個工具其實一直都在。

引擎執行緒最內側 frame 的模組位移是 7064008，該處的位元組是：

```
44 00 00 00 00 00 00 f0 7f   f64.const +inf      ← 無限逾時
61                           f64.eq
1b                           select
fe 01 02 00                  memory.atomic.wait32   ← 停在這裡
```

**同一輪自帶控制組**：同一個 worker 在卡死前是 10 格堆疊、卡死當下是 27 格，而**最內側六格
的位移逐 byte 相同**；其餘 pthread 兩欄完全一致（thread pool 在等工作），wasm 主 runtime
執行緒在卡死當下只剩 `MainLoop_runner` 一格＝閒置。

**代理呼叫這條路被關掉了**：卡死當下 `unmatchedProxyIssuesAtCapture` 與
`unmatchedReceivesAtCapture` **都是空的**——沒有任何一個未完成的 main-thread proxied call。
所以「停等是因為某個代理到主執行緒的呼叫沒人服務」不成立。
證據：[proxy-trace](evidence/sdk-e2/discovery/proxy-trace/chrome/README.md)。

## 二、那六格叫什麼名字（跨 build 對應，兩個獨立方法吻合）

`ee185b3d…` 沒有 name section。`e2-wait-diagnostic`（`150de122…`）有，但它帶著 037 的擋法，
037 的讀取卡死在它上面打不到——**兩份堆疊不可能出自同一輪**。

可以比的是**呼叫圖的形狀**。兩邊都抓到多條停在同一套 condvar 機制裡的執行緒，而它們在
**不同深度**離開共用前綴（做 timed wait 的 pool 執行緒在第 3 格分出去、做無限等的在第 4 格）。
每一個分岔點都是一條獨立約束。`tools/map_wait_frames_across_builds.py` 只配對**同角色**的
堆疊（長度相同且 JS 尾端相同），跨 build 解出 **12 個索引、零歧義**：

| `ee185b3d…` | 名字 |
|---|---|
| `$func15470` | `emscripten_futex_wait` |
| `$func27191` | `__timedwait_cp` |
| `$func36295` | `__pthread_cond_timedwait` |
| `$func7324` | `pthread_cond_wait` |
| `$func36249` | `std::__2::__libcpp_condvar_wait` |
| `$func5549` | `std::__2::condition_variable::wait` |

**這六格正好就是 037 停等堆疊的前綴。** 而 `$func15470 = emscripten_futex_wait`
與第一節那個位元組層的 `memory.atomic.wait32` **是兩個互相獨立的方法得到同一個結論**。

> **這個對應是推論，不是量測**，工具自己也這樣印。取代它的量測是把 pre-guard 那份原始碼
> 帶 `--profiling-funcs` 重連結一次。**上一輪為了一個旗標付了一個 build，而那個旗標
> 印的東西根本不是我以為的**（[pthread-trace](evidence/sdk-e2/discovery/pthread-trace/chrome/README.md)）；
> 這次先把不必重編就能拿到的拿完，重編要什麼也講清楚了。

## 三、它在等什麼（具名堆疊，引擎 `150de122…`）

有名字的那份 build 上，引擎執行緒的完整堆疊（35 格）：

```
emscripten_futex_wait
__timedwait_cp
__pthread_cond_timedwait
pthread_cond_wait
std::__2::__libcpp_condvar_wait
std::__2::condition_variable::wait
osl_waitCondition
Scheduler::IdlesLockGuard::IdlesLockGuard()          ← 等待點
sw::DocumentLayoutManager::DelLayoutFormat(SwFrameFormat*)
SwTextNode::DestroyAttr(SwTextAttr*)
SwTextNode::EraseText / DeleteAttribute
SwNodes::RemoveNode / DelNodes
SwDoc::~SwDoc / SwDoc::release
SwDocShell::~SwDocShell
SfxBaseModel::dispose / SwXTextDocument::close
doc_destroy(LibreOfficeKitDocumentStruct*)
probe::closeDocument → dispatch → engineLoop
```

**這就是 finding 012。** 012 當時只到「WASM 停在 document destroy」，現在停在 destroy 的
**哪一行、等的是哪一個條件**都在上面。

同一輪的主 runtime 執行緒堆疊是
`SvpSalInstance::ImplYield ← loop(void*) ← iterFunc ← callUserCallback ← runIter ← MainLoop_runner`
——**它在 emscripten 的主迴圈裡，不在 `Application::Execute()` 的迴圈裡**。這一格是下一節
那條原始碼推理的實測支點，不是假設。

## 四、為什麼那個條件永遠不會被設定（原始碼，基線樹 `671c848b…`）

**引用的是 build 用的那棵樹**：`study_LiteCore/libreoffice-26-8`，HEAD ＝
`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`（＝`validate_e1_c.py` 的 `CORE_BASELINE_HEAD`），
版本 26.8.0.1.0+。該樹有五個既存本地修改，**下列六個檔一個都不在其中**，
所以這幾段原始碼就是 wasm build 用的原始碼。

```cpp
// vcl/source/app/scheduler.cxx:280
Scheduler::IdlesLockGuard::IdlesLockGuard()
{
    …
    if (!Application::IsMainThread())
    {
        pSVData->m_inExecuteCondtion.reset();
        Application::PostUserEvent({});
        SolarMutexReleaser releaser;
        pSVData->m_inExecuteCondtion.wait();      // ← 停在這裡
    }
}
```

```cpp
// vcl/source/app/svapp.cxx:355
if (!pSVData->mpDefInst->DoExecute(nExitCode))    // ← Emscripten 上進不去
{
    if (Application::IsUseSystemEventLoop()) { …std::abort(); }
    while (!pSVData->maAppData.mbAppQuit)
    {
        Application::Yield();
        SolarMutexReleaser releaser;
        pSVData->m_inExecuteCondtion.set();        // ← 全樹唯一的 set()
    }
}
```

```cpp
// vcl/headless/svpinst.cxx:308（#if defined __EMSCRIPTEN__）
bool SvpSalInstance::DoExecute(int &) {
    assert(Application::IsUseSystemEventLoop());
    ReleaseYieldMutex(false);
    emscripten_set_main_loop_arg(loop, this, 100, 1);
    O3TL_UNREACHABLE;                              // ← 永不返回
}
```

`grep -rn m_inExecuteCondtion` 全樹只有四個位置：宣告（`vcl/inc/svdata.hxx:414`）、
**唯一的 `set()`**（`svapp.cxx:366`）、以及 guard 裡的 `reset()` 與 `wait()`
（`scheduler.cxx:292`、`:297`）。**設定它的那一行在 Emscripten build 上不可達。**

`m_bUseSystemLoop` 由 `vcl/headless/svpinst.cxx:103` 在 `#if defined __EMSCRIPTEN__`
之下設為 true，所以這條路徑不是組態選項，是這個平台的唯一路徑。

註解本身就寫明了它預期的是什麼：「Only main thread returning to `Application::Execute`
guarantees that the flag really took effect.」——**在 Emscripten 上主執行緒永遠不會
returning to `Application::Execute`**，因為它根本沒從 `DoExecute` 回來過。
`Application::PostUserEvent({})` 那一手也救不了：它讓主迴圈跑一圈，但設定條件的程式碼
不在主迴圈裡，在那個進不去的 `while` 裡。

## 五、它解釋了哪些既有 finding，哪些還沒

| finding | 現況 |
|---|---|
| [012](012-r6-styled-document-close-timeout.md) `close()` 不回應 | **已解釋，量到的**——`doc_destroy` 這條路 |
| [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md) as-char frame 段落格式動作卡死 | **已解釋，量到的**（2026-08-14）——見下 |
| [038](038-a-frame-inside-a-footnote-wedges-the-engine-on-selection.md) 註腳內 frame 選取卡死 | **已解釋，量到的**（2026-08-15）——`doc_getSelectionTypeAndText` 這條路，見第六之三節 |

### 預測命中，而且答案比預測本身重要（2026-08-14）

原本寫的可否證預測是：把 pre-guard 原始碼帶 `--profiling-funcs` 重連結，
**037 停等堆疊的第 7 格會是 `Scheduler::IdlesLockGuard::IdlesLockGuard()`**。

**建了（`e2-preguard-profiling`，wasm `e05fd156…`，`OXSDK_037_GUARD_OFF` ＋
`--profiling-funcs`），跑了，第 7 格就是它。** 深度也對得上：27 格，與當初那條沒有名字的
堆疊逐格對齊。先前靠消去法推出的 `$func2290 = osl_waitCondition` 也一併證實。

**但第 21 格才是這一輪真正的收穫**：

```
 0 emscripten_futex_wait          ← 停在這裡
 1 __timedwait_cp
 2 __pthread_cond_timedwait
 3 pthread_cond_wait
 4 std::__2::__libcpp_condvar_wait
 5 std::__2::condition_variable::wait
 6 osl_waitCondition
 7 Scheduler::IdlesLockGuard::IdlesLockGuard()      ← 預測的那一格
 8 sw::DocumentLayoutManager::DelLayoutFormat(SwFrameFormat*)
 9 SwTextNode::DestroyAttr → EraseText → DeleteAttribute
12 SwNodes::RemoveNode → DelNodes
14 SwDoc::~SwDoc → SwDoc::release
16 rtl::Reference<SwDoc>::~Reference
17 SwTransferable::~SwTransferable                  ← 沒有預料到
20 cppu::OWeakObject::release
21 doc_getTextSelection(...)                        ← 這確實是 037，不是關檔
22 probe::dispatch → engineLoop
```

**037 和 012 不是「共用同一個等待原語」，是同一個缺陷。** 兩者都是
**在非主執行緒上銷毀一份含 frame 的 `SwDoc`**；差別只在那份 SwDoc 是誰的：

- **012**：使用者的文件，經 `doc_destroy`。
- **037**：`getTextSelection` **自己造的暫時副本**。

核心那一段可以逐行對上（基線樹 `671c848b`）：`doc_getTextSelection`
（`desktop/source/lib/init.cxx:5926`）把 `pDoc->getSelection()` 取到一個**區域**
`css::uno::Reference`，函式返回時它出範圍 → `~SwTransferable`
（`sw/source/uibase/dochdl/swdtflvr.cxx:283`）→ `m_pClpDocFac.reset()`（`:295`）
→ 銷毀剪貼簿 `SwDoc`。

**所以卡死發生在資料已經取出之後的清理路上。** 這對客戶端的意義比「某個讀取會卡」大得多：
任何會複製一段含 frame 選取的路徑，都會在收尾時卡死，而那一段看起來是唯讀 API。

> **這個 build 與 `ee185b3d` 不是同一份原始碼**——它是現行原始碼把擋法用
> `OXSDK_037_GUARD_OFF` 編掉，`ee185b3d` 則是擋法還沒寫的時候。兩者在**這個呼叫點**等價
> （關掉時照樣讀型態、照樣記錄，只是不拒絕），但這是等價不是同一份，寫在這裡不含糊帶過。

## 六、為什麼 per-stage deadline 接不到

同 037 已經寫過的理由，這裡只補一句更根本的：`engineLoop` 的 `stageDeadline` 只在
**命令佇列空著、正要去等**的時候才看。停在 `dispatch()` 裡的一個不返回的呼叫，
永遠回不到那個檢查點。**任何以「引擎自己會逾時」為前提的復原設計，對這一類都無效**——
唯一有效的是宿主側的期限加上換掉 worker，也就是任務 #33 出貨的那條路。

## 六之二、對上游報告的影響（2026-08-14）

原本的報告只舉 `doc_destroy` 一個入口。現在有兩個，而且第二個更難防：

- **`doc_destroy`**：使用者明確要求關檔，客戶端至少知道自己在做危險的事。
- **`doc_getTextSelection`**：**看起來是唯讀的**。它在內部造一份 `SwTransferable`
  （帶自己的 `SwDoc` 副本），函式返回時解構，於是走同一條 `DelLayoutFormat` →
  `IdlesLockGuard`。**卡的是返回前的清理。**
  （「文字已經取出來了」這句 2026-08-15 收窄：堆疊證不出走到哪個分支，
  支持它的是原生對照 798 bytes／1 ms，不是堆疊。見第六之三節末。）

~~`doc_getSelectionType`（`init.cxx:5966`）也呼叫同一個 `pDoc->getSelection()`，
所以它很可能是 038 的入口——**未取得堆疊，這是推論**。~~

> **2026-08-15 更正並取代**：038 的堆疊取到了，入口是**鄰居**
> `doc_getSelectionTypeAndText`（`init.cxx:5988`），不是這裡點名的 `doc_getSelectionType`。
> 類別層級的推論（一個從 `getSelection()` 取區域 reference 的讀取函式）成立，
> **點名的那個函式錯了**。見第六之三節。

**這也解釋了我方擋法為什麼有效**：037 的擋法在讀取之前先問選取型態並拒絕，
於是根本不呼叫 `getTextSelection`，那份會卡死的副本就從來沒有被造出來。
它不是修好了什麼，只是不去踩。

> **但這句話有邊界，038 就在邊界之外。** 擋法問型態用的是 `readSelection()`
> → `getSelectionTypeAndText`——**那正是 038 量到會卡死的那個呼叫**。
> 所以在 038 的構造上，擋法不是「涵蓋不到」，是**自己會踩下去**。
> **這一步是原始碼推論**：038 那三次執行走的是 `getState`，擋法沒有被呼叫過。

## 六之三、第三個入口：`doc_getSelectionTypeAndText`（2026-08-15，量到的）

證據 `findings/evidence/sdk-e2/discovery/038-entry-point/`，
artifact 同樣是 `e2-preguard-profiling`（`e05fd156…`，**沒有重連結**，
就是第六之二節那顆）。預測寫在執行之前（`PREDICTION.md`，commit `90cc23d`）。

**與 037 的堆疊第 0～20 格逐格完全相同**——同一顆 artifact 上的直接比對，
不是靠敘述對齊。只在第 21 格分岔：

| | 第 21 格（LOK 入口） | 深度 |
|---|---|---|
| 037 | `doc_getTextSelection` | 27 |
| 038 | `doc_getSelectionTypeAndText` | 28（多一格 `probe::readSelection()`） |

**所以這不是三個缺陷，是一個缺陷的四個入口**（012 的 `doc_destroy` 算第一個）。
`init.cxx` 裡從 `pDoc->getSelection()` 取區域 transferable 的函式**恰好三個**：

| 函式 | `getSelection()` 行 | 狀態 |
|---|---|---|
| `doc_getTextSelection` | 5926 | **量到卡死**（037） |
| `doc_getSelectionType` | 5966 | 結構相同，**未量到**——我方引擎只在 ABI 缺 combined API 時才走它 |
| `doc_getSelectionTypeAndText` | 6004 | **量到卡死**（038） |

（`doc_getClipboard`（`init.cxx:6074`）也持區域 `XTransferable`，但**來源不是**
`pDoc->getSelection()`，不列入。）

每個函式其實持**兩個**區域 reference——`XTransferable` 加上 query 出來的
`XTransferable2`（如 `init.cxx:6004`／`6011`）——解構發生在兩者逆序釋放之後。

**「文字已經取出來了」這句話要收回。** `doc_getSelectionTypeAndText` 確實在返回前才寫
out-parameter（`init.cxx:6028`），但**堆疊不告訴我們它走到哪一個分支**：
`isComplex()`（`init.cxx:6011`）、傳輸失敗、長度超過 10000、空字串**四個提前 return**
一樣會釋放區域 reference、一樣走到解構，而且全部在寫 out-param 之前。
同一次執行裡 FX-CELL 的選取型態就是 `complex`，所以那不是可以順帶假設的事。

**能說的只有：卡的是函式返回前釋放區域 reference 的那段清理。**
037 那一段原本寫的「文字已經取出來了，卡的是收尾」也一併收窄成這句
（外部對抗性覆核指出）。

**`SolarMutexGuard` 不會讓工程執行緒變成主執行緒。** 三個函式都先取 Solar mutex，
而 `IdlesLockGuard` 判定非主執行緒之後會先 `SolarMutexReleaser` 再等
（`scheduler.cxx:296`–`297`），所以 off-main-thread 的分析不受影響。

## 七、上游報告草稿

> **Summary**: On an Emscripten build, `Scheduler::IdlesLockGuard` constructed off the
> main thread deadlocks permanently.
>
> `Scheduler::IdlesLockGuard::IdlesLockGuard()` (`vcl/source/app/scheduler.cxx`) waits on
> `ImplSVData::m_inExecuteCondtion` when `!Application::IsMainThread()`. The only `set()`
> of that condition in the whole tree is in `Application::Execute()`
> (`vcl/source/app/svapp.cxx`), inside the `if (!pSVData->mpDefInst->DoExecute(nExitCode))`
> body. On Emscripten, `SvpSalInstance::DoExecute()` (`vcl/headless/svpinst.cxx`, under
> `#if defined __EMSCRIPTEN__`) calls `emscripten_set_main_loop_arg()` and is marked
> `O3TL_UNREACHABLE` — it never returns, so that body is never entered and the condition
> is never set.
>
> Any off-main-thread path reaching the guard therefore parks forever. The one we hit is
> `DocumentLayoutManager::DelLayoutFormat()`, reached from `~SwDoc` while destroying a
> document that contains a frame: closing such a document from a LOK thread never returns.
> **Two of the three entry points we measured are selection readers**
> (`doc_getTextSelection`, `doc_getSelectionTypeAndText`), which destroy a clipboard
> `SwDoc` on the way out and so hang while looking read-only.
> Measured stacks and the reproduction are attached.

（完整版在 `findings/drafts/040-bugzilla.txt`；上面這段是摘要，兩份都要一起改。）
>
> Version: 26.8.0.1.0+ (`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`).

## 八、方法論：這一輪自己抓到的一個假訊號

儀器第一版把「控制組非空」當成 hook 有效的證據。但控制組裡的 mailbox 活動
**不管 `proxyToMainThread` 的包裝有沒有裝上都會有**——於是「卡死期間零 proxy」與
「包裝根本沒裝上」會產生一模一樣的輸出，**一個兩種世界都會通過的判準不是判準**。
已改為分開記 `proxyHookFiredInControl`，並新增
`proxy-hook-unproven-only-mailbox-in-control` 這一種具名結果。這一輪該欄位為 true，
所以結論不受影響——但那個洞本來會讓一個錯的排除看起來像量測。

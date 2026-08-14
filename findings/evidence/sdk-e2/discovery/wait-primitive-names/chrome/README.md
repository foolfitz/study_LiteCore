# wait-primitive-names — 把停等的那幾格取出名字

[proxy-trace](../../proxy-trace/chrome/README.md) 量到引擎執行緒停在
`memory.atomic.wait32`，但那是在 `ee185b3d…` 上，**沒有 name section**，所以堆疊是
`$func15470` 這種索引。`e2-wait-diagnostic`（`150de122…`）是帶 `--profiling-funcs` 連結的，
**有** 14.8 MB 的 name section——但它同時帶著 037 的擋法，037 的讀取卡死在它上面打不到。
**兩份堆疊不可能出自同一輪。**

利用的一點：**閒置的 pool 執行緒坐的是同一個等待點**（proxy-trace 的控制組裡看得很清楚）。
所以不必重現任何卡死，只要在有名字的 build 上暫停幾條執行緒就拿得到等待原語的名字。

## 拿到的比預期多：關檔那條路整條都具名

`result.json` 第一輪就抓到引擎執行緒的 35 格完整堆疊：

```
emscripten_futex_wait ← __timedwait_cp ← __pthread_cond_timedwait ← pthread_cond_wait
  ← __libcpp_condvar_wait ← condition_variable::wait ← osl_waitCondition
  ← Scheduler::IdlesLockGuard::IdlesLockGuard()
  ← sw::DocumentLayoutManager::DelLayoutFormat(SwFrameFormat*)
  ← SwTextNode::DestroyAttr ← EraseText ← DeleteAttribute
  ← SwNodes::RemoveNode ← DelNodes ← ~SwDoc ← SwDoc::release ← ~SwDocShell
  ← SfxBaseModel::dispose ← SwXTextDocument::close ← doc_destroy
  ← probe::closeDocument ← dispatch ← engineLoop
```

**這就是 [finding 012](../../../../012-r6-styled-document-close-timeout.md)**——它當年只到
「WASM 停在 document destroy」。歸因與原始碼依據見
[finding 040](../../../../040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md)。

`f038-wedge.json` 是第二輪，換 `frame-contexts` fixture、`wedge-split` 模式跑的：
**抓到逐格相同的同一條 35 格堆疊**（獨立第二次），但**沒有**打到 038 自己的選取卡死。
所以 038 的堆疊仍未取得。

## 同一輪的其他執行緒（判讀的對照）

| 執行緒 | 底部 |
|---|---|
| 主 runtime | `SvpSalInstance::ImplYield ← loop(void*) ← iterFunc ← runIter ← MainLoop_runner` |
| pool（9 格） | `condition_variable::__do_timed_wait ← BufferedDecompositionFlusher::run()` |
| pool（12 格） | `configmgr::Components::WriteThread::execute()` |

主 runtime 那一列是 040 第四節的實測支點：**它在 emscripten 的主迴圈裡，
不在 `Application::Execute()` 的迴圈裡**——而設定 `m_inExecuteCondtion` 的程式碼只在後者。

## 跨 build 對應：12 個索引、零歧義

`tools/map_wait_frames_across_builds.py` 只配對**同角色**的堆疊（長度相同且 JS 尾端相同）。
第一版用交叉配對，把做 timed wait 的 pool 執行緒和做無限等的引擎執行緒混在一起比，
於是第 3 格看起來「有兩個候選」——**那不是歧義，是配對方法錯了**。

改成同角色配對後，037 停等堆疊的前綴六格全部解出，且
`$func15470 = emscripten_futex_wait` **與 proxy-trace 那個位元組層的 `fe 01`
是兩個互相獨立的方法得到同一個結論**。

**這仍是推論，工具自己會印這句。** 取代它的量測是把 pre-guard 原始碼帶
`--profiling-funcs` 重連結一次。

## 這一輪沒能做到的事

多輪取樣（`--pause-rounds 3`）**在第 0 輪之後失效**：兩次執行都是所有 worker 在第 1、2 輪
都拿不到 `Debugger.paused`，不只是引擎那一條。所以
`stability.identicalAcrossRounds` **這一欄沒有資料，不能拿來當「停住」的證據**——
這是工具限制，不是量測結果。

「它停住不動」目前靠的是三條互相獨立的證據：finding 012 的 180 秒逾時（100% 重現、
兩瀏覽器）、這裡的堆疊落在那條路上、以及 040 第四節那條原始碼上不可達的 `set()`。

## f037-preguard-named.json（2026-08-14）：037 自己的具名堆疊

上面兩輪都只拿到 012 的關檔堆疊。這一份是專為此建的 **`e2-preguard-profiling`**
（wasm `e05fd156…`：現行原始碼把 037 擋法以 `OXSDK_037_GUARD_OFF` 編掉，加 `--profiling-funcs`；
**刻意不帶 `-sPTHREADS_DEBUG`**——那是上一輪的死路），在 **037 自己的卡死當下**暫停取得。

`--wait-for-hang` 是為此加的：命名這一招原本靠閒置執行緒共用等待點，
但要看的那一格在**共用前綴之上**，只有引擎真的卡住時才存在。

**27 格，與當初那條沒有名字的堆疊逐格對齊**，第 7 格正是預測的
`Scheduler::IdlesLockGuard::IdlesLockGuard()`；先前靠消去法推出的
`$func2290 = osl_waitCondition` 一併證實。

**第 21 格是 `doc_getTextSelection`，第 17 格是 `SwTransferable::~SwTransferable`。**
所以 037 卡的不是讀取，是讀完之後銷毀那份剪貼簿 `SwDoc` 的清理路徑——
與 [012](../../../../012-r6-styled-document-close-timeout.md) 是同一個缺陷的兩個入口。
歸因與原始碼見 [finding 040](../../../../040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md)。

**界線**：這個 build 與 `ee185b3d` **不是同一份原始碼**（一個是擋法編掉，一個是擋法還沒寫），
兩者在該呼叫點等價但不是同一份；函式索引也不可互相對應——不過現在不需要了，
這一份自己就有名字。

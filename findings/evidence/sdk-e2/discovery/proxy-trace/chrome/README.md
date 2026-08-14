# proxy-trace — 停等的執行緒在等 futex，不是在等主執行緒服務

前一輪（[wedge-thread-state](../../wedge-thread-state/chrome/README.md)）判出
**停等不是空轉**，並把下一個問題交出來：「它在等什麼」。當時列了兩條可能，需要不同的修法：

- **H1**：它送了一個**同步代理到主執行緒**的呼叫，卡在等那個呼叫被執行。
- **H2**：它卡在 wasm 內部的鎖／條件變數，跟代理無關。

這一輪把兩者分開了。**H1 死了，H2 成立。**

## 儀器：JS-only，wasm 一個位元組都沒動

`e2-proxy-trace` 由 `e2-preguard-diagnostic` 產生，`probe.wasm` 是**硬連結**（同 inode），
sha256 仍為 `ee185b3d…`；只有 `probe.js` 與 `sdk-worker.js` 被 patch，記錄
`proxyToMainThread` 兩側、`emscripten_receive_on_main_thread_js` 兩側與 mailbox 活動。
**pthread 側的紀錄在同步代理把該執行緒停住之前就先 forward 出去**，所以卡死之後仍讀得到。
產生器：`tools/build_e2_proxy_trace_profile.py`，跑法：`tools/probe_proxy_trace.py`。

## 結果

| | 值 |
|---|---|
| `hookFired` / `proxyHookFiredInControl` | true / true |
| `unmatchedProxyIssuesAtCapture` | **`[]`** |
| `unmatchedReceivesAtCapture` | **`[]`** |
| 卡死當下 wasm 主 runtime 執行緒 | `MainLoop_runner` **一格**＝閒置 |
| `Debugger.pause` 控制組／卡死當下 | 兩者皆成功 |

**擷取當下沒有任何未完成的 proxied call**，而且主 runtime 執行緒是閒的、有能力服務。
H1 因此不成立。

## 真正有用的是順手加上的 `Debugger.pause`

上一輪的結論是「CPU profile 對停等執行緒什麼都取不到」，於是停在那裡。**但 V8 的 inspector
可以中斷 `memory.atomic.wait32`**——所以停等執行緒的堆疊一直都拿得到，只是沒去拿。

同一輪、同一批 worker、卡死前後各取一次：

| worker | 卡死前 | 卡死當下 |
|---|---|---|
| `0AF845F2` | 10 格 | **27 格**（最內側六格位移逐 byte 相同） |
| `7A142EC8` | 12 格 | 12 格，**逐格相同** |
| `71353E28` | 9 格 | 9 格，**逐格相同** |
| `8659A3B5`（主 runtime） | 27 格深入應用層 | **1 格**＝閒置 |

**控制組是內建的**：兩條 pool 執行緒兩欄一模一樣，證明「兩欄相同」正是閒置該有的樣子；
`0AF845F2` 是唯一變的那條，它就是引擎執行緒。

## 停在哪一個指令（位元組層）

`0AF845F2` 最內側 frame 的模組位移 7064008，該處位元組：

```
44 00 00 00 00 00 00 f0 7f  f64.const +inf
61                          f64.eq
1b                          select
fe 01 02 00                 memory.atomic.wait32
```

`fe 01` 就是 `memory.atomic.wait32`。**停等發生在 wasm 內部**，不經 JS，
所以先前想「hook `Atomics.wait`」那條路本來就不可能有東西——glue 裡唯一的
`Atomics.waitAsync` 是 mailbox 用的。

名字見 [wait-primitive-names](../../wait-primitive-names/chrome/README.md)；
整件事的歸因見 [finding 040](../../../../040-idleslockguard-waits-on-a-condition-an-emscripten-build-can-never-set.md)。

## 這一輪自己抓到的一個假訊號

儀器第一版用「控制組非空」當 hook 有效的證據。但控制組裡的 mailbox 活動**不管
`proxyToMainThread` 的包裝有沒有裝上都會有**——於是「卡死期間零 proxy」與「包裝根本沒裝上」
會產生一模一樣的輸出。**一個兩種世界都會通過的判準不是判準。** 已分開記
`proxyHookFiredInControl`，並新增 `proxy-hook-unproven-only-mailbox-in-control` 這個具名結果。
本輪該欄位為 true，結論不受影響。

## 界線

- 這是 **037 的卡死**（pre-guard artifact，出貨的 `c89f069e…` 帶擋法打不到）。
- `namedOutcome` 印的是 `proxied-call-issued-during-hang`，那是**視窗定義造成的**：
  被算進「卡死視窗」的 8 筆代理呼叫落在視窗起點附近，而且**全部完成**。
  權威欄位是 `unmatchedProxyIssuesAtCapture`／`unmatchedReceivesAtCapture`，兩者皆空。
- trace 很吵：`dropped` 191198、保留 20000、擷取尾端 2000 筆。判讀靠的是尾端與未完成計數，
  不是總量。

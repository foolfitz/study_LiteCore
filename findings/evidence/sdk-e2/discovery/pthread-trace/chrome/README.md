# pthread-trace — emscripten 的 pthread 追蹤，跨過一次卡死

**結論先講：`-sPTHREADS_DEBUG=1` 不能回答「它在等什麼」。**

挑這個旗標是因為預期它會追 futex 等待與代理到主執行緒的呼叫。實際上
`src/lib/libpthread.js` 裡的 `#if PTHREADS_DEBUG` 只印**執行緒生命週期**：
`createThread`、`threadInitTLS`、`invokeEntryPoint`、`cleanupThread`、`terminateWorker`
這一類。**沒有一行印 futex、mutex 或 proxy。**

這一輪整場只有 66 行 console 輸出，全部來自啟動階段；卡死當下一行都沒有。

**選工具之前要先讀它會印什麼**——這一輪是我對旗標的假設錯了，不是量測失敗。

## 這個 build 還是給了東西

`--profiling-funcs` 讓 wasm 帶了 name section（14.8 MB），於是同一批 worker 再 profile
一次時，先前只能寫成 `wasm-function[36295]` 的那幾條有了名字：

    __pthread_cond_timedwait

也就是**一個 thread pool 在等工作**——先前是從「它呼叫 `_emscripten_check_blocking_allowed`」
推出來的，現在是直接量到的。

## 界線

追的是 finding 038 的卡死（註腳裡的 frame，選取時卡），不是 037 的讀取卡死——
這個 build 帶著 037 的擋法，讀取那條路打不到。

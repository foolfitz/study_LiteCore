# wedge-trace — finding 037 的 LOK callback 串流

`e2-wedge-trace` profile 與出貨的 `e2-format-discovery` **共用同一份 `probe.wasm`**
（`ee185b3d…`，由 `build/archive/e2-format-discovery-ee185b3d/` 打包，雜湊在
`ARTIFACT.sha256` 裡對過），差別只在 worker 副本多兩行：

```js
    case "lok":
      if (debugEnabled)
        postEvent("diagnostic", { level: "lok-trace", detail: event });
```

引擎本來就把**每一個 LOK callback** 當成 `{"type":"lok"}` 事件送出
（`probe_engine.cpp` `onLokCallback`，在處理之前送），出貨的 worker 只轉發其中兩個
id，其餘丟掉。這裡把整串轉發出來，因為**一個永遠不返回的 barrier 不會寫任何自己的證據**，
callback 串流是唯一還留著的紀錄。

**沒有重編引擎**，所以這批量測與它要解釋的那一輪綁在同一份 artifact 上（finding 027／036）。

- `result.json` 的 `engineTrace`：每一筆是一個 callback，附抵達頁面的時間戳。
- `engineTraceCounts`：依 id 計數，環狀緩衝丟掉的項目也還算在裡面。
- `liveness`（attempt-03 起）：三段活性梯——worker JS／wasm 主執行緒／引擎執行緒。

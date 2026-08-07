# R8 已知限制

- 沒有使用者授權的 T2 HTTPS／CDN 環境時，只能判定 `PARTIAL_GO_LOCAL_DELIVERY`；loopback 數字不是 CDN SLA。
- 真實 browser quota exhaustion 無安全、可攜的 deterministic 控制；本機只驗證 cache write failure、quota-like failure、
  bounded eviction 與 known-good 保留。
- candidate 採用需要明確 reload／新 session；不支援既有 Document Worker 熱換 release。
- Firefox 反覆建立大型 WASM Worker 存在 Finding 014 generation exhaustion；產品必須採 bounded reuse 與 reload 提示。
  R8-D在R8-C完整Firefox矩陣後的兩次active-cache corpus campaign都於第一批前timeout，因此Firefox的R8
  production validation採R7完整corpus／30分鐘soak與R8-C active-release矩陣的組合證據；對應summary保持
  `pass:false`，只在top-level `PARTIAL_GO_LOCAL_DELIVERY`明列接受，不能宣稱已完成單一combined run。
- Finding 012 的 styled document close 仍採 bounded Worker recovery；未儲存 mutation 不可恢復或自動重送。
- DOCX public open 仍為 Finding 013 的 typed unsupported；R8 delivery 通過不代表 DOCX import／export 已支援。
- Cangjie／Pinyin、document-content accessibility、安全 hyperlink activation、generic rich clipboard、圖片貼上與拖放未驗證或不支援。
- R8 不包含任意 caret、selection、方向鍵、delete、newline、Redo 或 rich formatting；這些屬 R8 後的 ODT-first 基本編輯器里程碑。
- SHA-256 是內容 identity，不是數位簽章；authenticity 依賴受信任 HTTPS origin 與部署權限。
- Service Worker 只管理 allowlisted application artifact 與固定 health fixture，不持久化使用者文件或協作資料。

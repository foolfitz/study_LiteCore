# SPEC R3-000：Semantic review operations

> **日期**：2026-08-01  
> **狀態**：已完成（GO）  
> **依據**：[R2 結果](../devlog/DEVLOG-2026-08-01-wasm-sdk-r2.md)、
> [SDK 主報告 §10](../research/RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)

## 1. 目標

在 R2 已穩定的 typed SDK boundary 上加入第一組 Writer review operations：

```text
search → read selection → replace selection → undo
       → add/list comment
       → enable tracked changes → replace → list redlines
       → save ODT → desktop round-trip
```

應用層只提交帶 `expectedRevision` 的語意操作，不取得 UNO object，也不能傳任意
`.uno:*` command。

## 2. v1 範圍

- 搜尋下一個純文字 match，方向可選；回傳是否找到、正規化 rectangles 與當下 revision。
- 讀取目前 plain-text selection。
- 以 UTF-8 純文字取代目前 selection。
- Undo 最近一次 Writer mutation。
- 在目前 selection／cursor 新增 comment，並列出 comments。
- 明確開啟／關閉 change tracking，並列出 tracked changes。
- 所有 mutation 使用 adapter-local、單調遞增 revision；revision 不因 undo 倒退。
- replace/comment/track-changes/undo 都要求 `expectedRevision`，不相符回報
  `STALE_REVISION`，且不得修改文件。
- 以 validated `replaceSelection` operation 作為 R3 的結構化結果插入切片。

## 3. 明確不在 R3

- 任意 UNO command passthrough、UNO object graph 或 raw LOK callback payload。
- regex、replace-all、跨 part search、多 selection、多文件並行。
- comment reply/edit/delete、redline accept/reject、作者身分與權限模型。
- Markdown parser／HTML paste；R3 只驗證純文字 structured replacement。
- 真 IME、DOCX corpus、Provider contract（R4）。
- **體積最佳化**：維持延後到 R5，R3 只記錄 artifact drift。

## 4. ABI 與相容性

R3 以 backward-compatible minor bump 將 C ABI 升為 1.1（`0x00010001`）。ABI 1.1 runtime
必須接受 1.0 client；major 不同或 client minor 高於 runtime 才回報 `INCOMPATIBLE_ABI`。

新增 capability bits：search、selection text、replace selection、undo、comments、tracked changes。
新增 exports：

```text
oxsdk_document_search
oxsdk_document_get_selection
oxsdk_document_replace_selection
oxsdk_document_undo
oxsdk_document_add_comment
oxsdk_document_list_comments
oxsdk_document_set_track_changes
oxsdk_document_list_changes
```

字串 input 仍採 borrowed pointer+length 並在 C call 返回前複製。Result 經既有事件通道回
Worker；comments／redlines 在 Worker 解析成 structured-clone data，主執行緒不看 raw LOK
payload。

## 5. Public TypeScript surface

```ts
const match = await doc.search("LibreOfficeKit")
const selection = await doc.getSelection()
await doc.replaceSelection("LOK", { expectedRevision: selection.revision })
await doc.undo({ expectedRevision: doc.revision })

await doc.addComment("R3 review note", {
  author: "OxOffice SDK",
  expectedRevision: doc.revision,
})
const comments = await doc.listComments()

await doc.setTrackChanges(true, { expectedRevision: doc.revision })
await doc.replaceSelection("replacement", { expectedRevision: doc.revision })
const changes = await doc.listTrackedChanges()
```

SDK 遇到 `STALE_REVISION` 必須回傳 typed `StaleRevisionError`，details 至少含 operation、
expected 與 current revision。

## 6. LOK adapter 邊界

- Search 僅由 allowlisted `.uno:ExecuteSearch` 實作，等待 search-result／not-found callback。
- Selection 僅使用 `getTextSelection("text/plain;charset=utf-8")`。
- Replace 使用既有 plain-text paste，作用於目前 selection。
- Undo、comment、track changes 使用固定 allowlisted UNO commands；不接受 caller command name。
- Comments 只查 `.uno:ViewAnnotations`；redlines 只查 `.uno:AcceptTrackedChanges` command values。
- 非同步 UNO/search request 在 callback 前視為 in-flight，cancel 回報 `NOT_CANCELLABLE`。

## 7. 驗收

1. ABI header assertions 證明 1.1 編碼與 1.0 相容規則；新增 exports/capabilities 完整。
2. SDK unit tests 覆蓋 search/selection、revision propagation、typed stale error、comment、redline
   與 ABI 1.0 client compatibility。
3. Chrome／Firefox 各至少 3 次完成：search → selection → replace → undo → comment → tracked
   replacement → save。
4. 每個瀏覽器重現 stale revision，不得發生文件 mutation。
5. 輸出 ODT 包含預期 replacement、comment 與 tracked-change markup，且桌面 LibreOffice 可開啟。
6. R2 conformance 與 R1 legacy smoke 仍通過。
7. 不修改 `libreoffice-26-8` tracked files；不連 unoembind、不用 JSPI／
   `PROXY_TO_PTHREAD`。
8. 交付 R3 DEVLOG、console/screenshots、round-trip 與機器可讀摘要。

## 8. Go／No-Go

**Go**：typed semantic operations、revision guard、undo、comment/redline round-trip 在兩個瀏覽器
成立，可進 R4 Provider SDK。

**部分 Go**：search/replace/undo 成立，但 comment 或 redline 失敗；保留 core operations，將
失敗能力自 manifest 移除並記錄 evidence，不用 generic UNO passthrough 掩蓋。

**停止回報**：操作只能靠修改 LibreOffice core、revision guard 無法避免 stale mutation，或
save round-trip 造成可重現壞檔。

## 9. 2026-08-01 實測結果

**判定：GO，可進 R4。**

- ABI 1.1、八個新增 exports 與六組 capability bits 已完成；Chrome／Firefox 均確認 1.0
  client 可連線，1.2／2.0 client 正確被拒絕，且 public SDK 沒有 generic UNO surface。
- Node SDK tests 8/8、C ABI header compile 與 Emscripten strict undefined-symbol link 通過。
- Chrome 150、Firefox 152 各 3 次完整 semantic review flow，6/6 通過；stale revision 均含
  expected/current details，故意寫入的文字沒有進入文件。
- 6 份 ODT 都包含預期取代、1 個 comment、2 個 changed regions 與 insertion/deletion，且桌面
  LibreOffice 26.2.4.2 全數可轉成 PDF。
- R2 conformance 兩個瀏覽器全數通過；R1 legacy flow 兩個瀏覽器 2/2 通過 round-trip。
- Runtime 相較 R2 僅增加 raw 22,982 bytes、gzip -9 9,804 bytes；只記錄 drift，最佳化仍在 R5。
- `libreoffice-26-8` tracked 狀態與進場前相同，未修改 core 或 Qt6 build。

完整數字與整合行為見
[R3 DEVLOG](../devlog/DEVLOG-2026-08-01-wasm-sdk-r3.md)及
[機器可讀摘要](../findings/evidence/sdk-r3/summary.json)。

# R7 最小人工驗收引導

R7最終判定不再要求額外人工驗收；下列僅供交付前5分鐘smoke，不取代machine evidence。

1. 啟動`cd wasm_sdk_probe && python3 web/serve.py --port 8766`。
2. Chrome或Firefox開啟`http://127.0.0.1:8766/r7-reference.html`。
3. 載入ODT，確認頁面可見、Search可命中、zoom與page controls可用。
4. 使用Fcitx5 Chewing輸入一小段台灣正體中文，按一次貼上純文字，儲存ODT。
5. 以桌面LibreOffice開啟輸出；確認中文與貼上內容各出現一次。

預期限制：DOCX會typed unsupported；Cangjie／Pinyin與完整document accessibility未宣稱；Firefox長時間反覆
建立／重啟大量Worker時應重新載入整個browser工作階段。若只做既有ODT閱讀／review，不需再次人工驗收。


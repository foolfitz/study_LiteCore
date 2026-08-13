# A7 的 round-trip 切片：這顆引擎寫出來的 ODT 是不是健全的文件

**日期**：2026-08-13　**判定**：`A7_ROUNDTRIP_PASS`
**綁定引擎**：`c89f069e7c43e78e630e4f7d62ba5d016c7aaf434d9f4abf5a0e009e931f9d0f`
**工具**：[`tools/validate_e2_a_roundtrip.py`](../../../../../wasm_sdk_probe/tools/validate_e2_a_roundtrip.py)
**報告**：[`report.json`](./report.json)

A3／A4／A5 問的都是同一種問題——「這一段有沒有進到動作要求的狀態」——而且都是**讀回檔案**來回答。
沒有一項問「這個 package 健不健全」，也沒有一項問「換一個 LibreOffice 打不打得開」。
規格第 5 節把那件事放在 A7，第 8 節讓 A7 成為 `GO_TO_E2_B` 的一部分；
2.8 節縮限 3 白紙黑字寫著把序列化器輸出釘成 ABI 是 A7 的工作、目前沒有任何地方驗過。
E2-000 第 10 節則把「清單切換造成 ODT 結構 silent loss」列為**停止條件級**風險——
結構檢查正是為那條而存在的。

## 這一輪做了什麼

**沒有跑任何新的瀏覽器輪。** 材料是既有證據樹裡、由現行 artifact 產出的存檔 ODT。

| | 值 |
|---|---|
| 綁定現行 artifact 的文件 | **406**（Chrome 222、Firefox 184） |
| 因綁定到舊 build 而略過 | 2 153（逐個 hash 列在 `report.json`） |
| 結構檢查通過 | 406／406 |
| 桌面版重開＋PDF 匯出成功 | 406／406 |
| 桌面版版本 | LibreOffice 26.2.4.2 620(Build:2) |

**結構檢查看到的東西**（不是「檢查跑過」而是「檢查有東西可看」）：
帶 `text:list` 的 254 份、帶 `text:h` 的 149 份、帶可解析樣式參照的 406 份。

每份文件跑七類檢查：ZIP CRC；`mimetype` 必須是第一筆且未壓縮；所有 `*.xml` 可解析；
zip 成員與 `META-INF/manifest.xml` 雙向相符；fixture 的 anchor 文字仍在；
**每一個樣式參照都解析得到宣告**；`text:list-item` 必有 `text:list` 父節點、
`text:list` 不得為空、`text:h` 必須有合法 outline level。

## 兩個檢查自己的控制組，因為不會失敗的檢查等於沒有檢查

**結構檢查**：拿證據樹裡一份真文件，五種破壞法各做一份——`mimetype` 移到最後、
`content.xml` 標籤不成對、把**有被參照的**樣式改名、從 manifest 拿掉 `content.xml`、
把 list-item 拉出 list。五種全部被抓到，逐項記在 `report.json` 的 `selfTest`。

**桌面重開**：把同一份文件弄成 XML 不成對，交給 soffice——**被拒絕**（`refusesABrokenDocument`）。
沒有這一條，「406 份都轉出 PDF」只證明 soffice 願意對任何東西吐 PDF。

## 第一版的自我測試是壞的，換掉了

第一版把 content.xml 裡**第一個**樣式宣告改名。它挑到的樣本 content.xml **一個樣式都沒宣告**，
於是那次突變什麼都沒改，`unresolved-style` 這條檢查回報「通過」而根本沒被執行——
而它正是對著 silent structure loss 那條停止條款的檢查。

改法兩件：突變改成「把**確實被參照到**的樣式改名」；樣本改成挑**表達力最高**的那一份，
並要求樣本本身至少帶一個可解析樣式與一個 list-item，否則自我測試直接判不通過。
現行樣本帶 21 個可解析樣式參照、1 個清單、7 個標題。

`tests/test_e2_a_roundtrip.py` 另外用合成文件逐條釘住每一類檢查（17 個測試），
並且抓出工具的一個真缺陷：deflate 流損壞時 `testzip()` 是**丟例外**不是回傳，
原本會讓整輪掃描中斷而不是讓一份文件判失敗。已修成具名失敗。

## 這一輪**不能**宣稱的事

1. **A7 沒有完成，E2-A 仍然沒有總判定。** A7 還有回歸那一半（R6～R8、E1-A／B／C、
   workspace preflight），本輪完全沒碰。第 8 節的 `GO_TO_E2_B` 因此仍未達成。
2. **桌面重開是跨版本，沒有同版本對照。** 引擎是 26.8，這台機器上只有 26.2 桌面版。
   跨版本其實正是縮限 3 想問的方向，但「同版本一定開得起來」這件事**沒有量**。
3. **只驗 package 開得起來，沒驗 PDF 的內容。** 判準是 `%PDF-` 檔頭與大小門檻，
   沒有比對頁數或文字。「重開後看起來一樣」不在本輪範圍。
4. **縮限 3 沒有解除。** 這一輪說的是 package 重開得了，不是 barrier 比對的那串
   readback markup 跨版本穩定。那要另外量。
5. **A6 仍未執行。**

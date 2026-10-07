# 113 — v15 的 CJK 子集只剩一個家族名：預設與 SC／JP／KR 的亞洲字型槽落到 Liberation Sans，含中文的行高縮成約 0.8 倍、文件重排

| | |
|---|---|
| **狀態** | **已確認**（2026-10-07）；成因已定位到字型家族名；候選修法已量（同一份 E 級子集包成五家族 TTC），**採不採用待擁有者決定** |
| **所在** | 我方打包：v15 的 CJK 包 `cjk-sub-e`（`tools/build_cjk_subset_pack.py`）。引擎、頁面、殼層都不是 |
| **發現日** | 2026-10-07（v15 產品路徑網 shakedown 的 A、B 兩處紅，診斷到底） |
| **嚴重度** | 一般：沒有東西消失、字也都畫得出來，但凡是沒指定亞洲字型、或指名 Noto Sans CJK SC／JP／KR 的文件，含中文的每一行都變矮、整份重排；存檔還會把 `Liberation Sans` 寫進文件的預設亞洲字型 |
| **可重現** | 100%（決定性：三輪逐格相同；探針 32 行逐列相同） |
| **是否上游** | 否 |

## 現象

v15 上，一行只要含中日韓文字、而該段的亞洲字型名稱不是剛好 `Noto Sans CJK TC`，行高就從 v8 的 20 px 變成 15–16 px（Chrome 畫布），
約 0.8 倍。字形照常畫出（glyph fallback 從子集補字），所以看不出「缺字」，只看得出行距擠、版面往上縮。產品路徑網因此紅了兩處：
Firefox 的游標兩格（取樣那一行換了內容）、Chrome 的第 42 格（腳註文件前兩行擠到 8 px 以內被併成一條 band，038 的誘因打錯行，
一次性的 worker 誘因被前一格用掉，第 42 格量不到 B4）。

## 重現步驟

1. `wasm_sdk_probe/tools/probe_cjk_font_slots.py --profiles e2-editor-v8 e2-editor-v15 --out <dir>`
2. 看 `<dir>/font-slots.json` 的 `documents[2].pitches` 與每份文件的 `fontNames`

**預期**：與 v8 相同（v15 只該改字形涵蓋範圍，規格 §19 登錄的是「日韓簡標記的文字改用繁中字形」）。
**實際**：預設、SC、JP、KR 四種的行高 16／16／15／16，v8 是 20／20／20／19；引擎寫下的預設亞洲字型是 `Liberation Sans`，v8 是 `Noto Sans CJK KR`。

## 證據

`evidence/v15-shakedown/cjk-ab/`（README 英文）：

- **A/B（同一支儀器、單一變因）**：同一顆 v15 連結、只把 CJK 包換回完整 `cjk-r5`（`e2-editor-v15-cjk-r5-ab`），兩個瀏覽器的每一格都回到
  v8 的結果；對 v15 的差異恰好是那三格紅。所以 B、096、082 這三個引擎改動在這幾格上是乾淨的，紅全部來自 CJK 包。
- **引擎自己的答案**：存檔讀回 `styles.xml` 的預設段落樣式——v8 與 A/B 都是 `Noto Sans CJK KR`，v15 是 `Liberation Sans`。
- **行高**：`font-slots-r3/pitches.txt`（16 種變體，各兩行相同的段落）。

## 分析

- 子集與原 TTC 每個 face 的垂直度量逐欄相同（`hhea`、`OS/2`、`head`），所以「選到子集」不會改行高；改的是**有沒有選到它**。
- 原 TTC 有十個家族（Sans 與 Mono 各 JP／KR／SC／TC／HK），子集只有 `Noto Sans CJK TC`。LibreOffice 挑預設亞洲字型時
  （`OutputDevice::GetDefaultFont`，`vcl/source/outdev/font.cxx:434` 起；zh-cn 的 `CJK_TEXT` 清單裡沒有任何一個存在的字型，
  於是用整串名稱去要一個實際的 font instance，取它的家族名），v8 落在 `Noto Sans CJK KR`，v15 落在 `Liberation Sans`；
  指名 SC／JP／KR 的段落同樣落到拉丁字型。**為什麼 v15 不落在 TC**（fontconfig 說 E 級子集涵蓋 zh-cn）**沒有追**——修法不需要它，
  而修法本身就是可否證的量測。
- 純拉丁行不受影響（任何設定下 v8／v15 都是 15–16）。
- **不是 v15 的差異、也沒有診斷**：台灣文件常用的名字（思源黑體、PMingLiU、新細明體、Microsoft JhengHei、AR PL UMing TW、標楷體，標
  zh-TW）在 **v8 上本來就是拉丁行高**。算不算保真度缺口，取決於拿什麼比（那些真字型自己的度量也不同於 Noto Sans CJK），沒有量。

## 候選修法（已量，未採用）

`tools/build_cjk_subset_ttc_candidate.py`：出貨的 E 級字型照原 TTC 的 face 順序（JP、KR、SC、TC、HK）放五次，只有 `name` 表不同
（TC 那個 face 保留子集原本的 name 表），存成表格共用的 collection。7,210,328 位元組，比出貨子集多 9,696（＋0.13%）；建兩次逐位元相同；
每個 face 的 cmap／hmtx／vmtx／hhea／OS/2／CFF／GSUB／GPOS 都與出貨子集相同。所以字形涵蓋、輪廓、度量都還是 E 級，而規格 §19 登錄的
損失會**照字面成真**：指名 SC／JP／KR／HK 的文字畫繁中字形、行高與 v8 相同。

不出貨的 profile `e2-editor-v15-cjk-ttc5-ab` 上：探針 32 行的位置與 v8 逐列相同、預設亞洲字型寫回 `Noto Sans CJK KR`；產品路徑網兩個瀏覽器各一輪，每一格都與完整 TTC 對照組相同（證據 README 第 4 節）。

## 還缺什麼

- [ ] 擁有者決定採不採用候選（採用＝新的 CJK 包＝新的 profile 身分，不需要重新連結）
- [ ] 規格 §19 的 tile 判準要修訂：日／簡／韓標記的文字本來就會換字形，「tile 逐張相同」在那些文件上不會成立

## 時間軸

- 2026-10-07 10:42–12:07 v15 產品路徑網，A、B 兩處紅（`evidence/v15-shakedown/product-path/`）
- 2026-10-07 13:24–13:37 A/B profile，兩處都回到 v8（預測先 commit：`8f54ea3a`）
- 2026-10-07 字型槽探針 r1（fixture 沒送出去，404）、r2、r3；五家族候選與其探針（預測：`7b8f1ec4`、`0a6222dd`）
- 2026-10-07 候選的產品路徑網：兩個瀏覽器各一輪，與完整 TTC 對照組逐格相同

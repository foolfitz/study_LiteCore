# 2026-08-15（第三段）：G1 那格關掉、第 5 節被逐項打回原始碼

接續 [`handoff/HANDOFF-2026-08-15c-session-state.md`](../handoff/HANDOFF-2026-08-15c-session-state.md)。
那份交接列了三條下一步，這一段做掉其中兩條，第三條（跨段處置）送去外部裁決。

## 做了什麼

### 一、G1 那格關掉了

第一輪把 G1 判 void 的理由是 fixture 不對——`第三段跨行 gamma` 是段落很高、
不是跨行。凍結的 E1 corpus（`frozenDate 2026-08-04`、`mutationPolicy copy-only`）
不能動，所以新開 `dist/e2b-fixtures/`，寫 `tools/create_e2b_fixtures.py` 產
`wrapped-paragraph.odt`（1319 字）。

三件事值得記：

**fixture 的錨點必須出現在每一條視覺行上。** 掃描是「在某個 y 選一整條橫帶再讀回
文字」，所以它只認得出**那一行**上的字。散文會把錨點放在第一行，`findSpan` 就
找不到跨距。改成重複 token（`G1WRAP-001…120`）之後每行都認得出來。

**調 fixture 與產生判定不能是同一次 run。** 「這段會不會換行」是 fixture 的性質，
量它要做一次 span select——而那就是 G1 的前半。所以加了 `--geometry-only`：
只選、只記矩形，不派送也不存檔。它報 3 與 1，之後判定輪也是 3 與 1。

**對照臂 G1c。** 同一份文件、同一個機制、瞄一段不會換行的段落，必須恰好 1 個矩形。
它擋的是「這顆 build 對什麼都回報多矩形」——若成立，G1 的計數什麼都證明不了。

結果：G1 兩瀏覽器各三輪**全過**，六次讀數完全一致。3 個矩形貼齊地鋪滿
`y=1807→4290`：第一行、中間整寬的併合塊、最後半行。

**預測的數字錯了。** 我猜 8–20 個矩形（1319 字除以行寬），實際 3，因為 LOK 會把
中間整寬的行併成一個高矩形。判準寫的是 `> 1`，那一條對。照記不刪。

### 二、分析器差點又犯同一個錯

把 G1 改瞄新 fixture 要改分析器的錨點表。以**臂名**為鍵的話，同一支分析器就判不出
第一輪的結果了——**那正是第一輪第三個比較器錯誤的形狀**（事後寫的判準悄悄偏離
事前登記的）。改成 `(arm, fixture)` 為鍵，兩個 fixture 都列著，然後拿第一輪的證據
重跑，`verdict.json` 兩瀏覽器都**逐位元重現**。

順帶：第一輪的 G1 現在是這條判準的**負向對照**——同一支分析器、同一條判準、
一份不會換行的 fixture，那一臂不會變綠。

### 三、第 5 節被逐項打回原始碼，撤掉一項、新增七項

第 5 節從 v1 到 v3 都是**從對抗性審查的意見寫的，不是從原始碼重讀寫的**。
這次請 codex 逐項回到 source 覆核，我再自己複驗每一項。

**第 4 項判為錯誤並撤回。** 我寫「no-op 的 revision 語意是版本差異」，依據是
`SPEC-E1-B:82`。那句是**規格原文**，不是**現行實作**：finding 022 之後引擎已經
不讀前置狀態（`probe_engine.cpp:3595` 的註解寫得很清楚），成功一律 `+1`，
client 也明文拒絕 `documented-state-noop`。v1 與路線 C 在 revision 上**沒有差異**。
順手在 E1-B 那一行加了取代標註——它到今天都還被當成現況引用。

**新增第 8 項，它推翻了第 3.9 節。** 我一直寫「產品 build 上重跑＝一次 relink」。
產品 objects 的旗標是 `-DOXSDK_EDITOR_DISCOVERY -DOXSDK_FINDING_016_SELECTION_BARRIER`
（`Makefile:538`），**沒有 `-DOXSDK_E2_FORMAT_BARRIER`**；而路線 C 整段包在那個
`#ifdef` 裡。**產品 build 根本沒有把路線 C 編進去**——那不是一次 relink，
那是一個還不存在的建置變體。

### 四、凍結測試少凍了兩個動作

覆核第 14 項時發現的，而且不是 v2 的問題，是**已出貨的 v1**：

- `editor-client.d.ts` 只宣告到 `set-italic`，`setInlineFormat` 只允許 bold／italic
  ——而 runtime 自己的錯誤訊息就寫著四種。
- `tests/editor_abi_header_test.cpp` 只 assert 動作 1–8，也完全沒碰
  `oxsdk_editor_select_range`。**那支測試存在的理由就是釘住 header，
  結果兩顆出貨 artifact 期間它只釘住十個動作裡的八個。**

兩邊補齊，並加 `declaration-drift.test.mjs` 直接讀 `.d.ts` 跟 runtime 比對。
三個新檢查各做突變控制都變紅。

### 五、finding 043 的重複單查了

七組跑完：六組零命中，一組四筆全部無關且早已修掉。**加跑五個正向對照**——
零命中和查詢語法壞掉從外面看是一樣的。`summary:selection` 打滿 200 筆上限，
`ALL content:setTextSelection` 命中一筆（2015 年 LOOL 的表格 UX，無關）。
那一筆同時說明草稿列的 `summary:setTextSelection` 太窄。

Component 用查得到的慣例確認：Writer 側 LOK 缺陷 100 筆樣本裡 41 筆落在
`LibreOffice/Writer`，是最大一群。

## 送出去給誰判

**codex**（`sandbox=read-only`）：第 5 節七項逐項覆核 ＋ 找漏 ＋ **relink 分區**
（哪些改動會重連結 probe.wasm、哪些不會）。回來的每一項我都自己回原始碼複驗，
抽查四項全對，其中一項反轉了我的規格文字。

**fable**（subagent，**agent id `a1a9e1c0a82203872`**，可用 SendMessage 續談）：
跨段範圍的處置怎麼定案。這一條決定唯一那次 relink 要編什麼進去。

## 還開著的

- **跨段處置**（等 fable）。定案之後要寫預測、進 relink、再測。
- **G1 的殘留一格**：範圍兩端都落在段落內部（掃描視窗到 4400 就停）。
  A 臂涵蓋「整段」、G1 涵蓋「多矩形」，**兩者的交集沒有量**。判斷是這格風險低，
  但它存在，寫在 README 與 9.6。
- **第 5 節第 8–13 項**，其中第 12 項（派送後失敗的 revision／dirty／recovery 語意）
  必須和跨段處置**同時**決定，否則就是第二次 relink。
- 兩件欠著的 Makefile（`f049` 的語法檢查、E2-B harness 與 `dist/e2b-fixtures/`
  的 target），留到那唯一一次 relink。

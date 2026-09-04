# 089 — 一份 13 KB 的試算表在 wasm 上逾時 180 秒，原生 269 毫秒開完

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | **未確認**——可能是上游，也可能是我方的 wasm 組態；沒查到根因前不要送 |
| **發現日** | 2026-09-05 |
| **嚴重度** | 嚴重（該檔完全開不起來） |
| **可重現** | **2/2** |
| **是否上游** | **未確認** |

## 現象

`sc/qa/unit/data/ods/tdf149752.ods`（13,463 bytes、兩張工作表）在候選
`e2-editor-v12` 上開啟逾時——`LOK_ERROR` 之前先撞到 SDK 的 180,000 毫秒上限。

**同一個 commit 的原生 LibreOffice 用同一支 LOK API 開它只要 269 毫秒。**

## 重現步驟

```bash
cd wasm_sdk_probe
python3 tools/probe_ods_on_profile.py --profile e2-editor-v12 \
    --fixture test-docs/ods/upstream/tdf149752.ods \
    --control dist/e2-fixtures/d1-anchors.odt --timeout 900
```

**預期**：像原生一樣開起來（parts=2）。
**實際**：`{"name":"DocumentSdkError","code":"TIMEOUT","message":"open timed out after 180000 ms"}`

## 證據

- `evidence/m4-ods/04-sweep-v12.json`——306 份語料的全量掃描，**303 開得起來、
  4 開不起來**。其中三筆是加密檔（原生也拒絕，是預期的拒絕），**這一筆是唯一
  「原生開得起來而候選開不起來」的**。
- `evidence/089/recheck-2-of-2.json`——單檔重跑，再次逾時。**同一次跑的 ODT 對照組
  正常開啟**，所以逾時不是儀器或環境。
- `evidence/m4-ods/01-native-oracle/oracle.jsonl`——原生：
  `loaded: true, parts: 2, 26775 x 25500, loadAndReadMs: 269`

## 分析

該檔與語料裡其他 305 份的區別，讀 `content.xml` 得到：

```
content.xml            77,195 字元
table:table                 2
table:table-row           129
table:table-cell          548          ← 實際只有五百多格
number-rows-repeated  最大 1,048,550   ← 2^20 − 26，「整張表剩下的列」
number-columns-repeated 最大 1,020
另有 table:database-range ×4、table:named-range ×3、chart ×1、office:forms ×2
```

**假說（未驗證）**：`number-rows-repeated` 那個接近整張表高度的重複計數，在 wasm 這顆
build 上走到一條會實體化或二次方展開的路徑，而原生沒有。

**這是假說。**沒有量到的東西包括：逾時發生在哪一個階段（`open.begin` 之後的 stage
事件在逾時的 run 裡沒有留下）、是 CPU 忙碌還是等待、以及把那個屬性改小之後是否就
開得起來。**在量到之前不得寫進上游報告**——上游會問「你怎麼知道是這個屬性」，而
目前的答案是「它是唯一顯眼的差異」，那不是根因。

**下一步（便宜、確定性）**：把該檔的 `number-rows-repeated` 改成小數字另存一份，
在同一顆 profile 上開。開得起來就把假說變成量測；仍然逾時就排除它，往
`database-range`／`named-range`／chart 逐一切。

## 對里程碑的意涵

不擋今天的任何事——ODS 讀取是未來的里程碑，而它的閘門判準（`handoff/
PLAN-2026-09-03-ods-reading.md` 的 G2）已經替這種情況寫好位置：一筆 entry 可以宣告
`expect: "refused"`，但**這一筆不是拒絕、是掛住**，而 G2 要求的是「型別化的拒絕」。
所以在根因查清之前，這個檔案會讓 G2 紅——**那是判準在做它該做的事**。

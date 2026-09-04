# 089 — 一份 13 KB 的試算表在 wasm 上逾時 180 秒，原生 269 毫秒開完

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | **未確認**——可能是上游，也可能是我方的 wasm 組態；沒查到根因前不要送 |
| **發現日** | 2026-09-05 |
| **嚴重度** | 嚴重（該檔完全開不起來） |
| **可重現** | **2/2**（另有兩個變體測試，見「分析」） |
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

### 假說一：**已否證**（2026-09-05）

做了那個單一變因的測試——只把 `number-rows-repeated` 與
`number-columns-repeated` 的上限壓到 64，**其餘每一個位元組原樣搬過去**，所以行為若有
差異，歸因不到別的東西上。

```
tdf149752-rows-capped.ods   opened=False  err=TIMEOUT  elapsed=180,994 ms
d1-anchors.odt（對照組）     opened=True   parts=1      elapsed=1,837 ms
```

**仍然逾時。`number-rows-repeated` 不是成因。**

這正是把它標成假說而不是寫成事實的理由：它是那份檔案裡唯一顯眼的差異，而「唯一顯眼」
不等於「就是它」。若當時寫進上游報告，會浪費 triager 的時間去追一個已經被否證的方向。

證據：`evidence/089/hypothesis-1-repeat-counts-REFUTED.json`

### 下一步

剩下的候選：`table:database-range` ×4、`table:named-range` ×3、chart ×1、
`office:forms` ×2。作法是**先一次全部拿掉**——開得起來就二分，仍然逾時就表示成因不在
`content.xml` 的這些特徵裡，要往 `styles.xml`／`settings.xml` 或那 129 列的內容本身找。

## 對里程碑的意涵

不擋今天的任何事——ODS 讀取是未來的里程碑，而它的閘門判準（`handoff/
PLAN-2026-09-03-ods-reading.md` 的 G2）已經替這種情況寫好位置：一筆 entry 可以宣告
`expect: "refused"`，但**這一筆不是拒絕、是掛住**，而 G2 要求的是「型別化的拒絕」。
所以在根因查清之前，這個檔案會讓 G2 紅——**那是判準在做它該做的事**。

## Bisected, 2026-09-05 — and the bisect's own premise was wrong

Nine probe runs on `e2-editor-v12`, each a single-variable strip of the original
(`tools/probe_ods_on_profile.py --profile e2-editor-v12 --timeout 300`). The
last five carried an ODT control, which opened in every one of them.

| variant | opened | elapsed |
| --- | --- | --- |
| original (`tdf149752.ods`) | no | TIMEOUT 181,026 ms |
| row `number-rows-repeated` capped | no | TIMEOUT 180,994 ms |
| chart removed | no | TIMEOUT 181,561 ms |
| `office:forms` removed | no | TIMEOUT 181,129 ms |
| `table:database-ranges` removed | no | TIMEOUT 181,181 ms |
| **`table:named-expressions` removed** | **yes** | **1,622 ms** |
| all four removed | yes | 1,418 ms |
| the three named ranges restored onto the stripped file | no | TIMEOUT 180,975 ms |
| only `Farben` restored | yes | 1,501 ms |
| only `Index` restored | yes | 1,461 ms |
| only `Index2` restored | yes | 1,478 ms |

The block is **433 bytes**. Removing it turns a 180-second hang into a 1.6-second
open, and putting it back onto the stripped file brings the hang back — so the
strip and the restore agree, in both directions, on a file that is otherwise
byte-identical.

### The reading that a bisect alone would have got wrong

"Three named ranges are individually harmless and jointly fatal" is what the
table says and is not what is happening. The document holds **99 cells** each
carrying

    of:=IF(COUNTIF(Index2;Index);"";Index)

with `Index` = `$Liste.$A$2:.$A$100` and `Index2` = `$Auswertung.$A$2:.$A$100`,
99 cells each. `COUNTIF` with a **range as its criterion** evaluates as an
array: 99 criteria against 99 cells, in each of 99 cells. Remove either name and
the formula cannot resolve it, so **the expensive evaluation never runs** —
the variant opens quickly because the work was disabled, not because the removed
name was innocent. `Farben` is referenced once, in a string, and is a passenger.

So the single-variable strips were not single-variable with respect to the thing
that costs: they were switching the computation on and off. The named ranges are
the switch. **The cost is formula evaluation at load.**

None of those 99 cells carries a cached result — they hold `<text:p/>` and no
`office:value`, and the document has no `table:calculation-settings` — so Calc
has nothing to trust and must compute. Native does the same work in **269 ms**
for the whole open. The gap is not "WASM is slower"; ~180 s against ~0.27 s is
three orders of magnitude, and a document with a second array-formula family
(99 cells of `SMALL([.$A$2:.$A$100];ROW())`, direct addresses, no names
involved) evaluates that family fine in every variant that opens.

### What is measured and what is not

* **Measured**: the trigger, in both directions, with a control; that the
  trigger is a formula-evaluation switch rather than a parse cost; that a second
  array-formula family in the same document is cheap.
* **Not measured**: where the time goes inside the evaluation, and whether the
  gap is a general Calc-on-WASM formula cliff or specific to `COUNTIF` with a
  range criterion. Two fixtures are built and unrun
  (`tdf149752-rows20.ods`, `tdf149752-rows50.ods`: the two named ranges
  shortened to A2:A20 and A2:A50, nothing else touched), which is the scaling
  measurement that would tell those apart. Do not attribute a cause before it
  runs — finding 040's precedent.
* **Not measured**: whether the SDK forces a hard recalculation on load that
  the native path skips. That is the product-side question, and it is the one
  worth answering first, because it is the only candidate here that is ours to
  fix.

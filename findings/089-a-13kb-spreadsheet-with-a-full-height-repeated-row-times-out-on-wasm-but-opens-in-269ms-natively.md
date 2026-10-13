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

## The product-side question is answered, and the answer is no (2026-09-06)

The section above named one candidate as "the one worth answering first, because
it is the only candidate here that is ours to fix": whether the SDK forces a
hard recalculation on load that the native path skips. It does not. Evidence:
`findings/evidence/089/recalc-on-load-2026-09-06.txt`.

`ScDocShell::LoadXML` (`sc/source/ui/docshell/docsh.cxx`) computes one boolean,
`bHardRecalc`, and calls `DoHardRecalc()` only if it is true. It is false here,
at four independent points, any one of which is sufficient:

* `officecfg::Office::Calc::Formula::Load::ODFRecalcMode` defaults to **1 =
  `RECALC_NEVER`**, and the code takes `DoHardRecalc()` only for `RECALC_ALWAYS`
  (0) or for an affirmative answer under `RECALC_ASK` (2).
* That default is **1 in the shipped package too**, not only in the source
  tree — read out of `base-e2-editor-v12.9901e9be29c9ded2.data` directly rather
  than inferred from the tree that built it.
* No override ships with the profile: no `registrymodifications` in the package
  metadata, and no loose `.xcu` under `dist/`.
* `desktop/source/lib/init.cxx` names none of `RecalcMode`, `DoHardRecalc` or
  `IsUserInteractionEnabled` — LOK sets no recalc mode of its own.

Even had the mode been `RECALC_ASK`, the branch tests the generator against the
product name, and every fixture here reports
`LibreOffice/6.0.2.1$Linux_X86_64` — the branch is written for documents some
other producer wrote.

**The default is shared, so native takes the same branch.** This is not a
difference between the two platforms that was found and then measured to be
small; it is a difference that does not exist.

### What this does not say

It does not say no computation happens at load. The `else` branch still
broadcasts `ScHint(SfxHintId::ScDataChanged, BCA_BRDCST_ALWAYS)`, and the 99
cells carry no cached result, so both platforms must interpret them. One
candidate for the ~670x gap is removed; the cause is still unnamed, and the
scaling fixtures (`tdf149752-rows20.ods`, `tdf149752-rows50.ods`) are still
built and unrun.

## The scaling fixtures ran, and it is a cliff, not a curve (2026-09-06)

Evidence: `findings/evidence/089/ladder-2026-09-06.txt` and the four probe
reports beside it. Profile `e2-editor-v12`; every run carried the ODT control,
and the control opened in every one.

| `Index`/`Index2` range | opened | elapsed |
| --- | --- | --- |
| `A2:A20` | yes | 1,423 ms |
| `A2:A25` | yes | 1,459 ms |
| `A2:A30` | yes | 1,208 ms |
| `A2:A34` | yes | 1,501 ms |
| `A2:A35` | yes | 1,245 ms |
| **`A2:A36`** | **no** | **TIMEOUT 180,919 / 180,991 ms** |
| `A2:A40` | no | TIMEOUT 180,953 ms |
| `A2:A50` | no | TIMEOUT 180,930 ms |
| `A2:A100` (the original) | no | TIMEOUT 181,026 ms |

**One row moves it from 1.2 s to more than 180 s.** That is the measurement the
earlier section said would tell a general formula cliff apart from a scaling
cost, and it answers against scaling: no polynomial does this. `36³/35³` is
1.09; the observed ratio is at least 145. Something switches between a range of
34 rows and a range of 35.

`rows36` timed out in two independent invocations, and in the second one
`rows34` and `rows35` opened normally in the same browser session immediately
before it, so this is not one bad run or a poisoned session.

### One candidate mechanism excluded, cheaply

`ScQueryCellIteratorSortedCache` — the sorted-range cache COUNTIF would switch
into for a large enough range — is **compiled out entirely** in this tree.
`CanBeUsedForSorterCache` (`sc/source/core/data/queryiter.cxx:1598`) begins with
`#if 1 / return false`, with a comment naming tdf#151958 and disabling it for
releases. The whole eligibility test below it, thresholds included, is
unreachable. Whatever switches at 36 rows, it is not that.

### What is measured, and what is still not

* **Measured**: that the cost is a threshold in the named range's length, at
  35→36 rows, reproduced twice, with a control in-band.
* **Not measured**: whether `rows36` finishes *eventually*. The 180 s is the
  SDK's own `open` timeout, hard-coded at
  `web/ods-decisive-probe-app.js:165`, not the probe's `--timeout`; a run that
  hits it has not been shown to be non-terminating. Raising it needs an
  instrument change and has not been made.
* **Not measured**: the same ladder natively. The native oracle opened the
  unmodified original in 269 ms, so the threshold may exist on both sides at
  different constants, or on one side only. **Nothing here licenses saying it is
  WASM-specific**, and the earlier "~670x gap" framing should be read as an
  observation about the original file, not as a rate.
* **Not measured**: `rows37`, `rows38`, `rows39` — built, and unrun because the
  first timeout consumed the run's budget.
* **The fixtures now have provenance.** They were built ad hoc in a scratchpad
  that no longer exists. `findings/evidence/089/build_row_ladder.py` rebuilds
  them, and `--verify` re-derives `rows20` and `rows50` and compares:
  `content.xml` is byte-identical for both (the whole zip is not, because zip
  metadata is not reproduced). It also asserts the shrink hits exactly the 2
  sites inside `<table:named-expressions>` and leaves the 99
  `SMALL([.$A$2:.$A$100];ROW())` references alone — a blanket replace on this
  document hits 200 sites, which this tree has already done once.

## The same ladder natively: flat. The cliff is WASM-side (2026-09-06)

Evidence: `findings/evidence/089/native-ladder-2026-09-06.txt` and
`native-ladder-2026-09-06.jsonl`. `ods_native_oracle.cpp` compiled `-O2` and run
on `build-native-26-8/instdir/program`, core commit `671c848b…` — the tree the
candidate is built from. One file per process, each under `timeout 300`, because
the oracle has no timeout of its own and a hang would have taken the batch.

| range | native `loadAndReadMs` | WASM |
| --- | --- | --- |
| `A2:A20` | 1,407 | 1,423 ms |
| `A2:A25` | 1,402 | 1,459 ms |
| `A2:A30` | 1,407 | 1,208 ms |
| `A2:A34` | 1,407 | 1,501 ms |
| `A2:A35` | 1,410 | 1,245 ms |
| **`A2:A36`** | **1,404** | **TIMEOUT ≥180 s** |
| `A2:A37` | 1,405 | unrun |
| `A2:A38` | 1,405 | unrun |
| `A2:A39` | 1,405 | unrun |
| `A2:A40` | 1,402 | TIMEOUT ≥180 s |
| `A2:A50` | 1,417 | TIMEOUT ≥180 s |
| `A2:A100` (original) | 1,400 | TIMEOUT ≥180 s |

**Native is flat: 1,399.59 to 1,416.87 ms, a 17 ms spread over twelve files.**
The same documents, the same core commit, and no threshold anywhere in the
range. **The 35→36 cliff does not exist natively.**

That is the licence the previous section said it did not have. It is now
measured, and this finding may be read as WASM-side.

### The oracle's number covers the evaluation — shown, not assumed

A native load that skipped the formulas would be flat for an uninteresting
reason. It did not skip them: with the named ranges present, the 99
`IF(COUNTIF(Index2;Index);"";Index)` cells read back as the empty string (and
`200` at the one row whose index is not in `Index2`); with the ranges removed,
the same cells read `#NAME?`. The read is sensitive to whether the formulas
evaluated, and on every rung of the ladder they did.

### Correction to an earlier claim in this finding

The section "Bisected, 2026-09-05" says *"None of those 99 cells carries a
cached result — they hold `<text:p/>` and no `office:value`"*. **13 of the 99 do
carry one** (`office:value-type="float" office:value="200"`); the other 86 are
bare `<text:p/>` with no value and no value-type. The claim that Calc has
nothing to trust and must compute holds for 86 of 99, not for all 99. Counted
here rather than eyeballed:
`native-ladder-2026-09-06.txt`, section "Cached results in the source document".

### Still not measured

Whether `rows36` on WASM finishes *eventually*. The 180 s is the SDK's own
`open` timeout hard-coded at `web/ods-decisive-probe-app.js:165`; nothing here
shows the load is non-terminating rather than merely slower than that. Native
takes 1.4 s, so if WASM is on the same algorithm the constant would have to be
worse by more than 128x for the same document — which is itself the observation
that makes "same algorithm, slower machine" hard to believe.

## `rows36` does not open in thirty minutes (2026-09-06)

Evidence: `findings/evidence/089/rows36-open-timeout-1800s.json`. The SDK's
`open` timeout was raised to 1,800,000 ms for this run — see
`findings/evidence/089/openTimeout-knob.md` for the knob and its red case.

| case | opened | elapsed |
| --- | --- | --- |
| `d1-anchors.odt` (control) | yes | 1,874 ms |
| `tdf149752-rows35.ods` (in-band control) | yes | 1,600 ms |
| `tdf149752-rows36.ods` | **no** | **1,800,901 ms — `open timed out after 1800000 ms`** |

`rows35` opened normally in the same session immediately before it, so the
engine was healthy when `rows36` was handed over.

**Against native's 1,404 ms for the same file, that is a factor of at least
1,282, and it had still not finished.** The earlier section said "if WASM is on
the same algorithm the constant would have to be worse by more than 128x — which
is itself the observation that makes 'same algorithm, slower machine' hard to
believe." The factor is now an order of magnitude past that and remains a lower
bound.

### What this still does not establish

**It is not proof of non-termination.** Thirty minutes is a longer bound, not an
unbounded one. What can be said is bounded and worth saying exactly: on this
profile the open does not complete within 1,800 s, while the same document on
the same core commit completes natively in 1.4 s.

Nothing here identifies where the time goes. Two candidates from the source
reading are already excluded — a forced hard recalculation on load (the default
is `RECALC_NEVER` and is shared with native) and the sorted-range cache
(compiled out entirely, tdf#151958) — and neither exclusion points at a
replacement. **Do not attribute a cause on this evidence**; finding 040's
precedent is that a confident wrong attribution here costs more than the
open question.

## Correction: the ladder measured a diagonal, and the frontier has two axes

Evidence: `findings/evidence/089/grid-2026-09-06.txt` and the five `grid-*.json`
reports beside it.

The section "The scaling fixtures ran, and it is a cliff, not a curve" says
*"Something switches between a range of 34 rows and a range of 35."* That
sentence is about **one** range, and the ladder does not measure one range: it
shortens `Index` and `Index2` **together**. Everything it establishes is about
the diagonal of a two-variable space, and I wrote it as though the space had one
axis. The cliff on the diagonal is real and reproduced; the attribution to "a
range" was not measured.

Varying them independently — `build_row_ladder.py --split INDEX INDEX2`, whose
`(35,35)` output is byte-identical in `content.xml` to the ladder's `rows35`:

| `Index` | `Index2` | opened |
| ---: | ---: | --- |
| 100 | 35 | yes, 1,486 ms |
| 36 | 35 | yes, 1,589 ms |
| 35 | 35 | yes, 1,245 ms |
| 20 / 25 / 30 / 33 / 34 | 36 | yes, 1,223–1,496 ms |
| **35** | **36** | **no — timeout, twice** |
| **36** | **36** | **no — timeout, twice** |

**It takes both.** `Index2 ≥ 36` is necessary and not sufficient: at `Index2 =
36` it still opens with `Index` anywhere from 20 to 34. `Index ≥ 35` is
necessary and not sufficient: at `Index2 = 35` it opens with `Index` at 100.

This kills the reading that one range is "the switch" and the other is inert,
which is where a one-axis ladder was pointing. It also rules out a simple size
product: `(35,36)` and `(36,35)` differ by one cell in each direction and by one
in the product, and one of them takes 1.6 s while the other does not finish.

`Index` is `$Liste.$A$2:.$A$n` — plain data on another sheet, the COUNTIF
criterion. `Index2` is `$Auswertung.$A$2:.$A$n` — the same column as the 99
`IF(COUNTIF(Index2;Index);"";Index)` cells that resolve through it, so the
search range overlaps the cells being computed. **Naming that as the mechanism
would be exactly the attribution this finding has twice refused to make**; it is
recorded as the structural difference between the two axes, not as a cause.

### What the earlier sections still say correctly

The diagonal cliff (rows35 opens, rows36 does not), the native ladder being flat
across the whole diagonal, and `rows36` not opening in 1,800 s are unaffected —
those are all measurements of specific files, and every one of those files still
behaves as recorded.

## 卡住時是在算還是在等：協定跑完，答案是「在等」；且發現一個計時落差（2026-09-07）

證據：`findings/evidence/089/cpu-or-wait-2026-09-07/`（`RESULT.md`、
`WAIT-SHAPE.md`、`TIMING-RECONCILIATION.md`）。本節只摘要，不重複判準；三份
檔案本身才是紀錄，且都只記資料，不點成因——`futex_do_wait` 是一個量測，不是
解釋，這條戒律延續自本 finding 先前兩次撤回歸因。

**第一階段結論（同日稍早跑完，不是本節新做的）**：兩輪獨立量測都判為
**Waiting**——`rows36` 卡住的 160.5 秒視窗裡，開出那份檔案的整個瀏覽器
process tree 沒有任何一條執行緒累積得到有意義的 CPU；同一批 tid 在自己開機
的 10 秒視窗裡確實有在算（0.98–1.02 秒 CPU），拿這個做同執行緒的正對照，排除
「探針根本沒接上」。細節與判準見 `RESULT.md`，本節不重複。

**Wait shape（本節新做，純分析，沒有再開瀏覽器）**：從已存的兩輪樣本重新
攤開逐執行緒資料，把「開機時在做事」跟「卡住時不做事」擺在同一張表對照。
關鍵幾點，都是數字：

* GEN(5) 的兩條 `DedicatedWorker` tid 在 `B(5)`（開機）視窗有量到 CPU（rate
  0.017–0.093 cores，其中一條還量到過一次 `R` 狀態），到了 `H`（卡住）視窗
  同一條 tid 掉到 0.00006–0.00069 cores，狀態 100% 是 `S`——兩輪一致。
* 不只是 GEN(5) 那幾條停了：把整棵 process tree 攤開（153–159 條執行緒、
  13–14 個 process，涵蓋 browser、每個 renderer、gpu-process、每個 utility、
  每個 zygote），`H` 整整 160.5 秒裡全樹合計耗用的 CPU 大約是**一顆核心的
  1%**；全樹裡曾經出現過 `R` 狀態的樣本，兩輪各只有 3–4 筆（出自 42,000 多筆
  樣本），而且都不是 GEN(5) 的執行緒，是 browser process 自己的housekeeping
  執行緒——這正是協定本身事先寫好、預期會有 CDP 輪詢器落地的地方，不是引擎
  的執行緒。全樹沒有任何執行緒出現過 `D` 狀態。
* Context-switch 的差異值得記一筆：GEN(5) 裡有一條 `DedicatedWorker` tid
  在整段 `H` 期間累積約 1600 次 voluntary context switch（等於平均每 100
  毫秒被喚醒一次），是全樹倒數第二高的喚醒次數，但同一條 tid 做的 CPU 工作量
  仍然趨近於零；GEN(5) 其餘每一條 tid 在同一段 160.5 秒裡只有 0–42 次
  voluntary switch。兩輪的數字幾乎完全一樣（1601 / 1600）。這只記成「有一條
  執行緒被反覆叫醒又睡回去，跟從來沒被叫醒不是同一張圖」，不猜為什麼。

**計時落差的預先登記與量測**：phase 1 兩輪都量到 `tdf161948_NaturalSort
SaveLoad.ods`（case 4，本協定拿來當「重但有限」的正對照）開檔只花
1.05–1.09 秒，但這份檔案先前在 2026-09-06 的 306 檔案掃描裡被記為
**30,688 毫秒**（`findings/evidence/m4-ods/04-sweep-v12.json:33191`）——同一台
機器、相差一天，落差約 27–29 倍。而 2026-09-06 這台機器**已知**同時扛著一個
孤兒的 headless Chrome（`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`
記錄從 20:21 起跑了約四小時）和 owner 自己的瀏覽器。**這只是一個待驗的假說，
不是結論**，所以在動手量之前，先把「量什麼、量幾次、每種結果各代表什麼」寫進
`TIMING-RECONCILIATION.md`，再去量。

量測本身：21:01–21:14 CST，三次獨立重跑（每次跑之前都查過機器閒置），针对
四個定點——`rows35`（開得動的近鄰）、`index36/index2-35`（開得動的另一個
近鄰）、`tdf161948`（落差本身）、`rows36`（預期開不動，180 秒封頂，不重跑
1,800 秒）：

| 檔案 | banked 數字 | 今天三次 | 比值 |
| --- | ---: | --- | ---: |
| `rows35` | 1,245 ms | 1,422 / 1,372 / 1,353 ms | 今天慢約 10% |
| `index36/index2-35` | 1,589 ms | 1,172 / 1,136 / 1,162 ms | 今天快約 27% |
| `tdf161948` | **30,688 ms** | **1,397 / 1,053 / 1,014 ms** | **今天快約 26.6 倍** |
| `rows36` | TIMEOUT（180,919 / 180,991 ms） | TIMEOUT，三次都在 180,835–180,854 ms | 一致 |

`rows35`、`index36/index2-35` 兩個短開檔案，今天的數字落在跟 banked 數字同一
個量級（跟 banked 資料自己兩次量到 `rows35` 也有 1,245 對 1,260 的差距是
同一種散布），但 `tdf161948` 這個原本卡在半分鐘的正對照，今天三次都落在
1.0–1.4 秒，跟 phase 1 同一天稍早量到的 1.05–1.09 秒幾乎疊在一起——也就是說
2026-09-07 這一整天（兩個獨立 session、五次量測）都量到快的數字，只有
2026-09-06 那一次（機器已知有其他負載）量到 30,688 毫秒。

**這licence 的是預先寫好的（ii）那一句，不是自己另外編的**：banked 的階梯是
在一個「現在說得出名字」的狀態下量到的（2026-09-06 那天機器有其他負載），
在對 `Index`/`Index2` 再說任何一句話之前，前緣（`Index ≥ 35` 且
`Index2 ≥ 36`）本身需要重新量過——這句話講完就停，**沒有在本節裡重量整個
grid**，那是另一件要另外編預算、另外預先登記的工作。同時也如實記下一個
預先登記時沒想到的不對稱：只有 `tdf161948` 這個 30 秒級的正對照量到數量級
落差，兩個秒級開檔沒有；這只記成「哪些檔案的數字動了、哪些沒動」，不解釋
為什麼。

---

## 檔案歸位：2026-09-07 的裁定原本落在一個錯名的檔案裡

`c2e64475` 把「主 session 的裁定」寫進了新開的
`089-a-13kb-spreadsheet-with-a-full-height-repeated-row-times-out-in-wasm.md`
——一個沒有標題、沒有前後文的檔案——而 089 的正本一直是這一份。兩個同號的
檔案並存，下一個人只會讀到其中一份，而且會讀到哪一份取決於他怎麼 glob。原文
一字不動搬到下面，錯名的那份刪除。**這是命名的更正，不是量測的改寫。**


### 主 session 的裁定：(ii) 成立且不移動，但今天已經還掉它的一部分（2026-09-07）

（append-only。上面兩節的判定與數字不改。）

**(ii) 照它自己寫下的觸發條款成立，維持。**觸發寫的是「`tdf161948` 落在
phase 1 的 ~1.05–1.09 秒而不是 ~30.7 秒，**或**兩個秒級開檔也明顯變快」，
第一個析取項三趟全中。執行者沒有因為只中一半就往 (i) 或 (iii) 靠，這是對的
——判準寫在跑之前，事後覺得不合身不是移動它的理由。

**它課的義務也維持：在重新量過之前，不得再複述 `Index ≥ 35` 且
`Index2 ≥ 36` 這個說法。**但今天的三個 fixture 已經把這筆義務的**對角線那
一半**還掉了：`rows35` 開得了（1,353–1,422 ms）、`index36/index2-35` 開得了
（1,136–1,172 ms）、`rows36` 三趟三次都逾時（180,835–180,854 ms）。**還欠的
是格線的非對角線部分**，也就是真正撐起「兩軸缺一不可」那句話的那些點
（`Index2 = 36` 而 `Index` 落在 20–34、以及 `Index = 100` 而 `Index2 = 35`）。
那才是下一次要編預算、要先登記的工作。

**這一輪逼出來、而且要帶著走的那個不對稱**：秒級的兩份重現得了，30 秒級的那
一份差 26.6 倍。「09-06 那天機器忙」若是唯一成因，秒級的也該一起膨脹。所以
它現在是**具名的未量測項**，不是已解釋的東西。

**wait shape 那一節裡最尖銳的一個數字**，記下來給下一輪用：掛住的 160.5 秒
裡整棵行程樹（13–14 個行程、153–159 條執行緒）合計只用掉約 1% 的一顆核心，
四萬多個取樣裡只有 3–4 個 `R` 而且全在瀏覽器自己的雜務執行緒上、`D` 是零；
但其中一條 `DedicatedWorker` 執行緒在同一段時間裡自願讓出 **約 1,600 次
（每秒約 10 次）**，兩趟幾乎一模一樣。**有人以固定節奏把它叫醒，而它醒來
沒做事又睡回去。**這是資料，不是成因；089 的兩次拒絕指認仍然有效。

---

## 非對角線量完了：outcome R（2026-09-07 晚）

先登錄的協定：`handoff/tasks/TASK-2026-09-07-089-off-diagonal-regrid.md`。
證據：`findings/evidence/089/off-diagonal-regrid-2026-09-07/`。十個點、每點三趟、
要求一致（2 比 1 算 SPLIT 不算過），判準與門檻全部寫在跑之前。`reduce.py`
是形式二的工具——只讀既有產物、不開瀏覽器、一行可重跑——它給出 **outcome R**，
而三個「測不出來」的觸發（E1／E2／E3）一個都沒點燃。

| 點 | fixture | 今天三趟（ms） | banked | 比 |
| --- | --- | --- | --- | --- |
| A1 | index20 × Index2 36 | 1370 / 1398 / 1118 | 1228 | 1.12 |
| A2 | index25 × Index2 36 | 1141 / 1150 / 1176 | 1484 | 0.77 |
| A3 | index30 × Index2 36 | 1178 / 1108 / 1148 | 1223 | 0.94 |
| A4 | index33 × Index2 36 | 1136 / 1161 / 1120 | 1274 | 0.89 |
| A5 | index34 × Index2 36 | 1127 / 1158 / 1351 | 1496 | 0.77 |
| A6 | index35 × Index2 36 | 三趟全逾時 | 逾時 | — |
| B1 | Index 100 × Index2 35 | 1354 / 1350 / 1142 | 1486 | 0.91 |
| B2 | index36 × Index2 35 | 1154 / 1158 / 1162 | 1589 | 0.73 |
| K1 | rows35 | 1118 / 1143 / 1352 | 1245 | 0.92 |
| K2 | rows36 | 三趟全逾時 | 逾時 | — |

時間比全部落在協定寫死的 [0.5, 2.0] 之內。

**裁定：`Index ≥ 35` 且 `Index2 ≥ 36` 這個說法可以再用了**——但要連著量測日期
與點位清單一起講（2026-09-07、上列十點、每點三趟一致）。它現在的效力來自這
一次量測，不是來自 2026-09-06 那道已知不可靠的階梯。

**綠燈是在一個被證明弄得紅的儀器上拿到的。**執行者的五個紅案全紅，但它誠實
記下 RC-3 照字面做不出來（2026-09-06 的 Row-A 報告單獨一份過不了 §4.5 的
RC-1 閘，示範到的是 void→C）。主 session 補做了字面版：用產生 R 的那六份報告，
把 A3 三趟的 `opened` 全翻掉，outcome 從 R 變成 C 並點名 A3
（`RC-3b-LITERAL-R-TO-C.md`）。紅案跟綠燈用不同輸入，證不到「這個綠可以被弄紅」
——跟 4a 第 6 條那半天是同一個道理。

### 但「開得起來」是代理，原始紀錄說的比它多

十個點的報告裡有**三種**狀態，不是兩種，而且 2026-09-06 的 banked 紀錄同樣帶著：

| 狀態 | 點 | `workerCrashed` |
| --- | --- | --- |
| 乾淨開檔 | A1 index20、A2 index25、A3 index30、A4 index33 | 三趟皆無 |
| 開得起來，但 worker 崩了 | A5 index34、**B1 index100×35**、**B2 index36×35**、K1 rows35 | **三趟皆有** |
| 逾時 | A6 index35×36、K2 rows36 | 三趟皆無 |

崩潰訊息 `Uncaught RuntimeError: memory access out of bounds`，與點位一一對應、
3/3 重現，而 2026-09-06 的 `grid-*.json` 在 `index100-index235`、
`index36-index235`、`index34-index236` 三筆上帶著同一個欄位。

這會回頭咬那句被復原的話：**支撐「`Index ≥ 35` 單獨不夠」的那兩個點（B1、B2）
全部落在中間那一種狀態。**說它們「開得好好的」是拿分類器的輸出當宣稱；它們的
原始紀錄說的是「開得起來，而且 worker 在過程中崩了」。復原的那句話要連這一句
一起講，否則就是再一次拿代理當宣稱。

**NU-089-2 升級**：從「逐 case 記錄」變成「3/3 重現、與點位一一對應」。
**仍然不指認成因**——`workerCrashed` 跟 `futex_do_wait` 一樣是量到的東西，不是
解釋。089 已經拒絕指認兩次。

**NU-089-1 維持未解釋**（為什麼 09-06 到 09-07 之間只有 30 秒級那一份動了）。
今天的 R 對它不是證據：這個 grid 每一點都是秒級，而協定明寫中途不得補一個
30 秒級的 fixture 進來。

**協定自己被逼出兩個文字瑕疵，登錄不修**：§1.2 的「六個欠款點」與 §5.1／§5.3
的 C2 子案（它要求 B1／B2 也在內）不一致，`reduce.py` 採了實質的八點讀法；
以及 RC-3 的字面寫法在 banked 輸入上不可達，已由 RC-3b 補上。兩者都不改變本
輪結果，但都不假裝沒發生。

---

## 判別臂：不是公式群組計算——outcome O-N（2026-10-13，只追加）

先登錄的協定：`handoff/tasks/TASK-2026-10-13f-089-threading-arms.md`（`47440469`，含更正 1）。證據：`findings/evidence/089/threading-arms-2026-10-13/`（`8d26c32f`）。儀器：`probe_ods_on_profile.py --engine-env`（`b028cbc6`），只改 scratch 鏡像裡那份 `probe.js` 的 ENV，引擎從 preRun 把 ENV 印回報告；沒有回聲的 case 一律作廢。

**假說 H-T（讀原始碼，跑之前寫的）**：懸崖是 Calc 的公式群組多執行緒計算在 WASM 上被走進去（群組權重 ≥ 100 才走，`formulacell.cxx:4897`；權重＝雙參照格數／10 × 群組長度）。**被否證。**

| 臂 | 環境變數 | rows36 | index35×36 | rows35 | index36×35 | 對照組 |
|---|---|---|---|---|---|---|
| E0-r2（儀器對照） | `OXSDK_089_ARM=control` | 逾時 | 逾時 | 崩 | 崩 | 全與 banked 同 |
| E1 ×3 | `SC_NO_THREADED_CALCULATION=1` | 逾時 3/3 | 逾時 3/3 | 乾淨 3/3 | 乾淨 3/3 | 乾淨 |
| E2 ×1 | `SC_FORCE_CALCULATION=core`（整個停用群組計算） | 逾時 | 逾時 | 乾淨 | 乾淨 | 乾淨 |
| E3 ×3（60 s 上限） | `SC_FORCE_CALCULATION=threads` | 逾時 3/3 | 逾時 3/3 | 乾淨 3/3 | 乾淨 3/3 | 乾淨（index30×36、rows20 沒有變慢） |

主 session 用自己的讀取器逐份核對十份報告，狀態與回聲（E0-r2 起每份 7/7）都與執行者的表相同。

**儀器先錯了一次，閘門擋下來**：E0-r1 回聲 0/7——探針頁在 `createDocumentEngine()` resolve 之後才掛聽眾，preRun 的回聲發給零個聽眾。是主 session 的設計錯，不是執行者的；修法（初始化之前掛聽眾）與修後 2/2 的儀器檢查在 `88472109`，E0-r1 留著當紅案。

**結論**：逾時**不在** Calc 的公式群組計算——E2 把群組計算整個關掉，rows36 照樣掛 180 秒。H-T 撤回，不留機械去維持它。

**同時量到、沒有解釋的（NU-089-3）**：**逾時與崩潰分開了。** rows35 與 index36×35 的 worker 崩潰（`memory access out of bounds`）在預設路徑上一再出現（banked 3/3、E0-r1、E0-r2），而只要設了任何一個 Calc 計算變數，不論值是什麼，七趟裡 14 次全不崩；`pthread_mutex_unlock failed: EPERM` 也是同一個分布。讀原始碼的一個線索（**未量**）：E1、E2、E3 三者都繞過 `ScCalcConfig::isThreadingEnabled()` 裡建立設定監聽器（`ConfigurationListenerProperty`，`calcconfig.cxx:87`）的那一步——E1 因為 `formulacell.cxx:5096` 的條件先短路，E2／E3 因為 `SC_FORCE_CALCULATION` 讓它提早 return；預設路徑才會建立它。這是一條可否證的線索，不是成因；本 finding 不指認成因的戒律照舊。

**還沒做、可以不連結就做的**（下一輪要先登錄）：其他能用環境變數關掉的執行緒使用者——`SAX_DISABLE_THREADS`（`sax/source/fastparser/fastparser.cxx:834`，content.xml 超過 10,000 位元組就開解析執行緒）、`MAX_CONCURRENCY=1`（`comphelper::ThreadPool` 的上限）。若這兩個也不翻，要知道「卡住時在等誰」就需要堆疊，而 v12／v14 的 `probe.wasm` 沒有 name section（主 session 2026-10-13 讀過：零個 custom section），要嘛用 CDP 對卡住的 worker 下 `Debugger.pause` 讀 JS 層的框架，要嘛請擁有者連結一份 `--profiling-funcs` 的診斷版（finding 037 有前例）。

### 更正 2 的兩臂：O-N2（2026-10-13，只追加）

協定：`TASK-2026-10-13f` 更正 2（`53044890`，跑之前寫）。證據同一目錄（`831fea32`）。主 session 逐份核對。

| 臂 | 環境變數 | rows36 | index35×36 | rows35 | index36×35 |
|---|---|---|---|---|---|
| E4 ×1 | `SAX_DISABLE_THREADS=1`（關掉 FastSaxParser 的解析執行緒） | 逾時 | 逾時 | 崩 | 崩 |
| E5 ×1 | `MAX_CONCURRENCY=1`（回聲確認 LO 自己的 4 被換成 1） | 逾時 | 逾時 | 崩 | 崩 |

兩臂第一趟都沒翻，照規則不補跑。**ODS 匯入路徑上能用環境變數關掉的四個執行緒使用者（群組多執行緒、群組計算、SAX 解析執行緒、ThreadPool 上限）都不是懸崖的開關。**

NU-089-3 多了兩個點：E4、E5 都**走預設的計算路徑**，兩者都照樣崩（各 2 次 `memory access out of bounds`）——崩潰跟著「有沒有設 Calc 計算變數」走，不跟 SAX 執行緒或 ThreadPool 上限走。`MAX_CONCURRENCY=1` 也崩，所以崩潰不是 ThreadPool 併發度的問題。

照更正 2：**不再猜環境變數**，下一步是卡住時的堆疊。v12 的 `probe.wasm` 沒有 name section，finding 037 的前例（`probe_wait_primitive_names.py` 的 docstring）已經說明：不重新連結只拿得到 `$funcN`，要命名得請擁有者連結一份 `--profiling-funcs` 版。走哪一條交 fable 代擁有者裁決（擁有者 2026-10-13 授權）。

### 裁決：先跑 pthread 堆疊臂（fable 代擁有者，2026-10-13，只追加）

擁有者原話：「有疑義的發給fable，我授權它代我下決定」；並提示「需要靈感的話可以參考 collabora source code」。工單 `findings/evidence/089/ruling/brief-1-next-step.md`（含之後補送的 F9–F11），裁決 `ruling-1.md`（`c6e10b21`，條件 1–14 以那份為準）。

**新假說 H-S（從 Collabora 原始碼來）**：Collabora 的 LibreOffice 在 WASM 上用 `-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536`（`cool-26-04/engine/solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk:25`），我們十條連結規則都一樣；我們的引擎在 `std::thread(engineLoop)`（`probe_engine.cpp:6518`）上跑 LOK，LibreOffice 在 Emscripten 上建執行緒也不設堆疊大小（`sal/osl/unx/thread.cxx:258–288`），所以都是 64 KB；這顆 build 沒有溢位檢查。預設值以字面量傳給 `__emscripten_thread_init(…,65536,false)`，所以可以只改鏡像那份 `probe.js`、不連結（`90fed9b7`，每條 pthread 回報自己實際拿到的大小）。

**白話理由（fable 原文）**：

> 這一張單子查了四十天，到今天為止能用環境變數關掉的四種執行緒都證明不是開關，剩下的路本來只有「請你再連結一份帶函式名的診斷版」或「不連結、只看得到編號的堆疊」。但你指到的 Collabora 原始碼點出一個更便宜、也更有力的假說：我們的引擎跑在一條 pthread 上，而每條 pthread 的堆疊只有 64 KB（原生是 8 MB），而且這顆 build 沒有堆疊溢位檢查——溢位會悄悄踩壞旁邊的記憶體，這跟「原生 1.4 秒、WASM 永遠不回來、旁邊幾個尺寸的 worker 死於 memory access out of bounds」的形狀吻合。這個數字是以字面量塞在 probe.js 裡的，所以不用連結、不動產品檔，只改 scratch 鏡像那一份就能把它調大調小，而且每條執行緒會回報自己實際拿到多少，工具已經寫好、等值檢查也過了。所以我的裁決是：先跑這一臂（兩個方向、加上一道尺寸階梯），它若成立，089 的開關就找到了，不需要你連結任何東西；它若不成立，才去跑那支只看編號的暫停探針；只有連那個都說不清，才在你下一次本來就要連結的場次順便加一份帶名字的診斷版。NU-089-3 那個崩潰暫時只登錄不另開臂，因為它只出現在我們自己切出來的 fixture 上，不擋 G2，而且這一臂的預測本來就包含「崩潰會不會消失」。

**裁決順帶更正主 session 的三件事**（主 session 都重新核對過）：

- **「`probe.js` 裡唯一的 65536」是錯的**：實際出現 6 次（`grep -o … | wc -l`）。主 session 用 `grep -c` 數的是行數，`probe.js` 幾乎只有一行。補丁之所以安全，是因為工具要求錨點 `,!ENVIRONMENT_IS_WEB,65536,false);` 恰好出現一次，而不是因為 65536 只有一個。錨點重複時會拒絕，已經用紅案示範過（`stack-arms-2026-10-13/redcase-anchor-count.txt`）。
- **NU-089-3 的「設定監聽器」讀法在 E1 上不成立**：`ScTokenArray::ResetVectorState()` 無條件呼叫 `isThreadingEnabled()`（`token.cxx:1741–1744`），所以 E1 一樣會建立監聽器，只有 E2 和 E3 跳過。共同因素不是它。NU-089-3 維持「量到、沒有解釋」，監聽器的讀法不得當成成因引用。
- **「原生 269 ms」是原檔在 m4 oracle 裡的數字**；原生 rows 階梯量到原檔 1,399.59 ms、rows36 1,404 ms。說到這幾個卡住的 fixture 時，要引約 1.4 秒。

**順序**：
1. 先跑 S（堆疊臂，協定是 `TASK-2026-10-13f` 更正 3，`4fc2673b`）。
2. 只有在 O-S-N 或 O-S-partial 時，才跑 A（只看編號的暫停探針，另立協定）。
3. 只有在 A 得到 O-A-WASM 時，才在擁有者下一次本來就要連結的場次，順便加一份帶名稱的診斷版。
4. 規格審核期間不提這件事。

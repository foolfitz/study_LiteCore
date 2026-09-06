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

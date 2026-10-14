| Question | Verdict | One-line reason |
|---|---|---|
| 1 — page number | COUNTEREXAMPLE | P2 accepts missing `parts`; P3 accepts temporal proximity as causation. |
| 1 — C / `caretBefore` | COUNTEREXAMPLE | C1 accepts missing evidence; E2 can select a post-request caret. |
| 2 | COUNTEREXAMPLE | Row rounding and a discarded counter baseline can reject correct behavior. |
| 3 | COUNTEREXAMPLE | Empty clauses and contradictory non-vacuity fields can produce PASS. |
| 4 | COUNTEREXAMPLE | Python does not implement the page helper’s malformed-entry handling. |
| 5 | COUNTEREXAMPLE | The time window merges separate flushes, including the cited click counterexample. |
| 6 | COUNTEREXAMPLE | Later PASS reports overwrite earlier failures; `counted` violations do not affect exit. |
| 7 | SHOULD | Several predicates lack red cases; most clause cases mutate their verdict alongside their evidence. |

## 1. Broken products that pass — COUNTEREXAMPLE

**P1-60 / P1-mixed: no defect found** in the comparison of populated, consistent position records. Report completeness is addressed under question 3.

**P2 — missing `parts` is accepted.** [`judge_v20_shakedown.py:78`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:78) explicitly permits `partsAt2s: null`, although ARMS requires count = parts = expected M.

Concrete passing fields:

```json
{
  "add": {
    "presses": 16,
    "hiddenAt2s": false,
    "textAt2s": "第 60 頁，共 61 頁",
    "expectedM": 61,
    "countAt2s": 61,
    "partsAt2s": null
  },
  "remove": {
    "presses": 16,
    "hiddenAt2s": false,
    "textAt2s": "第 60 頁，共 60 頁",
    "expectedM": 60,
    "countAt2s": 60,
    "partsAt2s": null
  }
}
```

This returns PASS without establishing the required engine `parts` values. Changing both committed Chrome `partsAt2s` fields to null also returned PASS.

There is an additional loss of evidence in [`run_v20_shakedown.py:695`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:695): if no reply arrives during the final wait, `countAt2s` uses the previously observed engine reply count, but `partsAt2s` substitutes that **count**, not the reply’s `parts`. The removal path repeats this at line 714. Thus `partsAt2s` can assert an equality that was never measured.

The count itself comes from observed engine replies, not page text. A page that reads rectangles only once would ordinarily fail P2 when its engine-reply count remains 60 after addition.

**P3 — proximity does not establish the request’s cause.** [`run_v20_shakedown.py:768`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:768) exempts every request within two seconds after any qualifying trigger, without attributing that request to the trigger.

Concrete input: a genuine `paint.documentSizeChanged` response at `t=1000`, followed by an independently scroll-induced `pageRectangles` request at `t=1500`. With paint activity and bottom reached, the report becomes:

```json
{
  "nonVacuous": true,
  "paintsInWindow": 1,
  "reachedBottom": true,
  "pageRectanglesRequestsInWindow": 1,
  "triggersInWindow": 1,
  "untriggeredRequests": 0
}
```

The judge returns PASS despite the forbidden scroll-induced request. This follows the literal ARMS time-window predicate; it cannot support the stronger causal claim “scrolling calls no engine.”

Likewise, a page that retains the paint trigger but additionally rereads on `documentChangeSequence` can pass these arms: P2 observes its successful page-count changes, while P3 performs no edit that would distinguish the extra trigger.

**C1 — absent evidence becomes successful evidence.** In [`run_v20_shakedown.py:830`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:830), absent `rev` and `beforeRev` compare equal. At line 834, missing rectangle count becomes zero through `(sel.get("n") or 0)`.

Concrete engine/observer inputs:

```json
{
  "answer": {
    "ok": true,
    "completion": "verified-boundary-noop",
    "changed": false,
    "boundaryNoop": {"waitedMs": 2251}
  },
  "engineRead": {
    "answered": true,
    "ok": true,
    "result": {"sel": {"collapsed": true, "n": null}}
  }
}
```

With the remaining normal fields, the runner produces `revisionUnchanged: true` and `noSelectionAt500ms: true`. Applying these missing values to the six committed Chrome rounds returned PASS. Revision preservation and an empty selection rectangle array have not been established.

A new key-specific toast such as `"unexpected error"` also passes: [`run_v20_shakedown.py:835`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:835) checks only the two reopen strings, whereas ARMS says “no toast.”

**E2 — the reference can be the caret after the request.** [`run_v20_shakedown.py:111`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:111) rounds timestamps to 0.1 ms. [`reference_caret`, line 878](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:878) accepts `t <= request.t`, ignoring the observer’s exact ordering field `s`.

Concrete ordered trace:

```text
s=0  ev  g=1  t=100.0  caret=A  seq=10
s=1  rq  g=1  t=101.0  rq=5
s=2  ev  g=1  t=101.0  caret=B  seq=11
```

Let `A={x:2684,y:7266,width:0,height:276}` and `B` differ only in `x:3000`. A defective refusal containing `caretBefore.rect=B, sourceSequence=11` receives all four true clauses and PASS. The true pre-request caret was A. This directly permits “the caret now” to pass as “the caret before.”

## 2. Correct behavior that fails — COUNTEREXAMPLE

**P1 — outward row rounding changes the page span.** The page floors the top row and ceils the bottom row in [`e2-editor-app.js:1278`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/web/e2-editor-app.js:1278). The runner uses the continuous region in [`run_v20_shakedown.py:454`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:454).

Concrete inputs:

```text
rectangles:
  {x:0,y:0,  width:100,height:500}
  {x:0,y:500,width:100,height:505}

document: width=100, height=1005
geometry: paperTop=0, paperBottom=100.5, paperHeight=100.5
          deskTop=50, deskBottom=60
docRows=101
```

The runner’s region is `y=500, height=100`, yielding `第 2 頁，共 2 頁`. The page’s specified conversion yields `y≈497.5248, height≈109.4554`, correctly producing `第 1–2 頁，共 2 頁`. With `hidden:false`, P1 returns FAIL.

Fractional height does not introduce an independent scale discrepancy: `docRows` cancels before rounding. The defect is that the runner omits the outward rounding, which matters at an exact edge.

Strict `<` itself: **no defect found**. Both page and runner use it.

**P3 — the first legitimate counter trigger is discarded.** [`run_v20_shakedown.py:739`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:739) drains the pre-window state; line 762 then starts `last_dsc=None`.

Concrete input: the discarded state had `dsc=0`; the window contains:

```text
t=1001  editor-state dsc=1
t=1002  pageRectangles request caused by that increment
t=1010  paint response changed=true
```

The first state does not register as an increment. The paint trigger occurs after the request. Consequently, `untriggeredRequests=1`, and the otherwise non-vacuous arm returns FAIL for a legitimate size-triggered reread.

**E2 — the same timestamp alias rejects correct data.** For the ordered trace in question 1, a correct refusal containing `rect=A, sourceSequence=10` returns FAIL because the runner selects B as its reference.

**C1 generation / E2 P sequence: no defect found against the literal ARMS predicates.** `generationStays1` intentionally requires generation 1, including the pre-key generation. A fixture-open reopen can therefore invalidate an otherwise correct key instance, but that is consistent with the written condition. Likewise, E2 explicitly requires sequence ≤ the reference. The current engine emits the barrier-start cache sequence even when using P’s rectangle; [`probe_engine.cpp:3380`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/src/probe_engine.cpp:3380) states that P has no recorded sequence.

## 3. Non-vacuity — COUNTEREXAMPLE

The documented empty cases return NOT_ESTABLISHED. The judge does not independently enforce several premises.

- **P3:** preserve `nonVacuous:true`, but set either `paintsInWindow:0` or `reachedBottom:false`. Both variants of the committed Chrome report return PASS. [`judge_v20_shakedown.py:86`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:86) trusts the summary flag.
- **C1:** six records with `clauses:{}` return PASS, including records marked `placement-mismatch` with no answer or engine read. “Judged” means merely that the key exists; the empty clause loop succeeds. See [`judge_v20_shakedown.py:105`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:105).
- **E2:** `cases:[{case:"C17",outcome:"verified-key-undo",judge:{clauses:{}}}], hold:null, refusalsObserved:0` returns PASS without any refusal. See [`judge_v20_shakedown.py:131`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:131).
- **P1:** retaining only the first committed position returns PASS. The judge does not reconcile positions with the rectangle-generated enumeration. This is incomplete coverage, rather than complete vacuity. See [`judge_v20_shakedown.py:40`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:40).
- **P2:** setting `remove.presses=0` while retaining successful measurement fields returns PASS. Only addition presses are checked at [`judge_v20_shakedown.py:62`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:62).

These are report-validation counterexamples; they do not establish that the current runner normally emits those contradictory records.

## 4. Independent implementations — COUNTEREXAMPLE

**Malformed entries differ.** For:

```text
rectangles=[null,{x:0,y:0,width:100,height:500}]
region={x:0,y:1,width:100,height:1}
```

The page returns `{first:2,last:2,count:2}`. Python `span_of` raises `TypeError`. The page skips malformed entries while retaining their indices and contribution to M; Python directly subscripts every entry. Compare [`narrow-editor-v2-session.js:225`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js:225) with [`run_v20_shakedown.py:435`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:435). Python also lacks the page’s malformed-region guards.

For valid finite rectangles, whole-rectangle intersection, strict overlap on both axes, string order, and formatting agree: **no defect found**.

Neither helper exactly reproduces native Writer’s margin treatment. Writer trims the first page’s bottom margin and the last page’s top margin in [`viewsh.cxx:2964`](/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/sw/source/core/view/viewsh.cxx:2964). This is the already registered whole-rectangle limit. Native `SwRect` uses inclusive coordinates whose right/bottom are origin + size − 1, so its `<=` overlap is not evidence that the half-open helpers should use `<=`; see [`swrect.hxx:68`](/home/jiajun/LibreOffice/study_LiteCore/libreoffice-26-8/sw/inc/swrect.hxx:68).

For a valid visible intersection, `region_of` measures the same quantity **before row rounding**. Question 2 supplies the concrete rounding discrepancy.

## 5. Lone-flush detector — COUNTEREXAMPLE

**±25 ms does not identify a flush.** Review 6’s own counterexample has a size-only flush at click +3 ms and the click’s separate caret callback at +25 ms. [`lok_summary`, line 1003](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/run_v20_shakedown.py:1003) combines them:

```text
{k:"mt",type:"lok",id:13,g:1,tw:3}
{k:"mt",type:"lok",id:1, g:1,tw:25}
```

Result: `lone=[]`, `flanked=1`; P2-c reads NOT_ESTABLISHED. Yet the size-only flush already allowed the premature acknowledgment at +5–6 ms described in [`review-6-engine-code.md:113`](/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/link-batch/review/review-6-engine-code.md:113).

Increasing the window to 28 ms would not repair this attribution problem. Conversely, moving the second callback from +25 to +26 ms relative to id 13 changes the reading to lone without establishing a different flush structure.

The detector also ignores generation: id 13 at `g=1,tw=100` is classified as flanked by id 1 at `g=2,tw=103`. Those callbacks cannot belong to one worker flush.

**IDs 8 and 14: no defect found** against the specified “no caret, selection or tiles” definition. `(0,1,2,3,4)` matches that enumeration. Adding STATE_CHANGED or SET_PART as company would change the criterion. The shipped worker does not forward either as `document-invalidated`; see [`sdk-worker.js:1182`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/sdk/sdk-worker.js:1182).

## 6. Exit rule — COUNTEREXAMPLE

**An earlier failure can disappear.** [`judge_v20_shakedown.py:197`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:197) assigns into `verdicts[(browser,arm)]` without rejecting duplicates or preserving failure.

Concrete reproduction: copy the committed Chrome main report, set `results.p3.untriggeredRequests=1`, and pass `[bad_report] + committed_reports` to `judge_reports`. It prints the earlier P3 FAIL but returns exit 0. Reversing the order returns exit 1. Thus directory filename order can determine whether a failed criterion remains visible to the exit rule.

**The `counted` rejection is informational only.** Set `counted:true` on a committed criterion report. [`judge_v20_shakedown.py:184`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:184) prints “a shakedown must say false,” but creates no failure. The complete set still exits 0.

**Missing instrumentation identity fails open.** Remove `identity.instrumentedWorker` from a passing criterion report. It still exits 0 because [`judge_v20_shakedown.py:195`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:195) rejects only literal true. A trace-worker criterion report with that declaration lost is therefore accepted.

Missing browsers and unknown arms: **no defect found**.

## 7. Red-case census — SHOULD

The following census covers every verdict predicate, including the runner clauses consumed by the judge. Mutation definitions are at [`judge_v20_shakedown.py:269`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:269).

| Predicate | Existing red case |
|---|---|
| Any arm’s `runnerError` | None |
| P1 missing reply / zero positions | `p1_no_reply`, changing both together |
| P1 missing expectation | None |
| P1 hidden | `p1_hidden` |
| P1 unequal text | `p1_off_by_one` |
| P1 parts/count summary | `p1_parts` |
| P2 absent add / no add press | `p2_no_press` covers zero presses; absent add has none |
| P2 absent remove | None |
| P2 hidden at +2 s | None |
| P2 text M ≠ expected M | `p2_text_stale` |
| P2 count ≠ expected M / text ≠ count | `p2_disagree`, exercising both together |
| P2 parts ≠ expected M | None |
| P3 non-vacuity: no paint / no bottom | `p3_no_paint` / `p3_no_bottom`; both also change `nonVacuous` |
| P3 untriggered request | `p3_untriggered` |
| C1 no judged rounds | `c1_all_mismatch` |
| C1 completion / generation | `c1_refused`, changing both together |
| C1 `changedFalse` | None |
| C1 `revisionUnchanged` | None |
| C1 `waitedMsPresent` | `c1_no_waited` |
| C1 `engineReadAnswered` | None |
| C1 `noSelectionAt500ms` | `c1_selection` |
| C1 `noReopenToast` | None |
| C1 fewer than six rounds | `c1_short` |
| E2 no judged refusal | `e2_no_refusal` |
| E2 presence / non-null rect / equality | `e2_absent` / `e2_null_rect` / `e2_differs`, with overlapping clause changes |
| E2 `sequenceNotAfterReference` | None |
| Criterion on trace worker | `criterion_on_trace_worker` |
| Missing browser / wrong expected page / unknown arm | No mutation; separate unit tests cover them |
| P2-c unseen / lone / non-lone | Three `p2c_red_cases()` |

The P2-c reader cases supply aggregate counts rather than actual traces. Detector tests separately cover lone 13, tiles at +3 ms, and tiles at +40 ms at [`judge_v20_shakedown.py:397`](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/judge_v20_shakedown.py:397). None covers separate flushes, generation separation, or the cited click timeline.

Most C1/E2 red cases change both the raw evidence **and** the corresponding boolean clause. They establish that the judge rejects false clauses; they do not establish that the runner derives those clauses correctly. The missing-value and timestamp counterexamples above therefore remain green despite all existing tests passing.

Verification: all six Python unit tests passed; judge `--self-test` reported zero failures; the page-number Node test command passed. Counterexamples used in-memory variants and pure helper calls. No browser, ddev, Nextcloud, or make operation was run; the working tree remained clean.
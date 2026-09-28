# Evidence for finding 099

Finding 099 was found and fixed together with 098, in the same file and the same
change (shell generation v52). Its unit-level evidence and the review seats live with
098's: `findings/evidence/098/README.md`, sections 1 and 3.

This directory holds the **browser-level** evidence for the **within-Worker** mode,
added 2026-09-28 after the fix landed. The **cross-Worker** mode is still measured at
unit level only (it needs two induced deaths and a revision coincidence).

## 1. Within-Worker, on the real engine — `probe_099_within_worker_review_path.py`

Until this run, the two premises the within-Worker mode rests on were read from source:
(a) the review path is reachable from the product's buttons, and (b) the engine does not
advance the revision on that path (`failFormatBarrier` never calls `advanceRevision`,
`src/probe_engine.cpp`). The unit test asserts the consequence against the test file's
**fixture** engine. This probe measures both premises and the consequence against the
real engine, through the product's own controls.

**Recipe** (all product controls; keys are real CDP key events; fixture
`multi-paragraph.odt`, five one-line paragraphs):

1. click past the end of line 2; type `F099REVIEWMARK` → r1
2. `insert-paragraph-break` → r2, caret on a new empty paragraph
3. ArrowLeft → half C banks 有（r2）; ArrowRight → back onto the empty paragraph
4. 「• 項目符號」 on the empty paragraph → finding 046's residual, the review path
   (toast 「…無法單獨核對你的段落。請看一下結果，不是你要的就按「復原」…」)
5. **ArrowLeft — the press under test**
6. an uncaught error inside the document worker (`induce_worker_failure`, the inducer
   check 42 uses on v14) → the product's notice → 「回到檢查點」 → save through the
   product's save button → read `content.xml`

**Arms** (the served session file differs only in two exact-text pairs; each arm
asserts `servedMatchesArm`):

| arm | 098 half (moves not mutations) | 099 half (guard compares stamps) | served session |
| --- | --- | --- | --- |
| `prefix` | reverted | reverted | `ad148f5b2961…` (code-equivalent to v51) |
| `a-only` | fixed | **reverted** | `b218f6c67302…` |
| `landed` | fixed | fixed | `191de3733589…` = the source tree's file (`servesLandedBytes: true`) |

`a-only` against `landed` isolates 099's fix: the one comparison is the only difference.

**Criteria** were written into the probe's docstring before the first run: VOID unless
every step reached its state, the step-3 label is exactly 有（r2） and stays, the toast
carries the review promise, the notice offers `rescue: checkpoint`, and — the
**positive control** — the saved document contains both the typed mark and the empty
paragraph (so what was restored is the r2 checkpoint, not r1 and not the authority
bytes). Then KEPT_THE_BULLET if the empty paragraph after the mark is inside a
`text:list-item`, LOST_THE_BULLET if not. Predicted: prefix LOST, a-only LOST,
landed KEPT.

### Result on `e2-editor-v8` (the page as `dist/` pins it) — `within-worker-v8-2026-09-28.json`

Chrome 151.0.7922.169, page `e2-editor-app.js` `1ec7baf9fb53…`, pin `4a2710bba1ef07d9`,
a fresh browser per attempt.

| arm | outcome | revision across the bullet | tested press | label before → after the tested press |
| --- | --- | --- | --- | --- |
| `prefix` | **LOST_THE_BULLET 3/3** | 2 → 2, 3/3 | 0.15–0.16 s | 有（r2） → 有（r2） |
| `a-only` | **LOST_THE_BULLET 3/3** | 2 → 2, 3/3 | 0.15–0.16 s | 有（r2） → 有（r2） |
| `landed` | **KEPT_THE_BULLET 3/3** | 2 → 2, 3/3 | 0.46 s | 有（r2） → 有（r2） |

`armsDisagreeAsPredicted: true`. What came back, in every attempt of every arm:
`E1-MULTI-START alpha`, `第二段中文 betaF099REVIEWMARK`, an empty paragraph,
`第三段跨行 gamma`, … — the mark and the break are always there (positive control
held 9/9); the empty paragraph is a list item only in `landed`.

Readings:

- **Premise (b) is measured, not read**: the revision did not move across the
  review-path bullet in 18 of 18 attempts on this core (9 here, 9 in run 1 below,
  where every attempt reached the bullet before the instrument failed).
- **The latency is a second, independent witness.** The tested press takes 0.46 s
  where a checkpoint save happens (`landed`) and 0.15 s where it is skipped; the
  step-3 press, which banks in every arm, takes 0.61 s in every arm.
- **The label cannot show it.** 有（r2） before and after the tested press in all three
  arms: the new checkpoint in `landed` is also at r2, because the revision did not
  move. A user sees the same label whether the bullet is protected or not — which is
  099 in one line.
- **LOST in `prefix`/`a-only` is not "the bullet never applied"**: `landed` runs the
  same recipe on the same engine, and the arms differ only in session code that runs
  after the bullet was dispatched. No arm verifies the bullet in the live session
  before the death (the page renders no list state, and the barrier's inability to
  verify it is the review path itself).

### Result on `e2-editor-v14` (the candidate, page repointed) — `within-worker-v14-2026-09-28.json`

`--profile e2-editor-v14`: the page is rewritten by `repointed_page`, the same function
`--candidate-profile` and `tools/build_cutover_page.py` use (page `d74801324d24…`, pin
`5847a1407d3af58f`). Diagnostic evidence class: it is the page a cutover to v14 would
serve, not the page that ships today. v14 matters more than v8 here: it is the profile
half C would ship with.

| arm | outcome | revision across the bullet | tested press |
| --- | --- | --- | --- |
| `prefix` | **LOST_THE_BULLET 3/3** | 2 → 2, 3/3 | 0.15–0.16 s |
| `a-only` | **LOST_THE_BULLET 3/3** | 2 → 2, 3/3 | 0.15–0.16 s |
| `landed` | **KEPT_THE_BULLET 3/3** | 2 → 2, 3/3 | 0.46 s |

`armsDisagreeAsPredicted: true`; positive control held 9/9; the step-3 press 0.61 s in
every arm, as on v8.

**Observation, not pursued.** On v14 this cell takes the **multi-block** route (toast
「…涵蓋了不只一個段落，無法單獨核對…」), the same as v8 — not finding 083's
empty-selection route (「取不到任何內容」), which 083 measured on the accessibility core
of `e2-editor-v10` on 2026-08-26. The product-path runner's own blank-line cell says
the same on v14 (`unverifiedSentence: multi-block` in
`findings/evidence/096/product-path/plain-e2-editor-v14-b4-01.json` and in
`findings/evidence/098/product-path/v52-profile-e2-editor-v14.json`), so it is not
this fixture. Which link changed the core's answer is unmeasured. 083's fix is still
correct for the shape it handles; the observation only means v14 does not currently
exercise it on this cell.

### Run 1: the inducer works once per browser — `within-worker-v8-2026-09-28-run1-inducer-once-per-browser.json`

The first run reused one Chrome session per arm. Attempt 1 of each arm came out as
predicted (prefix LOST, a-only LOST, landed KEPT); attempts 2 and 3 of every arm were
VOID at step 6 with `auto-attach delivered no session for a document worker` — 6 of 6.
`induce_worker_failure` turns `Target.setAutoAttach` on and leaves it on; a navigation
later, the second call finds no worker. The mechanism was **not isolated** (the likely
one — the new worker's `attachedToTarget` event arrives while `ChromeSession.call` is
waiting for something else and is discarded — is an inference). The probe now opens a
fresh browser per attempt.

**For the product-path runner**: `induce_worker_failure` has two call sites
(`run_e2_c_product_path.py`, check 42 and `recovery-returns-what-the-product-promised`).
In the 2026-09-28 v14 run only one of them fired. If a profile ever needs both in one
run, the second is expected to fail this way; check 42 would then report FAIL with
`B4: null` (its accepted cost, written in the runner), i.e. loud, not a silent green.
Not changed here.

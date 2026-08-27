# Handoff: instruments that hid what they were built to find

Written 2026-08-28, covering 08-27 and 08-28. Continues
[`HANDOFF-2026-08-26-the-guard-fired-on-its-own.md`](HANDOFF-2026-08-26-the-guard-fired-on-its-own.md).

**In one line.** Finding **084** was root-caused, fixed and measured — and the
first version of the instrument built to measure it **suppressed it**, 0 of 24
against 10 of 48. That turned out to be the shape of the whole two days: four
more times an instrument answered confidently about something it had never
looked at. The accessibility lineage now matches the shipped profile at
**38 PASS / 2 NOT_ESTABLISHED**, the cutover has a written gate with its first
soak run banked, and the revert has been executed rather than assumed.

## State

`e2-editor-v8` still ships. `web/e2-editor-app.js` points at it, the tree is
clean, and **nothing was pushed** — 26 commits are local.

**Shell generation v43** (`7e99d3a3b8ba789b`), frozen for finding 084's fix. No
relink, no engine change, no profile repackage in two days.

| | |
|---|---|
| shipped `e2-editor-v8`, plain runs | **38 PASS / 2 NE**, `ok: true`, checklist reconciles |
| a11y `e2-editor-v11`, plain runs | **38 PASS / 2 NE**, `ok: true` — was 37 / 3 |
| candidate page (`--candidate-profile`) | **38 / 2**, checklist reconciles as a candidate |
| gates | both static batteries, queue 61 items 0 drifted, E1-C intact, self-tests 14/14 and 35/35 |

## 1. Finding 084, root-caused and fixed

**Two writers, one guard.** The page's `editorState.caret` is written by the
engine's `editor-state` announcement (guarded on `sourceSequence` advancing,
added by finding 068) **and** by the drain's own `getState()` in
`editor-shell/editor-session.js:301-311`, which has no guard at all. A read
answered *before* an announcement and applied *after* it puts the old caret
back, and nothing asks again until the next commit.

Finding 068 guarded a slow **event** landing after a fresher **read**. The
symmetric case — a slow read after a fresher event — was left open, and it is
the one the product hits.

The signature, in the page's own state log:

```
seq=294 caret=3458,4904 rev=128
seq=295 caret=3458,4904 rev=128
seq=296 caret=5618,4904 rev=128   <- the caret ARRIVES
seq=294 caret=3458,4904 rev=129   <- the drain writes it BACK
```

`sourceSequence` going backwards while `revision` goes forwards in the same row
— the second identifies the writer, because only the drain writes those two
together. **10 of 10 dropped commits carried it.** The sink was moved to the new
caret and then moved back, so the page drew it correctly for one frame.

**Fixed** in `NarrowEditorV2Session` (subclass, for finding 068's reason: the
natural home is bound to E1-C's verdict), shell generation **v43**. Four design
decisions, each with a test and a mutation that reddens it; the guard is proven
**order-independent** — *after any interleaving the snapshot holds the highest
`sourceSequence` written* — over all 24 permutations of four arrivals, duplicates
in every position, a hostile stream, and the measured two-announcements-per-commit
shape in all three orders.

**Measured after: 60 commits on v11 (pre-fix was 48), 0 dropped, the guard
refusing 28 stale writes.** 24 on the shipped profile, 0 dropped, guard fired 0
times. The acceptance condition was written before the runs: *green is not
enough, the guard must have fired*, because a clean run whose guard never fired
has only shown that the race was not lost.

## 2. The extra announcement has a name, and it carries a stale caret

| | announcements per commit | sources |
|---|---|---|
| shipped `e2-editor-v8` | **1**, on 12 of 12 | `visible-cursor` |
| a11y `e2-editor-v11` | **2**, on 24 of 24 | `a11y-paragraph-changed`, then `visible-cursor` |

Deterministically one extra. It is `LOK_CALLBACK_A11Y_FOCUS_CHANGED` →
`editorSource = "a11y-paragraph-changed"` (`src/probe_engine.cpp:2433`) — read
from the engine's own dispatch, not inferred from two build variables, which is
what lets it be said at all given the core changed writer-only → writer+calc
*and* accessibility. **Nothing here measures calc, and nothing may be quoted as
if it did.**

**The extra announcement carries a caret of its own — the stale one**, because
the accessibility paragraph callback fires before the cursor has moved. Two
announcements per commit both claiming to describe the caret is the window 084
lived in. On the shipped core there is only one, it is always last, and there is
nothing left to overwrite it. **That is a rate, not immunity: the defective code
is shared JavaScript and ships today.**

## 3. The instruments — this is the part worth reading

**An instrument can suppress the defect it was built to measure.** The first
three-layer caret probe asked the engine for its caret *before every commit* — a
real engine command. Under it, 24 of 24 commits followed the caret. With the
identical configuration and no probe on a passing commit, **10 of 48 dropped**
(Fisher exact p = 0.012). The risk had been written into the limits section
*before* the runs, which is the only reason 0/24 read as "check the instrument"
rather than "it is fixed". `--caret-engine-probe stalled` is now the default: a
commit the sink followed sends the engine nothing.

**A stability predicate must distinguish settled from never-started.**
`stable_bands()` returned when the scan's shape repeated — and **two empty scans
agree with each other**, so a canvas that had not painted yet was "settled, zero
bands" half a second after opening. One arm abstained 3 of 8 runs and the
checklist could not reconcile. After the fix: `scanSettledAfterTries` is **4** in
three runs of three. A constant, not a rate — which is what an instrument reading
too early looks like once it stops.

**Things that arrive as EVENTS get thrown away by readers written for
request/response — three times in two days.** `ChromeSession.call` discards every
message whose id does not match. (a) The auto-attach probe polled with it, so all
eight `Target.attachedToTarget` events arrived inside the polling loop; it
reported zero attachments. (b) Wired into the runner, `setAutoAttach` was called
through the same helper — and Chrome emits the attach events **before** it
answers the command — so the report said "auto-attach delivered no session" on a
run where every attachment had happened. (c) 084's own probe dropped `sid` from
its record when it was rewritten, and two write-ups reasoned about the wrong
thing.

**A control refuted a plausible, tidy, wrong conclusion.** The plan had been to
tell the document worker from the pthreads by responsiveness — pthreads sit in
`Atomics.wait`. `Runtime.enable` is answered by the **browser**, not by the
target's JavaScript thread, and it timed out too. Without that control the record
would say "the pthreads are blocked, so they cannot be asked".

**A field that was not under test caught a false finding.** The ODT round-trip
probe first reported the sentinel lost in **both** directions — which would have
been a cross-version incompatibility finding, the most expensive kind, because it
argues against a cutover with evidence that is not about the cutover. `doc` was
still `list-contexts.odt`: the probe waited for `state == "ready"` after handing
the file over, and the page was **already** ready. *Which document is in front of
you* and *are you ready* are different sentences.

## 4. The cutover, adjudicated

An adjudication on 2026-08-27 returned **cut over with named conditions** and
corrected three things.

**The chicken-and-egg was false.** Non-diagnostic evidence seemed to require the
cutover and vice versa. The acceptance tool's objection is about **identity
binding**, not about which URL is live — so `repointed_page()` is now one
function with three callers (`--profile`, `--candidate-profile`,
`tools/build_cutover_page.py`), and a **candidate run** measures the page as it
will ship, carrying its own pin, with its sha256 in the report. The cutover is
then a flip to bytes already measured, proven by hash.

**My "the discovery rate has not levelled off" was unfalsifiable as written** —
and the burst is partly an artifact of first measurability: v8 had the same one at
the same age (049–053, all from its first manual round). The fix is a horizon,
now written: **`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`**.

**The benefit side is unmeasured.** Everything measured shows v11 is *no worse*.
The entire case for the cutover is `caretParagraphText` and `documentOutline`, and
**no screen reader has ever consumed them on v11's five bound identities.**

### The NE delta was a finding in an NE costume

Asked which check makes v11 37/3 against v8 38/2: it was
`recovery-returns-what-the-product-promised`, NOT_ESTABLISHED 5 runs of 5 because
finding 038's inducer no longer wedges that core — so **the product's safety net
for unsaved work was driven by nothing** on the profile a cutover would ship.

**Closed** with a second, defect-independent inducer: an uncaught error inside the
document worker, the class `DocumentSdk._handleCrash` listens for, reached through
`Target.setAutoAttach` (not `attachToTarget`, which returns a session id to which
nothing is ever answered). The checkpoint **survives the crash**; the branch under
test is the same one 038's route exercises; v11 went 37/3 → **38/2**. The shipped
profile is the control: 038 still reproduces there and the fallback never fires.

## 5. The size number I had been quoting was wrong

I had said **+19 MB (+17%)**. That is the **wasm alone**, and the wasm is not what
an institution downloads.

| | v8 | v11 | delta |
|---|---|---|---|
| `probe.js` + `probe.wasm` | 110.1 MB | 129.1 MB | +19.0 |
| `soffice.data` (core image) | **32.6 MB** | **103.5 MB** | **+70.9** |
| `cjk-r5` pack | 18.6 MB at startup | folded in | |
| `fallback-fonts-r5` | 46.8 MB **on demand** | folded in | |
| **required before the editor is usable** | **161.4 MB** | **232.8 MB** | **+71.4 MB, +44%** |

Two differences, not one: v11's core image is three times v8's, **and v11 has no
resource packs at all**, so the lazy loading v8 has is gone. The 2026-08-20
ruling accepted "+19.9 MB"; **the user's confirmation must be against +71.4 MB at
startup.** Cheap and owed: ask whether v11 can carry resource packs the way v8
does — that would remove most of the second difference.

## 6. The revert: executed, not assumed

The cutover was performed for real, the net run against the real page, the revert
performed with the same tool, and the net run again — with the revert on a
`trap … EXIT` so a run dying in the middle could not strand the tree.

38/2 before, 38/2 after, the page byte-identical to its baseline
`28e03e5bc9fcb8c4`, `git status` clean, the post-revert run reconciling
`ok: true`.

**And the rehearsal found what has to flip alongside.** The product page **is** the
shell bundle's entrypoint, so the cutover moves the bundle digest and every run
after it is refused — measured, `ok: false`. So the cutover is **four steps**:
write the page, stage it into `dist/`, **freeze the new generation and repoint
`MANIFEST`**, and the revert undoes all three. Step 3 was missing from the plan.
That is what "a revert that has never been executed" hides: not that the flip
fails, but that something else has to flip with it.

Also checked: `dist/profiles/resources/` is **shared** by twelve profiles, and
v8's archive holds **four of the five identities** — the core data is not in it.
A cutover does not endanger those files (v11 references none of them), so the
revert is still a flip; but the archive cannot restore v8 on its own and its
`ATTRIBUTION.md` says "the five identities" while listing four.

## What is left, in order

1. **The soak: 11 more clean runs**, across ≥3 calendar days, ≥2 per day, plus 3
   diagnostic runs at `--caret-rounds 12`. Run 1 of 12 is banked. Criteria are in
   the plan and **may not be moved**; any FAIL or any NE outside the two known
   ones restarts the count at zero.
2. **The screen-reader round** — needs the user or a machine with Orca/NVDA. This
   is the only condition that measures the *benefit*, and the one most likely to
   embarrass us in front of the buyer the schedule was rearranged for.
3. **Rehearse step 3** — freezing and un-freezing a generation was discovered by
   the rehearsal and has not itself been rehearsed.
4. **The archive's fifth identity** — either archive v8's core data beside it or
   correct the ATTRIBUTION's wording.
5. **Ask about resource packs on v11** (see §5).
6. **26 commits are unpushed.** Pushing is the user's step.

## The push

Nothing has been pushed. `git log --oneline github/main..HEAD` is 26.

# The v12 soak — the bank

Criteria: `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, the soak section
as amended 2026-08-29 (candidate `e2-editor-v12`, page sha `3dfdcfef…`).

A run counts only if: `ok: true` and `complete: true`; `check_usable_editor.py`
reconciles `ok: true` with `reconciledFor.kind == "candidate-cutover"` and
`profile == "e2-editor-v12"`; the composition is 38 PASS / 2 NOT_ESTABLISHED
with the NE set exactly `{notice-action-recovers-the-session,
a-refused-action-is-reported-and-changes-nothing}`; and the report carries
`candidateCutover.pageSha256 == 3dfdcfef…`.

**Which calendar day a run belongs to**: the day of the report's completion
timestamp. Written down because run 3 of the void v11 lineage started at 23:54
and finished at 00:01, and a criterion with an undefined boundary is the shape
this gate exists to stop.

| # | date | report | composition |
|---|---|---|---|
| 1 | 2026-08-29 | `../queue-v11-split-probe/criterion-2-net-v12.json` | 38 PASS / 2 NE, reconciled |
| 2 | 2026-08-29 | `soak-run-02-candidate.json` | 38 PASS / 2 NE, reconciled |
| 3 | 2026-08-29 | `soak-run-03-candidate.json` | 38 PASS / 2 NE, reconciled |
| 4 | 2026-08-29 | `soak-run-04-candidate.json` | 38 PASS / 2 NE, reconciled |

Run 1 is the split probe's criterion-2 run, banked in place rather than copied:
evidence in this tree is not moved. It satisfies every clean clause on the real
candidate page.

## The void lineage

Five clean runs on unsplit `e2-editor-v11` (2026-08-28 ×2, 2026-08-29 ×3) are
**void for this count** and retained, untouched, in
`../queue-v11-cutover-soak-not-started/`. They were voided by the candidate
changing identity, not by anything wrong with them.

## Interrupted, not banked

`interrupted-2026-08-29-0050-partial.json` is the **partial snapshot of an
interrupted run**, not a run. It carries `complete: false` and no `ok` and
stopped after 6 checks, so `check_usable_editor.py` refuses it — the guard
working.

It was written as `soak-run-02-candidate.json` and has been **renamed out of
the `soak-run-*` namespace**, kept rather than deleted. A file called
`soak-run-02-…` that is not run 2 is exactly what a later glob miscounts, and
the fix is a name that does not lie rather than a deletion that hides that the
interruption happened. Nothing about the product was measured by it.

**Superseded 2026-09-03** by the plan's amendment of that date: a run's day is
the UTC date of the report's own `completedAt`; reports without the field
(runs 1–6) count toward twelve and contribute no day. The dates in the table
above are the drafting party's assertion, corroborated only by mtime read before
any clone; the criterion does not consume them. The instrument now writes the
field, so runs 7–12 carry their own day.

## Voided 2026-09-05 — the candidate page moved, and the count is 0 of 12

The human round of 2026-09-04 forced two fixes into
`wasm_sdk_probe/web/e2-editor-app.js`, one of the shell bundle's thirteen
`included` paths. The candidate page's sha therefore moved from
`3dfdcfef…` to
**`20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95`**,
recomputed from source through `repointed_page()` against
`dist/profiles/e2-editor-v12/sdk-manifest.json`.

Every run banked above was taken on `3dfdcfef…` and is **void for this count**:

* Runs 2–8 moved, untouched, to `../queue-v12-cutover-soak-void-3dfdcfef/`,
  with `WHY-THESE-ARE-VOID.md` alongside them.
* Run 1 — the split probe's criterion-2 run, banked in place at
  `../queue-v11-split-probe/criterion-2-net-v12.json` — stays where it is,
  because it is that probe's evidence as well, and is dropped from this
  checker's `--also` list.
* `interrupted-2026-08-29-0050-partial.json` stays. It is a declared non-run and
  makes no sha claim; nothing about the page voids it.
* `diagnostic-01..03` stay in this directory and are **also void**, by
  `check_caret_diagnostics.py`'s own identity term (`pageShaMatches`), which
  pins them to the same sha. That is condition 2's business, not condition 1's;
  `check_soak_bank.py` continues to list them under
  `conditionTwoFiles_NOT_JUDGED_HERE` without judging them.

`check_soak_bank.py`'s `--expect-page-sha256` default is updated to the new sha
in the same change. **Until run 1 on the new page is banked, `--self-test`
aborts** with "self-test has no complete report to build from: it would
otherwise pass by measuring nothing" — the refusal that was written for exactly
this state, not a broken tool. It returns to normal with the first banked run.

Counting: **0 of 12**, no dayless runs, no carry-over. The 2026-09-03 amendment
(a run's day is the UTC date of its own `completedAt`) applies from run 1, and
every run from here carries the field, so the ≥3 UTC days clause is judged
entirely in-band for the first time. Earliest possible close from a 2026-09-05
start: **2026-09-07 UTC**.

### Run 1 on `20f09cc9…` — 2026-09-05 01:31–01:37 CST (UTC day **2026-09-04**)

`soak-run-01-candidate.json`. 40 checks, `ok: true`, the two standing
NOT_ESTABLISHED sentinels and nothing else.

**Correction to the paragraph above.** It said "earliest possible close from a
2026-09-05 start: 2026-09-07 UTC", reading the local date. The criterion counts
**UTC** days, and this run's `completedAt` is `2026-09-05T01:37:10+08:00`, which
is UTC **2026-09-04**. With ≥2 runs on each of 09-04, 09-05 and 09-06 the
earliest close is **2026-09-06 UTC**. The earlier sentence is left in place per
the append-only rule; this is what supersedes it.

**Read this before the next run.** Run 1 was taken twice. The first attempt was
clean, `ok: true`, and measured the **wrong page**: `run_e2_c_product_path.py`
builds its mirror from `dist/`, and `dist/e2-editor-app.js` was still the
2026-09-03 copy, carrying neither the 087 nor the 088 fix. It self-reported
`pageSha256: 3dfdcfef…` and this bank's `page-sha` clause would have refused it.
`make dist/e2-editor-app.js` fixes it; finding 090 records the gap and that
nothing compares the two sources. **A run taken without that copy being current
is a run on the incumbent page wearing the candidate's name.**

### Run 2 on `20f09cc9…` — 2026-09-05 01:53–01:59 CST (UTC day **2026-09-04**)

`soak-run-02-candidate.json`. 40 checks, `ok: true`, the two standing
NOT_ESTABLISHED sentinels and nothing else. `dist/e2-editor-app.js` was checked
against `web/` before the run and was already the same bytes
(`5aeae0e1…`), per finding 090.

UTC day 2026-09-04 now carries **2 runs** and satisfies the ≥2 clause. Two UTC
days remain to be earned, and ten runs.

### Runs 3–10 on `20f09cc9…` — 2026-09-06 18:27–19:16 CST (UTC day **2026-09-06**)

`soak-run-03-candidate.json` … `soak-run-10-candidate.json`, eight runs taken
back to back by one script, each ~6m07s. Every one: 40 checks, `ok: true`,
`complete: true`, `pageSha256: 20f09cc9…`, and the two standing NOT_ESTABLISHED
sentinels with nothing else in the set. `dist/e2-editor-app.js` was compared
against `web/e2-editor-app.js` before the batch and was the same bytes
(`5aeae0e1…`), per finding 090.

Bank state after these: **10 clean of 12**, one page sha, no dayless run, no
naive stamp. Qualifying UTC days: `2026-09-04` (2 runs) and `2026-09-06`
(8 runs). `count-reached` and `day-spread` are the only false clauses.

**Correction, and it costs a day.** The note under run 1 said the earliest close
is **2026-09-06 UTC**, on the assumption of ≥2 runs on each of 09-04, 09-05 and
09-06. **UTC 2026-09-05 passed with zero runs.** Nothing was measured on it and
nothing can be added to it; a UTC day that ends is not re-openable. So the
earliest close is **2026-09-07 UTC**, and it needs ≥2 clean runs on that day.
The 2026-09-06 sentence stands where it is per the append-only rule; this is
what supersedes it.

What that day cost is exactly one thing — the calendar — and nothing else. No
criterion moved, no run was voided, and the count did not restart. The gap is
recorded here rather than left to be inferred from a hole in `runsPerUtcDay`,
because a reader who found that hole later could not tell an unmeasured day from
a day whose runs were dropped.

**Remaining: two clean runs on UTC 2026-09-07** (Taipei 2026-09-07 08:00 →
2026-09-08 08:00), which closes both `count-reached` and `day-spread` together.

## Voided again 2026-09-06 — the page moved a second time, and the count is 0 of 12

The shipping shell was changed twice on 2026-09-06. The fix for finding 088
(the doubled-paragraph residue — every non-heading paragraph spoken twice,
~117 ms apart) landed in `wasm_sdk_probe/web/e2-editor-app.js`, one of the
shell bundle's thirteen `included` paths, so the candidate page's sha moved
again, from `20f09cc9…` to
**`39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e`**. The
frozen shell generation moved to **v45**
(`bundleSha256 a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578`)
in the same change. Full account:
`handoff/HANDOFF-2026-09-06-the-page-moved-twice-and-the-4b-instrument-broke.md`
and `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md` (task T0).

Ruling 1 of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` (2026-08-28)
applies again: **the count restarts on the day the page changes.** Everything
banked above this line is void for this count and none of it is deleted:

* All ten soak runs (`soak-run-01-candidate.json` …
  `soak-run-10-candidate.json`) — carried `pageSha256: 20f09cc9…` — moved to
  `../queue-v12-cutover-soak-void-20f09cc9/`.
* Condition 2's three diagnostic runs (`diagnostic-01-caret12.json`,
  `diagnostic-02-caret12.json`, `diagnostic-03-caret12.json`) — carried
  `pageSha256: 20f09cc9…` — moved to the same directory. Unlike the
  `3dfdcfef…` void of 2026-09-05, this time the diagnostics move with the runs
  rather than staying behind, so nothing left in this directory still claims
  `20f09cc9…`.
* The judge's own verdict on those three diagnostics, `VERDICT-condition-2.json`
  (every entry's `pageSha256` was `20f09cc9…`) — moved and renamed to
  `VERDICT-condition-2-on-20f09cc9.json`, matching the naming its
  `3dfdcfef…` predecessor already carries.
* `interrupted-2026-08-29-0050-partial.json` stays. It carries
  `pageSha256: 3dfdcfef…`, a different and older page; today's move does not
  touch it.
* `RESULT-condition-2.md` stays, with a further appended section recording
  this second void and where the diagnostics and verdict it described have
  gone.

Full disposition and per-file page shas:
`../queue-v12-cutover-soak-void-20f09cc9/WHY-THESE-ARE-VOID.md`.

`check_soak_bank.py`'s `DEFAULT_SHA` and `DEFAULT_SERVED_SHELL`, and
`check_caret_diagnostics.py`'s `DEFAULT_SHA`, are updated to `39895d15…` and
v45's `a46c8518…` in the same change (this commit). Counting: **0 of 12**, no
carry-over, restart complete. Everything in condition 2, condition 4a's eight
terms, the ODT round trip and revert condition 3 that was taken on
`20f09cc9…` is void along with it — see the handoff cited above for the full
list.

## Re-pointed 2026-09-07 — the 088 residue's second fix landed, page moved a third time, and the bank was already empty

Finding 088's residue was not fully gone at `39895d15…`: the live region was
only silenced when the two channels (`caretParagraph` and `documentOutline`)
agreed, and at the second heading in a walk they disagreed for one snapshot,
so the older paragraph's text was spoken once more. The fix in
`wasm_sdk_probe/web/e2-editor-app.js` changes the test from "do the two texts
match" to "does the structure channel have a focused node at all"
(`doubled = structureSpeaks !== null`), one of the shell bundle's thirteen
`included` paths, so the candidate page's sha moved again, from
`39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e` to
**`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`**. This is
also the cutover itself: the entrypoint's worker URL and pin move from
`e2-editor-v8` to `e2-editor-v12` in the same bytes. The frozen shell
generation moves to **v47** (`bundleSha256
cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`, verified
two ways — read from `e2/editor-shell-v2-bundle-v47.json` and recomputed with
`shell_bundle_digest` over the served files, both equal) in the same commit as
the source change, per ruling E-1. No v46 generation was ever frozen: the
attempt that produced these bytes was measured and reverted before a
generation existed for it, so this is the first frozen generation carrying the
fix. Full account: `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`,
section "T1c: v46 measures better; D1 = A lands it", and
`handoff/HANDOFF-2026-09-06-the-page-moved-twice-and-the-4b-instrument-broke.md`.

**Nothing is voided by this move.** The 2026-09-06 void above left this bank
holding **zero** soak runs and zero condition-2 diagnostics — `cleanRuns: 0`,
`totalRuns: 0` on `check_soak_bank.py` before this change, unchanged after it.
There is nothing on `39895d15…` to move to a `-void-` directory.

`check_soak_bank.py`'s `DEFAULT_SHA` and `DEFAULT_SERVED_SHELL`, and
`check_caret_diagnostics.py`'s `DEFAULT_SHA`, are updated to `9b29e39b…` and
v47's `cf7f9233…` in the same change (this commit). Both judges' `--self-test`
still decline with "self-test has no complete report to build from" /
"self-test has no COMPLETE diagnostic report to build from" — the same
refusal recorded for the previous empty-bank state, not a new defect.

Counting: **0 of 12**, no carry-over, restart complete (the count was already
at zero; this move does not restart it a second time — it re-points an empty
bank's identity constants). Finding 088 is recorded as fixed by this change in
`findings/088-*.md`, measured in
`findings/evidence/manual-round-v12d-9b29e39b/RESULT-4b-v45-vs-v46.md`.

## Corrected 2026-09-07 — generation v47 was frozen by mistake on a cut-over shell

Generation v47 was frozen by mistake on a cut-over shell (commit `000a57e2`);
the shell is restored to shipping v8 with the v46 hunk and frozen as v48;
candidate page sha unchanged; zero runs voided; count stays 0 of 12.

The mistake: the landing that produced `000a57e2` ran `build_cutover_page.py
--profile e2-editor-v12 --write`, which repointed `web/e2-editor-app.js`'s
`workerUrl` and `PINNED_WASM_SHA256` from `e2-editor-v8` to `e2-editor-v12` in
addition to applying the v46 hunk, and froze that shell as v47. The gate (the
twelve soak runs counted in this bank, condition 4a, condition 2, and the
owner's manual round) has not passed, so the served shell must not point at
the candidate profile yet — only the v46 fix was meant to land there.

The correction: `web/e2-editor-app.js` has its `workerUrl` and
`PINNED_WASM_SHA256` restored to exactly their `f7f20317` values
(`e2-editor-v8` / `4a2710bba1ef07d9`); `git diff f7f20317 --
wasm_sdk_probe/web/e2-editor-app.js` is exactly one hunk, the v46 one.
`dist/e2-editor-app.js` copied from the same bytes; all thirteen bound paths
verified byte-identical between `web/` and `dist/`. Frozen as **generation
v48** (`bundleSha256
ecfb6866117673c21a7c21995f7ea76fe60beb9f94a73c222053a18cc573a6ef`, verified
two ways as before). **v47's JSON is left in place, unedited** — generations
are never overwritten — as a record of the mistaken bytes; `MANIFEST` in
`build_e2_c_shell_bundle.py` now points at v48.

**The candidate page sha is unchanged.** `build_cutover_page.py --profile
e2-editor-v12` (no `--write`, nothing touched in the tree) measured from the
restored v8 shell still gives
`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c` — the same
value T1c measured and the same value this bank's `DEFAULT_SHA` already held,
because `build_cutover_page.py`'s repoint fully substitutes the two lines with
the target profile's own values rather than transforming whatever bytes are
already there; the resulting digest does not depend on whether the source it
started from was itself already cut over. `DEFAULT_SHA` in both judges is
therefore **unchanged**. `check_soak_bank.py`'s `DEFAULT_SERVED_SHELL` moves to
v48's `bundleSha256` above.

**Zero runs voided.** The bank held zero soak runs and zero condition-2
diagnostics before this correction (the 2026-09-06 void above) and holds zero
after it — there was nothing on the mistaken v47 shell to void. Counting: **0
of 12**, unchanged.

## Re-taken on `9b29e39b…` / v48 — runs 1 and 2, both banked, both FAIL (2026-09-07)

Task T2 of `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`. Same
command as "The soak — the gate itself" above, `--candidate-profile
e2-editor-v12`, `--out` into this directory:

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-01-candidate.json
python3 tools/check_usable_editor.py --report soak-run-01-candidate.json
```

(and the same for run 2). Both banked exactly as measured — the rule this file
already states: *"A FAIL … is a result: bank it, record it, do not re-run to
'get a clean one'."*

| run | completedAt (local) | UTC day | composition | run `ok` |
|---|---|---|---|---|
| `soak-run-01-candidate.json` | 2026-09-07T01:48:32+08:00 | 2026-09-06 | 37 PASS / 2 NE / 1 FAIL | **false** |
| `soak-run-02-candidate.json` | 2026-09-07T01:55:35+08:00 | 2026-09-06 | 37 PASS / 2 NE / 1 FAIL | **false** |

`check_usable_editor.py --report` still reconciles `ok: true`,
`reconciledFor.kind == "candidate-cutover"` on both — the failing check below is
not one of its sixteen tracked capabilities, so its reconciliation alone would
have looked clean. The bank's own clean-run predicate (raw `ok`, `complete`,
composition, `one-served-shell`) is what catches it.

**Two independent red signals, identical on both runs — recorded, not fixed
(this task's role is gate operation, not repair):**

1. **A real product check FAILed, same id both times:**
   `the-document-region-says-why-it-is-empty`, payload identical on both runs:
   ```
   "observed": {"present": true, "text": "", "reason": "paragraph", "offers": "1"}
   ```
   The oracle: *"the accessibility region always carries something to read: the
   focused paragraph on a profile that offers one … Empty is the failure."*
   `offers: "1"` means this profile claims to supply paragraph text;
   `reason: "paragraph"` names the cause as paragraph text, yet the region held
   none. This is the exact check that gate condition 4a's term-6 mutation
   (`--mutate projection-not-wired`) is designed to redden — here it reddened
   on an **unmutated** run, 2 of 2. Not filed as a numbered finding by this
   task; recorded for whoever picks up the queue next.

2. **`one-served-shell` is false on both runs, and it is structural, not a
   flake.** `check_soak_bank.py`'s `DEFAULT_SERVED_SHELL` is v48's declared
   `bundleSha256` (`ecfb6866117673c21a7c21995f7ea76fe60beb9f94a73c222053a18cc573a6ef`).
   A `--candidate-profile e2-editor-v12` run's `servedShell.servedSha256` is
   computed over the tree's current bound files with the entrypoint replaced by
   the candidate's own repointed page — and v47 and v48 (the T1d correction)
   differ from each other in **only** that entrypoint file. So a
   candidate-cutover run's served digest is, by construction, v47's
   `bundleSha256` — measured on both runs as exactly
   `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`
   (`distinctServedShellSha256` confirms one value, matching v47's frozen
   record). This will reproduce on every future candidate-cutover run against
   the current tree; it is not run-to-run variance. Whether `DEFAULT_SERVED_SHELL`
   should instead pin v47's value for candidate runs, or the clause needs a
   different read for `candidateCutover` reports, is a judgement call this
   role does not make.

`check_soak_bank.py`'s verdict, verbatim (run-list omitted, shown in the table
above; full record in `VERDICT-soak-2026-09-07.json`):

```json
"cleanRuns": 0, "totalRuns": 2,
"distinctPageSha256": ["9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c"],
"distinctServedShellSha256": ["cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4"],
"servedShellBundlesSeen": ["e2/editor-shell-v2-bundle-v48.json"],
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": false, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

Counting: **0 of 12**, unchanged (it was already 0 of 12). UTC day 2026-09-06
now has two runs on it, neither clean, so it contributes no qualifying day —
the day-spread clause still needs three UTC days each with two *clean* runs,
not merely two attempted ones. `python3 -m unittest tests.test_e2_c_shell_bundle`
ran 12/12 green immediately before each run, per finding 090's manual rule.

## R-2 corrected: `DEFAULT_SERVED_SHELL` moves to v47's digest (2026-09-07)

Item A of the T2 follow-up
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "T2 came back red;
the schedule is stopped", R-2). Both runs above show `one-served-shell: false`
even though `servedShell.servedSha256` is identical and stable on both
(`cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`): the
judge's `DEFAULT_SERVED_SHELL` in `tools/check_soak_bank.py` pinned v48's
`bundleSha256` (`ecfb6866…`, the shell as the tree serves it) instead of the
digest a `--candidate-profile e2-editor-v12` run actually serves, which is by
construction the digest of the cut-over shell — v47, the generation frozen by
mistake in `000a57e2` and corrected (not deleted) by v48. T0's original pin
(v45's `a46c8518…`) was wrong the same way and was never exercised before this.

`DEFAULT_SERVED_SHELL` now reads v47's `bundleSha256`,
`cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`. Verified
two ways: read directly from `wasm_sdk_probe/e2/editor-shell-v2-bundle-v47.json`,
and read `servedShell.servedSha256` from both banked
`soak-run-01-candidate.json` and `soak-run-02-candidate.json` — both equal it
(shown above and unchanged by this correction, since only the judge's constant
moved).

Re-run after the fix (full record in `VERDICT-soak-2026-09-07-r2-correction.json`,
banked beside the earlier `VERDICT-soak-2026-09-07.json` rather than overwriting
it): `one-served-shell: true` on both banked runs.
`every-run-clean` is still `false` (R-1, the product-path FAIL, untouched by
this item) and `count-reached` is still `false`. Counting: **0 of 12**,
unchanged — this correction removes one judge-side false negative, it does not
manufacture a clean run. `check_soak_bank.py --self-test` still declines,
verbatim: `RED 11's run must fail on one-served-shell and NOTHING else; other
false clauses: ['run-ok', 'pass-count']` — the same message the self-test gave
*before* this fix (checked by re-running it against the unmodified file), because
the self-test's RED 11 case exercises the real bank directory, and the real
bank's two banked runs already carry `run-ok: false` / `pass-count: false`
from R-1, not from anything this item touched. The self-test's own synthetic
fixtures (RED 1–10, 12) are unaffected and were not re-inspected line by line
here; the decline is attributed to R-1's contamination of the one case that
reads the live bank, not to a defect this correction introduced.

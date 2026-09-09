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

## Run 3 — the first run under the amended region check, banked CLEAN (2026-09-07)

Task T5b of `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, item 2, run
against the tree as landed by `02b0a7d4`/`7dbbcc70` (the 2026-09-07 amendment,
"the region check verifies the claim, not the node" —
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`). Per that amendment's count
semantics, runs 1–2 stay banked FAIL under the old wording and are not
re-judged; this is the first report whose fields (`deferredToStructure`,
`activeDescendant`, `structureText`) exist at all, so it is the first run that
can count.

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-03-candidate.json
python3 tools/check_usable_editor.py --report soak-run-03-candidate.json
```

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-03-candidate.json` | 2026-09-07T07:19:35+08:00 | 2026-09-06T23:19:35Z | 2026-09-06 | 38 PASS / 2 NE | **true** |

Composition **38 PASS / 2 NOT_ESTABLISHED**, NE set exactly
`{a-refused-action-is-reported-and-changes-nothing, notice-action-recovers-the-session}`
— the fixed pair — and **no FAIL**. `the-document-region-says-why-it-is-empty`
is in the PASS set for the first time on this page: `observed.deferredToStructure
== "1"`, `observed.structureText` non-empty, `reason == "paragraph"`,
`offers == "1"` — the deferral clause the amendment added, satisfied by the
page's own real behaviour rather than by widening around it (the red cases in
`findings/evidence/gate-4a-on-9b29e39b/` prove the same predicate still fails
when that is not true). `candidateCutover.pageSha256` and
`servedShell.servedSha256` match the bank's pinned values (shown in
`VERDICT-soak-2026-09-07-run03.json`, saved beside this file).

`check_usable_editor.py --report soak-run-03-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v12"`,
`problems: []` (full output saved as `check-usable-editor-run03.json`).

**Banked as the first run that can count.** `check_soak_bank.py` verdict
(full record `VERDICT-soak-2026-09-07-run03.json`):

```json
"cleanRuns": 1, "totalRuns": 3,
"clauses": {"one-served-shell": true, "every-run-clean": false,
            "count-reached": false, "day-spread": false, ...}
```

Matches the expectation exactly: `cleanRuns: 1`, `totalRuns: 3`,
`one-served-shell: true` on run 3. `every-run-clean`, `count-reached` and
`day-spread` are still false — one clean run out of twelve, on one UTC day —
which is the correct state for 1 of 12, not a new defect.

**`check_soak_bank.py --self-test`, run for the first time against a bank that
holds a clean report** (full record `SELFTEST-2026-09-07-run03.txt`). It no
longer declines by crashing: RED 11 (`with_served`, which mutates the
*last* sorted `soak-run-*.json`'s `servedShell` and demands that run fail on
`one-served-shell` and nothing else) now builds against `soak-run-03…`, which
is otherwise clean, so RED 11 passes for the first time — the isolation the
2026-09-07 R-2 note said could not happen until a clean run existed. All
twelve of the other declared RED cases (1–10, 12) print `RED (correct)`.

**But the self-test still exits 1**, on its GREEN control, verbatim:

```
RED (WRONG)    control: 6 dated runs spanning 3 UTC days
  control failed on: ['every-run-clean', 'count-reached', 'day-spread']
  days: []
```

Read, not fixed (this task's role is gate operation, not repair): the
control's `stamped()` helper builds six synthetic dated reports by cycling
`sources[index % len(sources)]` over **every** `complete: true` report in the
real bank — now three (`soak-run-01`, `02`, `03`) — round-robin, not filtered
to clean ones. Four of the six synthetic copies are therefore restamped
copies of the two FAIL reports (01, 02), so `every-run-clean` is false by
construction and no UTC day accumulates two clean stamps. This is a property
of `stamped()`'s sampling, not of run 3: it would reproduce identically the
day this bank's real FAIL count is anything other than zero, independent of
which reports are FAIL. Not this role's file to edit; recorded verbatim per
this task's instruction, for whoever owns `check_soak_bank.py` next.

Counting: **1 of 12**, first clean run banked. `python3 -m unittest
tests.test_e2_c_shell_bundle` and `make test-e2-c-static` both ran green
immediately before this run, per finding 090's manual rule.

## 2026-09-07 08:50 CST — the checklist output moved out of the bank

`check-usable-editor-run03.json` (the `check_usable_editor.py` reconciliation
of run 03, referenced above) was written into this directory and
`check_soak_bank.py` refused it as an unclassified file — the membership rule
doing its job. It is moved, unchanged, to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run03.json`.
Convention from here on: reconciliation outputs go in that sibling directory,
never in the bank; the bank holds runs, condition-2 diagnostics and the
judge's own `VERDICT-*.json` only.

## Run 04 — clean (2026-09-07)

Gate operation session (soak A2), same command as run 03, one after another.

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-04-candidate.json
python3 tools/check_usable_editor.py --report soak-run-04-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run04.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-04-candidate.json` | 2026-09-07T08:55:57+08:00 | 2026-09-07T00:55:57Z | 2026-09-07 | 38 PASS / 2 NE | **true** |

`complete: true`. NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL.
`candidateCutover.pageSha256` = `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`;
`servedShell.servedSha256` = `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`
(v47's `bundleSha256`, matching runs 01–03).

`check_usable_editor.py --report soak-run-04-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v12"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run04.json`, never
into this directory (the judge refuses unclassified files here).

## Run 05 — clean (2026-09-07), banked by the main session after its executor was stopped

Soak session A2's second run. The report was already written and complete when
the session's executor was stopped mid-session by the owner; the run itself was
finished (`complete: true`, `completedAt` present), so it is banked exactly as
measured rather than discarded — nothing about it was re-run, and the
reconciliation below was produced by the main session from the untouched
report.

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-05-candidate.json
python3 tools/check_usable_editor.py --report soak-run-05-candidate.json
```

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-05-candidate.json` | 2026-09-07T09:03:43+08:00 | 2026-09-07T01:03:43Z | 2026-09-07 | 38 PASS / 2 NE | **true** |

`startedAt` 2026-09-07T08:57:37+08:00 (2026-09-07T00:57:37Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL.
`candidateCutover.pageSha256` = `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`;
`servedShell.servedSha256` = `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`.

`check_usable_editor.py --report soak-run-05-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run05.json`.

Two `serve_candidate_page.py` server pairs (ports 8765) were left running by the
stopped session and were terminated by PID by the main session; no browser was
left behind.

## Run 06 — clean (2026-09-07)

Soak session A2's remaining run, resumed by a fresh gate-operation session after
run 05 was banked by the main session. Same command as runs 03–05.

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-06-candidate.json
python3 tools/check_usable_editor.py --report soak-run-06-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run06.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-06-candidate.json` | 2026-09-07T15:04:45+08:00 | 2026-09-07T07:04:45Z | 2026-09-07 | 38 PASS / 2 NE | **true** |

`startedAt` 2026-09-07T14:58:38+08:00 (2026-09-07T06:58:38Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL.
`candidateCutover.pageSha256` = `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`;
`servedShell.servedSha256` = `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`.

`check_usable_editor.py --report soak-run-06-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v12"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run06.json`.

## Run 07 — clean (2026-09-07)

Soak session B2's first run, same command as runs 03–06.

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-07-candidate.json
python3 tools/check_usable_editor.py --report soak-run-07-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run07.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-07-candidate.json` | 2026-09-07T15:54:45+08:00 | 2026-09-07T07:54:45Z | 2026-09-07 | 38 PASS / 2 NE | **true** |

`startedAt` 2026-09-07T15:48:38+08:00 (2026-09-07T07:48:38Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL.
`candidateCutover.pageSha256` = `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`;
`servedShell.servedSha256` = `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`.

`check_usable_editor.py --report soak-run-07-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v12"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run07.json`.

## Run 08 — clean (2026-09-07)

Soak session B2's second and last run, same command as runs 03–07.

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out soak-run-08-candidate.json
python3 tools/check_usable_editor.py --report soak-run-08-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run08.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-08-candidate.json` | 2026-09-07T16:02:18+08:00 | 2026-09-07T08:02:18Z | 2026-09-07 | 38 PASS / 2 NE | **true** |

`startedAt` 2026-09-07T15:56:11+08:00 (2026-09-07T07:56:11Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL.
`candidateCutover.pageSha256` = `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`;
`servedShell.servedSha256` = `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`.

`check_usable_editor.py --report soak-run-08-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v12"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run08.json`.

## The R-1 restart applied to this directory — runs 01 and 02 moved out (2026-09-07)

Task T6 of `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, section
"Two decisions by the owner, 2026-09-07 evening", sub-section **P-0**, owner's
decision **A**. The two banked FAIL runs recorded above under "Re-taken on
`9b29e39b…` / v48" have been moved, with `git mv` and unchanged, to

    ../queue-v12-cutover-soak-void-pre-r1/soak-run-01-candidate.json
    ../queue-v12-cutover-soak-void-pre-r1/soak-run-02-candidate.json

with a `WHY-THESE-ARE-VOID.md` beside them, modelled on
`../queue-v12-cutover-soak-void-3dfdcfef/` and
`../queue-v12-cutover-soak-void-20f09cc9/`.

**Authority.** The plan's section "R-1 = A, by the owner" (2026-09-07) already
ruled the restart: *"This changes the clean-run predicate, so the count
restarts — it is at 0; runs 1–2 stay banked FAIL under the old wording and are
not re-judged."* P-0 applies that ruling to this directory, because
`check_soak_bank.py` enumerates by glob (`soak-run-*.json`) and its clause
`"every-run-clean": len(clean) == len(runs) and bool(runs)` is taken over that
glob — so "not re-judged" and "the count is at 0" are consistent only if the
superseded lineage leaves the counting directory. Left in place, the twelfth
clean run would have produced `cleanRuns: 12, totalRuns: 14,
every-run-clean: false`.

Not voided by a page move: both carry `candidateCutover.pageSha256`
`9b29e39b…`, the same page every surviving run carries. What was superseded is
the clean-run predicate, not the bytes.

**Nothing else changed.** `tools/check_soak_bank.py` is untouched, including its
`DEFAULT_*` constants; no criterion text is relaxed; the surviving runs are
**not** renumbered (the bank now runs 03–08 with no 01/02, and the gap is the
record of the restart); no run was re-executed. Runs 01 and 02 had no
`check_usable_editor.py` output file — that convention started with run 03 —
and the three `VERDICT-soak-2026-09-07*.json` files stay here; the reasoning
for both is in the WHY file.

**The judge, before the move** (`cd wasm_sdk_probe && python3
tools/check_soak_bank.py`; full output in
`../queue-v12-cutover-soak-void-pre-r1/JUDGE-OUTPUT-before-the-move.txt`):

```json
"cleanRuns": 6, "totalRuns": 8,
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": false, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

`--self-test` before the move: `self-test passed: 12 red cases all red, and the
green control is green` (exit 0).

**The judge, after the move** (full output in
`../queue-v12-cutover-soak-void-pre-r1/JUDGE-OUTPUT-after-the-move.txt`):

```json
"cleanRuns": 6, "totalRuns": 6,
"distinctPageSha256": ["9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c"],
"distinctServedShellSha256": ["cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4"],
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": true, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

`--self-test` after the move: same 12 red / green control, exit 0.

Counting: **6 of 12**, unchanged by this move — it removes two runs that the
restart had already excluded from the count, and manufactures no clean run.
`ok` stays `false` on `count-reached` and `day-spread`; six more clean runs are
owed, at least two on each of two further UTC days. Per P-1 of the same
section, no further soak run is taken until T4 (the owner's manual round) is
done.

## The candidate moved to `e2-editor-v13`, and the judge's constants moved with it (2026-09-09)

The owner ran step 4 of `handoff/RUNBOOK-operator-093-engine-geometry.md` and
the relink minted `e2-editor-v13` (finding 093, section 「步驟 5」). Four
constants in `tools/check_soak_bank.py` moved together, in the commit before
run 09 and therefore before any run that could satisfy them — the order the
2026-09-08 amendment of
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` ("The re-freeze this
obliges, and its ORDER") requires:

| constant | before | after |
|---|---|---|
| `EXPECTED_PASS` | 38 | **39** |
| `DEFAULT_PROFILE` | `e2-editor-v12` | **`e2-editor-v13`** |
| `DEFAULT_SHA` | `9b29e39b…` | **`31787584…`** |
| `DEFAULT_SERVED_SHELL` | `cf7f9233…` (generation v47) | **`ea69984c…`** (measured) |

`tools/check_caret_diagnostics.py`'s `DEFAULT_SHA` moved to the same page;
its `DEFAULT_PROFILE` was deliberately left at `e2-editor-v12` and the
inconsistency is recorded in that file rather than silently repaired.

**The served-shell pin is a measured value, not a generation's digest.** Ruling
E-4 words the clause as *"the digest the cutover generation will declare"*. For
v12 that could be satisfied by reading a file only because generation v47 had
been frozen on the cut-over bytes by mistake (`000a57e2`). **No frozen
generation declares `ea69984c…`** — v49 is the shipping shell, entrypoint still
`e2-editor-v8`, declaring `4f8494b6…` — and freezing one on cutover bytes to
manufacture a file to read would repeat exactly what v48 was frozen to undo.
**The shipping page was not repointed**; `build_cutover_page.py --write` was not
run. §5 step 5.3 of the runbook, which instructs that repoint, is the cutover;
a correction saying so is appended to that runbook.

Both halves of the identity were recomputed from committed bytes before the
constants were edited, neither of them by reading the run being judged:

* `python3 tools/build_cutover_page.py --profile e2-editor-v13` (no `--write`)
  printed `pageSha256` `31787584…`;
* generation v49's `included` list with the entrypoint's hash replaced by that
  page sha, through `shell_bundle_digest` (`tools/validate_e1_c.py:134`),
  gives `ea69984c…`.

**Measured consequence, recorded because it looks like breakage and is not.**
With the constants moved and no post-relink run yet banked,
`check_soak_bank.py --self-test` exited 1 with `self-test has no clean report
to build from: it would otherwise pass by measuring nothing` — its fixtures are
built from live-bank reports the judge itself calls clean, and none of the six
2026-09-07 runs is clean under the new predicate. Run 09 restored it. This is
the mechanical trap the amendment named, and it is why the void move of those
six runs comes **after** this run, not before.

## Run 09 — clean, the first run on `e2-editor-v13` (2026-09-09)

First run under the amended predicate (**39 PASS / 2 NE**, the forty-first check
`the-projection-is-placed-where-the-document-is` having landed while the count
was zero) and the first on the new candidate page. Same recipe as runs 04–08.

```
make test-e2-c-static                       # exit 0, immediately before
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 --out soak-run-09-candidate.json
python3 tools/check_usable_editor.py --report soak-run-09-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run09.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-09-candidate.json` | 2026-09-09T13:06:41+08:00 | 2026-09-09T05:06:41Z | 2026-09-09 | 39 PASS / 2 NE | **true** |

`startedAt` 2026-09-09T13:00:34+08:00 (2026-09-09T05:00:34Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL. `knownRed: {}`,
`staleKnownRedDeclarations: []`, `pageErrors: null`, `offPageInk.worst: 0`,
`recoveryPairing.held: true`.
`candidateCutover.pageSha256` = `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
`pinBefore` `4a2710bba1ef07d9` → `pinAfter` `0fe25650bec1bac5`;
`servedShell.servedSha256` = `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`
on `e2/editor-shell-v2-bundle-v49.json` (declared `4f8494b6…`), `missing: []`,
`differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`.

The forty-first check reports `clausesExercised: ["C1", "C2", "C3"]` —
`geometry: "present"`, 24 paragraphs carried and 24 placed, `docOffsetTop: 0`
against a 929px canvas, focused node `a11y-node-7` band 259..279 overlapping the
caret band 250..266. C3 is exercised on a counted run for the first time; before
the relink it was inert on every profile and the amendment forbade quoting a
green run for it.

`check_usable_editor.py --report soak-run-09-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v13"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run09.json`, never
into this directory.

Desktop: one Chrome instance before and after (the owner's, browser main
211853, crashpad handler 211863), no headless Chrome and no
`serve_candidate_page.py` left behind. Nothing was killed.

Counting: **1 of 12**. The judge immediately after this run, with the six
superseded runs still in the directory:

```json
"cleanRuns": 1, "totalRuns": 7,
"clauses": {"every-run-clean": false, "one-page-sha": false,
            "count-reached": false, "day-spread": false, ...}
```

Each of the six fails on exactly the four clauses the move predicts —
`reconciled-profile`, `pass-count`, `page-sha`, `one-served-shell` — which is
the criterion doing its work, not a new defect. They are moved out in the next
section.

## Runs 03–08 moved out — the candidate is `e2-editor-v13` and the predicate is 39 PASS (2026-09-09)

The six clean runs recorded above under "Run 3" through "Run 08" have been
moved, with `git mv` and unchanged, to

    ../queue-v12-cutover-soak-void-9b29e39b/soak-run-03-candidate.json
    ../queue-v12-cutover-soak-void-9b29e39b/soak-run-04-candidate.json
    ../queue-v12-cutover-soak-void-9b29e39b/soak-run-05-candidate.json
    ../queue-v12-cutover-soak-void-9b29e39b/soak-run-06-candidate.json
    ../queue-v12-cutover-soak-void-9b29e39b/soak-run-07-candidate.json
    ../queue-v12-cutover-soak-void-9b29e39b/soak-run-08-candidate.json

with a `WHY-THESE-ARE-VOID.md` beside them, modelled on
`../queue-v12-cutover-soak-void-pre-r1/`. The directory is named for the page
they were taken on, following `-void-3dfdcfef` and `-void-20f09cc9`.

**Authority.** The owner's **D-c** ruling on finding 093 (`ed1ea02a`,
2026-09-08) restarted the count at zero by adjudication — and finding 093
records that the restart was *not* mechanically forced. Two mechanisms have
since made the same answer checkable: the relink minted `e2-editor-v13` and
moved the page to `31787584…` and the served shell to `ea69984c…`; and the
2026-09-08 amendment's forty-first check moved the clean composition to 39 PASS
/ 2 NE. Each of the six fails on exactly `reconciled-profile`, `pass-count`,
`page-sha` and `one-served-shell` — and on nothing else. §6.3 of
`handoff/RUNBOOK-operator-093-engine-geometry.md` requires that a voided run
physically leave the counting directory, because the judge enumerates by glob.

**Order, and why it is this way round.** The move follows run 09 rather than
preceding it. `check_soak_bank.py --self-test` builds its fixtures from live
bank reports the judge itself calls clean and refuses to run when there are
none; with the constants moved and nothing new banked it exited 1
(`self-test has no clean report to build from`), and run 09 restored it. An
empty bank would have left the tree holding a judge that could not prove it can
say no.

**Nothing else changed.** `tools/check_soak_bank.py` is untouched by this move
(its constants moved in the earlier commit, before run 09, which is the order
the amendment requires); no criterion text is relaxed; the surviving run is
**not** renumbered to 01, and the next run is 10; no run was re-executed. The
six `check_usable_editor.py` reconciliations for runs 03–08 stay in
`../queue-v12-cutover-soak-checklists/` (nothing globs that directory and the
RUNS.md sections above cite them in place); the three `diagnostic-*.json` and
the four `VERDICT-*.json` stay here. The reasoning for each is in the WHY file.

**The judge, before the move** (`cd wasm_sdk_probe && python3
tools/check_soak_bank.py`; full output in
`../queue-v12-cutover-soak-void-9b29e39b/JUDGE-OUTPUT-before-the-move.txt`):

```json
"cleanRuns": 1, "totalRuns": 7,
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": false, "count-reached": false,
            "one-page-sha": false, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

**The judge, after the move** (full output in
`../queue-v12-cutover-soak-void-9b29e39b/JUDGE-OUTPUT-after-the-move.txt`):

```json
"cleanRuns": 1, "totalRuns": 1,
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": true, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

`distinctPageSha256` is now the single value `31787584…` and
`distinctServedShellSha256` the single value `ea69984c…`;
`unclassifiedFiles: []`; the three `diagnostic-*.json` are listed under
`conditionTwoFiles_NOT_JUDGED_HERE` and the four `VERDICT-*.json` under
`verdictFiles_NOT_EVIDENCE`, judged by neither clause.
`check_soak_bank.py --self-test` exits 0 both before and after the move: twelve
red cases red, the green control green.

Counting: **1 of 12**, one UTC day (2026-09-09) with one run on it — no
qualifying day yet, since the clause wants ≥2 per day on ≥3 days. Earliest
close is UTC 2026-09-11, and only if the remaining eleven land 2+ on each of
two further UTC days.

## Run 10 — clean, `e2-editor-v13` (2026-09-09)

Same recipe as run 09.

```
make test-e2-c-static                       # exit 0, immediately before
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 --out soak-run-10-candidate.json
python3 tools/check_usable_editor.py --report soak-run-10-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run10.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-10-candidate.json` | 2026-09-09T13:23:41+08:00 | 2026-09-09T05:23:41Z | 2026-09-09 | 39 PASS / 2 NE | **true** |

`startedAt` 2026-09-09T13:17:35+08:00 (2026-09-09T05:17:35Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL. `knownRed: {}`,
`staleKnownRedDeclarations: []`, `pageErrors: null`, `offPageInk.worst: 0`,
`recoveryPairing.held: true`.
`candidateCutover.pageSha256` = `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
`pinBefore` `4a2710bba1ef07d9` → `pinAfter` `0fe25650bec1bac5`;
`servedShell.servedSha256` = `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`
on `e2/editor-shell-v2-bundle-v49.json` (declared `4f8494b6…`), `missing: []`,
`differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`.

`check_usable_editor.py --report soak-run-10-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v13"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run10.json`, never
into this directory.

Desktop: one Chrome instance before and after (the owner's, browser main
211853, crashpad handler 211863 — the same pids run 09 recorded, i.e. nothing
new was spawned), no headless Chrome and no `serve_candidate_page.py` left
behind. Nothing was killed.

Counting: **2 of 12**, one UTC day (2026-09-09) with two runs on it — the
first day now qualifies (≥2 runs), with two more qualifying UTC days still
needed.

## Run 11 — clean, `e2-editor-v13` (2026-09-09)

Same recipe as runs 09–10.

```
make test-e2-c-static                       # exit 0, immediately before
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 --out soak-run-11-candidate.json
python3 tools/check_usable_editor.py --report soak-run-11-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run11.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-11-candidate.json` | 2026-09-09T13:31:12+08:00 | 2026-09-09T05:31:12Z | 2026-09-09 | 39 PASS / 2 NE | **true** |

`startedAt` 2026-09-09T13:25:03+08:00 (2026-09-09T05:25:03Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL. `knownRed: {}`,
`staleKnownRedDeclarations: []`, `pageErrors: null`, `offPageInk.worst: 0`,
`recoveryPairing.held: true`.
`candidateCutover.pageSha256` = `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
`pinBefore` `4a2710bba1ef07d9` → `pinAfter` `0fe25650bec1bac5`;
`servedShell.servedSha256` = `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`
on `e2/editor-shell-v2-bundle-v49.json` (declared `4f8494b6…`), `missing: []`,
`differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`.

`check_usable_editor.py --report soak-run-11-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v13"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run11.json`, never
into this directory.

Desktop: one Chrome instance before and after (the owner's, browser main
211853, crashpad handler 211863 — unchanged since run 09), no headless Chrome
and no `serve_candidate_page.py` left behind. Nothing was killed.

Counting: **3 of 12**, one UTC day (2026-09-09) with three runs on it. Per
`tools/check_soak_bank.py`, immediately after this run:

```json
"cleanRuns": 3, "totalRuns": 3,
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": true, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

Job 1 for this session ends here: `cleanRuns: 3, totalRuns: 3,
every-run-clean: true`, one UTC day (2026-09-09) holding all three, so it
qualifies (≥2 runs) but the day-spread clause still needs ≥3 distinct
qualifying UTC days. `count-reached: false`, `ok: false`, as expected — twelve
runs are not banked yet and the schedule continues on later UTC days.

## Run 12 — clean, `e2-editor-v13` (2026-09-09)

Same recipe as runs 09–11.

```
make test-e2-c-static                       # exit 0, immediately before
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 --out soak-run-12-candidate.json
python3 tools/check_usable_editor.py --report soak-run-12-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run12.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-12-candidate.json` | 2026-09-09T14:30:50+08:00 | 2026-09-09T06:30:50Z | 2026-09-09 | 39 PASS / 2 NE | **true** |

`startedAt` 2026-09-09T14:24:42+08:00 (2026-09-09T06:24:42Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL. `knownRed: {}`,
`staleKnownRedDeclarations: []`, `pageErrors: null`, `offPageInk.worst: 0`,
`recoveryPairing.held: true`.
`candidateCutover.pageSha256` = `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
`pinBefore` `4a2710bba1ef07d9` → `pinAfter` `0fe25650bec1bac5`;
`servedShell.servedSha256` = `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`
on `e2/editor-shell-v2-bundle-v49.json` (declared `4f8494b6…`), `missing: []`,
`differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`.

The forty-first check reports `clausesExercised: ["C1", "C2", "C3"]` —
`geometry: "present"`, 24 paragraphs carried and 24 placed, `docOffsetTop: 0`
against a 929px canvas, focused node `a11y-node-7` band 259..279 overlapping
the caret band 250..266 — identical shape to run 09.

`check_usable_editor.py --report soak-run-12-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v13"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run12.json`, never
into this directory.

Desktop: one Chrome instance before and after (the owner's, browser main
211853, crashpad handler 211863 — unchanged since run 09), no headless Chrome
and no `serve_candidate_page.py` left behind. Nothing was killed.

Counting: **4 of 12**, one UTC day (2026-09-09) with four runs on it. Per
`tools/check_soak_bank.py`, immediately after this run:

```json
"cleanRuns": 4, "totalRuns": 4,
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": true, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

Still `count-reached: false` and `day-spread: false` as expected — one
qualifying UTC day (2026-09-09), two more still needed.

## Run 13 — clean, `e2-editor-v13` (2026-09-09)

Same recipe as runs 09–12.

```
make test-e2-c-static                       # exit 0, immediately before
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 --out soak-run-13-candidate.json
python3 tools/check_usable_editor.py --report soak-run-13-candidate.json \
    --output ../queue-v12-cutover-soak-checklists/check-usable-editor-run13.json
```

`make test-e2-c-static` exit 0 immediately before this run, per finding 090's
manual rule.

| run | completedAt (local) | completedAt (UTC) | UTC day | composition | run `ok` |
|---|---|---|---|---|---|
| `soak-run-13-candidate.json` | 2026-09-09T14:38:45+08:00 | 2026-09-09T06:38:45Z | 2026-09-09 | 39 PASS / 2 NE | **true** |

`startedAt` 2026-09-09T14:32:39+08:00 (2026-09-09T06:32:39Z). `complete: true`.
NE set exactly `{a-refused-action-is-reported-and-changes-nothing,
notice-action-recovers-the-session}`, no FAIL. `knownRed: {}`,
`staleKnownRedDeclarations: []`, `pageErrors: null`, `offPageInk.worst: 0`,
`recoveryPairing.held: true`.
`candidateCutover.pageSha256` = `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
`pinBefore` `4a2710bba1ef07d9` → `pinAfter` `0fe25650bec1bac5`;
`servedShell.servedSha256` = `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`
on `e2/editor-shell-v2-bundle-v49.json` (declared `4f8494b6…`), `missing: []`,
`differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`.

The forty-first check reports `clausesExercised: ["C1", "C2", "C3"]` —
`geometry: "present"`, 24 paragraphs carried and 24 placed, `docOffsetTop: 0`
against a 929px canvas, focused node `a11y-node-7` band 259..279 overlapping
the caret band 250..266 — identical shape to runs 09 and 12.

`check_usable_editor.py --report soak-run-13-candidate.json`: `"ok": true`,
`reconciledFor.kind == "candidate-cutover"`, `profile == "e2-editor-v13"`,
`problems: []`. Saved to
`../queue-v12-cutover-soak-checklists/check-usable-editor-run13.json`, never
into this directory.

Desktop: one Chrome instance before and after (the owner's, browser main
211853, crashpad handler 211863 — unchanged since run 09), no headless Chrome
and no `serve_candidate_page.py` left behind. Nothing was killed.

Counting: **5 of 12**, one UTC day (2026-09-09) with five runs on it. Per
`tools/check_soak_bank.py`, immediately after this run:

```json
"cleanRuns": 5, "totalRuns": 5,
"clauses": {"no-unclassified-file": true, "declared-non-runs-present": true,
            "every-run-clean": true, "count-reached": false,
            "one-page-sha": true, "no-naive-timestamp": true,
            "day-spread": false},
"ok": false
```

Still `count-reached: false` and `day-spread: false` as expected — one
qualifying UTC day (2026-09-09), two more still needed.

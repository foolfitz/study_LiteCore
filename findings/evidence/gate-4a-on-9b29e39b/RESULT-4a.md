# Condition 4a, re-taken on page `9b29e39b…` (shell generation v48)

**2026-09-07.** Seven of eight terms pass; term 6 could not be taken — recorded
below, not fixed. Task T2 of
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`.

This directory exists because the candidate page moved twice more since
`gate-4a-on-20f09cc9/` (finding 088's second fix, then the T1d/T1d-correction
split into v47/v48 — see
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "The page is final").
The previous take is left where it is, unedited and unmoved.

Commands, unchanged from `gate-4a-on-20f09cc9/RESULT-4a.md`:

```
python3 tools/probe_aria_projection.py --browser chrome \
    --candidate-profile e2-editor-v12 --out candidate-v12-run{1,2,3}.json
python3 tools/probe_aria_projection.py --browser chrome \
    --candidate-profile e2-editor-v8  --out control-v8.json
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --mutate projection-not-wired \
    --out term-6-mutation-projection-not-wired.json
python3 tools/check_4a.py --candidate candidate-v12-run{1,2,3}.json \
    --control control-v8.json \
    --expect-page-sha256 9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c \
    --out verdict-4a.json
```

## The seven terms `check_4a.py` judges — all pass

| term | verdict |
|---|---|
| **1 identity** | all three runs `pageSha256` **`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`**, profile `e2-editor-v12`, `shim: null`. |
| **2 text** | 9 of 9 fixture paragraphs found in `getFullAXTree`, `missing: []`, on each of the three runs. |
| **3 structure** | 1 heading node, AX `level: 1`, matching the ODT `outline-level: 1`; 2 `list` containers, 4 `listitem` nodes. Identical on all three runs. |
| **4 focus follows the caret** | 3 placements, 3 readings, 3 distinct, `matchedTheParagraphAimedAt: 3`, `established: true`, on all three runs. |
| **5 repetition** | 3 runs, `distinctSignatures: 1`. |
| **7 delta** | control `e2-editor-v8`: `documentTextInTree: false`, region `reason: "profile"`, `offers: "0"`, text 「這一版引擎沒有提供段落文字，所以無法朗讀文件內容。」 — same sentence as the `20f09cc9…` take. |
| **8 structure on the caret path** | the heading placement's focused node carries `role: heading`, `level: 1`; the other two carry no role, matching the fixture. `established: true` on all nine rows. |

`verdict-4a.json`: `"ok": true` over these seven terms.

## Term 6 — the mutation could not be applied on this page, and that is recorded rather than worked around

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --mutate projection-not-wired \
    --out term-6-mutation-projection-not-wired.json
```

exited with no report written and this message on stderr:

```
mutation 'projection-not-wired' expects exactly one occurrence of its pattern
in dist/e2-editor-app.js, found 0.  The tree moved under the mutation; fix the
pattern rather than the count.
```

The mutation's fixed string pattern was written against the pre-v46 source
(`structureSpeaks === text`). The v46 hunk that landed with this page changed
that comparison to `structureSpeaks !== null`
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "T1c: v46 measures
better"), so the pattern no longer matches anywhere in `dist/e2-editor-app.js`.
**`web/e2-editor-app.js` and `dist/e2-editor-app.js` were verified unchanged**
by the attempt — both `df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143`
before and after, and `git status --short` shows nothing touched under
`wasm_sdk_probe/` — the tool raised before writing anything to the tree or to
the output path.

This is a red result of running the recorded procedure, not an ambiguity in
what to run: the command is exactly the one `gate-4a-on-20f09cc9/` used and
`check_4a.py --help` unchanged. Per this task's role, the mutation's pattern is
not edited here. **Term 6 is un-measured on `9b29e39b…`** until the pattern is
updated to match the current source — a decision for whoever owns
`run_e2_c_product_path.py`'s `MUTATIONS` table, not for this gate-operation
pass.

## A related red already on record from this task's item 1

Soak runs 1 and 2 on this same page (`findings/evidence/queue-v12-cutover-soak/RUNS.md`,
section "Re-taken on `9b29e39b…` / v48") both FAILed on
`the-document-region-says-why-it-is-empty` — the exact check term 6's mutation
targets — on an **unmutated** run, 2 of 2. `check_4a.py`'s seven terms above do
not exercise that check (4a reads the AX tree and the live region's content
directly, not this runner's check list), so the two results are independent
measurements that happen to point at the same mechanism. Neither is
adjudicated here; both are on record for whoever picks this up next.

## The judge's red cases

Not re-derived here, per the 2026-09-06 take's own note: the corrected judge's
red cases were exhibited before it landed, over held records, in
`../gate-4a-reading-rule/`. This directory is what the seven terms say about
this page.

## Term 6 re-anchored, and measured on `9b29e39b…` for the first time (2026-09-07)

Item B of the T2 follow-up (`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`,
"T2 came back red; the schedule is stopped", R-3). The mutation's `find`
pattern in `tools/run_e2_c_product_path.py`'s `MUTATIONS["projection-not-wired"]`
was re-anchored from the pre-v46 call site
(`  projectFocusedParagraph(snapshot);\n`, 0 occurrences in the current
`dist/e2-editor-app.js`) to the current one
(`  projectFocusedParagraph(snapshot, structureSpeaks);\n`, exactly one
occurrence) — the v45 hunk (`78f1cb3a`, finding 088's residue fix) gave the
function a second parameter and changed the call site to pass it; the v46 hunk
(`000a57e2`/`2d319677`) did not touch this line again. Same "check" and
"reintroduces" fields: deleting the call still un-wires the live-region
projection entirely, which is the same semantic mutation the pre-088 pattern
expressed.

Static proof first: `python3 -m unittest tests.test_product_path_mutations`
(10 tests, including `test_every_mutation_matches_its_target_exactly_once`)
passes on the re-anchored table.

Then the red case, run for real on the candidate path:

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --mutate projection-not-wired \
    --out term-6-mutation-projection-not-wired.json
```

`complete: true`, `ok: true` (the run-level flag; it does not mean every check
passed — see below), 40 checks. Composition: **37 PASS / 2 NOT_ESTABLISHED
(`notice-action-recovers-the-session`, `a-refused-action-is-reported-and-changes-nothing`,
the same two the soak bank already expects) / 1 FAIL**, and the FAIL is
exactly `the-document-region-says-why-it-is-empty` — `mustGoRed` in
`mutationDetail` — and nothing else. This mutation reddens exactly the
projection term and no other term, on the first run against this page.

**Restoration verified by sha256, not assumed**: `web/e2-editor-app.js` and
`dist/e2-editor-app.js` are both `df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143`
after the run — unchanged from before it — because `apply_mutation` builds the
mutated copy in a scratch mirror and never writes `dist/` itself. This
mutation record is stamped (`term-6-mutation-projection-not-wired.json`,
labelled by its own `mutation` field) and is **not** banked into
`queue-v12-cutover-soak/`: it is evidence that the check can go red, not a
counted run.

**Re-run of `check_4a.py` for the full eight terms**, existing three candidate
runs (`candidate-v12-run{1,2,3}.json`) and the existing control
(`control-v8.json`) unchanged, output
`verdict-4a-2026-09-07-r3-recheck.json`: terms 1, 2, 3, 4, 5, 7, 8 all
`"ok": true`, identical to the verdict above — this re-anchor touched no
product file, so nothing about those seven terms could move. **Term 6 is
measured on `9b29e39b…` for the first time tonight** (it could not be applied
at all in the take above) and is now MET: the mutation reddens the check it
targets and nothing else.

`make test-e2-c-static` (run from `wasm_sdk_probe/`): **exit 0**. This is the
same target that exited 2 on the committed tree before this fix
(`AssertionError: 0 != 1 : projection-not-wired expects one occurrence of its
pattern in dist/e2-editor-app.js and found 0`, recorded in
`../queue-v12-cutover-revert-rehearsal/RESULT-2026-09-07-revert-condition-3-discharged-on-9b29e39b.md`).

**Not resolved by this item, and not this item's role to resolve**: the
mutation's target check, `the-document-region-says-why-it-is-empty`, is the
same check that FAILed unmutated on soak runs 1 and 2 (R-1, recorded above and
in `../queue-v12-cutover-soak/RUNS.md`). This item only re-earns the
mutation's ability to prove the check CAN go red; it says nothing about
whether the check's oracle is the right one to hold open the gate on an
unmutated run. See finding 092.

## Term 6, re-taken against a GREEN baseline: MET, and 4a is 8 of 8 (2026-09-07)

Item 3 of T5b (`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`), under
the amendment "the region check verifies the claim, not the node"
(`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`). The paragraph above
("The follow-up landed, with one downgrade") recorded term 6 as
NOT_ESTABLISHED because the previous mutation run's composition (37/2/1) was
identical to the unmutated baseline's — the check was red **before** the
mutation, so nothing about the run showed the mutation could cause a red
that would not otherwise be there. That defect is fixed here by comparing
against a run where the check is not red to begin with.

**The baseline it is compared against**:
`findings/evidence/queue-v12-cutover-soak/soak-run-03-candidate.json`
(`pageSha256` / `candidateCutover.pageSha256`
`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`,
`servedShell.servedSha256`
`cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4` — v47,
the same served shell as every other record in this directory).
**38 PASS / 2 NOT_ESTABLISHED, no FAIL.**
`the-document-region-says-why-it-is-empty` on that run:

```json
{"present": true, "text": "", "reason": "paragraph", "offers": "1",
 "deferredToStructure": "1", "activeDescendant": "a11y-node-7",
 "structureText": "MKBOLDONCARETFOLLOW0CARETFOLLOW1CARETFOLLOW2"}
```

`outcome: "PASS"` — the deferral clause the amendment added is satisfied by
the page's own real behaviour (a legitimate deferral: `reason == "paragraph"`,
`offers == "1"`, non-empty `structureText`), not by a predicate that cannot
fail. This is the "green to begin with" precondition term 6 needs.

**The mutation run**, from T5b item 1
(`findings/evidence/gate-4a-on-9b29e39b/term-6-mutation-projection-not-wired-post-amendment.json`,
same command as every earlier take:
`--browser chrome --candidate-profile e2-editor-v12 --mutate
projection-not-wired`): 40 checks, **37 PASS / 2 NOT_ESTABLISHED (the same
fixed pair) / 1 FAIL**, and the FAIL set is exactly
`{the-document-region-says-why-it-is-empty}` — `mustGoRed` in
`mutationDetail`, and `MUTATIONS["projection-not-wired"]["alsoRed"]` is `[]`
in the current table, so "nothing outside its declared `alsoRed`" holds by
construction (the FAIL set equals `{check} ∪ alsoRed` exactly). Restoration
verified: `web/e2-editor-app.js` and `dist/e2-editor-app.js` both
`df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143` after the
run, unchanged from before it.

**Term 6 is therefore MET** under this task's stated condition: the mutation
reddens exactly the target check while the unmutated baseline is green on it.
This is a different baseline than the take above compared against implicitly
(that take had no green baseline to compare to at all); the causal claim —
the instrument can fail here, and it is the mutation causing it, not a
pre-existing red — is now supported.

**Re-run of `check_4a.py` for the full eight terms**, same three candidate
runs (`candidate-v12-run{1,2,3}.json`) and the same control (`control-v8.json`)
— unchanged since neither the amendment nor T5b touched the AX-tree reads —
output `verdict-4a-2026-09-07-t5b-recheck.json`: terms 1, 2, 3, 4, 5, 7, 8 all
`"ok": true`, identical to every earlier take of these seven terms (they read
the AX tree and the live region's raw text/reason/offers, not the
`deferredToStructure`/`structureText` fields the amendment added, so the
predicate change could not move them). Combined with term 6 above:

**Gate condition 4a is 8 of 8 on `9b29e39b…` / shell v48, for the first time.**

`make test-e2-c-static` (run from `wasm_sdk_probe/`, immediately before the
mutation run above): **exit 0**.

# Condition 4a, re-earned on `31787584…` — 8 of 8

**2026-09-09.** Candidate profile `e2-editor-v13` (finding 093 option B, linked
today). All eight terms MET, each on records taken on this page, on this
session's tree, with `git status --short` clean apart from this directory.

The `9b29e39b…` take (`../gate-4a-on-9b29e39b/RESULT-4a.md`) is the immediately
preceding one. That page died when the relink moved the candidate identity to
`e2-editor-v13`; everything bound to it is void by the identity terms that were
already written, so 4a is re-earned here rather than carried forward. The
earlier take is left where it is, unedited and unmoved.

## Identity

| | |
|---|---|
| candidate profile | `e2-editor-v13` |
| candidate page | `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a` |
| shipped page (control, and the tree's own entrypoint) | `1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc` |
| served shell | `e2/editor-shell-v2-bundle-v49.json` |
| pins | before `4a2710bba1ef07d9`, after `0fe25650bec1bac5` |

`python3 tools/build_cutover_page.py --profile e2-editor-v13` (no `--write`,
nothing written) prints `pageSha256 31787584…` — the same value the three
records below carry and the same value `tools/check_soak_bank.py`'s
`DEFAULT_SHA` pins. **The shipping page was not repointed at any moment of this
pass**; it is still `1ec7baf9…`, still `e2-editor-v8`.

## Commands, unchanged from `../gate-4a-on-9b29e39b/RESULT-4a.md`

```
python3 tools/probe_aria_projection.py --browser chrome \
    --candidate-profile e2-editor-v13 --out candidate-v13-run{1,2,3}.json
python3 tools/probe_aria_projection.py --browser chrome \
    --candidate-profile e2-editor-v8  --out control-v8.json
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 --mutate projection-not-wired \
    --out term-6-mutation-projection-not-wired.json
python3 tools/check_4a.py --candidate candidate-v13-run{1,2,3}.json \
    --control control-v8.json \
    --expect-page-sha256 31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a \
    --out verdict-4a.json
```

`make test-e2-c-static` exit **0** immediately before the first measurement,
and exit **0** again at the end of the session (finding 090's manual rule).

## The seven terms `check_4a.py` judges — `verdict-4a.json` `"ok": true`

| term | verdict |
|---|---|
| **1 identity** | all three runs `kind: candidate`, profile `e2-editor-v13`, `shim: null`, `pageSha256` **`31787584…`**, equal to the expected sha passed on the command line. |
| **2 text** | 9 of 9 fixture paragraphs found in `getFullAXTree`, `missing: []`, on each of the three runs. |
| **3 structure** | 1 heading node, AX `level: 1`, matching the ODT `outline-level: 1`; 2 `list` containers, 4 `listitem` nodes. Identical on all three runs. |
| **4 focus follows the caret** | 3 placements, 3 readings, 3 distinct, `matchedTheParagraphAimedAt: 3`, `established: true`, on all three runs. Readings, in placement order: `E1-LC-HEADING`, `E1-LC-ISOLATED 前後都不是清單的段落`, `E1-LC-SPACER` — each compared in code against fixture paragraph *i* per Ruling 2 of the 2026-09-05 amendment, with `bandsFound: 9` on every record. |
| **5 repetition** | 3 runs, `distinctSignatures: 1`. |
| **7 delta** | control `e2-editor-v8`: `documentTextInTree: false`, region `reason: "profile"`, `offers: "0"`, text 「這一版引擎沒有提供段落文字，所以無法朗讀文件內容。」 — the same sentence as the `9b29e39b…` and `20f09cc9…` takes. Candidate side `documentTextInTree: true` on all three runs, so the delta discriminates rather than merely reporting. |
| **8 structure on the caret path** | placement 0's focused node carries `role: heading`, `level: 1`; placements 1 and 2 carry no role, matching the fixture. `established: true`, `axFocused: true`, `activeDescendantRef` `a11y-node-0/1/2` on all nine rows. |

## Term 6 — the mutation, taken against a baseline verified GREEN first

**This is the trap that cost half a day on 2026-09-07 and it was checked
before the mutation was run, not after.** If
`the-document-region-says-why-it-is-empty` is already red on an unmutated run
of this page, the mutation run's composition equals the baseline's and the run
proves nothing about causation.

**The baseline, on this exact page, three independent records:**

| baseline record | page | composition | `the-document-region-says-why-it-is-empty` |
|---|---|---|---|
| `../queue-v12-cutover-soak/soak-run-09-candidate.json` | `31787584…` | 39 PASS / 2 NE / **0 FAIL** | **PASS** |
| `../queue-v12-cutover-soak/soak-run-10-candidate.json` | `31787584…` | 39 PASS / 2 NE / **0 FAIL** | **PASS** |
| `../queue-v12-cutover-soak/soak-run-11-candidate.json` | `31787584…` | 39 PASS / 2 NE / **0 FAIL** | **PASS** |

Green 3 of 3. The precondition holds.

**The mutation run** (`term-6-mutation-projection-not-wired.json`): 41 checks,
`complete: true`, **38 PASS / 2 NOT_ESTABLISHED / 1 FAIL**, and the FAIL set is
exactly

```
{the-document-region-says-why-it-is-empty}
```

which is `mutationDetail.mustGoRed`, and `MUTATIONS["projection-not-wired"]`
carries `alsoRed: []`, so "the FAIL set equals `{check} ∪ alsoRed` exactly"
holds by construction. The NE set is the same fixed pair as every clean run
(`notice-action-recovers-the-session`,
`a-refused-action-is-reported-and-changes-nothing`). Verdict string:
*"the mutation was detected by the check that owns it"*.

Against the 39/2/0 baseline that is **one check moving from PASS to FAIL and
nothing else moving** — 39 PASS → 38 PASS, NE unchanged, one FAIL where there
were none. **Term 6 is MET.**

`mutationDetail` note: the mutation's own record reports
`candidateCutover.pageSha256` `beeb3b463a5e5dac989e4cdd78202b2682678c865b607114a7c158c6b8fef8a6`,
not `31787584…`. That is expected and is not an identity failure — the
mutation deletes a line from the page, so the mirrored page's digest must
differ; a mutation run that still hashed to `31787584…` would mean the mutation
had not been applied. Term 1's identity claim is carried by the three unmutated
candidate records, which is where `check_4a.py` reads it.

**Restoration verified by sha256, not assumed**: `web/e2-editor-app.js` and
`dist/e2-editor-app.js` were both
`1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc` before the
mutation run and both still `1ec7baf9…` after it — `apply_mutation` builds the
mutated copy in a scratch mirror and never writes `dist/`. `git status --short`
after the run shows only this untracked evidence directory.

## Were any of the other terms "already red before the change"?

Asked of every term, not only term 6. Terms 1–5, 7 and 8 are **not** red-case
terms: they are direct assertions over three candidate records and one control,
so there is no mutation whose effect could be confounded by a pre-existing red.
The one term with a differential shape is **term 7**, and its two sides are
measured to differ in the direction the term claims — candidate
`documentTextInTree: true`, control `false` — so the control is not "already
red" in a way that would make the delta vacuous; it is the absence the delta
exists to name.

## Not done here, and why

**No ninth term was added for the forty-first check**
(`the-projection-is-placed-where-the-document-is`, the 2026-09-08 amendment).
AGENTS.md §9's first condition — prior to satisfaction — closed for this gate
when the count left zero this morning (run 09, banked). A term asserting 4a
covers the projection's placement is therefore **a work item, not a gate
term**, and is registered as such rather than landed. 4a as it stands says
nothing about where the projection sits; the forty-first check in the product
net does, and it is a PASS on all three banked runs.

## Chrome census

One Chrome instance before and after every one of the five browser
measurements — the owner's (browser main 211853, crashpad handler 211863,
~30 children), unchanged throughout. No headless Chrome and no
`serve_candidate_page.py` left behind at any census. Nothing was killed.

## One surprise, recorded rather than smoothed

`probe_aria_projection.py`'s records carry **no `startedAt` / `completedAt`**.
The 2026-09-03 wall-clock ruling added those fields to
`run_e2_c_product_path.py`, and this probe was never brought along. It does not
affect 4a — 4a has no calendar-day clause, and its records are identified by
`pageSha256` — but it means a 4a record cannot be placed in time from its own
contents, only from the file's mtime and this document. Registered as a work
item, not fixed here.

# J-red: the v24 S5 reader's red cases, and red case (v) for T2 and T3

Spec `specs/SPEC-M3-link-batch-v24.md` §6.1 J-red (red cases (ii), (iii), (v)); default if not done or red: the reader may not judge v24. Run before the reader judged any v24 page (no v24 S5 page existed when this ran). No browser.

## The reader under test

`wasm_sdk_probe/tools/judge_v24_feature_selection.py` (new). It runs v23's reader functions as **their own code objects** re-bound to a namespace in which exactly three names are v24's — `PROFILE`, `Evidence` (v23's class, `__init__` and `opened` re-bound) and `readiness` (v23's text with the one payload line now carrying `route: "uno-insert-text"`). `tests/test_v24_feature_selection_judge.py` checks those identities (4/4). New code is only `t2()` and the `inspect_s5` wrapper that reads T2 on the raw request/response streams **before** anything else, so a page whose typing took the wrong route FAILs naming the route even when nothing else about it can be judged. T2's clauses carry the tags `# T2-route` (request route, reply method, any `method: "paste"` reply) and `# T2-proof` (a refused reply, a missing `completion`).

## Cases (`tools/jred_v24.py`, inputs read through the v24 plan)

Inputs: two v23 counted-02 pages from their tracked `.json.gz`, each checked against `s5-counted-02/report.json` — `chrome-shift-Down@caret-mid/type` (PASS in counted-02) as the base for the synthetic cases, and `chrome-shift-Right@cell-end/type` (finding 168's stop) for (iii).

| Case | Page | Real reader | Without `# T2-route` (3 lines) | Without `# T2-proof` (2 lines) |
|---|---|---|---|---|
| (ii-a) | base rewritten to the v24 wire shape, then the `s5cand` `x` reply replaced by the engine's proof-absent error (`MUTATION_OUTCOME_UNKNOWN`, `proof-absent-at-poll:UNO_COMMAND_RESULT`) | **FAIL**, proof | FAIL, proof | not FAIL (NE: v23 profile) |
| (ii-b) | same, `x` reply `ok` with `method: "uno-insert-text"` and no `completion` | **FAIL**, proof | FAIL, proof | not FAIL |
| (ii-c) | same rewrite, every reply proper (control) | T2 holds (overall NE: v23 profile) | same | same |
| (iii) | counted-02's shift-Right@cell-end/type as it is | **FAIL**, route and proof: `request route None`, `reply method 'paste'`, `reply completion None` | FAIL, proof only (route no longer named) | FAIL, route only |
| (iii′) | that page with `completion` added to every insertText reply: only the route is wrong | **FAIL**, route | not FAIL | FAIL, route |

**A finding about (iii) itself, and why (iii′) exists.** A real paste-route page lacks both the route and the proof, so (iii) is caught by both clauses, and removing the route clause alone leaves it red. By the spec's own test ("拿掉後紅案仍紅，代表紅另有原因，該守衛沒被測到") (iii) therefore cannot show that the route clause works. (iii′) is the route-only red; with it every guard has a red case that turns green exactly when that guard, and only that guard, is removed. (iii) still checks what the spec asks of it: FAIL with the reason naming the route.

**T3 (v)** (`run-01/t3-v/`): T3's set-equality line (`assert.deepEqual(...)` in `tests/v24-typed-insert-sdk.test.mjs`) removed in a scratch copy (sha256 `29d59365…`). Red case (iv)'s scratch input is rebuilt and checked byte-equal to `pre-link/t3-red/fake.diff`. Real test on (iv): exit 1. Guardless copy: on (iv) exit 0 (the equality clause is what made (iv) red), on the real `input/` exit 0, on an empty directory exit 1 (non-vacuity is a separate clause and still bites). Each run is checked to have executed exactly the one T3 test, since a name pattern that matches nothing also exits 0.

## Result

`run-01/` (2026-10-28 11:21 +0800): 36 checks, all ok, `RED_CASES_HOLD`, exit 0 (`run-01.stdout.txt`, `run-01.exit.txt`; `j-red.json` has every verdict and reason; both mutants are kept beside it, real reader sha256 `4531716b…`). The reader may judge v24 S5 pages.

What J-red does not cover: T1 (the S5 comparison) is v23's code object unchanged and keeps v23's record; the readiness line is covered by the identity test, not by a red case here.

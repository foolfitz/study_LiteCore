# SPEC-M3-select-all-v26 evidence

Spec: `specs/SPEC-M3-select-all-v26.md` (pinned `9f084bf06`). One directory per criterion.

| dir | criterion | state |
|---|---|---|
| `p1/` | 5.1 P1 profile identity | `P1_HOLDS` (dist and archive), red cases hold, v25 control red; fixed by execution once (see its README) |
| `u1/` | 5.2 U1 client and session | red before (6/7, the 7th is a regression guard that was already true), green after; session-list mutation turns exactly the two session tests red |
| `u2/` | 5.3 U2 page binding | red before 11/11 (the functions did not exist), green after 11/11 incl. two in-test source mutations (offer check, repeat check) |
| `u3/` | 5.5 U3 finding 174 presentation | red before on the three review cases, the three unchanged dispositions green before and after |
| `suite-after-page.txt` | the whole shell suite after the page change | 548/548 |

The three review sentences were compared by script between HEAD (`8c811bfb3`) and the changed page: each new
sentence equals the old one with its outer parentheses removed (3/3).

Harness fixes made while writing the tests (tests, not product): U1's omitted-manifest case first used
`undefined`, which a default parameter turned back into the grant (red for the wrong reason, fixed before the
witness was kept); `page-move-during-delete.test.mjs` assembles the whole keydown handler and needed the three
select-all helpers in scope (added with `optional`, so a generation-79 page restored for V0' still assembles); the
page comment first contained the literal `if (accel) return;`, which the wiring tests' `indexOf` matched before
the code (reworded).

Pre-existing reds, NOT caused here (both red at `9f084bf06`, checked in a scratch worktree):
`tests/test_e2_c_shell_bundle.py` `test_the_real_manifest_matches_the_real_tree` (reads the bundle tool's default
v76 manifest; v24/v25 workers already unlisted, the v26 worker joins them) and `tests/test_v23_c2_wrapper.py`
`test_literal_fixture_and_source_population` (expects the page to name the v22 worker).

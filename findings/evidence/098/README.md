# Evidence for findings 098 and 099

Both findings live in one file, `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js`,
and were fixed in one change (shell generation v52). The evidence for both is here;
`findings/evidence/099/README.md` points back to this file.

## 1. Unit level — `unit-selfcheck/`

The tests are in `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-session.test.mjs`
(section "finding 098" and "finding 099"). They drive the real session code against the
file's own fixture engine, which restarts revisions at zero on every open, as the engine
does (`src/probe_engine.cpp`, `gState.revision = 0` in open).

`selfcheck_unit_variants.py` serves the pre-fix session (`a7daa562`) with exact-text
replacements, beside the CURRENT test file, and records which tests go red.
Result (`selfcheck-2026-09-28.json`, 37 tests in the file):

| variant | pass | red |
| --- | --- | --- |
| pre-fix (`a7daa562`) | 31 | 098 minimal, 098 per-action, 098 shift, 099 grid, 099 revision sweep, 099 within-Worker |
| A only (moves are non-mutations) | 34 | 099 grid, 099 revision sweep, 099 within-Worker |
| C1 only (stamp guard, moves still mutations) | 31 | 096 holding-the-key, 098 minimal, 098 per-action, 098 shift, 099 grid, 099 revision sweep |
| A + C3 (guard 2 deleted) | 36 | 096 holding-the-key (the skipped counter) |
| **A + C1 (the landed fix)** | **37** | — |
| codex: A + C1 + skip on `revision + 1` | 35 | 099 grid, 099 revision sweep |
| opus V1: A + C1 + skip on `revision + 3` | 36 | 099 revision sweep |
| opus V2: no retry after a failed checkpoint save | 36 | 099 failed-save retry |
| opus V3: shift-move counted as a mutation | 36 | 098 shift |
| opus V4: revision guard kept in generation one | 35 | 099 within-Worker, 099 revision sweep |

Why "C1 only" also reds the 099 grid: without A a move bumps the stamp, so the second
move after the rollback banks again; the grid asserts it must not. "C1 only" passes the
within-Worker test, because the stamp does move on the review path.

The last five rows are wrong versions the two review seats built, each of which passed
every test in the file at the time. The tests that now catch them were added in
response: the grid (after codex; offsets −4..+2 only, so it did NOT catch V1), and
after opus the direct revision sweep (the guard asked at every `document.revision`
0..40 against a checkpoint banked at r20 — this is what pins "the skip does not read
the revision"), the within-Worker review-path scenario, the failed-save retry and the
shift-move test.

## 2. Browser level — `probe_098_a_caret_move_banks_a_checkpoint.py`

The user's path: the product's file input, a canvas pointerdown on a middle line, real
`ArrowRight` key events through CDP, the product's insert control. Mid-line so that no
press is a boundary press (the page pins `e2-editor-v8`, where a boundary press wedges —
finding 096). Two mirrors of `dist/` that differ only in the fix's two code lines; both
arms serve the same page (`e2-editor-app.js` sha256 `1ec7baf9fb53…`, pin
`4a2710bba1ef07d9`).

`red-case-v8-2026-09-28.json` (Chrome 151.0.7922.169, 3 attempts per arm):

| arm | `#s-checkpoint` after clean presses 1..5 | control (type, then one press) | outcome |
| --- | --- | --- | --- |
| unfixed | 無, 有（r0）, 有（r0）, 有（r0）, 有（r0） | 有（r1） | BANKED_ON_A_CLEAN_DOCUMENT 3/3 |
| fixed | 無, 無, 無, 無, 無 | 有（r1） | CLEAN_DOCUMENT_UNTOUCHED 3/3 |

Revision stayed `0` through every clean press in both arms and every press moved the
caret. In the unfixed arm press 2 took 0.61 s against 0.15 s for every other press —
the redundant checkpoint save is visible in the latency.

**Known limit of this run**: the fixed arm served the pre-fix file with the two code
lines swapped (`servedSessionSha256 6a1f1247…`), code-equivalent to the landed file
but not byte-identical (the landed file also rewrites comments). The field named
`treeSessionSha256` in that report is the hash of `dist/`'s copy at the time (the
pre-fix file), not of the source tree; the probe now records `distSessionSha256` and
`landedSessionSha256` separately.

**Rerun on the landed bytes** (`red-case-v8-2026-09-28-landed.json`, fixed arm only,
`--require-landed`, after `make e2-c-assets`): served session `191de3733589…` equals
the source tree's file (`servesLandedBytes: true`), pin `4a2710bba1ef07d9`.
CLEAN_DOCUMENT_UNTOUCHED 3/3 (無 on all five presses), control 有（r1） 3/3. This rerun
used the tightened predicate: "untouched" now requires exactly 無 on every press, not
"anything that does not start with 有" (a failed save renders 寫入失敗).

**What the page cannot show**: `dirty`. A fix that only guarded the checkpoint would
give the same labels; "a move is not a mutation" is pinned by the unit tests only.

**What this probe cannot see**: finding 099. It needs two induced deaths and a revision
coincidence; 099 is measured at unit level only.

## 3. Review seats

- `codex exec` (codex-cli 0.156.1, read-only sandbox), 2026-09-28: consumer census —
  no defect found (also checked the 51 `MUTATIONS` find-strings in
  `tools/run_e2_c_product_path.py`, each matches the source exactly once); rollback
  walk — no defect found; tests — the wrong `revision + 1` guard above, which passed.
  Disposition: the 099 test became the grid; the wrong guard now reds it.
- opus subagent, 2026-09-28: the landed code survived every attack; the tests did
  not — four wrong versions (V1–V4 above) passed all 33 tests then in the file. It also
  found the WITHIN-Worker way revision and content part company (a format action that
  comes back dispatched-unverified: the drain counts a mutation, `failFormatBarrier`
  never advances the revision), confirmed by the main session from
  `src/probe_engine.cpp` (`completeFormatBarrier` advances, `failFormatBarrier` does
  not) and now a unit test. Also flagged: comment overstatements (fixed), the probe's
  weak predicate and hash field name (fixed), and finding-text claims beyond what was
  measured (fixed in 096/098/099).

## 4. Product path after landing — `product-path/`

`tools/run_e2_c_product_path.py --browser chrome`, one run on the shipping profile (no
`--profile`) and one with `--profile e2-editor-v14`, sequential, after
`make test-e2-c-static` (exit 0), on shell generation v52 (`7a1e8815…`).

| run | result | served shell |
| --- | --- | --- |
| `v52-shipping-e2-editor-v8.json` | `ok: true`, 40 PASS / 2 NE | served = declared v52 |
| `v52-profile-e2-editor-v14.json` | `ok: true`, 40 PASS / 2 NE | differs only in the entrypoint (the repointed page `d7480132…`, same shape as the 09-10 v14 runs) |

Compared cell by cell with the last plain runs before the fix
(`findings/evidence/096/product-path/plain-e2-editor-v8-after-t8a.json` and
`plain-e2-editor-v14-b4-0{1,2,3}.json`): **no check changed outcome** on either profile.
The two NE are the same two as before (`notice-action-recovers-the-session`, the designed
sentinel; `a-refused-action-is-reported-and-changes-nothing`, diagnostic-only by
construction).

Check 42 (`a-boundary-arrow-press-does-not-cost-the-work`): v8 exercised B1, B3, B4
(inducer: the boundary press itself); v14 exercised all four, B1, B3, B2, B4 (inducer:
the worker failure). B3's control held on both — `checkpointBeforeTheKey` 無 after the
typing, 有（r1） after the key — because typing is still a mutation; only moves changed.
One run per profile, as the ruling asked; this is a no-regression check, not a count.

## 5. The shipped shell, v48 — `probe_098_v48_arrow_then_drag.py`

Added 2026-09-28 after landing. 098's scope section inferred, without measuring it, that
the shell users are served today (v48: moves are mutations, no half C) banks a
checkpoint of an untouched document when an arrow key is followed by a drag, through the
base class's `_checkpointBeforeSelection`.

**The v48 shell is rebuilt from git, not guessed.** All 13 files in
`e2/editor-shell-v2-bundle-v48.json`'s `included` list are taken from `2d319677` (the
commit that froze v48) and laid over a mirror of `dist/`; the probe recomputes the
bundle digest over the served files, the way the product-path runner does, and refuses
to run unless it equals the declared `ecfb6866…` (it did: `servesDeclared: true`).
`web/e2-editor.html` is outside the hash net (finding 094) and is taken from the same
commit (`servedHtmlSha256 7c2a37fe…`). The same scenarios run on the current `dist/`
(v52, served digest = declared `7a1e8815…`) as the comparison. Pin `4a2710bba1ef07d9`
(v8) on both; Chrome 151.0.7922.169; scenarios interleaved, 3 attempts each.

Criteria written in the probe's docstring before the first run; `#s-checkpoint` after
the drag settles:

| shell | drag only (control) | **one ArrowRight, then drag** | type, then drag (positive control) |
| --- | --- | --- | --- |
| v48 (shipped) | 無 3/3 | **有（r0） 3/3** | 有（r1） 3/3 |
| v52 (fixed) | 無 3/3 | 無 3/3 | 有（r1） 3/3 |

All 18 as predicted. The inference holds on the shipped bytes: a document nobody typed
into, one arrow key, one drag → a checkpoint of bytes identical to what was opened, the
label reads 有（r0）, and the drag takes 0.61 s instead of returning at once (the save).
Not data loss. On v52 the same gesture banks nothing — the fix measured through a
second consumer (the base class's selection checkpoint), not only through half C.

The "drag" column's `seconds` of 3.0 in the 無 cells is the probe's own 3-second wait for
the label to change, not a latency.

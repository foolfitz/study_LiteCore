# Handoff: v25 through section 6.3 (F1-F4 hold), section 9 reader, host 0.2.40 installed

Checkpoint **2026-10-29 ~18:55 +0800**. Supersedes 10-29f as the entry point.
Study HEAD **a79a7ee16** plus the commit that adds this file. Tree clean except the unrelated untracked `codex-claude-code-delegation.md`
(preserve it). **Nothing is running.** DDEV: only `litecore` (+ router) runs; at the owner's request
fgp-nc and nc-bridge were stopped at 18:06 and stay stopped (owner's choice). The install slot
(18:45:50-19:30) is over; any further DDEV step needs a new owner slot.

## Done this session (all offline, local mirror)

1. **Page cut-over** `e06d10a1b` (`findings/evidence/link-batch-v25/cutover/`): page `b15a6d8e` -> `6e66c930`,
   only the pin (`44cb15ea8d36f0e0`) and the worker URL; `make -n e2-c-assets` printed ONE `cp` (SDK unchanged).
   **V0′ was needed** (spec named none): both v24 count readers (`read_v24_remaining_cohort.py`,
   `judge_v24_product_four_arms.py`) bind the live shell digest, so on the live v25 tree they are NE by
   construction (`shell digest differs: 550b68bf…`). With only the page restored (source + `dist/`) both
   reproduce their committed outputs byte for byte; put back with the cutover tool (`--expect-sha256 6e66c930…`).
   Pass the four-arm judge the receipt's ABSOLUTE report paths, or its `runs[].dir` leaves differ.
2. **Generation 78** `9450e5340` (`freeze-78/`): `--manifest e2/editor-shell-v2-bundle-v78.json`, v77's seven
   exclusions verbatim + `sdk/v25-feature-worker.js`; digest `550b68bf…`, file `91bc4f68…`; only the page differs
   from v77. `Makefile:4947` passes `--manifest …v78.json` (red before / green after / red on v77 and on the
   default v76). `make test-e2-c-reachability` still red at `Makefile:4908` (coverage audit), problem list
   identical on the pre-cutover tree `b241c83a4`. V0′ re-run after the freeze: holds. The bundle tool's default
   `MANIFEST` stays v76 by design. If anything forces a shell change now, that is generation **79**.
3. **Section 9 reader** `dfa9ba6bd` (`tools/check_v25_ships_confined.py`, `section-9-reader/`):
   `CONFINED_V25_HOLDS` -- 39 differing preprocessed lines between the v25 line and the same line without the
   V25 define, 0 outside a branch governed by `OXSDK_E2_V25_FORMAT_PROOF`; v24's line on the tree equals
   `1f95a9fca`'s. Four red cases red on their own clause. **It found a blind spot in
   `what_the_link_ships.py`**: the old side copies only the `.cpp`, so sibling `.inc`/`.h` resolve to the LIVE
   tree; the v25 stage and witness changes (32 of the 39 lines, in two `.inc`) never appeared in
   `pre-link/ships.stdout.txt`. Spec 13.3's "exactly the four declared places" over-read it; section 14's carry-over
   decision cited it. Now tool-judged, same conclusion. **Open item**: which earlier batches' claims rested on
   `ships` with a changed sibling file (the tool itself is unfixed; not bound by v25).
4. **F1** `efa45ab66` (`f1/`): `diag_format.py` imported unchanged by `diag_format_v25.py`; v24 served from its
   own bytes via `tools/v25_f_products.py` (identity checked file by file; four red cases). Chrome, 3 runs:
   **F1_HOLDS** (`read_f1.py`, eight mutations red). The engine's own record is read inside the worker
   (`Target.setAutoAttach` + a `JSON.parse` observer, no served byte changes) because the page-level
   `dispatched` cannot distinguish serialisation from the stage fallback (v22 never sends `dispatched`; its page
   still shows `true`). v25: bullet stays `ready`, engine `dispatched: true`, `stage: awaiting-result`; saved
   `MKAFTERCLEAR` not italic, `MKITALAGAIN` italic; every set-* reply has a known `witness`. v24 0/3 on all.
5. **F2** `efa45ab66` (`f2/`, `tools/check_v25_clear_format_noop.py`): **F2_HOLDS**, Chrome + Firefox 3 each: v25
   four ok, `state-noop` x4; v24 `LOK_COMMAND_FAILED` at `set-bold`. **Recipe corrected before any evidence run**:
   the first clear-format after placing the caret does not trigger 172 (LOK broadcasts all four states in that
   flush; v24 answered four ok -- `recipe-witness-shake-01/`), so the tool presses twice and judges the second,
   with a `set-bold` witness `state-noop` clause. Findings 171/172 status updated: fixed in v25 and measured,
   not shipped.
6. **F3 criterion** pinned before any F3 run, `55b3acc59`, spec section 16 (owner chose **A, no regression**):
   the six DISPOSITIONS product cells must PASS; four `v23-product-*` arms excluded (F4); every other check: v24
   PASS -> v25 PASS, v24 non-PASS -> same or PASS, improvements named. Baseline v24 T4 run-02. Reader
   `tools/read_v25_f3.py` red on v24-as-v25 (exactly the six cells) and on seven mutations of a synthetic report.
7. **F4 tools** `55b3acc59`: `run_v25_four_arms.py`, `judge_v25_product_four_arms.py`,
   `v25_four_arms_identity.py` (v24's with v25 names; no V0″ preflight -- F4 is not a count). Preflight red on
   v76 and v77; the v25 reader refuses v24's counted four-arm records (`shell generation is not frozen 78`).

8. **F4** `762f7cfe3` (`f4/`): four arms 24/24 PASS, both browsers, identity v25 / generation 78.
9. **F3**: run-01 `F3_RED` under section 16 -- the only red was the designed sentinel
   `notice-action-recovers-the-session` (v24 PASS -> v25 NE), anti-correlated by construction with the bullet
   cell; its v24 PASS was produced by finding 171 (NE on v21/v22). Owner chose a correction (spec 16.1,
   `b3c6fea46`, before run-02): the sentinel is read from the same report's `recoveryPairing` (held, consistent,
   designed abstain when bulleting PASSes). **run-02 `F3_HOLDS`** (`a6bea3a4c`): every outcome equal to run-01;
   six P cells PASS; no regression; Chrome long document and Firefox clear-format improved. Self-test 11/11 red.
10. **Host 0.2.40 installed** `145d55034` (`findings/evidence/host-0.2.40/`): branch `host-0.2.40` (`ae1f9db`, info.xml
    only) on parent 4a8b3cd with the exact 0.2.38 engine that was live after the rollback. Engine
    **a08bc6ecb7241448** (46 files; vs 0.2.38: 38 identical, 4 changed modules, v25 profile added, v22 removed);
    archive `build/archive/host-0.2.40-engine-a08bc6ecb7241448`; PACKAGE_HOLDS 22/22; CANDIDATE_INSTALLED (documents
    and lock rows unchanged, routes 401); Files workflow 52/52 both browsers; post-install identity holds (two red
    cases red). **0.2.40 is the daily uncounted candidate.** Nominal shipped host stays 0.2.26; K has not run.
    Rollback prepared: `host-0.2.40/rollback-package.sh` (exact 0.2.38 engine; needs a slot).
11. Spec v25 sections 15, 16, 16.1, 17 appended; findings 171/172 status updated; DISPOSITIONS got an appended
    v25 re-measure note (rows 1-6 PASS on F3 run-02; row 9 two PASS observations, not N runs).

## Next steps

1. **Owner hand check on 0.2.40** (suggested, not a gate): on a blank line press the bullet button (expect no
   rollback demand); in plain text press clear-format twice (expect 「已清除…」 both times). The Files workflow's
   Writer arm uses the insert field, so these two fixes were measured on the mirror only.
2. **K** (spec v25 6.4, `k-protocol-ruling/RULING.md` revision 1, DISPOSITIONS): needs its own 8-10 h no-site
   window AND the settled K control protocol (`handoff/WORKORDER-v24-K-control-protocol.md`, still open: the old
   v8 control cannot run against the typedInsert page gate). Row 9 still owes its N runs; row 7's inducer limit
   and row 8's oracle limit apply as pinned.
3. **`what_the_link_ships.py` blind spot** (open item): list which earlier batches' "only declared hunks" claims
   relied on it while a sibling `.inc`/`.h` changed; decide whether the tool gets a successor (it is cited by
   other batches' records, so not edited in place).
4. Spec v25 section 2/10 leftovers: page clear-format continue-on-error; finding 038 candidate (wedge does not
   reproduce on the ordered engine); a successor to `induce_worker_failure`; the native N=5 arm for
   L-noop-trusts-last-state-item.

## Cautions (new this session)

- `dist/` serves v25 now. Any tool that means "v24" by "dist/ as served" (e.g. `diag_format.py`) silently
  measures v25. Serve v24 from its own bytes: `tools/v25_f_products.py`.
- The v24 count readers are red by construction on the live tree; re-read them only by restoring the declared
  page (V0′ recipe in `cutover/README.md`).
- `what_the_link_ships.py` cannot see changes in sibling includes; use `check_v25_ships_confined.py`'s method
  (`git archive` the whole `src/`, line markers) for any "only the declared hunks differ" claim.
- 172 needs a warmed state (LOK re-broadcasts only changed states); a single clear-format on fresh plain text
  passes even on v24.

## Section 34.4 this round

Fixed-by-execution **2** (F2's recipe before any evidence run; F3 correction 1 after run-01). Fixed-by-review **0**.

## Language

Replies to the owner: Taiwan Traditional Chinese (A/B/C for options). Evidence, upstream text and
`handoff/**`: English. `devlog/`, `research/`, `specs/`: zh-TW (specs append-only once pinned).

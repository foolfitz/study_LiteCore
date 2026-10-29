# K control protocol for v24: fable ruling (with revision 1)

Requested 2026-10-29 by the owner (option "ask fable to rule first") on
`handoff/WORKORDER-v24-K-control-protocol.md`. The adjudicator worked read-only on the files named
in the brief. The main session then checked the load-bearing citations, challenged item 5 with a
measurement, and the adjudicator revised item 5. This file records the ruling as delivered,
the revision, and the main session's verification. **No counted run, no repin, no edit to any
frozen file has happened because of this ruling.**

## Ruling: A, modified (not B)

Protocol A as written (a historical v8 page/shell/SDK closure *run* as reference and red) cannot be
executed by the frozen instruments, and building serving/reading machinery to keep it alive would
violate CLAUDE.md section 4. B is rejected because the impossibility is permanent: every engine from
v24 on carries `typedInsert`, so a same-source v8 run never exists again.

Forcing facts (each re-read by the main session, see "Verification" below):

- Frozen runners refuse a historical closure: `run_e2_c_product_path.py` `shell_lagging_source`
  (`:2692-2712`, used `:4773-4779`) and `run_merge_wasm_shakedown.py:1344-1348` exit when served
  shell modules differ from the live tree's source.
- The frozen merge judge cannot count a red bound elsewhere: `judge_counted_m2.py` `together()`
  (`:663-688`) requires every report, red included, to carry `binding == m.BINDING`.
- The merge runner is byte-identical to the one used by the 0.2.26 count (`aaee0cda...`), and
  `release-0.2.26/merge-m2/red-{chrome,firefox}.json` (+ `.docs`) are that runner's red arm on v8.
- The 0.2.26 product-path v8 row was a tolerance baseline (`release-0.2.26/product-path/judge.py`
  `verdict()`), not the net's sensitivity; the mutation red cases test the checks.

## Prescription (to be recorded before any counted run)

1. **Historical merge negative = the committed 0.2.26 red reports**, bound by reading, not serving:
   runner `aaee0cda...`, `candidate.profile e2-editor-v8`, `bound.wasmSha256 4a2710bb...` equal to the
   v8 archive, `binding == originalMergeBinding` (k-binding-inventory.json), `boot.state == ready`;
   plus `legacy-v8-gate-01/report.json` manifest `d70481cb...` with no `typedInsert`. Default if
   `sha256(run_merge_wasm_shakedown.py) != aaee0cda...`: merge red NOT ESTABLISHED, K does not hold.
2. **Old missing-behaviour signal** = `red_record` (`judge_counted_m2.py:413-417`), per browser the
   first three M2-1 cases `placed`, `refused`, `reopened`, recomputed from the kept docs; read by
   `judge_counted_m2.py --uncounted` on a K directory holding the v24 reports plus copies of the
   historical red reports and docs; expected exit 4, `red PASS`, `oneRunner` true.
3. **Counted-ness reader** (new file, own red cases): non-red reports `counted: true`,
   `binding == proposedMergeBinding`, `bound == binding` on all nine keys, runner `aaee0cda...`,
   stderr empty; red reports `binding == originalMergeBinding`, non-profile bound keys equal,
   wasm `4a2710bb...`. Red cases: run without override gives `counted: false`; one flipped hash.
4. **Binding override only in-process** in a new named K wrapper (precedent
   `run_v24_four_arms.py` `prepare()`): set `run_merge_wasm_shakedown.BINDING` to the proposed
   binding before `main()`, record `{default, used, applied}`. `BINDING` at `:176` is never edited;
   `judge_counted_m2.py` untouched.
5. **Product-path, revised (revision 1)**: plain v24 arm only, 3 rounds x 2 browsers, through the
   same wrapper rebinding `build_e2_c_shell_bundle.MANIFEST` to generation 77 before import. New
   reader (new file, own red cases).
   - Population: the ids, in order, of `link-batch-v24/pre-count/t4/run-02/{chrome,firefox}/report.json`
     (46); K runner hash must equal T4's (`7ba30235...`). P1: every report carries exactly those ids
     in that order, else STOP. P2: entrypoint `b15a6d8e...`, no `candidateCutover`,
     `shellManifestOverride.used` = v77 with the frozen file sha.
   - **P3 anchor = the committed 0.2.26 records of the last counted candidate, read not run**:
     `release-0.2.26/product-path/e2-editor-v21-{chrome,firefox}-r{1,2,3}.json`, with the old
     `verdict()` applied unchanged: v21 PASS 3/3 => v24 PASS 3/3; v21 FAIL n => v24 FAIL <= n;
     v21 NE => v24 0 FAIL; row 1' carries over for `recovery-returns-what-the-product-promised`.
     The 0.2.26 v8 row goes to P4 (descriptive) only. The four ids with no 0.2.26 row
     (`v23-product-*`) must be PASS 3/3.
   - Changed check semantics: between `3e824c97` (0.2.26 chain) and `7ba30235` the runner moved in
     `229704759`, `c6213c854`, `6c1640f64` (E1 `da5569079` and its revert `aaea53369` net zero). The
     historical row transfers by default; it is released for a cell **only** by a registered
     disposition citing the commit and hunk that touch that check. A released cell must PASS 3/3
     on K or carry a named instrument limit with its own ruling (precedent I-enter-raw-substring).
   - Red cases before K: flip a v24 cell where v21 was 3/3 => RED; a new id not 3/3 => RED;
     the 0.2.26 directory fed as K => STOP (42 != 46).
6. **Page-gate negative** (new K arm; forced by `legacy-v8-gate-01`, written before any K, per
   instance, closes at the first clean K): re-run `probe-legacy-v8-gate.py` into the K directory
   after shakedowns, expecting control PASS, legacy-v8 EXPECTED_REFUSAL, `insertRequests 0`, page
   `b15a6d8e...`, v8 wasm `4a2710bb...`. Registered as a page-gate negative, not a merge negative.
7. **Pins**: the 23 `frozenBy: []` pin sites move by one repin script in one commit, old values
   kept in comments; P4 expects `b15a6d8e...` for dist, web, the 0.2.39 archive and host-served.
8. **Count semantics**: v24 has no clean K, so nothing resets; after the first clean K no new
   criteria (later concerns become findings). Any of 1-6 not done => K NOT RUN, nominal stays
   0.2.26. A reader never made red is not evidence. **K cannot START while any of the nine cells
   below lacks a registered disposition.**

## The nine cells (revision 1)

PASS 3/3 for v21 at the 0.2.26 count, non-PASS in T4 on v24 (and already non-PASS on v23's counted
four-arm run for the first five):

| Browser | Check | v21 @0.2.26 | T4 (v24) |
| --- | --- | --- | --- |
| chrome | bulleting-a-blank-line-does-not-demand-a-rollback | PASS 3/3 | FAIL |
| chrome | an-inline-format-reaches-a-selection | PASS 3/3 | FAIL |
| chrome | every-inline-format-reaches-the-document | PASS 3/3 | NE |
| chrome | clear-format-removes-every-inline-format | PASS 3/3 | NE |
| chrome | a-boundary-arrow-press-does-not-cost-the-work | PASS 3/3 | FAIL |
| chrome | the-enter-key-reaches-the-document | PASS 3/3 | FAIL (named limit I-enter-raw-substring) |
| chrome | editing-a-long-document-stays-responsive | PASS 3/3 | run-02 FAIL, run-03 PASS |
| firefox | bulleting-a-blank-line-does-not-demand-a-rollback | PASS 3/3 | FAIL |
| firefox | every-inline-format-reaches-the-document | PASS 3/3 | NE |

Each needs an individual disposition before START: a product finding (the cell stays RED until fixed
or accepted as a named limit by ruling) or an instrument limit with ruling and cited hunk. The
boundary-arrow disposition (`link-batch-v23/review/ruling-fable-1.md:106`, addendum-1 section 2.1)
must be re-cited, not assumed. The intermittent long-document cell needs N runs, not the single flip
in `t4/README.md:83`. **Default if a disposition is never written: the cell reads against the 0.2.26
anchor, RED, K does not hold, nominal stays 0.2.26.**

Suggested offline bisect (no DDEV): the runner at `229704759^` (= `3e824c97`) on the v24 page; PASS
there and FAIL on `7ba30235` => instrument; FAIL on both => product.

## Premises found false or unsupported

- Work order: a historical closure as a *runnable* reference/red is refused by the frozen runners
  and uncountable by the frozen judge (above).
- Work order "retains its nine binding fields": true for the keys, silent on how frozen `BINDING`
  ever sees v24 values; needs the in-process override (item 4).
- Work order "generate the population from the frozen runner": the runner has no static check list;
  the population exists only in reports it produced (T4 run-02 + runner hash).
- `chain-0.2.26.sh` calls the product-path runner directly; on v24 that leaves the four-arm checks
  NE without the v77 rebinding (spec v24 section 17.5).
- `m3-production-ui/runs-0.2.26/README.md` "not run" is stale; the chain ran 2026-10-18 and held.
- `t4/README.md:30-32` compares v24 with v23 (and a context-only legacy file), not with the 0.2.26
  records; it must not be cited as "no regression since the last count".
- Side observation (finding candidate, not K): `legacy-v8.json` attempts 1-3 show the pill `ready`
  while `expired: true` after key presses on the refused page.

## Verification by the main session (2026-10-29)

Re-read, not inferred: `shell_lagging_source` body and its SystemExit in both runners; merge runner
sha256 `aaee0cda5be5...` equals `chain-20261018T160539Z.out:3`; both historical red reports carry
runner `aaee0cda`, `counted: true`, `binding == originalMergeBinding`, wasm `4a2710bb`, profile
`e2-editor-v8`, `boot.state ready`, three cases; `judge_counted_m2.py` `red_record` and `together()`
as cited; the 0.2.26 product-path `verdict()` tolerance rows; T4 run-02 46 unique ids per browser;
product-path runner sha `7ba30235...` now, `3e824c97` at `712f955ad`, intervening commits as listed;
v23 `product-four-arms-counted-01/chrome.json` FAIL/NE on the first five cells.

The first delivery's item 5 anchored tolerance on T4 (the candidate's own pre-count runs). The
main session measured the nine cells above (v8 and v21 PASS 3/3 at 0.2.26, non-PASS in T4) and
returned them; that anchor would have tolerated every regression since the last counted release.
Revision 1 replaced it with the v21 anchor. Counted for section 34: fixed-by-review 1 (ruling item 5).

# K nine cells: product, instrument or environment? (diagnostic, not K)

Required by the K ruling (`../k-protocol-ruling/RULING.md`, revision 1): nine product-path cells were
PASS 3/3 for v21 at the 0.2.26 count and are not PASS on v24 (T4). Each needs a disposition before
any K START. This directory holds the measurements that decide which kind of disposition.

## Already established by reading committed evidence (no run)

- No product-path run exists between the 0.2.26 count (2026-10-18) and the v23 four-arm integration
  (2026-10-27). The first post-count runs already show the cells non-PASS on v23.
- The v23 integration's `unpatched` reports used runner `5ca4451e`, which differs from the 0.2.26
  runner `3e824c97` only by commit `229704759`. That commit changes Firefox worker-error induction,
  the Firefox session launch, and the Chrome 096 boundary key delivery (CDP `rawKeyDown`/`keyUp` ->
  `v21_input.key`). It does not touch the code of the bulleting, inline-format, clear-format,
  Enter or long-document checks. `c6213c854`/`6c1640f64` add the four-arm block (after those checks)
  and a dormant observer mirror that changes the served HTML's module tag from the start.
- T4 failure records on v24 Chrome (run-02): bulleting -> `MUTATION_OUTCOME_UNKNOWN: the readback
  covers more than one paragraph` (state recoverable-error); every-inline-format -> the italic arm's
  precondition (italic off) not established, cache already `true`; clear-format -> precondition
  "all four on" not established, button toast `LOK_COMMAND_FAILED`; inline-format-selection -> the
  drag selected `KBOLD` inside the already-bold `MKBOLDON` marker (`wasBoldBefore: true`).

## Arms (declared before any run)

Both arms serve the **0.2.26 shipped product**: a scratch tree whose `wasm_sdk_probe/dist` is a
symlink mirror of the live dist with the 22 files of the 0.2.26 package (archive
`host-0.2.25-engine-f5f0df762e1855f2`, buildId f5f0df762e1855f2, page `605cf24b...`, profile
`e2-editor-v21`) decoded from `.gz` and materialized after a sha256 check against its MANIFEST.
`make_tree.py` builds it and writes a receipt. Plain arm, no flags, the way `chain-0.2.26.sh:250` ran it.
Nothing in the live tree, dist, frozen files or the host is modified; the scratch trees are discarded.

- **H2** -- today's tools (`git archive HEAD wasm_sdk_probe`, product-path runner `7ba30235...`) on the
  0.2.26 product, today's browsers. One round per browser.
- **H0** -- the 0.2.26 count's tools (`git archive 9c8d83cc3 wasm_sdk_probe`, runner `3e824c97...`)
  on the same product, today's browsers. One round per browser. Run if H2 leaves any cell non-PASS.

## Reading (written before the runs)

Per cell and browser, with T4 (today's tools on v24) as the third point:

| H0 (old tools, v21) | H2 (today's tools, v21) | T4 (today's tools, v24) | Reading |
| --- | --- | --- | --- |
| PASS | PASS | non-PASS | **product**: v21 -> v24 changed behaviour; finding |
| PASS | non-PASS | non-PASS | **instrument**: a tool change since 9c8d83cc3; locate the hunk |
| non-PASS | non-PASS | non-PASS | **environment** (browser/desk) or fixture: not attributable to v24 |

One round is a first reading, not a rate. A cell whose H-arm outcome contradicts its 0.2.26 3/3
history is re-run before it is used as a disposition. The four `v23-product-*` checks are expected
NE on v21 (no four-arm observer for that page) and are not read. The Chrome Enter cell keeps its
named limit I-enter-raw-substring regardless (v24 typed text carries rsid spans; v21 does not).
If H2 cannot boot or refuses the tree, that refusal is the result and is recorded verbatim.

## Addition before H3 (after H2, before any H0)

H2 came back PASS on all seven Chrome cells and both Firefox cells (`h2-*.json`; served page
`605cf24b`, wasm `db3408f5`, no v24 identity). Product-path reports do not record the Chrome version,
so "T4 was yesterday" cannot be excluded by reading. Added control **H3**: the live tree (same HEAD
tools as H2, runner `7ba30235`), plain arm, no wrapper, on the live dist (v24 page `b15a6d8e`),
both browsers, run immediately after H2. Only the product differs between H2 and H3. Reading: H3
non-PASS where H2 PASS => product (v21 -> v24) under identical tools, browsers and hour. H3 PASS =>
the T4 non-PASS was not reproduced; the cell is re-run before any disposition. The four
`v23-product-*` checks are NE without the v77 rebinding and are not read. H0 is then unnecessary
for any cell that is H2 PASS / H3 non-PASS.

## Addition before H4 (after H3)

H3 (v24, same tools/browsers/hour as H2) is non-PASS on 8 of the 9 cells where H2 (v21) is PASS;
`editing-a-long-document-stays-responsive` is PASS on both (the T4 run-02 FAIL did not recur).
v23 was never shipped in a host package: hosts 0.2.27-0.2.38 all carry v22 (page `3b96cb16`), and
0.2.39 is the first to carry v24. Added **H4**: today's tools on the 0.2.27 package (archive
`host-0.2.27-engine-817413d5ad5bd502`, buildId 817413d5ad5bd502, v22), same method as H2
(`make_tree.py` now takes the package directory as an optional fourth argument). Reading: H4 PASS on a
cell => the change entered between v22 and v24 (v23's ordered-command/unipoll work or v24) and the
shipped hosts 0.2.27-0.2.38 never had it, so host 0.2.39 is the first package to ship it. H4
non-PASS => it entered between v21 and v22 and has shipped since 0.2.27.

## Results (H2, H3, H4; one round per browser, 2026-10-29 09:46-10:31 +0800)

Identity read from each report: H2 page `605cf24b` + wasm `db3408f5` (v21); H4 page `3b96cb16` + wasm
`f7a40bcc` (v22); H3 page `b15a6d8e` + wasm `27615808` (v24). Same HEAD tools (runner `7ba30235`),
same browsers, consecutive runs; load 0.2-1.2 throughout (`runs.log`).

| Browser | Check | v21 (H2) | v22 (H4) | v24 (H3) | T4 (v24) |
| --- | --- | --- | --- | --- | --- |
| chrome | bulleting-a-blank-line-does-not-demand-a-rollback | PASS | PASS | FAIL | FAIL |
| chrome | an-inline-format-reaches-a-selection | PASS | PASS | FAIL | FAIL |
| chrome | every-inline-format-reaches-the-document | PASS | PASS | NE | NE |
| chrome | clear-format-removes-every-inline-format | PASS | PASS | NE | NE |
| chrome | a-boundary-arrow-press-does-not-cost-the-work | PASS | PASS | FAIL | FAIL |
| chrome | the-enter-key-reaches-the-document | PASS | PASS | FAIL | FAIL |
| chrome | editing-a-long-document-stays-responsive | PASS | PASS | PASS | FAIL (run-02) |
| firefox | bulleting-a-blank-line-does-not-demand-a-rollback | PASS | PASS | FAIL | FAIL |
| firefox | every-inline-format-reaches-the-document | PASS | PASS | NE | NE |

v21 and v22 are identical on **all 46 checks in both browsers**. Reading by the declared table:
eight cells are **product** changes that entered after v22, i.e. with v23's work or v24, and were
first shipped by host **0.2.39** (installed on the owner's DDEV earlier today). The Chrome Enter
cell is still the named instrument limit I-enter-raw-substring (rsid spans on v24 typed text; the
independent span-aware replay holds), so its product change is the oracle's, not the user's.
The long-document cell is PASS on all three products here: the T4 run-02 FAIL is the recorded
intermittent; N runs are still owed before it is dispositioned. H0 was not needed (no cell is
H2 non-PASS). The two non-nine differences between v21 and v24 are the designed sentinel
`notice-action-recovers-the-session` (NE on v21/v22, PASS on v24) in both browsers.

What the v24 records show the user would meet (H3): a bullet on a blank line ends in
`recoverable-error` with `MUTATION_OUTCOME_UNKNOWN: the readback covers more than one paragraph`
(both browsers); after bold on/off, the page's format cache already reads italic, underline and
strikethrough as `true` before each is pressed, so the presses toggle them off (both browsers);
clear-format answers `LOK_COMMAND_FAILED` (both browsers); the selection-format FAIL selected text
already bold (`wasBoldBefore`), plausibly downstream of the cache state. These are observations
from the regression net's records, not yet a characterised finding.

Process lesson: T4 compared v24 with v23, which was never shipped; the comparison base for a
regression net has to be the last shipped/counted product, or a regression introduced by an
unshipped intermediate becomes the baseline.

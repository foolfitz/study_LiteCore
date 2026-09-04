# 090 — Two instruments disagreed about which file is the product page, and only one of them ships

**Status**: fixed (one `make` target), and the gap that hid it is not.
**Measured**: 2026-09-05, `wasm_sdk_probe`, candidate `e2-editor-v12`.
**Class**: instrument, not product. Nothing shipped wrong; a gate nearly counted
runs on bytes nobody would ship.

## What happened

The product page exists twice:

* `web/e2-editor-app.js` — the source, and what `tools/serve_candidate_page.py`
  (the human round) and `tools/probe_aria_projection.py` (gate condition 4a)
  read;
* `dist/e2-editor-app.js` — a plain `cp` of it (`Makefile:2187`), and what
  `tools/run_e2_c_product_path.py` reads, because it builds its mirror from
  `dist/` (`root = PROJECT / "dist"`).

Findings 087 and 088 were fixed in `web/` on 2026-09-04 and verified there: 4a
went green on eight terms and Orca announced `heading 1` / `heading 2` /
`List with 2 items`. `dist/e2-editor-app.js` was left at its 2026-09-03 copy and
carried **none** of it — `aria-activedescendant` 7 occurrences in `web/`, 0 in
`dist/`; `lastStructureSignature` 4 and 0.

So the first soak run taken after the fixes measured the page **without** them,
returned `ok: true`, and self-reported
`candidateCutover.pageSha256 = 3dfdcfef…` — the pre-fix sha.

## What caught it, and what did not

**Caught it**: the run's own `pageSha256`, read against the amendment that had
just re-pointed the bank to `20f09cc9…`. `check_soak_bank.py` would have
refused the run at banking time on the `page-sha` clause. The binding did its
job.

**Did not catch it**: everything else. `dist/` is gitignored
(`.gitignore:34`), so no diff showed a stale copy. The `make` rule exists and is
correct; nobody ran it. Both instruments report "the candidate page" and neither
says which file it came from. Three green 4a runs and a full Orca round were
taken on one page while the product net ran on another, and the two agreed on
every check they shared, because they were each internally consistent.

This is the tree's own recurring shape, and the third instance recorded:
`AGENTS.md` has 「凍結的 profile 會把修法擋在門外」 from 2026-08-22 and
「harness 的路不是使用者的路」 from the same round. The variant here is new only
in that both paths were the harness's.

## Fix

`make dist/e2-editor-app.js`. `dist/` and `web/` are now byte-identical
(`5aeae0e1…`), and `repointed_page()` over either gives `20f09cc9…`.

## Not fixed

Nothing compares the two sources. A check that recomputes the candidate page
from **both** `web/` and `dist/` and refuses when they differ would have made
this loud at the start of any run, and does not exist. It belongs with the
runner rather than in a document, because a rule written down is a rule someone
has to remember on the day the copy goes stale.

Registered rather than built today: the fix is one `make` invocation and the
guard is a separate change with its own red case, and inventing machinery while
closing a gate is how a gate stops meaning anything.

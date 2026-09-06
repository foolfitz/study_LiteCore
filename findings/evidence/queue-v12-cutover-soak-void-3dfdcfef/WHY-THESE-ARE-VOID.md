# Seven clean soak runs on a page that no longer exists

Runs 2–8 of the `e2-editor-v12` cutover soak, taken 2026-08-29 to 2026-09-03
against candidate page sha
`3dfdcfef4abfe6b723b573f35e8ec8f885dcc42a8ed4d8338ad2381eb386f50f`.

They are **void for the count and retained untouched**, the same disposition the
five unsplit-v11 runs received in `../queue-v11-cutover-soak-not-started/`.

## What voided them

The human round of 2026-09-04 found findings 087 and 088. Both fixes landed in
`wasm_sdk_probe/web/e2-editor-app.js`, which is the product page itself, so the
candidate page's sha moved to
`20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95`.

`check_soak_bank.py` pins every counted run to one page sha
(`clauses["one-page-sha"]`, and `page-sha` per run). Nothing about these seven
runs was wrong. They measured bytes that will not ship.

## Why they are kept

Two reasons, neither of them sentiment.

They are the only evidence that the product path ran clean twelve-minus-four
times in a row on *some* page, which is what makes "the net is capable of a
clean run" a measurement rather than a hope. And a directory that quietly
shrinks when a candidate moves cannot be told apart from one that lost a member;
`check_soak_bank.py`'s RED 6 offers this lineage's predecessor as the candidate's
bank and requires that to be refused, which only works while the lineage exists
to be offered.

Disposition and the amendment that records it: `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, section "The candidate page moved, and what that voids" (2026-09-05).

## Condition 2's three diagnostic runs joined this directory (2026-09-06)

`diagnostic-01-caret12.json`, `diagnostic-02-caret12.json`,
`diagnostic-03-caret12.json` (taken 2026-09-03) and the judge's output of that
day, renamed to `VERDICT-condition-2-on-3dfdcfef.json`.

They are void for the same reason and by the same mechanism as the soak runs
above: `check_caret_diagnostics.py` term 1 requires
`candidate.pageSha256 == expect_sha` of **every complete run given to it**, and
these carry `3dfdcfef…`. They were moved rather than deleted, and moved rather
than left in place, because the judge globs `diagnostic-*.json` out of the bank
directory — left there, they would have made the re-take permanently red, and a
judge that is red for a page nobody is proposing says nothing about the page
somebody is.

What they still assert is unchanged and worth keeping: 36 committed rounds, 0
dropped, and the guard refusing a stale write 11, 7 and 6 times, on page
`3dfdcfef…`. That is the incumbent-lineage measurement of the finding 084 class.

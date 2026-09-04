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

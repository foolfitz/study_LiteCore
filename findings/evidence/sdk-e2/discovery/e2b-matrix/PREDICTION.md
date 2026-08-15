# Prediction: the E2-B positive matrix on the product artifact

**Written and committed before the harness exists and before any run.**

Criteria are `specs/SPEC-E2-B-paragraph-format-contract.md` 7.1 and 7.2, which
were written before this file. This predicts outcomes; it does not set
thresholds.

## What binds

Artifact `572035ac…`, profile `e2-editor-v2`, through the **product** v2 client
(`editor-shell-v2/paragraph-editor-client.js`). This is the run the freeze
rests on, so unlike the smoke and parity runs it judges **documents**.

## Shape

**5 actions × 3 gesture classes × 2 browsers × 3 rounds = 90 positive runs**,
plus the six cells 7.1 adds and the self-red arm 9.9 requires.

Gesture classes are the engine's own routing boundary, not a separate taxonomy:
`collapsed`, `range-single` (`preBlocks == 1`), `range-cross` (`preBlocks >= 2`).

## Per-run criteria (7.1, restated so this file is self-contained)

A run passes when all hold:

1. the route the engine reports equals the class the arm intended;
2. the action completes with `changed: null` and
   `completion: verified-format-readback`;
3. `revision == before + 1`;
4. the saved ODT shows every **targeted** paragraph in the target state;
5. **every other paragraph is byte-unchanged**;
6. for `range-cross`, `crossIdentityHeld` and `crossStateHeld` are both true.

Criterion 5 is the load-bearing one. Every action here is paragraph-level, so
without it a range that silently collapsed to a caret would satisfy everything
else — the same hole SPEC 3.4 was written to close.

## Predictions

**P1 — all 90 pass.** Basis: the five actions passed the section-3 gate on the
combination artifact for `range-single` (A1–A5, 3/3, both browsers, twice), the
collapsed class is what every E2-A verdict already covers, and the smoke run
showed all five dispatching on this artifact. `range-cross` is the newest path,
but its verification held on WASM in both browsers (`wasm-parity/`).

**P2 — the no-op arm advances the revision and leaves the body byte-identical.**
Dispatch `set-list-unordered` twice on the same paragraph; the second must still
report `revision + 1` while `<office:body>` is unchanged from after the first.
Basis: route C never reads the precondition, so it cannot report a no-op; the
smoke run already showed revision advancing on five consecutive dispatches
including ones that changed nothing. **This has never been measured with a
document comparison, which is why it is an arm.**

**P3 — the list-transition arm succeeds without structural loss.** `ul → ol` on
the same paragraph: the saved ODT shows an ordered list, one list item, and no
extra or lost paragraph. Basis: none. **This is the least supported prediction
here** — no round in this project has ever dispatched a list action onto an
already-listed paragraph, which is why "list switching causes silent ODT
structure loss" is a stop condition nothing could currently fire.

**P4 — mid-list `set-list-none` on items 2–3 of a five-item list splits the list
and loses nothing.** The two targeted paragraphs leave the list; the items
before and after remain listed. Basis: none measured; this is the structurally
riskiest ODT shape in the matrix.

**P5 — the mixed-state crossing arm passes.** ¶1 already a list, ¶2 plain, one
crossing range, `set-list-unordered`: both end listed, identity holds. Basis:
per-block extraction has only ever been measured on homogeneous pairs, so the
readback shape `<ul><li><p>…</li></ul><p>…` is new.

**P6 — the self-red arm fails, and that is the pass.** Expect `ol`, dispatch
bullet: `crossStateHeld` must be **false** and the action must fail. If it
succeeds, the per-block state check is not checking.

## What would make me stop rather than narrow

7.2's stop conditions, unchanged: a completion that cannot be attributed to one
request; a no-op indistinguishable from a loss; silent ODT structure loss on a
list switch. **P3 and P4 are the arms that could fire the third**, and if they
do the answer is a finding, not a narrowing.

## Rounds and citability

Three rounds per cell. Any cell whose verdict is not identical across all three
is recorded unstable and **may not be cited** — task #49's arms F, Y and Z
flipped exactly that way.

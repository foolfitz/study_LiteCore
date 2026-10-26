# Selection reader review 01 (before the first counted run)

An independent opus reviewer, read-only, read the diff `c092a15c..853f2522` of the selection reader, runner, page and tests. It also read the product `placeCaret`, the pre-red helpers, the preparation READMEs and RULING.md, and ran the 29 unit tests (all pass, none skipped). Its conclusion: no code defect would turn a wrong product into PASS within the current 14 shapes. It recommended a Firefox preparation before counting and hardening against `AttributeError`.

| # | Finding (reviewer's severity) | Disposition |
| --- | --- | --- |
| 1 | Medium: table-selection membership comes from the product's own plain move, so a wrong plain move could take a table member out of the A′ branch. Up/Down outside that branch have no native comparison. | The aggregate `judge()` records `nativeTextAgreement` (`agrees`, `roundsAgree`) for every S1 row with an observed selection: recorded, never asserted, so a flip is visible. `inspect()` output is unchanged, which keeps ruling (d). |
| 2 | Medium: no Firefox preparation of tonight's changes. | Planned before any counted run; not run yet because the native S5 measurement is in progress. |
| 3 | Low: `place_route` and the paint check could raise `AttributeError` on a `None` `selection`/`result`, which `inspect` does not catch. | Both chains now treat `None` as absent, giving NE. Tests: `selection-none`, paint `no-result`. |
| 4 | Low: export awaited a pending-hash snapshot once; a paint reply arriving during the await would serialize `sha256: null` (NE, never PASS). | Export loops until the pending list stops growing, then serializes synchronously. |
| 5 | Low: tests weaker than named: the paint test did not exercise the Worker wrapper's `paintIds` routing; test (b) fails only on text; no read-after-route or other-generation read case. | Added a Node test that drives the real wrapper across two workers (only a paint reply on the same worker is digested, a duplicate reply is not). Added `read-after-route` and `other-generation-read` route controls. Added `test_b_named_limit_caret_side_is_not_witnessed`, which shows the A′ caret limitation explicitly: old-premise geometry with Writer's text reads PASS with `anchorWitness: native-text-extent`. |
| 6 | Low: the setup-crossing check compares only the anchor and moving endpoints; a future body→body range spanning the table would not raise NE. | Recorded; true of no current shape. |
| 7 | `check_pre_red`: no defect. | — |

32/32 tests pass.

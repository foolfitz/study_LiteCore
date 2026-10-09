# Handoff, 2026-10-09 — R holds on host 0.2.8; findings 119 (new, data loss) and 111 fixed in the shell; shell v58 and host 0.2.9 being counted

Picks up from `HANDOFF-2026-10-08f-v19-validated-cutover-awaits-owner.md` (its Addendum's "Next: R"). Repository root `/home/jiajun/LibreOffice/study_LiteCore`; paths relative to it. The owner was asleep for all of this and authorised two things for this round only: keep going past the handoff instead of stopping, and let fable decide in their place where a decision was needed (both rulings are committed verbatim and their plain-language reasons are in the findings).

Entry points: this file; `specs/SPEC-M3-production-ui.md` §13 (R on v19) and §14 (119/111); `findings/119-*.md`, `findings/111-*.md`; `findings/evidence/m3-production-ui/RESULT-0.2.8.md`; `findings/evidence/fast-delete-recovery/`; `findings/evidence/111/`; `findings/evidence/release-0.2.9/`.

## What happened, in order

| Commits | What |
|---|---|
| `68716eba`, `c923fd53` | Native round R-host on the owner's document (predictions first): B-del's place is R0c's E02 (Writer merges); B-bs's place was never measured — Writer's first Backspace there removes the first-line indent, the second merges, and two presses give a `content.xml` byte-equal to E02's; the document's two ends are `nothing-selected` on v19's E shape. |
| `9b26cbb1` | Spec §13: R re-bound to v19 before any 0.2.8 run. K-del/K-bs are Writer's key (no reopen, paragraph text = native key arm); R-bs/R-del are refusals at the two ends; B-3x all at the start; places recalibrated to v19's 12474 × 308480-twip document (109's calibration was v8's layout). Merge spec §10.2's R row (reduced `content.xml` bytes) withdrawn for two reasons: the arm types first (§12, rsid) and E02 is byte-different on v19 anyway (finding 115). The product-path cell is satisfied by X5. |
| `c823b955`, `92281cc1`, `c54cd6e3`, `851d2ad2` | Runner change; shakedown 16 arms both browsers, mutations 40/40; the K red case on the v8 engine (engine dir swapped and restored; K arms red on the reopen); the R-bs positive control was red for another reason — v8's Home at the document start hangs 30 s (096's shape; v19 carries 096's A half). **A pin I hand-typed was wrong** (`c54cd6e3` appends the correction). Six runners re-pinned to 0.2.8. |
| `ec23ed43`, `65bea447`, `e8243a6c` | **R holds on 0.2.8**: production-ui K 12/12, R 12/12, ctl/S/P 6/6, B-3x 4/4, mutations 40/40; PAGE HONEST, LOCKS LAND (first run), VERSIONS CORRECT, ASSETS DELIVERED, HOST_ENTRY LANDS, SAME-SECOND SAVES KEPT, red cases all red; static exit 0. Findings 109 and 096 got status notes. |
| `89793022` … `29a48a9d` | **Finding 111 measured in browsers** (`tools/probe_111_overtake.py`): overtaking only for near-simultaneous keys — small fixture at 1–6 ms gaps, the owner's document up to ~14 ms (Firefox 10/10), 0 at ≥ 24 ms. |
| `d92d8e70` … `f2dcc4d4`, `7865a509` | **New finding 119 (data loss)**, met by accident in 111's owner-document run and reproduced with `tools/probe_fast_delete_recovery.py --same-page`: on the owner's document a Backspace pressed right after typing can fail with `EDITOR_STATE_UNAVAILABLE` (the selection barrier's negative deadline); the shell made that a rollback in `recoverable-error` with no checkpoint, save disabled, and the only exit reopened the last saved bytes — the typed X was gone. 2 natural failures in about 250 same-page attempts, 0 in 60 fresh-page attempts. |
| `697f296c` | **fable's ruling (owner's authority)**: 119 = D (shell fix now in 109's mould, engine cause registered); 111 = ship in the same release. |
| `65b4dcc6`, `73da170e`, `f26b80a6` | Spec §14 (criteria and predictions first); 119's fix (session + page; checkpoint at the refusal, `restart-required`, auto-reopen, wording never "unchanged", focus after the notice's reopen); 111's fix (session: non-text operations held behind characters still in the input adapter, generation guard). Unit tests and red cases for both. Neither touches E1-C's files (`editor-shell/editor-session.js`, `input/input-adapter.js`) or the engine. |
| `6dbaf7b7` … `1c3edf15` | On the candidate `dist/` (page `537d62d7…`, session `62a2a20e…`): F111-B 160/160 correct; F119-B injection arm 3/3 + 3/3 PASS (auto-reopen in 2.5–3.5 s, X and Y kept, typing without a click lands); natural arm 0 failures in 400 → per the rule written beforehand the natural path is registered 「沒有實例可量」 and the injection arm carries the browser half. Engine root cause C registered in `e2/relink-queue-v3.json` (`6a4015c9`). |
| `37fcb71e`, `521ed923`, `1c254368` | Shell generation **v58** frozen (`a6f9331a…`, differs from v57 in the session and the page only), after both probes. The freeze exposed one static red: the product-path runner's `rollback` mutation anchored on the line U6 rewrote. fable's second ruling: A, re-anchor only that mutation (two strings); witness saved; static exit 0; the re-anchored mutation run once and bit (the recovery cell went red; the declared sentinel abstained by design — reading written down). |
| litecore `069de55`; `db081684` | Host **0.2.9** (version bump; `engine/` re-packaged: buildId `7bf6dbd6142388f1`; 0.2.8's engine archived under `wasm_sdk_probe/build/archive/host-0.2.8-engine-63656ee4aa7e4059/`); seven runners re-pinned (pin lines only; spec §14.6). |
| (running) | The 0.2.9 chain `wasm_sdk_probe/build/m3-count-2026-10-09b/chain.sh`: six shakedowns → production-ui counted → six counted → product-path net (v8 repointed vs v19 plain, 3 rounds × 2 browsers; reader `findings/evidence/release-0.2.9/product-path/judge.py`, roles swapped vs X5, §36.2 row 1′ for the recovery cell only). Started 2026-10-08 23:20 UTC. |

## State

| Item | State |
|---|---|
| R on 0.2.8 | **Holds** (`RESULT-0.2.8.md`). |
| Finding 119 | Fixed in the shell on candidate bytes (unit + browser injection arm); natural path 「沒有實例可量」 (0 in 400 on the fixed page); engine cause C open (queue item `queue-f119-barrier-callback-late-after-insert`). Becomes 已修 only when R′ (the 0.2.9 count) is green. |
| Finding 111 | Fixed in the shell (unit + F111-B 160/160); 已修 only when R′ is green. |
| 0.2.9 | Packaged, upgraded on the dev instance, pinned; **count running**. |
| §34.4 counts (this stretch) | **Check fixes triggered by runs: 1** (the `rollback` mutation re-anchor, witness `release-0.2.9/product-path/test-e2-c-static-before-reanchor.txt`). **Triggered by reviews: 0.** New arms/readers written for this round (the production-ui K/R arms, the 0.2.9 product-path reader copy) are re-bindings ordered by the merge spec §4.4 and the ruling, not fixes of checks. |
| Tree | Clean after each commit; **not pushed** (`git rev-list --count github/main..HEAD` = 462 before this file). |

## Next

1. When the chain ends: read `chain.txt`; red cases on each counted report (as `RESULT-0.2.8.md` did); production-ui pooled red cases; run the product-path reader **after** making it red offline once (copy the 12 reports to a scratch dir, flip one v19 cell where v8 passes to FAIL → P3 MISS); write `RESULT-0.2.9.md`.
2. If everything is green: 119 and 111 → 已修 (119 with the natural path named as not measured), spec §14 result section, memory.
3. Anything red: by the rules in §14.2 and the rulings; a red the rules do not cover goes to fable (the owner's authorisation was for this round).
4. Then: the open list below.

## Open (carried and new)

- **C** (119's engine cause) — measure first (engine-side timestamps between the barrier's unit-selection post and `LOK_CALLBACK_TEXT_SELECTION`), then choose; needs a relink.
- After a failure in the standalone page, opening another document through the file input left typing dead for the rest of that page (111's owner run, 59 trials); not diagnosed; the host hides the file input.
- Carried from 10-08f: 038's drag not wedging 1 in 9; holding Delete; M2-4/M2-1b only on an instrumented page; §33.4 registrations; the v19 Makefile rule packs from `build/`; the ~628 ms emitters; the Firefox `an-inline-format-reaches-a-selection` reds; finding 115; the §28.5 limits.

## Standing rules (new this stretch; a–ff stand)

- **(gg) A full hash in a document comes from the shell, never from the keyboard.** `X=$(sha256sum f | cut -d' ' -f1)` and a heredoc with `$X`; a prefix alone is written as a prefix with "…". (`c54cd6e3`: 48 hand-typed characters in a binding.)
- **(hh) Between a shell change and its generation's freeze, the generation guard test is red by design.** Read "static exit 0" as "every other test passes" until the freeze, and require exit 0 after it (spec §14.5).
- **(ii) When a mutation's declared check is a sentinel that abstains, say which cell carried the capability and why an un-applied mutation would have left it green** (`release-0.2.9/product-path/PREDICTION.md`).
- **(jj) A diagnosis probe that leaves unsaved work hangs on the page's own leave prompt at the next navigation.** Save before moving on (`chrome-same-page-1` attempts 42–43).
- **(kk) Fresh-page and long-lived-page runs are different populations.** 119 never appeared in 60 fresh pages and appeared at the 41st and 61st document of a long-lived page.

## Results of the 0.2.9 chain (appended 2026-10-09, after it finished at 04:11 UTC)

**R′ holds on host 0.2.9** (`findings/evidence/m3-production-ui/RESULT-0.2.9.md`, spec §14.7): six shakedowns clean; production-UI K 12/12, R 12/12, ctl/S/P 6/6, B-3x 4/4, pooled mutations 40/40; PAGE HONEST, LOCKS LAND (first run), VERSIONS CORRECT, ASSETS DELIVERED, HOST_ENTRY LANDS, SAME-SECOND SAVES KEPT, each runner's red cases all red (154/99/68/156/23/70); product-path net P1–P3 HIT, 0 red cells, the two arms equal in all 84 cells, and v19 on the new page has no cell worse than on the old page; static exit 0. **Findings 119 and 111 are marked fixed** (119's natural path named as not measured; its engine cause C stays in the relink queue).

So "Next" above is done through step 2. What remains is the open list. Two of my own slips this stretch were caught by re-reading against the source of truth before they spread: a hand-typed hash (`c54cd6e3`) and an unchecked end time (`66cc9afc`); and two "as before" claims about numbers I had not compared (`a3f2a23e`, `e8243a6c`). Rule (gg) covers the first; the others are the same lesson — a number in a document is read from the file, at the moment of writing.

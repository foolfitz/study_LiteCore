# Handoff, 2026-10-13b — L-132-held-into-refusal measured, finding 134 registered and fixed in page `6470dec0…` (shell v65, host 0.2.16, an uncounted candidate)

The owner chose A (handle L-132-held-into-refusal, measure first; spec §13). After the measurement the owner said 「發給fable，我授權他帶我裁決」, so fable ruled on the owner's behalf: B + D now on the page, C queued for the link batch (`findings/evidence/132/held-into-refusal/ruling/ruling-1.md`). The plain-language reasons are in finding 134's 「裁決」 section.

## Commits (this round)

| commit | what |
|---|---|
| `32aaddb0` | Measurement run-1 (10 rounds, both browsers, all inside §13.3's predictions): (i) a held Backspace at the start burns all three Worker generations in 5.2–5.4 s (Chrome) / 7.1–7.2 s (Firefox), no data lost; (ii) a held Delete at the end, after one refusal, deletes **from the document start** (Chrome 82/83, Firefox 71/72 characters + one paragraph join) and that is saved. Brief, ruling, finding 134 registered before any fix, spec §13.5 (results + correction of §13.1's "not on screen") and §14 (ruling summary). |
| `702c19ec` | Page `6470dec0…`: **B** (`deleteRefusedThisHold`; the rest of a refused hold's repeats are not sent; the hold ends on keyup / a new press / window blur, window capture) and **D** (the engine's last caret read before `restart()`, put back by `placeCaret` after it; otherwise the toast says the caret is at the start). U-B1–U-B4 red on `abe93f45…` first, then 14/14. Probe gains arm `end-press-type`, a `scrollTop` sample and `markParagraphs`; judge `judge_held_into_refusal.py` (per round, per arm over the probe's own ARMS via `ast`). Reds: judge on run-1, fictitious arm, D's red on 0.2.15 (mark in paragraph 0 on both browsers; view jumps from ~21,470 to 0). Engine package buildId `9352fae3aea68b5e` built, host 0.2.16 installed (not committed then). 130-U identical to 0.2.15. |
| `0d7a5020` | Acceptance on host 0.2.16: judge exit 0, four arms, both browsers, 12 rounds. |
| `cf427f46` | Review 1 of the judge (opus, once): 0 BLOCKING. S1 registered as a one-time measurement (deletes reaching the sink after the first refusal: 8 / 74–86 per round before, 0 after); S2 → named limit L-134-judge-per-paragraph; S3 recorded at the freeze. Extra red `red-d-mark-at-end.txt`. |
| `67ba7cf6`…`6e5c6fe6` (sonnet, 7 commits incl. two pin re-binds `c0d507cc`, `e3b9cbfd`) | Condition 4 on `6470dec0…`: 132-B 12/12; 131-B 12/12; 128-B singles ≤ 25.7 ms, host segment `NOT_JUDGED` first (two PUTs, as on 0.2.15) then PASS on the one bounded re-run, red control red; 121-B 4/4; 129-B 54/54, 0 cells differ from both reference rounds; 122-B / C2 12 cells PASS. The main session re-ran the judges and read the same verdicts. |
| `c767934f` | **Shell generation v65 frozen**, `3bffb9463e9b4050940fe637fe5bc58e0703322344c3c5c1c5a6f8b0c2a616bd`; differs from v64 only in the page; `make test-e2-c-static` exit 0 after, E1-C intact. v65 names page `6470dec0…`, session `62a2a20e…`. |
| host `f5b34f0` | **Host 0.2.16** (`info.xml` only; `engine/` = archive `build/archive/host-0.2.16-engine-9352fae3aea68b5e/`, read-only, not in git). `occ app:list` = 0.2.16. |
| `a3c6f81a` | Spec §15 (results per condition, new named limits); finding 134 → fixed (uncounted candidate). |

## State

| item | state |
|---|---|
| Uncounted candidate | **0.2.16**: page `6470dec0…`, shell v65 `3bffb946…`, host `f5b34f0`, buildId `9352fae3aea68b5e`. Supersedes 0.2.15 (differs only in the page). Nominal shipped release is still 0.2.12. |
| Count | Still batched with the next engine-changing release (SPEC-M3-autosave §9.21). Now carries 127–134. The six M3 runners' page pins and the product-path judge copy are **still on `d761f1ce…` / 0.2.14** (not re-bound this round either; 10-13 handoff Next 2 lists the files). The 129-B probe and the two C2 judges are now pinned to `6470dec0…`. |
| Finding 134 | Fixed in 0.2.16. C (engine: at `nothing-selected` with `keyPosted === false`, complete as a no-op success instead of refusing) is written in spec §14 as the link-batch item; its acceptance is `start-press` → 0 refusals, generations `['1']`, red = run-1. |
| L-132-held-into-refusal | Closed (superseded by B1's named limit: one generation per automatic reopen). |
| Owner hand test of 0.2.16 | Not done. |

## Next

1. **Owner hand test of 0.2.16** (nothing in this round touched a real keyboard). Suggested items: (a) at the very end of a document press Delete once → 「正在重新載入…」, about 1–3 s → the caret is back at the end, then typing goes at the end; (b) hold Delete at the end about 2 s → one reload, nothing at the start of the document is deleted; (c) hold Backspace at the very start about 2 s → one reload, **no** 「請重新整理」 notice; (d) the 0.2.15 list (holds mid-text, single presses, autosave) for regressions. Expected and named (L-134-restore-flash): after (a)/(b) the view sits at the document start for about 0.7 s before scrolling back.
2. **Then the owner chooses**: A the link batch (C + the full count of 127–134, overnight, re-binding every pin as 10-13 Next 2 describes, with page `6470dec0…`) or B small items.

## Open / known gaps

1. **C2 near-miss**: Chrome ratio-2 owner-gap-80 on-screen max 148.7 ms against < 150 (on `abe93f45…` it was 41.1); keys 9–12 only, backlog 55.6 / 7.0 ms at keys 10/11; other 11 cells within ~5 ms of the previous run. Not re-run; cause unknown. B adds one sink keydown listener and two window capture listeners that do a few comparisons — an unmeasured reading that this is not B.
2. **L-134-restore-flash**: the caret goes back 0.71–0.78 s after the reopen (pill `busy`, toast still 「正在重新載入…」); ruling F6 had estimated 22–28 ms. Where text typed inside that window lands: review 1 reads from code that it lands at the restored caret; **unmeasured**.
3. **L-134-judge-per-paragraph**: the judge checks the paragraph of the mark, not its offset.
4. Tables / `anchor-mismatch` refusals and 119's `deleteUnverified` reopen go through the same B + D path; neither was measured in a browser this round (no table in the probe document).
5. Probe defect, not product: `deletesSeen` misses the first delete (latency label lag); server read-back and revision spans are authoritative.

## §34.4

因執行而修 0, 因審核而修 0. (The M1-5 / 119 U6 red during implementation was my product change hitting existing checks; the disposition changed the product, not the checks.)

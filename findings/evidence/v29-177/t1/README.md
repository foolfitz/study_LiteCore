# T1: C2 on v29 (2026-11-01)

Spec `specs/SPEC-M3-v29-tick-pacing.md` section 6 T1, append 2. Twelve cells, three rounds, the final page (HTML `ca58f40f`, page `022d0cd0`), desk gate clean before each round (owner closed Chrome and zen). `chain.sh`. The first attempt at r2 stopped on the gate's 1-minute load, raised by r1's own browsers (`log.txt`); r2 and r3 then ran with the gate waiting. r1 stands.

| round | judge_c2 | judge_p2 | Chrome `boundaries` commit | Firefox |
|---|---|---|---|---|
| r1 | PASS | PASS | 8.7 | 9 |
| r2 | PASS | FAIL | 11.3 | 9.7 |
| r3 | PASS | FAIL | 12.3 | 8.7 |

Medians, ms, gate <= 10. `judge_p2`'s only FAIL line in r2 and r3 is `chrome boundaries-gap200 commit median`.

Owner document, gap 80, ratio 2, commit / on-screen median, ms: Chrome 27.3/26.6, 23.7/22.2, 25.5/24.3; Firefox 14.9/12.8, 14.5/13.2, 13.1/11.8. Before v29 this cell was 548.7 (Chrome) and 574.1 (Firefox) ms commit at first contact (`k-0.2.44/first-contact/c2/r1/`, the same probe and cell). Corrected 2026-11-02: this line said 85 ms, which is finding 177's `boundaries` document.

**Reading.** By J-b.2 a `judge_p2` FAIL reads C2 FAIL. By spec section 6, written before the link, a `boundaries` commit over the line is not a v29 failure: the gate was set on v20 and whether it is re-set for the ordered engine is the owner's decision before the next K spec. So T1 is recorded as: C2 3 x PASS; the `boundaries` gate 1 of 3 under the line on Chrome, 3 of 3 on Firefox; decision open.

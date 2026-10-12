# Finding 134 acceptance on host 0.2.16 (ruling-1 condition 3; SPEC-M3-held-key §14)

Probe `findings/evidence/132/held-into-refusal/probe_held_into_refusal.py` (all four arms, default rounds: start-press 1, start-hold 2, end-hold 2, end-press-type 1; both browsers; hold 8 s at delay 500 / interval 30 ms), run 2026-10-13 by the main session. Judge `judge_held_into_refusal.py --page 6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b` → **exit 0, verdict PASS** (`judge-output.txt`).

Static (before = after): host 0.2.16 (info.xml, uncommitted; host repo HEAD still `568608c`), engine package buildId `9352fae3aea68b5e`, served page = dist page = `6470dec0…`.

| arm | Chrome | Firefox | pre-fix (run-1, 0.2.15) |
|---|---|---|---|
| start-press | 1 refusal, gens 1→2, document unchanged | same | same |
| start-hold ×2 | **1 refusal**, gens 1→2, no limit notice, document unchanged | same | 3 refusals, gens 1→2→3, limit `saved` |
| end-hold ×2 | **1 refusal**, gens 1→2, document unchanged, mark in the last paragraph (210) | same | 71–83 chars deleted from paragraph 0, saved |
| end-press-type | 1 refusal, gens 1→2, **typed mark in the last paragraph (210)** | same | mark in paragraph 0 (`../red-d-on-0.2.15/`) |

Red cases (produced before this green): `../judge/red-a-run-1.txt` (the judge on run-1 fails start-hold and end-hold on their rules, passes start-press, fails end-press-type as absent), `../judge/red-unknown-arm.txt` (a fictitious arm in the probe's ARMS fails), `../red-d-on-0.2.15/` (D's red: mark in paragraph 0 on both browsers).

## Observed, not judged

- **`#desk.scrollTop`** (condition 7): on the end arms the view jumps to 0 when the new generation is ready, and back to 21477 (Chrome) / 21463 (Firefox) when the caret is put back. On the start arms it stays 0.
- **The caret goes back 0.71–0.78 s after the reopen** (end arms; Chrome 1928→2663, 1888→2638, 1475→2187 ms; Firefox 2818→3575, 2804→3579, 2217→2965 ms from the first keydown). During that time the pill reads `busy` (it reads `ready` for about 1 ms first) and the toast still says 「正在重新載入…」; 「已重新載入。」 follows the caret. So the user sees the view at the document start for about 0.7 s and then back. Ruling-1 F6 estimated the window in which typed text could land at the start as one click acknowledgement (22–28 ms); measured it is about 30 times that. Where text typed inside that window lands: **not measured** (the probe types after a 2.5 s settle). Review 1 reads from code that it lands at the restored caret: `placeCaret` is queued in the same task as the focus, and the refusal had already emptied the typing queue (`../review/review-1-judge.md`). That reading is still unmeasured.
- Toasts: on the end arms the post-reopen toast has no 「游標現在在文件開頭」 sentence, i.e. D reported success on every round.

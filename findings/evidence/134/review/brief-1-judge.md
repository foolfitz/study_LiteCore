# Review brief 1 — adversarial review of the finding-134 judge (ruling-1 condition 9; one pass only)

You are the one adversarial review this judge gets (§34 stop rule: each reading tool is reviewed once; no verification of the verification after this). Your job is to find a way the judge says PASS while finding 134 is not fixed, or FAIL for a reason unrelated to it — "broken but green" first.

Read:
- `findings/evidence/132/held-into-refusal/ruling/ruling-1.md` — condition 3 is the judge's specification; conditions 1, 2 and 7 define what it judges.
- `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py` — the judge.
- `findings/evidence/132/held-into-refusal/probe_held_into_refusal.py` — the probe whose report it reads (`summarize()`, `server_read()`, `run_round()`, `INSTRUMENT`).
- The page change under test: `git diff 32aaddb0 -- wasm_sdk_probe/web/e2-editor-app.js` (B: `deleteRefusedThisHold`, `dropsRefusedRepeat`, `endsHeldDelete`; D: the caret read before `restart()` and the click after it in `reopenAfterBoundaryRefusal`).
- Red cases already produced: `findings/evidence/134/judge/red-a-run-1.txt` (judge on the pre-fix report run-1: start-hold and end-hold FAIL on their rules, start-press PASS, end-press-type FAIL as absent), `findings/evidence/134/judge/red-unknown-arm.txt` (a fictitious arm added to the probe's ARMS → FAIL), `findings/evidence/134/red-d-on-0.2.15/report.json` (the new arm on the pre-fix page: mark landed in paragraph 0).

Questions:
1. Construct concrete reports (or page behaviours) for which the judge exits 0 while (a) a held key at either end still reaches the engine after the refusal, (b) the next input after a reopen still lands away from the caret, or (c) the document is changed. For each: is it reachable with this probe and this page, or only by a hand-made report?
2. Are the per-round rules right for each arm under B+D? In particular: `start-hold` with B — is `refusals == 1` really what B+D produce (the five typed letters are deleted before the start is reached; D puts the caret back at the start; B drops the rest); `end-hold` — is `sameAsOriginal True` with `marks == 1` the right reading when the mark is typed before the hold; `end-press-type` — `markParagraphs == [last]`.
3. `summarize()` counts a refusal as a transition into `restart-required`. Can a refusal that does not reopen (e.g. the gesture-gate refusal "no selection has been reported yet", which costs no generation) or a reopen that is not a refusal escape or inflate the count in a way that flips a verdict?
4. Is the static check (served page and dist page equal the named sha; `static == staticAfter`) enough to bind the verdict to the bytes under test?
5. Anything in the probe that makes the rounds non-independent (server file reuse, locks, the owner's Firefox).

Output to `findings/evidence/134/review/review-1-judge.md`: BLOCKING (judge passes a broken fix, or fails a correct one, on a reachable path) / SHOULD / NOTE, each with file:line and the concrete report or behaviour. Do not edit anything else; do not run browsers or the probe; do not commit. Reply with the file path and a ≤20-line summary.

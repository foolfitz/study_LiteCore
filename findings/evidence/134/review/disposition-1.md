# Disposition of review 1 (judge for finding 134), main session, 2026-10-13

Review: `review-1-judge.md` (opus, one pass, §34). 0 BLOCKING, 3 SHOULD, 9 NOTE. No check, judge or probe is edited because of it: 因審核而修 0.

- **S1 (B is judged only through its consequences) — registered as a one-time measurement, no new rule.** Delete-type `beforeinput` events after the first `restart-required`, recomputed by the main session from the two reports:
  - run-1, pre-fix: start-hold 8, 8 (Chrome), 8, 8 (Firefox); end-hold 85, 86 (Chrome), 74, 75 (Firefox).
  - acceptance, 0.2.16: **0 in all eight hold rounds.**

  The reviewer's short-hold path (a hold that ends before the reopened engine takes a repeat would pass a page without B) needs `--hold-ms` under about 3 s. It does not apply at the probe's default of 8 s, where 131–171 repeats per round reached the sink more than 1 s after the new generation was ready. Adding the rule would edit a judge, which §34 allows only with a witness report. Not done.
- **S2 (D judged per paragraph, the claim is per caret) — named limit of the judge.** `mark_at_end` accepts the mark anywhere in the last paragraph, which is 72 characters and at least two lines. A D that restored to some other point in that paragraph would pass. Judging the position needs a new probe field and cannot be applied to existing reports. Registered as **L-134-judge-per-paragraph**, not fixed.
- **S3 (verdict bound to the page bytes, not the release) — taken at condition 5.** At the v65 freeze and the host 0.2.16 commit, record three things: the page and session v65 names (`6470dec0…`, `62a2a20e…`), and the buildId of the committed host's engine (`9352fae3aea68b5e`). This is a recording step and needs no judge change.
- **NOTE, missing red — done.** `../judge/red-d-mark-at-end.txt`: the judge on `../red-d-on-0.2.15/report.json` prints `mark in paragraphs [0], last is 210` for both browsers and exits 1.
- **NOTE, typed keys during the ~0.7 s restore window (reviewer, read from code, not measured).** The reviewer's code reading says text typed in that window lands at the restored caret, not at the start. `placeCaret` is queued in the same task as the focus, and the refusal had already emptied the typing queue. This contradicts ruling-1 F6's sentence on the window. The acceptance README records it as the reviewer's reading. Still unmeasured.
- **NOTE, placeCaret's timeout is `EDITOR_CARET_NOT_PLACED`, not `TIMEOUT` (reviewer).** It does not block the queue. This corrects ruling-1 F6's "TIMEOUT is in RECOVERY_ERRORS" for this path. Recorded only.
- **Other NOTEs** (refusal counter relies on catching a 0–1 ms `restart-required`, which can only fail a correct fix, never pass a broken one; headless rounds have no desktop blur; contamination across rounds fails through `marks`; the report carries no sha of the probe or judge; the verdict line omits the browsers; the server comparison is text-only): recorded, no action.

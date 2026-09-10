# 095 — is the click's silence the pre-death window of 096?

Protocol: `handoff/tasks/TASK-2026-09-10-095-is-it-096s-window.md`, registered
before the probe was written; its Execution record carries the shakedown fix
made before the first counted attempt (a placement-click change, not a
criterion change). This directory answers one question — does 095's silent
click sit inside 096's known 30 s wedge, on profiles without half A, and does
the long fixture avoid it because the press it lands on is not actually a
boundary press — and names no cause beyond what the probe's own criteria
force.

## The nine attempts

| arm | attempt | profile | fixture | caret moved after press | click placed caret | seconds to dead state | notice rescue | revision before / after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S8 | 1 | e2-editor-v8 | a11y-audible.odt | false | false | 30.001 | none | 0 / 0 |
| S8 | 2 | e2-editor-v8 | a11y-audible.odt | false | false | 30.001 | none | 0 / 0 |
| S8 | 3 | e2-editor-v8 | a11y-audible.odt | false | false | 30.0 | none | 0 / 0 |
| S14 | 1 | e2-editor-v14 | a11y-audible.odt | false | true | null | — (not died) | 0 / 0 |
| S14 | 2 | e2-editor-v14 | a11y-audible.odt | false | true | null | — (not died) | 0 / 0 |
| S14 | 3 | e2-editor-v14 | a11y-audible.odt | false | true | null | — (not died) | 0 / 0 |
| L8 | 1 | e2-editor-v8 | a11y-long.odt (133 paragraphs) | true | true | null | — (not died) | 0 / 0 |
| L8 | 2 | e2-editor-v8 | a11y-long.odt (133 paragraphs) | true | true | null | — (not died) | 0 / 0 |
| L8 | 3 | e2-editor-v8 | a11y-long.odt (133 paragraphs) | true | true | null | — (not died) | 0 / 0 |

Raw evidence: `s8-e2-editor-v8.json`, `s14-e2-editor-v14.json`,
`l8-e2-editor-v8-long.json`, and the shakedown that forced the probe's own
fix, `shakedown-1.json`.

## Per-arm reading against the pinned cells (protocol §2)

**S8 — MET, 3/3.** `clickPlacedCaret == false` while the press was pending
(`#s-latency` blank throughout — `latencyAfterPress` and `clickLatencyText`
both `""` on all three); `died == true`, `deadState ==
"recoverable-error"`, `noticeRescue == "none"`; `timeToDeadStateSeconds`
30.001 / 30.001 / 30.0, inside the pinned [29, 31] window and matching
096's own 30002–30003 ms; `revisionBeforePress == revisionAfterWatch ==
"0"` on all three. `noticeText` is character-identical to the owner's
quote on all three. Neither of the two named red conditions fired.

**S14 — MET, 3/3.** The press was answered fast (`下移一行 255–256 ms`,
close to 096's own after-the-link figures of 259–263 ms);
`clickPlacedCaret == true` at 0.757–0.759 s after the click started, well
inside the pinned 5 s; `died == false` through the full 65.1 s watch on
all three. Neither named red condition fired.

**L8 — MET, 3/3.** `caretMovedAfterPress == true` on all three (78→74 ms
range... actually `下移一行` 74–78 ms, `moveWatch.movedAfterSeconds`
0.151–0.155 s): the press was an answered move, not a boundary press by
the probe's own criterion. `clickPlacedCaret == true` at 0.785–0.786 s.
The named red condition (`caretMovedAfterPress == false` **and**
`died == false`) did not fire, because the first half of it — no
movement — was false on all three attempts.

## Positive-control rule (protocol §3)

**Met.** S8 died 3/3 and S14 did not die 3/3, in the same task session —
the instrument is not suspect; L8's cell is read as informative.

## What forced the fixture dependence, read from the probe's own evidence

L8's full-canvas ink scan found 682 ink bands on a 27,198 px canvas (the
canvas is not height-capped; it grows to fit the document) and the click
landed on the last one, `rowsBelowCount: 0` — the scan really did reach
the bottom of what was PAINTED. The single ArrowDown from there still
moved the caret in under 200 ms on all three attempts, which by the
probe's own moved/died criterion means it was not a boundary press: LOK
found somewhere to go from the last VISIBLE band. On the short fixture the
symmetric click (same `["past"]`-fraction placement, same single press)
wedged for the full 30 s on all three attempts. The difference between the
two fixtures is therefore in the document model past the last painted
ink, not in the probe's placement or its criterion — consistent with, and
no more than, the protocol's own §2 gloss for a green L8: "the fixture
dependence is explained by 'not a boundary press' — nothing more."

## Observed, not covered by any prediction — recorded, not explained

- **S14's press did not move the caret either** (`caretMovedAfterPress ==
  false`, all three), yet the session did not die and the click landed.
  Protocol §2 pins only that the press is answered fast and the click
  succeeds; it does not say whether the caret moves. Both S8 and S14 show
  `caretMovedAfterPress == false` — the two arms are told apart only by
  whether the session then wedges, not by whether the caret visibly moved.
- **`workerLiveness` accumulates stale worker sessions across attempts
  within one run.** Attempts 2 and 3 of every arm carry one or two entries
  with `"answered": false, "error": "...Session with given id not
  found."` before the live worker's own entry (`"answered": true`) — the
  probe's `worker_sessions` dict is never pruned of a prior attempt's
  detached worker, the same as `probe_096_boundary_arrow.py`'s own design
  (one `BufferingSession` reused across `--attempts`). The live worker
  answered in 0.0 s on every attempt in every arm; this is a bookkeeping
  artifact, not a signal about the product.
- **The boundary-press latency itself falls into two distinct clusters
  by arm, not by attempt**: S14 255–256 ms, L8 74–78 ms, both far above
  096's own pre-boundary baseline (37–39 ms) and neither addressed by any
  pinned criterion. Registered because it is a number the raw JSON carries,
  not because either width is predicted.

## Conclusion this task is licensed to state (protocol §5)

S8 and S14 are both green. 095 is re-attributed as the pre-death window of
096 on profiles without half A — see the appended zh-TW section on
`findings/095-*.md`, which keeps the file rather than merging it into 096.
L8 is green: the fixture dependence is explained by "not a boundary
press," and nothing further is claimed about why the core does not
broadcast at a boundary, or about the long document's true paragraph
count past the last painted band.

The harness-path caveat on the click stands: every click in this task is a
canvas `pointerdown` over CDP, not a physical mouse. What changes is what
the caveat is now a caveat ABOUT — with S8 and S14 green, the pending move
is the unit under test, and the owner pressed real arrow keys for 096; the
click is no longer load-bearing for attributing 095 to 096's window.

## Main-session pre-read (2026-09-10, append-only)

The nine attempts were re-read from the JSON with an independent reader
(first version treated `attempts` as the list; it is the count, the records
are in `runs` — caught by the raw value in the exception). Cells agree with
the table above.

**L8's seam, and what the fixture says.** `lastLineEvidence` reports the full
canvas scanned, the click on the last ink band, `rowsBelowCount: 0` — and the
same attempt reports the press answered as `下移一行` with the caret moved.
Both are true only if something inkless lies below. Read, not inferred:
`dist/a11y-long.odt`'s content.xml ends with
`<text:p text:style-name="Text_20_body"/>` — an empty paragraph, the last of
133 — while `test-docs/e1/a11y-audible.odt` ends with a non-empty paragraph.
So on the long fixture the last ink band is not the document's last line, and
on the short one it is. Rule for any probe that finds "the last line" by ink:
**ink locates the last painted line, never the document boundary.**

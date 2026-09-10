# TASK — is finding 095 the pre-death window of finding 096?

Pre-registered protocol for the T9 brief in
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, section "T9 — is
finding 095 the pre-death window of 096? (2026-09-10, append-only)".

**Written and committed before the probe exists.** Nothing below may be
edited after the first attempt that counts; corrections go in an appended
`## Execution record` that names what it supersedes (AGENTS.md §10). The
criteria below are restated from the brief in the form of JSON field names
this task's probe will emit; they are not widened, weakened, or added to.

**This task may not name a cause.** It tests one prediction about *when*
095's symptom occurs relative to 096's known death, on three arms. Why the
core does not answer a boundary move is out of scope (096's own standing
limit).

---

## 0. The question and the prediction, from the 096 trace

Finding 095: after ArrowDown at the document's last line, the next canvas
click places no caret — `#s-latency` blank for 25 s (the probe's own wait
cap, not a measured recovery time), no error, no toast, no notice. Observed
on `e2-editor-v8` and `e2-editor-v12`, short fixture, 6/6; the same click on
a 133-paragraph fixture (`a11y-long`) succeeded.

Finding 096: a boundary arrow press on a profile without half A leaves
`gEditorPending` armed forever; every later action or caret placement
answers `BUSY`; the SDK gives up after its own 30000 ms deadline and the
session enters `recoverable-error`. On `e2-editor-v14` (half A landed and
linked) the same press is answered in ~260 ms and nothing wedges.

**The prediction under test**: 095's click landed inside exactly this
window. On a profile without half A (v8, v12), the boundary press arms no
deadline, so the click 2 s later finds the session still `BUSY` and places
no caret; 095's probe stopped 5 s short of the 30 s deadline that would have
ended the wait with the no-checkpoint notice. On `e2-editor-v14` the press
is answered fast enough that the click lands. The fixture dependence is
predicted too: on the 133-paragraph document the *last painted line* is not
the document's last line, so the press made in 095's original observation
was never a boundary press and nothing wedged.

## 1. The three arms

All three: `Input.dispatchKeyEvent` for the key (not a synthesised
`KeyboardEvent`, not `session.action(...)`), the caret placed by a canvas
`pointerdown`, the fixture handed to the product's own `#file` input (not
the fixture-selector `probe_093_fix_shape_oracle.py` uses — recorded as a
deliberate divergence from 093's UI path, not from its file bytes, in the
probe's own docstring), engine state read the way
`findings/evidence/096/probe_096_boundary_arrow.py` reads it: its RAW CDP
event buffer, the worker's own console reached through
`Target.setAutoAttach`, the toast observer, and the state-pill transition
trace with page timestamps.

| arm | profile | fixture | attempts |
| --- | --- | --- | --- |
| **S8** | `e2-editor-v8` | `a11y-audible.odt` (short, 10 paragraphs) | 3 |
| **S14** | `e2-editor-v14` | `a11y-audible.odt` | 3 |
| **L8** | `e2-editor-v8` | the long fixture 095 used — `wasm_sdk_probe/dist/a11y-long.odt`, 133 paragraphs, installed into a scratch mirror exactly the way `probe_093_fix_shape_oracle.py`'s `install_long_fixture()` does (copy the bytes; nothing under `web/` or `dist/` is written) | 3 |

Per attempt: place the caret on the last line (found by an ink-band scan of
the whole canvas, floor 20 / limit 0.5×width — the same thresholds
`probe_096_boundary_arrow.py`'s `text_row()` uses, reused here because this
task additionally needs the *count* of bands, which `text_row()` does not
return); press **ArrowDown** once; at **+2 s** after the press, attempt one
canvas click near the top of the document using
`probe_093_fix_shape_oracle.py`'s `click_to_top(session, timeout=25.0,
ys=("0.09",))` — the exact call (`ys=("0.09",)`, one value, not the
function's four-value default) that produced 095's original observation,
so this arm measures what 095 measured and not a wider search over click
points; watch the state pill for **at least 60 s after the press** before
concluding "no dead state".

## 2. Criteria, pinned before the probe exists — per-attempt JSON fields

Every attempt record carries at least: `profile`, `fixture`,
`lastLineEvidence` (`{bandIndex, bandCount, fraction, scanCoveredFullCanvas,
rowsBelowCount}` — the probe's own evidence that the pressed line was the
last painted band, not an assumption), `pressedAt` (wall clock) and
`pressPageMs` (page `performance.now()`, same clock the state-pill trace
uses), `caretMovedAfterPress` (bool, 096's own before/after `sinkTop`/
`sinkLeft` criterion), `latencyAfterPress`, `clickStartedAt`,
`clickPlacedCaret` (bool: `定位游標` in `#s-latency` and not `失敗`),
`clickLatencyText`, `statePillTrace` (page-timestamped transitions),
`timeToDeadStateSeconds` (float or `null`, relative to `pressPageMs`),
`died`, `deadState`, `noticeShow`, `noticeRescue`, `noticeText`,
`revisionBeforePress`, `revisionAfterWatch`, `watchedSeconds` (>= 60),
`workerLiveness`, `toasts`, `pageErrors`, `cdpEvents`, `cdpEventsFromWorker`.

### S8 (v8, short fixture) — predicted

* `clickPlacedCaret == false` (no caret placed while the press is pending)
* `died == true`, `deadState == "recoverable-error"`,
  `noticeRescue == "none"`
* `timeToDeadStateSeconds` between 29 and 31
* `revisionBeforePress == revisionAfterWatch`

**Red for the prediction**: `clickPlacedCaret == true`, OR `died == false`
by 60 s after the press.

### S14 (v14, short fixture) — predicted

* the press is answered within 1 s: `caretMovedAfterPress == true` is not
  required by this arm's own gesture (the press is at the boundary, so the
  caret need not move for the press to be *answered*) — what is predicted
  is that the session stays `ready`/serviceable, evidenced by
  `clickPlacedCaret == true` within 5 s of the click starting
* `died == false` through the full 60 s+ watch

**Red**: `clickPlacedCaret == false`, OR `died == true` within the watch.

### L8 (v8, the long fixture) — predicted

* the press is **not** a boundary press: `caretMovedAfterPress == true`
  (an answered move under 1 s, by the sink-position criterion)
* `clickPlacedCaret == true`

**Red**: `caretMovedAfterPress == false` (a boundary press by the probe's
own criterion) **and** `died == false` (nothing wedges). If that cell is
red, the fixture dependence stays unexplained and finding 095's P1 sentence
may not be quoted to explain it — that must be written down, not patched
over.

## 3. Positive-control rule

**S8 must die and S14 must not, in the same batch.** If S8 does not die, or
S14 dies, the instrument is suspect before the product is — report that
first and do not read L8's cell as informative until the control pair is
resolved.

## 4. Default conclusion if this task is never run

095 stays "observed, not investigated" and may not be cited as 096's
pre-death window in any file this tree writes.

## 5. What a green does and does not license

**S8 + S14 green**: 095 is re-attributed as the pre-death window of 096 on
profiles without half A — recorded as a section appended to 095 (the file
is kept, not merged into 096), with a cross-reference to 096. The
harness-path caveat on the *click* remains (no real mouse here), but the
click is then no longer the unit under test: the pending move is, and the
owner pressed real keys for 096.

**L8 green**: the fixture dependence is explained by "not a boundary
press" — nothing more. It does not license any claim about why the core
does not broadcast at a boundary, and it does not retire 095 as its own
finding.

**Any of these red**: report exactly which cell was red and stop; no
narrowing beyond what that cell forces.

## 6. Constraints on the executor

Probe and JSON under `findings/evidence/095/`; `RESULT.md` in English; one
appended zh-TW section on `findings/095-*.md`; one appended
`## Execution record` here. No `build_cutover_page.py --write`, no `make`,
no edit under `src/ sdk/ web/ editor-shell*/ dist/ tools/`, no edit of
`findings/096-*.md` or anything under `findings/evidence/096/`, nothing
else run. One browser at a time. Count Chrome processes before and after
(by exact binary name / `/proc/*/exe`, never `pgrep -f`); kill only what
this task starts. Commit per unit, zh-TW subjects, trailer
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, no
`Claude-Session:` line, no push.

---

## Execution record

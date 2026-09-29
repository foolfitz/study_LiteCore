# Page honesty — shakedown reports

Runner: `wasm_sdk_probe/tools/check_m3_page_honesty.py --label shakedown`.
Spec: `specs/SPEC-M3-page-honesty.md` §4 as amended by §7 (runner fixes that
came out of these runs: §7.9, §7.10). Dev instance `litecore.ddev.site`, host
0.2.3 (`c740d2f`), page `f42e0227…`, session subclass `747eea71…`, engine
`4aa3646d4e540b32` (profile `e2-editor-v8`, wasm `4a2710bb…`). None of these
reports is a counted run; the page and session bindings are not pinned yet.

Every report holds the raw record of each arm; `--score REPORT` re-scores it
with the runner as it is now (so an old report can score differently from what
its run printed — see "scoring changed" below).

## First pass, 2026-09-29 (UTC)

| Report | Browser | Arms | Printed | What it showed |
|---|---|---|---|---|
| `091307` | Chrome | U0 | clean | The recorder works: `installed`, `fired`, the ask attributed to `runner` by stack, a CDP dialog, cancel keeps the page. |
| `091341` | Chrome | U1 | arm ok, report `problems` | By design: a U cell counts only with a clean U0 in the same browser and round, and this report had no U0. Raw record: both leaves guarded by the host with reason `page`, lock `held` and the server token unchanged after each cancel, then a 204 with the token onto the original, no copy, third leave not asked. |
| `091432` | Chrome | U0 Uwin U2 U3 U4 U5 U7 | clean | Uwin's trap fired while the host had recorded 0 saves and the guard reason was `page` only (the window, not `inFlight`); U4 reached 412 and a conflict copy; U2/U5 negatives have `fired` and no ask. |
| `091642` | Chrome | U0 U6a U6b Kheld Ksep Ktwo | clean | Download mode: the page asks (stack `page`), not after the download. Held Ctrl+S: 30/30 keydowns prevented, 1 host save. K-sep: two presses 2 ms apart, 2 saves. |
| `091816` | Chrome | Vro Vrw | **both red** | Both arms died before the census: the V4 click at canvas y 0.28 lands BELOW this fixture's text, so the caret goes to the LAST line, and ArrowDown there is finding 096 (the shipped v8 engine: 30 s timeout, `recoverable-error`). Not the view-only gate — the writable control died the same way. |
| `diag-v4-first-line/` | Chrome | — | — | Diagnostic (not a runner): the canvas ink bands of the five paragraphs are at 0.10–0.21 of the canvas height; a click at 0.28 puts the caret where a click on the fifth band does (sink top 598.39); from the first band ArrowDown answers `下移一行 38 ms`, `ready`, sink top 497 → 519. |
| `093035` | Chrome | Vro Vrw | Vro clean, Vrw red | After aiming at the first line (runner `TEXT_LINES`): Vro clean. Vrw: `delete-forward` with the caret at a paragraph's end is a cross-paragraph delete, refused by contract (`EDITOR_BOUNDARY_UNSUPPORTED`, session `restart-required`, SPEC-E1-C:139); every later item was then refused. |
| `093656` | Chrome | Vrw | clean | After laying out the precondition (one `move-character-left` before `delete-forward`): all 17 content-changing controls advance the revision. `move-character-left/right` show `失敗` here — the census had left a range selection, the page disables moves for a range, the runner force-enables them, and the session refuses with `EDITOR_FORMAT_GESTURE_UNSUPPORTED` (document unchanged, state `ready`): the designed gesture mask. Moves are exempt from "must advance"; that they work is V4/V7's job (they succeed in Vro, which has no selection). |
| `093838` | Firefox | all 15 | clean | First Firefox run. Stack attribution works with the `//# sourceURL=m3honesty-runner.js` function (`runner`/`host`/`page` all seen); localStorage is readable after the navigation (`fired` in every cell); WebDriver accepts the leave prompt, so asked cells still reach `/apps/files/`. |

### Scoring changed after these runs (§7.10)

- V2 now requires the census to cover every control the page lists (except
  `open-file`) — `093035` and `093656` still score clean.
- U7 now requires `#s-pending > 0` at `beforeunload`, read by the recorder.
  The first-pass reports have no such field, so their U7 rows now score red
  (`leave: pending '' at beforeunload`). That is the instrument changing, not
  the product; the final pass below carries the field.

## Final pass on the current runner, 2026-09-29 (UTC)

The runner as committed after §7.9/§7.10 (first line aim, the `delete-forward`
precondition, census coverage, `#s-pending` at `beforeunload`), one full round
per browser:

| Report | Browser | Result |
|---|---|---|
| `095133` | Chrome | clean, 15/15 arms |
| `100026` | Firefox | clean, 15/15 arms |

Red cases on these two reports: `red-cases-on-095133-100026.txt` —
`check_m3_page_honesty.py --red-cases 2026-09-29T095133+0000.json 2026-09-29T100026+0000.json`:
**116 red, 0 not red or missing.** Each case counts only if the problem it
causes contains the criterion's own string (not just any problem); one
report-level case checks that a failed U0 voids the same browser's U cells.

## The other two runners on the same page and host (same session)

- `findings/evidence/m3-assets/shakedown/2026-09-29T101213+0000.json` — K0–K2,
  one run per browser, with K2's save before each leave (§7.8). Both runs
  clean; the report is red only on `static: page` (`PAGE_SHA256` still names
  the old page — bindings are filled before counting, step 8). Per open: the
  save a 204 with the token, the leave's `fired` with no guard, the lock gone
  1.5–1.9 s after leaving, the second open (the saved document, the same
  paragraph action again) advancing the revision. Red cases:
  `red-cases-on-2026-09-29T101213.txt`, 90 red, 0 not.
- `findings/evidence/m3-locks/shakedown/2026-09-29T101313+0000.json` —
  K9′/K10′ only (§7.4), one run per browser each. The premise held in all
  four: the share read back 3 at open and 1 after the cut, the server's lock
  (owner `lcprobe`) still there at the cut, the PUT **403 with the token**
  (not 412). K9′: copy 201 in the recipient's folder. K10′: copy 403 →
  stranded; in Chrome both leaves guarded by the host with reason `stranded`.
  Red cases: `red-cases-on-2026-09-29T101313.txt` — every K9′/K10′ case red;
  the other arms are MISSING because this report ran only these two (a full
  locks shakedown is still due before counting).

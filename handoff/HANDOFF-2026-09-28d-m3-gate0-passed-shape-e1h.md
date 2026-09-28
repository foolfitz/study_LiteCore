# Handoff, 2026-09-28 (d) — M3 gate 0 passed, shape E1h

Entry points, in order: this file, `findings/evidence/m3-gate-0/RESULT.md` (verdict,
PASS sentence, named limits, measured table), `handoff/m3-gate-0/RULING.md`,
`research/ROADMAP-2026-08-20-milestones.md` §5.1 / §5.3.

## What happened this round

The owner was away and said "execute autonomously". Nothing needed a new decision: every
step came from fable's ruling (09-28c), so fable was not consulted again.

1. Reader `check_m3_gate0_report.py` run on shakedown 4: `VERDICT E1h` with
   `--allow-shakedown`, `NOT_ESTABLISHED` on (a) without it; `--red-cases` 24/24 red on
   the predicate each names. Shakedown 4's runner sha256 = the committed runner
   (`0be9f551…`). Committed before any counted data: `a9759513`.
2. Counted run `runs/2026-09-28T065153Z-apache-fpm.json` (06:51–07:01Z, ~10 min, not
   ~40) + `occ` evidence beside it: `da1ac151`.
3. Reader on it: **`VERDICT E1h shapes=E1h,E3 failing={}`**. Every prediction held.
4. RESULT.md + roadmap §5.1/§5.3 + research note §3.2 (zh-TW) + PREDICTION.md "Closed"
   append: `fd1aa2b7`.

## The adversarial fact-check (opus), and what it found

The prose was the only author-judgement part, so it went to an opus reviewer before
commit. 16 items: 4 wrong, 7 overstated, 5 notes. All were verified against raw fields
or sources before fixing (B′ rule: a subagent's diagnosis is a hypothesis until read).

The ones that matter beyond this gate:
- `external/richdocuments-listener.md` quoted the **author** date (2023-10-26). The
  listener shipped in `v8.4.0` (2024-04), behind `hasWASMSupport()`. The ruling
  (verbatim, not edited) inherited the error. A correction is appended to the evidence
  file.
- #4103's mechanism is "an app sets COEP on pages other apps own", not "an app injects
  cross-origin loads into every page". Both directions are now named separately.
- "In-place in Files is infeasible" was never measured: the editor never ran inside
  Files, and A4d (DIP iframe) isolates in Chrome. Own-routes-only is **the ruling's
  choice**, for #4103's reason. The roadmap now says so.
- Firefox E0 has no attribution field (toast `TIMEOUT … 120000 ms`), and neither does
  Firefox E1 (`WORKER_CRASHED`). Only Chrome attributes. Correlation plus the browser
  rule, stated as such.
- Instrument limit: the resource-timing list on the Files pages (A5 / A5-control) is
  capped at 250 entries (the browser default). No criterion reads it; it would matter if
  anyone later wants "every subresource was same-origin" on Files.

## State

- Tree clean after `fd1aa2b7` (apart from this file). Not pushed.
- Nextcloud instance `~/Projects/Nextcloud_Apps/litecoreprobe` is still running (ddev),
  probe app `f837937`, clean. Nothing depends on keeping it up.
- The soak gate for the v14 cutover is where 09-28b left it: 0/12, not cut over.

## What is next — the owner's call

- **A. Cutover path** (unchanged from 09-28b): freeze v14 + shell v52 + page, T4, 12-run
  soak over ≥ 3 UTC days. Until then v48 is what users get, and v52 fixes (098/099)
  do not reach them.
- **B. Continue M3 on the E1h shape.** Recommended if development continues before
  cutover. The smallest real step is an app skeleton: a Files action on `.odt` opens the
  E1h route and reads the file over WebDAV. Save, locking and versions come after that.
  Two design questions surface immediately, and both are the owner's to decide:
  (1) v14's `.data`/`.metadata` (40 MB) are 404 as static files under Apache's
  whitelist, so they must go through PHP, a rename to a whitelisted extension, or
  another route (roadmap §5.3). (2) Which of CONDITION 7's four COEP routes replaces
  PHP for the engine scripts, if any. PHP-served JS is small (worker 63 KB), so keeping
  PHP is a legitimate answer.
- **C. Instrument debt** (unchanged): make the worker-failure inducer re-armable.

My inclination: **B**, starting with the skeleton. Question (1) decides whether v14 can
ship inside Nextcloud at all without PHP streaming 40 MB, and it only shows up once a
real app serves v14.

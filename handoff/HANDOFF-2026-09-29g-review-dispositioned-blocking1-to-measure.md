# Handoff, 2026-09-29g — review dispositioned, BLOCKING 1 confirmed by reading source but not measured

Entry points: this file, `specs/SPEC-M3-page-honesty.md` §7.8 (K2 ruling A′, owner-facing WHY, 12
conditions) and §7.9/§7.10 (shakedown-forced runner fixes),
`findings/evidence/m3-page-honesty/review-2026-09-29-opus-implementation.md` (implementation
review, verbatim text + disposition table),
`findings/evidence/m3-page-honesty/shakedown/README.md` (per-report table),
`findings/evidence/m3-page-honesty/unit-red-cases/` (README + JSON, includes the new page red
cases), `findings/evidence/m3-assets/shakedown/2026-09-29T101213+0000.json` (condition 10),
`findings/evidence/m3-locks/shakedown/2026-09-29T101313+0000.json` (K9′/K10′ premise) and
`.../2026-09-29T101606+0000.json` (full locks shakedown, 22 arms),
`wasm_sdk_probe/tools/probe_m3_save_throw.py` (new probe for BLOCKING 1, never run),
`findings/evidence/m3-page-honesty/save-throw/host_fix_0_2_4.py` (fix script, in repo, NOT
applied), `wasm_sdk_probe/tools/check_m3_page_honesty.py`, `check_m3_assets.py`,
`check_m3_locks.py` (runners touched this round).

Picks up from `handoff/HANDOFF-2026-09-29f-page-honesty-implemented-not-shaken-down.md`. Commits
this session (`study_LiteCore`, `main`, not pushed): `85d4282e` (spec §7.8/§7.9), `1dc85602`
(first shakedown round, K2 ruling A′ landed on the runner side, K9′/K10′ runner),
`52743e62` (final shakedown evidence), `b61e9fd9` (implementation-review dispositions part 1:
page, tests, runner), `d7081a00` (full locks shakedown evidence + host 0.2.4 fix script, not
applied). Host repo `~/Projects/Nextcloud_Apps/litecore` is still at `c740d2f` (0.2.3), clean —
**the 0.2.4 fix is NOT applied.**

## Status

**K2 ruling (fable, on the owner's authorization) = A′ — 11 of 12 conditions done, one code-only
and never run.** `specs/SPEC-M3-page-honesty.md` §7.8 holds the ruling, the owner-facing WHY text,
and 12 conditions.

- Done: conditions 1–8 (spec; runner `check_m3_assets.py` gets a save-before-leave step and two
  "K2 instrument" clauses plus 3 red cases; `SPEC-M3-asset-delivery.md` gets a revision row;
  finding 105 gets prose appended plus a 裁決 section), 10 (assets shakedown
  `findings/evidence/m3-assets/shakedown/2026-09-29T101213+0000.json`, both browsers clean except
  one unpinned `static: page`; red cases 90/90 in `red-cases-on-2026-09-29T101213.txt`), 11 (a
  Firefox U1 shakedown now exists), 12 (registered).
- Condition 9 is a one-time measurement: `probe_m3_leave_unlock.py` now carries the leave
  recorder; arms `firefox:warm:edit,firefox:warm:none --repeats 12`. **CODE ONLY, never run.** Run
  it on the final page/host, before the H+J release archive; the owner decides timing; never
  alongside another M3 runner.

**Page-honesty runner shakedown — DONE for the pre-review page, but that baseline is now stale.**
`check_m3_page_honesty.py` shakedown forced runner fixes recorded in spec §7.9: V4/V2 were aiming
at canvas fraction y=0.28 (= the last line), which walked straight into finding 096 (kills v8
after 30 s) — now aims at the first ink band via `TEXT_LINES`; the writable-control
`delete-forward` at a paragraph end is a contract-boundary refusal, so the arm does one
`move-character-left` first. §7.10 records tool fixes the session itself found: U3's unit test
missed a `!==` revision-comparison mutant (measured 42/42 green before the fix; two assertions
added, now red), V2's census could pass on an empty set, U7 must read `#s-pending` at
`beforeunload`. Evidence: `findings/evidence/m3-page-honesty/shakedown/README.md`,
`unit-red-cases/` (README + JSON). Final-pass reports `2026-09-29T095133+0000.json` (Chrome) and
`2026-09-29T100026+0000.json` (Firefox) were 15/15 clean, red cases 116/116 — **but the page and
runner changed afterwards** (`b61e9fd9`, the review dispositions below), so these reports are no
longer the baseline. K-sep in particular has no clean run under the new scoring.

**K9′/K10′ and full locks shakedown — DONE.** `check_m3_locks.py` §7.4 shakedown
(`findings/evidence/m3-locks/shakedown/2026-09-29T101313+0000.json`): premise held in all four
arms (share 3→1 read back, server lock owned by `lcprobe` at the cut, PUT 403 WITH the token, not
412). Full locks shakedown (`.../2026-09-29T101606+0000.json`): all 22 arms (K1–K12) pass in both
browsers on page `f42e0227…` / host 0.2.3; red cases 99/99
(`red-cases-on-2026-09-29T101606.txt`).

**Opus adversarial review of the implementation and runners — DONE; all items dispositioned in
`b61e9fd9` except BLOCKING 1.** Review text and disposition table:
`findings/evidence/m3-page-honesty/review-2026-09-29-opus-implementation.md`. 2 BLOCKING, 4
SHOULD, 11 NOTE.

- BLOCKING 2 fixed: page `hasUnsavedWork()` is now fail-closed
  (`session ? session.hasUnsavedEdits() : false`); new test
  `wasm_sdk_probe/editor-shell-v2/tests/page-unsaved-work.test.mjs` compiles the page's function
  with only `session`/`savesUnsettled` in scope; 4 page mutants go red
  (`unit-red-cases/2026-09-29-page-red-cases.json`).
- SHOULDs fixed: V7 checks the two moves by name; the writable control also checks the reverse
  direction; K-sep's two presses are split across two evaluates and save #1 is read back from
  Nextcloud versions and must NOT carry the marker; the view-only unit test now covers
  selectRange/copySelection (the `mutation !== false` gate mutant, reproduced at 42/42 green, now
  red).
- NOTEs: the recorder records the `onbeforeunload` property channel too; every editing arm
  requires the edit to actually land; V1/V7/U1-Firefox are no longer vacuous on missing fields;
  a `HOST_COMMIT` pin was added (required for a counted run); 16 red cases added and broad
  substrings narrowed; K-two's second press now fires when the page shows 「儲存 N ms」 (during
  save #1). Registered but not fixed: held Enter on the save button (finding 106, via the button),
  `check_m3_assets`'s shared "K2 instrument" prefix and `check_m3_locks`'s any-problem red-case
  judging (both outside those runners' diff limits for this round), V2's keyboard-half limits
  (finding 067's path), V5/V4 vacuities compensated downstream, `e2-editor.html` unbound (finding
  094).
- A dry run of the page-honesty red cases against the old (now-stale) reports found 140 red; 14
  MISSING (K-sep only — needs a fresh run).
- The page is now `fc80050c…` in `wasm_sdk_probe/web/e2-editor-app.js` (also sets
  `data-litecore-page-guard="own"` when a host lacks `watchUnsaved`, a §7.1 non-conformance).
  `dist/` and the packaged engine are **NOT** updated. v2 unit suite 116/116, base shell 65/65.

**BLOCKING 1 — confirmed by reading the host source, NOT yet measured.** Host
`js/litecore-editor.js`: `put()` records `withToken: true` at send time; a 60 s `refreshLock()`
answered LOST while the PUT is still on the wire makes `loseLock()` set `token = null`; the PUT
then comes back 412; `saveOnce` calls `tokenOnServer(token)` with `null` → `held.replace` throws a
TypeError; `save()` has a `try`/`finally` but no `catch`, so the save rejects with no copy and
nothing stranded; the page has already cleared `dirty` and settles the save, so leaving is never
asked about — edits are lost. This falsifies spec §7.1's premise that "every rejection is a copy
or stranded." The §7.5-registered `.text()` throw is the same class of bug.

- Probe written, never run: `wasm_sdk_probe/tools/probe_m3_save_throw.py` (Chrome, CDP Fetch
  domain holds the save's PUT, deletes the `oc_files_lock` rows, lets every other request through
  until the host records its lock `lost` by refresh, then releases the PUT; verdict KEPT = bytes
  on the original, or in a copy, or (stranded and leave asked), else LOST). The first run may need
  debugging — the Fetch pump, and whether a refresh against a deleted lock row really answers a
  LOST status; if it does not, the probe's conclusion is "the host's refresh never lost the lock":
  rethink the trigger, do not change the expectation silently.
- Fix script (in repo, NOT applied): `findings/evidence/m3-page-honesty/save-throw/host_fix_0_2_4.py`.
  Step `b` = catch-all only (every save ends saved/copy/stranded; an unexpected throw strands the
  bytes; no version bump). Step `a` = ask about the token that was actually sent (`sentToken`) +
  `tokenOnServer` returns false on a null token + version 0.2.4.
- Planned three-step measurement on the same probe: (1) host `c740d2f` as-is → expect LOST; (2)
  apply step `b` in the host working tree (uncommitted; the probe uses a cold Chrome profile so it
  fetches the new JS) → expect KEPT via stranded + leave asked; (3) apply step `a` → expect KEPT
  on the original (deleting the lock row does not move the ETag, so the retry without the token
  should be 204) or a copy. Then commit host 0.2.4 and run `ddev occ upgrade` in the host dir;
  register finding 108 (data-loss path in our host; findings prose zh-TW, evidence English);
  append spec §7.11 (zh-TW) with the review dispositions summary, this measurement, and the §7.5
  `.text()` item now closed by the catch-all.

## State

- `study_LiteCore`: `main`, HEAD `d7081a00`, not pushed. Commits this session listed above.
- `~/Projects/Nextcloud_Apps/litecore`: `c740d2f` (0.2.3), clean, not pushed. The 0.2.4 fix script
  exists in `study_LiteCore` but has not been applied to the host tree.
- `litecoreprobe`: unchanged (`litecore` 0.2.1).
- `dist/` and the packaged engine are behind the reviewed page (`fc80050c…`); `dist/` still ships
  the pre-review page. Re-run `package_m3_engine.py` after the next `dist/` update.
- **Shell generation still NOT frozen** (carried from 09-29f) — `dist/` is ahead of the last
  frozen bundle (`e2/editor-shell-v2-bundle-v53.json`). `make test-e2-c-static` has not been run
  since these changes.
- Every page-honesty and assets shakedown report predating `b61e9fd9` is stale evidence for
  scoring purposes (the page and runner changed underneath it), even though the underlying
  measurements (canvas-aim fix, K9′/K10′ premise, etc.) still stand as findings.

## What is next

1. BLOCKING 1: run the three-step measurement on `probe_m3_save_throw.py`, commit host 0.2.4,
   `ddev occ upgrade`, register finding 108, append spec §7.11.
2. Update `dist/` from the final page: `make -n` first, then `make dist/e2-editor-app.js` (plain
   `cp`); then `python3 wasm_sdk_probe/tools/package_m3_engine.py` (new buildId).
3. Re-shakedown on the final page + host 0.2.4, one M3 runner at a time: page honesty (both
   browsers, all arms; then `--red-cases` on the two reports, expect roughly 154 including
   K-sep), assets (condition 10 again, red cases), locks (full, red cases), and — not yet run at
   all this round on the new page/host — versions, host_entry, same_second.
4. Freeze shell generation v54 (`tools/build_e2_c_shell_bundle.py`, MANIFEST pointer with a dated
   comment), then `make test-e2-c-static`.
5. Fill the pins as bindings written before the runs: page-honesty `PAGE_SHA256`,
   `SESSION_SHA256` (`747eea71…`, the subclass did not change this round), `HOST_VERSION` 0.2.4,
   `HOST_COMMIT`; plus the four §7.6 constants (`check_m3_locks.PAGE_SHA256`,
   `check_m3_assets.PAGE_SHA256`, `check_m3_versions.HOST_COMMIT`,
   `check_m3_same_second.HOST_VERSION`).
6. Counted runs (sonnet for long runs, never two M3 runners at once): PAGE HONEST, LOCKS LAND,
   VERSIONS CORRECT, ASSETS DELIVERED, HOST_ENTRY LANDS, SAME-SECOND SAVES KEPT; product-path net
   v8/v14 cell for cell against the baseline.
7. Then findings 106/107 (and 108) move to fixed; run condition 9's one-time measurement; run
   priority step 3 (H+J) on a 0.2.4 release archive.

## Things this round taught

- Aiming a runner at a fixed canvas fraction put the caret on the last line and walked straight
  into finding 096 — the V arms died before measuring anything; read where the click actually
  lands (ink bands) instead of trusting a fraction.
- Re-running old red cases instead of copying them found a mutant nothing had caught (the `!==`
  revision comparison); a red-case set is itself a sample, and adding one more plausible mutant is
  cheap insurance.
- The spec's U3 said "the page's judgement," but the test covered only the session's — the
  reviewer found the gap by asking which layer each claim actually lives in.
- A predicate that is true by construction (U7's pending check, K-two's secondAt) reads as
  evidence until someone asks whether any real product state could fail it.
- The host's "every save ends saved/copy/stranded" was an unwritten invariant held only by
  convention; an uncaught throw path broke it. Making it hold by construction (a catch-all) is the
  shape of the fix.

## Standing rules to carry

- Never run two M3 runners (or an M3 probe) at once — each clears the whole `oc_files_lock` table.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version
  bump and `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/`, and
  findings' prose are zh-TW. Specs and gate documents are append-only.
- A stray geckodriver (port 58719, ~27 h old as of 2026-09-29, not from this session) was left
  alone.
- Handed off at a task boundary because context passed the 400k soft limit, not because the round
  was finished — BLOCKING 1's measurement, dist update, re-shakedown, generation freeze, and every
  counted run are still ahead.

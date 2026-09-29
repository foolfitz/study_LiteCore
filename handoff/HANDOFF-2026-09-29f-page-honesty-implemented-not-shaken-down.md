# Handoff, 2026-09-29f — page honesty implemented, not shaken down; readback cost cleared

Entry points: this file, `specs/SPEC-M3-page-honesty.md` (criteria + §7 amendment + §7.7 census),
`findings/evidence/m3-page-honesty/review-2026-09-29-opus.md` (26-item review, disposition table),
`findings/107-page-leaving-with-unsaved-edits-asks-nothing-and-the-edits-are-gone.md`,
`findings/evidence/m3-unsaved-leave/` (107 probe + after-fix smoke),
`findings/evidence/m3-same-second/README.md` and `readback-size/` (readback-cost condition 6),
`wasm_sdk_probe/tools/check_m3_page_honesty.py` (new runner, not yet run).

Picks up from `handoff/HANDOFF-2026-09-29e-same-second-saves-kept.md` (condition 10, stopped for
the owner's choice among A/C/F/G/H/I/J). The owner asked to continue and for a priority
recommendation; agreed order: (1) readback cost on large documents, (2) C+I as one page-identity
round (extended mid-round with finding 107), (3) H+J merged onto the closing 0.2.3 release,
(4) A, (5) G, (6) F (upstream submissions stay on hold). This handoff covers (1) and the (2) design
and implementation; shakedown, red cases, generation freeze, and counted runs are still ahead.

## Status

**Readback cost — DONE.** Commit `184edcb9`; criteria committed alone first (`3f76f82d`,
`findings/evidence/m3-same-second/readback-size/CRITERIA.md`); probe
`wasm_sdk_probe/tools/probe_m3_readback_size.py`; report
`findings/evidence/m3-same-second/readback-size/2026-09-29T060123+0000.json`. Ruling D condition 6
(median read-back <= median PUT, host's own record) holds at every size tested — fixture, 1/5/20/50
MiB, up to 52.4 MB — in both browsers, ratio 0.32–0.61; the slowest read-back in every arm still
beat the fastest PUT. The read-back is a full uncompressed download; the "on a real link it costs
about size/downlink" framing is named, not measured (localhost only). `findings/evidence/m3-same-second/README.md`
got an appended correction and finding 103 was amended in place. No host change follows from this
— the page round carries no readback-cost fix.

**Finding 107 (NEW) — reproduced, not yet counted-run.** Leaving the editor with unsaved edits asks
nothing; the edits are gone. Chrome 3/3 with a control arm proving the instrument sees leave
dialogs. `findings/107-page-leaving-with-unsaved-edits-asks-nothing-and-the-edits-are-gone.md`,
evidence in `findings/evidence/m3-unsaved-leave/` (probe `probe_m3_unsaved_leave.py`), commit
`1b3e7060`. Missed until now because every existing M3 runner saves before it leaves — harness path
vs. user path again.

**Spec + review — DONE.** `specs/SPEC-M3-page-honesty.md`: criteria first (`6b77bf1a`), then an
opus read-only adversarial review (26 items, 4 BLOCKING — all 4 verified against source by the main
session), then a §7 amendment appended (append-only, `c3f3d826`;
`findings/evidence/m3-page-honesty/review-2026-09-29-opus.md` holds the review text and disposition
table).

**Implementation — DONE, NOT shaken down.** Commit `500eb39a`. Owner decision (2026-09-29):
read-only files = A, view-only (read, move the caret, no editing, no saving).

- `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js` — verified sha256
  `747eea71…` (`wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js`). Adds `setViewOnly`,
  `viewOnly`, `actionMutates` (fail-closed: only `BOUNDARY_CAPABLE_MOVES` count as non-mutating),
  `hasUnsavedEdits()`, and an `_enqueue` override that refuses `mutation: true` before queueing
  (`EDITOR_VIEW_ONLY`, `recovery: "none"`). `editor-shell/editor-session.js` (E1-C-bound) is
  untouched.
- Tests: +5 in `editor-shell-v2/tests/narrow-editor-v2-session.test.mjs`; v2 suite 112/112, base
  `editor-shell/tests` 65/65. Four red cases (gate removed; `actionMutates` default false;
  revision-based unsaved; unsaved without `pending`) each went red and were restored — not yet
  written into an evidence file.
- `wasm_sdk_probe/web/e2-editor-app.js` — verified sha256 `f42e0227…`
  (`wasm_sdk_probe/web/e2-editor-app.js`), was `fbfb59a4…`. Adds: 107 guard via `watchUnsaved`
  (page registers its own listener only when the host lacks one, and in download mode); 106
  `event.repeat` ignored (still calls `preventDefault`); view-only mode (session gate on,
  `#sink.readOnly`, `#text` disabled, `data-mutates` applied to every toolbar button at the end of
  `updateGestureAffordance()`, `saveDocument()` refuses in view-only); `EDITOR_VIEW_ONLY` shown as
  one sentence, 「唯讀：只能檢視」.
- `dist/` updated only by `make dist/e2-editor-app.js dist/editor-shell-v2/narrow-editor-v2-session.js`
  (plain `cp`, checked with `make -n` first); engine repackaged with
  `python3 wasm_sdk_probe/tools/package_m3_engine.py` (buildId `4aa3646d4e540b32`).
- New runner `wasm_sdk_probe/tools/check_m3_page_honesty.py` (sha256 `6764bd85…`, per session
  notes — not independently reverified here): arms U0, U1, Uwin, U2, U3, U4, U5, U7, U6a, U6b
  (download mode via `web/serve.py --root dist`), Kheld, Ksep, Ktwo, Vro, Vrw; scoring; `--score`;
  a counted run refuses until `PAGE_SHA256`/`SESSION_SHA256` are filled in. **Has not been run even
  once.** No `--red-cases` yet.
- Host repo `~/Projects/Nextcloud_Apps/litecore` — verified: `c740d2f` = 0.2.3
  (`appinfo/info.xml` `<version>0.2.3</version>`), working tree clean. Commit adds `load()`
  returning `readOnly`, `watchUnsaved`, `out.guards[{at, reasons}]`, `out.handedReadOnly`, and a
  read-only notice, 「唯讀：只能檢視，不能修改或存檔。」. The dev instance ran `ddev occ upgrade`
  to 0.2.3 and serves the new page and subclass.

**§7.7 (appended in `500eb39a`)** — a read-only static census (Explore agent) of every runner's
leave points. Only `check_m3_assets` K2 changes outcome: it leaves with an unsaved paragraph action
on both opens; host 0.2.3 then guards with reason `page` and skips the `beforeunload` UNLOCK; in
Firefox with the HTTP cache on, that lands on finding 105's unfixed pre-fix path, so K2-5 (lock
released within 10 s) is likely red. **DECISION PENDING before any counted run**: (A) K2 saves
before leaving — leaning this way; K2 measures asset delivery, the unsaved-leave path belongs to
U1; (B) accept and register; (C) host releases anyway on `page`-only reason — rejected, reopens
review item 2. The census also surfaced and fixed a timing flaw: `savesUnsettled` now settles when
`HOST.save()` settles (or the download is handed over), not after `run()`'s repaint.

## Design outcomes worth carrying forward

- In host mode the **host** is the sole `beforeunload` decider (`liteCoreHost.watchUnsaved(fn)`),
  because the host's listener registers before the page module is imported and releases the lock
  only when it does not guard — a page-level guard alone would leave a user who chose "stay"
  holding no lock. This was BLOCKING review item 2, found only by reading both scripts'
  registration order.
- "Unsaved" = session `dirty` || `pending > 0` || a save was asked for and has not yet settled
  (settled = `HOST.save()` resolved/rejected, or the anchor was clicked in download mode). Never
  revision-based (that repeats finding 099's class of bug).
- The recorder wraps `Event.prototype.preventDefault` and the `BeforeUnloadEvent.returnValue`
  setter, attributes by stack, stores results in localStorage under a per-cell nonce; a missing
  `fired` record fails the cell.
- K9′/K10′ predicates are written out in the spec (open writable, revoke the share after open, PUT
  403 with the token, "412 = red, stop").
- Regression pins enumerated as exactly four constants: `check_m3_locks.PAGE_SHA256`,
  `check_m3_assets.PAGE_SHA256`, `check_m3_versions.HOST_COMMIT`, `check_m3_same_second.HOST_VERSION`.
- §7.5 registers six items not fixed this round, including: Firefox "asked, then left" still relies
  on the `pagehide` UNLOCK (finding 105's unfixed path); `tokenOnServer` `.text()` throw leaves
  neither a copy nor a stranded lock; V2 measures revision, not content, because the runner has no
  handle to `session`.

## State

- `study_LiteCore`: `main`, clean (verified via `git status --short`), not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `c740d2f` (0.2.3), clean, not pushed; the dev instance has
  run `occ upgrade` to 0.2.3.
- `litecoreprobe`: still `litecore` 0.2.1 — unchanged.
- **Shell generation NOT frozen.** `dist/` is ahead of the last frozen bundle
  (`e2/editor-shell-v2-bundle-v53.json`). `make test-e2-c-static` has not been run since these
  changes — it may fail until v54 is frozen; check before assuming pass or fail.

## What is next

1. Decide assets K2 (§7.7 above); append the decision to the spec before touching that runner.
2. Shake down `check_m3_page_honesty.py` arm by arm, Chrome first. On first runs verify: Firefox
   stack attribution (the runner's asking listener is a `new Function` with
   `//# sourceURL=m3honesty-runner.js`); localStorage readable after the navigation; V2
   writable-control items that may not advance (set-list-none on a non-list paragraph, clear-format,
   undo/redo ordering, formats needing a range) — any exemption must be appended to §7.3 with its
   reason before counting.
3. Known deviation to amend into the spec before counting: §7.3's K-two says read `#s-pending > 0`
   right after dispatch, but the runner implements "the second press's host-clock time < the first
   save's PUT `respondedAt`", because `saveOnce` starts in a later microtask so `pending` can read 0
   within the same task.
4. Write red cases for the new runner (one mutation per criterion), on a clean shakedown report;
   also write the four unit-test red cases into an evidence file (not yet done).
5. `check_m3_locks.py`: implement K9′/K10′ per §7.4, add the pin, shake down (403 with token, else
   stop).
6. An opus adversarial review of the implementation and the runner, before any counted run.
7. Freeze shell generation v54 only after all shell/page changes land
   (`tools/build_e2_c_shell_bundle.py`, MANIFEST pointer with a dated comment); then
   `make test-e2-c-static`.
8. Fill the pins (the new runner's two, plus the four constants listed above) as bindings written
   before the runs.
9. Counted runs — sonnet for long runs, never two M3 runners at once: PAGE HONEST, LOCKS LAND
   (K9′/K10′), VERSIONS CORRECT, ASSETS DELIVERED, HOST_ENTRY LANDS, SAME-SECOND SAVES KEPT;
   product-path net v8/v14 cell for cell against the baseline.
10. Then findings 106 and 107 move to fixed; step 3 from the priority order (H+J) runs on a 0.2.3
    release archive.

## Things this round taught

- BLOCKING review item 2 (host-as-sole-decider) was structural and visible only by reading both
  scripts' registration order — it would have looked correct in every cell, and only failed a user
  who chose "stay."
- Harness path vs. user path, again: every existing M3 runner saved before leaving, which is why
  107 stayed invisible until a probe was written that does not save.
- A size claim (readback <= PUT) admitted on one small fixture was measured before building
  anything on it, and held up to 52.4 MB — measuring first was still the cheaper order than
  designing around an unverified claim.
- Unit-test red cases were run before trusting the new tests: four mutations, each went red.
- Handed off at a task boundary because context passed the 400k soft limit, not because the round
  was finished — shakedown, generation freeze, and every counted run are still ahead.

## Standing rules to carry

- Don't start or restart other ddev projects during a counted run; every M3 runner clears the whole
  `oc_files_lock` table, so never run two at once.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version
  bump and `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/`, and
  findings' prose are zh-TW.
- Spec and gate documents are append-only: corrections go at the end, naming what they supersede;
  the original stays.
